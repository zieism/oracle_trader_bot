#!/bin/bash

# Oracle Trader Bot - Backup Script
# This script creates comprehensive backups of the Oracle Trader Bot data

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
BACKUP_DIR="$PROJECT_DIR/backups"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# Load environment variables
if [[ -f "$PROJECT_DIR/.env" ]]; then
    set -a
    source "$PROJECT_DIR/.env"
    set +a
fi

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
Oracle Trader Bot - Backup Script

Usage: $0 [OPTIONS]

OPTIONS:
    -t, --type TYPE         Backup type: full, database, files, config (default: full)
    -r, --retention DAYS    Retention period in days (default: 30)
    -c, --compress          Compress backup files (default: enabled)
    -e, --encrypt           Encrypt backup files (requires BACKUP_ENCRYPTION_KEY)
    -s, --remote            Upload to remote storage (requires AWS configuration)
    -h, --help              Show this help message

BACKUP TYPES:
    full        Complete backup including database, files, and configuration
    database    Database backup only (PostgreSQL and Redis)
    files       Application data and logs
    config      Configuration files and environment

EXAMPLES:
    $0                                    # Full backup with default settings
    $0 -t database                        # Database backup only
    $0 -t full -r 60 -e -s               # Full encrypted backup with 60-day retention and remote upload

EOF
}

create_backup_dir() {
    local backup_name="oracle_trader_backup_${DATE}"
    local backup_path="$BACKUP_DIR/$backup_name"
    
    mkdir -p "$backup_path"
    echo "$backup_path"
}

backup_database() {
    local backup_path="$1"
    local db_backup_dir="$backup_path/database"
    
    log_info "Backing up PostgreSQL database..."
    mkdir -p "$db_backup_dir"
    
    # PostgreSQL backup
    docker-compose exec -T postgres pg_dump \
        -U "${POSTGRES_USER:-trader}" \
        -d "${POSTGRES_DB:-oracle_trader}" \
        --no-password \
        --verbose \
        --format=custom \
        --compress=9 \
        > "$db_backup_dir/postgres_backup.dump"
    
    # Also create a plain SQL backup for easier restoration
    docker-compose exec -T postgres pg_dump \
        -U "${POSTGRES_USER:-trader}" \
        -d "${POSTGRES_DB:-oracle_trader}" \
        --no-password \
        --verbose \
        --format=plain \
        > "$db_backup_dir/postgres_backup.sql"
    
    log_success "PostgreSQL backup completed"
    
    # Redis backup
    log_info "Backing up Redis data..."
    docker-compose exec -T redis redis-cli \
        --rdb /data/redis_backup_${DATE}.rdb \
        BGSAVE
    
    # Wait for Redis backup to complete
    sleep 5
    
    # Copy Redis backup
    docker cp $(docker-compose ps -q redis):/data/redis_backup_${DATE}.rdb "$db_backup_dir/"
    
    log_success "Redis backup completed"
}

backup_files() {
    local backup_path="$1"
    local files_backup_dir="$backup_path/files"
    
    log_info "Backing up application files..."
    mkdir -p "$files_backup_dir"
    
    # Backup application data
    if docker volume ls | grep -q oracle_trader_app_data; then
        docker run --rm \
            -v oracle_trader_app_data:/data \
            -v "$files_backup_dir":/backup \
            alpine:latest \
            tar czf /backup/app_data.tar.gz -C /data .
        
        log_success "Application data backup completed"
    fi
    
    # Backup logs
    if [[ -d "$PROJECT_DIR/logs" ]]; then
        tar czf "$files_backup_dir/logs.tar.gz" -C "$PROJECT_DIR" logs/
        log_success "Logs backup completed"
    fi
    
    # Backup Grafana data
    if docker volume ls | grep -q oracle_trader_grafana_data; then
        docker run --rm \
            -v oracle_trader_grafana_data:/data \
            -v "$files_backup_dir":/backup \
            alpine:latest \
            tar czf /backup/grafana_data.tar.gz -C /data .
        
        log_success "Grafana data backup completed"
    fi
    
    # Backup Prometheus data
    if docker volume ls | grep -q oracle_trader_prometheus_data; then
        docker run --rm \
            -v oracle_trader_prometheus_data:/data \
            -v "$files_backup_dir":/backup \
            alpine:latest \
            tar czf /backup/prometheus_data.tar.gz -C /data .
        
        log_success "Prometheus data backup completed"
    fi
}

backup_config() {
    local backup_path="$1"
    local config_backup_dir="$backup_path/config"
    
    log_info "Backing up configuration files..."
    mkdir -p "$config_backup_dir"
    
    # Backup environment file (without sensitive data)
    if [[ -f "$PROJECT_DIR/.env" ]]; then
        # Create sanitized version of .env file
        grep -v -E "(PASSWORD|SECRET|KEY|TOKEN)" "$PROJECT_DIR/.env" > "$config_backup_dir/env_template.txt" || true
        log_success "Environment template backup completed"
    fi
    
    # Backup Docker compose files
    cp "$PROJECT_DIR"/docker-compose*.yml "$config_backup_dir/" 2>/dev/null || true
    
    # Backup Nginx configuration
    if [[ -d "$PROJECT_DIR/nginx" ]]; then
        tar czf "$config_backup_dir/nginx_config.tar.gz" -C "$PROJECT_DIR" nginx/
        log_success "Nginx configuration backup completed"
    fi
    
    # Backup monitoring configuration
    if [[ -d "$PROJECT_DIR/monitoring" ]]; then
        tar czf "$config_backup_dir/monitoring_config.tar.gz" -C "$PROJECT_DIR" monitoring/
        log_success "Monitoring configuration backup completed"
    fi
    
    # Backup deployment scripts
    if [[ -d "$SCRIPT_DIR" ]]; then
        tar czf "$config_backup_dir/deployment_scripts.tar.gz" -C "$(dirname "$SCRIPT_DIR")" scripts/
        log_success "Deployment scripts backup completed"
    fi
}

compress_backup() {
    local backup_path="$1"
    local backup_name=$(basename "$backup_path")
    local compressed_file="$BACKUP_DIR/${backup_name}.tar.gz"
    
    log_info "Compressing backup..."
    tar czf "$compressed_file" -C "$BACKUP_DIR" "$backup_name"
    
    # Remove uncompressed directory
    rm -rf "$backup_path"
    
    log_success "Backup compressed: $compressed_file"
    echo "$compressed_file"
}

encrypt_backup() {
    local backup_file="$1"
    local encrypted_file="${backup_file}.enc"
    
    if [[ -z "${BACKUP_ENCRYPTION_KEY:-}" ]]; then
        log_error "BACKUP_ENCRYPTION_KEY not set. Cannot encrypt backup."
        return 1
    fi
    
    log_info "Encrypting backup..."
    openssl enc -aes-256-cbc -salt -pbkdf2 -iter 100000 \
        -in "$backup_file" \
        -out "$encrypted_file" \
        -pass pass:"$BACKUP_ENCRYPTION_KEY"
    
    # Remove unencrypted file
    rm "$backup_file"
    
    log_success "Backup encrypted: $encrypted_file"
    echo "$encrypted_file"
}

upload_to_remote() {
    local backup_file="$1"
    
    if [[ -z "${AWS_ACCESS_KEY_ID:-}" || -z "${AWS_SECRET_ACCESS_KEY:-}" || -z "${AWS_S3_BUCKET:-}" ]]; then
        log_warning "AWS credentials not configured. Skipping remote upload."
        return 0
    fi
    
    log_info "Uploading backup to remote storage..."
    
    # Install AWS CLI if not present
    if ! command -v aws &> /dev/null; then
        log_info "Installing AWS CLI..."
        curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
        unzip awscliv2.zip
        sudo ./aws/install
        rm -rf aws awscliv2.zip
    fi
    
    # Configure AWS CLI
    aws configure set aws_access_key_id "$AWS_ACCESS_KEY_ID"
    aws configure set aws_secret_access_key "$AWS_SECRET_ACCESS_KEY"
    aws configure set default.region "${AWS_REGION:-us-east-1}"
    
    # Upload backup
    local s3_key="oracle-trader-backups/$(basename "$backup_file")"
    aws s3 cp "$backup_file" "s3://$AWS_S3_BUCKET/$s3_key"
    
    log_success "Backup uploaded to S3: s3://$AWS_S3_BUCKET/$s3_key"
}

cleanup_old_backups() {
    local retention_days="$1"
    
    log_info "Cleaning up backups older than $retention_days days..."
    
    # Local cleanup
    find "$BACKUP_DIR" -name "oracle_trader_backup_*" -type f -mtime +$retention_days -delete
    
    # Remote cleanup (if configured)
    if [[ -n "${AWS_S3_BUCKET:-}" ]]; then
        local cutoff_date=$(date -d "$retention_days days ago" +%Y-%m-%d)
        aws s3 ls "s3://$AWS_S3_BUCKET/oracle-trader-backups/" --recursive | \
        awk '$1 < "'$cutoff_date'" {print $4}' | \
        while read -r key; do
            aws s3 rm "s3://$AWS_S3_BUCKET/$key"
        done
    fi
    
    log_success "Old backups cleaned up"
}

verify_backup() {
    local backup_file="$1"
    
    log_info "Verifying backup integrity..."
    
    if [[ "$backup_file" == *.tar.gz ]]; then
        if tar tzf "$backup_file" >/dev/null 2>&1; then
            log_success "Backup integrity verified"
        else
            log_error "Backup verification failed"
            return 1
        fi
    elif [[ "$backup_file" == *.enc ]]; then
        log_info "Encrypted backup - skipping integrity check"
    fi
}

generate_backup_report() {
    local backup_file="$1"
    local backup_size=$(du -h "$backup_file" | cut -f1)
    local backup_name=$(basename "$backup_file")
    
    cat << EOF > "$BACKUP_DIR/backup_report_${DATE}.txt"
Oracle Trader Bot Backup Report
==============================
Backup Name: $backup_name
Backup Date: $(date)
Backup Size: $backup_size
Backup Type: $BACKUP_TYPE
Compression: $COMPRESS_BACKUP
Encryption: $ENCRYPT_BACKUP
Remote Upload: $REMOTE_UPLOAD

Backup Contents:
$(tar tzf "$backup_file" 2>/dev/null | head -20)

System Information:
Docker Version: $(docker --version)
Docker Compose Version: $(docker-compose --version)
Disk Usage: $(df -h "$BACKUP_DIR")

EOF

    log_success "Backup report generated: $BACKUP_DIR/backup_report_${DATE}.txt"
}

# Default values
BACKUP_TYPE="full"
COMPRESS_BACKUP="true"
ENCRYPT_BACKUP="false"
REMOTE_UPLOAD="false"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--type)
            BACKUP_TYPE="$2"
            shift 2
            ;;
        -r|--retention)
            RETENTION_DAYS="$2"
            shift 2
            ;;
        -c|--compress)
            COMPRESS_BACKUP="true"
            shift
            ;;
        -e|--encrypt)
            ENCRYPT_BACKUP="true"
            shift
            ;;
        -s|--remote)
            REMOTE_UPLOAD="true"
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

# Validate backup type
case $BACKUP_TYPE in
    full|database|files|config)
        ;;
    *)
        log_error "Invalid backup type: $BACKUP_TYPE"
        usage
        exit 1
        ;;
esac

# Main execution
main() {
    echo "Oracle Trader Bot - Backup Script"
    echo "=================================="
    echo "Backup Type: $BACKUP_TYPE"
    echo "Retention: $RETENTION_DAYS days"
    echo "Compression: $COMPRESS_BACKUP"
    echo "Encryption: $ENCRYPT_BACKUP"
    echo "Remote Upload: $REMOTE_UPLOAD"
    echo "=================================="
    echo
    
    # Ensure Docker services are running
    cd "$PROJECT_DIR"
    if ! docker-compose ps | grep -q "Up"; then
        log_error "Docker services are not running. Please start them first."
        exit 1
    fi
    
    # Create backup directory
    mkdir -p "$BACKUP_DIR"
    
    # Create backup
    local backup_path=$(create_backup_dir)
    
    case $BACKUP_TYPE in
        full)
            backup_database "$backup_path"
            backup_files "$backup_path"
            backup_config "$backup_path"
            ;;
        database)
            backup_database "$backup_path"
            ;;
        files)
            backup_files "$backup_path"
            ;;
        config)
            backup_config "$backup_path"
            ;;
    esac
    
    # Compress backup
    local final_backup="$backup_path"
    if [[ "$COMPRESS_BACKUP" == "true" ]]; then
        final_backup=$(compress_backup "$backup_path")
    fi
    
    # Encrypt backup
    if [[ "$ENCRYPT_BACKUP" == "true" ]]; then
        final_backup=$(encrypt_backup "$final_backup")
    fi
    
    # Verify backup
    verify_backup "$final_backup"
    
    # Generate report
    generate_backup_report "$final_backup"
    
    # Upload to remote storage
    if [[ "$REMOTE_UPLOAD" == "true" ]]; then
        upload_to_remote "$final_backup"
    fi
    
    # Cleanup old backups
    cleanup_old_backups "$RETENTION_DAYS"
    
    log_success "Backup completed successfully: $final_backup"
}

# Trap errors
trap 'log_error "Backup failed. Check the logs above for details."' ERR

# Change to project directory
cd "$PROJECT_DIR"

# Run main function
main "$@"