"""Entry point: build the unified dataset."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from crime_skelnet.config  import Config
from crime_skelnet.data    import build

if __name__ == "__main__":
    build(Config())