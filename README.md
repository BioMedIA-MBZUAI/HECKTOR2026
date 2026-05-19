# HECKTOR2026 — Docker Submission Template

<p align="center">
  <img src="assets/images/HECKTOR_2026_Banner.png">
</p>

---

# ℹ️ About

This branch contains the Docker submission template and instructions for the [HECKTOR 2026 Challenge](TBA) hosted on Grand Challenge.

Unlike HECKTOR 2025, the 2026 edition has a **single unified task** — an end-to-end pipeline covering segmentation, TN staging, and prognosis. Your container must produce **all three outputs** in a single inference run.

Follow this guide to install Docker, integrate your models, test locally, save your container, and submit to Grand Challenge.

---

# 📑 Table of Contents

* [Installation](#️-installation)
* [Repository Structure](#-repository-structure)
* [Integrating Your Models](#-integrating-your-models)
* [Restrictions & Tips](#️-restrictions--submission-tips)
* [Saving & Uploading](#-saving-and-uploading)

---

# 🛠️ Installation

## Linux (recommended)

Install [Docker Engine](https://docs.docker.com/engine/install/) and [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html).

Verify:
```bash
docker run hello-world
docker run --rm --gpus all nvidia/cuda:12.1.1-runtime-ubuntu22.04 nvidia-smi
```

## macOS / Windows

Download and install [Docker Desktop](https://www.docker.com/products/docker-desktop). Verify:
```bash
docker --version
```

---

# 📁 Repository Structure

```text
Task/
├── Dockerfile              # Container definition — do not modify base image
├── requirements.txt        # Add your Python dependencies here
├── inference.py            # Entry point — implement your pipeline here
├── do_build.sh             # Build the container
├── do_test_run.sh          # Test the container locally
├── do_save.sh              # Save the container + model tarball for upload
├── model/                  # Place your model weights here (tracked via Git LFS).
│                           # Packed into model.tar.gz by do_save.sh and uploaded
│                           # separately to Grand Challenge under Algorithm > Models.
│                           # Mounted at /opt/ml/model at runtime.
└── test/
    ├── input/
    │   └── interf0/
    │       ├── ehr.json            # Sample clinical data
    │       ├── inputs.json         # GC-generated socket metadata
    │       └── images/
    │           ├── ct/             # Place a sample CT .mha file here for local testing
    │           └── pet/            # Place a sample PET .mha file here for local testing
    └── output/                     # Test outputs written here (gitignored)
```

---

# 🤖 Integrating Your Models

### Step 1 — Add your model weights

Place your trained model weights under `Task/model/`. These files are tracked via Git LFS. At submission time, `do_save.sh` packs this directory into a `model.tar.gz` that you upload **separately** to Grand Challenge under **Algorithm > Models**. At runtime, the tarball is extracted to `/opt/ml/model/` inside your container. Load weights from there in `inference.py`.

### Step 2 — Add your dependencies

Edit `Task/requirements.txt` to add any additional Python packages your model requires.

### Step 3 — Implement the pipeline in `inference.py`

`inference.py` is the container entry point. It already defines the expected I/O structure. Fill in the three `run_*` functions with your model code:

```python
def run_segmentation(ct_path, pet_path, ehr):
    # Returns numpy array: 0=background, 1=GTVp, 2=GTVn
    ...

def run_tn_staging(ct_path, pet_path, ehr, segmentation_array):
    # Returns (t_stage: str, n_stage: str), e.g. ("T2", "N1")
    ...

def run_prognosis(ct_path, pet_path, ehr, segmentation_array, t_stage, n_stage):
    # Returns float risk score (higher = higher recurrence risk)
    ...
```

### Expected outputs

| Output | Path inside container | Format |
|---|---|---|
| Segmentation mask | `/output/images/head-neck-tumor-segmentation/output.mha` | `.mha`, `uint8`, labels `{0: background, 1: GTVp, 2: GTVn}`, written at the input CT geometry (spacing/origin/direction) |
| T stage | `/output/t-stage.json` | JSON string, e.g. `"T2"` (AJCC/UICC 7th Edition: `T1`–`T4`) |
| N stage | `/output/n-stage.json` | JSON string, e.g. `"N1"` (AJCC/UICC 7th Edition: `N0`–`N3`; N2b/N2c collapsed to N2) |
| Prognosis | `/output/rfs.json` | JSON float, e.g. `42.0` — continuous risk score, **higher = higher recurrence risk** (concordant with shorter RFS) |

### Step 4 — Add sample test data and test locally

Place a sample CT `.mha` in `Task/test/input/interf0/images/ct/` and a sample PET `.mha` in `Task/test/input/interf0/images/pet/`, then run:

```bash
cd Task/
./do_test_run.sh
```

Outputs will be written to `Task/test/output/interf0/`.

### Step 5 — Save and upload

```bash
cd Task/
./do_save.sh
```

This produces **two** files ready for upload to Grand Challenge:
- `hecktor2026-task_<timestamp>.tar.gz` — the container image (upload as your **Algorithm Image**)
- `model.tar.gz` — your model weights (upload separately under **Algorithm > Models**)

---

# ⚠️ Restrictions & Submission Tips

1. **No network access** — your container must not attempt any HTTP, SSH, or DNS connections.
2. **GPU** — inference runs on an NVIDIA T4 (16 GB VRAM). Design your model accordingly.
3. **RAM limit** — peak memory must stay under **16 GB**.
4. **Container size** — the uploaded `.tar.gz` must not exceed **10 GB**.
5. **Filesystem** — all writes must go to `/output/` or `/tmp/`. Writing elsewhere will be blocked.
6. **Time limit** — the full pipeline (all three subtasks) must complete within **25 minutes**.
7. **I/O paths** — read from `/input/` only; write to `/output/` only.

### Common errors

| Error | Likely cause | Fix |
|---|---|---|
| `Model file not found` | Missing weights in `model/` (or model tarball not uploaded to GC) | Add your `.pth`/`.pt` files to `Task/model/` |
| `ModuleNotFoundError` | Missing dependency | Update `requirements.txt` and rebuild |
| `Permission denied` | Writing outside `/output/` or `/tmp/` | Redirect all writes |
| `Killed` / OOM | Exceeded memory limit | Reduce batch size or model size |
| `Timeout` | Exceeded 25-minute limit | Optimize preprocessing and inference |

---

# 💾 Saving and Uploading

1. **Save to tarball:**
   ```bash
   cd Task/
   ./do_save.sh
   ```

2. **Upload to Grand Challenge:** Follow the [Submission Guidelines](submission-guidelines.md).

3. **Phases:**

   | Phase | Cases | Purpose |
   |---|---|---|
   | Sanity Check | 3 | Verify your container runs without errors |
   | Validation (Phase 1) | ~50 | Leaderboard results; 2 submissions allowed |
   | Testing (Phase 2) | ~500 | Official ranking; 1 submission |

---

# 🎉 Good luck with your submission!

If you need support, post questions on the [Challenge Forum](TBA) or email `hecktor.challenge@gmail.com`.
