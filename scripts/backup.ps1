# Sauvegarde horodatee de la base sae_supervision.
# Garde les 7 derniers dumps, supprime les plus vieux.
#
# Prerequis : la variable d'environnement PGPASSWORD doit etre definie.
# Usage manuel : $env:PGPASSWORD="admin"; .\scripts\backup.ps1

$ErrorActionPreference = "Stop"

$PgDump   = "C:\Program Files\PostgreSQL\17\bin\pg_dump.exe"
$DbHost   = "127.0.0.1"
$DbPort   = "5432"
$DbName   = "sae_supervision"
$DbUser   = "sae_app"
$Retention = 7

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$BackupDir   = Join-Path $ProjectRoot "backups"
New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null

$Stamp   = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$OutFile = Join-Path $BackupDir "$DbName`_$Stamp.sql"

& $PgDump -h $DbHost -p $DbPort -U $DbUser -d $DbName -f $OutFile
if ($LASTEXITCODE -ne 0) {
    throw "pg_dump a echoue (code $LASTEXITCODE)"
}

Write-Host "Sauvegarde OK : $OutFile"

Get-ChildItem -Path $BackupDir -Filter "$DbName`_*.sql" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -Skip $Retention |
    Remove-Item -Force
