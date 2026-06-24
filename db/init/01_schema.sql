-- Create application schema (idempotent design)

CREATE DATABASE IF NOT EXISTS app_db;

USE app_db;

-- Main table for testing connectivity
CREATE TABLE IF NOT EXISTS health_check (
    id INT AUTO_INCREMENT PRIMARY KEY,
    service_name VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Seed initial row
INSERT INTO health_check (service_name, status)
VALUES ('dummy-python-app', 'initialized');