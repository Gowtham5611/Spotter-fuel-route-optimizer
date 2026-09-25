#!/usr/bin/env python
"""
Standalone script to import fuel prices from CSV into SQLite DB.
Equivalent to running: python manage.py import_fuel_prices
"""

import os
import sys
from pathlib import Path

# Ensure backend root is on sys.path and DJANGO_SETTINGS_MODULE is set
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()

from django.core.management import call_command

if __name__ == "__main__":
    print("Executing import_fuel_prices management command...")
    call_command("import_fuel_prices")
