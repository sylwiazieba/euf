from __future__ import annotations

import argparse
import re
from datetime import datetime
from pathlib import Path

import pandas as pd


def to_key(value: str, *, fallback: str) -> str:
    text = str(value or "").strip().lower()
    text = text.replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or fallback


def find_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    norm_to_actual = {str(c).strip().lower(): c for c in df.columns}
    for candidate in candidates:
        key = candidate.strip().lower()
        if key in norm_to_actual:
            return norm_to_actual[key]
    return None


def load_seeding_log(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Seeding log not found: {path}")

    if path.suffix.lower() in {".xlsx", ".xls"}:
        df = pd.read_excel(path)
    elif path.suffix.lower() == ".csv":
        df = pd.read_csv(path)
    else:
        raise ValueError("Input must be .csv, .xlsx, or .xls")

    crop_col = find_column(df, ["Crop", "crop", "Crop Type", "crop type"])
    variety_col = find_column(
        df,
        [
            "Variety",
            "variety",
            "Variety (or N/A)",
            "Variety or N/A",
            "Variety (or NA)",
        ],
    )

    if not crop_col or not variety_col:
        raise ValueError(
            "Could not find crop/variety columns. Found columns: "
            + ", ".join([str(c) for c in df.columns])
        )

    data = df[[crop_col, variety_col]].copy()
    data.columns = ["Crop", "Variety"]

    # Drop true nulls first so they cannot become literal "nan" text later.
    data = data.dropna(subset=["Crop", "Variety"])

    data["Crop"] = data["Crop"].astype(str).str.strip()
    data["Variety"] = data["Variety"].astype(str).str.strip()
    data = data[(data["Crop"] != "") & (data["Variety"] != "")]

    null_like = {"", "nan", "none", "null", "na", "n/a", "<na>", "n a"}
    data = data[
        ~data["Crop"].str.lower().isin(null_like)
        & ~data["Variety"].str.lower().isin(null_like)
    ]

    return data.drop_duplicates().sort_values(["Crop", "Variety"]).reset_index(drop=True)


def build_sheets(crop_varieties: pd.DataFrame, form_title: str, form_id: str):
    crop_map: dict[str, str] = {}
    crop_rows: list[dict[str, str]] = []

    for crop_label in sorted(crop_varieties["Crop"].unique()):
        crop_key = to_key(crop_label, fallback="crop")
        base = crop_key
        i = 2
        while crop_key in crop_map.values():
            crop_key = f"{base}_{i}"
            i += 1
        crop_map[crop_label] = crop_key
        crop_rows.append(
            {"list_name": "crop_type", "name": crop_key, "label": crop_label, "crop": ""}
        )

    variety_rows: list[dict[str, str]] = []
    seen_variety_names: set[str] = set()
    for row in crop_varieties.itertuples(index=False):
        crop_label = row.Crop
        variety_label = row.Variety
        crop_key = crop_map[crop_label]

        variety_name = to_key(variety_label, fallback="variety")
        if variety_name in seen_variety_names:
            variety_name = f"{to_key(crop_label, fallback='crop')}_{variety_name}"

        base = variety_name
        i = 2
        while variety_name in seen_variety_names:
            variety_name = f"{base}_{i}"
            i += 1

        seen_variety_names.add(variety_name)
        variety_rows.append(
            {
                "list_name": "variety",
                "name": variety_name,
                "label": variety_label,
                "crop": crop_key,
            }
        )

    # Add an "Other (not listed)" option to every crop's variety list so
    # choice_filter still works (no or_other conflict) and free-text is shown
    # only when the respondent explicitly picks it.
    other_variety_rows = [
        {
            "list_name": "variety",
            "name": "other",
            "label": "Other (not listed)",
            "crop": crop_key,
        }
        for crop_key in crop_map.values()
    ]

    unit_rows = [
        {"list_name": "unit_type", "name": "weight", "label": "Weight (lbs)", "crop": ""},
        {"list_name": "unit_type", "name": "volume", "label": "Volume (pots)", "crop": ""},
    ]

    # Placeholder variety with empty crop: satisfies Survey123 Connect's design-time
    # validator (which checks choices when ${crop} is still blank) without affecting
    # runtime filtering.
    placeholder_variety = [
        {"list_name": "variety", "name": "_placeholder", "label": "Select a crop first", "crop": ""}
    ]

    choices_df = pd.DataFrame(crop_rows + variety_rows + other_variety_rows + placeholder_variety + unit_rows)[
        ["list_name", "name", "label", "crop"]
    ]

    survey_df = pd.DataFrame(
        [
            {"type": "start", "name": "start", "label": "", "appearance": "", "relevant": "", "choice_filter": "", "required": "", "default": ""},
            {"type": "end", "name": "end", "label": "", "appearance": "", "relevant": "", "choice_filter": "", "required": "", "default": ""},
            {"type": "select_one crop_type or_other", "name": "crop", "label": "Crop Type", "appearance": "autocomplete", "relevant": "", "choice_filter": "", "required": "yes", "default": ""},
            {"type": "text", "name": "crop_other_text", "label": "Crop (if not listed)", "appearance": "", "relevant": "${crop}='other'", "choice_filter": "", "required": "yes", "default": ""},
            {"type": "select_one variety", "name": "variety", "label": "Variety", "appearance": "autocomplete", "relevant": "${crop}!='other'", "choice_filter": "crop=${crop}", "required": "yes", "default": ""},
            {"type": "text", "name": "variety_other_text", "label": "Variety (if not listed)", "appearance": "", "relevant": "${variety}='other'", "choice_filter": "", "required": "yes", "default": ""},
            {"type": "text", "name": "variety_for_other_crop", "label": "Variety", "appearance": "", "relevant": "${crop}='other'", "choice_filter": "", "required": "yes", "default": ""},
            {"type": "select_one unit_type", "name": "unit_type", "label": "Unit Type", "appearance": "minimal", "relevant": "", "choice_filter": "", "required": "yes", "default": ""},
            {"type": "decimal", "name": "harvest_weight_lbs", "label": "Weight Harvested (lbs)", "appearance": "", "relevant": "${unit_type}='weight'", "choice_filter": "", "required": "yes", "default": ""},
            {"type": "integer", "name": "harvest_volume_pots", "label": "Volume Harvested (pots)", "appearance": "", "relevant": "${unit_type}='volume'", "choice_filter": "", "required": "yes", "default": ""},
            {"type": "date", "name": "harvest_date", "label": "Harvest Date", "appearance": "", "relevant": "", "choice_filter": "", "required": "yes", "default": "today()"},
            {"type": "text", "name": "notes", "label": "Notes", "appearance": "multiline", "relevant": "", "choice_filter": "", "required": "", "default": ""},
        ]
    )[["type", "name", "label", "appearance", "relevant", "choice_filter", "required", "default"]]

    settings_df = pd.DataFrame(
        [{"form_title": form_title, "form_id": form_id, "version": "v1"}]
    )

    return survey_df, choices_df, settings_df


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a Survey123 XLSX with cascading Crop -> Variety choices from a seeding log."
    )
    parser.add_argument("--input", default="GIS/seeding_donation_cleaned.csv")
    parser.add_argument("--output", default="GIS/survey123_harvest_cascading_dropdown.xlsx")
    parser.add_argument("--form-title", default="Urban Farm Harvest Tracker")
    parser.add_argument("--form-id", default="urban_farm_harvest_tracker")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    crop_varieties = load_seeding_log(input_path)
    survey_df, choices_df, settings_df = build_sheets(crop_varieties, args.form_title, args.form_id)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    final_output = output_path
    try:
        with pd.ExcelWriter(final_output, engine="openpyxl") as writer:
            survey_df.to_excel(writer, sheet_name="survey", index=False)
            choices_df.to_excel(writer, sheet_name="choices", index=False)
            settings_df.to_excel(writer, sheet_name="settings", index=False)
    except PermissionError:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        final_output = output_path.with_name(f"{output_path.stem}_{stamp}{output_path.suffix}")
        with pd.ExcelWriter(final_output, engine="openpyxl") as writer:
            survey_df.to_excel(writer, sheet_name="survey", index=False)
            choices_df.to_excel(writer, sheet_name="choices", index=False)
            settings_df.to_excel(writer, sheet_name="settings", index=False)
        print(f"Primary output was locked. Wrote timestamped copy instead: {final_output}")

    print(f"Created {final_output}")
    print(f"Unique crops: {crop_varieties['Crop'].nunique()}")
    print(f"Crop-variety pairs: {len(crop_varieties)}")


if __name__ == "__main__":
    main()
