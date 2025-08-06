-- Oracle Trader Bot Database Initialization Script
-- This script sets up the initial database structure and security

-- Create extensions if they don't exist
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create a dedicated application user (if not exists)
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'trader_app') THEN
        CREATE ROLE trader_app WITH LOGIN PASSWORD 'secure_app_password';
    END IF;
END
$$;

-- Grant necessary permissions
GRANT CONNECT ON DATABASE oracle_trader TO trader_app;
GRANT USAGE ON SCHEMA public TO trader_app;
GRANT CREATE ON SCHEMA public TO trader_app;

-- Create audit table for tracking changes
CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    table_name VARCHAR(50) NOT NULL,
    operation VARCHAR(10) NOT NULL,
    old_values JSONB,
    new_values JSONB,
    user_id VARCHAR(50),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index for audit log performance
CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON audit_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_log_table_name ON audit_log(table_name);

-- Function to log changes (trigger function)
CREATE OR REPLACE FUNCTION log_changes()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO audit_log (table_name, operation, new_values)
        VALUES (TG_TABLE_NAME, TG_OP, row_to_json(NEW));
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO audit_log (table_name, operation, old_values, new_values)
        VALUES (TG_TABLE_NAME, TG_OP, row_to_json(OLD), row_to_json(NEW));
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO audit_log (table_name, operation, old_values)
        VALUES (TG_TABLE_NAME, TG_OP, row_to_json(OLD));
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Create function for health checks
CREATE OR REPLACE FUNCTION health_check()
RETURNS JSON AS $$
BEGIN
    RETURN json_build_object(
        'status', 'healthy',
        'timestamp', NOW(),
        'version', version(),
        'connections', (SELECT count(*) FROM pg_stat_activity),
        'database_size', pg_size_pretty(pg_database_size(current_database()))
    );
END;
$$ LANGUAGE plpgsql;

-- Security settings
-- Set secure defaults
ALTER DATABASE oracle_trader SET log_statement = 'all';
ALTER DATABASE oracle_trader SET log_min_duration_statement = 1000;

-- Grant permissions to trader_app
GRANT EXECUTE ON FUNCTION health_check() TO trader_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON audit_log TO trader_app;

-- Message for successful initialization
DO $$
BEGIN
    RAISE NOTICE 'Oracle Trader Bot database initialization completed successfully';
    RAISE NOTICE 'Database: %, Size: %', current_database(), pg_size_pretty(pg_database_size(current_database()));
END
$$;