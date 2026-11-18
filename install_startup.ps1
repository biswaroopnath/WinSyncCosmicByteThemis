$ErrorActionPreference = "Stop"

$exe = Join-Path $PSScriptRoot "dist\CosmicByteAccentSync.exe"
if (-not (Test-Path $exe)) {
    Write-Host "Executable not found. Run build_exe.bat first." -ForegroundColor Red
    exit 1
}

$startup = [Environment]::GetFolderPath("Startup")
$shortcutPath = Join-Path $startup "Cosmic Byte Accent Sync.lnk"

$ws = New-Object -ComObject WScript.Shell
$shortcut = $ws.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $exe
$shortcut.WorkingDirectory = Split-Path $exe
$shortcut.Description = "Synchronize Cosmic Byte keyboard lighting with Windows accent colour"
$shortcut.Save()

Write-Host "Startup enabled. The app will launch when you sign in to Windows." -ForegroundColor Green
Write-Host "Shortcut: $shortcutPath"
