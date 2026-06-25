# SQLite database backup script for API Pilot (Windows)
# Usage: .\scripts\backup_db.ps1 [backup_dir]

param([string]$BackupDir = ".\backups")

$DbPath = ".\data\api_pilot.db"
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$BackupFile = Join-Path $BackupDir "api_pilot_${Timestamp}.db"

if (-not (Test-Path $DbPath)) {
    Write-Error "Database not found at $DbPath"
    exit 1
}

New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null
Copy-Item $DbPath $BackupFile

Write-Host "Backup created: $BackupFile"

# Cleanup old backups (keep last 7)
Get-ChildItem "$BackupDir\api_pilot_*.db" | Sort-Object LastWriteTime -Descending | Select-Object -Skip 7 | Remove-Item -Force
