import os
import requests
import zipfile
import glob
import dataset_tools as dtools
from roboflow import Roboflow
from huggingface_hub import snapshot_download

BASE_DIR = "/data/datasets"
os.makedirs(BASE_DIR, exist_ok=True)

def is_downloaded(folder_name):
    path = os.path.join(BASE_DIR, folder_name)
    return os.path.exists(path) and len(os.listdir(path)) > 0

# 1. Weapon Dataset 2: Hugging Face
print("\n>>> Checking Dataset 2 (HuggingFace: US-Real-time-gun-detection)...")
hf_dir = "weapon_dataset2_hf_gun_detection"
if is_downloaded(hf_dir) and os.path.exists(os.path.join(BASE_DIR, hf_dir, "extracted")):
    print("Already downloaded and extracted. Skipping.")
else:
    try:
        snapshot_download(repo_id="jsalazar/US-Real-time-gun-detection-in-CCTV-An-open-problem-dataset", repo_type="dataset", local_dir=os.path.join(BASE_DIR, hf_dir))
        extract_dir = os.path.join(BASE_DIR, hf_dir, "extracted")
        os.makedirs(extract_dir, exist_ok=True)
        for z in glob.glob(os.path.join(BASE_DIR, hf_dir, "**", "*.zip"), recursive=True):
            print(f"Extracting {os.path.basename(z)}...")
            with zipfile.ZipFile(z, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
    except Exception as e:
        print(f"HuggingFace failed: {e}")

# 2. Weapon Dataset 5: Dataset Ninja
print("\n>>> Checking Dataset 5 (Dataset Ninja: Weapons in Images)...")
ninja_dir = "weapon_dataset5_ninja"
if is_downloaded(ninja_dir):
    print("Already downloaded. Skipping.")
else:
    try:
        dtools.download(dataset='Weapons in Images', dst_dir=os.path.join(BASE_DIR, ninja_dir))
    except Exception as e:
        print(f"Dataset Ninja failed: {e}")

# 3. Weapon Datasets 4, 7, 8, 9, 10: Roboflow
print("\n>>> Checking Roboflow Datasets...")
ROBOFLOW_API_KEY = os.environ.get("ROBOFLOW_API_KEY", "").strip()

datasets = [
    ("weapon-detection-cctv", "weapon-detection-cctv-v3-dataset", 1, "weapon_dataset4_roboflow"),
    ("matko-glucina-eauiv", "weapons-1uvvp", 3, "weapon_dataset7_roboflow"),
    ("asan-k1yfi", "weapons-hmzxb", 4, "weapon_dataset8_roboflow"),
    ("liver-gygux", "weapons-ef4r7", 3, "weapon_dataset9_roboflow"),
    ("project-cylpn", "weapons-se6jt", 1, "weapon_dataset10_roboflow"),
]

if not ROBOFLOW_API_KEY:
    print("WARNING: No Roboflow API key provided. Skipping Roboflow.")
else:
    rf = Roboflow(api_key=ROBOFLOW_API_KEY)
    for workspace, project, version, folder_name in datasets:
        if is_downloaded(folder_name):
            print(f"{folder_name} already exists. Skipping.")
        else:
            try:
                rf.workspace(workspace).project(project).version(version).download("yolov8", location=os.path.join(BASE_DIR, folder_name))
            except Exception as e:
                print(f"Roboflow {folder_name} failed: {e}")

# 4. Normal Dataset 3: VIRAT Aerial (Kitware API)
print("\n>>> Checking Normal Dataset 3 (VIRAT Aerial)...")
virat_dir = "normal_dataset3_virat"
if is_downloaded(virat_dir):
    print("Already downloaded. Skipping.")
else:
    api_url = "https://data.kitware.com/api/v1"
    try:
        r = requests.get(f"{api_url}/folder?parentType=collection&parentId=611e77a42fa25629b9daceba")
        if r.status_code == 200:
            for f in r.json():
                ir = requests.get(f"{api_url}/item?folderId={f['_id']}&limit=1000")
                if ir.status_code == 200:
                    for item in ir.json():
                        out_path = os.path.join(BASE_DIR, virat_dir, f['name'])
                        os.makedirs(out_path, exist_ok=True)
                        file_path = os.path.join(out_path, item['name'])
                        if not os.path.exists(file_path):
                            print(f"Downloading {item['name']}...")
                            with requests.get(f"{api_url}/item/{item['_id']}/download", stream=True) as dl_r:
                                dl_r.raise_for_status()
                                with open(file_path, 'wb') as f_out:
                                    for chunk in dl_r.iter_content(chunk_size=8192):
                                        f_out.write(chunk)
    except Exception as e:
        print(f"VIRAT Aerial failed: {e}")
