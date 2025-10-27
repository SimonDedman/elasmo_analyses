#!/usr/bin/env Rscript
# ============================================================================
# COLLABORATION NETWORK VISUALIZATIONS
# ============================================================================
# Purpose: Create visualizations of collaboration networks
#
# Visualizations:
#   1) Country collaboration network graph
#   2) Top country partnerships bar chart
#   3) International collaboration metrics
#
# Author: EEA 2025 Data Panel
# Date: 2025-10-26
# ============================================================================

library(tidyverse)
library(igraph)
library(ggraph)
library(scales)

cat("\n")
cat(paste0(strrep("=", 80), "\n"))
cat("COLLABORATION NETWORK VISUALIZATIONS\n")
cat(paste0(strrep("=", 80), "\n\n"))

# ============================================================================
# LOAD DATA
# ============================================================================

cat("=== LOADING DATA ===\n")

country_network <- read_csv(
  "outputs/analysis/country_collaboration_network.csv",
  show_col_types = FALSE
)

country_metrics <- read_csv(
  "outputs/analysis/country_collaboration_metrics.csv",
  show_col_types = FALSE
)

papers_per_country <- read_csv(
  "outputs/analysis/papers_per_country.csv",
  show_col_types = FALSE
)

cat(sprintf("Loaded %s country partnerships\n", comma(nrow(country_network))))
cat(sprintf("Loaded %s countries with metrics\n", nrow(country_metrics)))

# ============================================================================
# VISUALIZATION 1: TOP COUNTRY PARTNERSHIPS
# ============================================================================

cat("\n=== CREATING TOP PARTNERSHIPS BAR CHART ===\n")

# Sum bidirectional edges (USA-Australia and Australia-USA)
top_partnerships <- country_network %>%
  mutate(
    pair = paste(pmin(country1, country2), pmax(country1, country2), sep = "-")
  ) %>%
  group_by(pair) %>%
  summarize(
    total_papers = sum(n_papers),
    .groups = "drop"
  ) %>%
  separate(pair, into = c("country_a", "country_b"), sep = "-") %>%
  arrange(desc(total_papers)) %>%
  head(20) %>%
  mutate(
    partnership = paste(country_a, "-", country_b),
    partnership = fct_reorder(partnership, total_papers)
  )

p1 <- ggplot(top_partnerships, aes(x = partnership, y = total_papers)) +
  geom_col(fill = "#377EB8", alpha = 0.8) +
  geom_text(
    aes(label = comma(total_papers)),
    hjust = -0.2,
    size = 3
  ) +
  coord_flip() +
  scale_y_continuous(
    expand = expansion(mult = c(0, 0.15)),
    labels = comma
  ) +
  labs(
    title = "Top 20 International Research Partnerships",
    subtitle = "Number of collaborative shark research papers",
    x = NULL,
    y = "Number of Papers",
    caption = "EEA 2025 Data Panel"
  ) +
  theme_minimal(base_size = 12) +
  theme(
    plot.title = element_text(size = 16, face = "bold"),
    plot.subtitle = element_text(size = 11, color = "grey40"),
    plot.caption = element_text(size = 9, color = "grey50"),
    panel.grid.major.y = element_blank(),
    panel.grid.minor = element_blank()
  )

ggsave(
  "outputs/figures/top_country_partnerships.png",
  plot = p1,
  width = 10,
  height = 8,
  dpi = 300,
  bg = "white"
)

ggsave(
  "outputs/figures/top_country_partnerships.pdf",
  plot = p1,
  width = 10,
  height = 8,
  bg = "white"
)

cat("✓ Saved: top_country_partnerships.png + .pdf\n")

# ============================================================================
# VISUALIZATION 2: COLLABORATION METRICS BY COUNTRY
# ============================================================================

cat("\n=== CREATING COLLABORATION METRICS CHART ===\n")

# Join with total papers
country_collab_stats <- country_metrics %>%
  head(20) %>%
  left_join(papers_per_country, by = "country") %>%
  mutate(
    collab_rate = weighted_degree / paper_count * 100,
    country = fct_reorder(country, weighted_degree)
  )

p2 <- ggplot(country_collab_stats, aes(x = country, y = weighted_degree)) +
  geom_col(aes(fill = collab_rate), alpha = 0.9) +
  geom_text(
    aes(label = comma(weighted_degree)),
    hjust = -0.2,
    size = 3
  ) +
  coord_flip() +
  scale_y_continuous(
    expand = expansion(mult = c(0, 0.15)),
    labels = comma
  ) +
  scale_fill_viridis_c(
    option = "plasma",
    name = "Collaboration\nRate (%)",
    labels = function(x) sprintf("%.1f", x)
  ) +
  labs(
    title = "International Collaboration by Country",
    subtitle = "Total collaborative papers (color = collaboration rate)",
    x = NULL,
    y = "Number of International Collaborative Papers",
    caption = "EEA 2025 Data Panel | Collaboration rate = international papers / total papers"
  ) +
  theme_minimal(base_size = 12) +
  theme(
    plot.title = element_text(size = 16, face = "bold"),
    plot.subtitle = element_text(size = 11, color = "grey40"),
    plot.caption = element_text(size = 9, color = "grey50"),
    panel.grid.major.y = element_blank(),
    panel.grid.minor = element_blank(),
    legend.position = "right"
  )

ggsave(
  "outputs/figures/country_collaboration_metrics.png",
  plot = p2,
  width = 12,
  height = 8,
  dpi = 300,
  bg = "white"
)

ggsave(
  "outputs/figures/country_collaboration_metrics.pdf",
  plot = p2,
  width = 12,
  height = 8,
  bg = "white"
)

cat("✓ Saved: country_collaboration_metrics.png + .pdf\n")

# ============================================================================
# VISUALIZATION 3: COUNTRY COLLABORATION NETWORK GRAPH
# ============================================================================

cat("\n=== CREATING NETWORK GRAPH ===\n")

# Filter to top collaborations for readability
top_edges <- country_network %>%
  mutate(
    pair = paste(pmin(country1, country2), pmax(country1, country2), sep = "-")
  ) %>%
  group_by(pair) %>%
  summarize(
    country1 = first(country1),
    country2 = first(country2),
    total_papers = sum(n_papers),
    .groups = "drop"
  ) %>%
  arrange(desc(total_papers)) %>%
  head(50)  # Top 50 partnerships for clarity

# Build graph
g <- graph_from_data_frame(
  top_edges %>% select(country1, country2, total_papers),
  directed = FALSE
)

# Add node attributes
V(g)$size <- country_metrics$weighted_degree[match(V(g)$name, country_metrics$country)]
V(g)$size[is.na(V(g)$size)] <- 1

# Create network plot
set.seed(42)  # Reproducible layout
p3 <- ggraph(g, layout = "fr") +
  geom_edge_link(
    aes(width = total_papers, alpha = total_papers),
    color = "grey60"
  ) +
  geom_node_point(
    aes(size = size),
    color = "#377EB8",
    alpha = 0.7
  ) +
  geom_node_text(
    aes(label = name),
    size = 3,
    repel = TRUE,
    fontface = "bold"
  ) +
  scale_edge_width_continuous(
    range = c(0.3, 3),
    name = "Papers"
  ) +
  scale_edge_alpha_continuous(
    range = c(0.3, 0.9),
    guide = "none"
  ) +
  scale_size_continuous(
    range = c(3, 15),
    name = "Total Collab.\nPapers"
  ) +
  labs(
    title = "International Collaboration Network",
    subtitle = "Top 50 country partnerships in shark research",
    caption = "EEA 2025 Data Panel | Node size = total international papers, Edge width = partnership strength"
  ) +
  theme_graph(base_size = 12) +
  theme(
    plot.title = element_text(size = 16, face = "bold", hjust = 0.5),
    plot.subtitle = element_text(size = 11, color = "grey40", hjust = 0.5),
    plot.caption = element_text(size = 9, color = "grey50"),
    plot.background = element_rect(fill = "white", color = NA),
    legend.position = "right"
  )

ggsave(
  "outputs/figures/country_collaboration_network.png",
  plot = p3,
  width = 14,
  height = 10,
  dpi = 300,
  bg = "white"
)

# Skip PDF for network graph due to font rendering issues
cat("✓ Saved: country_collaboration_network.png\n")

# ============================================================================
# SUMMARY
# ============================================================================

cat("\n")
cat(paste0(strrep("=", 80), "\n"))
cat("COLLABORATION NETWORK VISUALIZATIONS COMPLETE\n")
cat(paste0(strrep("=", 80), "\n\n"))

cat("VISUALIZATIONS CREATED:\n")
cat("  1. top_country_partnerships.png + .pdf\n")
cat("  2. country_collaboration_metrics.png + .pdf\n")
cat("  3. country_collaboration_network.png + .pdf\n")

cat("\n")
cat(paste0(strrep("=", 80), "\n"))
