param(
    [string]$Root = "."
)

$ErrorActionPreference = "Stop"
$exitCode = 2
$rootPath = (Resolve-Path -LiteralPath $Root).Path
$trustedRepositoryRoot = (
    Resolve-Path -LiteralPath (Join-Path -Path $PSScriptRoot -ChildPath "..")
).Path
$trustedAuditScript = Join-Path -Path $PSScriptRoot -ChildPath "quality_audit.py"
$venvPython = Join-Path `
    -Path $trustedRepositoryRoot `
    -ChildPath ".venv\Scripts\python.exe"
if (Test-Path -LiteralPath $venvPython -PathType Leaf) {
    $pythonPath = (Resolve-Path -LiteralPath $venvPython).Path
}
else {
    $pythonCommand = Get-Command `
        -Name python `
        -CommandType Application `
        -ErrorAction Stop | Select-Object -First 1
    $pythonPath = $pythonCommand.Source
}

Push-Location -LiteralPath $trustedRepositoryRoot
try {
    & $pythonPath -I $trustedAuditScript --root $rootPath --text-only
    if ($null -eq $LASTEXITCODE) {
        throw "quality audit did not provide a native process exit code"
    }
    $exitCode = [int]$LASTEXITCODE
}
finally {
    Pop-Location
}
exit $exitCode
