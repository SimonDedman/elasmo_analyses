#!/usr/bin/env Rscript
# Generate geographic maps for shark research papers
# Uses paper_geography table (6,183 papers with author country data)

library(ggplot2)
library(sf)
library(rnaturalearth)
library(rnaturalearthdata)
library(RSQLite)
library(dplyr)
library(ggrepel)
library(shadowtext)

# Connect to database
conn <- dbConnect(SQLite(), "database/technique_taxonomy.db")

# Get papers per country
papers_df <- dbGetQuery(conn, "
  SELECT first_author_country as country, COUNT(*) as papers
  FROM paper_geography
  WHERE has_author_country = 1 AND first_author_country IS NOT NULL
  GROUP BY first_author_country
")
dbDisconnect(conn)

cat("Papers per country loaded:", nrow(papers_df), "countries\n")
cat("Total papers:", sum(papers_df$papers), "\n\n")

# Get world map
world <- ne_countries(scale = "medium", returnclass = "sf")

# Country name mapping for mismatches
country_mapping <- c(
  "USA" = "United States of America",
  "UK" = "United Kingdom",
  "Russia" = "Russian Federation",
  "Taiwan" = "Taiwan",
  "South Korea" = "Republic of Korea",
  "Iran" = "Iran (Islamic Republic of)",
  "Czech Republic" = "Czechia",
  "UAE" = "United Arab Emirates"
)

# Reverse mapping for labels (to show short names)
country_short_names <- c(
  "United States of America" = "USA",
  "United Kingdom" = "UK",
  "Russian Federation" = "Russia",
  "Republic of Korea" = "S. Korea",
  "Iran (Islamic Republic of)" = "Iran",
  "Czechia" = "Czech Rep.",
  "United Arab Emirates" = "UAE",
  "New Zealand" = "NZ",
  "South Africa" = "S. Africa",
  "Saudi Arabia" = "Saudi Ar."
)

# Large countries where labels should be placed directly at centroid (no repel)
large_countries <- c(
  "United States of America", "Canada", "Brazil", "Australia", "China",

"Russia", "India", "Argentina", "Mexico", "Indonesia", "South Africa",
  "Japan", "France", "Spain", "Germany", "Italy", "United Kingdom",
  "Sweden", "Norway", "Finland", "Poland", "Turkey", "Iran (Islamic Republic of)",
  "Saudi Arabia", "Egypt", "Algeria", "Libya", "Peru", "Chile", "Colombia",
  "Venezuela", "New Zealand", "Philippines", "Thailand", "Malaysia", "Vietnam",
  "Pakistan", "Bangladesh", "Myanmar", "Kazakhstan", "Mongolia", "Ukraine",
  "Ireland", "Portugal", "Greece", "Romania", "Bulgaria"
)

# Apply mapping
papers_df$country_mapped <- papers_df$country
for (old_name in names(country_mapping)) {
  papers_df$country_mapped[papers_df$country == old_name] <- country_mapping[old_name]
}

# Join with world map
world_data <- world %>%
  left_join(papers_df, by = c("name" = "country_mapped")) %>%
  mutate(
    papers = ifelse(is.na(papers), 0, papers),
    has_papers = papers > 0
  )

# Get centroids for labels
world_centroids <- world_data %>%
  st_centroid() %>%
  st_coordinates() %>%
  as.data.frame() %>%
  rename(lon = X, lat = Y)

world_data <- world_data %>%
  bind_cols(world_centroids)

# Manual centroid adjustments for countries with overseas territories, awkward shapes,
# or to prevent label overlaps
world_data <- world_data %>%
  mutate(
    lon = case_when(
      # Countries with overseas territories pulling centroid off
      name == "France" ~ 2.5,
      name == "United States of America" ~ -98,
      name == "Norway" ~ 8,  # Shift west to avoid Sweden overlap
      name == "Netherlands" ~ 5.5,

      # South America - Chile/Argentina overlap
      name == "Chile" ~ -75,  # Shift west (coast)
      name == "Argentina" ~ -64,  # Shift east (inland)

      # Southeast Asia - Singapore/Malaysia overlap
      name == "Singapore" ~ 107,  # Shift east into sea
      name == "Malaysia" ~ 102,  # Keep Malaysia centered

      # Middle East - Jordan/Saudi Arabia overlap
      name == "Jordan" ~ 38,  # Shift east
      name == "Saudi Arabia" ~ 45,  # Keep Saudi centered

      # Europe - Ireland/UK overlap
      name == "Ireland" ~ -9,  # Shift west into Atlantic
      name == "United Kingdom" ~ -1,  # Shift east

      # Europe - Switzerland/Portugal/Spain overlaps
      name == "Switzerland" ~ 8.5,  # Keep centered
      name == "Portugal" ~ -9,  # Shift west into Atlantic

      # Europe - Czech Republic/Poland overlap
      name == "Czechia" ~ 15.5,
      name == "Poland" ~ 19.5,  # Shift east

      # Europe - Austria/France overlap (Austria label drifting west)
      name == "Austria" ~ 14,  # Keep Austria east

      # South America - Ecuador/Colombia overlap
      name == "Ecuador" ~ -81,  # Shift west into Pacific
      name == "Colombia" ~ -73,  # Shift east

      # Southeast Asia - Hong Kong/Thailand overlap
      name == "Hong Kong" ~ 117,  # Shift east into sea
      name == "Thailand" ~ 101,  # Keep Thailand centered

      # Middle East - Israel/Egypt overlap
      name == "Israel" ~ 36,  # Shift east
      name == "Egypt" ~ 30,  # Keep Egypt west

      # Europe - Turkey/Cyprus overlap
      name == "Turkey" ~ 33,  # Shift Turkey east
      name == "Cyprus" ~ 33.5,  # Keep Cyprus, will adjust lat

      # Europe - Slovenia/Italy overlap
      name == "Slovenia" ~ 15,  # Shift east
      name == "Italy" ~ 12,  # Keep Italy west

      # Europe - Croatia/Bulgaria overlap
      name == "Croatia" ~ 16,  # Keep Croatia west
      name == "Bulgaria" ~ 25.5,  # Keep Bulgaria east

      # Europe - Denmark/Norway/Sweden overlaps
      name == "Denmark" ~ 10,  # Shift east
      name == "Sweden" ~ 16,  # Shift east

      TRUE ~ lon
    ),
    lat = case_when(
      # Countries with overseas territories
      name == "France" ~ 46.5,
      name == "United States of America" ~ 39,
      name == "Norway" ~ 64,  # Shift north
      name == "Netherlands" ~ 52.5,

      # South America
      name == "Chile" ~ -35,
      name == "Argentina" ~ -35,

      # Southeast Asia
      name == "Singapore" ~ 0,  # Shift south
      name == "Malaysia" ~ 4,

      # Middle East
      name == "Jordan" ~ 31,
      name == "Saudi Arabia" ~ 24,  # Shift south

      # Europe - Ireland/UK
      name == "Ireland" ~ 53.5,
      name == "United Kingdom" ~ 54,

      # Europe - various
      name == "Switzerland" ~ 46.8,
      name == "Portugal" ~ 39.5,
      name == "Czechia" ~ 49.8,
      name == "Poland" ~ 52,
      name == "Austria" ~ 47.5,

      # South America
      name == "Ecuador" ~ -1.5,
      name == "Colombia" ~ 4,

      # Southeast Asia
      name == "Hong Kong" ~ 22,
      name == "Thailand" ~ 15,

      # Middle East
      name == "Israel" ~ 31.5,
      name == "Egypt" ~ 27,

      # Europe - Turkey/Cyprus
      name == "Turkey" ~ 39,
      name == "Cyprus" ~ 34,  # Shift south

      # Europe - Slovenia/Italy/Croatia/Bulgaria
      name == "Slovenia" ~ 46,
      name == "Italy" ~ 43,
      name == "Croatia" ~ 45,
      name == "Bulgaria" ~ 43,

      # Scandinavia
      name == "Denmark" ~ 56,
      name == "Sweden" ~ 62,

      TRUE ~ lat
    )
  )

# Create short label names and determine if label should be direct or repelled
world_data <- world_data %>%
  mutate(
    short_name = ifelse(name %in% names(country_short_names),
                        country_short_names[name],
                        name),
    label = ifelse(papers > 0, paste0(short_name, "\n", papers), NA),
    is_large = name %in% large_countries
  )

# Check matches
matched <- sum(world_data$papers > 0)
cat("Countries matched:", matched, "\n")

# ============================================
# 1. WORLD MAP - Papers by Country
# ============================================
cat("\nGenerating world map...\n")

# Split labels: large countries get direct labels, small get repelled
# Include ALL countries with papers (papers > 0)
world_labels_direct <- world_data %>%
  filter(papers > 0 & is_large) %>%
  st_drop_geometry()

world_labels_repel <- world_data %>%
  filter(papers > 0 & !is_large) %>%
  st_drop_geometry()

p_world <- ggplot(data = world_data) +
  geom_sf(aes(fill = ifelse(has_papers, papers, NA)), color = "white", size = 0.1) +
  geom_sf(data = world_data %>% filter(!has_papers), fill = "grey85", color = "white", size = 0.1) +
  scale_fill_viridis_c(
    name = "Papers",
    trans = "log1p",
    breaks = c(1, 10, 50, 100, 500, 1000, 2000),
    labels = c("1", "10", "50", "100", "500", "1000", "2000"),
    option = "plasma",
    na.value = "grey85"
  ) +
  # Direct labels for large countries using shadowtext
  geom_shadowtext(
    data = world_labels_direct,
    aes(x = lon, y = lat, label = label),
    size = 2.5,
    fontface = "bold",
    color = "black",
    bg.color = "white",
    bg.r = 0.15,
    lineheight = 0.8
  ) +
  # Repelled labels for small/crowded countries
  geom_text_repel(
    data = world_labels_repel,
    aes(x = lon, y = lat, label = label),
    size = 2.3,
    fontface = "bold",
    color = "black",
    bg.color = "white",
    bg.r = 0.15,
    box.padding = 0.3,
    point.padding = 0.1,
    segment.color = "grey40",
    segment.size = 0.3,
    min.segment.length = 0,
    max.overlaps = 100,
    force = 2,
    lineheight = 0.8
  ) +
  labs(
    title = "Shark Research Papers by Author Country (1950-2025)",
    subtitle = paste0("Total: ", format(sum(papers_df$papers), big.mark=","), " papers from ", nrow(papers_df), " countries | Grey = no papers"),
    caption = "Source: shark-references.com database (n = 6,183 papers with author country data)"
  ) +
  theme_minimal() +
  theme(
    plot.title = element_text(size = 16, face = "bold"),
    plot.subtitle = element_text(size = 12),
    legend.position = "bottom",
    legend.key.width = unit(2, "cm")
  )

ggsave("outputs/figures/world_map_papers_by_country.png", p_world, width = 16, height = 10, dpi = 150)
cat("Saved: outputs/figures/world_map_papers_by_country.png\n")

# ============================================
# 2. EUROPE MAP - Papers by Country
# ============================================
cat("\nGenerating Europe map...\n")

europe_bbox <- c(xmin = -12, xmax = 40, ymin = 35, ymax = 72)

# European countries where labels fit inside
europe_large <- c("France", "Spain", "Germany", "Italy", "United Kingdom",
                  "Sweden", "Norway", "Finland", "Poland", "Turkey", "Romania",
                  "Ukraine", "Ireland", "Portugal", "Greece", "Bulgaria")

# Filter European countries for labels - ALL with papers
europe_labels_direct <- world_data %>%
  filter(lon >= europe_bbox["xmin"] & lon <= europe_bbox["xmax"] &
         lat >= europe_bbox["ymin"] & lat <= europe_bbox["ymax"] &
         papers > 0 & name %in% europe_large) %>%
  st_drop_geometry()

europe_labels_repel <- world_data %>%
  filter(lon >= europe_bbox["xmin"] & lon <= europe_bbox["xmax"] &
         lat >= europe_bbox["ymin"] & lat <= europe_bbox["ymax"] &
         papers > 0 & !(name %in% europe_large)) %>%
  st_drop_geometry()

p_europe <- ggplot(data = world_data) +
  geom_sf(aes(fill = ifelse(has_papers, papers, NA)), color = "white", size = 0.2) +
  geom_sf(data = world_data %>% filter(!has_papers), fill = "grey85", color = "white", size = 0.2) +
  coord_sf(xlim = c(europe_bbox["xmin"], europe_bbox["xmax"]),
           ylim = c(europe_bbox["ymin"], europe_bbox["ymax"]),
           expand = FALSE) +
  scale_fill_viridis_c(
    name = "Papers",
    trans = "log1p",
    breaks = c(1, 10, 50, 100, 200, 500, 700),
    labels = c("1", "10", "50", "100", "200", "500", "700"),
    option = "plasma",
    na.value = "grey85"
  ) +
  # Direct labels for large European countries using shadowtext
  geom_shadowtext(
    data = europe_labels_direct,
    aes(x = lon, y = lat, label = label),
    size = 3.0,
    fontface = "bold",
    color = "black",
    bg.color = "white",
    bg.r = 0.15,
    lineheight = 0.8
  ) +
  # Repelled labels for small European countries
  geom_text_repel(
    data = europe_labels_repel,
    aes(x = lon, y = lat, label = label),
    size = 2.8,
    fontface = "bold",
    color = "black",
    bg.color = "white",
    bg.r = 0.15,
    box.padding = 0.3,
    point.padding = 0.1,
    segment.color = "grey40",
    segment.size = 0.3,
    min.segment.length = 0,
    max.overlaps = 100,
    force = 3,
    lineheight = 0.8
  ) +
  labs(
    title = "Shark Research Papers by Author Country - Europe",
    subtitle = "European institutions leading shark research | Grey = no papers",
    caption = "Source: shark-references.com database"
  ) +
  theme_minimal() +
  theme(
    plot.title = element_text(size = 14, face = "bold"),
    plot.subtitle = element_text(size = 11),
    legend.position = "right"
  )

ggsave("outputs/figures/europe_map_papers_by_country.png", p_europe, width = 14, height = 10, dpi = 150)
cat("Saved: outputs/figures/europe_map_papers_by_country.png\n")

# ============================================
# 3. REGIONAL MAP - Global North/South
# ============================================
cat("\nGenerating regional map...\n")

# Add region classification
papers_df$region <- case_when(
  papers_df$country %in% c("USA", "Canada", "UK", "Germany", "France", "Italy", "Spain",
                           "Netherlands", "Belgium", "Sweden", "Norway", "Denmark", "Finland",
                           "Austria", "Switzerland", "Ireland", "Australia", "New Zealand",
                           "Japan", "South Korea", "Israel", "Portugal", "Greece", "Poland",
                           "Czech Republic", "Hungary", "Iceland", "Luxembourg", "Slovenia",
                           "Estonia", "Latvia", "Lithuania", "Slovakia", "Croatia", "Cyprus",
                           "Malta", "Monaco", "Singapore") ~ "Global North",
  TRUE ~ "Global South"
)

region_summary <- papers_df %>%
  group_by(region) %>%
  summarise(
    papers = sum(papers),
    countries = n()
  ) %>%
  mutate(pct = round(papers / sum(papers) * 100, 1))

cat("\nRegion summary:\n")
print(region_summary)

# Create bins for better visualization - separate 0 from others
world_data$papers_bin <- cut(world_data$papers,
                              breaks = c(-Inf, 0, 10, 50, 100, 250, 500, 1000, Inf),
                              labels = c("0", "1-10", "11-50", "51-100", "101-250", "251-500", "501-1000", ">1000"))

# Custom color palette with grey for 0
bin_colors <- c("0" = "grey85", "1-10" = "#FFFFB2", "11-50" = "#FECC5C", "51-100" = "#FD8D3C",
                "101-250" = "#F03B20", "251-500" = "#BD0026", "501-1000" = "#800026", ">1000" = "#4A0014")

# Labels for regional map - ALL countries with papers
regional_labels_direct <- world_data %>%
  filter(papers > 0 & is_large) %>%
  st_drop_geometry()

regional_labels_repel <- world_data %>%
  filter(papers > 0 & !is_large) %>%
  st_drop_geometry()

p_regional <- ggplot(data = world_data) +
  geom_sf(aes(fill = papers_bin), color = "white", size = 0.1) +
  scale_fill_manual(
    name = "Papers",
    values = bin_colors,
    na.value = "grey85"
  ) +
  # Direct labels for large countries using shadowtext
  geom_shadowtext(
    data = regional_labels_direct,
    aes(x = lon, y = lat, label = label),
    size = 2.5,
    fontface = "bold",
    color = "black",
    bg.color = "white",
    bg.r = 0.15,
    lineheight = 0.8
  ) +
  # Repelled labels for small countries
  geom_text_repel(
    data = regional_labels_repel,
    aes(x = lon, y = lat, label = label),
    size = 2.3,
    fontface = "bold",
    color = "black",
    bg.color = "white",
    bg.r = 0.15,
    box.padding = 0.3,
    point.padding = 0.1,
    segment.color = "grey40",
    segment.size = 0.3,
    min.segment.length = 0,
    max.overlaps = 100,
    force = 2,
    lineheight = 0.8
  ) +
  labs(
    title = "Global Distribution of Shark Research Papers",
    subtitle = paste0("Global North: ", region_summary$papers[region_summary$region == "Global North"],
                     " papers (", region_summary$pct[region_summary$region == "Global North"], "%) | ",
                     "Global South: ", region_summary$papers[region_summary$region == "Global South"],
                     " papers (", region_summary$pct[region_summary$region == "Global South"], "%) | Grey = no papers"),
    caption = "Source: shark-references.com database (n = 6,183 papers)"
  ) +
  theme_minimal() +
  theme(
    plot.title = element_text(size = 16, face = "bold"),
    plot.subtitle = element_text(size = 12),
    legend.position = "bottom"
  )

ggsave("outputs/figures/regional_map_papers_by_country.png", p_regional, width = 16, height = 10, dpi = 150)
cat("Saved: outputs/figures/regional_map_papers_by_country.png\n")

cat("\nAll maps generated successfully!\n")
