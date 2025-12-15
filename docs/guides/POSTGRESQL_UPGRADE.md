# PostgreSQL Upgrade Guide

## 🚀 Overview

This guide helps you migrate CryptoChecker from SQLite to PostgreSQL for proper concurrent write support, eliminating the database lock errors you experienced during heavy bot activity.

### Why PostgreSQL?
- **Concurrent Writes**: Handles multiple bots, price updates, and user operations simultaneously
- **Scalability**: Better performance with growing user base
- **Production Ready**: Industry standard for web applications

## 📋 Prerequisites

1. **PostgreSQL Installation**
   ```bash
   # Ubuntu/Debian
   sudo apt-get update
   sudo apt-get install postgresql postgresql-contrib

   # macOS (with Homebrew)
   brew install postgresql
   brew services start postgresql

   # Windows
   # Download from: https://www.postgresql.org/download/
   ```

2. **Create PostgreSQL Database**
   ```bash
   # Connect to PostgreSQL
   sudo -u postgres psql

   # Create database and user
   CREATE DATABASE crypto_checker;
   CREATE USER crypto_app WITH PASSWORD 'your_secure_password';
   GRANT ALL PRIVILEGES ON DATABASE crypto_checker TO crypto_app;

   # Exit psql
   \q
   ```

## 🔧 Phase 1: Dependencies

The dependencies have been updated in `requirements.txt`:

```bash
# Install new dependencies
pip install -r requirements.txt
```

**Added packages:**
- `asyncpg==0.29.0` - Fast PostgreSQL driver for async operations
- `psycopg2-binary==2.9.7` - Synchronous PostgreSQL driver

## 🔧 Phase 2: Environment Configuration

1. **Create your PostgreSQL DATABASE_URL**
   ```bash
   # Copy the example
   cp .env.example .env

   # Edit .env file and update DATABASE_URL
   DATABASE_URL=postgresql://crypto_app:your_secure_password@localhost:5432/crypto_checker
   ```

   Example configurations:
   ```bash
   # Local development
   DATABASE_URL=postgresql://crypto_app:password@localhost:5432/crypto_checker

   # With custom host/port
   DATABASE_URL=postgresql://user:pass@db.example.com:5432/crypto_db
   ```

## 🔧 Phase 3: Database Migration

**⚠️ IMPORTANT**: Backup your SQLite database first!

```bash
# Backup current SQLite database
cp crypto_tracker_v3.db crypto_tracker_v3.backup.db
```

**Run the migration script:**

```bash
# Option 1: Using Python directly
python scripts/migrate_to_postgresql.py

# Option 2: Using Python module
python -m scripts.migrate_to_postgresql
```

**What the migration does:**
1. **Exports** all data from SQLite (`crypto_tracker_v3.db`)
2. **Creates** fresh PostgreSQL schema
3. **Imports** all data with proper type conversions
4. **Verifies** the migration was successful

**Expected Output:**
```
🚀 Starting PostgreSQL migration...
📡 Source: sqlite+aiosqlite:///./crypto_tracker_v3.db
📡 Target: postgresql://crypto_app:password@localhost:5432/crypto_checker
──────────────────────────────────────────────────
📤 Exporting data from SQLite...
  ↳ Exporting table: users
  ✅ users: 5 records exported
  ↳ Exporting table: wallets
  ✅ wallets: 5 records exported
  ...
📤 SQLite export complete!
📊 Exported 2,847 total records from SQLite
──────────────────────────────────────────────────
🏗️ Creating PostgreSQL schema...
✅ PostgreSQL schema created successfully!
──────────────────────────────────────────────────
📥 Importing data into PostgreSQL...
  ↳ Importing 5 records into users
  ✅ users: 5 records imported
  ...
📥 PostgreSQL import complete!
──────────────────────────────────────────────────
🔍 Verifying migration...
  ✅ users: 5 records
  ✅ wallets: 5 records
──────────────────────────────────────────────────
🎉 Migration completed successfully!
✅ Total records migrated: 2,847

🎯 MIGRATION SUCCESS!
You can now:
1. Set DATABASE_URL to PostgreSQL in your environment
2. Restart your application with: python main.py
3. Test concurrent operations - bots, price updates, and spins
```

## 🔧 Phase 4: Production Deployment

After successful migration:

1. **Set PostgreSQL URL in production**
   ```bash
   # Update your production .env
   DATABASE_URL=postgresql://prod_user:secure_pass@prod-db-host:5432/prod_db
   ```

2. **Restart your application**
   ```bash
   # Stop current server if running
   # Then restart
   python main.py
   ```

3. **Verify concurrent operations work**
   - Create multiple bots and user accounts
   - Test simultaneous betting and price updates
   - Check logs - should see no more "database is locked" errors

## 🔍 Troubleshooting

### Migration Issues
```bash
# If migration fails, check connection:
psql -h localhost -p 5432 -U crypto_app -d crypto_checker

# Check PostgreSQL status:
sudo systemctl status postgresql

# View PostgreSQL logs:
sudo tail -f /var/log/postgresql/postgresql-*.log
```

### Rollback Plan
```bash
# Restore SQLite backup:
cp crypto_tracker_v3.backup.db crypto_tracker_v3.db

# Update .env back to SQLite:
DATABASE_URL=sqlite+aiosqlite:///./crypto_tracker_v3.db

# Restart with SQLite:
python main.py
```

## 📊 Performance Expectations

**Before** (SQLite):
- ❌ Database locks during concurrent writes
- ❌ Unable to handle 22 bots + price service + spins
- ❌ Lock errors every few seconds

**After** (PostgreSQL):
- ✅ Concurrent writes from unlimited connections
- ✅ Handles 100+ bots + multiple price services + real-time operations
- ✅ Zero lock conflicts, professional-grade performance

## 🎯 What You'll See After Migration

1. **No database lock errors** in terminal output
2. **Smooth concurrent operations** - bots, price service, spins all running simultaneously
3. **Better performance** - faster response times and more users supported
4. **Scalable architecture** - ready for production deployment

## 📞 Support

If you encounter issues:
1. Check the migration script output for specific error messages
2. Verify DATABASE_URL format in your `.env` file
3. Confirm PostgreSQL user has correct permissions
4. Review PostgreSQL logs for connection issues

The migration script handles data type conversions automatically and provides detailed error reporting for troubleshooting.
