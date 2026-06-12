# Downloading CrimeSkelNet Datasets

The `CrimeSkelNet` model extracts human postures (skeletons) and identifies anomalies across various environments. To train and evaluate the model, you need to compile data from 9 separate sources into a unified dataset.

We provide a Python script that perfectly mirrors your AWS environment setup, handling the downloading, extracting, and organization automatically.

## Prerequisites

Before running the download script, please ensure your environment is prepared:

1. **Install required python packages (`gdown` for Google Drive and `kaggle` for Kaggle datasets):**

   ```bash
   pip install gdown kaggle
   ```

2. **Configure Kaggle API Credentials:**
   Three of the datasets are hosted on Kaggle. You need to authenticate your machine.
   - Go to your Kaggle account settings and click "Create New API Token".
   - This will download a `kaggle.json` file.
   - Move this file to the `.kaggle` folder in your home directory (`~/.kaggle/kaggle.json` on Linux/Mac, or `C:\Users\<username>\.kaggle\kaggle.json` on Windows).
   - Ensure permissions are secure: `chmod 600 ~/.kaggle/kaggle.json` (Linux/Mac).

3. **Install Git:**
   The script requires `git` installed and available in your PATH to clone GitHub repositories.

## Running the Automation Script

The automated python script will download around 9 different datasets consisting of CSVs, YOLO JSONs, AlphaPose JSONs, and `.skeleton` files.

Navigate to the `crime_skelnet` directory and run the script:

```bash
cd "ai/components/crime_skelnet"
python scripts/download_datasets.py --data_dir /data/datasets
```

> **Note:** By default, `--data_dir` uses `/data/datasets` (which matches the settings used in `builder.py` and your standard AWS setup). If you are testing locally, you can change the target directory to something else, like `--data_dir ./data/datasets`. However, make sure to update your `config/settings.py` so the `builder.py` can find them!

### Datasets Included

1. **HR-Crime** (Dataset 14)
2. **Fight Surveillance** (Dataset 3 - GitHub)
3. **Real Life Violence** (Dataset 4 - Kaggle)
4. **Firearm Actions** (Dataset 7 - Mendeley Data)
5. **Shoplifting Video** (Dataset 9 - Kaggle)
6. **Shoplifting Videos** (Dataset 10 - Kaggle)
7. **PoseLift** (Dataset 8 - GitHub)
8. **RetailS** (Dataset 13 - GitHub / Google Drive)
9. **NTU RGB+D** (Dataset 1 - Google Drive Mirror)

After successful execution, all 9 source datasets will be positioned into the specified absolute directory exactly as expected by `builder.py`.
