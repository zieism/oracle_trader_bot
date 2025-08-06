#!/bin/bash

# Oracle Trader Bot - Monitoring Script
# This script monitors the health and performance of Oracle Trader Bot

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ALERT_EMAIL=""
SLACK_WEBHOOK=""
LOG_FILE="$PROJECT_DIR/logs/monitor.log"

# Thresholds
CPU_THRESHOLD=80
MEMORY_THRESHOLD=80
DISK_THRESHOLD=85
RESPONSE_TIME_THRESHOLD=5

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

usage() {
    cat << EOF
Oracle Trader Bot - Monitoring Script

Usage: $0 [OPTIONS]

OPTIONS:
    -c, --continuous        Run in continuous monitoring mode
    -i, --interval SECONDS  Monitoring interval in seconds (default: 60)
    -a, --alert-email EMAIL Email address for alerts
    -s, --slack-webhook URL Slack webhook URL for alerts
    -v, --verbose           Verbose output
    -h, --help              Show this help message

EXAMPLES:
    $0                                    # Single health check
    $0 -c -i 30                          # Continuous monitoring every 30 seconds
    $0 -a admin@example.com -s webhook   # Health check with alerts

EOF
}

send_alert() {
    local subject="$1"
    local message="$2"
    local severity="$3"
    
    # Email alert
    if [[ -n "$ALERT_EMAIL" ]]; then
        echo "$message" | mail -s "$subject" "$ALERT_EMAIL" 2>/dev/null || true
    fi
    
    # Slack alert
    if [[ -n "$SLACK_WEBHOOK" ]]; then
        local color="good"
        case $severity in
            "error") color="danger" ;;
            "warning") color="warning" ;;
        esac
        
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"$subject\",\"attachments\":[{\"color\":\"$color\",\"text\":\"$message\"}]}" \
            "$SLACK_WEBHOOK" 2>/dev/null || true
    fi
}

check_docker_services() {
    log_info "Checking Docker services..."
    
    cd "$PROJECT_DIR"
    local services_down=()
    
    # Check each service
    for service in oracle-trader postgres redis nginx prometheus grafana; do
        if ! docker-compose ps | grep -q "$service.*Up"; then
            services_down+=("$service")
        fi
    done
    
    if [[ ${#services_down[@]} -eq 0 ]]; then
        log_success "All Docker services are running"
        return 0
    else
        local message="Services down: ${services_down[*]}"
        log_error "$message"
        send_alert "Oracle Trader Bot - Services Down" "$message" "error"
        return 1
    fi
}

check_service_health() {
    log_info "Checking service health endpoints..."
    
    local failed_checks=()
    
    # Check main application health
    if ! curl -f -s -m 10 "http://localhost:8000/health" >/dev/null; then
        failed_checks+=("oracle-trader")
    fi
    
    # Check database connectivity
    if ! docker-compose exec -T postgres pg_isready -U "${POSTGRES_USER:-trader}" >/dev/null 2>&1; then
        failed_checks+=("postgres")
    fi
    
    # Check Redis
    if ! docker-compose exec -T redis redis-cli ping >/dev/null 2>&1; then
        failed_checks+=("redis")
    fi
    
    # Check Nginx
    if ! curl -f -s -m 5 "http://localhost:80" >/dev/null; then
        failed_checks+=("nginx")
    fi
    
    if [[ ${#failed_checks[@]} -eq 0 ]]; then
        log_success "All health checks passed"
        return 0
    else
        local message="Failed health checks: ${failed_checks[*]}"
        log_error "$message"
        send_alert "Oracle Trader Bot - Health Check Failed" "$message" "error"
        return 1
    fi
}

check_resource_usage() {
    log_info "Checking resource usage..."
    
    local alerts=()
    
    # Check CPU usage
    local cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | awk -F'%' '{print $1}')
    if (( $(echo "$cpu_usage > $CPU_THRESHOLD" | bc -l) )); then
        alerts+=("High CPU usage: ${cpu_usage}%")
    fi
    
    # Check memory usage
    local memory_usage=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100.0}')
    if [[ $memory_usage -gt $MEMORY_THRESHOLD ]]; then
        alerts+=("High memory usage: ${memory_usage}%")
    fi
    
    # Check disk usage
    local disk_usage=$(df "$PROJECT_DIR" | tail -1 | awk '{print $5}' | sed 's/%//')
    if [[ $disk_usage -gt $DISK_THRESHOLD ]]; then
        alerts+=("High disk usage: ${disk_usage}%")
    fi
    
    # Check Docker container resource usage
    local container_stats=$(docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemPerc}}" | tail -n +2)
    while IFS=$'\t' read -r container cpu mem; do
        cpu_num=$(echo "$cpu" | sed 's/%//')
        mem_num=$(echo "$mem" | sed 's/%//')
        
        if (( $(echo "$cpu_num > 90" | bc -l) )); then
            alerts+=("High CPU in container $container: $cpu")
        fi
        
        if (( $(echo "$mem_num > 90" | bc -l) )); then
            alerts+=("High memory in container $container: $mem")
        fi
    done <<< "$container_stats"
    
    if [[ ${#alerts[@]} -eq 0 ]]; then
        log_success "Resource usage is within normal limits"
        log_info "CPU: ${cpu_usage}%, Memory: ${memory_usage}%, Disk: ${disk_usage}%"
        return 0
    else
        local message=$(printf '%s\n' "${alerts[@]}")
        log_warning "Resource usage alerts:"
        echo "$message"
        send_alert "Oracle Trader Bot - High Resource Usage" "$message" "warning"
        return 1
    fi
}

check_application_metrics() {
    log_info "Checking application metrics..."
    
    # Check application response time
    local start_time=$(date +%s.%N)
    if curl -f -s -m "$RESPONSE_TIME_THRESHOLD" "http://localhost:8000/health" >/dev/null; then
        local end_time=$(date +%s.%N)
        local response_time=$(echo "$end_time - $start_time" | bc)
        
        if (( $(echo "$response_time > $RESPONSE_TIME_THRESHOLD" | bc -l) )); then
            local message="Slow response time: ${response_time}s"
            log_warning "$message"
            send_alert "Oracle Trader Bot - Slow Response" "$message" "warning"
        else
            log_success "Application response time: ${response_time}s"
        fi
    else
        log_error "Application not responding"
        return 1
    fi
    
    # Check for application errors in logs
    local error_count=$(docker-compose logs --tail=100 oracle-trader | grep -c "ERROR\|CRITICAL" || echo "0")
    if [[ $error_count -gt 10 ]]; then
        local message="High error rate in logs: $error_count errors in last 100 log entries"
        log_warning "$message"
        send_alert "Oracle Trader Bot - High Error Rate" "$message" "warning"
    fi
    
    # Check database connections
    local db_connections=$(docker-compose exec -T postgres psql -U "${POSTGRES_USER:-trader}" -d "${POSTGRES_DB:-oracle_trader}" -t -c "SELECT count(*) FROM pg_stat_activity;" 2>/dev/null | xargs || echo "0")
    if [[ $db_connections -gt 50 ]]; then
        local message="High database connection count: $db_connections"
        log_warning "$message"
        send_alert "Oracle Trader Bot - High DB Connections" "$message" "warning"
    fi
}

check_ssl_certificates() {
    log_info "Checking SSL certificate expiration..."
    
    if [[ -f "/etc/letsencrypt/live/${DOMAIN:-localhost}/cert.pem" ]]; then
        local cert_file="/etc/letsencrypt/live/${DOMAIN}/cert.pem"
        local expiry_date=$(openssl x509 -in "$cert_file" -noout -enddate | cut -d= -f2)
        local expiry_timestamp=$(date -d "$expiry_date" +%s)
        local current_timestamp=$(date +%s)
        local days_until_expiry=$(( (expiry_timestamp - current_timestamp) / 86400 ))
        
        if [[ $days_until_expiry -le 30 ]]; then
            local message="SSL certificate expires in $days_until_expiry days"
            log_warning "$message"
            send_alert "Oracle Trader Bot - SSL Certificate Expiring" "$message" "warning"
        else
            log_success "SSL certificate valid for $days_until_expiry days"
        fi
    else
        log_info "SSL certificate file not found (might be using HTTP)"
    fi
}

check_backup_status() {
    log_info "Checking backup status..."
    
    local backup_dir="$PROJECT_DIR/backups"
    if [[ -d "$backup_dir" ]]; then
        local latest_backup=$(find "$backup_dir" -name "oracle_trader_backup_*" -type f -printf '%T@ %p\n' | sort -n | tail -1 | cut -d' ' -f2-)
        
        if [[ -n "$latest_backup" ]]; then
            local backup_age=$(( ($(date +%s) - $(stat -c %Y "$latest_backup")) / 86400 ))
            
            if [[ $backup_age -gt 2 ]]; then
                local message="Last backup is $backup_age days old: $(basename "$latest_backup")"
                log_warning "$message"
                send_alert "Oracle Trader Bot - Backup Outdated" "$message" "warning"
            else
                log_success "Recent backup found: $(basename "$latest_backup") ($backup_age days old)"
            fi
        else
            log_warning "No backups found"
            send_alert "Oracle Trader Bot - No Backups Found" "No backup files found in $backup_dir" "warning"
        fi
    else
        log_warning "Backup directory not found"
    fi
}

generate_status_report() {
    local timestamp=$(date)
    local report_file="$PROJECT_DIR/logs/status_report_$(date +%Y%m%d_%H%M%S).txt"
    
    cat << EOF > "$report_file"
Oracle Trader Bot - Status Report
=================================
Generated: $timestamp

System Information:
- Hostname: $(hostname)
- Uptime: $(uptime)
- Load: $(cat /proc/loadavg)
- Memory: $(free -h | grep Mem)
- Disk: $(df -h "$PROJECT_DIR")

Docker Services:
$(docker-compose ps)

Container Resource Usage:
$(docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}")

Recent Application Logs:
$(docker-compose logs --tail=50 oracle-trader | tail -20)

Database Status:
$(docker-compose exec -T postgres psql -U "${POSTGRES_USER:-trader}" -d "${POSTGRES_DB:-oracle_trader}" -c "SELECT version();" 2>/dev/null || echo "Database not accessible")

Redis Status:
$(docker-compose exec -T redis redis-cli info replication 2>/dev/null || echo "Redis not accessible")

EOF

    log_success "Status report generated: $report_file"
}

# Default values
CONTINUOUS_MODE="false"
INTERVAL=60
VERBOSE="false"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -c|--continuous)
            CONTINUOUS_MODE="true"
            shift
            ;;
        -i|--interval)
            INTERVAL="$2"
            shift 2
            ;;
        -a|--alert-email)
            ALERT_EMAIL="$2"
            shift 2
            ;;
        -s|--slack-webhook)
            SLACK_WEBHOOK="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE="true"
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Load environment variables
if [[ -f "$PROJECT_DIR/.env" ]]; then
    set -a
    source "$PROJECT_DIR/.env"
    set +a
fi

# Ensure log directory exists
mkdir -p "$(dirname "$LOG_FILE")"

# Single monitoring check
run_health_check() {
    local overall_status=0
    
    echo "Oracle Trader Bot - Health Check"
    echo "================================"
    echo "Timestamp: $(date)"
    echo
    
    check_docker_services || overall_status=1
    check_service_health || overall_status=1
    check_resource_usage || overall_status=1
    check_application_metrics || overall_status=1
    check_ssl_certificates || overall_status=1
    check_backup_status || overall_status=1
    
    if [[ "$VERBOSE" == "true" ]]; then
        generate_status_report
    fi
    
    echo
    if [[ $overall_status -eq 0 ]]; then
        log_success "Overall health check: PASSED"
    else
        log_error "Overall health check: FAILED"
        send_alert "Oracle Trader Bot - Health Check Failed" "One or more health checks failed. Please review the monitoring logs." "error"
    fi
    
    return $overall_status
}

# Main execution
main() {
    cd "$PROJECT_DIR"
    
    if [[ "$CONTINUOUS_MODE" == "true" ]]; then
        log_info "Starting continuous monitoring (interval: ${INTERVAL}s)"
        
        while true; do
            run_health_check
            echo "Next check in ${INTERVAL} seconds..."
            echo "================================"
            sleep "$INTERVAL"
        done
    else
        run_health_check
    fi
}

# Trap signals for graceful shutdown in continuous mode
trap 'log_info "Monitoring stopped"; exit 0' SIGINT SIGTERM

# Run main function
main "$@"