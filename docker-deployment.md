# Docker Deployment Guide

## Production Deployment

### 1. Copy environment configuration
```bash
cp .env.docker.example .env
# Edit .env with your production values
```

### 2. Build and start all services
```bash
# Build images
docker-compose build

# Start all services
docker-compose up -d

# With Redis support
docker-compose --profile with-redis up -d
```

### 3. Check service health
```bash
# Check all containers
docker-compose ps

# Check logs
docker-compose logs -f

# Check specific service
docker-compose logs backend
```

### 4. Access the application
- **Main Application**: http://localhost (Nginx reverse proxy)
- **Backend API**: http://localhost/api/v1
- **API Documentation**: http://localhost/docs
- **Health Checks**: http://localhost/health

## Development Setup

### Start development environment
```bash
# Start database and Redis for development
docker-compose -f docker-compose.dev.yml up -d

# Access services:
# - PostgreSQL: localhost:5433
# - Redis: localhost:6380
# - Backend (if running in container): localhost:8001
```

## Service Management

### Individual service control
```bash
# Start specific services
docker-compose up -d postgres redis

# Restart a service
docker-compose restart backend

# View service logs
docker-compose logs -f nginx

# Execute commands in containers
docker-compose exec backend bash
docker-compose exec postgres psql -U oracle_user -d oracle_trader_bot
```

### Data management
```bash
# Backup database
docker-compose exec postgres pg_dump -U oracle_user oracle_trader_bot > backup.sql

# Restore database
cat backup.sql | docker-compose exec -T postgres psql -U oracle_user -d oracle_trader_bot

# View volumes
docker volume ls | grep oracle_trader

# Backup volumes
docker run --rm -v oracle_trader_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup.tar.gz /data
```

## Scaling and Production

### Horizontal scaling
```bash
# Scale backend instances
docker-compose up -d --scale backend=3

# Update nginx upstream configuration for load balancing
```

### Monitoring
```bash
# Resource usage
docker stats

# Container health
docker-compose ps
curl http://localhost/health
curl http://localhost/api/v1/health/app
```

### SSL/HTTPS Setup
1. Obtain SSL certificates
2. Mount certificates in nginx container
3. Update nginx configuration for HTTPS
4. Update environment variables for HTTPS URLs

## Troubleshooting

### Common issues
```bash
# Permission issues
docker-compose exec backend chown -R oracle:oracle /app

# Network connectivity
docker network ls
docker network inspect oracle_trader_network

# Container issues
docker-compose down
docker system prune -f
docker-compose build --no-cache
docker-compose up -d
```
