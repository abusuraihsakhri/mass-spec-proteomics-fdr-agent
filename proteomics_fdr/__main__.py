"""
Allow running proteomics_fdr package as a module: python -m proteomics_fdr
"""
from proteomics_fdr.cli import main
import sys

if __name__ == "__main__":
    sys.exit(main())
