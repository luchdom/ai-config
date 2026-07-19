[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$RequestPath
)

$ErrorActionPreference = 'Stop'
$engine = Join-Path -Path $PSScriptRoot -ChildPath 'cli.py'

if (-not (Test-Path -LiteralPath $engine -PathType Leaf)) {
    [Console]::Error.WriteLine('{"status":"failed","error":"Installed supervisor engine is missing"}')
    exit 2
}

& python $engine --request $RequestPath
exit $LASTEXITCODE
