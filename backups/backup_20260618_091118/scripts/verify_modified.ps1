$mergeFile = 'C:\Users\ZS\AppData\Roaming\io.github.clash-verge-rev.clash-verge-rev\profiles\Merge.yaml'

Write-Host "=== 关键字匹配（trycloudflare|ts.net|tailscale|cloudflare）==="
Get-Content $mergeFile | Select-String -Pattern 'trycloudflare|ts\.net|tailscale|cloudflare' | ForEach-Object { $_.Line }

Write-Host ""
Write-Host "=== 完整内容（80 行内全显示）==="
Get-Content $mergeFile

Write-Host ""
Write-Host "=== 文件大小 ==="
Write-Host "$((Get-Item $mergeFile).Length) 字节"
