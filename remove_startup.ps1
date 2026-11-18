$startup = [Environment]::GetFolderPath("Startup")
$shortcutPath = Join-Path $startup "Cosmic Byte Accent Sync.lnk"

if (Test-Path $shortcutPath) {
    Remove-Item $shortcutPath
    Write-Host "Automatic startup has been disabled." -ForegroundColor Green
} else {
    Write-Host "Startup shortcut was not found; nothing to remove."
}
