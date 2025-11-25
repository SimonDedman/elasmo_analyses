#!/usr/bin/env Rscript
# Generate geographic maps for shark research papers
# Uses paper_geography table (6,183 papers with author country data)

library(ggplot2)
library(sf)
library(rnaturalearth)
library(rnaturalearthdata)
library(RSQLite)
library(dplyr)

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

# Apply mapping
papers_df$country_mapped <- papers_df$country
for (old_name in names(country_mapping)) {
  papers_df$country_mapped[papers_df$country == old_name] <- country_mapping[old_name]
}

# Join with world map
world_data <- world %>%
  left_join(papers_df, by = c("name" = "country_mapped")) %>%
  mutate(papers = ifelse(is.na(papers), 0, papers))

# Check matches
matched <- sum(!is.na(world_data$papers) & world_data$papers > 0)
cat("Countries matched:", matched, "\n")

# ============================================
# 1. WORLD MAP - Papers by Country
# ============================================
cat("\nGenerating world map...\n")

p_world <- ggplot(data = world_data) +
  geom_sf(aes(fill = papers), color = "white", size = 0.1) +
  scale_fill_viridis_c(
    name = "Papers",
    trans = "log1p",
    breaks = c(0, 10, 50, 100, 500, 1000, 2000),
    labels = c("0", "10", "50", "100", "500", "1000", "2000"),
    option = "plasma",
    na.value = "grey90"
  ) +
  labs(
    title = "Shark Research Papers by Author Country (1950-2025)",
    subtitle = paste0("Total: ", format(sum(papers_df$papers), big.mark=","), " papers from ", nrow(papers_df), " countries"),
    caption = "Source: shark-references.com database (n = 6,183 papers with author country data)"
  ) +
  theme_minimal() +
  theme(
    plot.title = element_text(size = 16, face = "bold"),
    plot.subtitle = element_text(size = 12),
    legend.position = "bottom",
    legend.key.width = unit(2, "cm")
  )

ggsave("outputs/figures/world_map_papers_by_country.png", p_world, width = 14, height = 8, dpi = 150)
cat("Saved: outputs/figures/world_map_papers_by_country.png\n")

# ============================================
# 2. EUROPE MAP - Papers by Country
# ============================================
cat("\nGenerating Europe map...\n")

europe_bbox <- c(xmin = -25, xmax = 45, ymin = 35, ymax = 72)

p_europe <- ggplot(data = world_data) +
  geom_sf(aes(fill = papers), color = "white", size = 0.2) +
  coord_sf(xlim = c(europe_bbox["xmin"], europe_bbox["xmax"]),
           ylim = c(europe_bbox["ymin"], europe_bbox["ymax"]),
           expand = FALSE) +
  scale_fill_viridis_c(
    name = "Papers",
    trans = "log1p",
    breaks = c(0, 10, 50, 100, 200, 500, 700),
    labels = c("0", "10", "50", "100", "200", "500", "700"),
    option = "plasma",
    na.value = "grey90"
  ) +
  labs(
    title = "Shark Research Papers by Author Country - Europe",
    subtitle = "European institutions leading shark research",
    caption = "Source: shark-references.com database"
  ) +
  theme_minimal() +
  theme(
    plot.title = element_text(size = 14, face = "bold"),
    plot.subtitle = element_text(size = 11),
    legend.position = "right"
  )

ggsave("outputs/figures/europe_map_papers_by_country.png", p_europe, width = 12, height = 8, dpi = 150)
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

# Create bins for better visualization
world_data$papers_bin <- cut(world_data$papers,
                              breaks = c(-1, 0, 10, 50, 100, 250, 500, 1000, 2500),
                              labels = c("0", "1-10", "11-50", "51-100", "101-250", "251-500", "501-1000", ">1000"))

p_regional <- ggplot(data = world_data) +
  geom_sf(aes(fill = papers_bin), color = "white", size = 0.1) +
  scale_fill_brewer(
    name = "Papers",
    palette = "YlOrRd",
    na.value = "grey90"
  ) +
  labs(
    title = "Global Distribution of Shark Research Papers",
    subtitle = paste0("Global North: ", region_summary$papers[region_summary$region == "Global North"],
                     " papers (", region_summary$pct[region_summary$region == "Global North"], "%) | ",
                     "Global South: ", region_summary$papers[region_summary$region == "Global South"],
                     " papers (", region_summary$pct[region_summary$region == "Global South"], "%)"),
    caption = "Source: shark-references.com database (n = 6,183 papers)"
  ) +
  theme_minimal() +
  theme(
    plot.title = element_text(size = 16, face = "bold"),
    plot.subtitle = element_text(size = 12),
    legend.position = "bottom"
  )

ggsave("outputs/figures/regional_map_papers_by_country.png", p_regional, width = 14, height = 8, dpi = 150)
cat("Saved: outputs/figures/regional_map_papers_by_country.png\n")

cat("\nAll maps generated successfully!\n")
