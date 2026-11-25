
# ============================================================
# Master's Research Project
# 05_supplementary_visualizations.R
#
# Purpose:
# Analyze destination-informed parking experiments and
# generate network-level performance visualizations.
# ============================================================

suppressPackageStartupMessages({
  library(tidyverse)
  library(patchwork)
  library(scales)
})

cat("\n=== SUPPLEMENTARY AND NETWORK ANALYSIS ===\n")

# ------------------------------------------------------------
# 1. Configuration
# ------------------------------------------------------------

policy_order <- c(
  "Baseline",
  "Availability",
  "Smart V1",
  "Smart V2"
)

policy_colors <- c(
  "Baseline"     = "#6B7280",
  "Availability" = "#009E73",
  "Smart V1"     = "#0072B2",
  "Smart V2"     = "#D55E00"
)

policy_shapes <- c(
  "Baseline"     = 16,
  "Availability" = 17,
  "Smart V1"     = 15,
  "Smart V2"     = 18
)

dir.create("figures/pdf", recursive = TRUE, showWarnings = FALSE)
dir.create("figures/png", recursive = TRUE, showWarnings = FALSE)
dir.create("tables/csv", recursive = TRUE, showWarnings = FALSE)

# ------------------------------------------------------------
# 2. Publication theme
# ------------------------------------------------------------

theme_research <- function(base_size = 9) {

  theme_bw(
    base_size = base_size,
    base_family = "sans"
  ) +
    theme(
      plot.title = element_text(
        face = "bold",
        size = base_size + 1
      ),
      axis.title = element_text(face = "bold"),
      axis.text = element_text(color = "black"),
      panel.grid.major.x = element_blank(),
      panel.grid.minor = element_blank(),
      panel.grid.major.y = element_line(
        color = "grey90",
        linewidth = 0.3
      ),
      legend.position = "bottom",
      legend.title = element_blank(),
      strip.background = element_rect(
        fill = "grey95",
        color = "grey70"
      ),
      strip.text = element_text(face = "bold"),
      plot.caption = element_text(
        size = base_size - 2,
        hjust = 0
      ),
      plot.margin = margin(6, 8, 6, 6)
    )
}

theme_set(theme_research())

# ------------------------------------------------------------
# 3. Figure export function
# ------------------------------------------------------------

save_figure <- function(
    plot,
    filename,
    width = 3.5,
    height = 3.0
) {

  ggsave(
    file.path(
      "figures/pdf",
      paste0(filename, ".pdf")
    ),
    plot = plot,
    device = grDevices::cairo_pdf,
    width = width,
    height = height,
    units = "in",
    bg = "white"
  )

  ggsave(
    file.path(
      "figures/png",
      paste0(filename, ".png")
    ),
    plot = plot,
    width = width,
    height = height,
    units = "in",
    dpi = 300,
    bg = "white"
  )

  cat("Exported:", filename, "\n")
}

# ------------------------------------------------------------
# 4. Load supplementary experimental data
# ------------------------------------------------------------

supplementary <- read_csv(
  "data/supplementary/final_experiment_reports_completed.csv",
  show_col_types = FALSE
) %>%
  mutate(
    policy = recode(
      policy,
      baseline = "Baseline",
      availability = "Availability",
      smart = "Smart V1",
      smart_v2 = "Smart V2"
    ),

    policy = factor(
      policy,
      levels = policy_order
    ),

    occupancy = case_when(
      str_ends(experiment, "normal_occupancy") ~ "Normal",
      str_ends(experiment, "high_occupancy") ~ "High"
    ),

    network_total_co2_kg =
      network_total_co2_g / 1000
  )

balanced <- supplementary %>%
  filter(occupancy == "Normal")

exploratory <- supplementary %>%
  filter(occupancy == "High")

# ------------------------------------------------------------
# 5. Validate network-level data
# ------------------------------------------------------------

stopifnot(
  nrow(supplementary) == 24,
  nrow(balanced) == 20,
  nrow(exploratory) == 4,
  !anyNA(supplementary$policy),
  !anyNA(supplementary$occupancy),
  all(supplementary$network_metrics_available),
  all(supplementary$network_complete),
  all(supplementary$network_vehicle_count == 55),
  all(supplementary$background_vehicle_count == 15),
  all(supplementary$parking_vehicle_count == 40),
  all(supplementary$network_unfinished_trips == 0),
  all(supplementary$network_teleports == 0)
)

expected_pairs <- expand_grid(
  seed = 42:46,
  policy = factor(
    policy_order,
    levels = policy_order
  )
)

stopifnot(
  nrow(
    anti_join(
      expected_pairs,
      balanced,
      by = c("seed", "policy")
    )
  ) == 0
)

cat("\n=== NETWORK DATA VALIDATION ===\n")
cat("Balanced trials:", nrow(balanced), "\n")
cat("Exploratory trials:", nrow(exploratory), "\n")
cat("Network vehicles per trial: 55\n")
cat("Parking vehicles per trial: 40\n")
cat("Background vehicles per trial: 15\n")
cat("Network metrics validation passed.\n")

# ------------------------------------------------------------
# 6. Define performance metrics
# ------------------------------------------------------------

parking_metrics <- c(
  avg_parking_search_time = "Parking search time (s)",
  avg_distance_m = "Driving distance (m)",
  avg_walking_distance_m = "Walking distance (m)",
  avg_co2_g = "Parking vehicle CO2 (g)"
)

network_metrics <- c(
  network_avg_waiting_time_s =
    "Network waiting time (s/veh)",

  network_avg_time_loss_s =
    "Network time loss (s/veh)",

  network_avg_distance_m =
    "Network driving distance (m/veh)",

  network_total_co2_kg =
    "Network CO2 (kg/trial)",

  background_avg_waiting_time_s =
    "Background waiting time (s/veh)",

  background_avg_time_loss_s =
    "Background time loss (s/veh)",

  background_avg_distance_m =
    "Background driving distance (m/veh)",

  background_avg_co2_g =
    "Background CO2 (g/veh)"
)

all_metrics <- c(
  parking_metrics,
  network_metrics
)

stopifnot(
  all(names(all_metrics) %in% names(supplementary)),
  all(
    vapply(
      supplementary[names(all_metrics)],
      function(x) all(is.finite(x)),
      logical(1)
    )
  )
)

# ------------------------------------------------------------
# 7. Calculate descriptive statistics
# ------------------------------------------------------------

calculate_summary <- function(df, metrics) {

  df %>%
    pivot_longer(
      cols = all_of(names(metrics)),
      names_to = "metric",
      values_to = "value"
    ) %>%

    group_by(policy, metric) %>%

    summarise(
      n = n(),
      mean = mean(value),
      median = median(value),
      sd = sd(value),
      min = min(value),
      max = max(value),
      .groups = "drop"
    ) %>%

    mutate(
      metric_label = unname(metrics[metric])
    )
}

parking_summary <- calculate_summary(
  balanced,
  parking_metrics
)

network_summary <- calculate_summary(
  balanced,
  network_metrics
)

network_exploratory_summary <- calculate_summary(
  exploratory,
  network_metrics
)

# ------------------------------------------------------------
# 8. Baseline-relative comparisons
# ------------------------------------------------------------

calculate_changes <- function(df) {

  baseline <- df %>%
    filter(policy == "Baseline") %>%
    select(
      metric,
      baseline_mean = mean
    )

  df %>%
    left_join(baseline, by = "metric") %>%

    mutate(
      absolute_change = mean - baseline_mean,

      percentage_change = if_else(
        baseline_mean == 0,
        NA_real_,
        100 * absolute_change / baseline_mean
      )
    )
}

network_comparison <- calculate_changes(
  network_summary
)

parking_comparison <- calculate_changes(
  parking_summary
)

network_exploratory_comparison <- calculate_changes(
  network_exploratory_summary
)

# ------------------------------------------------------------
# 9. Create readable comparison tables
# ------------------------------------------------------------

create_mean_table <- function(df) {

  df %>%
    select(metric_label, policy, mean) %>%

    mutate(mean = round(mean, 2)) %>%

    pivot_wider(
      names_from = policy,
      values_from = mean
    ) %>%

    select(
      metric_label,
      all_of(policy_order)
    )
}

network_mean_table <- create_mean_table(
  network_summary
)

network_percentage_table <- network_comparison %>%
  filter(policy != "Baseline") %>%

  select(
    metric_label,
    policy,
    percentage_change
  ) %>%

  mutate(
    percentage_change = round(
      percentage_change,
      2
    )
  ) %>%

  pivot_wider(
    names_from = policy,
    values_from = percentage_change
  ) %>%

  select(
    metric_label,
    all_of(policy_order[-1])
  )

cat("\n=== NETWORK MEAN COMPARISON ===\n")

print(
  network_mean_table,
  n = Inf,
  width = Inf
)

cat("\n=== NETWORK PERCENTAGE CHANGE ===\n")

print(
  network_percentage_table,
  n = Inf,
  width = Inf
)

# ------------------------------------------------------------
# 10. Construct matched network-level differences
# ------------------------------------------------------------

network_pairs <- balanced %>%

  select(
    seed,
    policy,
    all_of(names(network_metrics))
  ) %>%

  pivot_longer(
    cols = all_of(names(network_metrics)),
    names_to = "metric",
    values_to = "value"
  ) %>%

  pivot_wider(
    names_from = policy,
    values_from = value
  ) %>%

  pivot_longer(
    cols = all_of(policy_order[-1]),
    names_to = "comparison_policy",
    values_to = "policy_value"
  ) %>%

  mutate(
    baseline_value = Baseline,
    difference = policy_value - baseline_value
  ) %>%

  select(
    seed,
    metric,
    comparison_policy,
    baseline_value,
    policy_value,
    difference
  )

stopifnot(
  nrow(network_pairs) == 120,
  all(is.finite(network_pairs$difference))
)

# ------------------------------------------------------------
# 11. Network-level statistical testing
# ------------------------------------------------------------

test_differences <- function(x) {

  stopifnot(all(is.finite(x)))

  n <- length(x)
  mean_difference <- mean(x)
  sd_difference <- sd(x)

  nonzero <- x[x != 0]

  sign_p <- if (length(nonzero) == 0) {
    1
  } else {
    binom.test(
      sum(nonzero > 0),
      length(nonzero),
      p = 0.5
    )$p.value
  }

  if (
    n < 2 ||
    is.na(sd_difference) ||
    sd_difference <=
      10 * .Machine$double.eps *
      max(1, abs(mean_difference))
  ) {

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

network_tests <- network_pairs %>%

  group_by(metric, comparison_policy) %>%

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
    metric_label = unname(network_metrics[metric]),

    p_adjusted = p.adjust(
      p_value,
      method = "holm"
    ),

    significant_adjusted = p_adjusted < 0.05
  )

cat("\n=== NETWORK-LEVEL PAIRED STATISTICAL TESTS ===\n")

network_tests %>%

  select(
    comparison_policy,
    metric_label,
    n,
    mean_difference,
    percentage_change,
    ci_lower,
    ci_upper,
    p_value,
    p_adjusted,
    sign_test_p
  ) %>%

  print(n = Inf, width = Inf)

# ------------------------------------------------------------
# 12. Reusable supplementary performance plot
# ------------------------------------------------------------

plot_performance <- function(
    summary_df,
    metric_name,
    y_label
) {

  plot_data <- summary_df %>%
    filter(metric == metric_name)

  ggplot(
    plot_data,
    aes(
      x = policy,
      y = mean,
      fill = policy
    )
  ) +
    geom_col(
      width = 0.65,
      color = "grey25",
      linewidth = 0.25
    ) +
    geom_errorbar(
      aes(
        ymin = pmax(0, mean - sd),
        ymax = mean + sd
      ),
      width = 0.15,
      linewidth = 0.4
    ) +
    scale_fill_manual(
      values = policy_colors
    ) +
    scale_y_continuous(
      limits = c(0, NA),
      expand = expansion(mult = c(0, 0.08)),
      labels = label_number()
    ) +
    labs(
      x = NULL,
      y = y_label,
      caption = "Error bars: +/- 1 SD across five trials per policy."
    ) +
    theme(
      legend.position = "none",
      axis.text.x = element_text(size = 8)
    )
}

# ------------------------------------------------------------
# Figure 14: Supplementary parking search time
# ------------------------------------------------------------

fig14 <- plot_performance(
  parking_summary,
  "avg_parking_search_time",
  "Parking search time (s)"
)

save_figure(
  fig14,
  "fig14_supplementary_search_time"
)

# ------------------------------------------------------------
# Figure 15: Supplementary driving distance
# ------------------------------------------------------------

fig15 <- plot_performance(
  parking_summary,
  "avg_distance_m",
  "Driving distance (m)"
)

save_figure(
  fig15,
  "fig15_supplementary_driving_distance"
)

# ------------------------------------------------------------
# Figure 16: Supplementary walking distance
# ------------------------------------------------------------

fig16 <- plot_performance(
  parking_summary,
  "avg_walking_distance_m",
  "Walking distance (m)"
)

save_figure(
  fig16,
  "fig16_supplementary_walking_distance"
)

# ------------------------------------------------------------
# Figure 17: Supplementary parking vehicle emissions
# ------------------------------------------------------------

fig17 <- plot_performance(
  parking_summary,
  "avg_co2_g",
  expression(CO[2]~emissions~(g))
)

save_figure(
  fig17,
  "fig17_supplementary_co2_emissions"
)

# ------------------------------------------------------------
# Figure 18: Network waiting time
# ------------------------------------------------------------

fig18 <- plot_performance(
  network_summary,
  "network_avg_waiting_time_s",
  "Network waiting time (s/veh)"
)

save_figure(
  fig18,
  "fig18_network_waiting_time"
)

# ------------------------------------------------------------
# Figure 19: Network time loss
# ------------------------------------------------------------

fig19 <- plot_performance(
  network_summary,
  "network_avg_time_loss_s",
  "Network time loss (s/veh)"
)

save_figure(
  fig19,
  "fig19_network_time_loss"
)

# ------------------------------------------------------------
# Figure 20: Background vehicle time loss
# ------------------------------------------------------------

fig20 <- plot_performance(
  network_summary,
  "background_avg_time_loss_s",
  "Background time loss (s/veh)"
)

save_figure(
  fig20,
  "fig20_background_time_loss"
)

# ------------------------------------------------------------
# Figure 21: Network CO2 emissions
# ------------------------------------------------------------

fig21 <- plot_performance(
  network_summary,
  "network_total_co2_kg",
  expression(Network~CO[2]~(kg/trial))
)

save_figure(
  fig21,
  "fig21_network_co2_emissions"
)

# ------------------------------------------------------------
# Figure 22: Network-level paired effects
# ------------------------------------------------------------

forest_metrics <- c(
  "network_avg_waiting_time_s",
  "network_avg_time_loss_s",
  "background_avg_time_loss_s",
  "network_total_co2_kg"
)

forest_data <- network_tests %>%

  filter(metric %in% forest_metrics) %>%

  mutate(
    comparison_policy = factor(
      comparison_policy,
      levels = rev(policy_order[-1])
    ),

    metric_label = factor(
      metric_label,
      levels = unname(
        network_metrics[forest_metrics]
      )
    )
  )

fig22 <- ggplot(
  forest_data,
  aes(
    x = mean_difference,
    y = comparison_policy,
    color = comparison_policy
  )
) +
  geom_vline(
    xintercept = 0,
    linetype = "dashed",
    color = "grey40"
  ) +
  geom_errorbar(
    data = forest_data %>%
      filter(
        is.finite(ci_lower),
        is.finite(ci_upper)
      ),
    aes(
      xmin = ci_lower,
      xmax = ci_upper
    ),
    orientation = "y",
    width = 0.15,
    linewidth = 0.6
  ) +
  geom_point(size = 2.3) +
  facet_wrap(
    ~ metric_label,
    scales = "free_x",
    ncol = 2
  ) +
  scale_color_manual(values = policy_colors) +
  labs(
    x = "Mean difference from Baseline",
    y = NULL,
    caption = paste(
      "Unadjusted 95% paired t confidence intervals.",
      "Five matched seed blocks per comparison."
    )
  ) +
  theme(legend.position = "none")

save_figure(
  fig22,
  "fig22_network_paired_effects",
  width = 7.16,
  height = 4.2
)

# ------------------------------------------------------------
# Figure 23: Combined supplementary parking performance
# ------------------------------------------------------------

fig23 <- (
  (fig14 + labs(caption = NULL)) |
  (fig15 + labs(caption = NULL))
) / (
  (fig16 + labs(caption = NULL)) |
  (fig17 + labs(caption = NULL))
) +
  plot_annotation(
    tag_levels = "a",
    tag_prefix = "(",
    tag_suffix = ")",
    caption = paste(
      "Low demand, normal occupancy.",
      "Error bars: +/- 1 SD across five trials per policy."
    )
  )

save_figure(
  fig23,
  "fig23_supplementary_performance_combined",
  width = 7.16,
  height = 5.5
)

# ------------------------------------------------------------
# Figure 24: Combined network performance
# ------------------------------------------------------------

fig24 <- (
  (fig18 + labs(caption = NULL)) |
  (fig19 + labs(caption = NULL))
) / (
  (fig20 + labs(caption = NULL)) |
  (fig21 + labs(caption = NULL))
) +
  plot_annotation(
    tag_levels = "a",
    tag_prefix = "(",
    tag_suffix = ")",
    caption = paste(
      "Low demand, normal occupancy.",
      "Error bars: +/- 1 SD across five trials per policy."
    )
  )

save_figure(
  fig24,
  "fig24_network_performance_combined",
  width = 7.16,
  height = 5.5
)

# ------------------------------------------------------------
# Figure 25: Network percentage change heatmap
# ------------------------------------------------------------

heatmap_data <- network_comparison %>%

  filter(policy != "Baseline") %>%

  mutate(
    metric_label = factor(
      metric_label,
      levels = rev(unname(network_metrics))
    )
  )

fig25 <- ggplot(
  heatmap_data,
  aes(
    x = policy,
    y = metric_label,
    fill = percentage_change
  )
) +
  geom_tile(
    color = "white",
    linewidth = 0.7
  ) +
  geom_text(
    aes(
      label = sprintf(
        "%+.1f%%",
        percentage_change
      )
    ),
    size = 3
  ) +
  scale_fill_gradient2(
    low = "#56B4E9",
    mid = "white",
    high = "#E69F00",
    midpoint = 0,
    name = "Change (%)"
  ) +
  labs(
    x = NULL,
    y = NULL,
    caption = "Negative values indicate reductions relative to Baseline."
  ) +
  theme(
    panel.grid = element_blank(),
    legend.title = element_text()
  )

save_figure(
  fig25,
  "fig25_network_percentage_heatmap",
  width = 6.2,
  height = 4.2
)

# ------------------------------------------------------------
# 13. Export network statistical tables
# ------------------------------------------------------------

output_tables <- list(

  supplementary_network_statistics =
    network_summary,

  supplementary_network_comparison =
    network_comparison,

  supplementary_network_mean_table =
    network_mean_table,

  supplementary_network_percentage_table =
    network_percentage_table,

  supplementary_network_paired_differences =
    network_pairs,

  supplementary_network_statistical_tests =
    network_tests,

  supplementary_network_exploratory_statistics =
    network_exploratory_summary,

  supplementary_network_exploratory_comparison =
    network_exploratory_comparison
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
cat("SUPPLEMENTARY AND NETWORK ANALYSIS COMPLETED\n")
cat("============================================\n")

cat("Balanced supplementary trials:",
    nrow(balanced), "\n")

cat("Exploratory supplementary trials:",
    nrow(exploratory), "\n")

cat("Network performance metrics:",
    length(network_metrics), "\n")

cat("Network statistical comparisons:",
    nrow(network_tests), "\n")

cat("Statistical tables exported:",
    length(output_tables), "\n")

cat("Figures generated: 12\n")
cat("PDF exports: 12\n")
cat("PNG exports: 12\n")
cat("Total figure files: 24\n")

cat("\nResults saved to tables/csv/\n")
cat("PDF figures saved to figures/pdf/\n")
cat("PNG figures saved to figures/png/\n")
