# Cosmic Byte Accent Sync for Windows 11

This utility keeps the Fixed Mode RGB colour of your supported Cosmic Byte keyboard matched to your Windows accent colour.

## Before You Start

- Set the keyboard to **Fixed Mode**.
- Close the official Cosmic Byte RGB software while the utility runs.
- Keep the keyboard connected.
- Find your keyboard's VID and PID by running `cosmic_byte_rbg.py --list`. Enter them in `cosmic_byte_accent_sync.py` as hexadecimal values with the `0x` prefix, then build.

## Build the EXE

1. Extract the entire folder to a normal location on your PC.
2. Install Python 3 for Windows if you don't have it. Enable **Add Python to PATH** during installation.
3. Double-click `build_exe.bat`.
4. When the build finishes, the executable is at `dist\CosmicByteAccentSync.exe`.

The EXE must be built on Windows with PyInstaller. Building it on Linux or macOS is not reliable.

## Run at Startup

You can use either the Startup folder or Task Scheduler.

**Option A: Startup folder (simplest)**

1. Right-click `install_startup.ps1` and choose **Run with PowerShell**.
2. The program starts each time you sign in.
3. To remove it, run `remove_startup.ps1` with PowerShell.

**Option B: Task Scheduler (more control)**

Use **Create Task**, not Create Basic Task.

1. Open Task Scheduler (`Win + R`, type `taskschd.msc`).
2. Click **Create Task...** in the Actions pane.
3. **General tab:** enter a name and description. Select **Run only when user is logged on**. Do not select "Run whether user is logged on or not" unless you have a specific reason. The accent colour is stored per user, so the task has to run as you. Running it as SYSTEM would read the wrong colour and write the log to the wrong folder.
4. **Triggers tab:** click **New...**, choose **At log on**, and click OK.
5. **Actions tab:** click **New...**, set Action to **Start a program**, and browse to `dist\CosmicByteAccentSync.exe`.
6. In the **Start in** field, enter the folder that contains the EXE, without quotation marks. Task Scheduler otherwise uses `C:\Windows\System32`, and PyInstaller builds often fail there.
7. Click OK.

## Test It

1. In Task Scheduler, right-click the task and choose **Run**.
2. Open Task Manager (`Ctrl + Shift + Esc`) and confirm `CosmicByteAccentSync.exe` is running.
3. Change your accent colour in Windows Settings and check that the keyboard follows.

## Troubleshooting

- **A console window appears:** rebuild the EXE with `--noconsole` in the PyInstaller command.
- **The program exits immediately:** check the log file at `%LOCALAPPDATA%\CosmicByteAccentSync\sync.log`.
- **Windows Security warns about the EXE:** confirm that you built it from this source before you allow it.

## Notes

- The PCAPNG capture is not needed at runtime, because the report templates are embedded in `cosmic_byte_accent_sync.py`.
- Startup runs when you sign in to Windows, not at the sign-in screen.
