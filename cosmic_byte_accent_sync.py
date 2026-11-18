#!/usr/bin/env python3
"""
Automatically synchronize a Cosmic Byte keyboard's Fixed Mode colour
with the current Windows accent colour.

Based on the user's confirmed working HID protocol:
  VID:PID = 258A:0049
  HID interface = usage_page 0xFF00 and "Col06" in its path
  Feature reports = 0x08B8 then 0x03B6
  RGB bytes in first report = offsets 29, 30, 31

Install:
    py -m pip install hidapi

Run continuously:
    py cosmic_byte_accent_sync.py

Apply once and exit:
    py cosmic_byte_accent_sync.py --once

Stop continuous syncing with Ctrl+C.
"""

import argparse
import base64
import ctypes
import logging
import os
import sys
import time
import winreg

import hid

VID = 0x258A
PID = 0x0049
REPORT_LENGTH = 1032
RGB_OFFSETS = (29, 30, 31)

# Exact report templates extracted from the working custom_fixed.pcapng.
RGB_REPORT_TEMPLATE = base64.b64decode(
    "Bgi4AEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAD/gAAAAP8A/wD//wD/AP8A////////AAAAAP8A/wD//wD/AP8A////////AAAAAP8A/wD//wD/AP8A////////AAAAAP8A/wD//wD/AP8A////////AAAAAP8A/wD//wD/AP8A////////AAAAAP8A/wD//wD/AP8A////////AAAAAP8A/wD//wD/AP8A////////AAAAAP8A/wD//wD/AP8A////////AAAAAP8A/wD//wD/AP8A////////AAAAAP8A/wD//wD/AP8A////////AAAAAP8A/wD//wD/AP8A////////AAAAAP8A/wD//wD/AP8A////////AAAAAP8A/wD//wD/AP8A////////AAAAAP8A/wD//wD/AP8A////////AAAAAP8A/wD//wD/AP8A////////AAAAAP8A/wD//wD/AP8A////////AAAAAP8A/wD//wD/AP8A////////AAAAAP8A/wD//wD/AP8A////////AAAAAP8A/wD//wD/AP8A////////AAAAAP8A/wD//wD/AP8A////////AAAAAP8A/wD//wD/AP8A////////AAAAAP8A/wD//wD/AP8A//////8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
)
APPLY_REPORT = base64.b64decode(
    "BgO2AAAAAAAAAAAAAABapQMDAAAAASABAAAAAFVVAQAAAAAA//8AKQcpBykHKQcpBykHKQcpBykHKQApBykHKQcpBykHKQcpBykHKQcpABAAAAdJB0kHSQdJB0kHSQdJCQgJCQAJAAkJCQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABapQMDAAAAAQABAAAAAFVVAQAAAAAA//8HSQdJB0kHSQdJB0kHSQdJB0kHSQdJB0kHSQdJB0kHSQdJB0kHSQdJB0kHSQdJB0kHSQdJB0kHSQdJCQkJCQkJCQkJCQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABapQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
)


def read_windows_accent_rgb():
    """
    Read HKCU\\Software\\Microsoft\\Windows\\DWM\\AccentColor.

    AccentColor is stored as an ABGR DWORD (AABBGGRR), so the low,
    middle and next bytes are the keyboard's R, G and B values.

    If that registry value is absent, use DwmGetColorizationColor,
    whose documented return format is ARGB (AARRGGBB).
    """
    key_path = r"Software\Microsoft\Windows\DWM"
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            value, _value_type = winreg.QueryValueEx(key, "AccentColor")
        value = int(value) & 0xFFFFFFFF
        red = value & 0xFF
        green = (value >> 8) & 0xFF
        blue = (value >> 16) & 0xFF
        return red, green, blue, "AccentColor registry value"
    except OSError:
        pass

    # Fallback: Microsoft documents DWM colorization as 0xAARRGGBB.
    color = ctypes.c_uint32()
    opaque = ctypes.c_int()
    dwmapi = ctypes.WinDLL("dwmapi")
    dwmapi.DwmGetColorizationColor.argtypes = [
        ctypes.POINTER(ctypes.c_uint32),
        ctypes.POINTER(ctypes.c_int),
    ]
    dwmapi.DwmGetColorizationColor.restype = ctypes.c_long
    result = dwmapi.DwmGetColorizationColor(
        ctypes.byref(color),
        ctypes.byref(opaque),
    )
    if result != 0:
        raise RuntimeError(
            "Could not read Windows accent colour "
            f"(DWM HRESULT 0x{result & 0xFFFFFFFF:08X})."
        )

    argb = color.value
    red = (argb >> 16) & 0xFF
    green = (argb >> 8) & 0xFF
    blue = argb & 0xFF
    return red, green, blue, "DWM colorization fallback"


def find_col06():
    for info in hid.enumerate(VID, PID):
        path = info.get("path", b"")
        path_text = (
            path.decode(errors="ignore")
            if isinstance(path, bytes)
            else str(path)
        )

        if info.get("usage_page") == 0xFF00 and "Col06" in path_text:
            device = hid.device()
            device.open_path(path)
            return device

    raise RuntimeError(
        "Could not find the Cosmic Byte Col06 vendor HID interface "
        f"for VID:PID {VID:04X}:{PID:04X}."
    )


def make_rgb_report(rgb):
    if len(RGB_REPORT_TEMPLATE) != REPORT_LENGTH:
        raise ValueError("Embedded RGB report template has the wrong length.")
    report = bytearray(RGB_REPORT_TEMPLATE)
    for position, value in zip(RGB_OFFSETS, rgb):
        report[position] = value
    return bytes(report)


def send_colour(device, rgb):
    rgb_report = make_rgb_report(rgb)

    first_result = device.send_feature_report(rgb_report)
    if first_result < 0:
        raise RuntimeError(
            f"RGB Feature Report failed (return value {first_result})."
        )

    # Preserve the delay used in the successful experiment.
    time.sleep(0.063)

    second_result = device.send_feature_report(APPLY_REPORT)
    if second_result < 0:
        raise RuntimeError(
            f"Apply Feature Report failed (return value {second_result})."
        )


def setup_logging():
    log_dir = os.path.join(
        os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
        "CosmicByteAccentSync",
    )
    os.makedirs(log_dir, exist_ok=True)
    logging.basicConfig(
        filename=os.path.join(log_dir, "sync.log"),
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        encoding="utf-8",
    )


def main():
    setup_logging()
    if sys.platform != "win32":
        logging.error("This program must be run on Windows.")
        raise SystemExit(1)

    parser = argparse.ArgumentParser(
        description="Sync Cosmic Byte Fixed Mode RGB with Windows accent colour."
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Apply the current Windows accent once, then exit.",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=2.0,
        help="How often to check for accent changes in seconds (default: 2).",
    )
    args = parser.parse_args()

    if args.interval < 0.25:
        parser.error("--interval must be at least 0.25 seconds")

    print("Cosmic Byte Windows Accent Colour Sync")
    print("--------------------------------------")
    print("Put the keyboard in Fixed Mode and close the official RGB software.")
    print("Press Ctrl+C to stop.\n")

    device = find_col06()
    last_rgb = None

    try:
        while True:
            accent = read_windows_accent_rgb()
            rgb = accent[:3]
            source = accent[3]

            if rgb != last_rgb:
                send_colour(device, rgb)
                hex_colour = "#{:02X}{:02X}{:02X}".format(*rgb)
                logging.info(
                    "Applied %s (R=%d, G=%d, B=%d) via %s",
                    hex_colour, rgb[0], rgb[1], rgb[2], source
                )
                last_rgb = rgb

            if args.once:
                break

            time.sleep(args.interval)

    except KeyboardInterrupt:
        print("\nAccent colour sync stopped.")
    finally:
        device.close()


if __name__ == "__main__":
    main()
