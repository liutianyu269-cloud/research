# 从 Linux 本地目录启动，避免 Docker Desktop 操作使 /mnt/c 下的当前目录失效。
# 参数直接交给原 evaluation 入口，例如 --name first --plan 或 --name first --resume。
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
    --dataset "$linuxRoot/config/datasets/skillgenbench.toml" `
    --environment "$linuxRoot/config/environments/skillgenbench.toml" `
    --agent "$linuxRoot/config/agents/openhands-skillgenbench.toml" `
    --evaluation "$linuxRoot/config/evaluation/skillgenbench.toml" @args
exit $LASTEXITCODE
