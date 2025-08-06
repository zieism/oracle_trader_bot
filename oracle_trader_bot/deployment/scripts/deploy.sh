#!/bin/bash

# Oracle Trader Bot - Production Deployment Script
# This script automates the deployment of Oracle Trader Bot on a VPS

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
COMPOSE_FILE="docker-compose.yml"
PROD_COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE=".env"

# Default values
DOMAIN=""
EMAIL=""
STAGING="false"
SKIP_FIREWALL="false"
SKIP_SSL="false"
DRY_RUN="false"

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
Oracle Trader Bot - Production Deployment Script

Usage: $0 [OPTIONS]

OPTIONS:
    -d, --domain DOMAIN         Domain name for the application (required)
    -e, --email EMAIL          Email for Let's Encrypt SSL certificates (required)
    -s, --staging              Use Let's Encrypt staging environment (default: false)
    -f, --skip-firewall        Skip firewall configuration (default: false)
    -c, --skip-ssl             Skip SSL certificate generation (default: false)
    -n, --dry-run              Show what would be done without executing (default: false)
    -h, --help                 Show this help message

EXAMPLES:
    $0 -d example.com -e admin@example.com
    $0 -d example.com -e admin@example.com --staging --skip-firewall
    $0 --dry-run -d example.com -e admin@example.com

EOF
}

check_requirements() {
    log_info "Checking system requirements..."
    
    # Check if running as root
    if [[ $EUID -eq 0 ]]; then
        log_error "This script should not be run as root. Please run as a regular user with sudo privileges."
        exit 1
    fi
    
    # Check for required commands
    local required_commands=("docker" "docker-compose" "curl" "openssl")
    for cmd in "${required_commands[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            log_error "Required command '$cmd' not found. Please install it first."
            exit 1
        fi
    done
    
    # Check Docker daemon
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running. Please start Docker and try again."
        exit 1
    fi
    
    # Check sudo privileges
    if ! sudo -n true 2>/dev/null; then
        log_error "This script requires sudo privileges. Please ensure you can run sudo commands."
        exit 1
    fi
    
    log_success "System requirements check passed"
}

install_docker() {
    log_info "Installing Docker and Docker Compose..."
    
    if command -v docker &> /dev/null; then
        log_info "Docker is already installed"
        return 0
    fi
    
    # Update package index
    sudo apt-get update
    
    # Install prerequisites
    sudo apt-get install -y \
        apt-transport-https \
        ca-certificates \
        curl \
        gnupg \
        lsb-release
    
    # Add Docker's official GPG key
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    
    # Set up stable repository
    echo \
        "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
        $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    # Install Docker Engine
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    
    # Add current user to docker group
    sudo usermod -aG docker $USER
    
    log_success "Docker installed successfully"
    log_warning "Please log out and log back in for Docker group changes to take effect"
}

configure_firewall() {
    if [[ "$SKIP_FIREWALL" == "true" ]]; then
        log_info "Skipping firewall configuration"
        return 0
    fi
    
    log_info "Configuring UFW firewall..."
    
    # Install UFW if not present
    if ! command -v ufw &> /dev/null; then
        sudo apt-get update
        sudo apt-get install -y ufw
    fi
    
    # Reset UFW to defaults
    sudo ufw --force reset
    
    # Set default policies
    sudo ufw default deny incoming
    sudo ufw default allow outgoing
    
    # Allow SSH (be careful not to lock yourself out)
    sudo ufw allow OpenSSH
    
    # Allow HTTP and HTTPS
    sudo ufw allow 80/tcp
    sudo ufw allow 443/tcp
    
    # Allow specific application ports if needed
    # sudo ufw allow 8000/tcp  # Only if you need direct access
    
    # Enable UFW
    sudo ufw --force enable
    
    log_success "Firewall configured successfully"
}

setup_environment() {
    log_info "Setting up environment configuration..."
    
    cd "$PROJECT_DIR"
    
    # Copy environment template if .env doesn't exist
    if [[ ! -f "$ENV_FILE" ]]; then
        if [[ -f "${ENV_FILE}.example" ]]; then
            cp "${ENV_FILE}.example" "$ENV_FILE"
            log_info "Created $ENV_FILE from template"
        else
            log_error "Environment template ${ENV_FILE}.example not found"
            exit 1
        fi
    fi
    
    # Generate secure secrets
    log_info "Generating secure secrets..."
    
    local secret_key=$(openssl rand -base64 32)
    local api_secret_key=$(openssl rand -base64 32)
    local jwt_secret_key=$(openssl rand -base64 32)
    local grafana_secret_key=$(openssl rand -base64 32)
    local postgres_password=$(openssl rand -base64 24)
    local redis_password=$(openssl rand -base64 24)
    local grafana_password=$(openssl rand -base64 16)
    
    # Update .env file
    sed -i "s/DOMAIN=.*/DOMAIN=$DOMAIN/" "$ENV_FILE"
    sed -i "s/SECRET_KEY=.*/SECRET_KEY=$secret_key/" "$ENV_FILE"
    sed -i "s/API_SECRET_KEY=.*/API_SECRET_KEY=$api_secret_key/" "$ENV_FILE"
    sed -i "s/JWT_SECRET_KEY=.*/JWT_SECRET_KEY=$jwt_secret_key/" "$ENV_FILE"
    sed -i "s/GRAFANA_SECRET_KEY=.*/GRAFANA_SECRET_KEY=$grafana_secret_key/" "$ENV_FILE"
    sed -i "s/POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=$postgres_password/" "$ENV_FILE"
    sed -i "s/REDIS_PASSWORD=.*/REDIS_PASSWORD=$redis_password/" "$ENV_FILE"
    sed -i "s/GRAFANA_ADMIN_PASSWORD=.*/GRAFANA_ADMIN_PASSWORD=$grafana_password/" "$ENV_FILE"
    sed -i "s/LETSENCRYPT_EMAIL=.*/LETSENCRYPT_EMAIL=$EMAIL/" "$ENV_FILE"
    
    if [[ "$STAGING" == "true" ]]; then
        sed -i "s/LETSENCRYPT_STAGING=.*/LETSENCRYPT_STAGING=true/" "$ENV_FILE"
    fi
    
    # Set secure permissions
    chmod 600 "$ENV_FILE"
    
    log_success "Environment configuration completed"
    log_warning "Generated passwords have been saved to $ENV_FILE"
    log_warning "Please backup this file securely and update with your actual API keys"
}

generate_ssl_dhparam() {
    log_info "Generating DH parameters for enhanced SSL security..."
    
    local ssl_dir="$PROJECT_DIR/nginx/ssl-config"
    mkdir -p "$ssl_dir"
    
    if [[ ! -f "$ssl_dir/dhparam.pem" ]]; then
        openssl dhparam -out "$ssl_dir/dhparam.pem" 2048
        log_success "DH parameters generated"
    else
        log_info "DH parameters already exist"
    fi
}

setup_ssl_certificates() {
    if [[ "$SKIP_SSL" == "true" ]]; then
        log_info "Skipping SSL certificate setup"
        return 0
    fi
    
    log_info "Setting up SSL certificates with Let's Encrypt..."
    
    cd "$PROJECT_DIR"
    
    # Update nginx configuration with domain
    sed -i "s/\${DOMAIN}/$DOMAIN/g" nginx/nginx.conf
    
    # Create initial certificate
    docker-compose run --rm certbot certonly \
        --webroot \
        --webroot-path=/var/www/certbot \
        --email "$EMAIL" \
        --agree-tos \
        --no-eff-email \
        $(if [[ "$STAGING" == "true" ]]; then echo "--staging"; fi) \
        -d "$DOMAIN" \
        -d "www.$DOMAIN"
    
    log_success "SSL certificates generated"
}

deploy_application() {
    log_info "Deploying Oracle Trader Bot..."
    
    cd "$PROJECT_DIR"
    
    # Choose compose file based on environment
    local compose_cmd="docker-compose"
    if [[ -f "$PROD_COMPOSE_FILE" ]]; then
        compose_cmd="docker-compose -f $COMPOSE_FILE -f $PROD_COMPOSE_FILE"
    fi
    
    # Pull latest images
    $compose_cmd pull
    
    # Build application
    $compose_cmd build --no-cache
    
    # Start services
    $compose_cmd up -d
    
    # Wait for services to be healthy
    log_info "Waiting for services to become healthy..."
    sleep 30
    
    # Check service health
    for service in oracle-trader postgres redis; do
        if docker-compose ps | grep -q "$service.*healthy\|Up"; then
            log_success "$service is running"
        else
            log_error "$service failed to start properly"
            docker-compose logs "$service"
            exit 1
        fi
    done
    
    log_success "Application deployed successfully"
}

setup_monitoring() {
    log_info "Setting up monitoring and alerts..."
    
    # Ensure monitoring services are running
    docker-compose up -d prometheus grafana
    
    # Wait for Grafana to be ready
    sleep 15
    
    # Check if Grafana is accessible
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 | grep -q "200\|302"; then
        log_success "Grafana is accessible"
    else
        log_warning "Grafana may not be ready yet"
    fi
    
    log_info "Monitoring setup completed"
}

setup_backup() {
    log_info "Setting up automated backups..."
    
    # Create backup directories
    mkdir -p "$PROJECT_DIR/backups"
    
    # Install backup script to cron
    local backup_script="$SCRIPT_DIR/backup.sh"
    if [[ -f "$backup_script" ]]; then
        chmod +x "$backup_script"
        
        # Add to crontab (daily backup at 2 AM)
        (crontab -l 2>/dev/null; echo "0 2 * * * $backup_script") | crontab -
        
        log_success "Automated backups configured"
    else
        log_warning "Backup script not found, skipping automated backup setup"
    fi
}

print_summary() {
    log_success "Deployment completed successfully!"
    echo
    echo "==================================="
    echo "Oracle Trader Bot Deployment Summary"
    echo "==================================="
    echo "Domain: https://$DOMAIN"
    echo "Admin Panel: https://admin.$DOMAIN (if configured)"
    echo "Grafana: https://$DOMAIN/grafana"
    echo "Prometheus: https://$DOMAIN/prometheus"
    echo
    echo "Default Grafana Credentials:"
    echo "Username: admin"
    echo "Password: (check your .env file)"
    echo
    echo "Important Files:"
    echo "- Environment: $PROJECT_DIR/.env"
    echo "- Logs: $PROJECT_DIR/logs/"
    echo "- Backups: $PROJECT_DIR/backups/"
    echo
    echo "Useful Commands:"
    echo "- View logs: docker-compose logs -f"
    echo "- Restart services: docker-compose restart"
    echo "- Update application: $SCRIPT_DIR/update.sh"
    echo "- Create backup: $SCRIPT_DIR/backup.sh"
    echo
    echo "==================================="
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -d|--domain)
            DOMAIN="$2"
            shift 2
            ;;
        -e|--email)
            EMAIL="$2"
            shift 2
            ;;
        -s|--staging)
            STAGING="true"
            shift
            ;;
        -f|--skip-firewall)
            SKIP_FIREWALL="true"
            shift
            ;;
        -c|--skip-ssl)
            SKIP_SSL="true"
            shift
            ;;
        -n|--dry-run)
            DRY_RUN="true"
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

# Validate required arguments
if [[ -z "$DOMAIN" ]]; then
    log_error "Domain name is required. Use -d or --domain option."
    usage
    exit 1
fi

if [[ -z "$EMAIL" && "$SKIP_SSL" != "true" ]]; then
    log_error "Email is required for SSL certificates. Use -e or --email option, or --skip-ssl to skip SSL setup."
    usage
    exit 1
fi

# Main execution
main() {
    echo "Oracle Trader Bot - Production Deployment"
    echo "========================================"
    echo "Domain: $DOMAIN"
    echo "Email: $EMAIL"
    echo "Staging SSL: $STAGING"
    echo "Skip Firewall: $SKIP_FIREWALL"
    echo "Skip SSL: $SKIP_SSL"
    echo "Dry Run: $DRY_RUN"
    echo "========================================"
    echo
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN MODE - No changes will be made"
        echo "Would perform the following actions:"
        echo "1. Check system requirements"
        echo "2. Install Docker (if needed)"
        echo "3. Configure firewall (if enabled)"
        echo "4. Setup environment configuration"
        echo "5. Generate SSL DH parameters"
        echo "6. Setup SSL certificates (if enabled)"
        echo "7. Deploy application"
        echo "8. Setup monitoring"
        echo "9. Setup automated backups"
        return 0
    fi
    
    check_requirements
    # install_docker  # Uncomment if Docker installation is needed
    configure_firewall
    setup_environment
    generate_ssl_dhparam
    setup_ssl_certificates
    deploy_application
    setup_monitoring
    setup_backup
    print_summary
}

# Trap errors and cleanup
trap 'log_error "Deployment failed. Check the logs above for details."' ERR

# Run main function
main "$@"