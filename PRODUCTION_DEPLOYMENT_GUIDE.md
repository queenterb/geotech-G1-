# Production Deployment Guide for CIS Billing System

## Executive Summary

This guide provides step-by-step instructions for deploying the CIS (Causal Inference System) billing and licensing platform to production. The system handles user management, subscription management, payment processing, and comprehensive analytics.

---

## Table of Contents

1. [Pre-Deployment Requirements](#pre-deployment-requirements)
2. [Infrastructure Setup](#infrastructure-setup)
3. [Database Configuration](#database-configuration)
4. [Environment Variables](#environment-variables)
5. [Application Deployment](#application-deployment)
6. [SSL/TLS Configuration](#ssltls-configuration)
7. [Monitoring & Logging](#monitoring--logging)
8. [Backup & Recovery](#backup--recovery)
9. [Security Hardening](#security-hardening)
10. [Post-Deployment Testing](#post-deployment-testing)
11. [Troubleshooting](#troubleshooting)

---

## Pre-Deployment Requirements

### Hardware Requirements
- **Minimum**: 2 CPU cores, 4GB RAM, 50GB storage
- **Recommended**: 4+ CPU cores, 8GB RAM, 100GB storage
- **Database**: SSD for SQLite or dedicated PostgreSQL/MySQL instance

### Software Requirements
- Python 3.8+ 
- Flask 2.0+
- SQLite3 or PostgreSQL/MySQL
- Node.js 14+ (for dashboard frontend)
- Nginx or Apache (reverse proxy)
- Supervisor or systemd (process management)

### Compliance & Security
- SSL/TLS certificates (Let's Encrypt recommended)
- PCI DSS compliance for payment processing
- GDPR compliance framework
- Data encryption standards (AES-256 for sensitive data)

---

## Infrastructure Setup

### Option 1: Linux Server (Recommended)

#### Step 1: Initial Server Setup
```bash
# Update system packages
sudo apt-get update && sudo apt-get upgrade -y

# Install dependencies
sudo apt-get install -y \
    python3 \
    python3-venv \
    python3-pip \
    nginx \
    supervisor \
    git \
    curl \
    wget \
    openssl

# Create application user
sudo useradd -m -s /bin/bash cis-app
sudo usermod -aG sudo cis-app

# Switch to app user
sudo su - cis-app
```

#### Step 2: Clone Repository
```bash
# Clone the CIS repository
git clone https://github.com/youorg/cis.git
cd cis

# Create Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install gunicorn  # WSGI server
pip install psycopg2-binary  # PostgreSQL adapter (if using PostgreSQL)
```

### Option 2: Docker Deployment (Recommended for Scaling)

#### Step 1: Build Docker Image
```bash
# Navigate to project root
cd /path/to/cis

# Build the Docker image
docker build -t cis-billing:1.0 -f Dockerfile .

# Test the image
docker run -it --rm cis-billing:1.0 python -c "from cis import main_detector; print('Success')"
```

#### Step 2: Run with Docker Compose
```bash
# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f cis-billing
```

---

## Database Configuration

### SQLite (Simple Setup)
```bash
# Database is automatically created at ~/.cis_billing.db
# Initialize database
python cis/database.py
```

### PostgreSQL (Recommended for Production)

#### Step 1: Install PostgreSQL
```bash
sudo apt-get install -y postgresql postgresql-contrib

# Switch to postgres user
sudo su - postgres

# Create database and user
createdb cis_billing
createuser cis_user
psql -c "ALTER USER cis_user WITH PASSWORD 'strong_password_here';"
psql -c "GRANT ALL PRIVILEGES ON DATABASE cis_billing TO cis_user;"
```

#### Step 2: Configure Connection String
```bash
# Set environment variable
export DATABASE_URL="postgresql://cis_user:password@localhost:5432/cis_billing"

# Or update config.json
{
  "database": {
    "type": "postgresql",
    "host": "localhost",
    "port": 5432,
    "name": "cis_billing",
    "user": "cis_user",
    "password": "strong_password"
  }
}
```

#### Step 3: Initialize Database Schema
```bash
python -c "from cis.database import init_database; init_database()"
```

---

## Environment Variables

### Create .env File
```bash
cat > ~/.cis_env << 'EOF'
# Flask Configuration
FLASK_ENV=production
FLASK_APP=cis/dashboard_new.py
SECRET_KEY=your_very_long_random_secret_key_here_min_32_chars

# Database
DATABASE_URL=postgresql://user:password@localhost/cis_billing
# OR for SQLite:
DATABASE_PATH=/var/lib/cis/cis_billing.db

# Stripe Integration
STRIPE_API_KEY=sk_live_your_real_stripe_key_here
STRIPE_PUBLISHABLE_KEY=pk_live_your_real_publishable_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret

# Email Configuration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FROM_EMAIL=noreply@cis-security.com
FROM_NAME="CIS Security"

# Application Settings
APP_HOST=0.0.0.0
APP_PORT=5000
LOG_LEVEL=INFO
DEBUG=False

# Security
HTTPS_REDIRECT=True
HSTS_MAX_AGE=31536000
CORS_ALLOWED_ORIGINS=https://cis-security.com

# Admin
ADMIN_EMAIL=admin@cis-security.com
ADMIN_PASSWORD=hash_of_strong_password

# Monitoring
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
DATADOG_API_KEY=your_datadog_key
EOF

# Load environment variables
source ~/.cis_env
```

---

## Application Deployment

### Step 1: Create Systemd Service File

```bash
sudo cat > /etc/systemd/system/cis-billing.service << 'EOF'
[Unit]
Description=CIS Billing Application
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=notify
User=cis-app
Group=cis-app
WorkingDirectory=/home/cis-app/cis

# Load environment
EnvironmentFile=/home/cis-app/.cis_env

# Start application with Gunicorn
ExecStart=/home/cis-app/cis/venv/bin/gunicorn \
    --workers 4 \
    --worker-class sync \
    --bind 127.0.0.1:5000 \
    --timeout 120 \
    --access-logfile /var/log/cis/access.log \
    --error-logfile /var/log/cis/error.log \
    --log-level info \
    cis.dashboard_new:app

# Restart policy
Restart=on-failure
RestartSec=10

# Security
PrivateTmp=yes
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable cis-billing.service
sudo systemctl start cis-billing.service

# Check status
sudo systemctl status cis-billing.service
```

### Step 2: Configure Nginx Reverse Proxy

```bash
sudo cat > /etc/nginx/sites-available/cis-billing << 'EOF'
upstream cis_app {
    server 127.0.0.1:5000;
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name cis-security.com www.cis-security.com;
    return 301 https://$server_name$request_uri;
}

# HTTPS Server
server {
    listen 443 ssl http2;
    server_name cis-security.com www.cis-security.com;
    
    # SSL certificates
    ssl_certificate /etc/letsencrypt/live/cis-security.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/cis-security.com/privkey.pem;
    
    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    
    # Logging
    access_log /var/log/nginx/cis-access.log;
    error_log /var/log/nginx/cis-error.log;
    
    # Proxy settings
    proxy_read_timeout 120s;
    proxy_connect_timeout 75s;
    
    location / {
        proxy_pass http://cis_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
    }
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=general:10m rate=10r/s;
    limit_req_zone $http_x_api_key zone=api:10m rate=100r/s;
    
    location /api/ {
        limit_req zone=api burst=150 nodelay;
        proxy_pass http://cis_app;
        proxy_set_header X-API-Key $http_x_api_key;
    }
}
EOF

# Enable site
sudo ln -s /etc/nginx/sites-available/cis-billing /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## SSL/TLS Configuration

### Let's Encrypt with Certbot

```bash
# Install Certbot
sudo apt-get install -y certbot python3-certbot-nginx

# Obtain certificate
sudo certbot certonly --nginx \
    -d cis-security.com \
    -d www.cis-security.com \
    --email admin@cis-security.com

# Auto-renewal
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer

# Verify renewal
sudo certbot renew --dry-run
```

---

## Monitoring & Logging

### Step 1: Setup Centralized Logging

```bash
# Install rsyslog (already included on most Linux)
sudo systemctl enable rsyslog
sudo systemctl start rsyslog

# Configure log rotation
sudo cat > /etc/logrotate.d/cis-billing << 'EOF'
/var/log/cis/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 cis-app cis-app
    sharedscripts
    postrotate
        systemctl reload cis-billing > /dev/null 2>&1 || true
    endscript
}
EOF
```

### Step 2: Application Monitoring

```bash
# Install Datadog Agent (example)
DD_AGENT_MAJOR_VERSION=7 \
DD_API_KEY=your_datadog_api_key \
bash -c "$(curl -L https://s3.amazonaws.com/dd-agent/scripts/install_agent.sh)"

# Or install Prometheus for metrics
sudo apt-get install -y prometheus node-exporter
```

### Step 3: Health Checks

```bash
# Create health check endpoint
# Add to dashboard_new.py:

@app.route('/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    }), 200

# Monitor with curl
curl -I https://cis-security.com/health
```

---

## Backup & Recovery

### Automated Database Backups

```bash
# Create backup script
cat > /usr/local/bin/backup-cis-db.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/var/backups/cis"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="cis_billing"
BACKUP_FILE="$BACKUP_DIR/$DB_NAME-$DATE.sql"

mkdir -p $BACKUP_DIR

# PostgreSQL backup
pg_dump -U cis_user $DB_NAME | gzip > $BACKUP_FILE.gz

# Keep last 30 days
find $BACKUP_DIR -type f -mtime +30 -delete

echo "Backup completed: $BACKUP_FILE.gz"
EOF

chmod +x /usr/local/bin/backup-cis-db.sh

# Schedule with cron
sudo crontab -e
# Add: 0 2 * * * /usr/local/bin/backup-cis-db.sh
```

### Manual Recovery

```bash
# List available backups
ls -lh /var/backups/cis/

# Restore from backup
gunzip < /var/backups/cis/cis_billing-20260115_020000.sql.gz | \
    psql -U cis_user cis_billing
```

---

## Security Hardening

### 1. Database Security

```sql
-- Create limited privilege user for application
CREATE USER cis_app_user WITH PASSWORD 'strong_password';
GRANT CONNECT ON DATABASE cis_billing TO cis_app_user;
GRANT USAGE ON SCHEMA public TO cis_app_user;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO cis_app_user;

-- Encrypt sensitive fields
-- Use pgcrypto extension
CREATE EXTENSION pgcrypto;

-- Encrypt API keys in database
ALTER TABLE users ADD COLUMN api_key_encrypted bytea;
```

### 2. API Key Management

```python
# Generate secure API keys
import secrets

def generate_api_key():
    """Generate a secure API key."""
    return f"cis_{secrets.token_urlsafe(32)}"

# Validate API keys
def validate_api_key(api_key):
    """Validate API key format and permissions."""
    if not api_key.startswith('cis_'):
        return False
    # Query database for key
    return True
```

### 3. Rate Limiting Configuration

```bash
# Add to Nginx configuration
limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;
limit_req_zone $http_x_api_key zone=api_per_user:10m rate=1000r/m;

location /login {
    limit_req zone=login burst=10 nodelay;
    proxy_pass http://cis_app;
}
```

### 4. Firewall Configuration

```bash
# UFW - Uncomplicated Firewall
sudo ufw enable
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH
sudo ufw allow 22/tcp

# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow PostgreSQL (internal only)
sudo ufw allow from 127.0.0.1 to 127.0.0.1 port 5432
```

---

## Post-Deployment Testing

### Step 1: Connectivity Tests

```bash
# Test application endpoint
curl -I https://cis-security.com/
# Should return 200

# Test API endpoint
curl -X GET https://cis-security.com/api/plans
# Should return plan list

# Test database connection
python -c "from cis.database import get_db_connection; \
    conn = get_db_connection(); \
    print('Database connection OK')"
```

### Step 2: Payment Processing Tests

```bash
# Test Stripe integration with test API key
# Create test charge
curl -X POST https://cis-security.com/api/charge \
    -H "Authorization: Bearer test_token" \
    -d "amount=1000" \
    -d "currency=usd"
```

### Step 3: Backup Verification

```bash
# Verify backups are being created
ls -lh /var/backups/cis/ | tail -1

# Test restore process on test database
# (Don't restore on production)
```

### Step 4: SSL/TLS Verification

```bash
# Check SSL certificate
curl -I --insecure https://cis-security.com/ 2>&1 | grep SSL

# Validate certificate chain
openssl s_client -connect cis-security.com:443 -showcerts
```

---

## Troubleshooting

### Common Issues & Solutions

#### Issue 1: Application Won't Start
```bash
# Check systemd service status
sudo systemctl status cis-billing
sudo journalctl -u cis-billing -n 50 --follow

# Check application logs
tail -f /var/log/cis/error.log

# Test Python imports
python -c "from cis.dashboard_new import app; print('Import OK')"
```

#### Issue 2: Database Connection Failed
```bash
# Test database connection
psql -U cis_user -d cis_billing -h localhost

# Check connection string format
echo $DATABASE_URL

# Verify PostgreSQL is running
sudo systemctl status postgresql
```

#### Issue 3: Payment Processing Fails
```bash
# Check Stripe API key
echo $STRIPE_API_KEY | head -c 20

# Test Stripe connectivity
curl https://api.stripe.com/v1/customers \
    -H "Authorization: Bearer $STRIPE_API_KEY" \
    -H "Content-Type: application/x-www-form-urlencoded"
```

#### Issue 4: High CPU/Memory Usage
```bash
# Check process usage
top -p $(pgrep -f gunicorn)

# Adjust Gunicorn workers (less memory = fewer workers)
# Edit /etc/systemd/system/cis-billing.service
# Change: --workers 2

# Reload systemd
sudo systemctl daemon-reload
sudo systemctl restart cis-billing
```

---

## Production Checklist

- [ ] Database configured and backed up
- [ ] SSL/TLS certificates installed
- [ ] Environment variables set
- [ ] Stripe API keys configured
- [ ] Email SMTP configured
- [ ] Monitoring configured
- [ ] Log rotation configured
- [ ] Backup schedule verified
- [ ] Firewall rules applied
- [ ] Health checks passing
- [ ] Load testing completed
- [ ] Security audit performed
- [ ] Documentation reviewed
- [ ] On-call support configured

---

## Support & Escalation

### Contact Information
- **Support Email**: support@cis-security.com
- **Emergency Hotline**: +1 (555) 123-4567
- **Slack Channel**: #cis-support

### Documentation
- [API Documentation](https://docs.cis-security.com)
- [Administrator Guide](./ADMIN_GUIDE.md)
- [Billing System Docs](./BILLING_SYSTEM_IMPLEMENTATION.md)

---

**Last Updated**: January 2026
**Version**: 1.0
**Maintainer**: CIS Operations Team
