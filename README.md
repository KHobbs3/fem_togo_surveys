# FEM Togo Survey App

Streamlit dashboard for the Togo FEM formative research survey (2026). It reads only pre-aggregated CSVs, never respondent-level data.

## Run

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Data

The CSVs in `data/` are written by `../pipeline_output` (`python -m pipeline.run_pipeline`) and are not committed. A page shows a "not found" message until its file exists.

To deploy without `data/`, upload the CSVs to Google Drive and add their file IDs to `DRIVE_FILE_IDS` in `src/data_loader.py`.

Only the label translation tables (`data/*_translations.csv`, `data/statement_labels.csv`) are versioned.
