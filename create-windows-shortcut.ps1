$ErrorActionPreference = "Stop"

$repoRoot = $PSScriptRoot
$shortcutPath = Join-Path $repoRoot "Paper Radar.lnk"
$targetPath = Join-Path $repoRoot "desktop\dist\win-unpacked\Paper Radar.exe"
$iconPath = Join-Path $repoRoot "desktop\assets\icon.ico"

if (-not (Test-Path -LiteralPath $targetPath)) {
    throw "Paper Radar.exe was not found at: $targetPath. Build the desktop app first with: npm --prefix desktop run build"
}

if (-not (Test-Path -LiteralPath $iconPath)) {
    throw "Shortcut icon was not found at: $iconPath"
}

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $targetPath
$shortcut.WorkingDirectory = Split-Path -Parent $targetPath
$shortcut.IconLocation = $iconPath
$shortcut.Description = "Launch Paper Radar desktop app"
$shortcut.WindowStyle = 1
$shortcut.Save()

Write-Host "Created shortcut: $shortcutPath"
