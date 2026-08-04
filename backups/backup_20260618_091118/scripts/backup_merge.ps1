$mergeFile = 'C:\Users\ZS\AppData\Roaming\io.github.clash-verge-rev.clash-verge-rev\profiles\Merge.yaml'
$backup = "$mergeFile.bak2"
Copy-Item -LiteralPath $mergeFile -Destination $backup -Force
if (Test-Path $backup) {
  Write-Host "已备份: $backup"
  Write-Host "大小: $((Get-Item $backup).Length) 字节"
} else {
  Write-Host "备份失败"
  exit 1
}
