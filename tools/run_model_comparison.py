"""Entry point. freeze/preflight are offline; run requires --execute."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from kg_pipeline.model_comparison import main
if __name__=='__main__': main()
