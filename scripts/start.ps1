$ErrorActionPreference = 'Stop'
$projectPath = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectPath
if (-not (Test-Path -LiteralPath '.venv/Scripts/python.exe')) { throw '请先按 README 安装 Python 依赖。' }
$apiProcess = Start-Process -FilePath (Join-Path $projectPath '.venv/Scripts/python.exe') -ArgumentList @('-m','uvicorn','services.api.main:app','--host','127.0.0.1','--port','8000') -WorkingDirectory $projectPath -WindowStyle Hidden -PassThru
try {
    Write-Host 'API: http://127.0.0.1:8000/docs'
    Set-Location -LiteralPath (Join-Path $projectPath 'apps/web')
    npm run dev
} finally {
    if (-not $apiProcess.HasExited) { Stop-Process -Id $apiProcess.Id }
}
