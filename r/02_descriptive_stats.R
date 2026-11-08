# =============================================================================
# 02_descriptive_stats.R
# Descriptive statistics by customer segment
#
# Input  : data/clean/segmented_data.csv  (produced by 01_clean_segment.R)
# Outputs: outputs/emv_by_segment.csv
#          outputs/distribution_by_segment.csv
#
# Run from the project root (open quick-commerce-india.Rproj).
# Packages: readr, dplyr
# =============================================================================

library(readr)
library(dplyr)

CLEAN_PATH <- "data/clean/segmented_data.csv"
OUT_DIR    <- "outputs"

SPEND_COL <- "How much is your average spend on an order?"
FREQ_COL  <- "How often do you shop online for groceries and essentials?"

# Segments ordered from lowest to highest value, so tables read as a scale
SEGMENT_LABELS <- c(
  "Bronze Segment (Q1)",
  "Silver Segment (Q2)",
  "Gold Segment (Q3)",
  "Diamond Segment (Q4)"
)

# -----------------------------------------------------------------------------
# 1. READ
# -----------------------------------------------------------------------------
# Answers are categories, so everything is read as text except EMV.
# Empty cells are treated as missing answers.
seg <- read_csv(
  CLEAN_PATH,
  col_types = cols(.default = col_character(), EMV = col_double()),
  na = ""
) %>%
  mutate(Segment = factor(Segment, levels = SEGMENT_LABELS))

cat("Dataset:", nrow(seg), "rows x", ncol(seg), "columns\n")

if (anyNA(seg$Segment)) {
  stop("Some rows have a segment outside the expected labels.")
}

dir.create(OUT_DIR, showWarnings = FALSE)

# -----------------------------------------------------------------------------
# 2. EMV BY SEGMENT
# -----------------------------------------------------------------------------
# Size, mean, median, min and max of EMV per segment.
# The median is reported alongside the mean because EMV is highly skewed:
# two extreme cases (EMV of 105,000) inflate the Diamond mean well above a
# typical customer in that group. Showing both makes that effect visible.
emv_by_segment <- seg %>%
  group_by(segment = Segment) %>%
  summarise(
    n      = n(),
    mean   = round(mean(EMV), 1),
    median = median(EMV),
    min    = min(EMV),
    max    = max(EMV),
    .groups = "drop"
  ) %>%
  arrange(segment)

write_csv(emv_by_segment, file.path(OUT_DIR, "emv_by_segment.csv"))
cat("\nEMV by segment:\n")
print(emv_by_segment)

# -----------------------------------------------------------------------------
# 3. DISTRIBUTION OF KEY VARIABLES BY SEGMENT
# -----------------------------------------------------------------------------
# Profile of each segment on three demographic variables and the two EMV
# inputs, to show which mix of ticket size and frequency defines each one.
# Percentages are computed within each segment (sum to 100 per segment):
# segments differ in size, and the point is to compare their composition.
# Long format (variable, segment, category, n, pct) is easy to filter,
# plot or join.
VARIABLES <- c(
  "Gender"             = "Gender",
  "Age"                = "Age",
  "Occupation"         = "Occupation",
  "Spend per order"    = SPEND_COL,
  "Shopping frequency" = FREQ_COL
)

# Logical order for ordinal variables; the rest are sorted alphabetically
CATEGORY_ORDER <- list(
  "Spend per order"    = c("100-500", "500-1000", "1000-2000", "2000-5000"),
  "Shopping frequency" = c("Daily", "Weekly", "Bi weekly", "Monthly",
                           "Rarely", "Other", "Never")
)

distribution_one <- function(label, column) {
  d <- seg %>%
    count(segment = Segment, category = .data[[column]], name = "n") %>%
    group_by(segment) %>%
    mutate(pct = round(100 * n / sum(n), 1)) %>%
    ungroup() %>%
    mutate(variable = label, .before = 1)

  # Missing answers, if any, are kept as an explicit category, not dropped
  order <- CATEGORY_ORDER[[label]]
  if (is.null(order)) order <- sort(unique(d$category))
  d %>%
    mutate(cat_rank = match(category, order)) %>%
    arrange(segment, cat_rank, category) %>%
    select(-cat_rank)
}

distribution_by_segment <- bind_rows(
  lapply(names(VARIABLES), function(lbl) distribution_one(lbl, VARIABLES[[lbl]]))
)

write_csv(distribution_by_segment,
          file.path(OUT_DIR, "distribution_by_segment.csv"))

cat("\nDistribution by segment:", nrow(distribution_by_segment),
    "rows saved to", file.path(OUT_DIR, "distribution_by_segment.csv"), "\n")
cat("Files written to", OUT_DIR, "/\n")
