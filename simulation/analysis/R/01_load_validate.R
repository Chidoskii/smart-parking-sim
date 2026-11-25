# ============================================================
# Master's Research Project
# Autonomous Parking Assignment and Campus Traffic Efficiency
#
# Script: 01_load_validate.R
# Purpose: Import and validate experimental datasets
# ============================================================

library(tidyverse)

# ------------------------------------------------------------
# 1. Import experimental datasets
# ------------------------------------------------------------

cat("\n=== LOADING EXPERIMENTAL DATASETS ===\n")

preliminary <- read_csv(
  "data/preliminary/experiment_reports_completed.csv",
  show_col_types = FALSE
)

primary <- read_csv(
  "data/primary/main_experiment_reports_completed.csv",
  show_col_types = FALSE
)

supplementary <- read_csv(
  "data/supplementary/final_experiment_reports_completed.csv",
  show_col_types = FALSE
)

datasets <- list(
  Preliminary = preliminary,
  Primary = primary,
  Supplementary = supplementary
)

# ------------------------------------------------------------
# 2. Validate dataset dimensions
# ------------------------------------------------------------

cat("\n=== DATASET DIMENSIONS ===\n")

dataset_summary <- tibble(
  Dataset = names(datasets),
  Rows = map_int(datasets, nrow),
  Columns = map_int(datasets, ncol),
  Expected_Rows = c(20, 120, 24)
) %>%
  mutate(
    Valid = Rows == Expected_Rows
  )

print(dataset_summary)

stopifnot(all(dataset_summary$Valid))

# ------------------------------------------------------------
# 3. Validate required columns
# ------------------------------------------------------------

required_columns <- c(
  "experiment",
  "seed",
  "policy",
  "vehicle_count",
  "avg_time_to_parking",
  "avg_parking_search_time",
  "avg_waiting_time",
  "avg_time_loss",
  "avg_distance_m",
  "avg_walking_distance_m",
  "avg_co2_g",
  "total_parking_reassignments",
  "total_parking_success",
  "total_completed_return_trip",
  "total_teleported",
  "complete",
  "status"
)

cat("\n=== REQUIRED COLUMN VALIDATION ===\n")

for (name in names(datasets)) {

  missing_columns <- setdiff(
    required_columns,
    names(datasets[[name]])
  )

  if (length(missing_columns) > 0) {
    stop(
      name, " is missing columns: ",
      paste(missing_columns, collapse = ", ")
    )
  }

  cat(name, ": All required columns present.\n")
}

# ------------------------------------------------------------
# 4. Validate parsing and numeric data types
# ------------------------------------------------------------

cat("\n=== DATA TYPE VALIDATION ===\n")

numeric_columns <- c(
  "seed",
  "vehicle_count",
  "avg_time_to_parking",
  "avg_parking_search_time",
  "avg_waiting_time",
  "avg_time_loss",
  "avg_distance_m",
  "avg_walking_distance_m",
  "avg_co2_g",
  "total_parking_reassignments",
  "total_parking_success",
  "total_completed_return_trip",
  "total_teleported"
)

for (name in names(datasets)) {

  df <- datasets[[name]]

  stopifnot(nrow(readr::problems(df)) == 0)

  stopifnot(
    all(map_lgl(df[numeric_columns], is.numeric))
  )

  stopifnot(is.logical(df$complete))

  cat(name, ": Data types and parsing valid.\n")
}

# ------------------------------------------------------------
# 5. Check missing values
# ------------------------------------------------------------

cat("\n=== MISSING VALUE ANALYSIS ===\n")

for (name in names(datasets)) {

  df <- datasets[[name]]

  missing_summary <- tibble(
    Column = names(df),
    Missing = colSums(is.na(df))
  ) %>%
    filter(Missing > 0)

  cat("\nDataset:", name, "\n")

  if (nrow(missing_summary) == 0) {
    cat("No missing values.\n")
  } else {
    print(missing_summary)
  }

  # Required analytical columns must not contain NA.
  stopifnot(
    !anyNA(df[required_columns])
  )
}

# ------------------------------------------------------------
# 6. Check duplicate experimental runs
# ------------------------------------------------------------

cat("\n=== DUPLICATE RUN VALIDATION ===\n")

for (name in names(datasets)) {

  duplicates <- datasets[[name]] %>%
    count(experiment, seed, policy) %>%
    filter(n > 1)

  cat(name, ": ", nrow(duplicates),
      " duplicate run identifiers.\n", sep = "")

  stopifnot(nrow(duplicates) == 0)
}

# ------------------------------------------------------------
# 7. Validate policy distributions
# ------------------------------------------------------------

cat("\n=== POLICY DISTRIBUTIONS ===\n")

expected_policies <- c(
  "baseline",
  "availability",
  "smart",
  "smart_v2"
)

for (name in names(datasets)) {

  df <- datasets[[name]]

  cat("\nDataset:", name, "\n")

  print(df %>% count(policy))

  stopifnot(
    setequal(unique(df$policy), expected_policies)
  )
}

# ------------------------------------------------------------
# 8. Validate random seed distributions
# ------------------------------------------------------------

cat("\n=== RANDOM SEED DISTRIBUTIONS ===\n")

for (name in names(datasets)) {

  cat("\nDataset:", name, "\n")

  print(
    datasets[[name]] %>%
      count(seed)
  )

  stopifnot(
    setequal(unique(datasets[[name]]$seed), 42:46)
  )
}

# ------------------------------------------------------------
# 9. Inspect experimental balance
# ------------------------------------------------------------

cat("\n=== EXPERIMENTAL BALANCE ===\n")

for (name in names(datasets)) {

  cat("\nDataset:", name, "\n")

  balance <- datasets[[name]] %>%
    count(experiment, policy) %>%
    pivot_wider(
      names_from = policy,
      values_from = n,
      values_fill = 0
    )

  print(balance, width = Inf)
}

# Validate the complete primary factorial matrix.

expected_primary <- expand_grid(
  experiment = c(
    "low_normal_occupancy",
    "low_high_occupancy",
    "normal_normal_occupancy",
    "normal_high_occupancy",
    "peak_normal_occupancy",
    "peak_high_occupancy"
  ),
  seed = 42:46,
  policy = expected_policies
)

missing_primary_runs <- anti_join(
  expected_primary,
  primary,
  by = c("experiment", "seed", "policy")
)

cat("\nMissing primary experimental combinations:",
    nrow(missing_primary_runs), "\n")

if (nrow(missing_primary_runs) > 0) {
  print(missing_primary_runs)
}

stopifnot(nrow(missing_primary_runs) == 0)

# ------------------------------------------------------------
# 10. Validate simulation reliability
# ------------------------------------------------------------

cat("\n=== SIMULATION RELIABILITY ===\n")

reliability_summary <- imap_dfr(
  datasets,
  function(df, name) {

    tibble(
      Dataset = name,
      Trials = nrow(df),
      Vehicles = sum(df$vehicle_count),
      Successful_Parking = sum(df$total_parking_success),
      Completed_Returns = sum(df$total_completed_return_trip),
      Teleports = sum(df$total_teleported),
      Completed_Trials = sum(df$complete),
      Parking_Success_Pct =
        100 * Successful_Parking / Vehicles,
      Return_Success_Pct =
        100 * Completed_Returns / Vehicles
    )
  }
)

print(reliability_summary, width = Inf)

for (name in names(datasets)) {

  df <- datasets[[name]]

  stopifnot(
    all(df$vehicle_count == 40),
    all(df$complete),
    all(df$status == "complete"),
    all(df$total_parking_success == df$vehicle_count),
    all(df$total_completed_return_trip == df$vehicle_count),
    all(df$total_teleported == 0)
  )
}

# ------------------------------------------------------------
# 11. Export validation summaries
# ------------------------------------------------------------

dir.create(
  "tables/csv",
  recursive = TRUE,
  showWarnings = FALSE
)

write_csv(
  dataset_summary,
  "tables/csv/dataset_validation_summary.csv"
)

write_csv(
  reliability_summary,
  "tables/csv/simulation_reliability_summary.csv"
)

# ------------------------------------------------------------
# 12. Final validation summary
# ------------------------------------------------------------

cat("\n============================================\n")
cat("DATA VALIDATION COMPLETED SUCCESSFULLY\n")
cat("============================================\n")

cat("Total simulation runs:",
    sum(dataset_summary$Rows), "\n")

cat("Total parking vehicle observations:",
    sum(reliability_summary$Vehicles), "\n")

cat("Successful parking events:",
    sum(reliability_summary$Successful_Parking), "\n")

cat("Completed return trips:",
    sum(reliability_summary$Completed_Returns), "\n")

cat("Total vehicle teleports:",
    sum(reliability_summary$Teleports), "\n")

cat("\nValidation reports saved to tables/csv/\n")
