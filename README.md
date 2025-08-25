# NFL GPP SimLab

A Streamlit app for an end‑to‑end GPP workflow:
- Simulator → runs a Monte Carlo engine to generate realistic projections and a large pool of candidate lineups
- GPP Blueprint (post‑sim curation) → selects a final portfolio via stacking, ownership, salary, and diversity constraints
- Optimizer tab → apply presets (Solo, 20‑max, 150‑max), tweak constraints, export CSV/JSON

Reference: see "Realistic NFL Monte Carlo Simulation.pdf" in this repo for the simulator's methodology.

## Quick start (UI only)
- Local
  - pip install -r requirements.txt
  - streamlit run app.py
- Render (recommended)
  - Build Command: pip install -r requirements.txt
  - Start Command: streamlit run app.py --server.address 0.0.0.0 --server.port $PORT
  - Persistence: attach a Disk so data/ persists between restarts

## Workflow
1) Simulator
   - Runs the Monte Carlo engine per "Realistic NFL Monte Carlo Simulation.pdf" to generate per‑player distributions and a large lineup pool.
   - Outputs: data/sim_week/{season}_w{week}_{timestamp}/ and a ZIP download from the UI.
2) GPP Blueprint (post‑sim curation)
   - Apply stacking, ownership caps, salary min/max, and diversity to the simulated lineup pool.
   - Use Presets: Solo, 20‑max, 150‑max; adjust any constraint before building.
3) Export
   - Download curated lineups as CSV/JSON for upload.

## Using the app
- Simulator tab
  - Configure Season/Week and sim parameters exposed by the PDF spec; run sims.
  - Preview outputs; download ZIP; Send to Curation forwards the lineup pool.
- Optimizer tab
  - Curate from Simulator outputs (recommended): load the simulated lineup pool and apply the GPP Blueprint.
  - Build from projections (optional): if you don't have a simulated pool, you can generate lineups from a players.csv, then apply the same presets.

## Files and persistence
- Sim outputs: data/sim_week/{season}_w{week}_{timestamp}/
- Curated lineups: data/lineups/{season}_w{week}_{timestamp}/
- Generated inputs (optional): data/generated/
- On Render, attach a Disk so these persist; otherwise use the ZIP download buttons in the UI.

## Notes
- The UI is the only supported way to run the app; no CLI is required or documented.
- New workflows added to the repo may require maintainer approval before first run (see the PR's "Approve workflows to run" banner).

## Documentation
- Roadmap and task lists: docs/ROADMAP.md
- Master reference (methodology, outputs, governance): docs/master_reference.md

## Contributing
- Small changes via PR are welcome. Keep README UI‑first and avoid adding CLI usage.
- For simulator details, see docs/ (and "Realistic NFL Monte Carlo Simulation.pdf").
