$ErrorActionPreference = "Stop"
$PackageDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$InstallRoot = Join-Path $env:ProgramFiles "Tessaris\AION"
$BrainRoot = Join-Path $env:ProgramData "Tessaris\Pilot Brain"
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Run this developer installer as Administrator."
}
New-Item -ItemType Directory -Force -Path $InstallRoot, $BrainRoot | Out-Null
Copy-Item -Recurse -Force (Join-Path $PackageDir "payload\*") $InstallRoot
& py -3 -m venv (Join-Path $InstallRoot "runtime")
$Python = Join-Path $InstallRoot "runtime\Scripts\python.exe"
& $Python -m pip install --disable-pip-version-check -r (Join-Path $InstallRoot "requirements-windows.txt")
[Environment]::SetEnvironmentVariable("TESSARIS_PILOT_BRAIN_ROOT", $BrainRoot, "Machine")
& $Python (Join-Path $InstallRoot "backend\modules\aion_business\runtime\sovereign_windows_service.py") --startup auto install
& $Python (Join-Path $InstallRoot "backend\modules\aion_business\runtime\sovereign_windows_service.py") start
Write-Host "Pilot AION Brain service installed. Run Set-Up-Pilot.ps1 to create the customer-owned brain."
