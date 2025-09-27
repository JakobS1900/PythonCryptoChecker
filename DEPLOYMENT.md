# 🚀 CryptoChecker Version3 - Deployment Guide

## 📋 Overview

This guide covers deploying CryptoChecker Version3 to production environments. The platform is designed to be deployment-ready with minimal configuration.

## 🔧 **Environment Setup**

### **1. Production Environment Variables**

Create a production `.env` file:

```bash
# Application Settings
DEBUG=False
SECRET_KEY=your-production-secret-key-change-this
HOST=0.0.0.0
PORT=8000

# Database Configuration (Production)
DATABASE_URL=postgresql+asyncpg://username:password@host:port/database

# Crypto API Settings
COINGECKO_API_KEY=your-coingecko-api-key
COINCAP_API_KEY=your-coincap-api-key
PRICE_UPDATE_INTERVAL=30

# Gaming Configuration
GEM_TO_USD_RATE=0.01
MIN_BET_AMOUNT=10
MAX_BET_AMOUNT=10000
GUEST_MODE_GEMS=5000

# JWT Authentication
JWT_SECRET_KEY=your-jwt-secret-key-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30

# CORS Settings
CORS_ORIGINS=["https://yourdomain.com", "https://www.yourdomain.com"]

# SSL/Security
FORCE_HTTPS=True
SECURE_COOKIES=True
```

### **2. Database Setup**

#### **SQLite (Development)**
```bash
# Default - no additional setup required
DATABASE_URL=sqlite+aiosqlite:///./crypto_tracker_v3.db
```

#### **PostgreSQL (Production)**
```bash
# Install PostgreSQL dependencies
pip install asyncpg psycopg2-binary

# Configure connection
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/cryptochecker_v3
```

#### **Database Migration**
```python
# Run database initialization
python -c "
import asyncio
from database.database import init_database
asyncio.run(init_database())
"
```

## 🐳 **Docker Deployment**

### **Dockerfile**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 cryptouser && chown -R cryptouser:cryptouser /app
USER cryptouser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/api/crypto/market/status || exit 1

# Start application
CMD ["python", "main.py"]
```

### **docker-compose.yml**
```yaml
version: '3.8'

services:
  cryptochecker:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:password@db:5432/cryptochecker
      - DEBUG=False
      - SECRET_KEY=${SECRET_KEY}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
    depends_on:
      - db
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=cryptochecker
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - cryptochecker
    restart: unless-stopped

volumes:
  postgres_data:
```

## 🌐 **Web Server Configuration**

### **Nginx Configuration**
```nginx
upstream cryptochecker {
    server cryptochecker:8000;
}

server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;

    # Static files
    location /static {
        alias /app/web/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # API endpoints
    location /api {
        proxy_pass http://cryptochecker;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Main application
    location / {
        proxy_pass http://cryptochecker;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## ☁️ **Cloud Deployment**

### **1. Heroku**
```bash
# Install Heroku CLI and login
heroku login

# Create app
heroku create cryptochecker-v3

# Set environment variables
heroku config:set SECRET_KEY=your-secret-key
heroku config:set JWT_SECRET_KEY=your-jwt-secret
heroku config:set DEBUG=False

# Add PostgreSQL addon
heroku addons:create heroku-postgresql:hobby-dev

# Deploy
git push heroku main
```

**Procfile**:
```
web: python main.py
```

### **2. DigitalOcean App Platform**
```yaml
# app.yaml
name: cryptochecker-v3
services:
- name: web
  source_dir: /
  github:
    repo: your-username/cryptochecker-v3
    branch: main
  run_command: python main.py
  environment_slug: python
  instance_count: 1
  instance_size_slug: basic-xxs
  envs:
  - key: SECRET_KEY
    value: your-secret-key
  - key: JWT_SECRET_KEY
    value: your-jwt-secret
  - key: DEBUG
    value: "False"
databases:
- name: cryptochecker-db
  engine: PG
  version: "15"
```

### **3. AWS ECS**
```yaml
# task-definition.json
{
  "family": "cryptochecker-v3",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "executionRoleArn": "arn:aws:iam::account:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "cryptochecker",
      "image": "your-account.dkr.ecr.region.amazonaws.com/cryptochecker-v3:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "DEBUG",
          "value": "False"
        }
      ],
      "secrets": [
        {
          "name": "SECRET_KEY",
          "valueFrom": "arn:aws:secretsmanager:region:account:secret:cryptochecker/secret-key"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/cryptochecker-v3",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

## 🔒 **Security Configuration**

### **1. SSL/TLS Setup**
```bash
# Let's Encrypt with Certbot
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

### **2. Firewall Configuration**
```bash
# UFW (Ubuntu)
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### **3. Security Headers**
Update `main.py` to include security middleware:

```python
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware

if not DEBUG:
    app.add_middleware(HTTPSRedirectMiddleware)
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["yourdomain.com", "*.yourdomain.com"]
    )
```

## 📊 **Monitoring & Logging**

### **1. Application Monitoring**
```python
# Add to main.py
import logging
from logging.handlers import RotatingFileHandler

# Configure logging
if not DEBUG:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(name)s %(message)s',
        handlers=[
            RotatingFileHandler('logs/app.log', maxBytes=10485760, backupCount=5),
            logging.StreamHandler()
        ]
    )
```

### **2. Health Checks**
```python
@app.get("/health")
async def health_check():
    """Health check endpoint for load balancers."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "3.0.0"
    }
```

### **3. Metrics Collection**
```python
from prometheus_client import Counter, Histogram, generate_latest

# Metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration')

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(generate_latest(), media_type="text/plain")
```

## 🔄 **Backup Strategy**

### **1. Database Backups**
```bash
#!/bin/bash
# backup.sh
DATE=$(date +%Y%m%d_%H%M%S)
pg_dump $DATABASE_URL > backups/cryptochecker_$DATE.sql
aws s3 cp backups/cryptochecker_$DATE.sql s3://your-backup-bucket/
find backups/ -name "*.sql" -mtime +7 -delete
```

### **2. Automated Backups with Cron**
```bash
# crontab -e
0 2 * * * /path/to/backup.sh
```

## 🚀 **Deployment Checklist**

### **Pre-Deployment**
- [ ] Environment variables configured
- [ ] Database connection tested
- [ ] SSL certificates installed
- [ ] Security headers configured
- [ ] Monitoring setup
- [ ] Backup strategy implemented

### **Deployment**
- [ ] Application deployed
- [ ] Database migrations run
- [ ] Static files served correctly
- [ ] Health checks passing
- [ ] SSL working
- [ ] Performance tested

### **Post-Deployment**
- [ ] Monitoring alerts configured
- [ ] Logs being collected
- [ ] Backups running
- [ ] Performance metrics tracked
- [ ] Error tracking active

## 🛠️ **Maintenance**

### **Regular Tasks**
- Monitor application logs
- Check database performance
- Update dependencies
- Renew SSL certificates
- Review security settings
- Backup verification

### **Scaling Considerations**
- **Horizontal Scaling**: Multiple app instances behind load balancer
- **Database Scaling**: Read replicas, connection pooling
- **Caching**: Redis for session storage and API caching
- **CDN**: CloudFlare/AWS CloudFront for static assets

---

## 🎯 **Production Ready**

CryptoChecker Version3 is designed for production deployment with:

- ✅ **Environment Configuration**: Flexible .env setup
- ✅ **Database Support**: SQLite for development, PostgreSQL for production
- ✅ **Container Ready**: Docker and docker-compose included
- ✅ **Security Focused**: HTTPS, security headers, input validation
- ✅ **Monitoring Ready**: Health checks, logging, metrics endpoints
- ✅ **Scalable Architecture**: Stateless design, database-backed sessions

**Deploy with confidence!** 🚀