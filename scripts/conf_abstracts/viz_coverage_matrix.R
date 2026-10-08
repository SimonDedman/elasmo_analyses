#!/usr/bin/env Rscript
## viz_coverage_matrix.R
## Slide graphic of conference-abstract coverage: one tile per meeting
## (series x year), coloured by how close we are to having its abstracts in
## the database. Built for the EEA 2026 talk to show which abstract books are
## still needed.
##
## Reads the Coverage sheet of outputs/conference_coverage_matrix.xlsx (cells
## are "Host city; Status - detail", written by build_coverage_matrix.py) and
## upgrades a cell to "in the database" where database/conference_abstracts.db
## already holds abstract bodies for that meeting, since the workbook can lag
## the database between rebuilds.
##
## Run from the repo root: Rscript scripts/conf_abstracts/viz_coverage_matrix.R

suppressPackageStartupMessages({
  library(tidyverse)
  library(openxlsx)
  library(RSQLite)
})

xlsx_path <- "outputs/conference_coverage_matrix.xlsx"
db_path   <- "database/conference_abstracts.db"
out_png   <- "outputs/figures/conference_coverage_matrix.png"
first_year <- 1983   # AES founded 1983

# Series shown, top to bottom: the four chondrichthyan society meetings, then
# every other series from which the corpus cites ten or more abstracts we do
# not hold, most-needed first (n_needed in the workbook's Conferences sheet).
# ASIH/JMIH is left out: it is the same book as AES. Workbook column ->
# display label, and the `meeting` key the database uses for that series.
series <- tribble(
  ~column,           ~label,                                   ~db_meeting, ~rotate,
  "EEA",             "EEA (Europe)",                           "EEA",       TRUE,
  "AES",             "AES (Americas)",                         "AES",       TRUE,
  "OCS",             "OCS (Oceania)",                          "OCS",       TRUE,
  "SI",              "Sharks International",                   "SI",        FALSE,
  "WCH",             "World Congress of Herpetology (101)",    NA,          FALSE,
  "Palaeo/geol",     "Palaeontology & geology meetings (81)",  NA,          TRUE,
  "ECC",             "Encuentro Colombiano, Condrictios (79)", NA,          FALSE,
  "SVP",             "Soc. Vertebrate Paleontology (57)",      NA,          TRUE,
  "IPFC",            "Indo-Pacific Fish Conference (49)",      "IPFC",      FALSE,
  "W Africa",        "West Africa shark colloquium (48)",      NA,          FALSE,
  "SOMEPEC",         "SOMEPEC (Mexico) (44)",                  "SOMEPEC",   FALSE,
  "SICB",            "SICB (38)",                              NA,          TRUE,
  "SIBM",            "SIBM, Italian marine biology (24)",      NA,          TRUE,
  "Mesozoic Fishes", "Mesozoic Fishes meetings (17)",          NA,          FALSE,
  "ICRS",            "Int. Coral Reef Symposium (13)",         NA,          FALSE,
  "GCFI",            "GCFI (13)",                              NA,          TRUE,
  "Pac Shark Wksp",  "Pacific Shark Workshop (12)",            NA,          FALSE,
  "AFS",             "American Fisheries Society (10)",        NA,          FALSE
)

# Workbook status -> slide category (fewer classes than the workbook's ten).
cat_levels <- c("In the database", "In hand, being processed",
                "Being sought: copy needed", "Missing: can you help?")
status_cat <- c(
  Ingested = cat_levels[1], Extracted = cat_levels[1], Partial = cat_levels[1],
  Digital = cat_levels[2], OCR = cat_levels[2], Schedule = cat_levels[2],
  Hardcopy = cat_levels[3], Programme = cat_levels[3], Pending = cat_levels[3],
  Missing = cat_levels[4]
)

cov <- read.xlsx(xlsx_path, sheet = "Coverage", check.names = FALSE, sep.names = " ")
long <- cov |>
  select(Year, all_of(series$column)) |>
  pivot_longer(-Year, names_to = "column", values_to = "cell") |>
  filter(!is.na(cell), Year >= first_year) |>
  mutate(
    Year   = as.integer(Year),
    # the status is the first word after the first ";"; the host city precedes it
    status = str_match(cell, "^[^;]*;\\s*([A-Za-z]+)")[, 2],
    city   = str_trim(str_replace(cell, ";.*$", "")),
    city   = str_replace(city, ",.*$", ""),                 # drop state / country
    city   = str_replace(city, "\\s*\\(.*\\)$", ""),   # drop "(=SI2022)" etc
    city   = case_when(city %in% c("?", "") ~ "",          # unknown host: no label
                       column == "EEA" & Year == 2026 ~ "You are here",
                       TRUE ~ city),
    city   = str_replace(city, "^Palma de Majorca$", "Palma"),
    city   = str_replace(city, "^Ciudad Universitaria$", "Mexico City"),
    city   = str_replace(city, "^Miraflores de la Sierra$", "Miraflores")
  ) |>
  filter(status != "NA") |>              # "NA - no meeting" cells
  filter(!(column == "EEA" & Year == 2020)) |>   # confirmed: no EEA meeting in 2020
  left_join(series, by = "column")

unknown <- setdiff(unique(long$status), names(status_cat))
if (length(unknown)) stop("Unmapped status in workbook: ", paste(unknown, collapse = ", "))

# Meetings whose abstract bodies are already in the database.
con <- dbConnect(SQLite(), db_path)
in_db <- dbGetQuery(con, "
  SELECT m.meeting AS db_meeting, m.year AS Year, COUNT(*) AS n,
         SUM(LENGTH(COALESCE(a.abstract_text, '')) > 200) AS n_body
  FROM abstracts a JOIN meetings m USING (meeting_id)
  GROUP BY 1, 2")
dbDisconnect(con)
in_db <- in_db |> filter(n_body / n > 0.5) |> select(db_meeting, Year) |> mutate(db_has = TRUE)

long <- long |>
  left_join(in_db, by = c("db_meeting", "Year")) |>
  mutate(
    category = unname(status_cat[status]),
    upgraded = !is.na(db_has) & category != cat_levels[1],
    category = if_else(upgraded, cat_levels[1], category),
    category = factor(category, levels = cat_levels),
    label    = factor(label, levels = rev(series$label))
  )

cat("Cells upgraded from the database:\n")
print(long |> filter(upgraded) |> select(column, Year, status), n = 50)
cat("\nTiles per series and category:\n")
print(long |> count(label, category) |> pivot_wider(names_from = category, values_from = n, values_fill = 0))
cat("\nMissing or copy-needed meetings:\n")
print(long |> filter(category %in% cat_levels[3:4]) |> arrange(label, Year) |>
        transmute(column, Year, category, cell = str_trunc(cell, 90)), n = 100)

# host-city labels on the tiles we still need (the two amber/red classes)
# Dense rows: rotated, on the tile (white on red, dark on amber). Sparse rows:
# upright, to the right of the tile, where the neighbouring years are blank.
lab <- long |>
  filter(category %in% cat_levels[3:4]) |>
  mutate(angle  = if_else(rotate, 90, 0),
         size   = if_else(rotate, 3.1, 3.4),
         x_lab  = if_else(rotate, Year, Year + 0.62),
         hjust  = if_else(rotate, 0.5, 0),
         colour = "grey5")                 # black on every tile: survives overrunning the box

cat_cols <- c("In the database" = "#1B7F5A", "In hand, being processed" = "#9BCB6C",
              "Being sought: copy needed" = "#F2B134", "Missing: can you help?" = "#EC6B74")

p <- ggplot(long, aes(Year, label)) +
  geom_tile(aes(fill = category), colour = "white", linewidth = 0.9, height = 0.8) +
  geom_text(data = lab, aes(x = x_lab, label = city, angle = angle, size = size,
                            colour = colour, hjust = hjust),
            fontface = "bold", lineheight = 0.8, show.legend = FALSE) +
  coord_cartesian(clip = "off") +
  scale_size_identity() +
  scale_colour_identity() +
  scale_fill_manual(values = cat_cols, name = NULL, drop = FALSE) +
  scale_x_continuous(breaks = seq(1985, 2025, 5), expand = expansion(add = 0.6),
                     sec.axis = dup_axis(name = NULL)) +
  labs(title = "Conference abstracts: what we hold, and what we still need",
       subtitle = paste0(format(sum(long$category == cat_levels[1])), " of ", nrow(long),
                         " meetings since ", first_year,
                         " are in the database. Blank = no meeting that year."),
       x = NULL, y = NULL) +
  theme_minimal(base_size = 16) +
  theme(
    plot.background  = element_rect(fill = "white", colour = NA),
    panel.grid       = element_blank(),
    plot.title       = element_text(face = "bold", size = 19),
    plot.subtitle    = element_text(colour = "grey35", size = 13),
    axis.text.y      = element_text(colour = "grey10", size = 14),
    axis.text.x      = element_text(colour = "grey35"),
    legend.position  = "bottom",
    legend.text      = element_text(size = 13),
    legend.key.size  = unit(0.55, "cm"),
    plot.margin      = margin(8, 14, 6, 8)
  )

ggsave(out_png, p, width = 16, height = 10.2, dpi = 200, bg = "white")
cat("\nSaved:", out_png, "\n")
