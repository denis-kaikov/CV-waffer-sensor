Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$projectFile = Join-Path $repoRoot "src\CassetteDatasetCapture\CassetteDatasetCapture.csproj"
$releaseDir = Join-Path $repoRoot "src\CassetteDatasetCapture\bin\Release\net8.0-windows"
$artifactsRoot = Join-Path $repoRoot "artifacts"
$portableRoot = Join-Path $artifactsRoot "portable\CassetteDatasetCapture"
$payloadRoot = Join-Path $artifactsRoot "installer_payload"
$packageZip = Join-Path $payloadRoot "package.zip"
$setupExe = Join-Path $artifactsRoot "CassetteDatasetCaptureSetup.exe"
$sedFile = Join-Path $artifactsRoot "CassetteDatasetCaptureSetup.sed"
$launcherSource = Join-Path $repoRoot "installer\Launcher.cs"
$installCmdSource = Join-Path $repoRoot "installer\install.cmd"
$installPs1Source = Join-Path $repoRoot "installer\install.ps1"

function Get-Latest8RuntimeVersion {
    param(
        [string]$BasePath
    )

    $version = Get-ChildItem $BasePath -Directory |
        Where-Object { $_.Name -like "8.*" } |
        Sort-Object { [version]$_.Name } -Descending |
        Select-Object -First 1 -ExpandProperty Name

    if (-not $version) {
        throw "No .NET 8 runtime found under $BasePath."
    }

    return $version
}

New-Item -ItemType Directory -Path $artifactsRoot -Force | Out-Null

if (-not (Test-Path (Join-Path $releaseDir "CassetteDatasetCapture.dll"))) {
    throw "Release build not found. Build the project first: dotnet build .\\src\\CassetteDatasetCapture\\CassetteDatasetCapture.csproj -c Release --no-restore"
}

if (Test-Path $portableRoot) {
    Remove-Item -LiteralPath $portableRoot -Recurse -Force
}

if (Test-Path $payloadRoot) {
    Remove-Item -LiteralPath $payloadRoot -Recurse -Force
}

New-Item -ItemType Directory -Path $portableRoot -Force | Out-Null
New-Item -ItemType Directory -Path $payloadRoot -Force | Out-Null

Get-ChildItem $releaseDir -File | Where-Object { $_.Name -ne "CassetteDatasetCapture.exe" } | ForEach-Object {
    Copy-Item $_.FullName -Destination (Join-Path $portableRoot $_.Name) -Force
}

$runtimeVersion = Get-Latest8RuntimeVersion "C:\Program Files\dotnet\shared\Microsoft.NETCore.App"
$desktopVersion = Get-Latest8RuntimeVersion "C:\Program Files\dotnet\shared\Microsoft.WindowsDesktop.App"
$fxrVersion = Get-Latest8RuntimeVersion "C:\Program Files\dotnet\host\fxr"

$dotnetRoot = Join-Path $portableRoot "dotnet"
New-Item -ItemType Directory -Path $dotnetRoot -Force | Out-Null

Copy-Item "C:\Program Files\dotnet\dotnet.exe" -Destination (Join-Path $dotnetRoot "dotnet.exe") -Force
Copy-Item "C:\Program Files\dotnet\host" -Destination (Join-Path $dotnetRoot "host") -Recurse -Force
Copy-Item "C:\Program Files\dotnet\shared\Microsoft.NETCore.App\$runtimeVersion" -Destination (Join-Path $dotnetRoot "shared\Microsoft.NETCore.App\$runtimeVersion") -Recurse -Force
Copy-Item "C:\Program Files\dotnet\shared\Microsoft.WindowsDesktop.App\$desktopVersion" -Destination (Join-Path $dotnetRoot "shared\Microsoft.WindowsDesktop.App\$desktopVersion") -Recurse -Force

$frameworkCsc = "C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
$launcherOut = Join-Path $portableRoot "CassetteDatasetCapture.exe"
& $frameworkCsc `
    /nologo `
    /target:winexe `
    "/out:$launcherOut" `
    /reference:System.dll `
    /reference:System.Core.dll `
    /reference:System.Windows.Forms.dll `
    $launcherSource
if ($LASTEXITCODE -ne 0) {
    throw "Launcher compilation failed."
}

Compress-Archive -Path (Join-Path $portableRoot "*") -DestinationPath $packageZip -Force

Copy-Item $installCmdSource -Destination (Join-Path $payloadRoot "install.cmd") -Force
Copy-Item $installPs1Source -Destination (Join-Path $payloadRoot "install.ps1") -Force

$escapedPayload = $payloadRoot.Replace("\", "\\")
$escapedSetup = $setupExe.Replace("\", "\\")

$sed = @"
[Version]
Class=IEXPRESS
SEDVersion=3
[Options]
PackagePurpose=InstallApp
ShowInstallProgramWindow=0
HideExtractAnimation=1
UseLongFileName=1
InsideCompressed=0
CAB_FixedSize=0
CAB_ResvCodeSigning=0
RebootMode=N
InstallPrompt=
DisplayLicense=
FinishMessage=Установка CassetteDatasetCapture завершена.
TargetName=$escapedSetup
FriendlyName=CassetteDatasetCapture Setup
AppLaunched=install.cmd
PostInstallCmd=<None>
AdminQuietInstCmd=install.cmd
UserQuietInstCmd=install.cmd
SourceFiles=SourceFiles
[Strings]
FILE0=install.cmd
FILE1=install.ps1
FILE2=package.zip
[SourceFiles]
SourceFiles0=$escapedPayload
[SourceFiles0]
%FILE0%=
%FILE1%=
%FILE2%=
"@

Set-Content -Path $sedFile -Value $sed -Encoding ASCII

& iexpress /N $sedFile | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "IExpress packaging failed."
}

Write-Output "Portable app: $portableRoot"
Write-Output "Setup.exe: $setupExe"
Write-Output ".NET runtime bundle versions:"
Write-Output "- Microsoft.NETCore.App: $runtimeVersion"
Write-Output "- Microsoft.WindowsDesktop.App: $desktopVersion"
Write-Output "- host/fxr: $fxrVersion"
