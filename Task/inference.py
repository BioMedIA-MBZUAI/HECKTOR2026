"""
HECKTOR 2026 Challenge — Inference Entry Point

This script is executed at container runtime on Grand Challenge.
It reads a paired CT + PET scan and clinical data (EHR) from /input,
runs the three-stage pipeline, and writes all outputs to /output:

  Subtask 1 — Segmentation:
      /output/images/tumor-lymph-node-segmentation/output.mha
        (label 0=background, 1=GTVp, 2=GTVn)

  Subtask 2 — TN Staging:
      /output/tn-staging.json
        {"T_stage": "T2", "N_stage": "N2"}

  Subtask 3 — Prognosis (RFS):
      /output/recurrence-free-survival.json
        {"recurrence-free-survival": <float>}

To test locally:
    ./do_test_run.sh

To save and upload:
    ./do_save.sh
"""

import json
from glob import glob
from pathlib import Path

import SimpleITK
import numpy as np

INPUT_PATH = Path("/input")
OUTPUT_PATH = Path("/output")
RESOURCE_PATH = Path("resources")


def run():
    # ------------------------------------------------------------------
    # 1. Load inputs
    # ------------------------------------------------------------------
    ct_path = get_image_file(INPUT_PATH / "images/ct")
    pet_path = get_image_file(INPUT_PATH / "images/pet")
    ehr = load_json(INPUT_PATH / "ehr.json")

    # ------------------------------------------------------------------
    # 2. Subtask 1 — Segmentation
    #    Replace the block below with your model's inference logic.
    #    Load your weights from RESOURCE_PATH / "checkpoints".
    # ------------------------------------------------------------------
    segmentation_array = run_segmentation(ct_path, pet_path, ehr)

    write_segmentation(
        location=OUTPUT_PATH / "images/tumor-lymph-node-segmentation",
        array=segmentation_array,
        reference_path=ct_path,
    )

    # ------------------------------------------------------------------
    # 3. Subtask 2 — TN Staging
    #    Replace the block below with your model's inference logic.
    #    You may use segmentation_array as an additional input.
    # ------------------------------------------------------------------
    t_stage, n_stage = run_tn_staging(ct_path, pet_path, ehr, segmentation_array)

    write_json(
        location=OUTPUT_PATH / "tn-staging.json",
        data={"T_stage": t_stage, "N_stage": n_stage},
    )

    # ------------------------------------------------------------------
    # 4. Subtask 3 — Prognosis
    #    Replace the block below with your model's inference logic.
    #    You may use segmentation_array and tn stage as additional inputs.
    # ------------------------------------------------------------------
    rfs_score = run_prognosis(ct_path, pet_path, ehr, segmentation_array, t_stage, n_stage)

    write_json(
        location=OUTPUT_PATH / "recurrence-free-survival.json",
        data={"recurrence-free-survival": float(rfs_score)},
    )

    return 0


# =============================================================================
# Subtask implementations — replace with your own model code
# =============================================================================

def run_segmentation(ct_path, pet_path, ehr):
    """
    Load your segmentation model from RESOURCE_PATH/checkpoints and run inference.
    Returns a numpy array with labels: 0=background, 1=GTVp, 2=GTVn.
    """
    ct_image = SimpleITK.ReadImage(ct_path)
    output_array = np.zeros(SimpleITK.GetArrayFromImage(ct_image).shape, dtype=np.uint8)
    # TODO: replace with your segmentation model inference
    return output_array


def run_tn_staging(ct_path, pet_path, ehr, segmentation_array):
    """
    Load your TN staging model from RESOURCE_PATH/checkpoints and run inference.
    Returns (t_stage: str, n_stage: str), e.g. ("T2", "N1").
    TN staging follows AJCC/UICC 7th Edition (N2b and N2c collapsed to N2).
    """
    # TODO: replace with your TN staging model inference
    t_stage = "T2"
    n_stage = "N0"
    return t_stage, n_stage


def run_prognosis(ct_path, pet_path, ehr, segmentation_array, t_stage, n_stage):
    """
    Load your prognosis model from RESOURCE_PATH/checkpoints and run inference.
    Returns a float risk score (higher = higher recurrence risk).
    """
    # TODO: replace with your prognosis model inference
    rfs_score = 0.0
    return rfs_score


# =============================================================================
# I/O utilities
# =============================================================================

def get_image_file(location):
    files = (
        glob(str(location / "*.mha"))
        + glob(str(location / "*.tif"))
        + glob(str(location / "*.tiff"))
        + glob(str(location / "*.nii.gz"))
    )
    if not files:
        raise FileNotFoundError(f"No image file found in {location}")
    return files[0]


def load_json(location):
    with open(location, "r") as f:
        return json.load(f)


def write_json(location, data):
    location.parent.mkdir(parents=True, exist_ok=True)
    with open(location, "w") as f:
        json.dump(data, f, indent=2)


def write_segmentation(location, array, reference_path):
    location.mkdir(parents=True, exist_ok=True)
    reference = SimpleITK.ReadImage(reference_path)
    if array.ndim == 4 and array.shape[0] == 1:
        array = array[0]
    img = SimpleITK.GetImageFromArray(array.astype(np.uint8))
    img.CopyInformation(reference)
    SimpleITK.WriteImage(img, str(location / "output.mha"), useCompression=True)


if __name__ == "__main__":
    raise SystemExit(run())
