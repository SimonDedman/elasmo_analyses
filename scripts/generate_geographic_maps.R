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

# Create short label names
world_data <- world_data %>%
  mutate(
    short_name = ifelse(name %in% names(country_short_names),
                        country_short_names[name],
                        name),
    label = ifelse(papers > 0, paste0(short_name, "\n", papers), NA)
  )

# Check matches
matched <- sum(world_data$papers > 0)
cat("Countries matched:", matched, "\n")

# ============================================
# 1. WORLD MAP - Papers by Country
# ============================================
cat("\nGenerating world map...\n")

# Filter for labels (only countries with papers, top countries for readability)
world_labels <- world_data %>%
  filter(papers >= 30) %>%  # Only label countries with 30+ papers for world map
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
  geom_text_repel(
    data = world_labels,
    aes(x = lon, y = lat, label = label),
    size = 2.5,
    fontface = "bold",
    box.padding = 0.3,
    point.padding = 0.2,
    segment.color = "grey50",
    segment.size = 0.3,
    min.segment.length = 0.2,
    max.overlaps = 30,
    force = 2
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

# Filter European countries for labels
europe_labels <- world_data %>%
  filter(lon >= europe_bbox["xmin"] & lon <= europe_bbox["xmax"] &
         lat >= europe_bbox["ymin"] & lat <= europe_bbox["ymax"] &
         papers > 0) %>%
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
  geom_text_repel(
    data = europe_labels,
    aes(x = lon, y = lat, label = label),
    size = 3,
    fontface = "bold",
    box.padding = 0.4,
    point.padding = 0.3,
    segment.color = "grey50",
    segment.size = 0.3,
    min.segment.length = 0.1,
    max.overlaps = 50,
    force = 3
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

# Labels for regional map (show more countries)
regional_labels <- world_data %>%
  filter(papers >= 20) %>%
  st_drop_geometry()

p_regional <- ggplot(data = world_data) +
  geom_sf(aes(fill = papers_bin), color = "white", size = 0.1) +
  scale_fill_manual(
    name = "Papers",
    values = bin_colors,
    na.value = "grey85"
  ) +
  geom_text_repel(
    data = regional_labels,
    aes(x = lon, y = lat, label = label),
    size = 2.5,
    fontface = "bold",
    box.padding = 0.3,
    point.padding = 0.2,
    segment.color = "grey50",
    segment.size = 0.3,
    min.segment.length = 0.2,
    max.overlaps = 35,
    force = 2
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
