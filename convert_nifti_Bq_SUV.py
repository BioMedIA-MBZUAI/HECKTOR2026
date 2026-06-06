#!/usr/bin/env python3
"""
Convert PET NIfTI images from BQML to SUVbw using metadata exported to CSV.

This is the NIfTI/CSV equivalent of convert_Bq_SUV.py. It does not read DICOM
files. The input PET NIfTI is expected to contain BQML values, and the CSV is
expected to contain one row per patient with at least:

    pid, units, bqml_to_suvbw_factor

If bqml_to_suvbw_factor is missing or empty, the script can compute it from:

    patient_weight_kg, dose_for_suv_bq

Example:
    python3 convert_nifti_Bq_SUV.py \
        --input-root /path/to/pet_nifti \
        --headers-csv "suv_conversion_tags.csv" \
        --output-root /path/to/suv_output
"""

import argparse
import math
import sys
from pathlib import Path

import nibabel as nib
import numpy as np
import pandas as pd


NIFTI_SUFFIXES = (".nii", ".nii.gz")


def is_nifti_file(path):
    name = path.name.lower()
    return name.endswith(NIFTI_SUFFIXES)


def strip_nifti_suffix(path):
    name = path.name
    lower_name = name.lower()
    if lower_name.endswith(".nii.gz"):
        return name[:-7]
    if lower_name.endswith(".nii"):
        return name[:-4]
    return path.stem


def find_column(columns, *names):
    normalized = {column.strip().lower(): column for column in columns}
    for name in names:
        column = normalized.get(name.strip().lower())
        if column:
            return column
    return None


def require_column(columns, *names):
    column = find_column(columns, *names)
    if column is None:
        expected = ", ".join(names)
        raise ValueError(f"CSV is missing required column: {expected}")
    return column


def load_header_rows(csv_path):
    df = pd.read_csv(csv_path)
    pid_col = require_column(df.columns, "pid", "patient_id", "patient")

    df["_pid"] = df[pid_col].astype(str).str.strip()
    df = df[df["_pid"] != ""].copy()

    duplicates = df[df["_pid"].duplicated()]["_pid"].unique()
    if len(duplicates):
        duplicate_text = ", ".join(duplicates[:10])
        raise ValueError(f"CSV has duplicate patient IDs: {duplicate_text}")

    columns = {
        "pid": pid_col,
        "units": find_column(df.columns, "units"),
        "factor": find_column(df.columns, "bqml_to_suvbw_factor", "suv_factor"),
        "weight_kg": find_column(df.columns, "patient_weight_kg", "weight_kg"),
        "dose_for_suv_bq": find_column(df.columns, "dose_for_suv_bq"),
        "decay_corrected_dose_bq": find_column(
            df.columns,
            "decay_corrected_dose_at_scan_bq",
            "decay_corrected_dose_bq",
        ),
    }

    if columns["factor"] is None and (
        columns["weight_kg"] is None
        or (columns["dose_for_suv_bq"] is None and columns["decay_corrected_dose_bq"] is None)
    ):
        raise ValueError(
            "CSV must contain bqml_to_suvbw_factor, or patient_weight_kg plus "
            "dose_for_suv_bq/decay_corrected_dose_at_scan_bq."
        )

    return df.set_index("_pid", drop=False), columns


def read_float(row, column):
    if column is None:
        return None
    value = row[column]
    if pd.isna(value):
        return None
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
    return float(value)


def extract_csv_suv_metadata(row, columns, allow_non_bqml=False):
    units = "UNKNOWN"
    if columns["units"] is not None and not pd.isna(row[columns["units"]]):
        units = str(row[columns["units"]]).strip().upper()

    if units != "BQML" and not allow_non_bqml:
        raise ValueError(
            f"CSV units are '{units}', expected 'BQML'. Use --allow-non-bqml only "
            "if the NIfTI values are known to be BQML-equivalent."
        )

    patient_weight_kg = read_float(row, columns["weight_kg"])
    dose_for_suv_bq = read_float(row, columns["dose_for_suv_bq"])
    if dose_for_suv_bq is None:
        dose_for_suv_bq = read_float(row, columns["decay_corrected_dose_bq"])

    if patient_weight_kg is not None and patient_weight_kg > 0 and dose_for_suv_bq is not None and dose_for_suv_bq > 0:
        computed_factor = (patient_weight_kg * 1000.0) / dose_for_suv_bq
        csv_factor = read_float(row, columns["factor"])
        if csv_factor is not None and csv_factor > 0 and not math.isclose(computed_factor, csv_factor, rel_tol=1e-5):
            raise ValueError(
                "CSV bqml_to_suvbw_factor does not match patient_weight_kg/dose_for_suv_bq "
                f"({csv_factor} vs {computed_factor})."
            )
        return {
            "units": units,
            "factor": computed_factor,
            "factor_source": "patient_weight_kg/dose_for_suv_bq",
        }

    factor = read_float(row, columns["factor"])
    if factor is not None and factor > 0:
        return {
            "units": units,
            "factor": factor,
            "factor_source": columns["factor"],
        }

    raise ValueError(
        "Missing valid SUV metadata. Need patient_weight_kg plus dose_for_suv_bq, "
        "or a positive bqml_to_suvbw_factor."
    )


def list_nifti_files(input_root):
    input_root = Path(input_root)
    if input_root.is_file():
        if not is_nifti_file(input_root):
            raise ValueError(f"Input file is not a NIfTI file: {input_root}")
        return [input_root]
    return sorted(path for path in input_root.rglob("*") if path.is_file() and is_nifti_file(path))


def score_patient_candidate(path, pid):
    pid_lower = pid.lower()
    name = strip_nifti_suffix(path).lower()
    path_text = str(path).lower()
    parts = [part.lower() for part in path.parts]

    if pid_lower not in path_text:
        return None
    if name == pid_lower or name == f"{pid_lower}__pt":
        return 100
    if name.startswith(f"{pid_lower}__pt"):
        return 95
    if name.startswith(pid_lower):
        return 90
    if pid_lower in name and "pt" in name:
        return 80
    if pid_lower in name:
        return 70
    if pid_lower in parts:
        return 60
    return 50


def resolve_patient_nifti(input_root, pid, input_pattern=None, nifti_files=None):
    input_root = Path(input_root)

    if input_pattern:
        candidate = input_root / input_pattern.format(pid=pid, patient=pid)
        if candidate.exists() and candidate.is_file() and is_nifti_file(candidate):
            return candidate
        raise FileNotFoundError(f"No NIfTI found for {pid} at pattern path: {candidate}")

    if nifti_files is None:
        nifti_files = list_nifti_files(input_root)

    if input_root.is_file() and len(nifti_files) == 1:
        only_file = nifti_files[0]
        score = score_patient_candidate(only_file, pid)
        if score is not None:
            return only_file
        raise FileNotFoundError(
            f"Input is a single NIfTI file but its path does not match patient ID {pid}."
        )

    scored = []
    for path in nifti_files:
        score = score_patient_candidate(path, pid)
        if score is not None:
            scored.append((score, path))

    if not scored:
        raise FileNotFoundError(f"No NIfTI file found for patient {pid}.")

    scored.sort(key=lambda item: (-item[0], str(item[1])))
    best_score = scored[0][0]
    best = [path for score, path in scored if score == best_score]
    if len(best) > 1:
        options = "\n  ".join(str(path) for path in best[:10])
        raise FileNotFoundError(f"Multiple NIfTI files matched patient {pid}:\n  {options}")

    return best[0]


def convert_bqml_nifti_to_suv(nifti_path, output_path, factor, overwrite=False):
    output_path = Path(output_path)
    if output_path.exists() and not overwrite:
        raise FileExistsError(f"Output exists, use --overwrite to replace: {output_path}")

    img = nib.load(str(nifti_path))
    bqml_data = img.get_fdata(dtype=np.float64)
    suv_data = (bqml_data * factor).astype(np.float32)

    header = img.header.copy()
    header.set_data_dtype(np.float32)
    header["scl_slope"] = 1
    header["scl_inter"] = 0
    header["descrip"] = b"SUVbw from BQML using CSV metadata"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    suv_img = nib.Nifti1Image(suv_data, img.affine, header)
    nib.save(suv_img, str(output_path))

    return suv_data.shape


def build_arg_parser():
    parser = argparse.ArgumentParser(
        description="Convert PET NIfTI images from BQML to SUVbw using a CSV header table."
    )
    parser.add_argument("--input-root", required=True, help="NIfTI file or folder containing PET NIfTI files.")
    parser.add_argument("--headers-csv", required=True, help="CSV containing one row of PET metadata per patient.")
    parser.add_argument("--output-root", required=True, help="Folder where SUV NIfTI files will be written.")
    parser.add_argument("--single-patient", help="Only convert this patient ID.")
    parser.add_argument(
        "--input-pattern",
        help=(
            "Optional relative pattern under --input-root, e.g. '{pid}.nii.gz', "
            "'{pid}/PET.nii.gz', or '{pid}/PET-CT/PET/{pid}.nii.gz'."
        ),
    )
    parser.add_argument(
        "--output-name-template",
        default="{pid}__PT.nii.gz",
        help="Output file name template. Default: '{pid}__PT.nii.gz'.",
    )
    parser.add_argument("--allow-non-bqml", action="store_true", help="Do not fail when CSV units are not BQML.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing output files.")
    parser.add_argument("--dry-run", action="store_true", help="Show matched inputs and factors without writing files.")
    return parser


def main(argv=None):
    args = build_arg_parser().parse_args(argv)

    header_rows, columns = load_header_rows(args.headers_csv)
    if args.single_patient:
        if args.single_patient not in header_rows.index:
            raise ValueError(f"Patient {args.single_patient} was not found in the CSV.")
        patient_ids = [args.single_patient]
    else:
        patient_ids = list(header_rows.index)

    nifti_files = None if args.input_pattern else list_nifti_files(args.input_root)
    if nifti_files is not None and not nifti_files:
        raise FileNotFoundError(f"No NIfTI files found under {args.input_root}.")

    successes = 0
    skipped = 0
    errors = 0

    for pid in patient_ids:
        row = header_rows.loc[pid]
        try:
            metadata = extract_csv_suv_metadata(row, columns, args.allow_non_bqml)
            nifti_path = resolve_patient_nifti(
                args.input_root,
                pid,
                input_pattern=args.input_pattern,
                nifti_files=nifti_files,
            )
            output_name = args.output_name_template.format(pid=pid, patient=pid)
            output_path = Path(args.output_root) / output_name

            if args.dry_run:
                print(
                    f"DRY RUN {pid}: {nifti_path} -> {output_path} "
                    f"(factor={metadata['factor']:.9g}, source={metadata['factor_source']})"
                )
                successes += 1
                continue

            shape = convert_bqml_nifti_to_suv(
                nifti_path,
                output_path,
                metadata["factor"],
                overwrite=args.overwrite,
            )
            print(
                f"Converted {pid}: {nifti_path} -> {output_path} "
                f"(shape={shape}, factor={metadata['factor']:.9g})"
            )
            successes += 1
        except FileNotFoundError as exc:
            print(f"Skipped {pid}: {exc}")
            skipped += 1
        except Exception as exc:
            print(f"Error processing {pid}: {exc}", file=sys.stderr)
            errors += 1

    print(f"Summary: converted={successes}, skipped={skipped}, errors={errors}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
