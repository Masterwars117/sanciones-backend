param(
    [string]$Container = "oracle_xe",
    [string]$User = "",
    [string]$Password = "",
    [string]$Service = "XEPDB1",
    [string]$OutputDir = "",
    [string[]]$Tables = @(
        "CAT_GENERO",
        "TIPOSANCION",
        "CAT_MONEDAS",
        "CAT_TFALTA",
        "CAT_TIPODOCTO",
        "DEPENDENCIAS",
        "INHABILIFEDERAL",
        "INHABILITADOS"
    )
)

$ErrorActionPreference = "Stop"

if (-not $OutputDir) {
    $OutputDir = Join-Path $PSScriptRoot "csv"
}

function Get-OracleContainerEnvValue {
    param([string]$Name)

    $envLines = docker inspect $Container --format "{{range .Config.Env}}{{println .}}{{end}}"
    foreach ($line in $envLines) {
        if ($line.StartsWith("$Name=")) {
            return $line.Substring($Name.Length + 1)
        }
    }

    return $null
}

if (-not $User) {
    $User = Get-OracleContainerEnvValue "APP_USER"
}

if (-not $Password) {
    $Password = Get-OracleContainerEnvValue "APP_USER_PASSWORD"
}

if (-not $User -or -not $Password) {
    throw "No pude detectar APP_USER/APP_USER_PASSWORD del contenedor. Pasa -User y -Password manualmente."
}

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

foreach ($table in $Tables) {
    $sql = @"
SET MARKUP CSV ON DELIMITER , QUOTE ON
SET FEEDBACK OFF
SET PAGESIZE 50000
SET LINESIZE 32767
SET LONG 1000000
SET LONGCHUNKSIZE 32767
SET TRIMSPOOL ON
ALTER SESSION SET NLS_DATE_FORMAT = 'YYYY-MM-DD';
ALTER SESSION SET NLS_TIMESTAMP_FORMAT = 'YYYY-MM-DD HH24:MI:SS';
SELECT * FROM "$table";
EXIT
"@

    Write-Host "Exportando $table..."
    $output = $sql | docker exec -i $Container sqlplus -s "$User/$Password@localhost/$Service"

    if ($LASTEXITCODE -ne 0) {
        throw "Fallo sqlplus al exportar $table."
    }

    $lines = @($output -split "`r?`n")
    while ($lines.Count -gt 0 -and [string]::IsNullOrWhiteSpace($lines[0])) {
        $lines = @($lines | Select-Object -Skip 1)
    }
    while ($lines.Count -gt 0 -and [string]::IsNullOrWhiteSpace($lines[$lines.Count - 1])) {
        $lines = @($lines | Select-Object -First ($lines.Count - 1))
    }

    $cleanOutput = $lines -join [Environment]::NewLine
    if ($cleanOutput -match "(ORA-\d+|SP2-\d+)") {
        throw "Oracle regreso un error al exportar $table.`n$cleanOutput"
    }

    $target = Join-Path $OutputDir "$table.csv"
    Set-Content -Path $target -Value $cleanOutput -Encoding UTF8
    Write-Host "OK: $target"
}

Write-Host "Exportacion terminada."
