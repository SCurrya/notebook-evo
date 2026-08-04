$mergeFile = 'C:\Users\ZS\AppData\Roaming\io.github.clash-verge-rev.clash-verge-rev\profiles\Merge.yaml'
Write-Host "--- Length ---"
(Get-Item $mergeFile).Length
Write-Host "--- Content ---"
Get-Content $mergeFile
