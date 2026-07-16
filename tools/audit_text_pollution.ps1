param(
    [string]$Root = "."
)

$ErrorActionPreference = "Stop"
$rootPath = (Resolve-Path -LiteralPath $Root).Path
$utf8 = [System.Text.UTF8Encoding]::new($false, $true)
$extensions = @(".py", ".md", ".json", ".yml", ".yaml", ".toml", ".bat", ".ps1", ".spec")
$excludedPrefixes = @("Version/", ".work/", ".venv/", "build/", "dist/", ".pytest-agent-domain/")
$toolArtifacts = @(
    ([char]0xE200 + "cite"),
    ("assistant" + " to="),
    ("recipient=" + "functions.")
)
$issues = [System.Collections.Generic.List[string]]::new()

$gitUtf8 = [System.Text.UTF8Encoding]::new($false)
$previousConsoleEncoding = [Console]::OutputEncoding
$previousOutputEncoding = $OutputEncoding
try {
    # Windows PowerShell otherwise decodes Git's UTF-8 path output with the
    # active OEM code page. Chinese file names then become literal question
    # marks and are no longer valid paths for ReadAllBytes.
    [Console]::OutputEncoding = $gitUtf8
    $OutputEncoding = $gitUtf8
    $relativePaths = & git -c core.quotepath=false -C $rootPath `
        ls-files --cached --others --exclude-standard
    if ($LASTEXITCODE -ne 0) {
        throw "git ls-files failed"
    }
}
finally {
    [Console]::OutputEncoding = $previousConsoleEncoding
    $OutputEncoding = $previousOutputEncoding
}

foreach ($relativePath in $relativePaths) {
    $normalized = $relativePath.Replace("\", "/")
    if ($excludedPrefixes.Where({ $normalized.StartsWith($_) }).Count -gt 0) {
        continue
    }
    if (-not $extensions.Contains([System.IO.Path]::GetExtension($normalized))) {
        continue
    }

    $fullPath = Join-Path $rootPath $relativePath
    try {
        $text = $utf8.GetString([System.IO.File]::ReadAllBytes($fullPath))
    }
    catch [System.Text.DecoderFallbackException] {
        $issues.Add("INVALID_UTF8 $normalized")
        continue
    }

    $lineNumber = 0
    foreach ($line in ($text -split "`r?`n")) {
        $lineNumber += 1
        if ($line -match "^(<<<<<<<|=======|>>>>>>>)") {
            $issues.Add("MERGE_MARKER ${normalized}:$lineNumber")
        }
        foreach ($artifact in $toolArtifacts) {
            if ($line.Contains($artifact)) {
                $issues.Add("TOOL_ARTIFACT ${normalized}:$lineNumber")
            }
        }
        foreach ($character in $line.ToCharArray()) {
            $codePoint = [int]$character
            if ($codePoint -ge 0xE000 -and $codePoint -le 0xF8FF) {
                $issues.Add(
                    "PRIVATE_USE ${normalized}:$lineNumber U+$('{0:X4}' -f $codePoint)"
                )
                break
            }
        }
    }
}

if ($issues.Count -gt 0) {
    $issues | Sort-Object -Unique | ForEach-Object { Write-Output $_ }
    Write-Output "TEXT_POLLUTION_SCAN=FAIL issues=$($issues.Count)"
    exit 1
}

Write-Output "TEXT_POLLUTION_SCAN=PASS files=$($relativePaths.Count)"
