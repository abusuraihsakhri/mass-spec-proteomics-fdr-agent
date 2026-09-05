"""
Pytest configuration for mass-spec-proteomics-fdr-agent test suite.
Sets required environment variables for cryptographic operations.
"""
import os
import sys
from pathlib import Path

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set a test-only audit secret key (never use in production)
os.environ.setdefault("AUDIT_SECRET_KEY", "test-only-audit-secret-key-2026-fdr-agent")
