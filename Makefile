# Makefile for Oracle Trader Bot Docker Operations

.PHONY: help build up down logs clean dev-up dev-down prod-up prod-down health backup restore

# Default target
help: ## Show this help message
	@echo "Oracle Trader Bot - Docker Operations"
	@echo "====================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ==================== PRODUCTION COMMANDS ====================

build: ## Build all Docker images
	docker-compose build --no-cache

build-backend: ## Build only backend image
	docker-compose build backend

build-frontend: ## Build only frontend image  
	docker-compose build frontend

prod-up: ## Start production environment
	docker-compose up -d

prod-up-with-redis: ## Start production environment with Redis
	docker-compose --profile with-redis up -d

prod-down: ## Stop production environment
	docker-compose down

prod-logs: ## View production logs
	docker-compose logs -f

prod-restart: ## Restart production environment
	docker-compose restart

# ==================== DEVELOPMENT COMMANDS ====================

dev-up: ## Start development environment
	docker-compose -f docker-compose.dev.yml up -d

dev-down: ## Stop development environment
	docker-compose -f docker-compose.dev.yml down

dev-logs: ## View development logs
	docker-compose -f docker-compose.dev.yml logs -f

dev-shell: ## Open shell in development backend
	docker-compose -f docker-compose.dev.yml exec backend bash

# ==================== UTILITY COMMANDS ====================

health: ## Check service health
	@echo "Checking service health..."
	@curl -s http://localhost/health && echo " - Nginx: OK" || echo " - Nginx: FAIL"
	@curl -s http://localhost/api/v1/health/app | jq .status && echo " - Backend: OK" || echo " - Backend: FAIL"
	@docker-compose ps

logs: ## View logs for all services
	docker-compose logs -f

logs-backend: ## View backend logs
	docker-compose logs -f backend

logs-frontend: ## View frontend logs
	docker-compose logs -f frontend

logs-nginx: ## View nginx logs
	docker-compose logs -f nginx

logs-db: ## View database logs
	docker-compose logs -f postgres

# ==================== DATABASE COMMANDS ====================

db-shell: ## Open database shell
	docker-compose exec postgres psql -U oracle_user -d oracle_trader_bot

db-backup: ## Backup database
	@echo "Creating database backup..."
	docker-compose exec postgres pg_dump -U oracle_user oracle_trader_bot > backups/db_backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "Backup completed: backups/db_backup_$$(date +%Y%m%d_%H%M%S).sql"

db-restore: ## Restore database (requires BACKUP_FILE variable)
	@if [ -z "$(BACKUP_FILE)" ]; then echo "Usage: make db-restore BACKUP_FILE=path/to/backup.sql"; exit 1; fi
	cat $(BACKUP_FILE) | docker-compose exec -T postgres psql -U oracle_user -d oracle_trader_bot
	@echo "Database restored from $(BACKUP_FILE)"

# ==================== MAINTENANCE COMMANDS ====================

clean: ## Clean up Docker resources
	docker-compose down -v
	docker system prune -f
	docker volume prune -f

clean-images: ## Remove all Oracle Trader Bot images
	docker images | grep oracle_trader | awk '{print $$3}' | xargs -r docker rmi -f

stats: ## Show container resource usage
	docker stats

volumes: ## List Docker volumes
	docker volume ls | grep oracle_trader

ps: ## Show running containers
	docker-compose ps

# ==================== SETUP COMMANDS ====================

setup-env: ## Copy environment file template
	@if [ ! -f .env ]; then \
		cp .env.docker.example .env; \
		echo "Created .env file from template. Please edit with your values."; \
	else \
		echo ".env file already exists. Skipping."; \
	fi

setup-dirs: ## Create necessary directories
	mkdir -p backups ssl logs

init: setup-env setup-dirs ## Initialize project for Docker deployment
	@echo "Oracle Trader Bot Docker environment initialized!"
	@echo "1. Edit .env file with your configuration"
	@echo "2. Run 'make build' to build images"
	@echo "3. Run 'make prod-up' to start production environment"

# ==================== TESTING COMMANDS ====================

test-backend: ## Run backend tests in container
	docker-compose exec backend python -m pytest tests/ -v

test-integration: ## Run integration tests
	docker-compose exec backend python -m pytest tests/test_integration_smoke.py -v

# ==================== MONITORING COMMANDS ====================

monitor: ## Monitor all services (requires watch command)
	@echo "Monitoring Oracle Trader Bot services (Ctrl+C to exit)..."
	watch -n 5 'echo "=== Container Status ===" && docker-compose ps && echo && echo "=== Health Checks ===" && curl -s http://localhost/health && echo && curl -s http://localhost/api/v1/health/app | jq . 2>/dev/null'

# ==================== ADVANCED COMMANDS ====================

scale-backend: ## Scale backend service (requires REPLICAS variable)
	@if [ -z "$(REPLICAS)" ]; then echo "Usage: make scale-backend REPLICAS=3"; exit 1; fi
	docker-compose up -d --scale backend=$(REPLICAS)

update: ## Update and restart services
	git pull
	docker-compose build
	docker-compose up -d
	@echo "Services updated and restarted!"

# Environment-specific shortcuts
dev: dev-up ## Alias for dev-up
prod: prod-up ## Alias for prod-up
stop: prod-down ## Alias for prod-down
