"""Entry point: train CrimeSkelNet."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from crime_skelnet.config    import Config
from crime_skelnet.training  import trainer

if __name__ == "__main__":
    trainer.train(Config())