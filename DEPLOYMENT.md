# 🚀 Deployment Guide

## Development Environment

### Prerequisites
- Python 3.8 or higher
- pip (Python package installer)
- Modern web browser
- 4GB+ RAM recommended
- 1GB+ free disk space

### Quick Setup

1. **Clone Repository**
```bash
git clone <repository-url>
cd PythonCryptoChecker
```

2. **Create Virtual Environment** (Recommended)
```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate
```

3. **Install Dependencies**
```bash
pip install -r requirements.txt
```

4. **Run Development Server**
```bash
python run.py
```

5. **Access Platform**
- Open browser to: http://localhost:8000
- API Documentation: http://localhost:8000/api/docs

## Production Deployment

### Environment Variables

Create a `.env` file in the project root:

```env
# Server Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=False

# Security
SECRET_KEY=your-super-secret-key-here
SESSION_SECRET=your-session-secret-here

# Database
DATABASE_URL=sqlite:///./crypto_platform.db

# CORS Settings
ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

### Docker Deployment

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "run.py"]
```

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  crypto-platform:
    build: .
    ports:
      - "8000:8000"
    environment:
      - HOST=0.0.0.0
      - PORT=8000
      - DEBUG=False
    volumes:
      - ./data:/app/data
    restart: unless-stopped
```

Deploy with Docker:

```bash
docker-compose up -d
```

### Cloud Deployment Options

#### 1. Heroku

```bash
# Install Heroku CLI
# Create Procfile
echo "web: python run.py" > Procfile

# Deploy
heroku create your-app-name
git push heroku main
```

#### 2. Railway

```bash
# Install Railway CLI
npm install -g @railway/cli

# Deploy
railway login
railway init
railway up
```

#### 3. DigitalOcean App Platform

1. Connect GitHub repository
2. Configure build settings:
   - Build Command: `pip install -r requirements.txt`
   - Run Command: `python run.py`
3. Set environment variables
4. Deploy

### Nginx Configuration (Optional)

For production with reverse proxy:

```nginx
server {
    listen 80;
    server_name yourdomain.com;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /static/ {
        alias /path/to/your/app/web/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

## Database Setup

### SQLite (Default)
- Automatically created on first run
- Located at `./crypto_platform.db`
- Perfect for development and small deployments

### PostgreSQL (Production)

1. **Install PostgreSQL**
2. **Create Database**
```sql
CREATE DATABASE crypto_platform;
CREATE USER crypto_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE crypto_platform TO crypto_user;
```

3. **Update Environment**
```env
DATABASE_URL=postgresql://crypto_user:your_password@localhost/crypto_platform
```

4. **Install PostgreSQL Driver**
```bash
pip install psycopg2-binary
```

## Performance Optimization

### Static File Serving

For production, serve static files with a CDN or web server:

```python
# In main.py, disable static file serving
# app.mount("/static", StaticFiles(directory="web/static"), name="static")
```

### Caching

Add Redis for session storage and caching:

```bash
pip install redis
```

```python
# Add to main.py
import redis
from starlette.middleware.sessions import SessionMiddleware

redis_client = redis.Redis(host='localhost', port=6379, db=0)
```

### Monitoring

Add application monitoring:

```bash
pip install prometheus-client
```

## Security Checklist

- [ ] Change default secret keys
- [ ] Enable HTTPS in production
- [ ] Configure CORS properly
- [ ] Set up rate limiting
- [ ] Enable security headers
- [ ] Regular security updates
- [ ] Database connection encryption
- [ ] Input validation and sanitization

## Troubleshooting

### Common Issues

1. **Port Already in Use**
```bash
# Find process using port 8000
lsof -i :8000
# Kill process
kill -9 <PID>
```

2. **Database Connection Issues**
```bash
# Check database file permissions
ls -la crypto_platform.db
# Reset database
rm crypto_platform.db
python main.py  # Will recreate
```

3. **Static Files Not Loading**
- Check file permissions
- Verify static file paths
- Clear browser cache

### Logs

Application logs are output to console. For production:

```python
import logging
logging.basicConfig(level=logging.INFO)
```

## Backup Strategy

### Database Backup

```bash
# SQLite
cp crypto_platform.db backup_$(date +%Y%m%d).db

# PostgreSQL
pg_dump crypto_platform > backup_$(date +%Y%m%d).sql
```

### Full Application Backup

```bash
tar -czf backup_$(date +%Y%m%d).tar.gz \
  --exclude='.venv' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  .
```

---

## Support

For deployment issues:
1. Check application logs
2. Verify environment variables
3. Test database connectivity
4. Confirm port availability
5. Review security settings

*Last Updated: September 9, 2025*
