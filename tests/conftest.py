"""
Test configuration for pytest.
This file ensures proper path setup and shared fixtures for all tests.
"""
import os
import sys
from pathlib import Path

# Add the parent directory to sys.path to make the self-promise package importable
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import shared fixtures here if needed
