# Autonomous Vehicle Parking — Research Analysis

## Overview

This directory contains the statistical analysis, visualization, and publication-output generation pipeline for the Master's research project:

**Evaluating Autonomous Vehicle Parking Assignment Strategies and Their Impact on Campus Traffic Efficiency Using SUMO**

California State Polytechnic University, Pomona
Department of Computer Science

The research investigates how autonomous vehicle parking assignment strategies influence parking efficiency, passenger walking distance, vehicle travel distance, emissions, and traffic network performance within a university campus.

The analysis is implemented in R and uses an automated, reproducible computational pipeline.

## Research Objectives

The primary objectives of this analysis are to:

1. Evaluate the effectiveness of availability-based parking assignment relative to conventional parking behavior.
2. Investigate the trade-off between passenger walking convenience and vehicle traffic efficiency.
3. Determine how parking occupancy and traffic demand influence parking policy effectiveness.
4. Evaluate destination-informed parking assignment.
5. Examine the network-level effects of coordinated parking strategies.
6. Produce reproducible statistical results and publication-ready research outputs.

## Parking Policies

Four parking assignment policies are evaluated.

| Policy       | Description                                                                      |
| ------------ | -------------------------------------------------------------------------------- |
| Baseline     | Conventional preferred parking assignment with localized parking search.         |
| Availability | Availability-based reassignment when preferred parking is unavailable.           |
| Smart V1     | Weighted parking optimization emphasizing passenger walking distance.            |
| Smart V2     | Weighted parking optimization with greater emphasis on vehicle driving distance. |

### Smart Policy Weights

| Cost Component    | Smart V1 | Smart V2 |
| ----------------- | -------: | -------: |
| Driving distance  |     0.25 |     0.45 |
| Walking distance  |     0.60 |     0.40 |
| Parking occupancy |     0.15 |     0.15 |
| Total             |     1.00 |     1.00 |

The weights represent experimentally selected policy configurations rather than globally optimal solutions.

## Experimental Datasets

The analysis uses three separate experimental datasets.

| Dataset                     | Trials | Parking Vehicle Observations |
| --------------------------- | -----: | ---------------------------: |
| Preliminary                 |     20 |                          800 |
| Primary                     |    120 |                        4,800 |
| Supplementary — Balanced    |     20 |                          800 |
| Supplementary — Exploratory |      4 |                          160 |
| Total                       |    164 |                        6,560 |

Each completed simulation trial contains 40 experimental parking vehicles.

The datasets are analyzed separately because changes in parking initialization, routing, and experimental configuration prevent direct pooling of the experimental batches.

### Preliminary Experiments

The preliminary experiments evaluate the four parking policies under high parking occupancy using five randomized departure-order seeds.

These experiments provide an initial evaluation of parking policy behavior and informed the subsequent experimental design.

### Primary Experiments

The primary experimental dataset evaluates:

- Four parking policies.
- Three traffic demand levels.
- Two parking occupancy levels.
- Five randomized departure-order seeds.

The resulting factorial design contains:

4 policies × 3 demand levels × 2 occupancy levels × 5 seeds = 120 simulation trials.

### Supplementary Experiments

The supplementary experiments evaluate destination-informed initial parking assignments and include network-level performance metrics.

The balanced supplementary dataset contains 20 trials under low traffic demand and normal parking occupancy.

Four additional high-occupancy trials are retained for exploratory descriptive analysis.

The exploratory trials are excluded from inferential comparisons because only one matched seed is available.

## Experimental Configuration

| Parameter                               |             Value |
| --------------------------------------- | ----------------: |
| Parking areas                           |               121 |
| Physical parking capacity               |             5,887 |
| Campus destinations                     |                 5 |
| Experimental parking vehicles per trial |                40 |
| Low-demand background vehicles          |                15 |
| Normal-demand background vehicles       |                29 |
| Peak-demand background vehicles         |               116 |
| Normal parking occupancy                | Approximately 40% |
| High parking occupancy                  | Approximately 90% |
| Departure-order seeds                   |             42–46 |

## Directory Structure

```text
analysis/
├── data/
│   ├── preliminary/
│   ├── primary/
│   └── supplementary/
├── R/
│   ├── 01_load_validate.R
│   ├── 02_descriptive_statistics.R
│   ├── 03_statistical_tests.R
│   ├── 04_primary_visualizations.R
│   ├── 05_supplementary_visualizations.R
│   └── 06_export_tables.R
├── figures/
│   ├── pdf/
│   └── png/
├── tables/
│   ├── csv/
│   └── latex/
├── logs/
├── renv/
├── .Rprofile
├── DESCRIPTION
├── renv.lock
├── run_analysis.R
└── README.md
```

## Input Data

The analysis requires the following experimental datasets:

```text
data/preliminary/
    experiment_reports_completed.csv

data/primary/
    main_experiment_reports_completed.csv

data/supplementary/
    final_experiment_reports_completed.csv
```

These files contain trial-level results collected from completed SUMO simulation experiments.

The original experimental datasets should remain unchanged during statistical analysis.

## Software Requirements

The analysis was developed and verified using:

- R version 4.6.2
- Windows 11
- renv
- tidyverse
- patchwork
- broom
- scales
- knitr

The rmarkdown package is also included for optional research reporting.

Package dependencies are managed using renv and recorded in the renv.lock file.

## Environment Setup

Install R before executing the analysis.

From the analysis directory, restore the recorded package environment:

```bash
Rscript -e "renv::restore(prompt = FALSE)"
```

Verify dependency consistency:

```bash
Rscript -e "renv::status()"
```

The expected result is:

```text
No issues found -- the project is in a consistent state.
```

The recorded R version should be used whenever possible. The renv lockfile manages package dependencies but does not install the R runtime itself.

## Running the Analysis

Execute the complete analysis pipeline:

```bash
Rscript run_analysis.R
```

The master script executes all six analytical stages in sequence, creates the required output directories, validates output counts, and records execution information.

Individual stages can also be executed separately from the analysis directory. Stages that depend on previously generated results should be executed in pipeline order.

## Analysis Pipeline

### Stage 1 — Data Loading and Validation

Script: R/01_load_validate.R

Responsibilities:

- Load the experimental datasets.
- Validate required columns and data types.
- Identify missing values.
- Detect duplicate simulation runs.
- Verify experimental balance.
- Validate policy and seed distributions.
- Evaluate simulation completion and reliability.

### Stage 2 — Descriptive Statistics

Script: R/02_descriptive_statistics.R

Responsibilities:

- Calculate descriptive statistics.
- Compare parking policy performance.
- Calculate percentage changes relative to baseline.
- Evaluate traffic demand and occupancy conditions.
- Analyze parking reassignment frequency.
- Export statistical CSV tables.

### Stage 3 — Inferential Statistical Analysis

Script: R/03_statistical_tests.R

Responsibilities:

- Construct matched random-seed comparisons.
- Conduct paired statistical tests.
- Calculate confidence intervals.
- Calculate standardized effect sizes.
- Apply Holm multiple-comparison corrections.
- Conduct exact sign tests.
- Evaluate occupancy and demand effect contrasts.
- Support research hypothesis evaluation.

### Stage 4 — Primary Visualizations

Script: R/04_primary_visualizations.R

Generates 13 research figures covering primary experimental performance, parking policy trade-offs, occupancy effects, traffic demand effects, and matched statistical comparisons.

### Stage 5 — Supplementary and Network Analysis

Script: R/05_supplementary_visualizations.R

Evaluates destination-informed parking assignment and network-level performance.

Generates eight statistical CSV tables and 12 research figures.

### Stage 6 — Publication Tables

Script: R/06_export_tables.R

Generates 12 LaTeX tables suitable for integration into the IEEE research manuscript.

## Statistical Methodology

The inferential analysis uses matched comparisons based on randomized departure-order seeds.

Where multiple experimental conditions contribute to an overall comparison, policy differences are aggregated within each seed before inferential testing.

The seed serves as the matched analytical block. Individual parking vehicle observations are not treated as independent statistical replicates.

Statistical methods include:

- Paired t-tests.
- Unadjusted 95% confidence intervals.
- Cohen's dz effect sizes.
- Holm-adjusted p-values within analytical families.
- Exact two-sided sign tests.
- Occupancy and demand effect contrasts.

Because inferential comparisons contain five matched seed blocks, statistical conclusions should be interpreted with appropriate caution.

The exact two-sided sign test has a minimum attainable p-value of 0.0625 with five nonzero matched differences.

## Performance Metrics

### Parking-Level Metrics

- Parking search time.
- Time to parking.
- Vehicle driving distance.
- Passenger walking distance.
- Vehicle waiting time.
- Vehicle time loss.
- Carbon dioxide emissions.
- Parking reassignment frequency.

### Network-Level Metrics

- Average network vehicle waiting time.
- Average network vehicle time loss.
- Average network vehicle driving distance.
- Total network carbon dioxide emissions.
- Background vehicle waiting time.
- Background vehicle time loss.
- Background vehicle driving distance.
- Background vehicle carbon dioxide emissions.

Network-level metrics are available for the supplementary experimental dataset.

## Generated Research Outputs

A successful execution produces:

| Output                         | Count |
| ------------------------------ | ----: |
| Statistical CSV tables         |    46 |
| Unique research figures        |    25 |
| PDF figure exports             |    25 |
| PNG figure exports             |    25 |
| LaTeX publication tables       |    12 |
| LaTeX table manifest           |     1 |
| Total generated research files |   109 |

Each research figure is exported in PDF and PNG format.

PDF figures support vector-based publication graphics, while PNG figures support presentations and general documentation.

## Figure Index

| Figure | Description                             |
| ------ | --------------------------------------- |
| 01     | Primary parking search time             |
| 02     | Primary driving distance                |
| 03     | Primary walking distance                |
| 04     | Primary carbon dioxide emissions        |
| 05     | Parking occupancy interaction           |
| 06     | Traffic demand interaction              |
| 07     | Primary experimental conditions         |
| 08     | Primary paired policy effects           |
| 09     | Driving and walking distance trade-off  |
| 10     | Parking reassignments                   |
| 11     | Primary percentage-change heatmap       |
| 12     | High-occupancy matched-seed comparisons |
| 13     | Combined primary performance            |
| 14     | Supplementary parking search time       |
| 15     | Supplementary driving distance          |
| 16     | Supplementary walking distance          |
| 17     | Supplementary carbon dioxide emissions  |
| 18     | Network waiting time                    |
| 19     | Network time loss                       |
| 20     | Background vehicle time loss            |
| 21     | Network carbon dioxide emissions        |
| 22     | Network paired policy effects           |
| 23     | Combined supplementary performance      |
| 24     | Combined network performance            |
| 25     | Network percentage-change heatmap       |

## Publication Table Index

| Table | Description                                 |
| ----- | ------------------------------------------- |
| 01    | Experimental configuration                  |
| 02    | Dataset distribution                        |
| 03    | Simulation reliability                      |
| 04    | Parking policy weights                      |
| 05    | Primary performance                         |
| 06    | Primary percentage changes                  |
| 07    | Primary statistical tests                   |
| 08    | High-occupancy performance                  |
| 09    | Experimental condition effects              |
| 10    | Supplementary performance                   |
| 11    | Network performance                         |
| 12    | Significant network statistical comparisons |

## Research Findings

### Primary Experiments

Availability-based parking assignment reduced parking search time, driving distance, and carbon dioxide emissions relative to baseline.

Under high parking occupancy, the Availability policy reduced average parking search time by approximately 9.01%.

Smart V1 reduced passenger walking distance by approximately 45.1%, but increased driving distance by approximately 19.0%.

Smart V2 reduced walking distance by approximately 31.4%, with a smaller driving distance increase of approximately 3.04%.

These findings demonstrate a trade-off between passenger walking convenience and vehicle traffic efficiency.

### Supplementary Experiments

Under the balanced destination-informed experimental configuration, Smart V2 achieved the following changes relative to baseline:

| Metric                        | Percentage Change |
| ----------------------------- | ----------------: |
| Parking search time           |            -34.9% |
| Driving distance              |            -5.84% |
| Parking vehicle CO2 emissions |            -7.73% |
| Time to parking               |            -10.6% |
| Walking distance              |            +3.93% |

These results suggest that parking initialization and assignment configuration can influence the effectiveness of weighted parking optimization.

Differences between experimental batches should not be interpreted as isolated causal effects of destination-informed initialization because routing and implementation changes were also introduced.

### Network-Level Findings

Within the balanced supplementary experiments, Smart V2 reduced total network carbon dioxide emissions by approximately 2.65%.

The reduction was statistically significant under the paired t-test methodology after Holm correction.

Network time loss decreased descriptively by approximately 6.29%, although this result was not statistically significant after multiple-comparison correction.

Background vehicle performance did not demonstrate statistically significant differences after correction.

## Computational Reproducibility

The analysis pipeline was executed successfully within an isolated R package environment managed using renv.

A clean-output reproducibility test was performed by moving previously generated figures and statistical tables outside the project directory and re-executing the complete analysis pipeline.

The verification results were:

| Verification                     | Result   |
| -------------------------------- | -------- |
| Analysis stages completed        | 6 of 6   |
| Statistical CSV checksum matches | 46 of 46 |
| LaTeX table checksum matches     | 12 of 12 |
| PDF figures regenerated          | 25 of 25 |
| PNG figures regenerated          | 25 of 25 |
| Empty figure files               | 0        |
| Dependency consistency           | Passed   |

SHA-256 checksum comparisons confirmed byte-for-byte reproducibility of all 46 statistical CSV files and all 12 LaTeX publication tables.

Figure regeneration was verified through file counts and nonempty file validation.

These results establish local computational reproducibility within the tested environment.

They do not establish cross-platform reproducibility, independent simulation-model validity, or exact visual equivalence of regenerated figures.

## Execution Records

The logs directory contains:

- Pipeline execution manifest.
- Pipeline output validation summary.
- R session information.
- Package version information.
- Input dataset checksums.

These records support auditing and verification of the computational analysis.

## Research Limitations

The analysis should be interpreted in consideration of the following limitations:

- Five randomized departure-order seeds.
- A fixed parking occupancy distribution.
- Simulation-based rather than empirically calibrated traffic behavior.
- Approximate campus destination coordinates.
- Approximate walking distance measurements.
- Fixed weighted optimization parameters.
- Incomplete supplementary high-occupancy experiments.
- Differences in implementation between experimental batches.
- Network-level metrics available only for supplementary experiments.

All 164 completed simulation trials achieved successful parking and return-trip completion without vehicle teleports. This does not imply that every attempted simulation completed successfully.

## Research Status

- Simulation implementation: Complete
- Experimental data collection: Complete
- Statistical analysis: Complete
- Hypothesis evaluation: Complete
- Research visualizations: Complete
- Publication table generation: Complete
- Automated analysis pipeline: Complete
- Local computational reproducibility: Verified
- Final research manuscript: In progress
