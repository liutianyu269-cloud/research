$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$dotenvPath = Join-Path $projectRoot '.env'

git -C $projectRoot check-ignore --quiet -- .env
if ($LASTEXITCODE -ne 0) {
    throw '.env 未被 Git 忽略，已停止输入密钥。'
}
$existing = if (Test-Path -LiteralPath $dotenvPath) {
    [System.IO.File]::ReadAllText($dotenvPath)
} else {
    ''
}
if ([regex]::IsMatch($existing, '(?m)^\s*THINGO_API_KEY\s*=')) {
    Write-Host '本机 .env 已包含 THINGO_API_KEY，未覆盖已有设置。'
    return
}

Write-Host '只输入 Thingo 平台 API Key，不输入账户登录密码。'
Write-Host '密钥会保存在当前 research 项目被 Git 忽略的 .env 文件中，不显示在屏幕或聊天里。'
$secureKey = Read-Host 'Thingo API Key（输入隐藏）' -AsSecureString
$keyPointer = [IntPtr]::Zero
try {
    $keyPointer = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)
    $plainKey = [System.Runtime.InteropServices.Marshal]::PtrToStringBSTR($keyPointer).Trim()
    if ([string]::IsNullOrWhiteSpace($plainKey) -or $plainKey.Contains("`n") -or $plainKey.Contains("`r")) {
        throw 'API Key 不能为空或包含换行。'
    }
    $escapedKey = $plainKey.Replace('\', '\\').Replace('"', '\"')
    $separator = if ($existing.Length -gt 0 -and -not $existing.EndsWith("`n")) { "`n" } else { '' }
    $entry = $separator + 'THINGO_API_KEY="' + $escapedKey + '"' + "`n"
    [System.IO.File]::AppendAllText($dotenvPath, $entry, [System.Text.UTF8Encoding]::new($false))
    Write-Host '已保存。没有调用模型，可以关闭此窗口并回到聊天。'
} finally {
    if ($keyPointer -ne [IntPtr]::Zero) {
        [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($keyPointer)
    }
    $plainKey = $null
    $escapedKey = $null
    $entry = $null
    $secureKey.Dispose()
}
