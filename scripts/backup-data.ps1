# ============================================================
# Open Notebook 数据备份脚本
# 备份内容：
#   1. SurrealDB 数据库（rocksdb 目录）
#   2. 上传文件 (data/uploads)
#   3. .env 配置（脱敏）
# 用法：
#   powershell -File E:\notebook\scripts\backup-data.ps1            # 备份到默认目录
#   powershell -File E:\notebook\scripts\backup-data.ps1 -Keep 7    # 只保留最近 7 份
# ============================================================

param(
    [int]$Keep = 5,                                  # 保留最近 N 份备份
    [string]$BackupRoot = 'E:\notebook\backups'      # 备份根目录
)

$ErrorActionPreference = 'Stop'
$timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$backupDir = Join-Path $BackupRoot "backup_$timestamp"

function Write-Log {
    param([string]$Message, [string]$Level = 'INFO')
    $ts = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    Write-Host "[$ts] [$Level] $Message"
}

Write-Log "========== 开始备份 =========="
Write-Log "备份目录: $backupDir"

# 1. SurrealDB 数据库
# 注意：跳过 LOCK 文件（SurrealDB 运行时持有它，无法复制且不需要备份）
$dbSrc = 'E:\notebook\open-notebook\surreal_data\db'
if (Test-Path $dbSrc) {
    $dbDst = Join-Path $backupDir 'surrealdb'
    New-Item -ItemType Directory -Path $dbDst -Force | Out-Null
    Get-ChildItem $dbSrc -Force | Where-Object { $_.Name -ne 'LOCK' } | ForEach-Object {
        Copy-Item $_.FullName -Destination $dbDst -Recurse -Force
    }
    $size = (Get-ChildItem $dbDst -Recurse -File | Measure-Object Length -Sum).Sum
    Write-Log "✅ SurrealDB 已备份 ($([math]::Round($size/1MB,2)) MB)"
} else {
    Write-Log "⚠️ 未找到 SurrealDB 目录: $dbSrc" 'WARN'
}

# 2. 上传文件
$uploadSrc = 'E:\notebook\open-notebook\data\uploads'
if (Test-Path $uploadSrc) {
    $uploadDst = Join-Path $backupDir 'uploads'
    New-Item -ItemType Directory -Path $uploadDst -Force | Out-Null
    Copy-Item -Path "$uploadSrc\*" -Destination $uploadDst -Recurse -Force
    $size = (Get-ChildItem $uploadDst -Recurse -File | Measure-Object Length -Sum).Sum
    Write-Log "✅ 上传文件已备份 ($([math]::Round($size/1MB,2)) MB)"
} else {
    Write-Log "⚠️ 未找到上传目录: $uploadSrc" 'WARN'
}

# 3. .env 配置（脱敏：只保留键名，值打码）
$envSrc = 'E:\notebook\open-notebook\.env'
if (Test-Path $envSrc) {
    $envDst = Join-Path $backupDir '.env.backup'
    Get-Content $envSrc | ForEach-Object {
        if ($_ -match '^([A-Z_]+)=(.*)$') {
            $key = $matches[1]
            $val = $matches[2]
            if ($val.Length -gt 4) {
                "$key=$($val.Substring(0,4))****(已脱敏，真实值见原 .env)"
            } else {
                "$key=****(已脱敏)"
            }
        } else {
            $_
        }
    } | Set-Content $envDst -Encoding UTF8
    Write-Log "✅ .env 配置已备份（脱敏）"
}

Write-Log "========== 备份完成 ✅ =========="
Write-Log "备份位置: $backupDir"

# 清理旧备份
$oldBackups = Get-ChildItem $BackupRoot -Directory -Filter 'backup_*' -ErrorAction SilentlyContinue |
    Sort-Object Name -Descending | Select-Object -Skip $Keep
foreach ($old in $oldBackups) {
    Remove-Item $old.FullName -Recurse -Force
    Write-Log "🧹 已清理旧备份: $($old.Name)"
}
