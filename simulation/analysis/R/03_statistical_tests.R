
# ============================================================
# Master's Research Project
# Autonomous Parking Assignment and Campus Traffic Efficiency
#
# Script: 03_statistical_tests.R
# Purpose: Matched statistical comparisons of parking policies
# ============================================================

library(tidyverse)
library(broom)

# ------------------------------------------------------------
# 1. Load descriptive analysis
# ------------------------------------------------------------

if (!exists("primary_data") ||
    !exists("supplementary_balanced")) {
  source("R/02_descriptive_statistics.R")
}

cat("\n=== INFERENTIAL STATISTICAL ANALYSIS ===\n")

# ------------------------------------------------------------
# 2. Define inferential performance metrics
# ------------------------------------------------------------

inferential_metrics <- c(
  "avg_time_to_parking",
  "avg_parking_search_time",
  "avg_waiting_time",
  "avg_time_loss",
  "avg_distance_m",
  "avg_walking_distance_m",
  "avg_co2_g"
)

comparison_policies <- c(
  "Availability",
  "Smart V1",
  "Smart V2"
)

# ------------------------------------------------------------
# 3. Construct matched policy differences
# ------------------------------------------------------------

create_paired_differences <- function(df) {

  paired <- df %>%
    select(
      experiment,
      seed,
      demand,
      occupancy,
      policy,
      all_of(inferential_metrics)
    ) %>%

    pivot_longer(
      cols = all_of(inferential_metrics),
      names_to = "metric",
      values_to = "value"
    ) %>%

    pivot_wider(
      names_from = policy,
      values_from = value
    )

  stopifnot(
    !anyNA(paired[policy_order])
  )

  paired %>%
    pivot_longer(
      cols = all_of(comparison_policies),
      names_to = "comparison_policy",
      values_to = "policy_value"
    ) %>%

    mutate(
      baseline_value = Baseline,
      difference = policy_value - baseline_value
    ) %>%

    select(
      experiment,
      seed,
      demand,
      occupancy,
      metric,
      comparison_policy,
      baseline_value,
      policy_value,
      difference
    )
}

primary_pairs <- create_paired_differences(
  primary_data
)

supplementary_pairs <- create_paired_differences(
  supplementary_balanced
)

# ------------------------------------------------------------
# 4. Aggregate matched differences within seed
# ------------------------------------------------------------

aggregate_seed_blocks <- function(
    paired_df,
    condition_variables = character()
) {

  paired_df %>%

    group_by(
      across(all_of(condition_variables)),
      metric,
      comparison_policy,
      seed
    ) %>%

    summarise(
      conditions = n(),
      baseline_value = mean(baseline_value),
      policy_value = mean(policy_value),
      difference = mean(difference),
      .groups = "drop"
    )
}

primary_seed_blocks <- aggregate_seed_blocks(
  primary_pairs
)

primary_occupancy_blocks <- aggregate_seed_blocks(
  primary_pairs,
  c("occupancy")
)

primary_demand_blocks <- aggregate_seed_blocks(
  primary_pairs,
  c("demand")
)

primary_condition_blocks <- aggregate_seed_blocks(
  primary_pairs,
  c("demand", "occupancy")
)

supplementary_seed_blocks <- aggregate_seed_blocks(
  supplementary_pairs
)

stopifnot(
  all(primary_seed_blocks$conditions == 6),
  all(primary_occupancy_blocks$conditions == 3),
  all(primary_demand_blocks$conditions == 2),
  all(primary_condition_blocks$conditions == 1),
  all(supplementary_seed_blocks$conditions == 1)
)

# ------------------------------------------------------------
# 5. Define statistical testing function
# ------------------------------------------------------------

test_differences <- function(x) {

  stopifnot(all(is.finite(x)))

  n <- length(x)
  mean_difference <- mean(x)
  sd_difference <- sd(x)

  # Exact sign test excludes zero differences.
  nonzero <- x[x != 0]

  sign_p <- if (length(nonzero) == 0) {
    1
  } else {
    binom.test(
      sum(nonzero > 0),
      length(nonzero),
      p = 0.5,
      alternative = "two.sided"
    )$p.value
  }

  # Handle constant differences explicitly.
  if (n < 2 ||
      is.na(sd_difference) ||
      sd_difference <=
        10 * .Machine$double.eps *
        max(1, abs(mean_difference))) {

    return(
      tibble(
        n = n,
        mean_difference = mean_difference,
        sd_difference = sd_difference,
        standard_error = NA_real_,
        t_statistic = NA_real_,
        df = NA_real_,
        p_value = NA_real_,
        ci_lower = NA_real_,
        ci_upper = NA_real_,
        cohens_dz = NA_real_,
        sign_test_p = sign_p,
        nonzero_pairs = length(nonzero),
        test_status = "Constant or insufficient differences"
      )
    )
  }

  # A one-sample t-test on paired differences
  # is equivalent to a paired t-test.

  result <- t.test(
    x,
    mu = 0,
    alternative = "two.sided",
    conf.level = 0.95
  )

  tibble(
    n = n,
    mean_difference = mean_difference,
    sd_difference = sd_difference,
    standard_error = sd_difference / sqrt(n),
    t_statistic = unname(result$statistic),
    df = unname(result$parameter),
    p_value = result$p.value,
    ci_lower = result$conf.int[1],
    ci_upper = result$conf.int[2],
    cohens_dz = mean_difference / sd_difference,
    sign_test_p = sign_p,
    nonzero_pairs = length(nonzero),
    test_status = "Completed"
  )
}

# ------------------------------------------------------------
# 6. Apply statistical tests
# ------------------------------------------------------------

run_paired_tests <- function(
    seed_blocks,
    condition_variables = character()
) {

  seed_blocks %>%

    group_by(
      across(all_of(condition_variables)),
      metric,
      comparison_policy
    ) %>%

    group_modify(
      ~ {

        stopifnot(
          nrow(.x) == 5,
          setequal(.x$seed, 42:46)
        )

        test_differences(.x$difference) %>%

          mutate(
            baseline_mean = mean(.x$baseline_value),
            policy_mean = mean(.x$policy_value),

            percentage_change = if_else(
              baseline_mean == 0,
              NA_real_,
              100 * mean_difference / baseline_mean
            )
          )
      }
    ) %>%

    ungroup() %>%

    mutate(
      metric_label = recode(
        metric,
        !!!metric_labels
      ),

      # Holm correction across the entire
      # family of tests in this output table.

      p_adjusted = p.adjust(
        p_value,
        method = "holm"
      ),

      significant_unadjusted = p_value < 0.05,
      significant_adjusted = p_adjusted < 0.05,

      direction = case_when(
        mean_difference < 0 ~ "Reduction",
        mean_difference > 0 ~ "Increase",
        TRUE ~ "No change"
      )
    )
}

# ------------------------------------------------------------
# 7. Primary overall policy comparisons
# ------------------------------------------------------------

primary_tests <- run_paired_tests(
  primary_seed_blocks
)

# ------------------------------------------------------------
# 8. Primary occupancy-level comparisons
# ------------------------------------------------------------

primary_occupancy_tests <- run_paired_tests(
  primary_occupancy_blocks,
  c("occupancy")
)

# ------------------------------------------------------------
# 9. Primary demand-level comparisons
# ------------------------------------------------------------

primary_demand_tests <- run_paired_tests(
  primary_demand_blocks,
  c("demand")
)

# ------------------------------------------------------------
# 10. Primary condition-level comparisons
# ------------------------------------------------------------

primary_condition_tests <- run_paired_tests(
  primary_condition_blocks,
  c("demand", "occupancy")
)

# ------------------------------------------------------------
# 11. Balanced supplementary comparisons
# ------------------------------------------------------------

supplementary_tests <- run_paired_tests(
  supplementary_seed_blocks
)

# ------------------------------------------------------------
# 12. Test whether policy effects differ by occupancy
# ------------------------------------------------------------

occupancy_contrast_blocks <-
  primary_occupancy_blocks %>%

  select(
    metric,
    comparison_policy,
    seed,
    occupancy,
    difference
  ) %>%

  pivot_wider(
    names_from = occupancy,
    values_from = difference
  ) %>%

  mutate(
    difference = High - Normal
  )

occupancy_interaction_tests <-
  occupancy_contrast_blocks %>%

  group_by(metric, comparison_policy) %>%

  group_modify(
    ~ test_differences(.x$difference)
  ) %>%

  ungroup() %>%

  mutate(
    metric_label = recode(metric, !!!metric_labels),
    p_adjusted = p.adjust(p_value, method = "holm"),
    significant_adjusted = p_adjusted < 0.05
  )

# ------------------------------------------------------------
# 13. Test whether policy effects differ by demand
# ------------------------------------------------------------

demand_contrast_blocks <-
  primary_demand_blocks %>%

  select(
    metric,
    comparison_policy,
    seed,
    demand,
    difference
  ) %>%

  pivot_wider(
    names_from = demand,
    values_from = difference
  ) %>%

  mutate(
    normal_vs_low = Normal - Low,
    peak_vs_low = Peak - Low,
    peak_vs_normal = Peak - Normal
  ) %>%

  pivot_longer(
    cols = c(
      normal_vs_low,
      peak_vs_low,
      peak_vs_normal
    ),
    names_to = "contrast",
    values_to = "difference"
  )

demand_interaction_tests <-
  demand_contrast_blocks %>%

  group_by(
    metric,
    comparison_policy,
    contrast
  ) %>%

  group_modify(
    ~ test_differences(.x$difference)
  ) %>%

  ungroup() %>%

  mutate(
    metric_label = recode(metric, !!!metric_labels),
    p_adjusted = p.adjust(p_value, method = "holm"),
    significant_adjusted = p_adjusted < 0.05
  )

# ------------------------------------------------------------
# 14. Print statistical results
# ------------------------------------------------------------

display_results <- function(df) {

  df %>%

    select(
      any_of(c("demand", "occupancy", "contrast")),
      comparison_policy,
      metric_label,
      n,
      mean_difference,
      ci_lower,
      ci_upper,
      p_value,
      p_adjusted,
      cohens_dz,
      sign_test_p
    ) %>%

    mutate(
      across(
        c(
          mean_difference,
          ci_lower,
          ci_upper,
          cohens_dz
        ),
        ~ round(.x, 3)
      )
    ) %>%

    print(n = Inf, width = Inf)
}

cat("\n=== PRIMARY OVERALL PAIRED TESTS ===\n")

display_results(primary_tests)

cat("\n=== PRIMARY HIGH-OCCUPANCY TESTS ===\n")

display_results(
  primary_occupancy_tests %>%
    filter(occupancy == "High")
)

cat("\n=== BALANCED SUPPLEMENTARY PAIRED TESTS ===\n")

display_results(supplementary_tests)

cat("\n=== OCCUPANCY EFFECT CONTRASTS ===\n")

display_results(occupancy_interaction_tests)

cat("\n=== DEMAND EFFECT CONTRASTS ===\n")

display_results(demand_interaction_tests)

# ------------------------------------------------------------
# 15. Verify key research comparison
# ------------------------------------------------------------

cat("\n=== H1: HIGH-OCCUPANCY PARKING SEARCH ===\n")

h1_seed_differences <- primary_occupancy_blocks %>%

  filter(
    occupancy == "High",
    metric == "avg_parking_search_time",
    comparison_policy == "Availability"
  ) %>%

  select(
    seed,
    baseline_value,
    policy_value,
    difference
  )

print(h1_seed_differences, width = Inf)

h1_result <- primary_occupancy_tests %>%

  filter(
    occupancy == "High",
    metric == "avg_parking_search_time",
    comparison_policy == "Availability"
  )

print(h1_result, width = Inf)

# ------------------------------------------------------------
# 16. Export statistical results
# ------------------------------------------------------------

statistical_tables <- list(

  primary_paired_differences = primary_pairs,
  primary_seed_blocks = primary_seed_blocks,

  primary_occupancy_seed_blocks =
    primary_occupancy_blocks,

  primary_demand_seed_blocks =
    primary_demand_blocks,

  primary_condition_seed_blocks =
    primary_condition_blocks,

  primary_statistical_tests = primary_tests,

  primary_occupancy_tests =
    primary_occupancy_tests,

  primary_demand_tests =
    primary_demand_tests,

  primary_condition_tests =
    primary_condition_tests,

  primary_occupancy_interaction_tests =
    occupancy_interaction_tests,

  primary_demand_interaction_tests =
    demand_interaction_tests,

  supplementary_paired_differences =
    supplementary_pairs,

  supplementary_seed_blocks =
    supplementary_seed_blocks,

  supplementary_statistical_tests =
    supplementary_tests,

  h1_high_occupancy_seed_differences =
    h1_seed_differences,

  h1_high_occupancy_test =
    h1_result
)

iwalk(
  statistical_tables,
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
# 17. Final statistical summary
# ------------------------------------------------------------

cat("\n============================================\n")
cat("INFERENTIAL STATISTICAL ANALYSIS COMPLETED\n")
cat("============================================\n")

cat("Primary overall comparisons:",
    nrow(primary_tests), "\n")

cat("Primary occupancy comparisons:",
    nrow(primary_occupancy_tests), "\n")

cat("Primary demand comparisons:",
    nrow(primary_demand_tests), "\n")

cat("Primary condition comparisons:",
    nrow(primary_condition_tests), "\n")

cat("Occupancy effect contrasts:",
    nrow(occupancy_interaction_tests), "\n")

cat("Demand effect contrasts:",
    nrow(demand_interaction_tests), "\n")

cat("Supplementary comparisons:",
    nrow(supplementary_tests), "\n")

cat("Statistical tables exported:",
    length(statistical_tables), "\n")

cat("\nResults saved to tables/csv/\n")
