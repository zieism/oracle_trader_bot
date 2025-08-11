# Oracle Trader Bot - Health Check Script (PowerShell)
# Tests all important endpoints

$SERVER_URL = "http://194.127.178.181"
Write-Host "🔍 Testing Oracle Trader Bot endpoints on $SERVER_URL" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Gray

function Test-Endpoint {
    param(
        [string]$Name,
        [string]$Url
    )
    
    Write-Host "$Name..." -ForegroundColor Yellow
    try {
        $response = Invoke-WebRequest -Uri $Url -Method GET -TimeoutSec 10 -UseBasicParsing
        Write-Host "  ✅ Status: $($response.StatusCode) | Content Length: $($response.Content.Length) bytes" -ForegroundColor Green
        return $true
    }
    catch {
        $statusCode = $_.Exception.Response.StatusCode.value__
        if ($statusCode) {
            Write-Host "  ⚠️  Status: $statusCode | Error: $($_.Exception.Message)" -ForegroundColor Yellow
        } else {
            Write-Host "  ❌ Connection failed: $($_.Exception.Message)" -ForegroundColor Red
        }
        return $false
    }
    Write-Host ""
}

# Test endpoints
$results = @()
$results += Test-Endpoint "1. Main page" "$SERVER_URL/"
$results += Test-Endpoint "2. Dashboard" "$SERVER_URL/dashboard/"
$results += Test-Endpoint "3. Health endpoint" "$SERVER_URL/health"
$results += Test-Endpoint "4. API health" "$SERVER_URL/api/health"
$results += Test-Endpoint "5. Dashboard test endpoint" "$SERVER_URL/dashboard/api/test-data"
$results += Test-Endpoint "6. Dashboard data endpoint" "$SERVER_URL/dashboard/api/dashboard-data"

Write-Host "================================================" -ForegroundColor Gray
$successCount = ($results | Where-Object { $_ -eq $true }).Count
$totalCount = $results.Count

if ($successCount -eq $totalCount) {
    Write-Host "✅ All endpoints are healthy! ($successCount/$totalCount)" -ForegroundColor Green
} elseif ($successCount -gt 0) {
    Write-Host "⚠️  Partially healthy: $successCount/$totalCount endpoints working" -ForegroundColor Yellow
} else {
    Write-Host "❌ Server appears to be down: $successCount/$totalCount endpoints working" -ForegroundColor Red
}

Write-Host ""
Write-Host "Expected responses:" -ForegroundColor Cyan
Write-Host "- Status 200: Endpoint working correctly" -ForegroundColor Gray
Write-Host "- Status 302: Redirect (normal for main page)" -ForegroundColor Gray
Write-Host "- Status 404: Endpoint not found" -ForegroundColor Gray
Write-Host "- Status 500: Server error" -ForegroundColor Gray
