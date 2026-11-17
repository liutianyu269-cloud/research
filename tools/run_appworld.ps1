$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot 'run_evaluation_wsl.ps1') `
    -Dataset 'appworld' -Agent 'openhands-appworld' -EvaluationArguments $args
exit $LASTEXITCODE
