# Oracle Trader Bot - Automated Deployment Script
# This script will connect to the VPS and deploy the latest changes

$server = "194.127.178.181"
$username = "root" 
$password = "Z9X07C##z9z9z9"

Write-Host "🚀 Oracle Trader Bot Deployment Script" -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Gray
Write-Host ""

# Create secure string for password
$securePassword = ConvertTo-SecureString $password -AsPlainText -Force
$credential = New-Object System.Management.Automation.PSCredential ($username, $securePassword)

Write-Host "📡 Attempting to connect to server $server..." -ForegroundColor Yellow

try {
    # Since direct SSH automation is challenging in PowerShell, provide manual instructions
    Write-Host ""
    Write-Host "🔧 Manual Deployment Instructions:" -ForegroundColor Green
    Write-Host "===================================" -ForegroundColor Gray
    Write-Host ""
    Write-Host "1. Open a new terminal/command prompt" -ForegroundColor White
    Write-Host "2. Run: ssh $username@$server" -ForegroundColor Cyan
    Write-Host "3. Enter password: $password" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "4. Once connected, run these commands:" -ForegroundColor White
    Write-Host ""
    
    $commands = @(
        "# Check current location",
        "pwd",
        "ls -la",
        "",
        "# Navigate to project (try both locations)", 
        "cd /opt/oracle_trader_bot 2>/dev/null || cd /root/oracle_trader_bot",
        "",
        "# Update from GitHub",
        "git pull origin main",
        "",
        "# Check current containers",
        "docker ps -a",
        "",
        "# Stop current containers", 
        "docker-compose -f oracle_trader_bot/deployment/docker-compose.yml down",
        "",
        "# Rebuild and start services",
        "docker-compose -f oracle_trader_bot/deployment/docker-compose.yml up -d --build",
        "",
        "# Check logs",
        "docker-compose -f oracle_trader_bot/deployment/docker-compose.yml logs oracle-trader | tail -50",
        "",
        "# Test endpoints",
        "curl http://localhost/health",
        "curl http://localhost/dashboard/api/test-data"
    )
    
    foreach ($command in $commands) {
        if ($command.StartsWith("#")) {
            Write-Host $command -ForegroundColor Green
        } elseif ($command -eq "") {
            Write-Host ""
        } else {
            Write-Host $command -ForegroundColor Cyan
        }
    }
    
    Write-Host ""
    Write-Host "🔍 After deployment, test these URLs:" -ForegroundColor Yellow
    Write-Host "http://194.127.178.181/health" -ForegroundColor Cyan
    Write-Host "http://194.127.178.181/dashboard/" -ForegroundColor Cyan
    Write-Host "http://194.127.178.181/dashboard/api/test-data" -ForegroundColor Cyan
    
} catch {
    Write-Host "❌ Error: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "✅ Deployment instructions ready!" -ForegroundColor Green
