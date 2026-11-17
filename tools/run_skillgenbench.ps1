# 保留原CLI；实际启动交给共用WSL入口。
$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot 'run_evaluation_wsl.ps1') `
    -Dataset 'skillgenbench' -Agent 'openhands-skillgenbench' -EvaluationArguments $args
exit $LASTEXITCODE
