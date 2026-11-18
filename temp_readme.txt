COSMIC BYTE ACCENT SYNC — WINDOWS 11 BUILD KIT
===============================================

WHAT IT DOES
Synchronizes the Fixed Mode RGB colour of the supported Cosmic Byte
keyboard with the current Windows accent colour.

IMPORTANT BEFORE RUNNING
- Put the keyboard in Fixed Mode.
- Close the official Cosmic Byte RGB/control software while this runs.
- Keep the keyboard connected.
- This utility uses the HID protocol already embedded in the Python file.

Note : You will need to know VID/PID ( add 0x as it is in hexadecimal )of your keyboard - use cosmic_byte_rbg.py --list to determine them and change it in cosmic_byte_accent_sync.py then build


BUILD THE EXE
1. Extract this entire folder to a normal folder on your PC.
2. Install Python 3 for Windows if it is not already installed.
   During installation, enable "Add Python to PATH" if offered.
3. Double-click build_exe.bat.
4. When it finishes, the EXE will be at:
   dist\CosmicByteAccentSync.exe

ENABLE AUTOMATIC STARTUP
1. After building, right-click install_startup.ps1.
2. Choose "Run with PowerShell".
3. The shortcut is added to your Windows Startup folder.
   The program will start automatically after you sign in.

DISABLE AUTOMATIC STARTUP
Run remove_startup.ps1 with PowerShell.

LOG FILE
The hidden/background EXE writes its activity and errors to:
%LOCALAPPDATA%\CosmicByteAccentSync\sync.log

NOTES
- The PCAPNG capture is not required at runtime: the working report
  templates are already embedded in cosmic_byte_accent_sync.py.
- The EXE is built on Windows using PyInstaller; it cannot be reliably
  built as a Windows EXE from Linux or macOS.
- Startup means Windows user sign-in, not before the sign-in screen.
- If Windows Security asks about the EXE, verify that you built it from
  this supplied source before allowing it.








instead use task scheduler

To run an executable silently and automatically via Windows Task Scheduler without any console windows or dialogue boxes popping up, you need to configure the task to run under a specific security context.
Here is the step-by-step setup to ensure it runs completely in the background:

Step 1: Create the Basic Task

1. Press Win + R, type taskschd.msc, and press Enter to open Task Scheduler.
2. In the right-hand Actions pane, click Create Task... (do not choose Create Basic Task).
3. In the General tab, give your task a Name and Description.

Step 2: Configure the Secret to Silent Execution 🤫

This is the critical step that prevents any dialogue boxes, command prompts, or windows from appearing when the task triggers.
1. Under the General tab, look at the Security options section at the bottom.
2. Select the radio button: "Run whether user is logged on or not".
	• Why this works: Windows treats tasks run in this mode as background services, completely isolating them from the visual desktop session. Even if your .exe tries to open a window, Windows will suppress it.
3. Check the box for "Run with highest privileges" if your executable requires administrator permissions.
4. Set the "Configure for:" dropdown to your version of Windows (e.g., Windows 10 or Windows 11).

Step 3: Define Your Triggers & Actions

1. Switch to the Triggers tab, click New..., and choose when you want the executable to run (e.g., On a schedule, At startup, or At log on). Click OK.
2. Switch to the Actions tab and click New....
3. Set Action to Start a program.
4. In the Program/script box, browse and select the path to your executable (e.g., C:\Path\To\YourApp.exe).
5. Crucial for PyInstaller apps: In the Start in (optional) box, paste the path to the folder containing your executable (e.g., C:\Path\To\). Leave out the trailing quotes if the path has spaces.
	• Why: PyInstaller executables often crash instantly if they cannot resolve relative paths to their dependencies, and Task Scheduler defaults the working directory to C:\Windows\System32 if this field is left blank.

Step 4: Save and Authenticate

1. Click OK to save the task.
2. A Windows Security prompt will pop up asking for your user account password. Enter your password and click OK.
	• Note: If your Windows user account does not have a password, Windows Security will reject this. You can change the user context to SYSTEM in the General tab by clicking "Change User or Group..." and typing SYSTEM if you do not have a user password.

🧪 How to Test It

To make sure it works without waiting for the scheduled time:
1. Right-click your newly created task in the list and click Run.
2. Open Task Manager (Ctrl + Shift + Esc) and look under the Details or Background processes tab. You should see your executable running silently without any window on your screen.
If you notice the script isn't running properly, let me know:
• Is your executable a PyInstaller --onefile or --onedir build?
• Does the executable require any command-line arguments or network access to run?
I can help you debug the Task Scheduler history codes if it fails.

