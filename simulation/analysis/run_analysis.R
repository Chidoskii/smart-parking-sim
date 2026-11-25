
# ============================================================
# Master's Research Project
# run_analysis.R
#
# Purpose:
# Execute the complete reproducible research analysis pipeline.
#
# Usage:
# Rscript run_analysis.R
# ============================================================

# ------------------------------------------------------------
# 1. Pipeline initialization
# ------------------------------------------------------------

pipeline_start <- Sys.time()

cat("\n")
cat("============================================================\n")
cat("AUTONOMOUS PARKING RESEARCH ANALYSIS PIPELINE\n")
cat("============================================================\n")

cat("Started:", format(pipeline_start), "\n")
cat("R version:", R.version.string, "\n")

# ------------------------------------------------------------
# 2. Set working directory
# ------------------------------------------------------------

script_argument <- grep(
  "^--file=",
  commandArgs(trailingOnly = FALSE),
  value = TRUE
)

if (length(script_argument) > 0) {

  script_path <- sub(
    "^--file=",
    "",
    script_argument[1]
  )

  analysis_root <- dirname(
    normalizePath(
      script_path,
      mustWork = TRUE
    )
  )

  setwd(analysis_root)
}

cat("Working directory:", getwd(), "\n")

# ------------------------------------------------------------
# 3. Verify required packages
# ------------------------------------------------------------

required_packages <- c(
  "tidyverse",
  "broom",
  "patchwork",
  "scales",
  "knitr"
)

missing_packages <- required_packages[
  !vapply(
    required_packages,
    requireNamespace,
    quietly = TRUE,
    FUN.VALUE = logical(1)
  )
]

if (length(missing_packages) > 0) {

  stop(
    paste(
      "Missing required packages:",
      paste(missing_packages, collapse = ", ")
    )
  )
}

cat("\nRequired R packages are available.\n")

# ------------------------------------------------------------
# 4. Define analysis stages
# ------------------------------------------------------------

scripts <- c(
  "R/01_load_validate.R",
  "R/02_descriptive_statistics.R",
  "R/03_statistical_tests.R",
  "R/04_primary_visualizations.R",
  "R/05_supplementary_visualizations.R",
  "R/06_export_tables.R"
)

stage_names <- c(
  "Data loading and validation",
  "Descriptive statistics",
  "Inferential statistical analysis",
  "Primary research visualizations",
  "Supplementary and network analysis",
  "Publication LaTeX tables"
)

stopifnot(
  all(file.exists(scripts))
)

# ------------------------------------------------------------
# 5. Verify input datasets
# ------------------------------------------------------------

input_files <- c(
  "data/preliminary/experiment_reports_completed.csv",
  "data/primary/main_experiment_reports_completed.csv",
  "data/supplementary/final_experiment_reports_completed.csv"
)

stopifnot(
  all(file.exists(input_files)),
  all(file.info(input_files)$size > 0)
)

cat("All required input datasets are available.\n")

# ------------------------------------------------------------
# 6. Create output directories
# ------------------------------------------------------------

output_directories <- c(
  "tables/csv",
  "tables/latex",
  "figures/pdf",
  "figures/png",
  "logs"
)

for (directory in output_directories) {

  dir.create(
    directory,
    recursive = TRUE,
    showWarnings = FALSE
  )
}

# ------------------------------------------------------------
# 7. Initialize execution manifest
# ------------------------------------------------------------

execution_manifest <- data.frame(
  Stage = integer(),
  Description = character(),
  Script = character(),
  Status = character(),
  Duration_Seconds = numeric(),
  stringsAsFactors = FALSE
)

manifest_path <- "logs/pipeline_execution_manifest.csv"

rscript <- file.path(
  R.home("bin"),
  if (.Platform$OS.type == "windows") {
    "Rscript.exe"
  } else {
    "Rscript"
  }
)

stopifnot(file.exists(rscript))

# ------------------------------------------------------------
# 8. Execute analysis stages
# ------------------------------------------------------------

for (i in seq_along(scripts)) {

  cat("\n")
  cat("============================================================\n")

  cat(
    sprintf(
      "STAGE %d OF %d: %s\n",
      i,
      length(scripts),
      stage_names[i]
    )
  )

  cat("Script:", scripts[i], "\n")
  cat("============================================================\n")

  stage_start <- Sys.time()

  exit_code <- system2(
    command = rscript,
    args = shQuote(scripts[i])
  )

  stage_end <- Sys.time()

  duration <- as.numeric(
    difftime(
      stage_end,
      stage_start,
      units = "secs"
    )
  )

  status <- if (exit_code == 0) {
    "Completed"
  } else {
    "Failed"
  }

  execution_manifest <- rbind(
    execution_manifest,

    data.frame(
      Stage = i,
      Description = stage_names[i],
      Script = scripts[i],
      Status = status,
      Duration_Seconds = round(duration, 2),
      stringsAsFactors = FALSE
    )
  )

  write.csv(
    execution_manifest,
    manifest_path,
    row.names = FALSE
  )

  cat("\nStage status:", status, "\n")
  cat("Duration:", round(duration, 2), "seconds\n")

  if (exit_code != 0) {

    stop(
      paste(
        "Analysis pipeline halted at:",
        scripts[i]
      )
    )
  }
}

# ------------------------------------------------------------
# 9. Validate generated research outputs
# ------------------------------------------------------------

count_files <- function(directory, pattern) {

  length(
    list.files(
      directory,
      pattern = pattern
    )
  )
}

output_summary <- data.frame(

  Output = c(
    "Statistical CSV tables",
    "PDF figures",
    "PNG figures",
    "LaTeX tables",
    "LaTeX table manifest"
  ),

  Expected = c(
    46,
    25,
    25,
    12,
    1
  ),

  Actual = c(
    count_files("tables/csv", "\\.csv$"),
    count_files("figures/pdf", "\\.pdf$"),
    count_files("figures/png", "\\.png$"),
    count_files("tables/latex", "\\.tex$"),
    count_files("tables/latex", "^table_manifest\\.csv$")
  )
)

output_summary$Valid <-
  output_summary$Expected == output_summary$Actual

write.csv(
  output_summary,
  "logs/pipeline_output_summary.csv",
  row.names = FALSE
)

cat("\n=== OUTPUT VALIDATION ===\n")

print(
  output_summary,
  row.names = FALSE
)

stopifnot(
  all(output_summary$Valid)
)

# ------------------------------------------------------------
# 10. Record R environment information
# ------------------------------------------------------------

capture.output(
  sessionInfo(),
  file = "logs/session_info.txt"
)

package_versions <- data.frame(

  Package = required_packages,

  Version = vapply(
    required_packages,

    function(package) {
      as.character(packageVersion(package))
    },

    character(1)
  )
)

write.csv(
  package_versions,
  "logs/package_versions.csv",
  row.names = FALSE
)

# Record checksums of original input datasets.

input_checksums <- data.frame(
  File = input_files,
  MD5 = unname(tools::md5sum(input_files))
)

write.csv(
  input_checksums,
  "logs/input_data_checksums.csv",
  row.names = FALSE
)

# ------------------------------------------------------------
# 11. Final execution summary
# ------------------------------------------------------------

pipeline_end <- Sys.time()

total_duration <- as.numeric(
  difftime(
    pipeline_end,
    pipeline_start,
    units = "secs"
  )
)

cat("\n")
cat("============================================================\n")
cat("RESEARCH ANALYSIS PIPELINE COMPLETED SUCCESSFULLY\n")
cat("============================================================\n")

cat("Completed stages:", nrow(execution_manifest), "\n")

cat(
  "Total generated research outputs:",
  sum(output_summary$Actual),
  "\n"
)

cat(
  "Total execution time:",
  round(total_duration, 2),
  "seconds\n"
)

cat("Started:", format(pipeline_start), "\n")
cat("Finished:", format(pipeline_end), "\n")

cat("\n=== EXECUTION MANIFEST ===\n")

print(
  execution_manifest,
  row.names = FALSE
)

cat("\nExecution records saved to logs/\n")
cat("All research analysis stages completed.\n")
