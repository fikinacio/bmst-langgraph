"""Pytest configuration — sets fake env vars before any module imports settings.

src/config/settings.py creates a module-level Settings() instance that fails
with ValidationError if required vars are missing. This file runs before any
test collection, so the env vars are in place when settings is imported.
"""

import os

# Required by Settings — values are fakes that don't hit any real service
_TEST_ENV = {
    "ANTHROPIC_API_KEY": "test-anthropic-key",
    "BMST_API_KEY": "test-bmst-key",
    "SUPABASE_URL": "https://test.supabase.co",
    "SUPABASE_SERVICE_KEY": "test-supabase-service-key",
    "EVOLUTION_API_URL": "http://test-evolution:8080",
    "EVOLUTION_API_KEY": "test-evolution-key",
    "EVOLUTION_INSTANCE": "test-instance",
    "REVISOR_APPROVER_PHONE": "+41795748225",
    "REDIS_URL": "redis://localhost:6379",
}

for key, value in _TEST_ENV.items():
    os.environ.setdefault(key, value)
