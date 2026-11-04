import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'local/python'),str(ROOT/'src')]
from kg_runtime.card_experiment import main
if __name__=='__main__':main()
