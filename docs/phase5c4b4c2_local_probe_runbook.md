# Phase 5C-4B.4C-2A local ThetaData entitlement probe

## Purpose and authorization boundary

This Windows-only manual procedure checks schema/access for exactly nine approved,
minimal, read-only ThetaData API v3 queries. It is not a downloader, backtest,
trading client, runtime integration, mapping decision, plan change, or cutover.
Only don Manuel may run the authenticated command in the separate 4C-2B phase.

The probe uses Python's standard library and ThetaData's documented HTTPS API v3
API-key authentication (`Authorization: Bearer`), with fixed GET endpoints. No
project or third-party package is required. Use Python 3.10 or later; check it with:

```powershell
python --version
```

Do **not** install or change repository requirements. If Python is absent, install
it from python.org, then reopen PowerShell.

## Set, run, and remove the credential

From a fresh PowerShell in the repository root, enter the key interactively so it
does not appear in the command itself or get committed:

```powershell
$secure = Read-Host 'ThetaData API key' -AsSecureString
$ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
try { $env:THETADATA_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr) }
finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) }
Remove-Variable secure, ptr
.\tools\run_thetadata_entitlement_probe.ps1 -Date 2026-01-15
Remove-Item Env:\THETADATA_API_KEY
```

Replace the sample date with one explicitly selected for the authorized check.
One date only is accepted. Never put the key in this repository, a script, shell
history, screenshot, chat, issue, or result file. The wrapper writes only
`phase5c4b4c2_probe_result.json` and fails if that file is absent.

For a network-free validation (which reads no credential), run Python directly:

```powershell
python .\tools\thetadata_entitlement_probe.py --dry-run --date 2026-01-15
```

## Expected sanitized output

The JSON contains only metadata, per-probe outcomes/schema field names/counts, and
the safety ledger. It never contains headers, URLs, account identifiers, raw
responses, market rows, or market values. Empty data, timeouts, and authentication
failures do not mean an entitlement denial. Options results do not decide the SPX
index result, and first-order Greeks do not decide EOD Gamma.

Send back **only** `phase5c4b4c2_probe_result.json`. Do not send console captures,
the environment, credential, request/response traces, provider downloads, browser
storage, configuration files, or any raw market data.

## Failures and accidental exposure

`CREDENTIAL_UNAVAILABLE` means no request was made. For another failure, stop; do
not broaden dates, follow pagination, retry manually in a loop, alter endpoints,
or paste diagnostics containing request details. Preserve only the sanitized JSON
if generated and report its status classes.

If a key may have been exposed, immediately remove it from the environment, revoke
or rotate it through ThetaData's official account controls, close the shell, and
remove it from shell history/logs where possible. Do not commit a cleanup alone:
contact the repository administrator to purge history and treat the old key as
compromised.
