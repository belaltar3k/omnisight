# Weapon Detection Dataset — Phase 1: Unification Pipeline

## Goal
Convert all 12 datasets from their various formats into a single unified YOLO dataset:
```
/data/datasets/unified/
  train/images/   train/labels/
  val/images/     val/labels/
  test/images/    test/labels/
  data.yaml
```
Single class: `0 = weapon`

---

## Prerequisites

```bash
pip install boto3 opencv-python-headless Pillow tqdm numpy scipy
```

Set your AWS credentials before running anything:
```bash
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_DEFAULT_REGION=your_region   # e.g. us-east-1
```

Set your bucket name:
```bash
export S3_BUCKET=omnisharp-fcds
```

---

## Execution Order

Run these scripts **in order**. Each is safe to re-run (idempotent).

### Step 1 — Create output directory structure
```bash
python scripts/00_create_dirs.py
```

### Step 2 — Convert & copy each dataset
Run each converter. They all write into `/data/datasets/unified/staging/<dataset_name>/`
then register entries into a manifest CSV.

```bash
# Dataset 1: weapon_dataset1_cctv_weapon (YOLO, person+weapon → weapon only)
python converters/ds1_cctv_weapon.py

# Dataset 2: normal_dataset2_umbrellas (YOLO, weapon+umbrella → weapon only, umbrella-only → hard neg)
python converters/ds2_umbrellas.py

# Dataset 3: normal_dataset3_virat (raw videos → negative frames)
python converters/ds3_virat.py

# Dataset 4: weapon_dataset5_ninja (Supervisely JSON → YOLO)
python converters/ds5_ninja.py

# Dataset 5: weapon_dataset6_CCTV_Gun UCF only (COCO JSON → YOLO)
python converters/ds6_ucf.py

# Dataset 6: weapon_dataset8_roboflow (YOLO, 1 class → weapon)
python converters/ds8_roboflow.py

# Dataset 7: weapon_dataset9_roboflow (YOLO, 1 class → weapon, no val/test → split)
python converters/ds9_roboflow.py

# Dataset 8: weapon_dataset10_roboflow (YOLO, 2 classes → weapon only, drop class 0)
python converters/ds10_roboflow.py

# Dataset 9: HARIS_Weapon_Detection_Dataset (YOLO, gun+knife → weapon = class 0)
python converters/ds11_haris.py

# Dataset 10: Weapon_Detection_for_Yolo (YOLO, already weapon → direct copy)
python converters/ds12_weapon_yolo.py

# Dataset 11: UCFDataset normal videos → negatives
python converters/ds13_ucf_normal.py

# Dataset 12: normal_dataset1_mall frames → negatives
python converters/ds_mall_negatives.py
```

### Step 3 — Merge staging into final train/val/test
```bash
python scripts/01_merge_splits.py
```

### Step 4 — Validate the final dataset
```bash
python scripts/02_validate_dataset.py
```

### Step 5 — Print final statistics
```bash
python scripts/03_stats.py
```

---

## Split Strategy

| Split | Source | Rationale |
|-------|--------|-----------|
| **test** | weapon_dataset6_CCTV_Gun UCF only | Real CCTV, never seen in train, held-out domain |
| **val**  | HARIS val/ + ds8_roboflow val/ | Different source from train |
| **train**| Everything else | All remaining positives + negatives |

This ensures test metrics are **honest** — different domain from training data.

---

## Class Mapping (all datasets → class 0 = weapon)

| Dataset | Original classes | Action |
|---------|-----------------|--------|
| ds1_cctv_weapon | 0=person, 1=weapon | Keep only class 1 → remap to 0 |
| ds2_umbrellas | 0=person, 1=weapon, 2=umbrella | Keep class 1 → remap to 0; umbrella-only images → empty labels (hard neg) |
| ds3_virat | none (videos) | Extract frames → empty labels |
| ds5_ninja | weapon (Supervisely) | Convert bbox → class 0 |
| ds6_ucf | COCO handgun | Keep weapon boxes → class 0 |
| ds8_roboflow | 0=Weapon | Remap 0→0 (direct) |
| ds9_roboflow | 0=Gun | Remap 0→0 (direct) |
| ds10_roboflow | 0='0', 1=weapons | Keep class 1 → remap to 0; drop class 0 |
| ds11_haris | 0=gun, 1=knife | Both → remap to 0 |
| ds12_weapon_yolo | 0=Weapon | Direct copy |
| ds13_ucf_normal | none (videos) | Extract frames → empty labels |
| mall | none (frames) | Empty labels |

---

## Output Structure

```
/data/datasets/unified/
├── data.yaml
├── train/
│   ├── images/   (jpg/png)
│   └── labels/   (txt, YOLO format, class 0 only)
├── val/
│   ├── images/
│   └── labels/
└── test/
    ├── images/
    └── labels/
```

**Label format** (YOLO normalized):
```
0 cx cy w h
0 cx cy w h
```
Empty `.txt` = negative image (no weapons).
