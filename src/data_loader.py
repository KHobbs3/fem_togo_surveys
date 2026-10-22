import io
import re
import urllib.request
from pathlib import Path

import pandas as pd
import streamlit as st

# ── Pre-aggregated loaders (safe: no PII) ──────────────────────────────────
#
# Every CSV here is written by pipeline_output/ (`python -m pipeline.run_pipeline`)
# into togo_app/data/, and read from there. data/ is gitignored, so for a deployed
# copy (e.g. Streamlit Community Cloud) upload a file to Google Drive and paste its
# file ID into DRIVE_FILE_IDS under the same name -- the ID wins over the local file.
# Get a file's ID from its "Share" link: https://drive.google.com/file/d/<FILE_ID>/view

COUNTRY = "Togo"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

DRIVE_FILE_IDS = {
    # Access
    "access_affordability.csv":           "1AKgtJzSbt1Rj9Tt33dBS5hNECpC8dXTf",
    "access_composite.csv":               "1AeZTKtNKp76hrTShc5PksnMn4CbW1Q9r",
    "access_stockout_responses.csv":      "1lBHcRMcelfy1yVrKQZKBxgpyPnRjEj16",
    "access_stockouts.csv":               "1AePqa9TQIbACRaRqysFtcoKAvm7F_Nto",
    "access_travel.csv":                  "1ALp-GdNC23dob39KBL-kuYf5R6PRGa3u",
    # Family planning
    "fp_funnel.csv":                      "1hN9i6b8sLyeuYFtvmiyfPswENjY4rnku",
    "fp_intent.csv":                      "1_ktwblcmMHzbkUvVMD24wWhYsLSiV8yT",
    "fp_methods.csv":                     "1SsvfRgIKjpr2PyR72eWI9gisLW_4fsRx",
    "fp_nonuse_reasons.csv":              "1UXuoAgSwTSwZK4Gy4IL0CPAZP2_zu13E",
    "fp_reason_use.csv":                  "1i8KMoMBjkNHWfjP8YgrRwQRXaIHityXT",
    "fp_timing.csv":                      "1LOJSAJA7XwXTzGIL7d_SRTrahEzWyDJL",
    "fp_unmet.csv":                       "1Lg8QA8Ylxgoar4zAo3NSE0loDPiSuEQL",
    # Personality
    "personality_decision_confident.csv": "1QM2o-IDvN_LDgAd8Xf21dwPqp54vuMd5",
    "personality_forming_beliefs.csv":    "1Xl9-4p-NAnpFEOX0xI8RoOdMmdTH0pfO",
    "personality_goals_achievable.csv":   "1V4AejPLVFK5M7TpBfVlkswornfp6ryo9",
    "personality_life_goals.csv":         "1ngUQinCtv7q3oDAju4ghAOQuly8d-FtN",
    "personality_likeable_traits.csv":    "1DV-URS9FRQb7JcJW70d9eHSArpNYdqhF",
    "personality_role_models.csv":        "1w7cS9QMUlywVk3u9dHX4FIXdybRB7z1x",
    "personality_wellbeing.csv":          "1xmjhGKDbYNu1PPG5aEBiObp1BjbMneML",
    # Personas
    "personas_centroids.csv":             "1NGd7OX6wKe-T3SBsTf3F7rwkAYFtvCFI",
    "personas_profile.csv":               "1z2dE8k__DwEXBoDJ5JYbBguvJtXseObp",
    "personas_elbow.csv":                 "1EJKggaRpLw8AFEPePNzTBW8dfiaEzSep",
    "personas_centroids_by_gender.csv":   "1ktNCeVPtLx9zylSdDByn731Gy1SSsdpQ",
    "personas_profile_by_gender.csv":     "1e11tKtpeuSIHPoxZWmL1RYaQBs7H_M1R",
    "personas_centroids_by_region.csv":   "1z9VibynsAXF3alpfVKhLtzal6m0NwsSt",
    "personas_profile_by_region.csv":     "1t0rtOaOcXRPGRGMotz8fIk6GiEHdZ7TM",
    "personas_elbow_by_region.csv":       "1bPAwOKsUzQoHvVXC8dvGBjVm2g-JIoZ3",
    "culture_clusters_centroids.csv":     "1spqP43vCg_aj_ihfzRaApwv2fxos14io",
    "culture_clusters_profile.csv":       "1j5EBZBKaUs6zuGByJWDcUas1UUxRkheq",
    "culture_clusters_elbow.csv":         "1CPK6t0veNPLWEXq92QDfYHUwI8anDzGp",
    # Drivers & barriers table (dated file; see load_drivers_barriers)
    "drivers_barriers_table.csv":         "1Q_lVl3vF-MwhMS5FoAA_s3jn_AkEekdL",
    # Respondents / statements
    "respondents_profile.csv":            "1CA2MGH2Mahfh0g-gg6r4nP3sbeG0fIy2",
    "statements_heatmap.csv":             "1ulpvgRj8k4mja4VVZClGwF75KZ3pfmBY",
    # Label tables (also versioned in data/; read by src/translations.py)
    "statement_labels.csv":               "1aEJnx_ZcHcQEu9A-P4K-6In-yOjVsNeH",
    "driver_barrier_translations.csv":    "1rbYmPmbWZo1xijevno7XbmXY9vr_KF38",
    "radio_translations.csv":             "1WYqe-MqD_M1OVHtpGjbRM7xokOimQxUF",
    # Radio
    f"{COUNTRY}_question_table_by_station_*.csv":               "1NBj3dEm6xNNv9lWoQsB61vWmFdC2iLmr",
    f"{COUNTRY}_question_table_by_state_*.csv":                 "1e1OhI-fsBZYZz9j4fBV3US2_w4rES-v3"
}


def _latest(pattern):
    """Newest dated file matching `pattern` in data/ (dates are yy_mm_dd), or the
    pattern itself so a Drive ID can still be keyed on it."""
    matches = sorted(p.name for p in DATA_DIR.glob(pattern))
    return matches[-1] if matches else pattern


DRIVE_URL = "https://drive.usercontent.google.com/download?export=download&confirm=t&id="


def _read_drive(name, file_id, **kwargs):
    """CSV from Drive, or None (with an on-page error) if Drive sends a web page
    instead -- what happens when the file isn't shared as "Anyone with the link"."""
    request = urllib.request.Request(DRIVE_URL + file_id, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read()
    except Exception as exc:
        st.error(f"Couldn't download {name} from Google Drive ({exc}).")
        return None
    if raw.lstrip()[:15].lower().startswith((b"<!doctype", b"<html")):
        st.error(
            f"Google Drive returned a web page instead of {name}. In Drive, set the file's "
            "sharing to \"Anyone with the link\" (Viewer) and check its ID in DRIVE_FILE_IDS."
        )
        return None
    return pd.read_csv(io.BytesIO(raw), **kwargs)


# ttl: a file whose Drive sharing gets fixed shows up within 10 minutes, no restart.
@st.cache_data(show_spinner=False, ttl="10m")
def _load(name, **kwargs):
    file_id = DRIVE_FILE_IDS.get(name)
    if file_id:
        df = _read_drive(name, file_id, **kwargs)
        if df is not None:
            return df
    path = DATA_DIR / name
    if not path.exists():
        return None
    return pd.read_csv(path, **kwargs)


# ── Statements / drivers-barriers ──────────────────────────────────────────

def load_statement_labels():
    return _load("statement_labels.csv")


def load_statements_heatmap():
    return _load("statements_heatmap.csv", index_col=0)


# ── Access page ─────────────────────────────────────────────────────────────

def load_access_stockouts():
    return _load("access_stockouts.csv", index_col=0)


def load_access_stockout_responses():
    return _load("access_stockout_responses.csv", index_col=0)


def load_access_travel():
    return _load("access_travel.csv", index_col=0)


def load_access_affordability():
    return _load("access_affordability.csv", index_col=0)


def load_access_composite():
    return _load("access_composite.csv", index_col=0)


# ── Radio page ───────────────────────────────────────────────────────────────

def clean_column_name(col):
    col = re.sub(r'^\d+_\d+_', '', col)
    col = re.sub(r'_+\d+$', '', col)
    col = col.replace('_', ' ').strip().title()
    return col


def load_radio_by_station():
    df = _load(_latest(f"{COUNTRY}_question_table_by_station_*.csv"))
    if df is not None:
        df.set_index(df.columns[0], inplace=True)
    return df


def load_radio_by_state():
    df = _load(_latest(f"{COUNTRY}_question_table_by_state_*.csv"))
    if df is not None:
        df.set_index(df.columns[0], inplace=True)
    return df


# ── Family planning page ──────────────────────────────────────────────────────

def load_fp_funnel():
    return _load("fp_funnel.csv", index_col=0)


def load_fp_timing():
    return _load("fp_timing.csv", index_col=0)


def load_fp_methods():
    return _load("fp_methods.csv", index_col=0)


def load_fp_reason_use():
    return _load("fp_reason_use.csv", index_col=0)


def load_fp_intent():
    return _load("fp_intent.csv", index_col=0)


def load_fp_nonuse_reasons():
    return _load("fp_nonuse_reasons.csv", index_col=0)


def load_fp_unmet():
    return _load("fp_unmet.csv", index_col=0)


# ── Personality page ──────────────────────────────────────────────────────────

def load_personality_life_goals():
    return _load("personality_life_goals.csv", index_col=0)


def load_personality_goals_achievable():
    return _load("personality_goals_achievable.csv", index_col=0)


def load_personality_role_models():
    return _load("personality_role_models.csv", index_col=0)


def load_personality_likeable_traits():
    return _load("personality_likeable_traits.csv", index_col=0)


def load_personality_forming_beliefs():
    return _load("personality_forming_beliefs.csv", index_col=0)


def load_personality_decision_confident():
    return _load("personality_decision_confident.csv", index_col=0)


def load_personality_wellbeing():
    return _load("personality_wellbeing.csv", index_col=0)


# ── Respondent profile page ───────────────────────────────────────────────────

def load_respondents_profile():
    return _load("respondents_profile.csv", index_col=0)


# ── Personas page ─────────────────────────────────────────────────────────────

def load_personas_centroids():
    return _load("personas_centroids.csv", index_col=0)


def load_personas_profile():
    return _load("personas_profile.csv", index_col=0)


def load_personas_centroids_by_gender():
    return _load("personas_centroids_by_gender.csv", index_col=0)


def load_personas_profile_by_gender():
    return _load("personas_profile_by_gender.csv", index_col=0)


def load_personas_elbow():
    return _load("personas_elbow.csv", index_col=0)


def load_personas_centroids_by_region():
    return _load("personas_centroids_by_region.csv", index_col=0)


def load_personas_profile_by_region():
    return _load("personas_profile_by_region.csv", index_col=0)


def load_personas_elbow_by_region():
    return _load("personas_elbow_by_region.csv", index_col=0)


# Standalone culture clustering (religion, life goals, top driver/barrier --
# region deliberately excluded as a clustering input, see
# CULTURE_CLUSTERING_VARS in pipeline/config.py).
def load_culture_clusters_centroids():
    return _load("culture_clusters_centroids.csv", index_col=0)


def load_culture_clusters_profile():
    return _load("culture_clusters_profile.csv", index_col=0)


def load_culture_clusters_elbow():
    return _load("culture_clusters_elbow.csv", index_col=0)


# ── Drivers & barriers ──────────────────────────────────────────────────────
# Produced by table_analysis/03_driver_barrier_table_w_counts.ipynb and copied
# into data/ by `python -m pipeline.run_pipeline --pages drivers_barriers`.
# Togo's notebook labels its geographic split "DEPARTMENT" (GEO_SPLIT_LABEL);
# those columns are renamed to the "REGION: ..." names the page reads.
def load_drivers_barriers():
    # The local file is dated, so the Drive copy is keyed on a fixed name instead;
    # it wins when set, and the newest local file is the fallback.
    df = _load("drivers_barriers_table.csv") if "drivers_barriers_table.csv" in DRIVE_FILE_IDS else None
    if df is None:
        df = _load(_latest(f"{COUNTRY}_drivers-barriers_table_[0-9]*.csv"))
    if df is not None:
        df = df.rename(columns=lambda c: re.sub(r"^DEPARTMENT:", "REGION:", c))
    return df


# ── Phone Pulse pages -- NOT COLLECTED FOR TOGO ────────────────────────────
# No phone pulse follow-up has been fielded yet, so every Phone Pulse page in
# app.py is stubbed rather than wired to loaders.


# ── Shared parsing helpers (used by drivers/barriers) ──────────────────────

def parse_subgroup_prevalence(cell_str):
    result = {}
    if pd.isna(cell_str) or str(cell_str).strip() == "":
        return result
    for line in str(cell_str).split("\n"):
        line = line.strip()
        match = re.match(r"^(.+?):\s*([\d.]+)%", line)
        if match:
            result[match.group(1).strip()] = float(match.group(2))
    return result


def parse_statements(cell_str):
    if pd.isna(cell_str) or str(cell_str).strip() == "":
        return None, {}
    lines = [l.strip() for l in str(cell_str).split("\n") if l.strip()]
    statement = None
    percentages = {}
    for line in lines:
        match = re.match(r"^(.+?):\s*([\d.]+)%", line)
        if match:
            percentages[match.group(1).strip()] = float(match.group(2))
        elif statement is None and "%" not in line:
            statement = line
    return statement, percentages


PRIORITY_ORDER = {"Very high": 4, "High": 3, "Medium": 2, "Low": 1}


def get_priority_sort_key(p):
    return PRIORITY_ORDER.get(str(p).strip(), 0)


USER_CATEGORY_LABELS = {
    "user":        "Current user",
    "nonuser":     "Non-user",
    "future_user": "Future user",
    "past_user":   "Past user",
}

AGE_GROUPS  = ["16-20", "21-30", "31-45"]
URBAN_RURAL = ["Rural", "Semi-urbain", "Urbain"]

# Regions = Togo's sampling strata (`province`), south to north. Mirrors
# REGIONS / PROVINCE_TO_REGION in pipeline_output/pipeline/config.py.
REGIONS = ["Maritime", "Plateaux", "Centrale", "Kara"]