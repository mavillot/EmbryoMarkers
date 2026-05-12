# EmbryoMarkers

Interactive dashboard to upload embryo **images** or **timelapse videos** and extract embryo markers (blastocyst structures, fragmentation, grading, stage, cell count).

## What You Get

- Image analysis:
  - Blastocyst structures segmentation (ZP / TE / ICM) + derived markers (areas, ratios, ZP thickness/symmetry, TE fractal dimension, ICM eccentricity, BC metrics, etc.)
  - Optional fragmentation mask + fragmentation index
  - Optional grading (EXP / TE / ICM)
  - Optional stage classification
  - Optional cell counting
- Video analysis:
  - Overview (duration, frames processed, blastocyst formation time)
  - Evolution plots for the extracted markers across sampled frames

## Quick Start

### 1) Download the repository

Option A: clone with git

```bash
git clone https://github.com/mavillot/EmbryoMarkers.git
cd EmbryoMarkers
```

Option B: download as ZIP

1. Open https://github.com/mavillot/EmbryoMarkers
2. Click `Code` then `Download ZIP`
3. Unzip it and open a terminal in the extracted folder

### 2) Install dependencies

From the repository root:

```bash
python3 -m pip install -r requirements.txt
```

### 3) Download models

Create a folder called `models/` in the repo root (next to `dashboard/` and `inference/`).

```bash
mkdir -p models
```

Download the released model files and save them into `models/` with the exact filenames:

- `models/stage_classif.pth`
  - https://github.com/mavillot/EmbryoMarkers/releases/download/stage_classification/stage_classif.pth
- `models/fragmentation_hrnet.pth`
  - https://github.com/mavillot/EmbryoMarkers/releases/download/fragmentation/fragmentation_hrnet.pth
- `models/EXP.pt`
  - https://github.com/mavillot/EmbryoMarkers/releases/download/exp/EXP.pt
- `models/cell_count.pt`
  - https://github.com/mavillot/EmbryoMarkers/releases/download/cell_count/cell_count.pt
- `models/segmentation_hrnet.pth`
  - https://github.com/mavillot/EmbryoMarkers/releases/download/blasto_structure/segmentation_hrnet.pth
- `models/TE.pt`
  - https://github.com/mavillot/EmbryoMarkers/releases/download/TE/TE.pt
- `models/ICM.pt`
  - https://github.com/mavillot/EmbryoMarkers/releases/download/ICM/ICM.pt

After downloading, your `models/` folder should look like:

```text
models/
  segmentation_hrnet.pth
  fragmentation_hrnet.pth
  cell_count.pt
  EXP.pt
  TE.pt
  ICM.pt
  stage_classif.pth
```

### 4) Run the dashboard

```bash
python3 -m streamlit run dashboard/app.py
```

Open the URL that Streamlit prints (usually `http://localhost:8501`).

## Usage Notes

- The sidebar toggles control which models run:
  - `Blastocyst structures`: enables ZP/TE/ICM segmentation and all structure-derived markers/graphs.
  - `Fragmentation`: computes the fragmentation mask + fragmentation index.
  - `Grading`: runs EXP/TE/ICM grading classifiers.
  - `Stage`: runs stage classification.
  - `Cell count`: runs the cell counting model.

- If you are on CPU, enable only what you need. Some models are heavy.

## Supported Inputs

- Images: `.png`, `.jpg`, `.jpeg`, `.bmp`, `.tiff`
- Videos: `.mp4`, `.avi`, `.mov`, `.mkv`

## Project Layout

- `dashboard/app.py`: Streamlit dashboard
- `inference/`: inference code (image/video pipelines)
- `models/`: model checkpoints (download from releases)
- `tmp/`: temporary files created at runtime
