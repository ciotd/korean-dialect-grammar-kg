"""Run from any working directory: python tools/run_kg_pipeline.py --help."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from kg_pipeline.runner import main
if __name__=='__main__':main()
