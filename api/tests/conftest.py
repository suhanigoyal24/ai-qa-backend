#conftest.py
import os
import django
import pytest
from django.conf import settings

# Set Django settings BEFORE importing anything else
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

@pytest.fixture(autouse=True)
def setup_django():
    """Auto-setup Django for all tests"""
    if not settings.configured:
        django.setup()