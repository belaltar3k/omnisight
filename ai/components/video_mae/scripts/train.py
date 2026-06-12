"""Entry point: train VideoMAE + CrimeTransformer."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from video_mae.config   import Config
from video_mae.training import train

if __name__ == "__main__":
    train(Config())