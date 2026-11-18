#!/usr/bin/env python3
"""
Cosmic Byte Fixed-Mode RGB experiment.

Reads the two 1032-byte HID reports from a USBPcap .pcapng capture,
changes the suspected RGB bytes in the 0x08B8 report (payload offsets
29, 30, 31), then sends 0x08B8 followed by the captured 0x03B6 report.

Install:
    py -m pip install hidapi

First list HID devices:
    py cosmic_byte_rgb.py --list

Then send (replace VID/PID with values shown by --list):
    py cosmic_byte_rgb.py --vid 0xVVVV --pid 0xPPPP --rgb FF 80 00 --send

Use --interface N if more than one interface matches.
"""

import argparse
import struct
import sys
import time
from pathlib import Path

REPORT_LEN = 1032
RGB_OFFSETS = (29, 30, 31)
CMD_RGB = bytes((0x06, 0x08, 0xB8, 0x00))
CMD_APPLY = bytes((0x06, 0x03, 0xB6, 0x00))


def pcapng_packets(path):
    data = Path(path).read_bytes()
    offset = 0
    endian = "<"

    while offset + 12 <= len(data):
        block_type = struct.unpack_from(endian + "I", data, offset)[0]

        # Section Header Block determines byte order.
        if block_type == 0x0A0D0D0A:
            bom = data[offset + 8:offset + 12]
            if bom == b"\x4d\x3c\x2b\x1a":
                endian = "<"
            elif bom == b"\x1a\x2b\x3c\x4d":
                endian = ">"
            else:
                raise ValueError("Unrecognized PCAPNG byte-order magic")

        block_type, block_len = struct.unpack_from(endian + "II", data, offset)
        if block_len < 12 or offset + block_len > len(data):
            raise ValueError("Malformed PCAPNG block")

        if block_type == 6:  # Enhanced Packet Block
            captured_len = struct.unpack_from(endian + "I", data, offset + 20)[0]
            packet = data[offset + 28:offset + 28 + captured_len]
            yield packet

        offset += block_len


def extract_reports(path):
    found = {}
    for packet in pcapng_packets(path):
        # USBPcap header is 28 bytes; HID class data begins after
        # the 8-byte SET_REPORT/class-transfer prefix in this capture.
        if len(packet) < 36 + REPORT_LEN:
            continue
        report = packet[36:36 + REPORT_LEN]
        command = report[:4]
        if command in (CMD_RGB, CMD_APPLY):
            found[command] = bytearray(report)

    missing = [cmd.hex(" ") for cmd in (CMD_RGB, CMD_APPLY) if cmd not in found]
    if missing:
        raise ValueError(
            "Could not find both required HID reports in the capture. "
            "Missing: " + ", ".join(missing)
        )
    return found[CMD_RGB], found[CMD_APPLY]


def parse_byte(value):
    try:
        number = int(value, 16)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("RGB values must be hex bytes, e.g. FF or 80") from exc
    if not 0 <= number <= 255:
        raise argparse.ArgumentTypeError("RGB bytes must be between 00 and FF")
    return number


def list_devices():
    try:
        import hid
    except ImportError:
        print("Missing dependency. Install with: py -m pip install hidapi")
        return 1

    devices = hid.enumerate()
    if not devices:
        print("No HID devices found.")
        return 0

    for item in devices:
        vid = item.get("vendor_id", 0)
        pid = item.get("product_id", 0)
        print(
            f"VID:PID={vid:04X}:{pid:04X}  "
            f"interface={item.get('interface_number')}  "
            f"usage_page={item.get('usage_page')}  "
            f"product={item.get('product_string')!r}  "
            f"path={item.get('path')!r}"
        )
    return 0


def main():
    parser = argparse.ArgumentParser(description="Set Cosmic Byte Fixed-Mode RGB using a captured HID template.")
    parser.add_argument("--capture", default="custom_fixed.pcapng", help="Reference PCAPNG capture")
    parser.add_argument("--list", action="store_true", help="List HID devices and exit")
    parser.add_argument("--vid", type=lambda x: int(x, 0), help="Keyboard USB vendor ID, e.g. 0x1234")
    parser.add_argument("--pid", type=lambda x: int(x, 0), help="Keyboard USB product ID, e.g. 0x5678")
    parser.add_argument("--interface", type=int, help="Optional HID interface number")
    parser.add_argument("--rgb", nargs=3, type=parse_byte, metavar=("RR", "GG", "BB"),
                        default=(255, 128, 0), help="RGB hex bytes (default: FF 80 00)")
    parser.add_argument("--delay", type=float, default=0.06, help="Delay between reports in seconds")
    parser.add_argument("--send", action="store_true", help="Actually send reports; without this, only previews them")
    args = parser.parse_args()

    if args.list:
        return list_devices()

    rgb_report, apply_report = extract_reports(args.capture)
    for offset, value in zip(RGB_OFFSETS, args.rgb):
        rgb_report[offset] = value

    print(f"Capture: {args.capture}")
    print(f"RGB to send: #{args.rgb[0]:02X}{args.rgb[1]:02X}{args.rgb[2]:02X}")
    print(f"Report 1: {len(rgb_report)} bytes, command={rgb_report[:4].hex(' ')}, "
          f"RGB bytes={bytes(rgb_report[i] for i in RGB_OFFSETS).hex(' ')}")
    print(f"Report 2: {len(apply_report)} bytes, command={apply_report[:4].hex(' ')}")

    if not args.send:
        print("\nPreview only. Add --send to transmit these reports.")
        return 0

    if args.vid is None or args.pid is None:
        parser.error("--vid and --pid are required when using --send")

    try:
        import hid
    except ImportError:
        print("Missing dependency. Install with: py -m pip install hidapi", file=sys.stderr)
        return 2

    matches = [
        d for d in hid.enumerate(args.vid, args.pid)
        if args.interface is None or d.get("interface_number") == args.interface
    ]
    if not matches:
        print("No matching HID interface found. Check VID/PID and --interface.", file=sys.stderr)
        return 2
    if len(matches) > 1:
        print("More than one HID interface matches. Re-run with --interface N.", file=sys.stderr)
        for d in matches:
            print(f"  interface={d.get('interface_number')} path={d.get('path')!r}")
        return 2

    device = hid.device()
    try:
        device.open_path(matches[0]["path"])
        # hidapi expects the complete report, including the captured 0x06 prefix.
        sent1 = device.write(bytes(rgb_report))
        if sent1 != REPORT_LEN:
            raise RuntimeError(f"First report write returned {sent1}, expected {REPORT_LEN}")
        time.sleep(max(0.0, args.delay))
        sent2 = device.write(bytes(apply_report))
        if sent2 != REPORT_LEN:
            raise RuntimeError(f"Second report write returned {sent2}, expected {REPORT_LEN}")
        print("Both reports sent. Check whether the keyboard changed to the requested colour.")
    finally:
        device.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
