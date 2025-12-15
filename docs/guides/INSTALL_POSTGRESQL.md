# PostgreSQL Installation Guide

## 🖥️ Windows Installation

### Step 1: Download PostgreSQL
1. Visit: https://www.postgresql.org/download/windows/
2. Click **"Download the installer"**
3. Choose **"Windows x86-64"** and download the latest version (15.x or 16.x recommended)

### Step 2: Run Installer
1. Run the downloaded `.exe` file as Administrator
2. Choose installation directory (default is fine)
3. Select components to install:
   - ✅ PostgreSQL Server
   - ✅ pgAdmin 4 (graphical interface)
   - ✅ Command Line Tools
   - ✅ Stack Builder (optional)

### Step 3: Configure Setup
1. **Password**: Set a strong password for the PostgreSQL superuser (`postgres`)
2. **Port**: Keep default port `5432`
3. **Locale**: Choose `English, United States` or your preferred locale

### Step 4: Verify Installation
```powershell
# Open Command Prompt as Administrator
# Test PostgreSQL connection
psql -U postgres -h localhost

# Should show PostgreSQL prompt:
# postgres=#
```

---

## 🍎 macOS Installation (with Homebrew)

### Step 1: Install Homebrew (if not installed)
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### Step 2: Install PostgreSQL
```bash
# Install PostgreSQL
brew install postgresql

# Start PostgreSQL service
brew services start postgresql
```

### Step 3: Initialize Database (if needed)
```bash
# Initialize PostgreSQL (usually done automatically by brew)
initdb /usr/local/var/postgres

# Or try starting psql directly
createdb
```

### Step 4: Set Up Password
```bash
# Access PostgreSQL as superuser
psql postgres

# Inside psql, set password:
postgres=# \password postgres
# Enter your password when prompted

# Exit psql
postgres=# \q
```

### Step 5: Verify Installation
```bash
# Test connection
psql -U postgres -h localhost

# Should show PostgreSQL prompt:
# postgres=#
```

---

## 🐧 Ubuntu/Debian Linux Installation

### Step 1: Update Package Lists
```bash
sudo apt update
```

### Step 2: Install PostgreSQL and pgAdmin
```bash
# Install PostgreSQL
sudo apt install postgresql postgresql-contrib

# Optional: Install pgAdmin (graphical interface)
sudo apt install pgadmin4 pgadmin4-apache2
```

### Step 3: Enable and Start Service
```bash
# Enable PostgreSQL to start on boot
sudo systemctl enable postgresql

# Start PostgreSQL service
sudo systemctl start postgresql

# Check status
sudo systemctl status postgresql
```

### Step 4: Set Up Database User
```bash
# Switch to postgres user
sudo -u postgres psql

# Inside psql, create user and database:
postgres=# CREATE USER postgres WITH PASSWORD 'your_secure_password';
postgres=# ALTER USER postgres CREATEDB;
postgres=# \q
```

### Step 5: Configure PostgreSQL (Optional)
```bash
# Edit pg_hba.conf for local connections
sudo nano /etc/postgresql/15/main/pg_hba.conf

# Add this line for local md5 authentication:
# local   all             postgres                                md5

# Restart PostgreSQL
sudo systemctl restart postgresql
```

### Step 6: Verify Installation
```bash
# Test connection
sudo -u postgres psql

# Should show PostgreSQL prompt:
# postgres=#
```

---

## 🚀 Database Setup & User Creation

### Step 1: Connect to PostgreSQL
```bash
# Windows (PowerShell/Command Prompt)
psql -U postgres -h localhost

# macOS/Linux
psql -U postgres
```

### Step 2: Create Database and User
```sql
-- In PostgreSQL console:

-- Create database for CryptoChecker
CREATE DATABASE crypto_checker;

-- Create application user with password
CREATE USER crypto_app WITH PASSWORD 'your_secure_password_here';

-- Grant all privileges on the database
GRANT ALL PRIVILEGES ON DATABASE crypto_checker TO crypto_app;

-- Set default connection limit
ALTER USER crypto_app CONNECTION LIMIT 100;

-- List databases to verify
\l

-- Quit PostgreSQL
\q
```

### Step 3: Test Connection as Application User
```bash
# Test connection with application user
psql -U crypto_app -d crypto_checker -h localhost

# Inside psql:
crypto_checker=> \dt  -- Should show no tables yet
crypto_checker=> \q
```

---

## 🔧 Environment Configuration

### Step 1: Set DATABASE_URL in Your Project
```bash
# Copy environment template
cp .env.example .env

# Edit .env file
nano .env  # or use your preferred editor
```

**Add/Edit this line in `.env`:**
```bash
# PostgreSQL URL Format:
DATABASE_URL=postgresql://crypto_app:your_secure_password_here@localhost:5432/crypto_checker

# Examples:
# Local development
DATABASE_URL=postgresql://crypto_app:secret123@localhost:5432/crypto_checker

# Remote server
DATABASE_URL=postgresql://crypto_app:password@your-server.com:5432/crypto_checker

# With custom port
DATABASE_URL=postgresql://crypto_app:password@localhost:5532/crypto_checker
```

### Step 2: Test Connection from Python
```bash
# Test database connection
python -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL')

async def test_connection():
    engine = create_async_engine(DATABASE_URL, echo=True)
    try:
        async with engine.connect() as conn:
            result = await conn.execute('SELECT version()')
            version = result.scalar()
            print('✅ PostgreSQL connection successful!')
            print(f'Version: {version}')
    except Exception as e:
        print(f'❌ Connection failed: {e}')
    finally:
        await engine.dispose()

asyncio.run(test_connection())
"
```

---

## 🔍 Troubleshooting Common Issues

### Issue: "Connection refused"
**Cause**: PostgreSQL service not running
**Solution**:
```bash
# Windows
# Start from Services panel or:
net start postgresql-x64-15

# macOS
brew services start postgresql

# Linux
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### Issue: "Authentication failed"
**Cause**: Wrong password or authentication method
**Solution**:
```bash
# Reset postgres password:
psql -U postgres
\password postgres
# Enter new password...

# Or check pg_hba.conf authentication method
```

### Issue: "Database does not exist"
**Cause**: Database not created yet
**Solution**:
```bash
psql -U postgres
CREATE DATABASE crypto_checker;
GRANT ALL PRIVILEGES ON DATABASE crypto_checker TO crypto_app;
\q
```

### Issue: "psql: command not found"
**Cause**: PATH not configured correctly
**Windows Solution**:
```powershell
# Add PostgreSQL bin directory to PATH
# Usually: C:\Program Files\PostgreSQL\15\bin
# Or: C:\Program Files\PostgreSQL\16\bin

# Verify in new terminal:
psql --version
```

### Issue: Port 5432 in use
**Solution**: Find and stop conflicting service, or configure different port

---

## 📊 Post-Installation Verification

### 1. Check PostgreSQL Version
```bash
psql --version
# Should show: PostgreSQL 15.x.x or 16.x.x
```

### 2. Check Running Services
```bash
# Windows
psql -U postgres -c "SELECT version();"

# macOS/Linux
sudo -u postgres psql -c "SELECT version();"
```

### 3. Check Database Contents
```bash
psql -U crypto_app -d crypto_checker -c "SELECT current_database(), current_user, version();"
```

### 4. Check Connections
```bash
# Active connections
psql -U postgres -c "SELECT datname, usename, client_addr, state FROM pg_stat_activity;"
```

---

## 🎯 Next Steps After Installation

1. **Install Python Dependencies**
```bash
pip install -r requirements.txt
```

2. **Run Database Migration**
```bash
python scripts/migrate_to_postgresql.py
```

3. **Start Application**
```bash
python main.py
```

4. **Test Concurrent Operations**
- Check that bots can place bets simultaneously
- Verify price service runs without locks
- Confirm multiple spins can happen concurrently

---

## ⚡ Quick Setup Script (Optional)

For **Ubuntu/Debian** users, here's a complete setup script:

```bash
#!/bin/bash

# PostgreSQL Quick Setup Script
# Run with: chmod +x setup_postgres.sh && ./setup_postgres.sh

echo "🚀 Setting up PostgreSQL for CryptoChecker..."

# Install PostgreSQL
sudo apt update
sudo apt install -y postgresql postgresql-contrib

# Start service
sudo systemctl enable postgresql
sudo systemctl start postgresql

# Setup database and user
sudo -u postgres psql << EOF
CREATE DATABASE crypto_checker;
CREATE USER crypto_app WITH PASSWORD 'secure_password_123';
GRANT ALL PRIVILEGES ON DATABASE crypto_checker TO crypto_app;
ALTER USER crypto_app CONNECTION LIMIT 100;
EOF

echo "✅ PostgreSQL setup complete!"
echo "You can now run: python scripts/migrate_to_postgresql.py"
```

---

## 📚 Additional Resources

- **PostgreSQL Official Documentation**: https://www.postgresql.org/docs/
- **pgAdmin Setup Guide**: https://www.pgadmin.org/docs/pgadmin4/latest/index.html
- **Connection String Documentation**: https://www.postgresql.org/docs/current/libpq-connect.html

Need help with any step? Just let me know your operating system and the specific error you're encountering.
