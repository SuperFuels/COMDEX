$ErrorActionPreference = "Stop"
$PackageDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $PackageDir
$Python = Join-Path $PackageDir ".pilot-setup-venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    py -3 -m venv ".pilot-setup-venv"
    & $Python -m pip install --disable-pip-version-check -r "requirements.txt"
}
& $Python -m backend.modules.aion_business.runtime.sovereign_setup_service
