#!/bin/bash

# Oracle Trader Bot - Deployment Validation Script
# This script validates the deployment configuration files

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

validate_file_exists() {
    local file="$1"
    local description="$2"
    
    if [[ -f "$file" ]]; then
        log_success "$description exists"
        return 0
    else
        log_error "$description missing: $file"
        return 1
    fi
}

validate_script_syntax() {
    local script="$1"
    local name="$2"
    
    if bash -n "$script" 2>/dev/null; then
        log_success "$name script syntax is valid"
        return 0
    else
        log_error "$name script has syntax errors"
        return 1
    fi
}

validate_directory_structure() {
    log_info "Validating directory structure..."
    
    local errors=0
    
    # Check main directories
    for dir in nginx scripts systemd docs; do
        if [[ -d "$PROJECT_DIR/$dir" ]]; then
            log_success "Directory $dir exists"
        else
            log_error "Directory $dir missing"
            errors=$((errors + 1))
        fi
    done
    
    return $errors
}

validate_configuration_files() {
    log_info "Validating configuration files..."
    
    local errors=0
    
    # Check Docker Compose files
    validate_file_exists "$PROJECT_DIR/docker-compose.yml" "Base Docker Compose" || errors=$((errors + 1))
    validate_file_exists "$PROJECT_DIR/docker-compose.prod.yml" "Production Docker Compose" || errors=$((errors + 1))
    
    # Check environment template
    validate_file_exists "$PROJECT_DIR/.env.example" "Environment template" || errors=$((errors + 1))
    
    # Check Nginx configuration
    validate_file_exists "$PROJECT_DIR/nginx/nginx.conf" "Nginx configuration" || errors=$((errors + 1))
    
    # Check systemd service
    validate_file_exists "$PROJECT_DIR/systemd/oracle-trader.service" "Systemd service" || errors=$((errors + 1))
    
    return $errors
}

validate_scripts() {
    log_info "Validating deployment scripts..."
    
    local errors=0
    
    # Check script files exist and are executable
    local scripts=("deploy.sh" "backup.sh" "monitor.sh" "update.sh")
    
    for script in "${scripts[@]}"; do
        local script_path="$PROJECT_DIR/scripts/$script"
        
        if validate_file_exists "$script_path" "$script script"; then
            if [[ -x "$script_path" ]]; then
                log_success "$script is executable"
            else
                log_warning "$script is not executable (will be fixed)"
                chmod +x "$script_path"
            fi
            
            validate_script_syntax "$script_path" "$script" || errors=$((errors + 1))
        else
            errors=$((errors + 1))
        fi
    done
    
    return $errors
}

validate_environment_template() {
    log_info "Validating environment template..."
    
    local env_file="$PROJECT_DIR/.env.example"
    local errors=0
    
    # Check for essential variables
    local required_vars=("DOMAIN" "SECRET_KEY" "POSTGRES_PASSWORD" "REDIS_PASSWORD")
    
    for var in "${required_vars[@]}"; do
        if grep -q "^$var=" "$env_file"; then
            log_success "Required variable $var found"
        else
            log_error "Required variable $var missing from template"
            errors=$((errors + 1))
        fi
    done
    
    # Count total variables
    local var_count=$(grep -c "^[A-Z_]*=" "$env_file" || echo "0")
    log_info "Environment template contains $var_count variables"
    
    if [[ $var_count -lt 50 ]]; then
        log_warning "Environment template has fewer variables than expected"
    fi
    
    return $errors
}

validate_docker_compose() {
    log_info "Validating Docker Compose configuration..."
    
    local errors=0
    
    # Check for required services in base compose file
    local required_services=("oracle-trader" "postgres" "redis" "nginx")
    
    for service in "${required_services[@]}"; do
        if grep -q "^  $service:" "$PROJECT_DIR/docker-compose.yml"; then
            log_success "Service $service defined in base compose file"
        else
            log_error "Service $service missing from base compose file"
            errors=$((errors + 1))
        fi
    done
    
    # Check for production overrides
    if grep -q "resources:" "$PROJECT_DIR/docker-compose.prod.yml"; then
        log_success "Production resource limits configured"
    else
        log_warning "Production resource limits not found"
    fi
    
    return $errors
}

validate_documentation() {
    log_info "Validating documentation..."
    
    local errors=0
    
    # Check documentation files
    local docs=("VPS-Setup-Guide.md" "Security-Guide.md" "Troubleshooting.md")
    
    for doc in "${docs[@]}"; do
        validate_file_exists "$PROJECT_DIR/docs/$doc" "$doc documentation" || errors=$((errors + 1))
    done
    
    # Check README
    validate_file_exists "$PROJECT_DIR/README.md" "Deployment README" || errors=$((errors + 1))
    
    return $errors
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    local warnings=0
    
    # Check for common tools
    local tools=("curl" "openssl" "git")
    
    for tool in "${tools[@]}"; do
        if command -v "$tool" &> /dev/null; then
            log_success "$tool is available"
        else
            log_warning "$tool is not installed (required for deployment)"
            warnings=$((warnings + 1))
        fi
    done
    
    # Check if running on supported OS
    if [[ -f /etc/os-release ]]; then
        local os_info=$(grep "^ID=" /etc/os-release | cut -d= -f2 | tr -d '"')
        if [[ "$os_info" == "ubuntu" ]]; then
            log_success "Running on Ubuntu (supported)"
        else
            log_warning "Running on $os_info (Ubuntu recommended)"
        fi
    fi
    
    return $warnings
}

generate_validation_report() {
    local total_errors="$1"
    local total_warnings="$2"
    
    echo
    echo "=================================="
    echo "Deployment Validation Report"
    echo "=================================="
    echo "Total Errors: $total_errors"
    echo "Total Warnings: $total_warnings"
    echo
    
    if [[ $total_errors -eq 0 ]]; then
        if [[ $total_warnings -eq 0 ]]; then
            log_success "Deployment configuration is fully validated!"
            echo "You can proceed with deployment using:"
            echo "  ./scripts/deploy.sh -d your-domain.com -e your-email@domain.com"
        else
            log_warning "Deployment configuration is mostly valid with $total_warnings warnings"
            echo "You can proceed with deployment, but review the warnings above"
        fi
        return 0
    else
        log_error "Deployment configuration has $total_errors errors that must be fixed"
        echo "Please resolve the errors above before attempting deployment"
        return 1
    fi
}

# Main execution
main() {
    echo "Oracle Trader Bot - Deployment Validation"
    echo "========================================"
    echo "Validating deployment configuration..."
    echo
    
    cd "$PROJECT_DIR"
    
    local total_errors=0
    local total_warnings=0
    
    # Run all validations
    validate_directory_structure || total_errors=$((total_errors + $?))
    validate_configuration_files || total_errors=$((total_errors + $?))
    validate_scripts || total_errors=$((total_errors + $?))
    validate_environment_template || total_errors=$((total_errors + $?))
    validate_docker_compose || total_errors=$((total_errors + $?))
    validate_documentation || total_errors=$((total_errors + $?))
    check_prerequisites || total_warnings=$((total_warnings + $?))
    
    # Generate report
    generate_validation_report "$total_errors" "$total_warnings"
}

# Run main function
main "$@"