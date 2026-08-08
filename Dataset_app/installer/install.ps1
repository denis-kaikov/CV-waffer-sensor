Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Windows.Forms

$sourceRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$packageZip = Join-Path $sourceRoot "package.zip"
$installRoot = Join-Path $env:LOCALAPPDATA "Programs\CassetteDatasetCapture"
$startMenuDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\CassetteDatasetCapture"
$desktopShortcut = Join-Path ([Environment]::GetFolderPath("Desktop")) "CassetteDatasetCapture.lnk"

if (-not (Test-Path $packageZip)) {
    throw "package.zip not found рядом с install.ps1."
}

if (Test-Path $installRoot) {
    Remove-Item -LiteralPath $installRoot -Recurse -Force
}

New-Item -ItemType Directory -Path $installRoot -Force | Out-Null
Expand-Archive -LiteralPath $packageZip -DestinationPath $installRoot -Force

New-Item -ItemType Directory -Path $startMenuDir -Force | Out-Null

$shell = New-Object -ComObject WScript.Shell
$targetExe = Join-Path $installRoot "CassetteDatasetCapture.exe"

$startMenuShortcut = Join-Path $startMenuDir "CassetteDatasetCapture.lnk"
$shortcut = $shell.CreateShortcut($startMenuShortcut)
$shortcut.TargetPath = $targetExe
$shortcut.WorkingDirectory = $installRoot
$shortcut.Save()

$desktop = $shell.CreateShortcut($desktopShortcut)
$desktop.TargetPath = $targetExe
$desktop.WorkingDirectory = $installRoot
$desktop.Save()

[System.Windows.Forms.MessageBox]::Show(
    "Установка завершена.`nПапка: $installRoot",
    "CassetteDatasetCapture",
    [System.Windows.Forms.MessageBoxButtons]::OK,
    [System.Windows.Forms.MessageBoxIcon]::Information
) | Out-Null
