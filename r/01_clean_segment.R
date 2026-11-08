# =============================================================================
# 01_clean_segment.R
# Cleaning, estimated monthly value (EMV) and customer segmentation
#
# Input : data/raw/Quick Commerce Consumer Behavior (100Responses).xlsx
#         (quick commerce consumer behavior survey, India)
# Output: data/clean/segmented_data.csv  -> single data source for the app
#
# Run from the project root (open quick-commerce-india.Rproj).
# Packages: readxl, dplyr, readr
# =============================================================================

library(readxl)
library(dplyr)
library(readr)

# -----------------------------------------------------------------------------
# 0. PARAMETERS
# -----------------------------------------------------------------------------
# Quantile method. Type 7 is R's default (linear interpolation). Kept as a
# parameter because EMV is highly discrete and the method can shift the cuts.
QUANTILE_TYPE <- 7

RAW_PATH   <- "data/raw/Quick Commerce Consumer Behavior (100Responses).xlsx"
CLEAN_PATH <- "data/clean/segmented_data.csv"

# Column names used more than once
CITY_COL   <- "Current Residence City"
OCC_COL    <- "Occupation"
INCOME_COL <- "Please state your monthly income."
SPEND_COL  <- "How much is your average spend on an order?"
FREQ_COL   <- "How often do you shop online for groceries and essentials?"

# -----------------------------------------------------------------------------
# 1. READ
# -----------------------------------------------------------------------------
# Read headers first to set column types: Timestamp as date, everything else
# as text. Prevents type guessing from turning answers into numbers (e.g. a
# postal code typed as a city) and keeps ranges like "0-15000" as categories.
header <- names(read_excel(RAW_PATH, n_max = 0, .name_repair = "minimal"))
col_types <- ifelse(trimws(header) == "Timestamp", "date", "text")

# trim_ws = FALSE: readxl trims every cell by default. Disabled so that value
# cleaning is explicit and applied only where intended (step 3).
raw <- read_excel(
  RAW_PATH,
  col_types    = col_types,
  trim_ws      = FALSE,
  .name_repair = "minimal"
)

# Trim leading/trailing spaces from column names only (at least one header
# has a trailing space). Nothing else changes: the app references questions
# by their exact text, including the one with a comma ("fruits, vegetables").
names(raw) <- trimws(names(raw))

cat("File read:", nrow(raw), "rows x", ncol(raw), "columns\n")

# -----------------------------------------------------------------------------
# 2. COLUMN SELECTION
# -----------------------------------------------------------------------------
# (a) The 17 questions behind the dashboard charts: demographic and
#     socioeconomic profile, ordering habits and service preferences.
APP_COLS <- c(
  "Gender",
  "Age",
  CITY_COL,
  "Status of your accommodation in your Current City",
  OCC_COL,
  INCOME_COL,
  "Monthly Household Income",
  "Your current relationship status",
  "Do you have loved ones in different city?",
  "What type of products do you typically order through quick commerce platforms?",
  "What delivery time frame do you expect from a quick commerce platform?",
  "At what time of the day generally do you order?",
  "What factors influence your choice of a quick commerce platform?",
  "How important are discounts and offers in your decision to use a quick commerce platform?",
  "Would you prefer if you have a live product feed (a short video of the product) for fruits, vegetables and other perishables on quick commerce platform?",
  "What would motivate you to switch from your current quick commerce platform to Flipkart?",
  "What would you suggest Flipkart do to become your preferred quick commerce platform?"
)

# (b) The two inputs of EMV: spend per order and purchase frequency. Also
#     used in the descriptive statistics to profile each segment.
EMV_COLS <- c(SPEND_COL, FREQ_COL)

KEEP_COLS <- c(APP_COLS, EMV_COLS)

# Everything else is dropped, "Name" in particular: it adds nothing to the
# analysis and would expose personal data (anonymization). Unused ranking and
# free-text questions are dropped too: keeping only what each chart needs
# limits exposure and makes the data behind the dashboard explicit.
missing_cols <- setdiff(KEEP_COLS, names(raw))
if (length(missing_cols) > 0) {
  stop(
    "These columns were not found in the file:\n  - ",
    paste(missing_cols, collapse = "\n  - ")
  )
}

df <- raw %>% select(all_of(KEEP_COLS))
cat("Columns kept:", ncol(df), "of", ncol(raw), "\n")

# -----------------------------------------------------------------------------
# 3. VALUE CLEANING
# -----------------------------------------------------------------------------
# Answer texts are left untouched because the dashboard shows categories as
# they are (e.g. "0-15000", "Between 1Lakh - 2Lakh"). Only variants of the
# same answer are unified. No rows are removed here: EMV is computed on the
# full sample first.

# --- 3.1 City of residence ---
# Free-text field: the same city appears with extra spaces, different casing,
# typos or the state appended. Left as is, one city would split into several
# bars in the chart.
CITY_MAP <- c(
  "amritsar"        = "Amritsar",
  "AMRITSAR"        = "Amritsar",
  "Anritsar"        = "Amritsar",
  "Amritsar Punjab" = "Amritsar"
)

city_before <- df[[CITY_COL]]
city_after  <- trimws(city_before)
n_trimmed   <- sum(city_after != city_before, na.rm = TRUE)

is_variant <- city_after %in% names(CITY_MAP)
city_after[is_variant] <- unname(CITY_MAP[city_after[is_variant]])
df[[CITY_COL]] <- city_after

cat("\n[City] values with spaces trimmed:", n_trimmed, "\n")
cat("[City] variants unified as 'Amritsar':", sum(is_variant), "\n")

# --- 3.2 Occupation ---
# "Business" and "Business Owner" are variants of the same answer. Unified
# into the dashboard's category so no respondent drops out of the chart.
is_business <- df[[OCC_COL]] %in% "Business"
df[[OCC_COL]][is_business] <- "Business Owner"
cat("[Occupation] 'Business' -> 'Business Owner':", sum(is_business), "\n")

# -----------------------------------------------------------------------------
# 4. ESTIMATED MONTHLY VALUE (EMV)
# -----------------------------------------------------------------------------
# EMV = typical spend per order x orders per month (rupees per month).
# Combines both dimensions of customer value, ticket size and frequency,
# into a single measure.

# Spend per order: the survey records ranges, not amounts. The midpoint is
# the most neutral point estimate when the distribution within each range is
# unknown. All ranges are closed (no open "5000+"), so it is always defined.
# Survey note: ranges share their bounds (100-500, 500-1000, ...); this does
# not affect the calculation since each respondent picked one option.
SPEND_MIDPOINT <- c(
  "100-500"   = 300,
  "500-1000"  = 750,
  "1000-2000" = 1500,
  "2000-5000" = 3500
)

# Monthly frequency, as orders per month:
#   Daily     -> 30   (one order per day)
#   Weekly    -> 4    (four weeks per month; conservative vs. 4.3)
#   Bi weekly -> 2    (read as every two weeks)
#   Monthly   -> 1
#   Rarely    -> 0.5  (about one order every two months)
#   Other     -> 0.2  (sporadic, no stated habit; deliberately low weight)
#   Never     -> 0    (no online orders of this kind; EMV of zero)
MONTHLY_FREQ <- c(
  "Daily"     = 30,
  "Weekly"    = 4,
  "Bi weekly" = 2,
  "Monthly"   = 1,
  "Rarely"    = 0.5,
  "Other"     = 0.2,
  "Never"     = 0
)

# Any answer outside these maps stops the script. An unmapped value is never
# silently turned into 0, which would push that respondent to the lowest
# segment without justification.
unmapped_spend <- setdiff(unique(df[[SPEND_COL]]), names(SPEND_MIDPOINT))
unmapped_freq  <- setdiff(unique(df[[FREQ_COL]]),  names(MONTHLY_FREQ))

if (length(unmapped_spend) > 0 || length(unmapped_freq) > 0) {
  stop(
    "Unmapped values found for EMV.\n",
    "  Spend per order: ", paste(unmapped_spend, collapse = " | "), "\n",
    "  Frequency:       ", paste(unmapped_freq,  collapse = " | ")
  )
}

df <- df %>%
  mutate(
    EMV = unname(SPEND_MIDPOINT[.data[[SPEND_COL]]]) *
          unname(MONTHLY_FREQ[.data[[FREQ_COL]]]),
    # Rounded to avoid floating-point residue (e.g. 3500 x 0.2)
    EMV = round(EMV, 2)
  )

cat("\n[EMV] summary over", nrow(df), "responses:\n")
print(summary(df$EMV))

# -----------------------------------------------------------------------------
# 5. SEGMENTATION BY EMV QUARTILES
# -----------------------------------------------------------------------------
# Why quartiles? There are no external business thresholds for a high-value
# customer in this market, so cuts are relative to the sample. Quartiles
# give groups of comparable size, depend on rank rather than magnitude
# (robust to the strong right skew of EMV), and are easy to communicate
# ("the top 25% by spend").
#
# Assignment rule: an EMV equal to a cut stays in the lower segment
# (right-closed intervals). Since EMV is the product of two categorical
# variables there are many ties, so segments are not exactly 25% each:
# respondents with the same EMV always stay together.
#
# Segmentation uses the full sample, before any display filter (see step 7).
SEGMENT_LABELS <- c(
  "Bronze Segment (Q1)",
  "Silver Segment (Q2)",
  "Gold Segment (Q3)",
  "Diamond Segment (Q4)"
)

cuts <- quantile(df$EMV, probs = c(0.25, 0.50, 0.75),
                 type = QUANTILE_TYPE, names = FALSE)

# Equivalent to cut(..., right = TRUE), but does not fail if two cuts coincide
seg_idx <- 1 + (df$EMV > cuts[1]) + (df$EMV > cuts[2]) + (df$EMV > cuts[3])
df$Segment <- SEGMENT_LABELS[seg_idx]

cat("\n[Segmentation] quantile type =", QUANTILE_TYPE, "\n")
cat("[Segmentation] cuts (Q1 | Q2 | Q3):",
    paste(cuts, collapse = " | "), "\n")

# -----------------------------------------------------------------------------
# 6. CONSISTENCY CHECK
# -----------------------------------------------------------------------------
if (any(is.na(df$EMV))) {
  stop(sum(is.na(df$EMV)), " responses have no EMV.")
}

seg_counts <- table(factor(df$Segment, levels = SEGMENT_LABELS))
if (any(seg_counts == 0)) {
  stop("Segments with no cases: ",
       paste(names(seg_counts)[seg_counts == 0], collapse = ", "))
}

cat("\n[Consistency] EMV available for every response.\n")
cat("[Consistency] respondents per segment (full sample):\n")
print(seg_counts)

# -----------------------------------------------------------------------------
# 7. FINAL FILTER FOR THE DASHBOARD
# -----------------------------------------------------------------------------
# Rows that cannot be shown correctly in the profile charts are excluded:
#   - numeric city (e.g. a postal code instead of a city name);
#   - monthly income outside the survey's valid categories (currently a
#     safeguard against unexpected categories if the input changes).
#
# Why after segmenting? Quartile cuts are computed on the full sample. A
# respondent's EMV is still valid market information even if their city was
# mistyped. Filtering first would let a data-entry issue in an unrelated
# field shift the cuts, and with them other respondents' segments.
#
# Survey note: "100000+" and "200000+" overlap. Both are kept as each
# respondent chose them; reassigning them would mean inventing information.
VALID_INCOME <- c(
  "0-15000", "15001-25000", "25001-40000", "40001-60000",
  "60001-85000", "85001-100000", "100000+", "200000+"
)

numeric_city   <- grepl("^[0-9]+$", df[[CITY_COL]])
invalid_income <- !(df[[INCOME_COL]] %in% VALID_INCOME)
to_drop        <- numeric_city | invalid_income

cat("\n[Filter] rows with numeric city:          ", sum(numeric_city), "\n")
cat("[Filter] rows with income outside the list:", sum(invalid_income), "\n")
cat("[Filter] total rows removed:               ", sum(to_drop), "\n")
if (any(to_drop)) {
  cat("[Filter] removed rows:\n")
  print(
    df[to_drop, ] %>%
      transmute(
        city    = .data[[CITY_COL]],
        income  = .data[[INCOME_COL]],
        EMV,
        Segment,
        reason  = case_when(
          numeric_city[to_drop] & invalid_income[to_drop] ~ "numeric city + invalid income",
          numeric_city[to_drop]                           ~ "numeric city",
          TRUE                                            ~ "invalid income"
        )
      )
  )
}

df_final <- df[!to_drop, ]

# -----------------------------------------------------------------------------
# 8. EXPORT
# -----------------------------------------------------------------------------
# EMV is written as text without scientific notation (105000, not 1e+05)
format_emv <- function(x) format(x, scientific = FALSE, trim = TRUE,
                                 drop0trailing = TRUE)

# EMV and Segment go last. Missing values are written as empty cells.
out <- df_final %>%
  relocate(EMV, Segment, .after = last_col()) %>%
  mutate(EMV = format_emv(EMV))

write_csv(out, CLEAN_PATH, na = "")

cat("\n[Export]", CLEAN_PATH, "->", nrow(out), "rows x",
    ncol(out), "columns\n")
cat("[Export] respondents per segment (final dataset):\n")
print(table(factor(out$Segment, levels = SEGMENT_LABELS)))
