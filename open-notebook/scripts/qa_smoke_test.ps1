# QA 冒烟测试 - Agent 自验报告生成（开发环境无密码模式）
$ErrorActionPreference = "Continue"
$base = "http://127.0.0.1:5055"
$report = @()

function Test-Item($name, $method, $path, $body = $null) {
    try {
        $params = @{ Uri = "$base$path"; Method = $method; UseBasicParsing = $true; TimeoutSec = 30 }
        if ($body) { $params.Body = $body; $params.ContentType = "application/json" }
        $r = Invoke-WebRequest @params
        $report += "$name -> PASS ($($r.StatusCode))"
        return $true
    } catch {
        $code = if ($_.Exception.Response) { $_.Exception.Response.StatusCode.value__ } else { "ERR" }
        $report += "$name -> FAIL ($code): $($_.Exception.Message)"
        return $false
    }
}

$report += "=== Agent 自验报告 ==="
$report += "时间: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
$report += ""

# 1. 核心端点
Test-Item "笔记本列表" "GET" "/api/notebooks"
Test-Item "健康检查" "GET" "/health"

# 2. 混合检索
Test-Item "混合检索" "POST" "/api/search/hybrid" '{"query":"AI Agent 技术","limit":5}'

# 3. 自适应检索
Test-Item "自适应检索" "POST" "/api/search/adaptive" '{"query":"什么是MCP协议","limit":5}'

# 4. RAG 评估
Test-Item "评估报告列表" "GET" "/api/eval/reports"
Test-Item "单题评估" "POST" "/api/eval/run-single" '{"question":"什么是MCP？","reference":"MCP由Anthropic提出","top_k":3}'

# 5. Agent 系统
Test-Item "Agent列表" "GET" "/api/agents"
Test-Item "Agent统计" "GET" "/api/agents/stats"

# 6. 知识图谱
Test-Item "知识图谱" "GET" "/api/knowledge-graph"
Test-Item "图谱问答" "POST" "/api/knowledge-graph/ask" '{"question":"什么是AI Agent"}'

# 7. 其他核心
Test-Item "模型列表" "GET" "/api/models"
Test-Item "凭证列表" "GET" "/api/credentials"
Test-Item "设置" "GET" "/api/settings"

$report += ""
$passes = ($report | Select-String "PASS").Count
$fails = ($report | Select-String "FAIL").Count
$report += "=== 汇总: $passes 通过 / $fails 失败 ==="
$report | Out-File -FilePath "qa_report.txt" -Encoding utf8
$report
