# Database Reset (Development Only)

This document explains how to reset the local development database for Version3.

WARNING: This script drops and recreates all tables in the configured `DATABASE_URL`. Only run in local development environments.

Usage

1. Activate your virtual environment (Windows PowerShell):

   ```powershell
   & .\.venv\Scripts\Activate.ps1
   cd Version3
   python scripts/reset_db.py
   ```

2. The script will drop all tables, recreate them, and re-seed default data.

Notes

- In production, use a proper migration tool (Alembic) instead of this script.
- After running this, local data will be lost and recreated.
