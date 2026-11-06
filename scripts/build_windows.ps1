$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$OriginalPath = $env:PATH
$PythonRoot = Split-Path -Parent (Get-Command python).Source
Push-Location $ProjectRoot
try {
    # Prevent unrelated tools on the development PATH from supplying Qt DLLs.
    $env:PATH = "$PythonRoot;$PythonRoot\Scripts;$env:SystemRoot\System32;$env:SystemRoot"
    python -m unittest discover -s tests -v
    if ($LASTEXITCODE -ne 0) { throw 'Tests failed' }
    python scripts/build_icon.py
    if ($LASTEXITCODE -ne 0) { throw 'Icon build failed' }
    python -m PyInstaller installer/hypersolve.spec --noconfirm --clean --distpath dist --workpath build
    if ($LASTEXITCODE -ne 0) { throw 'Executable build failed' }
    python scripts/package_companion.py
    if ($LASTEXITCODE -ne 0) { throw 'Companion packaging failed' }
    python scripts/smoke_packaged.py
    if ($LASTEXITCODE -ne 0) { throw 'Packaged manager smoke failed' }
    $CompilerCandidates = @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
    )
    $Compiler = $CompilerCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
    if (-not $Compiler) { throw 'Install Inno Setup 6, then rerun this build.' }
    & $Compiler installer/installer.iss
    if ($LASTEXITCODE -ne 0) { throw 'Installer build failed' }
    python scripts/release_manifest.py
    if ($LASTEXITCODE -ne 0) { throw 'Manifest generation failed' }
} finally {
    $env:PATH = $OriginalPath
    Pop-Location
}
