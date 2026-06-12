#!/usr/bin/env python3
"""
Script to download and organize the UCF-Crime dataset for the VideoMAE component.
"""

import os
import sys
import shutil
import urllib.request
import zipfile
from pathlib import Path
import argparse

# Official dataset link: https://www.crcv.ucf.edu/projects/real-world/
DROPBOX_URL = "https://www.dropbox.com/sh/75v5ehq4cdg5g5g/AABvnJSwZI7zXb8_myBA0CLHa?dl=1"

CRIME_CLASSES = [
    "Abuse", "Arrest", "Arson", "Assault", "Burglary", "Explosion",
    "Fighting", "RoadAccidents", "Robbery", "Shooting", "Shoplifting",
    "Stealing", "Vandalism"
]

def download_file(url: str, dest_path: Path):
    """Downloads a file with a progress bar."""
    print(f"Downloading from {url}...")
    try:
        def reporthook(count, block_size, total_size):
            if total_size > 0:
                percent = int(count * block_size * 100 / total_size)
                sys.stdout.write(f"\r...{min(percent, 100)}%")
                sys.stdout.flush()

        urllib.request.urlretrieve(url, dest_path, reporthook)
        print("\nDownload complete!")
    except Exception as e:
        print(f"\nError downloading dataset: {e}")
        print("Note: The UCF-Crime dataset is extremely large (>50GB).")
        print("If this download fails, please download the parts manually from:")
        print("https://www.dropbox.com/sh/75v5ehq4cdg5g5g/AABvnJSwZI7zXb8_myBA0CLHa?dl=0")
        print("and place them in the 'downloads' directory.")
        sys.exit(1)

def extract_archive(archive_path: Path, extract_to: Path):
    """Extracts zip archives to the destination."""
    print(f"Extracting {archive_path.name} to {extract_to}...")
    try:
        with zipfile.ZipFile(archive_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
        print("Extraction complete.")
    except zipfile.BadZipFile:
        print(f"Warning: {archive_path.name} is not a valid zip file. Skipping extraction.")

def organize_dataset(base_dir: Path, target_dir: Path):
    """
    Organizes the extracted raw videos into the structure expected by the pipeline:
      target_dir/
        train/
          normal/
          anomaly/
            Abuse/
            Robbery/
            ...
        test/
          normal/
          anomaly/
            Abuse/
            Robbery/
            ...
    
    Uses standard UCF-Crime naming conventions to infer split and class.
    """
    print(f"Organizing videos from {base_dir} to {target_dir}...")
    
    # Create target directories
    for split in ["train", "test"]:
        (target_dir / split / "normal").mkdir(parents=True, exist_ok=True)
        for crime in CRIME_CLASSES:
            (target_dir / split / "anomaly" / crime).mkdir(parents=True, exist_ok=True)

    # Move normal videos (These are usually prefixed with 'Normal' or found in specific normal folders)
    # The split designation for normal videos in UCF is typically done by the text splits,
    # but as a heuristic, videos named 'Normal_Videos...' or similar without crime keywords are Normal.
    
    video_files = list(base_dir.rglob("*.mp4"))
    
    if not video_files:
        print("No .mp4 files found in the extracted directory to organize.")
        return

    moved_count = 0
    for vid_path in video_files:
        vid_name = vid_path.name.lower()
        vid_parent = vid_path.parent.name.lower()
        
        # Determine if normal or anomaly
        is_normal = "normal" in vid_name or "normal" in vid_parent
        
        # Determine class for anomaly
        assigned_crime = None
        if not is_normal:
            for crime in CRIME_CLASSES:
                if crime.lower() in vid_name or crime.lower() in vid_parent:
                    assigned_crime = crime
                    break
        
        # Determine split (by default use Train if test is not explicitly stated in path,
        # but a robust implementation parses the split text files if available).
        split = "test" if "test" in str(vid_path).lower() else "train"
        
        # Determine destination
        if is_normal:
            dest = target_dir / split / "normal" / vid_path.name
        else:
            if assigned_crime is None:
                # Default fallback
                dest = target_dir / split / "anomaly" / "Abuse" / vid_path.name
            else:
                dest = target_dir / split / "anomaly" / assigned_crime / vid_path.name
                
        shutil.move(str(vid_path), str(dest))
        moved_count += 1

    print(f"Dataset organization complete. Moved {moved_count} videos.")

def main():
    parser = argparse.ArgumentParser(description="Download and extract the UCF-Crime dataset.")
    parser.add_argument("--data_dir", type=str, default="data/raw_videos", help="Output directory for raw videos.")
    parser.add_argument("--download_dir", type=str, default="data/downloads", help="Temporary directory for downloaded archives.")
    parser.add_argument("--skip_download", action="store_true", help="Skip download and only organize existing files in download_dir.")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent
    data_dir = project_root / args.data_dir
    download_dir = project_root / args.download_dir

    download_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    archive_path = download_dir / "ucf_crime_dataset.zip"

    if not args.skip_download:
        if not archive_path.exists():
            download_file(DROPBOX_URL, archive_path)
        else:
            print(f"Archive {archive_path.name} already exists. Skipping download.")

    # Extract all .zip files in the download directory
    for zip_file in download_dir.glob("*.zip"):
        extract_to = download_dir / zip_file.stem
        extract_archive(zip_file, extract_to)

    # Organize the extracted videos
    organize_dataset(download_dir, data_dir)
    print(f"Finished! Data is prepared at: {data_dir.resolve()}")

if __name__ == "__main__":
    main()
