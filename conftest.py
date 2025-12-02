"""Pytest configuration file."""

import sys
from pathlib import Path

# Ensure the project root is in the path for imports
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
