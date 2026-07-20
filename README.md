# EUF — Harvest Dashboard

Interactive dashboard for tracking and analyzing Easton Urban Farm harvest records across crop types, distribution channels, and seasonal patterns.

## Features

- **Harvest by Crop Type** — Stacked bar chart showing total harvest (lbs) broken down by distribution destination (Food Pantry, donations, etc.)
- **Pots Distributed** — Bar chart tracking community garden starts (potted seedlings given to neighbors)
- **Harvest Calendar** — Weekly heatmap showing when each crop was harvested and relative intensity throughout the season

## Data

- **Source:** `harvest_tracker_euf_20260719.xlsx` (updated weekly)
- **Unit handling:**
  - Weight (lbs) — direct measurement
  - Bunches (herbs) — converted to ~0.5 lbs per bunch
  - Pots — individual seedlings for community distribution
  - Bins — unweighed harvested bins (tracked separately)

## Deployment

This app is deployed on **Streamlit Cloud** for easy stakeholder access.

**To run locally:**
```bash
pip install -r requirements.txt
streamlit run harvest_dashboard_app.py
```

## Files

- `harvest_dashboard_app.py` — Streamlit app (main dashboard)
- `harvest_dashboard.ipynb` — Jupyter notebook (development/analysis)
- `requirements.txt` — Python dependencies
- `harvest_tracker_euf_20260719.xlsx` — Data file (not committed to repo)

---

**Last updated:** July 20, 2026
