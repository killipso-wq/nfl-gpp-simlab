# NFL GPP Sim Optimizer

A Monte Carlo simulator for NFL DFS that generates advanced projections and GPP strategy insights through an intuitive Streamlit interface.

**Methodology**: This app implements the simulation framework detailed in [Realistic NFL Monte Carlo Simulation.pdf](https://github.com/user-attachments/files/21975791/Realistic.NFL.Monte.Carlo.Simulation.pdf), our governing specification for simulator behavior.

## Quick Start

### Local Development
```bash
pip install -r requirements.txt
streamlit run app.py
```

### Render Deployment

**Standard Setup:**
- Service connected to GitHub repository
- Start command: `streamlit run app.py`
- Environment: `STREAMLIT_SERVER_MAX_UPLOAD_SIZE=300` (optional, for larger uploads)

**Paid Plan with Data Persistence:**
- Attach a Disk to your service so `data/` persists across deployments
- Keep existing port/address flags in your configuration
- Manual Deploy → Clear build cache & deploy after merges

## Workflow: Simulator → GPP Blueprint → Export

### 1. Simulator Tab
- **Upload** your site's players.csv file (PLAYER, POS, TEAM, OPP, FPTS, SAL, RST%, etc.)
- **Configure** simulation parameters (number of sims, random seed)
- **Review** column mapping and any warnings
- **Run** Monte Carlo simulation
- **Download** results: sim_players.csv, compare.csv, diagnostics_summary.csv, flags.csv, or complete ZIP bundle

### 2. Optimizer Tab
The Optimizer tab primarily curates from Simulator outputs to apply GPP strategy:
- **GPP Presets**: Apply proven strategy blueprints using simulator outputs
  - Contest size presets (Small/Mid/Large field)
  - Ownership bands, boom thresholds, dart requirements
  - Stack configurations and salary management
- **Build from Projections** (optional): Generate players.csv directly from nfl_data_py when no site file available

### 3. Export and Deploy
- Download optimized lineups
- Review ownership distribution and uniqueness
- Upload to your DFS platform

## Key Features

### Advanced Projections
- **Monte Carlo simulation** based on 2023-2024 NFL data
- **Boom probability** and ceiling projections for GPP optimization
- **Value metrics** per $1k salary for stack efficiency
- **Dart identification** for low-owned tournament leverage

### Smart Diagnostics
- **Accuracy metrics**: MAE, RMSE, correlation vs site projections
- **Coverage analysis**: How often site projections fall within sim ranges
- **Flag detection**: Outliers and data quality issues
- **Reproducible results** with seeded random number generation

### GPP Strategy Integration
- **Ownership leverage**: Target optimal ownership bands by contest size
- **Stack optimization**: QB correlations with bring-back considerations
- **Salary management**: Contest-specific leftover strategies
- **Uniqueness factors**: Avoid chalk combinations without leverage

## Data Structure

The app manages simulation data across these key directories:

- **`data/sim_week/`**: Individual week simulation outputs
- **`data/lineups/`**: Generated optimal lineup configurations  
- **`data/generated/`**: Processed files and intermediate results

## Player File Format

Upload a CSV with these columns:

**Required:**
- PLAYER, POS, TEAM, OPP

**Optional but Recommended:**
- FPTS (site projection), SAL (salary), RST% (ownership)
- O/U (game total), SPRD (spread) for environment hints
- VAL (site value metric)

The app auto-detects column synonyms and shows mapping warnings for missing fields.

## Simulation Outputs

Each run produces:
- **sim_players.csv**: Projections with floor/ceiling, boom probability
- **compare.csv**: Side-by-side with site data, deltas, value metrics
- **diagnostics_summary.csv**: Accuracy stats by position
- **flags.csv**: Notable outliers and data issues
- **metadata.json**: Run parameters for reproducibility

## Advanced Usage

For CLI tools, batch processing, and developer guidance, see [CONTRIBUTING.md](CONTRIBUTING.md).