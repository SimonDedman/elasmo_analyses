#!/usr/bin/env Rscript
# ============================================================================
# DATA Cross-Cutting Visualization
# ============================================================================
# Creates tree/network graphic showing how DATA techniques are used across
# all shark research disciplines
#
# Input: outputs/analysis/data_science_segmentation.csv
# Output: outputs/figures/data_crosscutting_tree.png (and .pdf)
#
# Author: EEA 2025 Data Panel
# Date: 2025-10-26
# ============================================================================

# Load required packages
library(tidyverse)
library(igraph)
library(ggraph)
library(scales)

# Set paths
input_file <- "outputs/analysis/data_science_segmentation.csv"
output_dir <- "outputs/figures"
dir.create(output_dir, showWarnings = FALSE, recursive = TRUE)

# ============================================================================
# 1. Load and Process Data
# ============================================================================

cat("Loading DATA segmentation data...\n")
data_seg <- read_csv(input_file, show_col_types = FALSE)

cat(sprintf("Total DATA papers: %d\n", nrow(data_seg)))
cat(sprintf("  DATA only: %d (%.1f%%)\n",
    sum(data_seg$category == "DATA_only"),
    sum(data_seg$category == "DATA_only") / nrow(data_seg) * 100))
cat(sprintf("  DATA primary + others: %d (%.1f%%)\n",
    sum(data_seg$category == "DATA_primary_with_others"),
    sum(data_seg$category == "DATA_primary_with_others") / nrow(data_seg) * 100))
cat(sprintf("  DATA cross-cutting: %d (%.1f%%)\n",
    sum(data_seg$category == "DATA_cross_cutting"),
    sum(data_seg$category == "DATA_cross_cutting") / nrow(data_seg) * 100))

# ============================================================================
# 2. Calculate DATA-Discipline Connections
# ============================================================================

cat("\nCalculating DATA-discipline connections...\n")

# Parse disciplines column and count connections
connections <- data_seg %>%
  # Remove DATA_only papers (no other disciplines to connect to)
  filter(category != "DATA_only") %>%
  # Split disciplines column
  mutate(disciplines = str_split(disciplines, ",")) %>%
  unnest(disciplines) %>%
  # Remove DATA itself (we only care about connections to other disciplines)
  filter(disciplines != "DATA") %>%
  # Count papers for each discipline
  group_by(disciplines) %>%
  summarise(
    papers = n(),
    .groups = "drop"
  ) %>%
  rename(discipline = disciplines) %>%
  arrange(desc(papers))

cat("\nDATA connections by discipline:\n")
print(connections)

# ============================================================================
# 3. Create Network Graph Structure
# ============================================================================

# Create edges (DATA to each discipline)
edges <- connections %>%
  mutate(from = "DATA", to = discipline) %>%
  select(from, to, papers)

# Create nodes
nodes <- bind_rows(
  tibble(
    name = "DATA",
    papers = nrow(data_seg),  # All DATA papers
    type = "central"
  ),
  connections %>%
    mutate(
      name = discipline,
      type = "peripheral"
    ) %>%
    select(name, papers, type)
)

# Discipline full names and colors
discipline_info <- tibble(
  code = c("DATA", "GEN", "BIO", "FISH", "MOV", "TRO", "CON", "BEH"),
  full_name = c(
    "Data Science",
    "Genetics & Genomics",
    "Biology & Life History",
    "Fisheries & Stock Assessment",
    "Movement & Space Use",
    "Trophic & Community Ecology",
    "Conservation & Policy",
    "Behaviour & Sensory"
  ),
  color = c(
    "#2E86AB",  # DATA - deep blue
    "#A23B72",  # GEN - purple
    "#F18F01",  # BIO - orange
    "#C73E1D",  # FISH - red
    "#6A994E",  # MOV - green
    "#BC4B51",  # TRO - dark red
    "#8B7E74",  # CON - brown
    "#5E548E"   # BEH - purple-grey
  )
)

# Add full names and colors to nodes
nodes <- nodes %>%
  left_join(discipline_info, by = c("name" = "code"))

# ============================================================================
# 4. Create Network Graph Object
# ============================================================================

cat("\nCreating network graph...\n")

# Create igraph object
g <- graph_from_data_frame(edges, directed = TRUE, vertices = nodes)

# ============================================================================
# 5. Create Tree Layout Visualization
# ============================================================================

cat("Creating tree visualization...\n")

# Create ggraph with tree layout
p_tree <- ggraph(g, layout = "tree", circular = FALSE) +
  # Draw edges with varying thickness based on paper count
  geom_edge_link(
    aes(width = papers, alpha = papers),
    color = "#2E86AB",
    arrow = arrow(length = unit(3, "mm"), type = "closed"),
    end_cap = circle(15, "mm")
  ) +
  # Draw nodes
  geom_node_point(
    aes(size = papers, color = name),
    alpha = 0.8
  ) +
  # Add node labels
  geom_node_text(
    aes(label = paste0(full_name, "\n", comma(papers), " papers")),
    size = 3.5,
    repel = TRUE,
    fontface = "bold",
    color = "grey20"
  ) +
  # Scales
  scale_edge_width_continuous(
    range = c(0.5, 4),
    guide = "none"
  ) +
  scale_edge_alpha_continuous(
    range = c(0.3, 0.8),
    guide = "none"
  ) +
  scale_size_continuous(
    range = c(8, 25),
    guide = "none"
  ) +
  scale_color_manual(
    values = setNames(discipline_info$color, discipline_info$code),
    guide = "none"
  ) +
  # Theme
  theme_void() +
  theme(
    plot.background = element_rect(fill = "white", color = NA),
    panel.background = element_rect(fill = "white", color = NA)
  ) +
  labs(
    title = "Data Science in Shark Research: A Cross-Cutting Discipline",
    subtitle = sprintf(
      "%s papers use data science techniques across all research areas\n%.1f%% are cross-cutting (data techniques in other disciplines)",
      comma(nrow(data_seg)),
      sum(data_seg$category == "DATA_cross_cutting") / nrow(data_seg) * 100
    ),
    caption = "Node size = number of papers | Edge width = connection strength"
  ) +
  theme(
    plot.title = element_text(size = 18, face = "bold", hjust = 0.5),
    plot.subtitle = element_text(size = 12, hjust = 0.5, margin = margin(b = 20)),
    plot.caption = element_text(size = 9, hjust = 0.5, margin = margin(t = 10)),
    plot.margin = margin(20, 20, 20, 20)
  )

# Save tree visualization
ggsave(
  filename = file.path(output_dir, "data_crosscutting_tree.png"),
  plot = p_tree,
  width = 12,
  height = 10,
  dpi = 300
)

ggsave(
  filename = file.path(output_dir, "data_crosscutting_tree.pdf"),
  plot = p_tree,
  width = 12,
  height = 10
)

cat(sprintf("✅ Saved: %s\n", file.path(output_dir, "data_crosscutting_tree.png")))
cat(sprintf("✅ Saved: %s\n", file.path(output_dir, "data_crosscutting_tree.pdf")))

# ============================================================================
# 6. Create Circular Network Visualization (Alternative)
# ============================================================================

cat("\nCreating circular network visualization...\n")

p_circular <- ggraph(g, layout = "linear", circular = TRUE) +
  # Draw edges
  geom_edge_arc(
    aes(width = papers, alpha = papers),
    color = "#2E86AB",
    strength = 0.3
  ) +
  # Draw nodes
  geom_node_point(
    aes(size = papers, color = name),
    alpha = 0.8
  ) +
  # Add labels
  geom_node_text(
    aes(
      label = paste0(name, "\n", comma(papers)),
      angle = -((-node_angle(x, y) + 90) %% 180) + 90
    ),
    size = 3,
    repel = FALSE,
    hjust = "outward",
    vjust = "outward",
    fontface = "bold"
  ) +
  # Scales
  scale_edge_width_continuous(range = c(0.5, 3), guide = "none") +
  scale_edge_alpha_continuous(range = c(0.3, 0.8), guide = "none") +
  scale_size_continuous(range = c(10, 30), guide = "none") +
  scale_color_manual(
    values = setNames(discipline_info$color, discipline_info$code),
    guide = "none"
  ) +
  coord_fixed() +
  theme_void() +
  theme(
    plot.background = element_rect(fill = "white", color = NA),
    panel.background = element_rect(fill = "white", color = NA)
  ) +
  labs(
    title = "Data Science Connections Across Shark Research Disciplines",
    subtitle = "Circular network showing cross-cutting nature of data science",
    caption = sprintf("Based on %s papers using data science techniques", comma(nrow(data_seg)))
  ) +
  theme(
    plot.title = element_text(size = 16, face = "bold", hjust = 0.5),
    plot.subtitle = element_text(size = 11, hjust = 0.5, margin = margin(b = 20)),
    plot.caption = element_text(size = 9, hjust = 0.5, margin = margin(t = 10)),
    plot.margin = margin(20, 20, 20, 20)
  )

ggsave(
  filename = file.path(output_dir, "data_crosscutting_circular.png"),
  plot = p_circular,
  width = 10,
  height = 10,
  dpi = 300
)

ggsave(
  filename = file.path(output_dir, "data_crosscutting_circular.pdf"),
  plot = p_circular,
  width = 10,
  height = 10
)

cat(sprintf("✅ Saved: %s\n", file.path(output_dir, "data_crosscutting_circular.png")))
cat(sprintf("✅ Saved: %s\n", file.path(output_dir, "data_crosscutting_circular.pdf")))

# ============================================================================
# 7. Create Sankey Diagram (Flow Visualization)
# ============================================================================

cat("\nCreating Sankey flow diagram...\n")

# Prepare data for Sankey
sankey_data <- data_seg %>%
  mutate(disciplines = str_split(disciplines, ",")) %>%
  unnest(disciplines) %>%
  filter(disciplines != "DATA") %>%
  count(category, disciplines) %>%
  rename(from = category, to = disciplines, value = n)

# Map category names to readable labels
sankey_data <- sankey_data %>%
  mutate(from = case_when(
    from == "DATA_only" ~ "Pure DATA",
    from == "DATA_primary_with_others" ~ "DATA Primary",
    from == "DATA_cross_cutting" ~ "DATA Cross-Cutting",
    TRUE ~ from
  ))

# Create simple bar chart showing flow
p_flow <- sankey_data %>%
  ggplot(aes(x = from, y = value, fill = to)) +
  geom_col(position = "stack", alpha = 0.8) +
  scale_fill_manual(
    values = setNames(
      discipline_info$color[discipline_info$code != "DATA"],
      discipline_info$code[discipline_info$code != "DATA"]
    ),
    name = "Discipline"
  ) +
  scale_y_continuous(labels = comma) +
  labs(
    title = "How Data Science Integrates with Other Disciplines",
    subtitle = "Breakdown by DATA paper category",
    x = "DATA Paper Category",
    y = "Number of Papers",
    caption = "Each bar shows which disciplines use data science techniques"
  ) +
  theme_minimal(base_size = 12) +
  theme(
    plot.title = element_text(size = 16, face = "bold", hjust = 0.5),
    plot.subtitle = element_text(size = 11, hjust = 0.5, margin = margin(b = 15)),
    axis.title = element_text(size = 11, face = "bold"),
    legend.position = "right",
    panel.grid.major.x = element_blank()
  )

ggsave(
  filename = file.path(output_dir, "data_integration_flow.png"),
  plot = p_flow,
  width = 10,
  height = 7,
  dpi = 300
)

ggsave(
  filename = file.path(output_dir, "data_integration_flow.pdf"),
  plot = p_flow,
  width = 10,
  height = 7
)

cat(sprintf("✅ Saved: %s\n", file.path(output_dir, "data_integration_flow.png")))

# ============================================================================
# 8. Summary Statistics
# ============================================================================

cat("\n" %R% strrep("=", 60) %R% "\n")
cat("DATA CROSS-CUTTING SUMMARY STATISTICS\n")
cat(strrep("=", 60) %R% "\n\n")

cat(sprintf("Total papers using DATA techniques: %s\n", comma(nrow(data_seg))))
cat(sprintf("\nBreakdown:\n"))
cat(sprintf("  Pure DATA (no other disciplines):  %4d (%5.1f%%)\n",
    sum(data_seg$category == "DATA_only"),
    sum(data_seg$category == "DATA_only") / nrow(data_seg) * 100))
cat(sprintf("  DATA primary + other disciplines:  %4d (%5.1f%%)\n",
    sum(data_seg$category == "DATA_primary_with_others"),
    sum(data_seg$category == "DATA_primary_with_others") / nrow(data_seg) * 100))
cat(sprintf("  Cross-cutting (other primary):     %4d (%5.1f%%)\n",
    sum(data_seg$category == "DATA_cross_cutting"),
    sum(data_seg$category == "DATA_cross_cutting") / nrow(data_seg) * 100))

cat(sprintf("\nTop disciplines using DATA techniques:\n"))
for (i in 1:nrow(connections)) {
  disc_name <- discipline_info$full_name[discipline_info$code == connections$discipline[i]]
  cat(sprintf("  %2d. %-35s %5d papers\n", i, disc_name, connections$papers[i]))
}

cat("\n" %R% strrep("=", 60) %R% "\n")
cat("All visualizations saved to: outputs/figures/\n")
cat(strrep("=", 60) %R% "\n")
