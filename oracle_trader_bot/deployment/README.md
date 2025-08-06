# Oracle Trader Bot - Deployment

This directory contains production-ready deployment configurations and automation scripts for deploying the Oracle Trader Bot on Virtual Private Servers (VPS).

## Quick Start

### Prerequisites
- Ubuntu 20.04+ VPS with root/sudo access
- Domain name pointing to your server IP
- 4GB+ RAM, 50GB+ storage, 2+ CPU cores

### One-Command Deployment

```bash
# Clone the repository
git clone https://github.com/zieism/oracle_trader_bot.git
cd oracle_trader_bot/deployment

# Run deployment script
./scripts/deploy.sh -d your-domain.com -e your-email@domain.com
```

This will:
- ✅ Install Docker and Docker Compose
- ✅ Configure UFW firewall
- ✅ Generate SSL certificates with Let's Encrypt
- ✅ Set up Nginx reverse proxy
- ✅ Configure monitoring with Grafana/Prometheus
- ✅ Start all services with health checks
- ✅ Set up automated backups

## Directory Structure

```
deployment/
├── docker-compose.yml          # Development Docker Compose
├── docker-compose.prod.yml     # Production Docker Compose
├── .env.example               # Environment variables template
├── nginx/
│   ├── nginx.conf            # Nginx reverse proxy config
│   └── ssl-config/           # SSL/TLS configurations
├── scripts/
│   ├── deploy.sh            # Main deployment script
│   ├── backup.sh            # Backup automation
│   ├── monitor.sh           # Health monitoring
│   ├── update.sh            # Zero-downtime updates
│   └── init-db.sql          # Database initialization
├── systemd/
│   └── oracle-trader.service # Systemd service file
└── docs/
    ├── VPS-Setup-Guide.md    # Complete setup guide
    ├── Security-Guide.md     # Security best practices
    └── Troubleshooting.md    # Problem resolution
```

## Configuration Files

### Docker Compose

- **docker-compose.yml**: Base configuration for all environments
- **docker-compose.prod.yml**: Production overrides with:
  - Resource limits and health checks
  - Security configurations
  - Optimized logging and monitoring
  - Backup containers

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
nano .env
```

Key variables to configure:
- `DOMAIN`: Your domain name
- `POSTGRES_PASSWORD`: Secure database password
- `SECRET_KEY`: Application secret key
- Exchange API credentials (KuCoin, Binance, etc.)
- Notification settings (email, Slack, etc.)

### Nginx Configuration

Production-ready Nginx setup with:
- SSL/TLS termination
- HTTP/2 and modern cipher suites
- Rate limiting and DDoS protection
- Security headers (HSTS, CSP, etc.)
- WebSocket support
- Static file caching

## Scripts

### Deployment Script

```bash
# Basic deployment
./scripts/deploy.sh -d example.com -e admin@example.com

# With options
./scripts/deploy.sh \
  --domain example.com \
  --email admin@example.com \
  --staging \
  --skip-firewall
```

### Backup Script

```bash
# Full backup
./scripts/backup.sh

# Database only
./scripts/backup.sh -t database

# Encrypted backup with remote storage
./scripts/backup.sh -e -s
```

### Monitoring Script

```bash
# Single health check
./scripts/monitor.sh

# Continuous monitoring
./scripts/monitor.sh -c -i 30

# With alerts
./scripts/monitor.sh -a admin@example.com
```

### Update Script

```bash
# Update to latest
./scripts/update.sh

# Update to specific version
./scripts/update.sh -t v1.2.0

# Rollback
./scripts/update.sh --rollback
```

## Service Management

### Using Docker Compose

```bash
# Start services
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f oracle-trader

# Restart service
docker-compose restart oracle-trader

# Stop all services
docker-compose down
```

### Using Systemd

```bash
# Install systemd service
sudo cp systemd/oracle-trader.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable oracle-trader

# Control service
sudo systemctl start oracle-trader
sudo systemctl stop oracle-trader
sudo systemctl restart oracle-trader
sudo systemctl status oracle-trader
```

## Monitoring and Alerts

### Access Monitoring Dashboards

- **Application**: `https://your-domain.com`
- **Grafana**: `https://your-domain.com/grafana`
- **Prometheus**: `https://your-domain.com/prometheus` (restricted)

### Health Checks

```bash
# Application health
curl https://your-domain.com/health

# Service health
./scripts/monitor.sh

# Resource monitoring
docker stats
```

### Log Management

```bash
# Application logs
docker-compose logs oracle-trader

# All service logs
docker-compose logs

# Nginx logs
tail -f logs/nginx/access.log
tail -f logs/nginx/error.log

# System logs
journalctl -u oracle-trader -f
```

## Security Features

### Built-in Security

- 🔒 UFW firewall with rate limiting
- 🔒 Let's Encrypt SSL certificates
- 🔒 Security headers and HSTS
- 🔒 Container security policies
- 🔒 Database encryption and authentication
- 🔒 Secret management best practices

### Additional Security

- SSH key-based authentication
- Fail2ban for intrusion prevention
- Regular security updates
- Access control and IP restrictions
- Audit logging and monitoring

## Backup and Recovery

### Automated Backups

- Daily backups with configurable retention
- Database and file backups
- Optional encryption and remote storage
- Backup integrity verification

### Manual Backup

```bash
# Create backup
./scripts/backup.sh

# List backups
ls -la backups/

# Restore from backup
# (See Troubleshooting guide for restore procedures)
```

## Performance Optimization

### Resource Limits

Configured in `docker-compose.prod.yml`:
- Memory limits to prevent OOM
- CPU limits for fair resource sharing
- Storage quotas and cleanup policies

### Database Optimization

- Connection pooling
- Query optimization
- Index management
- Regular maintenance tasks

### Caching

- Redis for application caching
- Nginx for static file caching
- Browser caching headers

## Troubleshooting

Common issues and solutions:

1. **Services not starting**: Check logs and resource availability
2. **SSL certificate issues**: Verify DNS and run cert renewal
3. **Database connection errors**: Check credentials and network
4. **High resource usage**: Review limits and scaling options
5. **Performance issues**: Check monitoring dashboards

See `docs/Troubleshooting.md` for detailed guidance.

## Support

- 📖 **Documentation**: See `docs/` directory
- 🐛 **Issues**: Report on GitHub
- 💬 **Discussions**: GitHub Discussions
- 📧 **Email**: Check repository contacts

## Contributing

To contribute to deployment configurations:

1. Fork the repository
2. Create a feature branch
3. Test changes thoroughly
4. Submit a pull request

## License

This deployment configuration is part of the Oracle Trader Bot project and follows the same license terms.