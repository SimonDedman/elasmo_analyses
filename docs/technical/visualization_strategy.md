---
editor_options:
  markdown:
    wrap: 72
---

# Visualization Strategy for EEA 2025 Data Panel

## Overview

This document outlines visualization approaches for presenting analytical
method trends over time, including interactive branching timelines and
design-focused graphics for the panel presentation.

**Primary Goal:** Create compelling visualizations showing the evolution
and adoption of analytical methods across disciplines (2000-2025).

---

## 1. Branching Timeline with Variable Thickness

### Concept

**Visual Metaphor:** River/stream network where:
- **Branches** = Analytical methods within each discipline
- **Branch thickness** = Number of papers using that method (by year)
- **Flow direction** = Time progression (2000 → 2025)
- **Color** = Discipline category

**Example:**
```
                            ┌─────── Acoustic Telemetry (thick: 50 papers/yr)
Movement & Spatial ────────┼─────── Satellite Tracking (medium: 25 papers/yr)
(2000-2025)                └─────── SDMs (thin→thick: 5→30 papers/yr growth)
```

### Implementation Options

#### Option A: R `{ggplot2}` + `{ggsankey}` (Sankey/Alluvial Diagram)

**Best for:** Showing method flow and transitions over time

**Example Code:**

```r
library(ggplot2)
library(ggsankey)
library(dplyr)
library(duckdb)

# Query data from database
con <- dbConnect(duckdb::duckdb(), "data/lit_review.duckdb")

method_counts <- dbGetQuery(con, "
  SELECT
    year,
    CASE
      WHEN a_acoustic_telemetry = TRUE THEN 'Acoustic Telemetry'
      WHEN a_satellite_tracking = TRUE THEN 'Satellite Tracking'
      WHEN a_sdm = TRUE THEN 'Species Distribution Models'
      -- ... (add all methods)
    END AS method,
    COUNT(*) as paper_count
  FROM literature_review
  WHERE d_movement_spatial = TRUE
    AND year BETWEEN 2000 AND 2025
  GROUP BY year, method
  ORDER BY year, paper_count DESC
")

# Create Sankey diagram
method_counts %>%
  make_long(year, method, value = paper_count) %>%
  ggplot(aes(x = x,
             next_x = next_x,
             node = node,
             next_node = next_node,
             fill = factor(method),
             value = paper_count)) +
  geom_sankey(flow.alpha = 0.5, node.color = "gray30") +
  geom_sankey_label(size = 3, color = "white", fill = "gray40") +
  scale_fill_viridis_d(option = "turbo", name = "Method") +
  theme_sankey(base_size = 14) +
  labs(
    title = "Evolution of Analytical Methods in Movement & Spatial Ecology",
    subtitle = "Branch thickness = Number of papers using method",
    x = "Year",
    y = NULL
  ) +
  theme(legend.position = "bottom")

ggsave("figures/movement_methods_sankey.png", width = 14, height = 10, dpi = 300)
```

**Pros:**
- ✅ Native R implementation
- ✅ Shows flow between time periods
- ✅ Variable thickness based on counts
- ✅ Multiple disciplines side-by-side

**Cons:**
- ⚠️ Can get cluttered with many methods
- ⚠️ Not truly "branching" (more like parallel flows)

---

#### Option B: R `{networkD3}` (Interactive Force-Directed Network)

**Best for:** Interactive exploration, showing method relationships

**Example Code:**

```r
library(networkD3)
library(dplyr)
library(jsonlite)

# Prepare nodes (years + methods)
nodes <- data.frame(
  name = c(
    paste0("Year ", 2000:2025),  # Time nodes
    "Acoustic Telemetry",
    "Satellite Tracking",
    "SDMs",
    # ... all methods
  ),
  group = c(
    rep("Time", 26),  # Years
    rep("Movement Methods", 3),  # Method categories
    # ...
  )
)

# Prepare edges (connections with weights)
links <- method_counts %>%
  mutate(
    source = match(paste0("Year ", year), nodes$name) - 1,  # 0-indexed
    target = match(method, nodes$name) - 1,
    value = paper_count  # Edge thickness
  ) %>%
  select(source, target, value)

# Create interactive network
network <- forceNetwork(
  Links = links,
  Nodes = nodes,
  Source = "source",
  Target = "target",
  Value = "value",
  NodeID = "name",
  Group = "group",
  opacity = 0.8,
  fontSize = 14,
  zoom = TRUE,
  legend = TRUE
)

# Save as HTML
saveNetwork(network, "figures/movement_methods_network.html")
```

**Pros:**
- ✅ Interactive (zoom, pan, hover for details)
- ✅ Self-organizing layout
- ✅ Variable edge thickness
- ✅ Can embed in GitHub Pages

**Cons:**
- ⚠️ Temporal progression not explicit (requires encoding)
- ⚠️ May be too "busy" for static presentation slides

---

#### Option C: R `{plotly}` + Custom Branching Layout (RECOMMENDED)

**Best for:** Custom control over branching visualization, interactivity

**Example Code:**

```r
library(plotly)
library(dplyr)
library(tidyr)

# Prepare data with cumulative counts
method_timeline <- dbGetQuery(con, "
  SELECT
    year,
    SUM(CASE WHEN a_acoustic_telemetry = TRUE THEN 1 ELSE 0 END) as acoustic_telemetry,
    SUM(CASE WHEN a_satellite_tracking = TRUE THEN 1 ELSE 0 END) as satellite_tracking,
    SUM(CASE WHEN a_sdm = TRUE THEN 1 ELSE 0 END) as sdm,
    SUM(CASE WHEN a_home_range = TRUE THEN 1 ELSE 0 END) as home_range
  FROM literature_review
  WHERE d_movement_spatial = TRUE
    AND year BETWEEN 2000 AND 2025
  GROUP BY year
  ORDER BY year
") %>%
  pivot_longer(-year, names_to = "method", values_to = "count")

# Create branching plot with variable line width
fig <- plot_ly(method_timeline,
               x = ~year,
               y = ~count,
               split = ~method,
               type = 'scatter',
               mode = 'lines',
               line = list(shape = 'spline'),  # Smooth curves
               # Variable line width based on count
               transforms = list(
                 list(
                   type = 'aggregate',
                   groups = ~method,
                   aggregations = list(
                     list(target = 'y', func = 'sum', enabled = TRUE)
                   )
                 )
               )) %>%
  layout(
    title = list(
      text = "Analytical Method Adoption in Movement & Spatial Ecology<br><sub>Line thickness ∝ papers/year</sub>",
      font = list(size = 18)
    ),
    xaxis = list(title = "Year"),
    yaxis = list(title = "Number of Papers"),
    hovermode = 'x unified',
    legend = list(
      orientation = 'h',
      y = -0.2
    )
  )

# Add variable line width based on counts
for(method_name in unique(method_timeline$method)) {
  method_data <- filter(method_timeline, method == method_name)

  fig <- fig %>%
    add_trace(
      x = method_data$year,
      y = method_data$count,
      name = method_name,
      type = 'scatter',
      mode = 'lines',
      line = list(
        width = scales::rescale(method_data$count, to = c(2, 15)),  # Scale 2-15px
        shape = 'spline',
        color = viridis::viridis(8)[which(unique(method_timeline$method) == method_name)]
      ),
      hovertemplate = paste0(
        "<b>%{fullData.name}</b><br>",
        "Year: %{x}<br>",
        "Papers: %{y}<br>",
        "<extra></extra>"
      )
    )
}

# Save as interactive HTML
htmlwidgets::saveWidget(fig, "figures/movement_methods_timeline.html")

# Also save static PNG for slides
orca(fig, "figures/movement_methods_timeline.png", width = 1400, height = 900)
```

**Pros:**
- ✅ **Highly customizable** (exact branching layout control)
- ✅ **Interactive HTML** for GitHub Pages
- ✅ **Static PNG export** for slides (via `orca` or `kaleido`)
- ✅ **Variable line thickness** directly represents paper counts
- ✅ Smooth spline curves create organic "flowing" appearance
- ✅ Hover tooltips show exact counts

**Cons:**
- ⚠️ Requires manual layout for true "branching" (methods diverging from trunk)
- ⚠️ `orca` installation needed for PNG export (or use `kaleido`)

---

#### Option D: D3.js Custom Visualization (Most Flexible)

**Best for:** Ultimate control, publication-quality interactive graphics

**Example Code (JavaScript):**

```javascript
// data.json structure
{
  "discipline": "Movement & Spatial",
  "methods": [
    {
      "name": "Acoustic Telemetry",
      "years": [
        {"year": 2000, "count": 5},
        {"year": 2001, "count": 8},
        // ... through 2025
      ]
    },
    // ... other methods
  ]
}

// D3.js visualization
const margin = {top: 50, right: 150, bottom: 50, left: 50};
const width = 1200 - margin.left - margin.right;
const height = 800 - margin.top - margin.bottom;

const svg = d3.select("#viz")
  .append("svg")
  .attr("width", width + margin.left + margin.right)
  .attr("height", height + margin.top + margin.bottom)
  .append("g")
  .attr("transform", `translate(${margin.left},${margin.top})`);

// Scales
const xScale = d3.scaleLinear()
  .domain([2000, 2025])
  .range([0, width]);

const yScale = d3.scaleLinear()
  .domain([0, d3.max(data.methods, d => d3.max(d.years, y => y.count))])
  .range([height, 0]);

const colorScale = d3.scaleOrdinal()
  .domain(data.methods.map(d => d.name))
  .range(d3.schemeTableau10);

// Line generator with variable width
const lineGenerator = d3.line()
  .x(d => xScale(d.year))
  .y(d => yScale(d.count))
  .curve(d3.curveBasis);  // Smooth curves

// Draw methods as paths with variable stroke width
data.methods.forEach(method => {
  svg.append("path")
    .datum(method.years)
    .attr("fill", "none")
    .attr("stroke", colorScale(method.name))
    .attr("d", lineGenerator)
    // Variable stroke width based on average count
    .attr("stroke-width", d => {
      const avgCount = d3.mean(d, y => y.count);
      return Math.sqrt(avgCount) * 2;  // Scale thickness
    })
    .attr("opacity", 0.7)
    .on("mouseover", function(event, d) {
      d3.select(this).attr("opacity", 1);
      // Show tooltip
    })
    .on("mouseout", function(event, d) {
      d3.select(this).attr("opacity", 0.7);
    });
});

// Add axes, labels, legend...
```

**Pros:**
- ✅ **Ultimate flexibility** (any layout possible)
- ✅ **Publication-quality** (SVG output)
- ✅ **Interactive** (tooltips, zoom, pan)
- ✅ **GitHub Pages compatible** (pure HTML/JS)

**Cons:**
- ❌ Requires JavaScript knowledge
- ❌ More development time
- ❌ Harder to integrate with R workflow

---

### Recommended Approach

**Primary:** **Option C - R `{plotly}` with custom layout**

**Rationale:**
1. Native R integration (fits existing workflow)
2. Interactive HTML for GitHub Pages
3. Static PNG export for presentation slides
4. Variable line thickness directly controlled
5. Reasonable development time

**Secondary:** **Option A - `{ggsankey}`** as fallback if time-constrained

---

## 2. GitHub Pages Hosting

### Setup

```bash
# In project root
cd "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"

# Create docs directory for GitHub Pages (or use existing)
mkdir -p docs/figures

# Move HTML visualizations
cp figures/*.html docs/figures/

# Create index.html for landing page
cat > docs/index.html << 'EOF'
<!DOCTYPE html>
<html>
<head>
  <title>EEA 2025 Data Panel - Method Evolution Visualizations</title>
  <style>
    body {
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
      max-width: 1200px;
      margin: 0 auto;
      padding: 20px;
      background: #f5f5f5;
    }
    h1 { color: #2c3e50; }
    .viz-container {
      background: white;
      padding: 20px;
      margin: 20px 0;
      border-radius: 8px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    iframe {
      width: 100%;
      height: 800px;
      border: none;
    }
  </style>
</head>
<body>
  <h1>EEA 2025 Data Panel: Evolution of Analytical Methods</h1>
  <p>Interactive visualizations showing the adoption of emerging technologies in elasmobranch research (2000-2025)</p>

  <div class="viz-container">
    <h2>Movement & Spatial Ecology Methods</h2>
    <iframe src="figures/movement_methods_timeline.html"></iframe>
  </div>

  <div class="viz-container">
    <h2>Genetics & Genomics Methods</h2>
    <iframe src="figures/genetics_methods_timeline.html"></iframe>
  </div>

  <!-- Add all 8 disciplines -->

  <footer>
    <p><em>Data source: Systematic literature review of >5,000 papers (2000-2025)</em></p>
  </footer>
</body>
</html>
EOF

# Enable GitHub Pages
git add docs/
git commit -m "Add interactive visualizations for GitHub Pages"
git push

# Configure on GitHub:
# Settings → Pages → Source: Deploy from branch → Branch: main → Folder: /docs
```

**URL:** `https://[username].github.io/[repo-name]/`

**Example:** `https://simondedman.github.io/eea2025-data-panel/`

---

## 3. Design-Focused Graphics: Claude Code Capabilities

### Current Limitations

**Claude Code CANNOT directly interface with:**
- ❌ Canva API (requires authentication, not supported)
- ❌ Adobe Creative Suite (desktop apps, no programmatic access)
- ❌ Figma API (requires authentication tokens)

### What Claude Code CAN Do

#### A. Generate Design Specifications

```r
# Claude can create detailed design specs as structured data
design_spec <- list(
  title = "Evolution of Shark Research Technologies",
  subtitle = "2000-2025",
  layout = "branching_timeline",
  dimensions = list(width = 1920, height = 1080),  # 16:9 for slides
  color_palette = c(
    biology = "#2ecc71",
    behaviour = "#3498db",
    trophic = "#e74c3c",
    genetics = "#9b59b6",
    movement = "#f39c12",
    fisheries = "#1abc9c",
    conservation = "#34495e",
    data_science = "#e67e22"
  ),
  fonts = list(
    title = "Montserrat Bold 48pt",
    subtitle = "Montserrat Regular 24pt",
    labels = "Open Sans 14pt"
  ),
  elements = list(
    list(
      type = "timeline",
      x = 100, y = 200,
      width = 1720, height = 700,
      branch_data = method_counts
    ),
    list(
      type = "legend",
      x = 1500, y = 100,
      items = discipline_colors
    )
  )
)

# Export as JSON for Canva/Figma import
jsonlite::write_json(design_spec, "design_spec.json", pretty = TRUE)
```

**Then:** Manually import to Canva using design specs as reference

---

#### B. Create High-Quality R Graphics for Import

**Claude can generate publication-quality R graphics** that you can import to Canva as elements:

```r
library(ggplot2)
library(showtext)  # For custom fonts

# Add Google Fonts
font_add_google("Montserrat", "montserrat")
font_add_google("Open Sans", "opensans")
showtext_auto()

# Create high-res figure for Canva import
timeline_plot <- ggplot(method_timeline, aes(x = year, y = count,
                                              color = method,
                                              size = count)) +
  geom_line(linewidth = 2, alpha = 0.8) +
  geom_point(alpha = 0.6) +
  scale_color_manual(values = discipline_colors) +
  scale_size_continuous(range = c(1, 10)) +
  labs(
    title = "Evolution of Movement Ecology Methods",
    subtitle = "2000-2025",
    x = NULL,
    y = "Papers per Year"
  ) +
  theme_minimal(base_size = 16, base_family = "opensans") +
  theme(
    plot.title = element_text(family = "montserrat", face = "bold", size = 28),
    plot.subtitle = element_text(family = "montserrat", size = 18),
    legend.position = "right",
    plot.background = element_rect(fill = "white", color = NA),
    panel.grid.minor = element_blank()
  )

# Export as high-res PNG with transparency
ggsave(
  "figures/movement_timeline_canva.png",
  plot = timeline_plot,
  width = 16,
  height = 9,
  dpi = 300,
  bg = "transparent"  # Transparent background for layering in Canva
)

# Export as SVG for infinite scaling
ggsave(
  "figures/movement_timeline_canva.svg",
  plot = timeline_plot,
  width = 16,
  height = 9
)
```

**Workflow:**
1. Claude generates high-quality R graphics (PNG/SVG)
2. You import to Canva as elements
3. Add design flourishes in Canva (backgrounds, icons, text overlays)

---

#### C. Generate Plotly Figures Styled for Presentations

```r
library(plotly)

# Create presentation-ready interactive plot
fig <- plot_ly(
  method_timeline,
  x = ~year,
  y = ~count,
  color = ~method,
  type = 'scatter',
  mode = 'lines+markers',
  line = list(width = 4),
  marker = list(size = 10)
) %>%
  layout(
    title = list(
      text = "<b>Evolution of Analytical Methods</b><br><sub>Movement & Spatial Ecology</sub>",
      font = list(family = "Montserrat, sans-serif", size = 24, color = "#2c3e50")
    ),
    xaxis = list(
      title = "Year",
      titlefont = list(family = "Open Sans, sans-serif", size = 16),
      gridcolor = "#ecf0f1",
      showline = TRUE,
      linecolor = "#bdc3c7"
    ),
    yaxis = list(
      title = "Papers per Year",
      titlefont = list(family = "Open Sans, sans-serif", size = 16),
      gridcolor = "#ecf0f1",
      showline = TRUE,
      linecolor = "#bdc3c7"
    ),
    plot_bgcolor = "#ffffff",
    paper_bgcolor = "#f8f9fa",
    font = list(family = "Open Sans, sans-serif", size = 14),
    legend = list(
      font = list(size = 14),
      bgcolor = "#ffffff",
      bordercolor = "#bdc3c7",
      borderwidth = 1
    ),
    hovermode = 'x unified'
  )

# Save for embedding in presentation
htmlwidgets::saveWidget(fig, "figures/movement_methods_presentation.html")

# Or export static image
orca(fig, "figures/movement_methods_slide.png", width = 1920, height = 1080)
```

**Use in:**
- PowerPoint (insert HTML or PNG)
- Google Slides (insert PNG or link to GitHub Pages HTML)
- Reveal.js slides (embed HTML directly)

---

#### D. Create Programmatic SVG Graphics

**Claude can generate custom SVG graphics** with precise control:

```r
library(grid)
library(gridSVG)

# Create custom branching diagram
grid.newpage()

# Main trunk
grid.lines(
  x = c(0.1, 0.9),
  y = c(0.5, 0.5),
  gp = gpar(col = "#34495e", lwd = 20)
)

# Branches (methods)
branch_data <- data.frame(
  method = c("Acoustic Telemetry", "Satellite Tracking", "SDMs"),
  start_x = c(0.3, 0.5, 0.7),
  end_x = c(0.4, 0.6, 0.8),
  end_y = c(0.7, 0.8, 0.6),
  thickness = c(15, 10, 12)  # Based on paper counts
)

for(i in 1:nrow(branch_data)) {
  grid.lines(
    x = c(branch_data$start_x[i], branch_data$end_x[i]),
    y = c(0.5, branch_data$end_y[i]),
    gp = gpar(col = "#3498db", lwd = branch_data$thickness[i])
  )

  # Add label
  grid.text(
    label = branch_data$method[i],
    x = branch_data$end_x[i],
    y = branch_data$end_y[i],
    just = "left",
    gp = gpar(fontsize = 14, fontface = "bold")
  )
}

# Export as SVG
grid.export("figures/branching_diagram.svg")
```

**Then:** Import SVG to Canva/Figma for final design touches

---

### Recommended Workflow for Design Graphics

**Step 1: Data Processing in R (Claude generates code)**

```r
# Calculate method trends
method_summary <- dbGetQuery(con, "
  SELECT
    year,
    discipline,
    method,
    COUNT(*) as papers,
    SUM(COUNT(*)) OVER (PARTITION BY method ORDER BY year) as cumulative
  FROM (
    -- Unpivot analysis columns
    SELECT study_id, year, d_movement_spatial as discipline,
           'Acoustic Telemetry' as method
    FROM literature_review
    WHERE a_acoustic_telemetry = TRUE
    UNION ALL
    -- ... repeat for all methods
  )
  GROUP BY year, discipline, method
")

write_csv(method_summary, "data/method_trends_for_design.csv")
```

**Step 2: Generate Base Visualizations in R (Claude generates code)**

```r
# High-quality static plots
ggsave("figures/for_canva/timeline_base.png", width = 16, height = 9, dpi = 300, bg = "transparent")

# Interactive HTML plots
htmlwidgets::saveWidget(fig, "figures/interactive/timeline.html")
```

**Step 3: Manual Design in Canva (You do this)**

1. Import PNG/SVG from R
2. Add backgrounds, icons, branding
3. Adjust colors, fonts, layouts
4. Export final graphics (PNG/PDF for slides)

**Step 4: Host Interactive Versions on GitHub Pages (Claude generates)**

```bash
# Upload HTML visualizations
git add docs/figures/*.html
git commit -m "Add interactive visualizations"
git push
```

---

## 4. Alternative: Quarto Presentations

**Claude CAN generate complete presentation systems** using Quarto:

```yaml
# presentation.qmd
---
title: "Evolution of Analytical Methods in Elasmobranch Research"
subtitle: "EEA 2025 Data Panel"
author: "Simon Dedman et al."
format:
  revealjs:
    theme: [default, custom.scss]
    slide-number: true
    transition: slide
    background-transition: fade
    embed-resources: true
---

## Movement & Spatial Ecology {.scrollable}

```{r}
#| echo: false
#| fig-width: 12
#| fig-height: 7

library(plotly)
# ... plotly code here
fig
```

## Genetics & Genomics {.scrollable}

```{r}
#| echo: false
# ... next visualization
```
```

**Render:**

```bash
quarto render presentation.qmd
```

**Output:** Self-contained HTML presentation with embedded interactive graphics

**Host on GitHub Pages:** Instant deployment

---

## 5. Summary & Recommendations

### For Panel Presentation Graphics

**Recommended Stack:**

1. **Data Processing:** R + DuckDB (Claude generates)
2. **Base Visualizations:** R `{plotly}` (Claude generates)
3. **Interactive Hosting:** GitHub Pages (Claude generates HTML)
4. **Static Slides:** Export PNG from Plotly (Claude generates export code)
5. **Design Polish:** Manual in Canva (you do this)

**Visualization Priority:**

1. **Branching timeline with variable thickness** (plotly) - CRITICAL
2. **Method co-occurrence network** (networkD3) - HIGH
3. **Geographic heatmap** (leaflet or plotly) - MEDIUM
4. **Temporal trend facets** (ggplot2) - MEDIUM

### Claude Code's Role

**CAN DO:**
- ✅ Generate all R visualization code
- ✅ Create interactive HTML (plotly, networkD3, D3.js)
- ✅ Export high-res PNG/SVG for Canva import
- ✅ Set up GitHub Pages hosting
- ✅ Create Quarto presentations
- ✅ Generate design specifications (JSON)
- ✅ Create programmatic SVG graphics

**CANNOT DO:**
- ❌ Direct Canva API integration
- ❌ Automated Figma/Adobe edits
- ❌ Generate graphics without R/Python code

**Workflow:**
1. Claude generates R code → High-quality visualizations
2. You import to Canva → Add design polish
3. Claude generates GitHub Pages → Host interactive versions

---

## Next Steps

1. **Complete database** (Phases 1-4)
2. **Extract method counts** by year and discipline (Phase 5)
3. **Generate visualizations** using code in this doc (Phase 5)
4. **Host on GitHub Pages** (Phase 5)
5. **Import to Canva** for final slide design (Phase 6)
6. **Embed in presentation** (Phase 6-7)

**Estimated Timeline:**
- Visualization code generation: 1 day (Assistant)
- Rendering all disciplines: 1 day (Assistant)
- GitHub Pages setup: 2 hours (Assistant)
- Canva design polish: 2-3 days (SD + GT)

---

*Last updated: 2025-10-02*
*Status: Strategy documented, awaiting Phase 5 (analysis)*
