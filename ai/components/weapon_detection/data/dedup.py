"""
phase2/dedup.py

Perceptual hash deduplication for the unified weapon dataset.

Strategy:
  1. Compute pHash (64-bit) for every image in train/val/test
  2. Build a BK-tree for fast Hamming-distance search
  3. Find all pairs with hamming_distance <= THRESHOLD (default 8)
  4. Within each duplicate cluster:
       - ALWAYS keep test images (never delete test)
       - ALWAYS keep val images over train images
       - Within train: keep the one with the most weapon boxes
         (prefer informative positives over negatives)
  5. Hard-delete duplicates from disk (image + label)
  6. Write a dedup report

Why pHash + BK-tree:
  - pHash is robust to JPEG re-compression, slight resize, brightness shifts
    (all common across Roboflow re-exports of the same source image)
  - BK-tree gives O(log N) neighbor search vs O(N²) brute force
  - At threshold=8 out of 64 bits: ~12.5% bit tolerance → catches near-dupes
    without false-positiving on visually similar but different scenes

Expected duplicate rate: 15–35% given Roboflow re-export overlap
"""

import sys
import struct
import hashlib
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple, Optional
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data.utils import log, BASE_OUT, SPLITS, read_yolo_label

try:
    from PIL import Image
    import numpy as np
except ImportError:
    raise SystemExit("pip install Pillow numpy")

# ── Config ────────────────────────────────────────────────────────────────────
HASH_SIZE  = 8          # pHash grid: 8×8 = 64 bits
THRESHOLD  = 8          # max Hamming distance to consider duplicate (out of 64)
IMAGE_EXTS = {".jpg", ".jpeg", ".png"}

# Split priority (higher = keep over lower)
SPLIT_PRIORITY = {"test": 3, "val": 2, "train": 1}


# ── pHash implementation (no imagehash dependency needed) ─────────────────────

def phash(img_path: Path, hash_size: int = 8) -> Optional[int]:
    """
    Compute perceptual hash (pHash) as a 64-bit integer.
    Algorithm: DCT-based — resize to (hash_size*4 x hash_size*4),
    compute DCT, take top-left hash_size² coefficients, threshold at median.
    """
    try:
        with Image.open(img_path) as img:
            img = img.convert("L").resize(
                (hash_size * 4, hash_size * 4), Image.LANCZOS
            )
            pixels = np.array(img, dtype=float)
    except Exception:
        return None

    # 2D DCT via separable 1D DCTs
    dct = _dct2(pixels)
    dct_low = dct[:hash_size, :hash_size]
    # Exclude DC component (top-left) from median
    med = np.median(dct_low[1:] if dct_low.size > 1 else dct_low)
    bits = (dct_low > med).flatten()

    # Pack 64 bits into a Python int
    h = 0
    for bit in bits:
        h = (h << 1) | int(bit)
    return h


def _dct2(a: np.ndarray) -> np.ndarray:
    """2D DCT-II via scipy if available, else numpy fallback."""
    try:
        from scipy.fft import dct
        return dct(dct(a, axis=0, norm="ortho"), axis=1, norm="ortho")
    except ImportError:
        # Numpy fallback (slower but no scipy dependency)
        N = a.shape[0]
        M = a.shape[1]
        result = np.zeros_like(a)
        for u in range(N):
            for v in range(M):
                result[u, v] = np.sum(
                    a * np.cos(np.pi * u * (2 * np.arange(N)[:, None] + 1) / (2 * N))
                      * np.cos(np.pi * v * (2 * np.arange(M)[None, :] + 1) / (2 * M))
                )
        return result


def hamming_distance(a: int, b: int) -> int:
    """Number of differing bits between two 64-bit integers."""
    return bin(a ^ b).count("1")


# ── BK-Tree for fast nearest-neighbor search ──────────────────────────────────

class BKTree:
    """
    Burkhard-Keller tree for Hamming distance metric.
    Allows finding all items within distance d of a query in O(log N) avg.
    """
    def __init__(self):
        self.root = None  # (hash_value, item_id, children_dict)

    def add(self, hash_val: int, item_id: int):
        if self.root is None:
            self.root = [hash_val, item_id, {}]
            return
        node = self.root
        while True:
            d = hamming_distance(hash_val, node[0])
            if d == 0:
                return  # exact duplicate hash, skip
            if d not in node[2]:
                node[2][d] = [hash_val, item_id, {}]
                return
            node = node[2][d]

    def search(self, hash_val: int, max_dist: int) -> List[Tuple[int, int]]:
        """Return [(distance, item_id)] for all items within max_dist."""
        if self.root is None:
            return []
        results = []
        stack = [self.root]
        while stack:
            node = stack.pop()
            d = hamming_distance(hash_val, node[0])
            if d <= max_dist:
                results.append((d, node[1]))
            # Search children with distance in [d-max_dist, d+max_dist]
            for child_d, child in node[2].items():
                if abs(child_d - d) <= max_dist:
                    stack.append(child)
        return results


# ── Union-Find for clustering duplicates ──────────────────────────────────────

class UnionFind:
    def __init__(self, n):
        self.parent = list(range(n))
        self.rank   = [0] * n

    def find(self, x):
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, x, y):
        rx, ry = self.find(x), self.find(y)
        if rx == ry:
            return
        if self.rank[rx] < self.rank[ry]:
            rx, ry = ry, rx
        self.parent[ry] = rx
        if self.rank[rx] == self.rank[ry]:
            self.rank[rx] += 1


# ── Main deduplication logic ───────────────────────────────────────────────────

def count_weapon_boxes(img_path: Path) -> int:
    """Count number of weapon bounding boxes for this image."""
    split = img_path.parts[-3]          # .../train/images/file.jpg
    lbl_path = BASE_OUT / split / "labels" / (img_path.stem + ".txt")
    if not lbl_path.exists():
        return 0
    return len(read_yolo_label(lbl_path))


def keep_score(img_path: Path) -> Tuple[int, int]:
    """
    Score used to decide which image to keep in a duplicate cluster.
    Higher = better to keep.
    Returns (split_priority, n_weapon_boxes)
    Tuples compare lexicographically → split priority first, then box count.
    """
    split = img_path.parts[-3]
    return (SPLIT_PRIORITY.get(split, 0), count_weapon_boxes(img_path))


def run_deduplication(dry_run: bool = False) -> dict:
    """
    Main dedup entry point.
    dry_run=True: only report, don't delete anything.
    Returns stats dict.
    """
    # ── 1. Collect all images ────────────────────────────────────────────────
    log.info("Collecting all images...")
    all_images: List[Path] = []
    for split in SPLITS:
        img_dir = BASE_OUT / split / "images"
        if img_dir.exists():
            imgs = [f for f in img_dir.glob("*.*") if f.suffix.lower() in IMAGE_EXTS]
            all_images.extend(imgs)
            log.info(f"  {split}: {len(imgs)} images")

    log.info(f"  Total: {len(all_images)} images")

    # ── 2. Compute pHashes ───────────────────────────────────────────────────
    log.info("Computing perceptual hashes (pHash 8x8)...")
    hashes: Dict[int, int] = {}   # idx → hash value
    failed = []

    for idx, img_path in enumerate(tqdm(all_images, desc="Hashing", unit="img")):
        h = phash(img_path)
        if h is None:
            failed.append(img_path)
            log.warning(f"  Failed to hash: {img_path.name}")
        else:
            hashes[idx] = h

    log.info(f"  Hashed: {len(hashes)} | Failed: {len(failed)}")

    # ── 3. Build BK-tree and find duplicates ─────────────────────────────────
    log.info(f"Building BK-tree and finding duplicates (threshold={THRESHOLD})...")
    tree = BKTree()
    idx_list = sorted(hashes.keys())

    for idx in tqdm(idx_list, desc="Building BK-tree", unit="node"):
        tree.add(hashes[idx], idx)

    # Find duplicate pairs
    duplicate_pairs = set()
    for idx in tqdm(idx_list, desc="Searching duplicates", unit="query"):
        neighbors = tree.search(hashes[idx], THRESHOLD)
        for dist, neighbor_idx in neighbors:
            if neighbor_idx != idx:
                pair = (min(idx, neighbor_idx), max(idx, neighbor_idx))
                duplicate_pairs.add(pair)

    log.info(f"  Found {len(duplicate_pairs)} duplicate pairs")

    # ── 4. Cluster duplicates with Union-Find ────────────────────────────────
    uf = UnionFind(len(all_images))
    for a, b in duplicate_pairs:
        uf.union(a, b)

    # Group by cluster root
    clusters: Dict[int, List[int]] = defaultdict(list)
    for idx in idx_list:
        root = uf.find(idx)
        clusters[root].append(idx)

    # Only keep clusters with >1 member
    dup_clusters = {r: members for r, members in clusters.items() if len(members) > 1}
    log.info(f"  {len(dup_clusters)} duplicate clusters")

    # ── 5. Decide what to keep/delete ────────────────────────────────────────
    log.info("Selecting survivors (keep best per cluster)...")
    to_delete: List[Path] = []
    to_keep:   List[Path] = []

    for root, members in dup_clusters.items():
        member_paths = [all_images[i] for i in members]

        # Sort by score descending — best candidate first
        member_paths.sort(key=keep_score, reverse=True)

        survivor = member_paths[0]
        to_keep.append(survivor)

        for duplicate in member_paths[1:]:
            # Never delete test images — safety guardrail
            if duplicate.parts[-3] == "test":
                log.warning(
                    f"  Would delete TEST image {duplicate.name} "
                    f"(dup of {survivor.name}) — SKIPPING for safety"
                )
                to_keep.append(duplicate)
            else:
                to_delete.append(duplicate)

    # ── 6. Delete duplicates ─────────────────────────────────────────────────
    n_deleted_img = 0
    n_deleted_lbl = 0

    if not dry_run:
        log.info(f"Deleting {len(to_delete)} duplicate images...")
        for img_path in tqdm(to_delete, desc="Deleting", unit="file"):
            split = img_path.parts[-3]
            lbl_path = BASE_OUT / split / "labels" / (img_path.stem + ".txt")

            if img_path.exists():
                img_path.unlink()
                n_deleted_img += 1
            if lbl_path.exists():
                lbl_path.unlink()
                n_deleted_lbl += 1
    else:
        log.info(f"[DRY RUN] Would delete {len(to_delete)} duplicate images")
        n_deleted_img = len(to_delete)
        n_deleted_lbl = len(to_delete)

    stats = {
        "total_images":    len(all_images),
        "hash_failures":   len(failed),
        "duplicate_pairs": len(duplicate_pairs),
        "dup_clusters":    len(dup_clusters),
        "deleted":         n_deleted_img,
        "remaining":       len(all_images) - n_deleted_img,
        "dup_rate_pct":    round(n_deleted_img / max(len(all_images), 1) * 100, 1),
    }

    return stats
