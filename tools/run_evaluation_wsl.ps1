param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('skillgenbench', 'appworld')]
    [string]$Dataset,
    [Parameter(Mandatory = $true)]
    [ValidateSet('openhands-skillgenbench', 'openhands-appworld')]
    [string]$Agent,
    [string[]]$EvaluationArguments = @()
)

# 共享WSL启动流程；各数据集入口只选择配置并传递evaluation参数。
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$driveLetter = $projectRoot.Substring(0, 1).ToLowerInvariant()
$linuxRoot = '/mnt/' + $driveLetter + $projectRoot.Substring(2).Replace('\', '/')
$linuxParent = $linuxRoot.Substring(0, $linuxRoot.LastIndexOf('/'))
$pythonPath = $linuxParent + '/research-venv-wsl/bin/python'
$runnerCode = @'
import runpy
import sys
from pathlib import Path
from dotenv import load_dotenv

project = Path(sys.argv.pop(1))
load_dotenv(project / '.env', override=False)
runpy.run_module('evaluation', run_name='__main__')
'@

& wsl -d Ubuntu --cd /tmp -- env "PYTHONPATH=$linuxRoot" "TIKTOKEN_CACHE_DIR=$linuxRoot/logs/tiktoken-cache" `
    $pythonPath -X utf8 -u -c $runnerCode $linuxRoot `
    --dataset "$linuxRoot/config/datasets/$Dataset.toml" `
    --environment "$linuxRoot/config/environments/$Dataset.toml" `
    --agent "$linuxRoot/config/agents/$Agent.toml" `
    --evaluation "$linuxRoot/config/evaluation/$Dataset.toml" @EvaluationArguments
exit $LASTEXITCODE
