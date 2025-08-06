#!/bin/bash

# Oracle Trader Bot - Update Script
# This script handles zero-downtime updates of the Oracle Trader Bot

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
BACKUP_BEFORE_UPDATE="true"
UPDATE_TIMEOUT=300

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

usage() {
    cat << EOF
Oracle Trader Bot - Update Script

Usage: $0 [OPTIONS]

OPTIONS:
    -b, --branch BRANCH     Git branch to update to (default: main)
    -t, --tag TAG           Git tag to update to (overrides branch)
    -s, --skip-backup       Skip backup before update
    -f, --force             Force update without confirmation
    -r, --rollback          Rollback to previous version
    -h, --help              Show this help message

EXAMPLES:
    $0                      # Update to latest main branch
    $0 -t v1.2.0           # Update to specific tag
    $0 -b develop          # Update to develop branch
    $0 --rollback          # Rollback to previous version

EOF
}

pre_update_checks() {
    log_info "Running pre-update checks..."
    
    # Check if we're in a git repository
    if [[ ! -d "$PROJECT_DIR/.git" ]]; then
        log_error "Not in a git repository. Cannot perform update."
        exit 1
    fi
    
    # Check if Docker services are running
    cd "$PROJECT_DIR"
    if ! docker-compose ps | grep -q "Up"; then
        log_error "Docker services are not running. Please start them first."
        exit 1
    fi
    
    # Check for uncommitted changes
    if [[ -n "$(git status --porcelain)" ]]; then
        log_warning "Uncommitted changes detected:"
        git status --short
        echo
        if [[ "$FORCE_UPDATE" != "true" ]]; then
            read -p "Continue with update? (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                log_info "Update cancelled by user"
                exit 0
            fi
        fi
    fi
    
    # Check available disk space
    local available_space=$(df "$PROJECT_DIR" | awk 'NR==2 {print $4}')
    if [[ $available_space -lt 1048576 ]]; then  # Less than 1GB
        log_warning "Low disk space: $(df -h "$PROJECT_DIR" | awk 'NR==2 {print $4}') available"
    fi
    
    log_success "Pre-update checks completed"
}

backup_before_update() {
    if [[ "$BACKUP_BEFORE_UPDATE" != "true" ]]; then
        log_info "Skipping backup before update"
        return 0
    fi
    
    log_info "Creating backup before update..."
    
    local backup_script="$SCRIPT_DIR/backup.sh"
    if [[ -f "$backup_script" ]]; then
        "$backup_script" -t full
        log_success "Backup completed before update"
    else
        log_warning "Backup script not found, skipping backup"
    fi
}

get_current_version() {
    cd "$PROJECT_DIR"
    local current_commit=$(git rev-parse HEAD)
    local current_branch=$(git rev-parse --abbrev-ref HEAD)
    local current_tag=$(git describe --tags --exact-match 2>/dev/null || echo "no-tag")
    
    echo "Current version: $current_branch@$current_commit ($current_tag)"
}

update_source_code() {
    local target="$1"
    
    log_info "Updating source code to $target..."
    
    cd "$PROJECT_DIR"
    
    # Fetch latest changes
    git fetch --all --tags
    
    # Save current state for potential rollback
    echo "$(git rev-parse HEAD)" > .last_version
    
    # Checkout target version
    if [[ "$target" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        # It's a tag
        git checkout "tags/$target"
    else
        # It's a branch
        git checkout "$target"
        git pull origin "$target"
    fi
    
    log_success "Source code updated to $target"
}

update_dependencies() {
    log_info "Updating dependencies..."
    
    cd "$PROJECT_DIR"
    
    # Check if requirements have changed
    if git diff HEAD~1 HEAD --name-only | grep -q "requirements"; then
        log_info "Requirements files changed, rebuilding Docker images..."
        docker-compose build --no-cache
    else
        log_info "No dependency changes detected"
    fi
}

perform_rolling_update() {
    log_info "Performing rolling update..."
    
    cd "$PROJECT_DIR"
    
    # Scale up new instances
    docker-compose up -d --scale oracle-trader=2 --no-recreate
    
    # Wait for new instances to be healthy
    log_info "Waiting for new instances to become healthy..."
    sleep 30
    
    # Check health of new instances
    local retries=10
    while [[ $retries -gt 0 ]]; do
        if curl -f -s -m 5 "http://localhost:8000/health" >/dev/null; then
            log_success "New instances are healthy"
            break
        fi
        
        retries=$((retries - 1))
        if [[ $retries -eq 0 ]]; then
            log_error "New instances failed to become healthy"
            return 1
        fi
        
        log_info "Waiting for instances to become healthy... ($retries retries left)"
        sleep 10
    done
    
    # Scale down old instances
    docker-compose up -d --scale oracle-trader=1
    
    # Remove old containers
    docker container prune -f
    
    log_success "Rolling update completed"
}

run_database_migrations() {
    log_info "Running database migrations..."
    
    cd "$PROJECT_DIR"
    
    # Run migrations in a temporary container
    docker-compose exec oracle-trader python -c "
import asyncio
from app.db.base import init_db

async def run_migrations():
    try:
        await init_db()
        print('Database migrations completed successfully')
    except Exception as e:
        print(f'Migration failed: {e}')
        raise

asyncio.run(run_migrations())
" || {
        log_error "Database migrations failed"
        return 1
    }
    
    log_success "Database migrations completed"
}

restart_services() {
    log_info "Restarting services..."
    
    cd "$PROJECT_DIR"
    
    # Restart services with health checks
    docker-compose restart
    
    # Wait for services to be ready
    local max_wait=120
    local elapsed=0
    
    while [[ $elapsed -lt $max_wait ]]; do
        if curl -f -s -m 5 "http://localhost:8000/health" >/dev/null; then
            log_success "Services restarted successfully"
            return 0
        fi
        
        sleep 5
        elapsed=$((elapsed + 5))
        log_info "Waiting for services to restart... (${elapsed}s/${max_wait}s)"
    done
    
    log_error "Services failed to restart within timeout"
    return 1
}

post_update_verification() {
    log_info "Running post-update verification..."
    
    # Run health checks
    local monitor_script="$SCRIPT_DIR/monitor.sh"
    if [[ -f "$monitor_script" ]]; then
        if "$monitor_script"; then
            log_success "Post-update health checks passed"
        else
            log_error "Post-update health checks failed"
            return 1
        fi
    else
        log_warning "Monitor script not found, skipping detailed health checks"
        
        # Basic health check
        if curl -f -s -m 10 "http://localhost:8000/health" >/dev/null; then
            log_success "Basic health check passed"
        else
            log_error "Basic health check failed"
            return 1
        fi
    fi
    
    # Check logs for errors
    local error_count=$(docker-compose logs --tail=50 oracle-trader | grep -c "ERROR\|CRITICAL" || echo "0")
    if [[ $error_count -gt 0 ]]; then
        log_warning "Found $error_count errors in recent logs"
        docker-compose logs --tail=20 oracle-trader | grep "ERROR\|CRITICAL" || true
    fi
}

rollback_update() {
    log_info "Rolling back to previous version..."
    
    cd "$PROJECT_DIR"
    
    if [[ ! -f ".last_version" ]]; then
        log_error "No previous version information found"
        exit 1
    fi
    
    local previous_commit=$(cat .last_version)
    
    # Checkout previous version
    git checkout "$previous_commit"
    
    # Restart services
    docker-compose restart
    
    # Wait for services to be ready
    sleep 30
    
    if curl -f -s -m 10 "http://localhost:8000/health" >/dev/null; then
        log_success "Rollback completed successfully"
        rm -f .last_version
    else
        log_error "Rollback failed - services not responding"
        exit 1
    fi
}

send_update_notification() {
    local status="$1"
    local version="$2"
    
    # Load environment for notification settings
    if [[ -f "$PROJECT_DIR/.env" ]]; then
        set -a
        source "$PROJECT_DIR/.env"
        set +a
    fi
    
    local message="Oracle Trader Bot update $status to version $version"
    
    # Email notification
    if [[ -n "${EMAIL_TO:-}" ]]; then
        echo "$message" | mail -s "Oracle Trader Bot Update $status" "$EMAIL_TO" 2>/dev/null || true
    fi
    
    # Slack notification
    if [[ -n "${SLACK_WEBHOOK_URL:-}" ]]; then
        local color="good"
        if [[ "$status" == "failed" ]]; then
            color="danger"
        fi
        
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"$message\",\"attachments\":[{\"color\":\"$color\",\"text\":\"Update $status\"}]}" \
            "$SLACK_WEBHOOK_URL" 2>/dev/null || true
    fi
}

# Default values
TARGET_BRANCH="main"
TARGET_TAG=""
FORCE_UPDATE="false"
ROLLBACK_MODE="false"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -b|--branch)
            TARGET_BRANCH="$2"
            shift 2
            ;;
        -t|--tag)
            TARGET_TAG="$2"
            shift 2
            ;;
        -s|--skip-backup)
            BACKUP_BEFORE_UPDATE="false"
            shift
            ;;
        -f|--force)
            FORCE_UPDATE="true"
            shift
            ;;
        -r|--rollback)
            ROLLBACK_MODE="true"
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

# Main execution
main() {
    echo "Oracle Trader Bot - Update Script"
    echo "================================="
    
    if [[ "$ROLLBACK_MODE" == "true" ]]; then
        rollback_update
        send_update_notification "rolled back" "previous"
        return 0
    fi
    
    local target="${TARGET_TAG:-$TARGET_BRANCH}"
    
    echo "Target version: $target"
    echo "Skip backup: $([ "$BACKUP_BEFORE_UPDATE" = "false" ] && echo "yes" || echo "no")"
    echo "Force update: $FORCE_UPDATE"
    echo "================================="
    echo
    
    get_current_version
    echo
    
    if [[ "$FORCE_UPDATE" != "true" ]]; then
        read -p "Proceed with update? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Update cancelled by user"
            exit 0
        fi
    fi
    
    # Update process
    if pre_update_checks && \
       backup_before_update && \
       update_source_code "$target" && \
       update_dependencies && \
       run_database_migrations && \
       restart_services && \
       post_update_verification; then
        
        log_success "Update completed successfully!"
        send_update_notification "completed" "$target"
        
        # Cleanup
        rm -f .last_version
        docker system prune -f
        
    else
        log_error "Update failed!"
        send_update_notification "failed" "$target"
        
        if [[ -f ".last_version" ]]; then
            log_info "You can rollback using: $0 --rollback"
        fi
        
        exit 1
    fi
}

# Trap errors
trap 'log_error "Update process interrupted"' ERR

# Run main function
main "$@"