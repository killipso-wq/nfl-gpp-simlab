# Contributing to NFL GPP SimLab

Principles
- UI‑first: end users interact via the Streamlit UI. Avoid adding CLI usage or instructions.
- Keep docs clear and task‑oriented. Deep technical details live in docs/.

Local development
- Python 3.10+
- Install: pip install -r requirements.txt
- Run UI: streamlit run app.py
- Data persistence: outputs live under:
  - data/sim_week/{season}_w{week}_{timestamp}/
  - data/lineups/{season}_w{week}_{timestamp}/
  - data/generated/
- On Render, attach a Disk so data/ persists; use:
  - Start Command: streamlit run app.py --server.address 0.0.0.0 --server.port $PORT

Pull requests
- Keep changes scoped. Update README only with UI‑first instructions.
- Add or update docs under docs/ when introducing new concepts or modules.
- Approve workflows: maintainers may need to click "Approve workflows to run" on first run of new Actions.

Documentation
- README.md: concise quick start + UI workflow.
- docs/ROADMAP.md: checklists and planned work.
- docs/master_reference.md: methodology, outputs, governance.
- docs/archive/: historical snapshots as needed.

Support
- Open issues or PRs with clear scope. Reference "Realistic NFL Monte Carlo Simulation.pdf" for simulator behavior when relevant.