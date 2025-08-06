# Oracle Trader Bot - VPS Setup Guide

This guide provides step-by-step instructions for deploying the Oracle Trader Bot on a Virtual Private Server (VPS) with production-ready configuration.

## Prerequisites

### System Requirements

- **Operating System**: Ubuntu 20.04 LTS or newer (recommended)
- **RAM**: Minimum 4GB, recommended 8GB or more
- **Storage**: Minimum 50GB SSD
- **CPU**: 2+ cores recommended
- **Network**: Static IP address and domain name

### Required Software

The deployment script will install these automatically, but you can install them manually:

- Docker Engine 20.10+
- Docker Compose 2.0+
- Git
- curl
- openssl
- UFW (Uncomplicated Firewall)

## Quick Start

### 1. Initial Server Setup

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Create a dedicated user for the application
sudo adduser oracle-trader
sudo usermod -aG sudo oracle-trader
sudo usermod -aG docker oracle-trader

# Switch to the application user
sudo su - oracle-trader
```

### 2. Clone the Repository

```bash
# Clone the repository
git clone https://github.com/zieism/oracle_trader_bot.git
cd oracle_trader_bot/deployment

# Make scripts executable
chmod +x scripts/*.sh
```

### 3. Run the Deployment Script

```bash
# Basic deployment with SSL
./scripts/deploy.sh -d your-domain.com -e your-email@domain.com

# Staging deployment (for testing)
./scripts/deploy.sh -d your-domain.com -e your-email@domain.com --staging

# Skip firewall configuration (if you manage it separately)
./scripts/deploy.sh -d your-domain.com -e your-email@domain.com --skip-firewall
```

### 4. Configure Environment Variables

After running the deployment script, edit the `.env` file with your actual API keys:

```bash
nano .env
```

Update the following important variables:
- Exchange API credentials (KuCoin, Binance, Kraken)
- Email/notification settings
- Security keys (auto-generated but can be customized)

### 5. Start the Services

```bash
# Start in production mode
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f oracle-trader
```

## Detailed Configuration

### Domain and DNS Setup

1. **Purchase a domain** from a registrar (Namecheap, GoDaddy, etc.)

2. **Configure DNS records**:
   ```
   A Record: @ -> YOUR_SERVER_IP
   A Record: www -> YOUR_SERVER_IP
   A Record: admin -> YOUR_SERVER_IP (optional)
   ```

3. **Wait for DNS propagation** (can take up to 48 hours)

### SSL Certificate Configuration

The deployment script automatically configures Let's Encrypt SSL certificates. Manual configuration:

```bash
# Test SSL certificate generation (staging)
docker-compose run --rm certbot certonly \
  --webroot --webroot-path=/var/www/certbot \
  --email your-email@domain.com \
  --agree-tos --staging \
  -d your-domain.com -d www.your-domain.com

# Generate production certificates
docker-compose run --rm certbot certonly \
  --webroot --webroot-path=/var/www/certbot \
  --email your-email@domain.com \
  --agree-tos \
  -d your-domain.com -d www.your-domain.com
```

### Firewall Configuration

The deployment script configures UFW automatically. Manual setup:

```bash
# Reset and configure UFW
sudo ufw --force reset
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow essential services
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS

# Enable firewall
sudo ufw --force enable

# Check status
sudo ufw status verbose
```

### Systemd Service Setup

Enable automatic startup on boot:

```bash
# Copy systemd service file
sudo cp systemd/oracle-trader.service /etc/systemd/system/

# Update paths in service file if needed
sudo sed -i 's|/opt/oracle-trader-bot|'"$PWD"'|g' /etc/systemd/system/oracle-trader.service

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable oracle-trader
sudo systemctl start oracle-trader

# Check status
sudo systemctl status oracle-trader
```

## Security Hardening

### 1. SSH Configuration

```bash
# Edit SSH configuration
sudo nano /etc/ssh/sshd_config

# Recommended settings:
# Port 2222                    # Change default port
# PermitRootLogin no
# PasswordAuthentication no
# PubkeyAuthentication yes
# MaxAuthTries 3

# Restart SSH service
sudo systemctl restart ssh
```

### 2. Fail2Ban Installation

```bash
# Install fail2ban
sudo apt install fail2ban

# Configure jail for SSH
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local

# Edit configuration
sudo nano /etc/fail2ban/jail.local

# Start fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

### 3. Regular Security Updates

```bash
# Enable automatic security updates
sudo apt install unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades

# Configure automatic updates
echo 'Unattended-Upgrade::Automatic-Reboot "false";' | sudo tee -a /etc/apt/apt.conf.d/50unattended-upgrades
```

## Monitoring and Maintenance

### Health Monitoring

```bash
# Run health check
./scripts/monitor.sh

# Continuous monitoring
./scripts/monitor.sh --continuous --interval 60

# With alerts
./scripts/monitor.sh -a admin@yourdomain.com -s https://hooks.slack.com/your-webhook
```

### Backup Management

```bash
# Create full backup
./scripts/backup.sh

# Database only backup
./scripts/backup.sh -t database

# Encrypted backup with remote storage
./scripts/backup.sh -e -s
```

### Updates

```bash
# Update to latest version
./scripts/update.sh

# Update to specific tag
./scripts/update.sh -t v1.2.0

# Rollback if needed
./scripts/update.sh --rollback
```

## Accessing the Application

After successful deployment, access your application at:

- **Main Application**: `https://your-domain.com`
- **API Documentation**: `https://your-domain.com/docs` (if enabled)
- **Grafana Dashboard**: `https://your-domain.com/grafana`
- **Prometheus Metrics**: `https://your-domain.com/prometheus` (restricted access)

### Default Credentials

- **Grafana**: admin / (check .env file for password)

## Performance Optimization

### 1. Database Optimization

```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U trader -d oracle_trader

# Common optimizations
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;

# Restart PostgreSQL
docker-compose restart postgres
```

### 2. Redis Optimization

```bash
# Redis memory optimization
docker-compose exec redis redis-cli CONFIG SET maxmemory-policy allkeys-lru
docker-compose exec redis redis-cli CONFIG SET maxmemory 256mb
```

### 3. Application Scaling

```bash
# Scale application instances
docker-compose up -d --scale oracle-trader=3

# Load balancing is handled by Nginx automatically
```

## Troubleshooting

### Common Issues

1. **Services not starting**:
   ```bash
   # Check logs
   docker-compose logs oracle-trader
   
   # Check system resources
   free -h
   df -h
   ```

2. **Database connection issues**:
   ```bash
   # Test database connectivity
   docker-compose exec postgres pg_isready -U trader
   
   # Check database logs
   docker-compose logs postgres
   ```

3. **SSL certificate issues**:
   ```bash
   # Check certificate status
   docker-compose logs nginx
   
   # Renew certificates manually
   docker-compose run --rm certbot renew
   ```

4. **High resource usage**:
   ```bash
   # Monitor resource usage
   docker stats
   
   # Check application metrics
   curl http://localhost:8000/metrics
   ```

### Log Locations

- **Application logs**: `./logs/`
- **Nginx logs**: `./logs/nginx/`
- **Database logs**: Check with `docker-compose logs postgres`
- **System logs**: `/var/log/syslog`

### Getting Help

1. **Check the logs** first for any error messages
2. **Run the health check** script: `./scripts/monitor.sh`
3. **Review the troubleshooting guide** in `docs/Troubleshooting.md`
4. **Create an issue** on the GitHub repository with:
   - Error logs
   - System information
   - Steps to reproduce

## Next Steps

1. **Configure monitoring alerts** for proactive issue detection
2. **Set up automated backups** to remote storage
3. **Implement CI/CD pipeline** for automated deployments
4. **Scale horizontally** by adding more application instances
5. **Optimize performance** based on monitoring data

## Security Considerations

- **Regular updates**: Keep all components updated
- **Strong passwords**: Use complex passwords for all accounts
- **Network security**: Properly configure firewall rules
- **Access control**: Limit SSH and administrative access
- **Monitoring**: Implement comprehensive logging and alerting
- **Backups**: Regular, tested backups stored securely

For more detailed information, refer to the additional documentation files in the `docs/` directory.