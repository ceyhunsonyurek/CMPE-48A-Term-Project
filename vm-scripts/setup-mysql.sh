#!/bin/bash
# MySQL Installation and Setup Script for URL Shortener
# Run this script on the MySQL VM instance

set -e  # Exit on error

echo "=== MySQL Installation Script ==="

# Update package list
echo "Updating package list..."
sudo apt-get update

# Install MySQL Server
echo "Installing MySQL Server..."
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y mysql-server

# Start MySQL service
echo "Starting MySQL service..."
sudo systemctl start mysql
sudo systemctl enable mysql

# Configure MySQL to allow remote connections
echo "Configuring MySQL for remote connections..."
sudo sed -i 's/bind-address.*/bind-address = 0.0.0.0/' /etc/mysql/mysql.conf.d/mysqld.cnf

# Restart MySQL to apply changes
sudo systemctl restart mysql

# Create database and user
echo "Creating database and user..."
sudo mysql << EOF
CREATE DATABASE IF NOT EXISTS urlshortener;
CREATE USER IF NOT EXISTS 'appuser'@'%' IDENTIFIED BY 'urlshortener2024';
GRANT ALL PRIVILEGES ON urlshortener.* TO 'appuser'@'%';
FLUSH PRIVILEGES;
EOF

# Create tables
echo "Creating database tables..."
sudo mysql urlshortener << EOF
CREATE TABLE IF NOT EXISTS users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS urls (
    id INT PRIMARY KEY AUTO_INCREMENT,
    original_url TEXT NOT NULL,
    user_id INT NOT NULL,
    clicks INT DEFAULT 0,
    created DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    INDEX idx_user_id (user_id),
    INDEX idx_user_id_created (user_id, created)
);
EOF

echo "=== MySQL Setup Complete ==="
echo "Database: urlshortener"
echo "User: appuser"
echo "Password: urlshortener2024"
echo ""
echo "MySQL is now configured and ready to accept connections from GKE cluster."

