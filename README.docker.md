# 🐳 Oracle Trader Bot - Docker Deployment

Production-ready containerized deployment with Docker Compose, featuring Nginx reverse proxy, PostgreSQL database, optional Redis caching, and comprehensive health monitoring.

## 🏗️ Architecture

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│    Nginx    │───▶│   Frontend   │    │   Backend   │
│ Reverse     │    │  (React +    │    │  (FastAPI + │
│ Proxy       │    │   Nginx)     │    │  Uvicorn)   │
│ :80/:443    │    │   :3000      │    │   :8000     │
└─────────────┘    └──────────────┘    └─────────────┘
       │                                       │
       │           ┌─────────────┐            │
       └──────────▶│ PostgreSQL  │◀───────────┘
                   │ Database    │
                   │   :5432     │
                   └─────────────┘
                           │
                   ┌─────────────┐
                   │    Redis    │
                   │   (Cache)   │
                   │   :6379     │
                   └─────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Docker Engine 20.10+
- Docker Compose 2.0+
- 4GB+ available RAM
- 10GB+ available disk space

### 1. Clone and Setup
```bash
git clone https://github.com/your-username/oracle_trader_bot.git
cd oracle_trader_bot

# Initialize Docker environment
make init
```

### 2. Configure Environment
```bash
# Edit environment variables
nano .env

# Essential settings:
POSTGRES_PASSWORD=your_secure_password
ADMIN_API_TOKEN=your_admin_token
KUCOIN_API_KEY=your_api_key  # Optional for trading
```

### 3. Deploy
```bash
# Build and start all services
make build
make prod-up

# Or with Redis caching
make prod-up-with-redis
```

### 4. Verify Deployment
```bash
# Check service health
make health

# View logs
make logs

# Access application
open http://localhost
```

## 📋 Available Services

| Service    | URL                        | Purpose                  |
|------------|----------------------------|--------------------------|
| **App**    | http://localhost           | Main application         |
| **API**    | http://localhost/api/v1    | Backend API              |
| **Docs**   | http://localhost/docs      | API documentation        |
| **Health** | http://localhost/health    | System health check      |

## 🛠️ Development Setup

### Start Development Environment
```bash
# Start development databases
make dev-up

# Run frontend/backend locally with hot reload
cd oracle-trader-frontend && npm run dev  # Port 5173
cd oracle_trader_bot && python -m uvicorn app.main:app --reload  # Port 8000
```

### Development URLs
- **Frontend**: http://localhost:5173
- **Backend**: http://localhost:8000
- **Database**: localhost:5433
- **Redis**: localhost:6380

## 📁 File Structure

```
oracle_trader_bot/
├── Dockerfile.backend           # Backend container
├── Dockerfile.frontend          # Frontend container
├── docker-compose.yml           # Production setup
├── docker-compose.dev.yml       # Development setup
├── .env.docker.example          # Environment template
├── .dockerignore               # Docker build exclusions
├── Makefile                    # Docker operations
├── nginx/                      # Nginx configurations
│   ├── nginx.conf             # Main Nginx config
│   ├── reverse-proxy.conf     # Reverse proxy setup
│   └── frontend.conf          # Frontend-only config
└── init-db/                   # Database initialization
    └── 01-init-database.sh    # DB setup script
```

## ⚙️ Configuration

### Environment Variables (.env)

#### Application Settings
```bash
PROJECT_NAME=Oracle Trader Bot
APP_STARTUP_MODE=full          # full (DB) or lite (file)
DEBUG=false
```

#### Database Configuration
```bash
POSTGRES_DB=oracle_trader_bot
POSTGRES_USER=oracle_user
POSTGRES_PASSWORD=secure_password
```

#### Security Settings
```bash
ADMIN_API_TOKEN=your_admin_token
SETTINGS_ENCRYPTION_KEY=32_char_key
SETTINGS_RATE_LIMIT=10/min
HEALTH_RATE_LIMIT=30/min
```

#### Exchange Integration
```bash
KUCOIN_API_KEY=your_api_key
KUCOIN_API_SECRET=your_api_secret
KUCOIN_API_PASSPHRASE=your_passphrase
KUCOIN_SANDBOX=true
```

### Service Configuration

#### Backend Features
- ✅ Non-root user execution
- ✅ Health checks
- ✅ Volume persistence
- ✅ Environment-based config
- ✅ Graceful shutdown

#### Frontend Features
- ✅ Multi-stage build (Node.js → Nginx)
- ✅ Static asset optimization
- ✅ Gzip compression
- ✅ Cache headers
- ✅ SPA routing support

#### Nginx Features
- ✅ Reverse proxy with load balancing
- ✅ Rate limiting
- ✅ Security headers
- ✅ Static asset caching
- ✅ Gzip compression
- ✅ WebSocket support

## 📊 Monitoring & Health Checks

### Health Check Endpoints
```bash
# Global health
curl http://localhost/health

# Application health
curl http://localhost/api/v1/health/app

# Database health
curl http://localhost/api/v1/health/db

# Exchange health
curl http://localhost/api/v1/health/exchange
```

### Container Health Status
```bash
# Check all containers
docker-compose ps

# Detailed health info
make health

# Real-time monitoring
make monitor
```

### Logs and Debugging
```bash
# All service logs
make logs

# Specific service logs
make logs-backend
make logs-frontend  
make logs-nginx
make logs-db

# Follow logs in real-time
docker-compose logs -f backend
```

## 💾 Data Management

### Persistent Volumes
- **postgres_data**: Database files
- **redis_data**: Redis persistence
- **backend_logs**: Application logs
- **backend_settings**: Settings files
- **nginx_logs**: Nginx access/error logs

### Database Operations
```bash
# Backup database
make db-backup

# Restore database
make db-restore BACKUP_FILE=backup.sql

# Database shell
make db-shell

# Manual backup
docker-compose exec postgres pg_dump -U oracle_user oracle_trader_bot > backup.sql
```

## 🔧 Operations

### Service Management
```bash
# Build images
make build

# Start production
make prod-up

# Stop all services
make prod-down

# Restart specific service
docker-compose restart backend

# Scale backend
make scale-backend REPLICAS=3
```

### Maintenance
```bash
# Update application
make update

# Clean Docker resources
make clean

# View resource usage
make stats

# Prune unused resources
docker system prune -f
```

## 🚀 Production Deployment

### 1. Server Preparation
```bash
# Install Docker and Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 2. Production Configuration
```bash
# Clone repository
git clone https://your-repo.com/oracle_trader_bot.git
cd oracle_trader_bot

# Setup environment
cp .env.docker.example .env

# Edit production values
nano .env
```

### 3. SSL/HTTPS Setup (Optional)
```bash
# Create SSL directory
mkdir ssl

# Copy SSL certificates
cp your-domain.crt ssl/
cp your-domain.key ssl/

# Update nginx configuration for HTTPS
# Uncomment SSL sections in nginx/reverse-proxy.conf
```

### 4. Deploy
```bash
# Build and deploy
make build
make prod-up

# Verify deployment
make health
```

## 🔐 Security Features

### Container Security
- ✅ Non-root user execution
- ✅ Read-only root filesystems where possible
- ✅ Security scanning with health checks
- ✅ Minimal base images (Alpine Linux)

### Application Security
- ✅ Security headers middleware
- ✅ Rate limiting per endpoint
- ✅ Admin token authentication
- ✅ Settings encryption (optional)
- ✅ Audit logging

### Network Security
- ✅ Internal network isolation
- ✅ Nginx reverse proxy
- ✅ CORS configuration
- ✅ SSL/TLS support ready

## 🐛 Troubleshooting

### Common Issues

#### Container Won't Start
```bash
# Check logs
make logs-backend

# Verify environment
docker-compose config

# Rebuild without cache
docker-compose build --no-cache
```

#### Database Connection Issues
```bash
# Check database health
docker-compose exec postgres pg_isready -U oracle_user

# Verify connection string
docker-compose exec backend env | grep POSTGRES
```

#### Permission Issues
```bash
# Fix ownership
docker-compose exec backend chown -R oracle:oracle /app

# Check volume mounts
docker volume inspect oracle_trader_postgres_data
```

#### Network Connectivity
```bash
# Inspect network
docker network inspect oracle_trader_network

# Test internal connectivity
docker-compose exec backend curl http://postgres:5432
```

### Performance Optimization

#### Resource Limits
```yaml
# Add to docker-compose.yml services
deploy:
  resources:
    limits:
      memory: 512M
      cpus: '0.5'
```

#### Caching
```bash
# Enable Redis caching
make prod-up-with-redis

# Monitor cache usage
docker-compose exec redis redis-cli INFO memory
```

## 📈 Scaling

### Horizontal Scaling
```bash
# Scale backend instances
make scale-backend REPLICAS=3

# Update nginx upstream for load balancing
# Edit nginx/reverse-proxy.conf
```

### Vertical Scaling
```yaml
# Increase resources in docker-compose.yml
deploy:
  resources:
    limits:
      memory: 2G
      cpus: '2'
```

### External Services
For production at scale, consider:
- **Database**: AWS RDS, Google Cloud SQL
- **Cache**: AWS ElastiCache, Redis Cloud
- **Load Balancer**: AWS ALB, Cloudflare
- **Monitoring**: Prometheus, Grafana

## 📞 Support

### Logs Location
- **Application**: `/app/logs/` (mounted volume)
- **Nginx**: `/var/log/nginx/` (mounted volume)
- **Database**: Docker logs only

### Configuration Files
- **Environment**: `.env`
- **Nginx**: `nginx/` directory
- **Database Init**: `init-db/` directory

### Useful Commands
```bash
# Complete cleanup and restart
make clean && make build && make prod-up

# Emergency stop
docker-compose kill

# Container shell access
docker-compose exec backend bash
docker-compose exec postgres psql -U oracle_user -d oracle_trader_bot
```

---

For more detailed documentation:
- [Architecture Guide](docs/ARCHITECTURE.md)
- [Setup Instructions](docs/SETUP.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)
