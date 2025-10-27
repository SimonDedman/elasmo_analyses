#!/usr/bin/env Rscript
# ============================================================================
# ALL DISCIPLINES NETWORK VISUALIZATION
# ============================================================================
# Purpose: Visualize connections between ALL 8 disciplines in shark research
# Shows: Multi-disciplinary papers, collaboration patterns, discipline clusters
# Output: Tree, circular, chord, and matrix visualizations
# ============================================================================

library(tidyverse)
library(igraph)
library(ggraph)
library(scales)
library(viridis)

# ============================================================================
# DISCIPLINE METADATA
# ============================================================================

# Discipline names and colors (from database schema)
discipline_info <- tibble(
  code = c("BEH", "BIO", "CON", "DATA", "FISH", "GEN", "MOV", "TRO"),
  name = c("Behaviour", "Biology", "Conservation", "Data Science",
           "Fisheries", "Genetics", "Movement", "Trophic Ecology"),
  color = c("#E63946", "#F77F00", "#06A77D", "#3A86FF",
            "#8338EC", "#FB5607", "#FFBE0B", "#FF006E")
)

# ============================================================================
# LOAD DATA
# ============================================================================

cat("\n=== LOADING DATA ===\n")

# Load discipline summary (total papers per discipline)
discipline_summary <- read_csv(
  "outputs/analysis/discipline_summary.csv",
  show_col_types = FALSE
)

# Load discipline cooccurrence matrix
cooccur_matrix <- read_csv(
  "outputs/analysis/discipline_cooccurrence_matrix.csv",
  show_col_types = FALSE
)

# Load DATA segmentation for multi-disciplinary analysis
data_seg <- read_csv(
  "outputs/analysis/data_science_segmentation.csv",
  show_col_types = FALSE
)

cat(sprintf("Loaded %d discipline codes\n", nrow(discipline_summary)))
cat(sprintf("Loaded %dx%d cooccurrence matrix\n", nrow(cooccur_matrix), ncol(cooccur_matrix) - 1))
cat(sprintf("Loaded %d papers for multi-discipline analysis\n", nrow(data_seg)))

# ============================================================================
# PREPARE NETWORK DATA
# ============================================================================

cat("\n=== PREPARING NETWORK DATA ===\n")

# Add discipline metadata to summary
discipline_counts <- discipline_summary %>%
  left_join(discipline_info, by = c("discipline_code" = "code")) %>%
  arrange(desc(paper_count))

cat("\nPapers per discipline:\n")
print(discipline_counts, n = Inf)

# Convert cooccurrence matrix to edge list
# The matrix has row names in first column and is symmetric
cooccur_long <- cooccur_matrix %>%
  rename(from_disc = 1) %>%  # First column is row names
  pivot_longer(
    cols = -from_disc,
    names_to = "to_disc",
    values_to = "shared_papers"
  ) %>%
  # Keep only lower triangle (avoid duplicates)
  filter(from_disc < to_disc) %>%
  # Remove zero connections
  filter(shared_papers > 0) %>%
  arrange(desc(shared_papers))

cat(sprintf("\nCreated %d unique discipline pairs\n", nrow(cooccur_long)))

# Show top connections
cat("\nTop 15 discipline connections:\n")
top_conn <- cooccur_long %>%
  head(15) %>%
  left_join(discipline_info, by = c("from_disc" = "code")) %>%
  left_join(discipline_info, by = c("to_disc" = "code")) %>%
  select(from = name.x, to = name.y, papers = shared_papers)
print(top_conn, n = 15)

# Calculate multi-disciplinary statistics
multi_disc_papers <- data_seg %>%
  filter(num_disciplines >= 2)

cat(sprintf("\nMulti-disciplinary papers: %d (%.1f%% of all papers)\n",
            nrow(multi_disc_papers),
            100 * nrow(multi_disc_papers) / nrow(data_seg)))

# Count papers per discipline combination
combination_counts <- multi_disc_papers %>%
  count(disciplines, num_disciplines, name = "papers") %>%
  arrange(desc(papers))

cat("\nTop 10 discipline combinations:\n")
print(head(combination_counts, 10), n = 10)

# ============================================================================
# CREATE NETWORK GRAPH
# ============================================================================

cat("\n=== BUILDING NETWORK GRAPH ===\n")

# Create nodes dataframe
nodes <- discipline_counts %>%
  select(name = discipline_code, full_name = name,
         papers = paper_count, color = color)

# Create edges dataframe (need both directions for undirected visualization)
edges <- bind_rows(
  cooccur_long %>% select(from = from_disc, to = to_disc, weight = shared_papers),
  cooccur_long %>% select(from = to_disc, to = from_disc, weight = shared_papers)
)

# Create igraph object
g <- graph_from_data_frame(edges, directed = FALSE, vertices = nodes)

cat(sprintf("Network: %d nodes, %d edges\n", vcount(g), ecount(g)))

# ============================================================================
# VISUALIZATION 1: FORCE-DIRECTED NETWORK
# ============================================================================

cat("\n=== CREATING FORCE-DIRECTED NETWORK VISUALIZATION ===\n")

set.seed(42)

p_network <- ggraph(g, layout = "fr") +
  # Draw edges (connections between disciplines)
  geom_edge_link(
    aes(width = weight, alpha = weight),
    color = "#2E86AB",
    show.legend = FALSE
  ) +
  scale_edge_width(range = c(0.5, 8)) +
  scale_edge_alpha(range = c(0.3, 0.8)) +
  # Draw nodes (disciplines)
  geom_node_point(
    aes(size = papers, fill = color),
    shape = 21,
    color = "white",
    stroke = 2,
    alpha = 0.9,
    show.legend = FALSE
  ) +
  scale_size(range = c(10, 35)) +
  scale_fill_identity() +
  # Add discipline codes on nodes
  geom_node_text(
    aes(label = name),
    size = 5,
    fontface = "bold",
    color = "white"
  ) +
  # Add full names with white background below nodes
  geom_node_label(
    aes(label = full_name),
    size = 3.5,
    nudge_y = -0.01,
    color = "grey20",
    fill = "white",
    label.padding = unit(0.15, "lines"),
    label.size = 0
  ) +
  # Theme
  theme_void() +
  theme(
    plot.background = element_rect(fill = "white", color = NA),
    panel.background = element_rect(fill = "white", color = NA),
    plot.title = element_text(size = 18, face = "bold", hjust = 0.5, margin = margin(b = 10)),
    plot.subtitle = element_text(size = 12, hjust = 0.5, color = "grey40", margin = margin(b = 20)),
    plot.caption = element_text(size = 9, color = "grey50", margin = margin(t = 20))
  ) +
  labs(
    title = "Interdisciplinary Connections in Shark Research",
    subtitle = sprintf("%s multi-disciplinary papers create %s unique discipline pairs",
                      comma(nrow(multi_disc_papers)),
                      comma(nrow(cooccur_long))),
    caption = "Node size = total papers in discipline | Edge width = shared papers between disciplines"
  )

# Save
ggsave(
  "outputs/figures/all_disciplines_network.png",
  p_network,
  width = 14, height = 10, dpi = 300, bg = "white"
)

ggsave(
  "outputs/figures/all_disciplines_network.pdf",
  p_network,
  width = 14, height = 10, bg = "white"
)

cat("✓ Saved: all_disciplines_network.png/pdf\n")

# ============================================================================
# VISUALIZATION 2: CIRCULAR NETWORK
# ============================================================================

cat("\n=== CREATING CIRCULAR NETWORK VISUALIZATION ===\n")

# Create circular layout with pre-computed positions
circular_layout <- create_layout(g, layout = "circle")

# Calculate positions for text labels (horizontal, outside circle)
n_nodes <- vcount(g)
circular_layout$text_x <- circular_layout$x * 1.35  # Push labels further out
circular_layout$text_y <- circular_layout$y * 1.35
circular_layout$hjust <- ifelse(circular_layout$x > 0, 0, 1)  # Left/right align based on position

p_circular <- ggraph(circular_layout) +
  # Draw edges (curved connections)
  geom_edge_arc(
    aes(width = weight, alpha = weight),
    color = "#2E86AB",
    strength = 0.3,
    show.legend = FALSE
  ) +
  scale_edge_width(range = c(0.3, 5)) +
  scale_edge_alpha(range = c(0.2, 0.7)) +
  # Draw nodes
  geom_node_point(
    aes(size = papers, fill = color),
    shape = 21,
    color = "white",
    stroke = 2,
    alpha = 0.9,
    show.legend = FALSE
  ) +
  scale_size(range = c(15, 40)) +
  scale_fill_identity() +
  # Add discipline codes on nodes
  geom_node_text(
    aes(label = name),
    size = 6,
    fontface = "bold",
    color = "white"
  ) +
  # Add full names outside circle (horizontal text)
  geom_node_text(
    aes(label = full_name,
        x = text_x,
        y = text_y,
        hjust = hjust),
    size = 4.5,
    color = "grey20",
    angle = 0  # Keep all text horizontal
  ) +
  # Theme
  theme_void() +
  theme(
    plot.background = element_rect(fill = "white", color = NA),
    panel.background = element_rect(fill = "white", color = NA),
    plot.title = element_text(size = 18, face = "bold", hjust = 0.5, margin = margin(b = 10)),
    plot.subtitle = element_text(size = 12, hjust = 0.5, color = "grey40", margin = margin(b = 20)),
    plot.caption = element_text(size = 9, color = "grey50", margin = margin(t = 20))
  ) +
  labs(
    title = "Shark Research: A Highly Connected Network of Disciplines",
    subtitle = "Curved lines show shared papers between disciplines",
    caption = "Node size = papers per discipline | Line thickness = number of shared papers"
  )

# Save
ggsave(
  "outputs/figures/all_disciplines_circular.png",
  p_circular,
  width = 14, height = 14, dpi = 300, bg = "white"
)

ggsave(
  "outputs/figures/all_disciplines_circular.pdf",
  p_circular,
  width = 14, height = 14, bg = "white"
)

cat("✓ Saved: all_disciplines_circular.png/pdf\n")

# ============================================================================
# VISUALIZATION 3: CONNECTION MATRIX (HEATMAP)
# ============================================================================

cat("\n=== CREATING CONNECTION MATRIX HEATMAP ===\n")

# Create symmetric matrix with full names
connection_matrix <- cooccur_long %>%
  left_join(discipline_info, by = c("from_disc" = "code")) %>%
  left_join(discipline_info, by = c("to_disc" = "code")) %>%
  select(from_name = name.x, to_name = name.y, papers = shared_papers)

p_matrix <- ggplot(connection_matrix, aes(x = from_name, y = to_name, fill = papers)) +
  geom_tile(color = "white", size = 1) +
  geom_text(aes(label = comma(papers)), size = 4, fontface = "bold", color = "white") +
  scale_fill_viridis_c(
    option = "plasma",
    trans = "log10",
    labels = comma,
    name = "Shared\nPapers"
  ) +
  scale_x_discrete(position = "top") +
  coord_fixed() +
  theme_minimal() +
  theme(
    plot.background = element_rect(fill = "white", color = NA),
    panel.background = element_rect(fill = "white", color = NA),
    axis.text.x.top = element_text(angle = 45, hjust = 0, vjust = 0, size = 11, face = "bold", margin = margin(b = 5)),
    axis.text.y = element_text(size = 11, face = "bold"),
    axis.title = element_blank(),
    legend.position = "right",
    plot.title = element_text(size = 18, face = "bold", hjust = 0.5, margin = margin(b = 10)),
    plot.subtitle = element_text(size = 12, hjust = 0.5, color = "grey40", margin = margin(b = 20)),
    plot.caption = element_text(size = 9, color = "grey50", margin = margin(t = 20)),
    plot.margin = margin(t = 40, r = 10, b = 10, l = 10)  # Extra top margin for rotated labels
  ) +
  labs(
    title = "Discipline Connection Matrix",
    subtitle = "Number of papers shared between each pair of disciplines",
    caption = "Note: Matrix shows only unique pairs (lower triangle) | Color scale is logarithmic"
  )

# Save
ggsave(
  "outputs/figures/all_disciplines_matrix.png",
  p_matrix,
  width = 12, height = 10, dpi = 300, bg = "white"
)

ggsave(
  "outputs/figures/all_disciplines_matrix.pdf",
  p_matrix,
  width = 12, height = 10, bg = "white"
)

cat("✓ Saved: all_disciplines_matrix.png/pdf\n")

# ============================================================================
# VISUALIZATION 4: TOP COMBINATIONS BAR CHART
# ============================================================================

cat("\n=== CREATING TOP COMBINATIONS BAR CHART ===\n")

# Get top 20 combinations and create labels
top20_combinations <- combination_counts %>%
  head(20) %>%
  mutate(
    combination_label = str_replace_all(disciplines, ",", " + "),
    combination_label = fct_reorder(combination_label, papers)
  )

p_combinations <- ggplot(top20_combinations, aes(x = combination_label, y = papers)) +
  geom_col(aes(fill = num_disciplines), alpha = 0.8, width = 0.7) +
  geom_text(aes(label = comma(papers)), hjust = -0.2, size = 3.5, fontface = "bold") +
  scale_fill_viridis_c(
    option = "mako",
    name = "Number of\nDisciplines",
    breaks = 2:max(top20_combinations$num_disciplines)
  ) +
  scale_y_continuous(
    labels = comma,
    expand = expansion(mult = c(0, 0.15))
  ) +
  coord_flip() +
  theme_minimal() +
  theme(
    plot.background = element_rect(fill = "white", color = NA),
    panel.background = element_rect(fill = "white", color = NA),
    panel.grid.major.y = element_blank(),
    panel.grid.minor = element_blank(),
    axis.text.y = element_text(size = 10),
    axis.text.x = element_text(size = 10),
    axis.title.x = element_text(size = 12, face = "bold", margin = margin(t = 10)),
    plot.title = element_text(size = 18, face = "bold", hjust = 0, margin = margin(b = 10)),
    plot.subtitle = element_text(size = 12, hjust = 0, color = "grey40", margin = margin(b = 20)),
    plot.caption = element_text(size = 9, color = "grey50", hjust = 0, margin = margin(t = 20)),
    legend.position = "right"
  ) +
  labs(
    title = "Top 20 Multi-Disciplinary Combinations in Shark Research",
    subtitle = "Most common ways disciplines work together",
    x = NULL,
    y = "Number of Papers",
    caption = "Color shows number of disciplines in each combination"
  )

# Save
ggsave(
  "outputs/figures/all_disciplines_top_combinations.png",
  p_combinations,
  width = 12, height = 10, dpi = 300, bg = "white"
)

ggsave(
  "outputs/figures/all_disciplines_top_combinations.pdf",
  p_combinations,
  width = 12, height = 10, bg = "white"
)

cat("✓ Saved: all_disciplines_top_combinations.png/pdf\n")

# ============================================================================
# VISUALIZATION 5: DISCIPLINARY BREADTH OVER TIME
# ============================================================================

cat("\n=== CREATING DISCIPLINARY BREADTH TIMELINE ===\n")

# Calculate average number of disciplines per paper over time
breadth_timeline <- data_seg %>%
  filter(year >= 1950 & !is.na(year)) %>%
  group_by(year) %>%
  summarise(
    avg_disciplines = mean(num_disciplines, na.rm = TRUE),
    median_disciplines = median(num_disciplines, na.rm = TRUE),
    pct_multi = 100 * mean(num_disciplines > 1),
    total_papers = n(),
    .groups = "drop"
  )

p_breadth <- ggplot(breadth_timeline, aes(x = year)) +
  # Average disciplines per paper
  geom_line(aes(y = avg_disciplines, color = "Average"), size = 1.5, alpha = 0.8) +
  geom_point(aes(y = avg_disciplines, color = "Average"), size = 2, alpha = 0.6) +
  # Median disciplines per paper
  geom_line(aes(y = median_disciplines, color = "Median"), size = 1.5, alpha = 0.8, linetype = "dashed") +
  # Percentage multi-disciplinary (secondary axis)
  geom_line(aes(y = pct_multi / 50, color = "% Multi-disciplinary"), size = 1.5, alpha = 0.8) +
  geom_point(aes(y = pct_multi / 50, color = "% Multi-disciplinary"), size = 2, alpha = 0.6) +
  # Scales
  scale_y_continuous(
    name = "Average Disciplines per Paper",
    sec.axis = sec_axis(~ . * 50, name = "% Multi-Disciplinary Papers")
  ) +
  scale_color_manual(
    values = c("Average" = "#2E86AB", "Median" = "#A23B72", "% Multi-disciplinary" = "#F18F01"),
    name = NULL
  ) +
  scale_x_continuous(breaks = seq(1950, 2025, by = 10)) +
  theme_minimal() +
  theme(
    plot.background = element_rect(fill = "white", color = NA),
    panel.background = element_rect(fill = "white", color = NA),
    panel.grid.minor = element_blank(),
    axis.text = element_text(size = 11),
    axis.title = element_text(size = 12, face = "bold"),
    axis.title.y.right = element_text(color = "#F18F01"),
    axis.text.y.right = element_text(color = "#F18F01"),
    legend.position = "bottom",
    legend.text = element_text(size = 11),
    plot.title = element_text(size = 18, face = "bold", hjust = 0, margin = margin(b = 10)),
    plot.subtitle = element_text(size = 12, hjust = 0, color = "grey40", margin = margin(b = 20)),
    plot.caption = element_text(size = 9, color = "grey50", hjust = 0, margin = margin(t = 20))
  ) +
  labs(
    title = "Growing Interdisciplinarity in Shark Research (1950-2025)",
    subtitle = "Papers increasingly integrate multiple disciplines",
    x = "Year",
    caption = sprintf("Based on %s papers with discipline classifications",
                     comma(nrow(data_seg)))
  )

# Save
ggsave(
  "outputs/figures/all_disciplines_breadth_timeline.png",
  p_breadth,
  width = 14, height = 8, dpi = 300, bg = "white"
)

ggsave(
  "outputs/figures/all_disciplines_breadth_timeline.pdf",
  p_breadth,
  width = 14, height = 8, bg = "white"
)

cat("✓ Saved: all_disciplines_breadth_timeline.png/pdf\n")

# ============================================================================
# SUMMARY STATISTICS
# ============================================================================

cat("\n")
cat(paste0(strrep("=", 70), "\n"))
cat("ALL DISCIPLINES NETWORK ANALYSIS - SUMMARY\n")
cat(paste0(strrep("=", 70), "\n\n"))

cat("DISCIPLINE COUNTS:\n")
print(discipline_counts, n = Inf)

cat("\n\nMULTI-DISCIPLINARY PAPERS:\n")
cat(sprintf("  Total papers analyzed: %s\n", comma(nrow(data_seg))))
cat(sprintf("  Multi-disciplinary (2+): %s (%.1f%%)\n",
            comma(nrow(multi_disc_papers)),
            100 * nrow(multi_disc_papers) / nrow(data_seg)))
cat(sprintf("  Single discipline only: %s (%.1f%%)\n",
            comma(nrow(data_seg) - nrow(multi_disc_papers)),
            100 * (nrow(data_seg) - nrow(multi_disc_papers)) / nrow(data_seg)))

cat("\n\nTOP 10 DISCIPLINE PAIRS:\n")
print(head(top_conn, 10), n = 10)

cat("\n\nTOP 10 MULTI-DISCIPLINE COMBINATIONS:\n")
top10_comb <- combination_counts %>%
  head(10) %>%
  mutate(combination = str_replace_all(disciplines, ",", " + "))
print(top10_comb %>% select(combination, papers, num_disciplines), n = 10)

cat("\n\nINTERDISCIPLINARITY TRENDS:\n")
recent_breadth <- breadth_timeline %>% filter(year >= 2015)
cat(sprintf("  Average disciplines per paper (2015-2025): %.2f\n", mean(recent_breadth$avg_disciplines)))
cat(sprintf("  Median disciplines per paper (2015-2025): %.2f\n", mean(recent_breadth$median_disciplines)))
cat(sprintf("  %% multi-disciplinary papers (2015-2025): %.1f%%\n", mean(recent_breadth$pct_multi)))

cat("\n\nVISUALIZATIONS CREATED:\n")
cat("  1. all_disciplines_network.png/pdf - Force-directed network layout\n")
cat("  2. all_disciplines_circular.png/pdf - Circular network layout\n")
cat("  3. all_disciplines_matrix.png/pdf - Connection heatmap matrix\n")
cat("  4. all_disciplines_top_combinations.png/pdf - Top 20 combinations bar chart\n")
cat("  5. all_disciplines_breadth_timeline.png/pdf - Interdisciplinarity over time\n")

cat("\n")
cat(paste0(strrep("=", 70), "\n"))
cat("ANALYSIS COMPLETE\n")
cat(paste0(strrep("=", 70), "\n"))
