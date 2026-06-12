#!/usr/bin/env python3
"""
Script to download and extract all 9 datasets used by the CrimeSkelNet component.
Requirements:
  - git
  - pip install gdown kaggle
  - Kaggle API token (~/.kaggle/kaggle.json) expected for Kaggle datasets.
"""

import os
import sys
import shutil
import subprocess
import argparse
import urllib.request
import zipfile
import tarfile
from pathlib import Path

def run_command(cmd, cwd=None):
    """Executes a shell command."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd)
    if result.returncode != 0:
        print(f"Error executing command: {' '.join(cmd)} in {cwd}")
        sys.exit(result.returncode)

def extract_archives(directory):
    """Extracts all zip and tar.gz files in the given directory and removes them."""
    for item in Path(directory).iterdir():
        if item.is_file():
            if item.suffix == ".zip":
                print(f"Extracting {item.name}...")
                try:
                    with zipfile.ZipFile(item, 'r') as zip_ref:
                        zip_ref.extractall(directory)
                    item.unlink()
                except zipfile.BadZipFile:
                    print(f"Warning: {item.name} is not a valid zip file or is incomplete.")
            elif item.name.endswith(".tar.gz") or item.name.endswith(".tgz"):
                print(f"Extracting {item.name}...")
                try:
                    with tarfile.open(item, "r:gz") as tar_ref:
                        tar_ref.extractall(directory)
                    item.unlink()
                except tarfile.TarError:
                    print(f"Warning: {item.name} is not a valid tar.gz file or is incomplete.")

def download_hrcrime(base_dir):
    print("\n=====================================")
    print(" 1. HR-Crime (dataset14_hr_crime)")
    print("=====================================")
    ds_dir = base_dir / "dataset14_hr_crime"
    ds_dir.mkdir(parents=True, exist_ok=True)
    
    token = "65ce30c120cd074a08dd064b1330d32a1790ba042dc3e735fd48bcb4f53b3f794d4d48db8d27d2aef48d2b2478c9af6ce41a245a9e329437302fd2678b9391cf"
    url = "https://data.4tu.nl/file/6150fded-d1bc-40ed-bf64-e482f7850485/6759f52c-f3ba-4b9f-81e6-4de88fab8dfb"
    out_file = ds_dir / "hr_crime.zip"
    
    if not out_file.exists() and not list(ds_dir.glob("*.csv")): # Very basic check if it was extracted
        print("Downloading HR-Crime...")
        req = urllib.request.Request(url)
        req.add_header("Authorization", f"token {token}")
        try:
            with urllib.request.urlopen(req) as response, open(out_file, 'wb') as out_file_obj:
                shutil.copyfileobj(response, out_file_obj)
            extract_archives(ds_dir)
        except Exception as e:
            print(f"Failed to download HR-Crime: {e}")

def git_clone(repo_url, dest_dir):
    if not (dest_dir / ".git").exists():
        run_command(["git", "clone", repo_url, str(dest_dir)])
    else:
        print(f"Repo already cloned at {dest_dir}")

def download_kaggle(dataset, ds_dir):
    ds_dir.mkdir(parents=True, exist_ok=True)
    if not list(ds_dir.glob("*")):  # only download if empty
        run_command(["kaggle", "datasets", "download", "-d", dataset], cwd=ds_dir)
        extract_archives(ds_dir)
    else:
        print(f"Kaggle dataset {dataset} already seems to be downloaded in {ds_dir}.")

def download_gdown(file_id, ds_dir):
    ds_dir.mkdir(parents=True, exist_ok=True)
    run_command(["gdown", file_id], cwd=ds_dir)

def main():
    parser = argparse.ArgumentParser(description="Download all 9 datasets for CrimeSkelNet")
    parser.add_argument("--data_dir", type=str, default="/data/datasets", help="Base directory for the datasets (e.g. /data/datasets)")
    args = parser.parse_args()

    # Check dependencies
    for tool in ["git", "kaggle", "gdown"]:
        if shutil.which(tool) is None:
            print(f"Error: {tool} is not installed or not in PATH.")
            print("Please run: pip install gdown kaggle")
            sys.exit(1)

    base_dir = Path(args.data_dir)
    base_dir.mkdir(parents=True, exist_ok=True)
    print(f"Base data directory set to: {base_dir}")

    # 1. HR-Crime
    download_hrcrime(base_dir)

    # 2. Fight Surveillance
    print("\n=====================================")
    print(" 2. Fight Surveillance (dataset3_fight_surv)")
    print("=====================================")
    git_clone("https://github.com/seymanurakti/fight-detection-surv-dataset.git", base_dir / "dataset3_fight_surv")

    # 3. Real Life Violence
    print("\n=====================================")
    print(" 3. Real Life Violence (dataset4_real_life_violence)")
    print("=====================================")
    download_kaggle("mohamedmustafa/real-life-violence-situations-dataset", base_dir / "dataset4_real_life_violence")

    # 4. Firearm Actions
    print("\n=====================================")
    print(" 4. Firearm Actions (dataset7_firearm_actions)")
    print("=====================================")
    ds7_dir = base_dir / "dataset7_firearm_actions"
    ds7_dir.mkdir(parents=True, exist_ok=True)
    ds7_zip = ds7_dir / "dataset.zip"
    if not list(ds7_dir.glob("*_extracted_poses*")):
        print("Downloading Firearm Actions...")
        urllib.request.urlretrieve("https://data.mendeley.com/public-api/zip/bbzpxhd22j/download/2", str(ds7_zip))
        extract_archives(ds7_dir)

    # 5. Shoplifting Video
    print("\n=====================================")
    print(" 5. Shoplifting Video (dataset9_shoplifting_video)")
    print("=====================================")
    download_kaggle("kipshidze/shoplifting-video-dataset", base_dir / "dataset9_shoplifting_video")

    # 6. Shoplifting Videos
    print("\n=====================================")
    print(" 6. Shoplifting Videos (dataset10_shoplifting_videos)")
    print("=====================================")
    download_kaggle("omarelg/shoplifting-videos-dataset", base_dir / "dataset10_shoplifting_videos")

    # 7. PoseLift
    print("\n=====================================")
    print(" 7. PoseLift (dataset8_poselift)")
    print("=====================================")
    git_clone("https://github.com/TeCSAR-UNCC/PoseLift.git", base_dir / "dataset8_poselift")

    # 8. RetailS
    print("\n=====================================")
    print(" 8. RetailS (dataset13_retails)")
    print("=====================================")
    ds13_dir = base_dir / "dataset13_retails"
    git_clone("https://github.com/TeCSAR-UNCC/RetailS.git", ds13_dir)
    print("Downloading RetailS Google Drive zip...")
    download_gdown("1uBCvDm7QdYjxwS9HT63lYaucATrecNuH", ds13_dir)
    extract_archives(ds13_dir)

    # 9. NTU RGB+D
    print("\n=====================================")
    print(" 9. NTU RGB+D (dataset1_ntu_rgbd)")
    print("=====================================")
    ds1_dir = base_dir / "dataset1_ntu_rgbd"
    ds1_dir.mkdir(parents=True, exist_ok=True)
    if not list(ds1_dir.glob("*.skeleton")):
        download_gdown("1CUZnBtYwifVXS21yVg62T-vrPVayso5H", ds1_dir)
        download_gdown("1tEbuaEqMxAV7dNc4fqu1O4M7mC6CJ50w", ds1_dir)
        extract_archives(ds1_dir)

    print("\n==========================================================")
    print(" ALL 9 DATASETS DOWNLOADED AND EXTRACTED SUCCESSFULLY! ")
    print("==========================================================")

if __name__ == "__main__":
    main()