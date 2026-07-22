param(
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$runtimeOutput = Join-Path $repoRoot "build\editor-runtime"
$specOutput = Join-Path $repoRoot "build\editor-runtime-spec"

Push-Location $repoRoot
try {
    & $Python -m pip install -e ".[editor,packaging]"
    if (Test-Path $runtimeOutput) { Remove-Item -LiteralPath $runtimeOutput -Recurse -Force }
    New-Item -ItemType Directory -Path $runtimeOutput | Out-Null
    & $Python -m PyInstaller --noconfirm --clean --onefile --name text-sandbox-editor-api --paths (Join-Path $repoRoot "src") --distpath $runtimeOutput --workpath $specOutput --specpath $specOutput (Join-Path $repoRoot "scripts\editor_api_entry.py")
    Push-Location (Join-Path $repoRoot "editor")
    try {
        npm install
        npm run build
    } finally {
        Pop-Location
    }
    npx tauri build --config (Join-Path $repoRoot "src-tauri\tauri.conf.json")
} finally {
    Pop-Location
}
