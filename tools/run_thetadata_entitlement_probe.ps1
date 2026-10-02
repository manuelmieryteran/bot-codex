param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^\d{4}-\d{2}-\d{2}$')]
    [string]$Date
)

$ErrorActionPreference = 'Stop'
$OutputFile = Join-Path (Get-Location) 'phase5c4b4c2_probe_result.json'

if ([string]::IsNullOrWhiteSpace($env:THETADATA_API_KEY)) {
    throw 'CREDENTIAL_UNAVAILABLE'
}

if (Test-Path $OutputFile) { Remove-Item -LiteralPath $OutputFile -Force }
python (Join-Path $PSScriptRoot 'thetadata_entitlement_probe.py') --date $Date --output $OutputFile
if ($LASTEXITCODE -ne 0 -or -not (Test-Path $OutputFile)) {
    throw 'SANITIZED_RESULT_NOT_GENERATED'
}

# The JSON file is the sole result. The credential and response payloads are never printed.
