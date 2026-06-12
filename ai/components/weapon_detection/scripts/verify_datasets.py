import os

BASE_DIR = "/data/datasets"

datasets_to_check = {
    "Weapon Dataset 1 (Kaggle CCTV)": "weapon_dataset1_cctv_weapon",
    "Weapon Dataset 2 (HF Gun Detection)": "weapon_dataset2_hf_gun_detection",
    "Weapon Dataset 3 (FiDaSS GDrive)": "weapon_dataset3_FiDaSS",
    "Weapon Dataset 4 (Roboflow v3)": "weapon_dataset4_roboflow",
    "Weapon Dataset 5 (Dataset Ninja)": "weapon_dataset5_ninja",
    "Weapon Dataset 6 (GitHub CCTV-Gun)": "weapon_dataset6_CCTV_Gun",
    "Weapon Dataset 7 (Roboflow matko)": "weapon_dataset7_roboflow",
    "Weapon Dataset 8 (Roboflow asan)": "weapon_dataset8_roboflow",
    "Weapon Dataset 9 (Roboflow liver)": "weapon_dataset9_roboflow",
    "Weapon Dataset 10 (Roboflow cylpn)": "weapon_dataset10_roboflow",
    "Normal Dataset 1 (Mall Dataset)": "normal_dataset1_mall",
    "Normal Dataset 2 (Kaggle Umbrellas)": "normal_dataset2_umbrellas",
    "Normal Dataset 3 (VIRAT Aerial)": "normal_dataset3_virat"
}

print("\n" + "="*70)
print("                    DATASET VERIFICATION REPORT                    ")
print("="*70)

all_good = True
success_count = 0

for name, folder in datasets_to_check.items():
    path = os.path.join(BASE_DIR, folder)
    if os.path.exists(path):
        contents = os.listdir(path)
        if len(contents) > 0:
            if folder == "weapon_dataset2_hf_gun_detection" and not os.path.exists(os.path.join(path, "extracted")):
                print(f"⚠️  [PARTIAL] {name.ljust(35)} | Downloaded, but unzipping failed")
                all_good = False
            else:
                print(f"✅ [SUCCESS] {name.ljust(35)} | Found ({len(contents)} items at root)")
                success_count += 1
        else:
            print(f"❌ [FAILED]  {name.ljust(35)} | Folder is EMPTY")
            all_good = False
    else:
        print(f"❌ [FAILED]  {name.ljust(35)} | Folder is MISSING")
        all_good = False

print("-" * 70)
print(f"Total Successful: {success_count} / {len(datasets_to_check)}")
if all_good:
    print("🎉 ALL DATASETS DOWNLOADED AND EXTRACTED SUCCESSFULLY!")
print("=" * 70 + "\n")
