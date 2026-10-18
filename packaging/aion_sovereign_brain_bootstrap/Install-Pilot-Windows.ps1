$ErrorActionPreference = "Stop"
$PackageDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$InstallRoot = Join-Path $env:ProgramFiles "Tessaris\AION"
$BrainRoot = Join-Path $env:ProgramData "Tessaris\Pilot Brain"
$NodeStateRoot = Join-Path $env:ProgramData "Tessaris Node"
$ServiceName = "TessarisPilotBrain"
$ServiceIdentity = "NT SERVICE\$ServiceName"
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Run this developer installer as Administrator."
}
New-Item -ItemType Directory -Force -Path $InstallRoot, $BrainRoot, $NodeStateRoot | Out-Null
Copy-Item -Recurse -Force (Join-Path $PackageDir "payload\*") $InstallRoot
& py -3 -m venv (Join-Path $InstallRoot "runtime")
$Python = Join-Path $InstallRoot "runtime\Scripts\python.exe"
& $Python -m pip install --disable-pip-version-check -r (Join-Path $InstallRoot "requirements-windows.txt")
[Environment]::SetEnvironmentVariable("TESSARIS_PILOT_BRAIN_ROOT", $BrainRoot, "Machine")
[Environment]::SetEnvironmentVariable("TESSARIS_NODE_STATE_ROOT", $NodeStateRoot, "Machine")
& $Python (Join-Path $InstallRoot "backend\modules\aion_business\runtime\sovereign_windows_service.py") --startup auto install
& sc.exe config $ServiceName obj= $ServiceIdentity password= ""
if ($LASTEXITCODE -ne 0) { throw "Could not assign the dedicated Tessaris service identity." }
& icacls.exe $InstallRoot /inheritance:r /grant:r "SYSTEM:(OI)(CI)F" "BUILTIN\Administrators:(OI)(CI)F" "${ServiceIdentity}:(OI)(CI)RX"
if ($LASTEXITCODE -ne 0) { throw "Could not protect the Tessaris application directory." }
& icacls.exe $BrainRoot /inheritance:r /grant:r "SYSTEM:(OI)(CI)F" "BUILTIN\Administrators:(OI)(CI)F" "${ServiceIdentity}:(OI)(CI)M"
if ($LASTEXITCODE -ne 0) { throw "Could not grant the service access to its brain directory." }
& icacls.exe $NodeStateRoot /inheritance:r /grant:r "SYSTEM:(OI)(CI)F" "BUILTIN\Administrators:(OI)(CI)F" "${ServiceIdentity}:(OI)(CI)M"
if ($LASTEXITCODE -ne 0) { throw "Could not grant the service access to its Node-state directory." }
& $Python (Join-Path $InstallRoot "backend\modules\aion_business\runtime\sovereign_windows_service.py") start
Write-Host "Pilot AION Brain service installed. Run Set-Up-Pilot.ps1 to create the customer-owned brain."
