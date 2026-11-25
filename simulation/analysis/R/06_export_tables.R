
# ============================================================
# Master's Research Project
# 06_export_tables.R
#
# Purpose:
# Generate publication-ready LaTeX tables for the IEEE paper.
# ============================================================

suppressPackageStartupMessages({
  library(tidyverse)
  library(knitr)
})

cat("\n=== PUBLICATION TABLE GENERATION ===\n")

# ------------------------------------------------------------
# 1. Configuration
# ------------------------------------------------------------

input_dir <- "tables/csv"
output_dir <- "tables/latex"

dir.create(
  output_dir,
  recursive = TRUE,
  showWarnings = FALSE
)

policy_order <- c(
  "Baseline",
  "Availability",
  "Smart V1",
  "Smart V2"
)

metric_labels <- c(
  avg_time_to_parking = "Time to parking (s)",
  avg_parking_search_time = "Parking search time (s)",
  avg_waiting_time = "Waiting time (s)",
  avg_time_loss = "Time loss (s)",
  avg_distance_m = "Driving distance (m)",
  avg_walking_distance_m = "Walking distance (m)",
  avg_co2_g = "CO2 emissions (g)"
)

core_metrics <- c(
  "avg_parking_search_time",
  "avg_distance_m",
  "avg_walking_distance_m",
  "avg_co2_g"
)

# ------------------------------------------------------------
# 2. Helper functions
# ------------------------------------------------------------

load_table <- function(filename) {

  path <- file.path(input_dir, filename)

  stopifnot(file.exists(path))

  read_csv(
    path,
    show_col_types = FALSE
  )
}

format_number <- function(x, digits = 2) {

  ifelse(
    is.na(x),
    "--",
    formatC(
      x,
      format = "f",
      digits = digits,
      big.mark = ","
    )
  )
}

format_p <- function(x) {

  vapply(
    x,
    function(p) {

      if (is.na(p)) {
        return("--")
      }

      if (p < 0.001) {
        return(
          formatC(
            p,
            format = "e",
            digits = 2
          )
        )
      }

      formatC(
        p,
        format = "f",
        digits = 4
      )
    },
    character(1)
  )
}

format_percentage <- function(x) {

  ifelse(
    is.na(x),
    "--",
    sprintf("%+.2f", x)
  )
}

format_ci <- function(lower, upper) {

  ifelse(
    is.na(lower) | is.na(upper),
    "--",
    paste0(
      "[",
      format_number(lower),
      ", ",
      format_number(upper),
      "]"
    )
  )
}

exported_files <- character()

# ------------------------------------------------------------
# 3. Reusable LaTeX export function
# ------------------------------------------------------------

export_latex <- function(
    df,
    filename,
    caption,
    label,
    wide = FALSE,
    note = NULL
) {

  environment <- if (wide) {
    "table*"
  } else {
    "table"
  }

  table_body <- knitr::kable(
    df,
    format = "latex",
    booktabs = TRUE,
    escape = TRUE,
    row.names = FALSE,
    align = c(
      "l",
      rep("r", ncol(df) - 1)
    )
  )

  width_command <- if (wide) {
    "\\textwidth"
  } else {
    "\\columnwidth"
  }

  latex <- c(
    paste0("\\begin{", environment, "}[t]"),
    "\\centering",
    paste0("\\caption{", caption, "}"),
    paste0("\\label{tab:", label, "}"),
    "\\small",
    "\\setlength{\\tabcolsep}{4pt}",
    paste0(
      "\\begin{adjustbox}{max width=",
      width_command,
      "}"
    ),
    as.character(table_body),
    "\\end{adjustbox}"
  )

  if (!is.null(note)) {

    latex <- c(
      latex,
      "\\par\\smallskip",
      paste0(
        "\\begin{minipage}{",
        width_command,
        "}"
      ),
      "\\footnotesize",
      note,
      "\\end{minipage}"
    )
  }

  latex <- c(
    latex,
    paste0("\\end{", environment, "}")
  )

  path <- file.path(
    output_dir,
    paste0(filename, ".tex")
  )

  writeLines(latex, path)

  exported_files <<- c(
    exported_files,
    path
  )

  cat("Exported:", filename, "\n")
}

# ------------------------------------------------------------
# 4. Load statistical results
# ------------------------------------------------------------

reliability <- load_table(
  "simulation_reliability_summary.csv"
)

primary_tests <- load_table(
  "primary_statistical_tests.csv"
)

occupancy_tests <- load_table(
  "primary_occupancy_tests.csv"
)

occupancy_interactions <- load_table(
  "primary_occupancy_interaction_tests.csv"
)

demand_interactions <- load_table(
  "primary_demand_interaction_tests.csv"
)

supplementary_tests <- load_table(
  "supplementary_statistical_tests.csv"
)

network_means <- load_table(
  "supplementary_network_mean_table.csv"
)

network_tests <- load_table(
  "supplementary_network_statistical_tests.csv"
)

# ------------------------------------------------------------
# Table 01: Experimental configuration
# ------------------------------------------------------------

table01 <- tibble(
  Parameter = c(
    "Parking areas",
    "Physical parking capacity",
    "Campus destinations",
    "Parking vehicles per trial",
    "Low-demand background vehicles",
    "Normal-demand background vehicles",
    "Peak-demand background vehicles",
    "Normal parking occupancy",
    "High parking occupancy",
    "Departure-order seeds",
    "Parking policies"
  ),

  Value = c(
    "121",
    "5,887",
    "5",
    "40",
    "15",
    "29",
    "116",
    "Approximately 40%",
    "Approximately 90%",
    "42--46",
    "4"
  )
)

export_latex(
  table01,
  "table01_experimental_configuration",
  "Simulation Experimental Configuration",
  "experimental_configuration"
)

# ------------------------------------------------------------
# Table 02: Experimental dataset distribution
# ------------------------------------------------------------

table02 <- tibble(
  Dataset = c(
    "Preliminary",
    "Primary",
    "Supplementary (balanced)",
    "Supplementary (exploratory)",
    "Total"
  ),

  Conditions = c(1, 6, 1, 1, 9),

  Trials = c(
    20, 120, 20, 4, 164
  ),

  Observations = c(
    800, 4800, 800, 160, 6560
  )
)

export_latex(
  table02,
  "table02_dataset_distribution",
  "Distribution of Completed Experimental Trials",
  "dataset_distribution",
  wide = TRUE,

  note = paste(
    "Observations refer to parking vehicle observations,",
    "not independent statistical replicates.",
    "Experimental batches were analyzed separately."
  )
)

# ------------------------------------------------------------
# Table 03: Simulation reliability
# ------------------------------------------------------------

table03 <- reliability %>%

  transmute(
    Dataset,
    Trials,
    Vehicles,
    `Successful parking` = Successful_Parking,
    `Completed returns` = Completed_Returns,
    Teleports,
    `Parking success (%)` =
      format_number(Parking_Success_Pct, 1)
  )

export_latex(
  table03,
  "table03_simulation_reliability",
  "Simulation Reliability for Completed Trials",
  "simulation_reliability",
  wide = TRUE,

  note = paste(
    "Results apply only to completed experimental trials.",
    "Unsuccessful supplementary simulation attempts",
    "are not included in these totals."
  )
)

# ------------------------------------------------------------
# Table 04: Parking optimization weights
# ------------------------------------------------------------

table04 <- tibble(
  Policy = c(
    "Smart V1",
    "Smart V2"
  ),

  Driving = c(
    "0.25",
    "0.45"
  ),

  Walking = c(
    "0.60",
    "0.40"
  ),

  Occupancy = c(
    "0.15",
    "0.15"
  )
)

export_latex(
  table04,
  "table04_policy_weights",
  "Weighted Parking Assignment Parameters",
  "policy_weights",

  note = paste(
    "The weights sum to one for each policy.",
    "They represent selected experimental configurations",
    "rather than globally optimized parameters."
  )
)

# ------------------------------------------------------------
# 5. Performance table helper
# ------------------------------------------------------------

create_performance_table <- function(tests) {

  baseline <- tests %>%

    group_by(metric) %>%

    summarise(
      mean = first(baseline_mean),
      .groups = "drop"
    ) %>%

    mutate(
      policy = "Baseline"
    )

  alternatives <- tests %>%

    transmute(
      metric,
      policy = comparison_policy,
      mean = policy_mean
    )

  bind_rows(
    baseline,
    alternatives
  ) %>%

    filter(metric %in% names(metric_labels)) %>%

    mutate(
      Metric = unname(metric_labels[metric]),

      Metric = factor(
        Metric,
        levels = unname(metric_labels)
      ),

      mean = format_number(mean)
    ) %>%

    select(
      Metric,
      policy,
      mean
    ) %>%

    pivot_wider(
      names_from = policy,
      values_from = mean
    ) %>%

    arrange(Metric) %>%

    select(
      Metric,
      all_of(policy_order)
    )
}

# ------------------------------------------------------------
# Table 05: Primary performance
# ------------------------------------------------------------

table05 <- create_performance_table(
  primary_tests
)

export_latex(
  table05,
  "table05_primary_performance",
  "Mean Performance in the Primary Experiments",
  "primary_performance",
  wide = TRUE,

  note = paste(
    "Values represent mean per-parking-vehicle performance",
    "across 30 trials per policy."
  )
)

# ------------------------------------------------------------
# Table 06: Primary percentage changes
# ------------------------------------------------------------

table06 <- primary_tests %>%

  filter(metric %in% names(metric_labels)) %>%

  mutate(
    Metric = unname(metric_labels[metric]),

    Metric = factor(
      Metric,
      levels = unname(metric_labels)
    ),

    Change = format_percentage(
      percentage_change
    )
  ) %>%

  select(
    Metric,
    comparison_policy,
    Change
  ) %>%

  pivot_wider(
    names_from = comparison_policy,
    values_from = Change
  ) %>%

  arrange(Metric) %>%

  select(
    Metric,
    all_of(policy_order[-1])
  )

export_latex(
  table06,
  "table06_primary_percentage_changes",
  "Percentage Change Relative to Baseline in the Primary Experiments",
  "primary_percentage_changes",
  wide = TRUE,

  note = paste(
    "All values are percentages.",
    "Negative values indicate reductions",
    "relative to the baseline policy."
  )
)

# ------------------------------------------------------------
# 6. Statistical comparison table helper
# ------------------------------------------------------------

create_test_table <- function(tests) {

  tests %>%

    transmute(
      Metric = unname(metric_labels[metric]),

      Policy = comparison_policy,

      Difference = format_number(
        mean_difference
      ),

      `95% CI` = format_ci(
        ci_lower,
        ci_upper
      ),

      `Adjusted p` = format_p(
        p_adjusted
      )
    )
}

# ------------------------------------------------------------
# Table 07: Primary paired statistical comparisons
# ------------------------------------------------------------

table07 <- primary_tests %>%

  filter(metric %in% core_metrics) %>%

  arrange(
    match(metric, core_metrics),
    match(
      comparison_policy,
      policy_order
    )
  ) %>%

  create_test_table()

export_latex(
  table07,
  "table07_primary_statistical_tests",
  "Paired Policy Comparisons for Primary Performance Metrics",
  "primary_statistical_tests",
  wide = TRUE,

  note = paste(
    "Differences are calculated as policy minus baseline.",
    "Each comparison uses five matched seed blocks.",
    "Confidence intervals are unadjusted.",
    "P-values use Holm correction within the primary",
    "overall comparison family."
  )
)

# ------------------------------------------------------------
# Table 08: High-occupancy performance
# ------------------------------------------------------------

table08 <- occupancy_tests %>%

  filter(
    occupancy == "High"
  ) %>%

  create_performance_table()

export_latex(
  table08,
  "table08_high_occupancy_performance",
  "Mean Primary Performance Under High Parking Occupancy",
  "high_occupancy_performance",
  wide = TRUE,

  note = paste(
    "Results represent 15 trials per policy",
    "across three traffic demand levels."
  )
)

# ------------------------------------------------------------
# Table 09: Occupancy and demand effects
# ------------------------------------------------------------

occupancy_rows <- occupancy_interactions %>%

  filter(
    comparison_policy == "Availability",
    metric %in% core_metrics
  ) %>%

  transmute(
    Factor = "Occupancy",
    Policy = comparison_policy,
    Metric = unname(metric_labels[metric]),

    Contrast = "High - Normal",

    Difference = format_number(
      mean_difference
    ),

    `Adjusted p` = format_p(
      p_adjusted
    )
  )

demand_rows <- demand_interactions %>%

  filter(
    metric == "avg_parking_search_time",
    contrast == "peak_vs_low"
  ) %>%

  transmute(
    Factor = "Demand",
    Policy = comparison_policy,
    Metric = unname(metric_labels[metric]),

    Contrast = "Peak - Low",

    Difference = format_number(
      mean_difference
    ),

    `Adjusted p` = format_p(
      p_adjusted
    )
  )

table09 <- bind_rows(
  occupancy_rows,
  demand_rows
)

export_latex(
  table09,
  "table09_condition_effects",
  "Selected Occupancy and Traffic Demand Effect Contrasts",
  "condition_effects",
  wide = TRUE,

  note = paste(
    "Contrasts represent changes in policy effects",
    "relative to baseline between experimental conditions.",
    "Holm correction was applied separately to the",
    "occupancy and demand comparison families.",
    "Selected contrasts are presented for brevity."
  )
)

# ------------------------------------------------------------
# Table 10: Supplementary parking performance
# ------------------------------------------------------------

table10 <- create_performance_table(
  supplementary_tests
)

export_latex(
  table10,
  "table10_supplementary_performance",
  "Mean Performance in the Balanced Supplementary Experiments",
  "supplementary_performance",
  wide = TRUE,

  note = paste(
    "Destination-informed experiments under low traffic",
    "demand and normal parking occupancy.",
    "Five trials per policy.",
    "The four exploratory high-occupancy trials are excluded."
  )
)

# ------------------------------------------------------------
# Table 11: Network-level performance
# ------------------------------------------------------------

table11 <- network_means %>%

  rename(
    Metric = metric_label
  ) %>%

  mutate(
    across(
      all_of(policy_order),
      ~ format_number(.x)
    )
  ) %>%

  select(
    Metric,
    all_of(policy_order)
  )

export_latex(
  table11,
  "table11_network_performance",
  "Network and Background Vehicle Performance",
  "network_performance",
  wide = TRUE,

  note = paste(
    "Results are based on the balanced supplementary",
    "experiments with 55 vehicles per trial, including",
    "40 parking vehicles and 15 background vehicles."
  )
)

# ------------------------------------------------------------
# Table 12: Significant network-level comparisons
# ------------------------------------------------------------

table12 <- network_tests %>%

  filter(
    !is.na(p_adjusted),
    p_adjusted < 0.05
  ) %>%

  transmute(
    Metric = metric_label,

    Policy = comparison_policy,

    Difference = format_number(
      mean_difference
    ),

    `Change (%)` = format_percentage(
      percentage_change
    ),

    `95% CI` = format_ci(
      ci_lower,
      ci_upper
    ),

    `Adjusted p` = format_p(
      p_adjusted
    )
  )

export_latex(
  table12,
  "table12_network_statistical_tests",
  "Network-Level Comparisons Significant After Holm Correction",
  "network_statistical_tests",
  wide = TRUE,

  note = paste(
    "Each comparison uses five matched seed blocks.",
    "Confidence intervals are unadjusted.",
    "Holm correction was applied to the network-level",
    "comparison family.",
    "These supplementary findings are exploratory."
  )
)

# ------------------------------------------------------------
# 7. Validate exported files
# ------------------------------------------------------------

stopifnot(
  length(exported_files) == 12,
  all(file.exists(exported_files)),
  all(file.info(exported_files)$size > 0),
  nrow(table07) == 12,
  nrow(table12) == 4
)

# ------------------------------------------------------------
# 8. Generate LaTeX table manifest
# ------------------------------------------------------------

manifest <- tibble(
  Table = basename(exported_files),

  Bytes = file.info(
    exported_files
  )$size
)

write_csv(
  manifest,
  file.path(
    output_dir,
    "table_manifest.csv"
  )
)

cat("\n=== EXPORTED TABLE MANIFEST ===\n")

print(
  manifest,
  n = Inf,
  width = Inf
)

# ------------------------------------------------------------
# 9. Final summary
# ------------------------------------------------------------

cat("\n============================================\n")
cat("LATEX TABLE GENERATION COMPLETED\n")
cat("============================================\n")

cat(
  "LaTeX tables generated:",
  length(exported_files),
  "\n"
)

cat(
  "Significant network comparisons:",
  nrow(table12),
  "\n"
)

cat("Tables saved to tables/latex/\n")
cat("Table manifest generated.\n")
