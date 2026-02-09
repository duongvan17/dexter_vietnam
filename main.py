"""
Dexter Vietnam - AI Trading Assistant Entry Point
"""
import sys
import os

# Ensure parent dir is in path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dexter_vietnam.cli import main

if __name__ == "__main__":
    main()
