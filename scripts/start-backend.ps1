# Start DESCEND backend (from REBUILD OF SYSTEM)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..\Backend
$env:FLASK_PORT = if ($env:FLASK_PORT) { $env:FLASK_PORT } else { "5000" }
python run.py
