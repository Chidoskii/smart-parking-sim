# Smart Parking Simulation

## Evaluating Autonomous Vehicle Parking Assignment Strategies and Their Impact on Campus Traffic Efficiency Using SUMO

**Author:** Chidiebere Okpara  
**Institution:** California State Polytechnic University, Pomona  
**Department:** Computer Science  
**Program:** Master of Science in Computer Science  
**Year:** 2026

## Project Overview

This project investigates the impact of autonomous vehicle parking assignment strategies on traffic efficiency within a university campus transportation environment.

The simulation framework integrates the Simulation of Urban Mobility (SUMO), Python-based parking assignment algorithms, a backend communication service, and an interactive geographic visualization interface.

The primary research objective is to evaluate how coordinated parking assignment influences vehicle travel, parking search activity, pedestrian walking distance, traffic congestion, and vehicle emissions under varying traffic demand and parking occupancy conditions.

## Research Objectives

- Evaluate coordinated autonomous vehicle parking assignment strategies.
- Compare conventional parking behavior with availability-based and multi-objective parking assignment.
- Investigate trade-offs between driving distance, walking distance, and parking occupancy.
- Examine the influence of traffic demand and parking scarcity on policy effectiveness.
- Develop a reproducible simulation and statistical analysis framework.
- Evaluate potential network-level transportation impacts.

## Parking Assignment Policies

| Policy       | Description                                                                                 |
| ------------ | ------------------------------------------------------------------------------------------- |
| Baseline     | Conventional parking behavior with localized, reactive parking search.                      |
| Availability | Parking assignment informed by parking availability.                                        |
| Smart V1     | Weighted parking assignment emphasizing destination proximity and reduced walking distance. |
| Smart V2     | Weighted parking assignment with greater emphasis on driving efficiency.                    |

The Smart policies evaluate parking alternatives using a weighted cost function incorporating driving distance, walking distance, and parking occupancy.

### Smart Policy Weights

| Cost Component    | Smart V1 | Smart V2 |
| ----------------- | -------: | -------: |
| Driving distance  |     0.25 |     0.45 |
| Walking distance  |     0.60 |     0.40 |
| Parking occupancy |     0.15 |     0.15 |

## System Architecture

The simulation framework consists of five primary components:

| Component             | Technology                  | Responsibility                                                |
| --------------------- | --------------------------- | ------------------------------------------------------------- |
| Traffic simulation    | SUMO                        | Microscopic vehicle movement and traffic modeling             |
| Simulation controller | Python and TraCI            | Parking assignment, vehicle monitoring, and dynamic routing   |
| Backend               | Node.js, Express, Socket.IO | Simulation communication and data distribution                |
| Frontend              | React, Vite, MapLibre GL JS | Interactive geographic visualization                          |
| Statistical analysis  | R                           | Data validation, statistical comparisons, figures, and tables |

## Experimental Design

The research models the transportation environment surrounding California State Polytechnic University, Pomona.

| Parameter                    | Configuration |
| ---------------------------- | ------------- |
| Parking areas                | 121           |
| Modeled parking spaces       | 5,887         |
| Parking vehicles per trial   | 40            |
| Campus destinations          | 5             |
| Parking policies             | 4             |
| Traffic demand levels        | 3             |
| Parking occupancy levels     | 2             |
| Experimental seeds           | 42–46         |
| Completed research trials    | 164           |
| Parking-vehicle observations | 6,560         |

### Traffic Demand

| Demand Level | Parking Vehicles | Background Vehicles | Total Vehicles |
| ------------ | ---------------: | ------------------: | -------------: |
| Low          |               40 |                  15 |             55 |
| Normal       |               40 |                  29 |             69 |
| Morning Peak |               40 |                 116 |            156 |

### Parking Occupancy

| Occupancy Condition | Initial Occupancy | Available Spaces |
| ------------------- | ----------------: | ---------------: |
| Normal              | Approximately 40% |            3,532 |
| High                | Approximately 90% |              589 |

### Experimental Datasets

| Experimental Phase | Completed Trials | Parking-Vehicle Observations |
| ------------------ | ---------------: | ---------------------------: |
| Preliminary        |               20 |                          800 |
| Primary            |              120 |                        4,800 |
| Supplementary      |               24 |                          960 |
| **Total**          |          **164** |                    **6,560** |

The primary experiments use a balanced factorial design. The supplementary experiments investigate destination-informed initial parking assignment and refined routing configurations.

The supplementary dataset contains a balanced low-demand, normal-occupancy subset of 20 trials and four exploratory high-occupancy trials. Not all originally planned supplementary experiments completed successfully.

## Performance Metrics

The experimental framework evaluates:

- Time to parking
- Parking search time
- Vehicle driving distance
- Pedestrian walking distance
- Vehicle waiting time
- Traffic time loss
- Carbon dioxide emissions
- Parking reassignment activity
- Network-level transportation performance
- Background vehicle performance

## Repository Structure

```text
smart-parking-sim/
├── backend/
│   ├── scripts/
│   └── src/
├── frontend/
│   ├── public/
│   └── src/
├── shared/
│   ├── config/
│   └── geojson/
├── data/
├── simulation/
│   ├── analysis/
│   │   ├── data/
│   │   ├── R/
│   │   ├── README.md
│   │   └── renv.lock
│   ├── experiments/
│   │   ├── configs/
│   │   └── experiment_runner.py
│   ├── results/
│   ├── scripts/
│   │   ├── analysis/
│   │   ├── diagnostics/
│   │   ├── exports/
│   │   └── generators/
│   ├── src/
│   │   └── parking_policies/
│   ├── sumo/
│   │   ├── additionals/
│   │   ├── config/
│   │   ├── network/
│   │   ├── routes/
│   │   └── scenarios/
│   ├── tests/
│   └── requirements.txt
└── README.md
```

## Installation

### Prerequisites

The research framework was developed and evaluated using
the following software environment:

| Software         | Version    |
| ---------------- | ---------- |
| Operating System | Windows 11 |
| Python           | 3.14.3     |
| Eclipse SUMO     | 1.27.1     |
| Node.js          | 25.6.1     |
| npm              | 11.9.0     |
| R                | 4.6.2      |
| Git              | Required   |

These versions document the research environment.
Compatibility with other software versions and operating
systems has not been formally evaluated.

SUMO installation instructions:
https://sumo.dlr.de/docs/Installing/index.html

Ensure that SUMO and Rscript are available through the
system PATH and that the SUMO TraCI Python tools are
accessible.

### Clone the Repository

```bash
git clone https://github.com/Chidoskii/smart-parking-sim.git
cd smart-parking-sim
```

### Python Environment

Create a virtual environment:

```bash
python -m venv .venv
```

Activate the environment on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Alternatively, on Linux or macOS:

```bash
source .venv/bin/activate
```

Install the Python dependencies:

```bash
python -m pip install -r simulation/requirements.txt
```

Verify the SUMO installation:

```bash
sumo --version
```

## Interactive Visualization

The backend and frontend provide an interactive visualization environment for monitoring simulated vehicle activity and parking occupancy.

### Backend

From the repository root, open a PowerShell terminal:

```powershell
cd backend
npm ci
Copy-Item .env.example .env
npm start
```

The backend runs on port 5000 by default.

For development with automatic server restarts, use:

```powershell
npm run dev
```

The backend uses Express and Socket.IO to provide
REST API endpoints and real-time simulation updates.

### Frontend

In a separate terminal, from the repository root:

```powershell
cd frontend
npm ci
Copy-Item .env.example .env
npm run dev
```

The frontend communicates with the backend through the configured API endpoint.

## Running Simulation Experiments

All experiment runner commands should be executed from the repository root.

Display the available command-line arguments:

```bash
python simulation/experiments/experiment_runner.py --help
```

### Preliminary Experiments

```bash
python simulation/experiments/experiment_runner.py --config simulation/experiments/experiment_config.json
```

### Primary Experiments

```bash
python simulation/experiments/experiment_runner.py --config simulation/experiments/main_experiment_config.json
```

### Supplementary Experiments

```bash
python simulation/experiments/experiment_runner.py --config simulation/experiments/final_experiment_config.json
```

The experiment runner supports configuration selection, custom report directories, report-only aggregation, and termination upon encountering an error.

Review the experiment configuration files before execution. The current configurations may require additional environment setup, and executing the supplementary configuration does not guarantee reproduction of the exact set of successfully completed research trials.

## Research Data and Statistical Analysis

The experimental datasets used in the research are included in the repository.

```text
simulation/analysis/data/
├── preliminary/
│   └── experiment_reports_completed.csv
├── primary/
│   └── main_experiment_reports_completed.csv
└── supplementary/
    └── final_experiment_reports_completed.csv
```

The statistical analysis pipeline performs:

1. Experimental data loading and validation.
2. Descriptive statistical analysis.
3. Matched-seed statistical comparisons.
4. Primary experimental visualizations.
5. Supplementary and network-level visualizations.
6. Research table generation.

The analysis includes paired statistical comparisons, confidence intervals, standardized effect sizes, exact sign tests, and Holm multiple-comparison adjustments.

### Windows R Configuration

If Rscript is not recognized in PowerShell, add the R
installation directory to the current terminal's PATH:

```powershell
$env:Path = "C:\Program Files\R\R-4.6.2\bin;$env:Path"
```

Adjust the installation path if necessary.

Verify the installation:

```powershell
Rscript --version
```

### Reproduce the Statistical Analysis

Navigate to the analysis directory:

```bash
cd simulation/analysis
```

Restore the R dependency environment:

```bash
Rscript -e "renv::restore()"
```

Execute the complete analysis pipeline:

```bash
Rscript run_analysis.R
```

The analysis pipeline generates research tables, visualizations, statistical results, and reproducibility metadata.

For detailed instructions, see the [Research Analysis README](simulation/analysis/README.md).

The archived experimental datasets allow the statistical analysis to be reproduced without rerunning the SUMO experiments.

## Research Findings

The experimental results demonstrate that parking assignment effectiveness depends on parking scarcity, initial parking assignment, and the relative importance assigned to driving and walking efficiency.

Availability-based parking assignment reduced parking search activity in the primary experiments, particularly under high parking occupancy.

The Smart policies substantially reduced pedestrian walking distance but introduced additional vehicle travel and emissions under the primary experimental configuration.

The supplementary experiments demonstrated improved vehicle-level performance under destination-informed initial parking assignment and refined routing configurations.

These findings highlight the importance of considering both vehicle and pedestrian transportation objectives when designing coordinated parking assignment strategies.

## Research Limitations

- The simulation represents a modeled campus environment rather than a calibrated deployment of real-world autonomous vehicles.
- Autonomous vehicle behavior is represented primarily through parking assignment and routing decisions.
- Walking distances are estimated rather than generated through a complete pedestrian simulation.
- Experimental comparisons use a limited number of matched random seeds.
- Parking occupancy scenarios use a fixed initial occupancy distribution.
- Supplementary experimental configurations differ from the primary configurations.
- Not all planned supplementary trials completed successfully.
- Simulation-based emissions are model estimates rather than direct physical measurements.

## Geographic Data and Third-Party Attribution

The SUMO road network incorporates geographic data derived from OpenStreetMap.

© OpenStreetMap contributors.

https://www.openstreetmap.org/copyright

OpenStreetMap data is made available under the Open Database License (ODbL).

SUMO is developed by the German Aerospace Center (DLR) and other contributors.

https://sumo.dlr.de/

Third-party software and geographic data remain subject to their respective licensing and attribution requirements.

## Citation

If you use this repository in academic research, please cite the associated research software:

```bibtex
@misc{okpara2026smartparking,
  author       = {Chidiebere Okpara},
  title        = {Smart Parking Simulation:
                  Autonomous Vehicle Parking
                  Assignment Framework},
  year         = {2026},
  howpublished = {GitHub repository},
  url          = {https://github.com/Chidoskii/smart-parking-sim}
}
```

## Author

Chidiebere Okpara

Master of Science in Computer Science  
California State Polytechnic University, Pomona

GitHub: https://github.com/Chidoskii

## License

Third-party software, geographic data, and other externally sourced materials remain subject to their respective licenses.
