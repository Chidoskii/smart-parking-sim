
# ============================================================
# Master's Research Project
# 04_primary_visualizations.R
#
# Purpose:
# Generate publication-quality figures for the primary
# parking assignment experiments.
# ============================================================

suppressPackageStartupMessages({
  library(tidyverse)
  library(patchwork)
  library(scales)
})

cat("\n=== PRIMARY RESEARCH VISUALIZATIONS ===\n")

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
      plot.subtitle = element_text(
        size = base_size - 1,
        color = "grey30"
      ),
      axis.title = element_text(
        face = "bold"
      ),
      axis.text = element_text(
        color = "black"
      ),
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
      strip.text = element_text(
        face = "bold"
      ),
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
    filename = file.path(
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
    filename = file.path(
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
# 4. Load primary experimental data
# ------------------------------------------------------------

primary <- read_csv(
  "data/primary/main_experiment_reports_completed.csv",
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

    demand = case_when(
      str_starts(experiment, "low_") ~ "Low",
      str_starts(experiment, "normal_") ~ "Normal",
      str_starts(experiment, "peak_") ~ "Peak"
    ),

    occupancy = case_when(
      str_ends(experiment, "high_occupancy") ~ "High",
      str_ends(experiment, "normal_occupancy") ~ "Normal"
    ),

    demand = factor(
      demand,
      levels = c("Low", "Normal", "Peak")
    ),

    occupancy = factor(
      occupancy,
      levels = c("Normal", "High")
    )
  )

stopifnot(
  nrow(primary) == 120,
  !anyNA(primary$policy),
  !anyNA(primary$demand),
  !anyNA(primary$occupancy)
)

# Load previously exported inferential results.

primary_tests <- read_csv(
  "tables/csv/primary_statistical_tests.csv",
  show_col_types = FALSE
)

h1_seed_data <- read_csv(
  "tables/csv/h1_high_occupancy_seed_differences.csv",
  show_col_types = FALSE
)

# ------------------------------------------------------------
# 5. Performance metric definitions
# ------------------------------------------------------------

metric_labels <- c(
  avg_parking_search_time = "Parking Search Time (s)",
  avg_distance_m = "Driving Distance (m)",
  avg_walking_distance_m = "Walking Distance (m)",
  avg_co2_g = "CO2 Emissions (g)",
  avg_time_to_parking = "Time to Parking (s)",
  avg_waiting_time = "Waiting Time (s)",
  avg_time_loss = "Time Loss (s)"
)

core_metrics <- c(
  "avg_parking_search_time",
  "avg_distance_m",
  "avg_walking_distance_m",
  "avg_co2_g"
)

primary_long <- primary %>%
  pivot_longer(
    cols = all_of(names(metric_labels)),
    names_to = "metric",
    values_to = "value"
  ) %>%
  mutate(
    metric_label = unname(metric_labels[metric])
  )

# ------------------------------------------------------------
# 6. Calculate descriptive plotting statistics
# ------------------------------------------------------------

overall_summary <- primary_long %>%
  group_by(policy, metric, metric_label) %>%
  summarise(
    n = n(),
    mean = mean(value),
    sd = sd(value),
    .groups = "drop"
  )

occupancy_summary <- primary_long %>%
  group_by(policy, occupancy, metric, metric_label) %>%
  summarise(
    n = n(),
    mean = mean(value),
    sd = sd(value),
    .groups = "drop"
  )

demand_summary <- primary_long %>%
  group_by(policy, demand, metric, metric_label) %>%
  summarise(
    n = n(),
    mean = mean(value),
    sd = sd(value),
    .groups = "drop"
  )

condition_summary <- primary_long %>%
  group_by(
    policy,
    demand,
    occupancy,
    metric,
    metric_label
  ) %>%
  summarise(
    n = n(),
    mean = mean(value),
    sd = sd(value),
    .groups = "drop"
  )

# ------------------------------------------------------------
# 7. Reusable overall performance plot
# ------------------------------------------------------------

plot_overall <- function(metric_name, y_label) {

  plot_data <- overall_summary %>%
    filter(metric == metric_name)

  ggplot(
    plot_data,
    aes(x = policy, y = mean, fill = policy)
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
    scale_fill_manual(values = policy_colors) +
    scale_y_continuous(
      limits = c(0, NA),
      expand = expansion(mult = c(0, 0.08)),
      labels = label_number()
    ) +
    labs(
      x = NULL,
      y = y_label,
      caption = "Error bars: +/- 1 SD across 30 trials per policy."
    ) +
    theme(
      legend.position = "none",
      axis.text.x = element_text(size = 8)
    )
}

# ------------------------------------------------------------
# Figure 01: Parking search time
# ------------------------------------------------------------

fig01 <- plot_overall(
  "avg_parking_search_time",
  "Parking search time (s)"
)

save_figure(fig01, "fig01_primary_search_time")

# ------------------------------------------------------------
# Figure 02: Driving distance
# ------------------------------------------------------------

fig02 <- plot_overall(
  "avg_distance_m",
  "Driving distance (m)"
)

save_figure(fig02, "fig02_primary_driving_distance")

# ------------------------------------------------------------
# Figure 03: Walking distance
# ------------------------------------------------------------

fig03 <- plot_overall(
  "avg_walking_distance_m",
  "Walking distance (m)"
)

save_figure(fig03, "fig03_primary_walking_distance")

# ------------------------------------------------------------
# Figure 04: CO2 emissions
# ------------------------------------------------------------

fig04 <- plot_overall(
  "avg_co2_g",
  "CO2 emissions (g)"
)

save_figure(fig04, "fig04_primary_co2_emissions")

# ------------------------------------------------------------
# Figure 05: Occupancy interaction
# ------------------------------------------------------------

fig05 <- occupancy_summary %>%
  filter(metric == "avg_parking_search_time") %>%
  ggplot(
    aes(
      x = occupancy,
      y = mean,
      color = policy,
      shape = policy,
      group = policy
    )
  ) +
  geom_line(linewidth = 0.7) +
  geom_point(size = 2.4) +
  scale_color_manual(values = policy_colors) +
  scale_shape_manual(values = policy_shapes) +
  scale_x_discrete(
    labels = c(
      "Normal" = "Normal (40%)",
      "High" = "High (90%)"
    )
  ) +
  labs(
    x = "Parking occupancy",
    y = "Mean parking search time (s)",
    caption = "15 trials per policy at each occupancy level."
  )

save_figure(
  fig05,
  "fig05_primary_occupancy_interaction",
  width = 3.5,
  height = 3.2
)

# ------------------------------------------------------------
# Figure 06: Demand interaction
# ------------------------------------------------------------

fig06 <- demand_summary %>%
  filter(metric == "avg_parking_search_time") %>%
  ggplot(
    aes(
      x = demand,
      y = mean,
      color = policy,
      shape = policy,
      group = policy
    )
  ) +
  geom_line(linewidth = 0.7) +
  geom_point(size = 2.4) +
  scale_color_manual(values = policy_colors) +
  scale_shape_manual(values = policy_shapes) +
  labs(
    x = "Traffic demand",
    y = "Mean parking search time (s)",
    caption = "10 trials per policy at each demand level."
  )

save_figure(
  fig06,
  "fig06_primary_demand_interaction",
  width = 3.5,
  height = 3.2
)

# ------------------------------------------------------------
# Figure 07: Six experimental conditions
# ------------------------------------------------------------

fig07 <- condition_summary %>%
  filter(metric == "avg_parking_search_time") %>%
  ggplot(
    aes(
      x = demand,
      y = mean,
      color = policy,
      shape = policy,
      group = policy
    )
  ) +
  geom_line(linewidth = 0.6) +
  geom_point(size = 2) +
  geom_errorbar(
    aes(
      ymin = mean - sd,
      ymax = mean + sd
    ),
    width = 0.08,
    linewidth = 0.35,
    position = position_dodge(width = 0.15)
  ) +
  facet_wrap(~ occupancy, nrow = 1) +
  scale_color_manual(values = policy_colors) +
  scale_shape_manual(values = policy_shapes) +
  labs(
    x = "Traffic demand",
    y = "Parking search time (s)",
    caption = "Error bars: +/- 1 SD; five trials per condition and policy."
  )

save_figure(
  fig07,
  "fig07_primary_experimental_conditions",
  width = 7.16,
  height = 3.2
)

# ------------------------------------------------------------
# Figure 08: Paired policy effects and confidence intervals
# ------------------------------------------------------------

forest_data <- primary_tests %>%
  filter(
    metric_label %in% unname(metric_labels[core_metrics])
  ) %>%
  mutate(
    comparison_policy = factor(
      comparison_policy,
      levels = rev(policy_order[-1])
    ),
    metric_label = factor(
      metric_label,
      levels = unname(metric_labels[core_metrics])
    )
  )

fig08 <- ggplot(
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
  fig08,
  "fig08_primary_paired_effects",
  width = 7.16,
  height = 4.2
)

# ------------------------------------------------------------
# Figure 09: Driving versus walking distance trade-off
# ------------------------------------------------------------

tradeoff_summary <- primary %>%
  group_by(policy) %>%
  summarise(
    driving = mean(avg_distance_m),
    walking = mean(avg_walking_distance_m),
    .groups = "drop"
  )

fig09 <- ggplot(
  primary,
  aes(
    x = avg_distance_m,
    y = avg_walking_distance_m,
    color = policy,
    shape = policy
  )
) +
  geom_point(
    alpha = 0.35,
    size = 1.4
  ) +
  geom_point(
    data = tradeoff_summary,
    aes(
      x = driving,
      y = walking
    ),
    size = 4
  ) +
  scale_color_manual(values = policy_colors) +
  scale_shape_manual(values = policy_shapes) +
  labs(
    x = "Driving distance (m)",
    y = "Walking distance (m)",
    caption = "Small points: individual trial means. Large points: policy means."
  )

save_figure(
  fig09,
  "fig09_primary_driving_walking_tradeoff",
  width = 5,
  height = 3.8
)

# ------------------------------------------------------------
# Figure 10: Parking reassignment operations
# ------------------------------------------------------------

fig10 <- ggplot(
  primary,
  aes(
    x = policy,
    y = total_parking_reassignments,
    fill = policy
  )
) +
  geom_boxplot(
    width = 0.55,
    alpha = 0.8,
    outlier.shape = NA
  ) +
  geom_jitter(
    width = 0.12,
    height = 0,
    size = 1.1,
    alpha = 0.5,
    color = "grey25"
  ) +
  scale_fill_manual(values = policy_colors) +
  labs(
    x = NULL,
    y = "Reassignment operations per trial",
    caption = "30 trials per policy."
  ) +
  theme(legend.position = "none")

save_figure(
  fig10,
  "fig10_primary_parking_reassignments",
  width = 3.5,
  height = 3.2
)

# ------------------------------------------------------------
# Figure 11: Percentage change heatmap
# ------------------------------------------------------------

baseline_summary <- overall_summary %>%
  filter(policy == "Baseline") %>%
  select(
    metric,
    baseline_mean = mean
  )

heatmap_data <- overall_summary %>%
  filter(policy != "Baseline") %>%
  left_join(
    baseline_summary,
    by = "metric"
  ) %>%
  mutate(
    percentage_change =
      100 * (mean - baseline_mean) / baseline_mean,

    metric_label = factor(
      metric_label,
      levels = rev(unname(metric_labels))
    )
  )

fig11 <- ggplot(
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
      label = sprintf("%+.1f%%", percentage_change)
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
    legend.position = "bottom",
    legend.title = element_text()
  )

save_figure(
  fig11,
  "fig11_primary_percentage_heatmap",
  width = 5.5,
  height = 3.8
)

# ------------------------------------------------------------
# Figure 12: High-occupancy matched seed comparison
# ------------------------------------------------------------

seed_plot_data <- h1_seed_data %>%
  select(
    seed,
    baseline_value,
    policy_value
  ) %>%
  pivot_longer(
    cols = c(baseline_value, policy_value),
    names_to = "policy",
    values_to = "search_time"
  ) %>%
  mutate(
    policy = recode(
      policy,
      baseline_value = "Baseline",
      policy_value = "Availability"
    ),
    policy = factor(
      policy,
      levels = policy_order[1:2]
    )
  )

fig12 <- ggplot(
  seed_plot_data,
  aes(
    x = policy,
    y = search_time,
    group = factor(seed)
  )
) +
  geom_line(
    color = "grey60",
    linewidth = 0.6
  ) +
  geom_point(
    aes(color = policy, shape = policy),
    size = 2.5
  ) +
  scale_color_manual(values = policy_colors) +
  scale_shape_manual(values = policy_shapes) +
  labs(
    x = NULL,
    y = "Parking search time (s)",
    caption = paste(
      "Each line represents one matched seed block,",
      "averaged across three demand levels."
    )
  ) +
  theme(legend.position = "none")

save_figure(
  fig12,
  "fig12_high_occupancy_matched_seeds",
  width = 3.5,
  height = 3.2
)

# ------------------------------------------------------------
# Figure 13: Combined primary performance figure
# ------------------------------------------------------------

fig13 <- (
  (fig01 + labs(caption = NULL)) |
  (fig02 + labs(caption = NULL))
) / (
  (fig03 + labs(caption = NULL)) |
  (fig04 + labs(caption = NULL))
) +
  plot_annotation(
    tag_levels = "a",
    tag_prefix = "(",
    tag_suffix = ")",
    caption = "Error bars: +/- 1 SD across 30 trials per policy."
  )

save_figure(
  fig13,
  "fig13_primary_performance_combined",
  width = 7.16,
  height = 5.5
)

# ------------------------------------------------------------
# 8. Completion summary
# ------------------------------------------------------------

cat("\n============================================\n")
cat("PRIMARY VISUALIZATIONS COMPLETED\n")
cat("============================================\n")

cat("Primary trials:", nrow(primary), "\n")
cat("Figures generated: 13\n")
cat("PDF exports: 13\n")
cat("PNG exports: 13\n")
cat("Total figure files: 26\n")

cat("\nPDF figures saved to figures/pdf/\n")
cat("PNG figures saved to figures/png/\n")
