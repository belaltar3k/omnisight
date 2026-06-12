#!/bin/bash

BASE_DIR="/data/datasets"
sudo mkdir -p $BASE_DIR
sudo chown -R $USER:$USER $BASE_DIR

# Function to check if a directory exists and is not empty
is_downloaded() {
    if [ -d "$1" ] && [ "$(ls -A $1 2>/dev/null)" ]; then
        return 0 # True, it's downloaded
    else
        return 1 # False, missing or empty
    fi
}

echo "Installing Python dependencies..."
pip install -q kaggle huggingface_hub dataset-tools roboflow requests

# ---------------------------------------------------------
# WEAPON DATASETS
# ---------------------------------------------------------

echo -e "\n>>> Checking Dataset 1 (Kaggle: cctv-weapon-dataset)..."
if is_downloaded "$BASE_DIR/weapon_dataset1_cctv_weapon"; then
    echo "Already downloaded. Skipping."
else
    kaggle datasets download -d simuletic/cctv-weapon-dataset -p $BASE_DIR/weapon_dataset1_cctv_weapon --unzip || echo "Dataset 1 failed."
fi

echo -e "\n>>> Checking Dataset 6 (GitHub: CCTV-Gun)..."
if is_downloaded "$BASE_DIR/weapon_dataset6_CCTV_Gun"; then
    echo "Already downloaded. Skipping."
else
    git clone https://github.com/srikarym/CCTV-Gun.git $BASE_DIR/weapon_dataset6_CCTV_Gun || echo "Dataset 6 failed."
fi

# ---------------------------------------------------------
# NORMAL DATASETS
# ---------------------------------------------------------

echo -e "\n>>> Checking Normal Dataset 1 (Mall Dataset)..."
if is_downloaded "$BASE_DIR/normal_dataset1_mall"; then
    echo "Already downloaded. Skipping."
else
    mkdir -p $BASE_DIR/normal_dataset1_mall
    wget -q --show-progress -O $BASE_DIR/normal_dataset1_mall/mall_dataset.zip https://personal.ie.cuhk.edu.hk/~ccloy/files/datasets/mall_dataset.zip
    unzip -q -o $BASE_DIR/normal_dataset1_mall/mall_dataset.zip -d $BASE_DIR/normal_dataset1_mall/
fi

echo -e "\n>>> Checking Normal Dataset 2 (Kaggle: rifles-vs-umbrellas)..."
if is_downloaded "$BASE_DIR/normal_dataset2_umbrellas"; then
    echo "Already downloaded. Skipping."
else
    kaggle datasets download -d simuletic/cctv-weapon-detection-rifles-vs-umbrellas -p $BASE_DIR/normal_dataset2_umbrellas --unzip || echo "Normal Dataset 2 failed."
fi

# ---------------------------------------------------------
# TRIGGER PYTHON SCRIPTS
# ---------------------------------------------------------
echo -e "\n>>> Executing Python script for HuggingFace, Roboflow, Dataset Ninja, and Kitware..."
echo "*************************************************************************"
echo "NOTE: To download Roboflow datasets, you MUST provide an API key."
echo "Get it at: https://app.roboflow.com/ -> Settings -> Roboflow API"
echo "*************************************************************************"
read -s -p "Enter your Roboflow API Key (Press ENTER if you don't have one or already downloaded): " ROBOFLOW_API_KEY
echo ""
export ROBOFLOW_API_KEY=$ROBOFLOW_API_KEY

python3 download_python_parts.py

echo -e "\n>>> Running Verification Checks..."
python3 verify_datasets.py
