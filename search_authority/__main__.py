"""Allow running as python -m search_authority."""
from .cli import main
import sys

sys.exit(main() or 0)
