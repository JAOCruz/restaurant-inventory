# Strict error handling (replicates 'set -euo pipefail')
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

# Resolve paths correctly on Windows
$PROJECT_ROOT = (Get-Item $PSScriptRoot).Parent.FullName
$DATA_DIR = Join-Path $PROJECT_ROOT "data"
$DB_FILE = Join-Path $DATA_DIR "inventory.db"

Write-Host "Creating data directory at $DATA_DIR..."
# -Force acts like 'mkdir -p' (skips if folder exists)
New-Item -ItemType Directory -Force -Path $DATA_DIR | Out-Null

Write-Host "Initializing SQLite database at $DB_FILE..."
# Safest way to stream files into an executable in PowerShell
Get-Content (Join-Path $PROJECT_ROOT "sql\schema.sql") -Raw | sqlite3 $DB_FILE

Write-Host "Seeding database..."
Get-Content (Join-Path $PROJECT_ROOT "sql\seed.sql") -Raw | sqlite3 $DB_FILE

Write-Host "Database initialized successfully."
