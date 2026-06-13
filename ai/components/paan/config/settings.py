from dataclasses import dataclass, field
from typing import List


@dataclass
class Config:
    # -- Audio preprocessing --------------------------------------------------
    sample_rate:     int   = 16000
    gunshot_sr:      int   = 8000
    gunshot_clip_s:  float = 4.0
    n_mels:          int   = 64
    n_fft:           int   = 512
    hop_length:      int   = 160

    # -- Stage 1: YAMNet (coarse filter) --------------------------------------
    yamnet_url:      str   = "https://tfhub.dev/google/yamnet/1"
    yamnet_thresh:   float = 0.0

    crime_keywords: List[str] = field(default_factory=lambda: [
        "gunshot", "gunfire", "explosion", "screaming",
        "shout", "breaking glass", "speech", "inside",
    ])

    # -- Stage 2: Swin gunshot classifier -------------------------------------
    gunshot_model:   str   = "ranvir-not-found/swin-wda_gunshot-detection"
    gunshot_thresh:  float = 0.7

    # -- Stage 3: FlexSED (semantic reasoning) --------------------------------
    flexsed_thresh:  float = 0.10
    flexsed_batch:   int   = 5

    surveillance_events: List[str] = field(default_factory=lambda: [
        "loud gunshot",
        "sound of a pistol or handgun firing",
        "automatic weapon or heavy machine gun firing continuously",
        "loud explosion or bomb blast",
        "sounds of a violent physical fight or brawl",
        "person screaming in terror, fear, or distress",
        "glass window breaking, shattering, or smashing violently",
        "police car siren sounding or wailing",
    ])

    # -- Misc -----------------------------------------------------------------
    device:          str   = "cuda"
