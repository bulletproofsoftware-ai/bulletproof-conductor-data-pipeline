"""Root conftest.py -- ensure project root is on sys.path.

The masking_engine package (with underscores) is a normal Python
package that can be imported directly.
"""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent

# Ensure project root is in sys.path
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
