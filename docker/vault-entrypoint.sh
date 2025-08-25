#!/bin/bash
set -e

# hAIveMind Enterprise Credential Vault Entrypoint Script
# Author: Lance James, Unit 221B

# Default configuration
VAULT_CONFIG_PATH=${VAULT_CONFIG_PATH:-/app/config}
VAULT_LOG_PATH=${VAULT_LOG_PATH:-/var/log/vault}
VAULT_LOG_LEVEL=${VAULT_LOG_LEVEL:-INFO}
VAULT_ENVIRONMENT=${VAULT_ENVIRONMENT:-production}

# Logging function
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" >&2
}

# Error handling
error_exit() {
    log "ERROR: $1"
    exit 1
}

# Wait for service to be ready
wait_for_service() {
    local host=$1
    local port=$2
    local service_name=$3
    local timeout=${4:-30}
    
    log "Waiting for $service_name at $host:$port..."
    
    for i in $(seq 1 $timeout); do
        if nc -z "$host" "$port" 2>/dev/null; then
            log "$service_name is ready!"
            return 0
        fi
        sleep 1
    done
    
    error_exit "$service_name is not available after ${timeout}s"
}

# Database health check
check_database() {
    if [ -n "$VAULT_DATABASE_URL" ]; then
        log "Checking database connectivity..."
        
        # Extract database connection details from URL
        DB_HOST=$(echo "$VAULT_DATABASE_URL" | sed -n 's/.*@\([^:]*\):.*/\1/p')
        DB_PORT=$(echo "$VAULT_DATABASE_URL" | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
        
        if [ -n "$DB_HOST" ] && [ -n "$DB_PORT" ]; then
            wait_for_service "$DB_HOST" "$DB_PORT" "PostgreSQL" 60
            
            # Test actual database connection
            if ! pg_isready -h "$DB_HOST" -p "$DB_PORT" -q; then
                error_exit "Database is not ready"
            fi
        else
            log "Warning: Could not parse database URL for health check"
        fi
    fi
}

# Redis health check
check_redis() {
    if [ -n "$VAULT_REDIS_URL" ]; then
        log "Checking Redis connectivity..."
        
        # Extract Redis connection details from URL
        REDIS_HOST=$(echo "$VAULT_REDIS_URL" | sed -n 's/redis:\/\/\([^:]*\):.*/\1/p')
        REDIS_PORT=$(echo "$VAULT_REDIS_URL" | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
        
        if [ -n "$REDIS_HOST" ] && [ -n "$REDIS_PORT" ]; then
            wait_for_service "$REDIS_HOST" "$REDIS_PORT" "Redis" 30
            
            # Test actual Redis connection
            if [ -n "$VAULT_REDIS_PASSWORD" ]; then
                REDISCLI_AUTH="$VAULT_REDIS_PASSWORD" redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping > /dev/null || error_exit "Redis authentication failed"
            else
                redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping > /dev/null || error_exit "Redis connection failed"
            fi
        else
            log "Warning: Could not parse Redis URL for health check"
        fi
    fi
}

# hAIveMind health check
check_haivemind() {
    if [ -n "$HAIVEMIND_MEMORY_SERVER_URL" ]; then
        log "Checking hAIveMind Memory Server connectivity..."
        
        # Extract host and port from URL
        HAIVEMIND_HOST=$(echo "$HAIVEMIND_MEMORY_SERVER_URL" | sed -n 's/http:\/\/\([^:]*\):.*/\1/p')
        HAIVEMIND_PORT=$(echo "$HAIVEMIND_MEMORY_SERVER_URL" | sed -n 's/.*:\([0-9]*\).*/\1/p')
        
        if [ -n "$HAIVEMIND_HOST" ] && [ -n "$HAIVEMIND_PORT" ]; then
            wait_for_service "$HAIVEMIND_HOST" "$HAIVEMIND_PORT" "hAIveMind Memory Server" 30
        fi
    fi
}

# Initialize configuration
init_config() {
    log "Initializing configuration..."
    
    # Create log directory
    mkdir -p "$VAULT_LOG_PATH"
    
    # Validate required environment variables
    local required_vars=(
        "VAULT_DATABASE_URL"
        "VAULT_REDIS_URL"
        "VAULT_JWT_SECRET"
    )
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            error_exit "Required environment variable $var is not set"
        fi
    done
    
    # Set default values for optional variables
    export HAIVEMIND_MACHINE_ID=${HAIVEMIND_MACHINE_ID:-vault-$(hostname)}
    export VAULT_ENVIRONMENT=${VAULT_ENVIRONMENT:-production}
    export VAULT_DEBUG=${VAULT_DEBUG:-false}
    
    log "Configuration initialized successfully"
}

# Database migration
run_migrations() {
    log "Running database migrations..."
    
    # Check if migration script exists
    if [ -f "/app/scripts/migrate.py" ]; then
        python /app/scripts/migrate.py || error_exit "Database migration failed"
        log "Database migrations completed successfully"
    else
        log "No migration script found, skipping migrations"
    fi
}

# Initialize vault data
init_vault_data() {
    log "Initializing vault data..."
    
    # Check if initialization script exists
    if [ -f "/app/scripts/init_vault.py" ]; then
        python /app/scripts/init_vault.py || error_exit "Vault initialization failed"
        log "Vault data initialized successfully"
    else
        log "No initialization script found, skipping vault data initialization"
    fi
}

# Start API server
start_api_server() {
    log "Starting Vault API Server..."
    
    # Set Python path
    export PYTHONPATH="/app/src:$PYTHONPATH"
    
    # Start the API server
    exec python -m uvicorn src.vault.api_server:app \
        --host 0.0.0.0 \
        --port 8080 \
        --workers 4 \
        --log-level "${VAULT_LOG_LEVEL,,}" \
        --access-log \
        --use-colors \
        --loop uvloop \
        --http httptools
}

# Start worker process
start_worker() {
    log "Starting Vault Worker..."
    
    export PYTHONPATH="/app/src:$PYTHONPATH"
    
    exec python /app/src/vault/worker.py
}

# Start backup service
start_backup() {
    log "Starting Backup Service..."
    
    export PYTHONPATH="/app/src:$PYTHONPATH"
    
    exec python /app/scripts/backup_service.py
}

# Start monitoring service
start_monitoring() {
    log "Starting Monitoring Service..."
    
    export PYTHONPATH="/app/src:$PYTHONPATH"
    
    exec python /app/scripts/monitoring_service.py
}

# Run database maintenance
run_maintenance() {
    log "Running database maintenance..."
    
    export PYTHONPATH="/app/src:$PYTHONPATH"
    
    python /app/scripts/maintenance.py || error_exit "Database maintenance failed"
    log "Database maintenance completed successfully"
}

# Generate initial admin user
create_admin_user() {
    log "Creating initial admin user..."
    
    export PYTHONPATH="/app/src:$PYTHONPATH"
    
    python /app/scripts/create_admin.py || log "Admin user creation failed or user already exists"
}

# Main execution
main() {
    log "Starting hAIveMind Enterprise Credential Vault"
    log "Environment: $VAULT_ENVIRONMENT"
    log "Log Level: $VAULT_LOG_LEVEL"
    
    # Initialize configuration
    init_config
    
    case "$1" in
        "api-server")
            check_database
            check_redis
            check_haivemind
            run_migrations
            init_vault_data
            create_admin_user
            start_api_server
            ;;
        "worker")
            check_database
            check_redis
            check_haivemind
            start_worker
            ;;
        "backup")
            check_database
            start_backup
            ;;
        "monitoring")
            check_database
            check_redis
            start_monitoring
            ;;
        "migrate")
            check_database
            run_migrations
            ;;
        "maintenance")
            check_database
            check_redis
            run_maintenance
            ;;
        "init")
            check_database
            check_redis
            run_migrations
            init_vault_data
            create_admin_user
            ;;
        "shell")
            export PYTHONPATH="/app/src:$PYTHONPATH"
            exec /bin/bash
            ;;
        *)
            log "Usage: $0 {api-server|worker|backup|monitoring|migrate|maintenance|init|shell}"
            log "Available commands:"
            log "  api-server  - Start the main API server"
            log "  worker      - Start background worker process"
            log "  backup      - Start backup service"
            log "  monitoring  - Start monitoring service"
            log "  migrate     - Run database migrations only"
            log "  maintenance - Run database maintenance"
            log "  init        - Initialize vault (migrations + data + admin user)"
            log "  shell       - Start interactive shell"
            exit 1
            ;;
    esac
}

# Trap signals for graceful shutdown
trap 'log "Received shutdown signal, exiting..."; exit 0' SIGTERM SIGINT

# Run main function
main "$@"