# ============================================================
# Master's Research Project
# Autonomous Parking Assignment and Campus Traffic Efficiency
#
# Script: 02_descriptive_statistics.R
# Purpose: Calculate descriptive experimental statistics
# ============================================================

library(tidyverse)

# ------------------------------------------------------------
# 1. Load validated datasets
# ------------------------------------------------------------

if (!all(vapply(
  c("preliminary", "primary", "supplementary"),
  exists,
  logical(1)
))) {
  source("R/01_load_validate.R")
}

cat("\n=== DESCRIPTIVE STATISTICAL ANALYSIS ===\n")

# ------------------------------------------------------------
# 2. Define policy labels and ordering
# ------------------------------------------------------------

policy_order <- c(
  "Baseline",
  "Availability",
  "Smart V1",
  "Smart V2"
)

policy_labels <- c(
  baseline = "Baseline",
  availability = "Availability",
  smart = "Smart V1",
  smart_v2 = "Smart V2"
)

# ------------------------------------------------------------
# 3. Define performance metrics
# ------------------------------------------------------------

metric_labels <- c(
  avg_time_to_parking = "Time to Parking (s)",
  avg_parking_search_time = "Parking Search Time (s)",
  avg_waiting_time = "Waiting Time (s)",
  avg_time_loss = "Time Loss (s)",
  avg_distance_m = "Driving Distance (m)",
  avg_walking_distance_m = "Walking Distance (m)",
  avg_co2_g = "CO2 Emissions (g)",
  total_parking_reassignments = "Parking Reassignments"
)

performance_metrics <- names(metric_labels)

# ------------------------------------------------------------
# 4. Prepare analytical datasets
# ------------------------------------------------------------

prepare_data <- function(df) {

  df %>%
    mutate(
      policy = factor(
        recode(policy, !!!policy_labels),
        levels = policy_order
      ),

      demand = case_when(
        str_detect(experiment, "(^|_)low_") ~ "Low",
        str_detect(experiment, "(^|_)normal_") &
          str_detect(experiment, "^normal_") ~ "Normal",
        str_detect(experiment, "^peak_") ~ "Peak",
        TRUE ~ "Unspecified"
      ),

      occupancy = case_when(
        str_detect(experiment, "high_occupancy$") ~ "High",
        str_detect(experiment, "normal_occupancy$") ~ "Normal",
        TRUE ~ "Unspecified"
      ),

      demand = factor(
        demand,
        levels = c("Low", "Normal", "Peak", "Unspecified")
      ),

      occupancy = factor(
        occupancy,
        levels = c("Normal", "High", "Unspecified")
      )
    )
}

preliminary_data <- prepare_data(preliminary)
primary_data <- prepare_data(primary)
supplementary_data <- prepare_data(supplementary)

# Separate balanced supplementary experiments
# from exploratory high-occupancy experiments.

supplementary_balanced <- supplementary_data %>%
  filter(
    demand == "Low",
    occupancy == "Normal"
  )

supplementary_exploratory <- supplementary_data %>%
  filter(
    demand == "Low",
    occupancy == "High"
  )

stopifnot(
  nrow(supplementary_balanced) == 20,
  nrow(supplementary_exploratory) == 4,
  all(primary_data$demand != "Unspecified"),
  all(primary_data$occupancy != "Unspecified")
)

# ------------------------------------------------------------
# 5. Create reusable descriptive statistics function
# ------------------------------------------------------------

calculate_statistics <- function(df, grouping_variables) {

  df %>%
    pivot_longer(
      cols = all_of(performance_metrics),
      names_to = "metric",
      values_to = "value"
    ) %>%

    group_by(
      across(all_of(grouping_variables)),
      metric
    ) %>%

    summarise(
      n = n(),
      mean = mean(value),
      median = median(value),
      sd = sd(value),
      min = min(value),
      q1 = quantile(value, 0.25),
      q3 = quantile(value, 0.75),
      max = max(value),
      .groups = "drop"
    ) %>%

    mutate(
      metric_label = recode(metric, !!!metric_labels)
    )
}

# ------------------------------------------------------------
# 6. Calculate preliminary statistics
# ------------------------------------------------------------

cat("\n=== PRELIMINARY EXPERIMENT STATISTICS ===\n")

preliminary_statistics <- calculate_statistics(
  preliminary_data,
  c("policy")
)

print(
  preliminary_statistics %>%
    select(policy, metric_label, n, mean, sd),
  n = Inf
)

# ------------------------------------------------------------
# 7. Calculate primary overall statistics
# ------------------------------------------------------------

cat("\n=== PRIMARY OVERALL STATISTICS ===\n")

primary_statistics <- calculate_statistics(
  primary_data,
  c("policy")
)

print(
  primary_statistics %>%
    select(policy, metric_label, n, mean, sd),
  n = Inf
)

# ------------------------------------------------------------
# 8. Calculate primary condition-level statistics
# ------------------------------------------------------------

primary_condition_statistics <- calculate_statistics(
  primary_data,
  c("demand", "occupancy", "policy")
)

primary_demand_statistics <- calculate_statistics(
  primary_data,
  c("demand", "policy")
)

primary_occupancy_statistics <- calculate_statistics(
  primary_data,
  c("occupancy", "policy")
)

# ------------------------------------------------------------
# 9. Calculate supplementary statistics
# ------------------------------------------------------------

cat("\n=== BALANCED SUPPLEMENTARY STATISTICS ===\n")

supplementary_statistics <- calculate_statistics(
  supplementary_balanced,
  c("policy")
)

print(
  supplementary_statistics %>%
    select(policy, metric_label, n, mean, sd),
  n = Inf
)

supplementary_condition_statistics <- calculate_statistics(
  supplementary_data,
  c("demand", "occupancy", "policy")
)

supplementary_exploratory_statistics <- calculate_statistics(
  supplementary_exploratory,
  c("policy")
)

# ------------------------------------------------------------
# 10. Calculate percentage changes relative to baseline
# ------------------------------------------------------------

calculate_baseline_changes <- function(
    statistics_df,
    condition_variables = character()
) {

  join_columns <- c(condition_variables, "metric")

  baseline_values <- statistics_df %>%
    filter(policy == "Baseline") %>%
    select(
      all_of(join_columns),
      baseline_mean = mean
    )

  statistics_df %>%
    left_join(
      baseline_values,
      by = join_columns
    ) %>%

    mutate(
      absolute_change = mean - baseline_mean,

      percentage_change = if_else(
        baseline_mean == 0,
        NA_real_,
        100 * absolute_change / baseline_mean
      )
    )
}

preliminary_comparison <- calculate_baseline_changes(
  preliminary_statistics
)

primary_comparison <- calculate_baseline_changes(
  primary_statistics
)

primary_condition_comparison <- calculate_baseline_changes(
  primary_condition_statistics,
  c("demand", "occupancy")
)

primary_demand_comparison <- calculate_baseline_changes(
  primary_demand_statistics,
  c("demand")
)

primary_occupancy_comparison <- calculate_baseline_changes(
  primary_occupancy_statistics,
  c("occupancy")
)

supplementary_comparison <- calculate_baseline_changes(
  supplementary_statistics
)

supplementary_exploratory_comparison <- calculate_baseline_changes(
  supplementary_exploratory_statistics
)

# ------------------------------------------------------------
# 11. Generate readable policy comparison tables
# ------------------------------------------------------------

create_mean_table <- function(statistics_df) {

  statistics_df %>%
    select(metric_label, policy, mean) %>%
    mutate(mean = round(mean, 2)) %>%
    pivot_wider(
      names_from = policy,
      values_from = mean
    ) %>%
    select(metric_label, all_of(policy_order))
}

create_percentage_table <- function(comparison_df) {

  comparison_df %>%
    filter(policy != "Baseline") %>%
    select(metric_label, policy, percentage_change) %>%
    mutate(
      percentage_change = round(percentage_change, 2)
    ) %>%
    pivot_wider(
      names_from = policy,
      values_from = percentage_change
    ) %>%
    select(metric_label, all_of(policy_order[-1]))
}

primary_mean_table <- create_mean_table(
  primary_statistics
)

primary_percentage_table <- create_percentage_table(
  primary_comparison
)

supplementary_mean_table <- create_mean_table(
  supplementary_statistics
)

supplementary_percentage_table <- create_percentage_table(
  supplementary_comparison
)

cat("\n=== PRIMARY MEAN COMPARISON ===\n")

print(primary_mean_table, n = Inf, width = Inf)

cat("\n=== PRIMARY PERCENTAGE CHANGE FROM BASELINE ===\n")

print(primary_percentage_table, n = Inf, width = Inf)

cat("\n=== SUPPLEMENTARY MEAN COMPARISON ===\n")

print(supplementary_mean_table, n = Inf, width = Inf)

cat("\n=== SUPPLEMENTARY PERCENTAGE CHANGE FROM BASELINE ===\n")

print(supplementary_percentage_table, n = Inf, width = Inf)

# ------------------------------------------------------------
# 12. Parking reassignment statistics
# ------------------------------------------------------------

reassignment_statistics <- primary_data %>%
  group_by(policy) %>%
  summarise(
    trials = n(),
    total_reassignments = sum(total_parking_reassignments),
    mean_reassignments = mean(total_parking_reassignments),
    sd_reassignments = sd(total_parking_reassignments),
    min_reassignments = min(total_parking_reassignments),
    max_reassignments = max(total_parking_reassignments),
    .groups = "drop"
  )

cat("\n=== PRIMARY PARKING REASSIGNMENT STATISTICS ===\n")

print(reassignment_statistics, width = Inf)

# ------------------------------------------------------------
# 13. Export descriptive statistics
# ------------------------------------------------------------

output_tables <- list(

  preliminary_statistics = preliminary_statistics,
  preliminary_comparison = preliminary_comparison,

  primary_statistics = primary_statistics,
  primary_condition_statistics = primary_condition_statistics,
  primary_demand_statistics = primary_demand_statistics,
  primary_occupancy_statistics = primary_occupancy_statistics,

  primary_comparison = primary_comparison,
  primary_condition_comparison = primary_condition_comparison,
  primary_demand_comparison = primary_demand_comparison,
  primary_occupancy_comparison = primary_occupancy_comparison,

  primary_mean_table = primary_mean_table,
  primary_percentage_table = primary_percentage_table,

  supplementary_statistics = supplementary_statistics,
  supplementary_condition_statistics =
    supplementary_condition_statistics,

  supplementary_comparison = supplementary_comparison,
  supplementary_mean_table = supplementary_mean_table,
  supplementary_percentage_table =
    supplementary_percentage_table,

  supplementary_exploratory_statistics =
    supplementary_exploratory_statistics,

  supplementary_exploratory_comparison =
    supplementary_exploratory_comparison,

  reassignment_statistics = reassignment_statistics
)

dir.create(
  "tables/csv",
  recursive = TRUE,
  showWarnings = FALSE
)

iwalk(
  output_tables,
  function(df, filename) {

    write_csv(
      df,
      file.path(
        "tables/csv",
        paste0(filename, ".csv")
      )
    )
  }
)

# ------------------------------------------------------------
# 14. Final summary
# ------------------------------------------------------------

cat("\n============================================\n")
cat("DESCRIPTIVE STATISTICS COMPLETED\n")
cat("============================================\n")

cat("Preliminary trials:", nrow(preliminary_data), "\n")
cat("Primary trials:", nrow(primary_data), "\n")
cat("Balanced supplementary trials:",
    nrow(supplementary_balanced), "\n")
cat("Exploratory supplementary trials:",
    nrow(supplementary_exploratory), "\n")

cat("Performance metrics:", length(performance_metrics), "\n")
cat("Statistical tables exported:", length(output_tables), "\n")

cat("\nResults saved to tables/csv/\n")
