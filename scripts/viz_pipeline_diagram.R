## viz_pipeline_diagram.R
## EEA 2025 Data Panel — Project Pipeline Diagram
## Pure ggplot2 implementation using geom_rect, geom_segment, geom_text
## Output: outputs/figures/pipeline_diagram.{png,pdf}

library(ggplot2)

## -- Colour palette -----------------------------------------------------------
COL_SOURCE  <- "#2E86AB"   # blue       Stage 1: Data Sources
COL_ACQUIRE <- "#2E9E77"   # green      Stage 2: Paper Acquisition
COL_SCHEMA  <- "#D4711A"   # orange     Stage 3: Schema Design
COL_EXTRACT <- "#C0392B"   # red        Stage 4: Extraction Pipeline
COL_ENRICH  <- "#7B2D8B"   # purple     Stage 5: Enrichment
COL_OUTPUT  <- "#1A7A6E"   # teal       Stage 6: Outputs
COL_FUTURE  <- "#6D7D8B"   # slate-grey Stage 7: Future

COL_BG      <- "#F5F6F8"

## -- Layout constants ---------------------------------------------------------
BOX_W     <- 3.8   # box width
BOX_H     <- 0.60  # box height (each item)
BOX_VGAP  <- 0.10  # vertical gap between item boxes
HDR_H     <- 0.42  # stage header block height
STAGE_GAP <- 0.08  # gap between header bottom and first item (shrunk per tweak 4)
COL_GAP   <- 0.55  # space above stage N header (grown per tweak 4)

X_L <- 0.6          # left column x start
X_R <- 10.6         # right column x start
TOP <- 21.2         # y of top of Stage 1 & 2 header tops

## -- Helper: build item boxes for one stage -----------------------------------
make_boxes <- function(stage_id, x_left, y_hdr_top, items, fill_col) {
  n <- length(items)
  item_tops <- y_hdr_top - HDR_H - STAGE_GAP -
    (seq_len(n) - 1) * (BOX_H + BOX_VGAP)
  data.frame(
    stage = stage_id,
    label = items,
    xmin  = x_left,
    xmax  = x_left + BOX_W,
    ymin  = item_tops - BOX_H,
    ymax  = item_tops,
    xctr  = x_left + BOX_W / 2,
    yctr  = item_tops - BOX_H / 2,
    fill  = fill_col,
    stringsAsFactors = FALSE
  )
}

## Stage total height (header + items)
stage_total_h <- function(n_items) {
  HDR_H + STAGE_GAP + n_items * BOX_H + (n_items - 1) * BOX_VGAP
}

## -- Stage y_hdr_top values ---------------------------------------------------
N1 <- 5; N2 <- 4; N3 <- 4; N4 <- 3; N5 <- 8; N6 <- 5

yt1 <- TOP
yt2 <- TOP
yt3 <- yt1 - stage_total_h(N1) - COL_GAP
yt4 <- yt3                                  # Stage 4 aligned with Stage 3
yt5 <- yt3 - stage_total_h(N3) - COL_GAP
yt6 <- yt5                                  # Stage 6 aligned with Stage 5
## Stage 7 starts below the lower of stages 5 and 6
yt7 <- min(yt5 - stage_total_h(N5), yt6 - stage_total_h(N6)) - COL_GAP

## -- Stage 1: Data Sources ----------------------------------------------------
s1 <- make_boxes(1, X_L, yt1,
  c("Shark-References DB\n(30,553 papers)",
    "OpenAlex API\n(authors + citations)",
    "Sharkipedia API\n(species traits)",
    "Genderize.io\n(gender inference)",
    "Unpaywall\n(open access status)"),
  COL_SOURCE)

## -- Stage 2: Paper Acquisition -----------------------------------------------
s2 <- make_boxes(2, X_R, yt2,
  c("PDF library\n(16,303 PDFs)",
    "Shark-References NAS\n(Jurgen uploads)",
    "Direct download &\ncoauthor contributions",
    "Download tracking\nweb interface"),
  COL_ACQUIRE)

## -- Stage 3: Schema Design ---------------------------------------------------
s3 <- make_boxes(3, X_L, yt3,
  c("6 schemas, 123 binary\ncolumns total",
    "Eco(20) - Pressure(26)\nGear(28) - Impact(21)",
    "Discipline(19) -\nOcean Basin(9)",
    "Validated: Beukhof 2026,\nISSCFG, BMIS"),
  COL_SCHEMA)

## -- Stage 4: Extraction Pipeline (3 items, tweak 3) --------------------------
s4 <- make_boxes(4, X_R, yt4,
  c("PDF text extraction\n(section stripping)",
    "Keyword + frequency\n+ anchor scoring",
    "Evidence audit trail\n(217K+ rows)"),
  COL_EXTRACT)

## -- Stage 5: Enrichment (6 items, tweak 1 adds Altmetric) --------------------
s5 <- make_boxes(5, X_L, yt5,
  c("Author data\n(28,953 unique authors)",
    "Gender inference\n(87% resolved)",
    "Institution country\nmapping (87.7%)",
    "Geographic pipeline\n(study country, basin)",
    "Journal quality\n(SciMago ranks)",
    "Sharkipedia species\ntraits + life history",
    "Bycatch inference\n(target species)",
    "Altmetric/Dimensions\nsocial data (pending)"),
  COL_ENRICH)

## -- Stage 6: Outputs (5 items, tweak 2+3: moved parquet here, 118+) ----------
s6 <- make_boxes(6, X_R, yt6,
  c("Output: enriched\n.parquet (1,546+ cols)",
    "118+ analytical\nvisualisations",
    "Schema extraction\nevidence CSV",
    "Per-journal download\npages",
    "Meeting review\nworkbooks"),
  COL_OUTPUT)

## -- Stage 7: Future Directions (2x2 layout, tweaks 6+8) ---------------------
## Tweak 6: normal width, centred
## Tweak 8: 2x2 layout with equal horizontal and vertical spacing

s7_vgap  <- BOX_VGAP           # vertical gap between rows (same as elsewhere)
s7_hgap  <- BOX_VGAP           # horizontal gap = vertical gap (tweak 8)
s7_bw    <- BOX_W              # same box width as other stages
s7_total_w <- 2 * s7_bw + s7_hgap
s7_x_centre <- (X_L + X_R + BOX_W) / 2
s7_x_left  <- s7_x_centre - s7_total_w / 2
s7_x_right <- s7_x_left + s7_bw + s7_hgap

yt7_item_top <- yt7 - HDR_H - STAGE_GAP

s7_items <- c(
  "Automated update pipeline",
  "Living database with\ncommunity curation",
  "Interactive HTML dashboard\n(GitHub Pages)",
  "LLM conversational interface\n(Qdrant + Ollama)"
)

## Row 1: items 1 (left) and 2 (right)
## Row 2: items 3 (left) and 4 (right)
s7 <- data.frame(
  stage = 7L,
  label = s7_items,
  xmin  = c(s7_x_left, s7_x_right, s7_x_left, s7_x_right),
  xmax  = c(s7_x_left + s7_bw, s7_x_right + s7_bw,
            s7_x_left + s7_bw, s7_x_right + s7_bw),
  ymin  = c(yt7_item_top - BOX_H,
            yt7_item_top - BOX_H,
            yt7_item_top - 2 * BOX_H - s7_vgap,
            yt7_item_top - 2 * BOX_H - s7_vgap),
  ymax  = c(yt7_item_top,
            yt7_item_top,
            yt7_item_top - BOX_H - s7_vgap,
            yt7_item_top - BOX_H - s7_vgap),
  fill  = COL_FUTURE,
  stringsAsFactors = FALSE
)
s7$xctr <- (s7$xmin + s7$xmax) / 2
s7$yctr <- (s7$ymin + s7$ymax) / 2

## Combine all boxes
all_boxes <- rbind(s1, s2, s3, s4, s5, s6, s7)

## -- Stage headers ------------------------------------------------------------
hdr_solo <- data.frame(
  label = c("Stage 1: Data Sources",
            "Stage 2: Paper Acquisition",
            "Stage 3: Schema Design",
            "Stage 4: Extraction Pipeline",
            "Stage 5: Enrichment",
            "Stage 6: Outputs"),
  xmin  = c(X_L, X_R, X_L, X_R, X_L, X_R),
  xmax  = c(X_L, X_R, X_L, X_R, X_L, X_R) + BOX_W,
  ymin  = c(yt1, yt2, yt3, yt4, yt5, yt6) - HDR_H,
  ymax  = c(yt1, yt2, yt3, yt4, yt5, yt6),
  xctr  = c(X_L, X_R, X_L, X_R, X_L, X_R) + BOX_W / 2,
  yctr  = c(yt1, yt2, yt3, yt4, yt5, yt6) - HDR_H / 2,
  fill  = c(COL_SOURCE, COL_ACQUIRE, COL_SCHEMA,
            COL_EXTRACT, COL_ENRICH, COL_OUTPUT),
  stringsAsFactors = FALSE
)

## Stage 7 header: normal width, centred (tweak 6)
hdr_s7 <- data.frame(
  label = "Stage 7: Future Directions",
  xmin  = s7_x_left,
  xmax  = s7_x_right + s7_bw,
  ymin  = yt7 - HDR_H,
  ymax  = yt7,
  xctr  = s7_x_centre,
  yctr  = yt7 - HDR_H / 2,
  fill  = COL_FUTURE,
  stringsAsFactors = FALSE
)

## -- Arrows -------------------------------------------------------------------
## Tweak 4: vertical arrows go to the STAGE HEADER box, not to first item
## Tweak 5: S5 & S6 arrows go to the Stage 7 header box

x_l_mid <- X_L + BOX_W / 2
x_r_mid <- X_R + BOX_W / 2

## Vertical midpoints of each stage (header + items combined)
s1_vmid <- (yt1 + min(s1$ymin)) / 2
s2_vmid <- (yt2 + min(s2$ymin)) / 2
s3_vmid <- (yt3 + min(s3$ymin)) / 2
s4_vmid <- (yt4 + min(s4$ymin)) / 2
s5_vmid <- (yt5 + min(s5$ymin)) / 2
s6_vmid <- (yt6 + min(s6$ymin)) / 2

## Horizontal arrows at the vertical centre of the RIGHT stage (shorter one)
## so the arrow intersects the down-arrow at its midpoint
h_y_12 <- s2_vmid    # S1->S2: centre of S2
h_y_34 <- s4_vmid    # S3->S4: centre of S4
h_y_56 <- s6_vmid    # S5->S6: centre of S6

arrows_df <- data.frame(
  x    = c(
    ## Left-column vertical arrows (to stage header boxes)
    x_l_mid,                         # S1 bottom -> S3 header top
    x_l_mid,                         # S3 bottom -> S5 header top
    ## Right-column vertical arrows
    x_r_mid,                         # S2 bottom -> S4 header top
    x_r_mid,                         # S4 bottom -> S6 header top
    ## Horizontal cross arrows
    X_L + BOX_W,                     # S1 -> S2
    X_L + BOX_W,                     # S3 -> S4
    X_L + BOX_W,                     # S5 -> S6
    ## S5 & S6 -> S7 header
    x_l_mid,                         # S5 bottom -> S7 header top
    x_r_mid                          # S6 bottom -> S7 header top
  ),
  y    = c(
    min(s1$ymin) - 0.03,
    min(s3$ymin) - 0.03,
    min(s2$ymin) - 0.03,
    min(s4$ymin) - 0.03,
    h_y_12,
    h_y_34,
    h_y_56,
    min(s5$ymin) - 0.03,
    min(s6$ymin) - 0.03
  ),
  xend = c(
    x_l_mid,
    x_l_mid,
    x_r_mid,
    x_r_mid,
    X_R,
    X_R,
    X_R,
    s7_x_centre - s7_total_w / 4,
    s7_x_centre + s7_total_w / 4
  ),
  yend = c(
    yt3 + 0.03,                      # -> S3 header top
    yt5 + 0.03,                      # -> S5 header top
    yt4 + 0.03,                      # -> S4 header top
    yt6 + 0.03,                      # -> S6 header top
    h_y_12,                           # horizontal: same y
    h_y_34,
    h_y_56,
    yt7 + 0.03,                      # -> S7 header top
    yt7 + 0.03
  ),
  stringsAsFactors = FALSE
)

## -- Canvas limits ------------------------------------------------------------
y_lo <- min(s7$ymin) - 0.7
y_hi <- TOP + 1.6

## -- Build ggplot -------------------------------------------------------------
p <- ggplot() +
  theme_void() +
  theme(
    plot.background  = element_rect(fill = COL_BG, colour = NA),
    panel.background = element_rect(fill = COL_BG, colour = NA),
    plot.title    = element_text(
      size = 20, face = "bold", colour = "#1A1A2E",
      hjust = 0.5, margin = margin(b = 3)),
    plot.subtitle = element_text(
      size = 11.5, colour = "#444455",
      hjust = 0.5, margin = margin(b = 14)),
    plot.margin   = margin(12, 12, 12, 12)
  ) +
  labs(
    title    = "EEA 2025 Data Panel: Project Pipeline",
    subtitle = "30,553 papers  |  16,303 PDFs  |  123 schema columns  |  28,953 authors"
  ) +
  coord_cartesian(xlim = c(0, 20), ylim = c(y_lo, y_hi), expand = FALSE) +

  ## -- Subtle column lane shading ---------------------------------------------
  annotate("rect",
    xmin = X_L - 0.4, xmax = X_L + BOX_W + 0.4,
    ymin = yt7 + 0.1, ymax = y_hi - 0.9,
    fill = "#D6E8F5", colour = NA, alpha = 0.4) +
  annotate("rect",
    xmin = X_R - 0.4, xmax = X_R + BOX_W + 0.4,
    ymin = yt7 + 0.1, ymax = y_hi - 0.9,
    fill = "#D5EFE6", colour = NA, alpha = 0.4) +

  ## -- Column lane labels -----------------------------------------------------
  annotate("text",
    x = X_L + BOX_W / 2, y = y_hi - 0.45,
    label = "Sources -> Schema -> Enrichment",
    colour = "#3A6EA5", size = 3.2, fontface = "bold.italic", hjust = 0.5) +
  annotate("text",
    x = X_R + BOX_W / 2, y = y_hi - 0.45,
    label = "Acquisition -> Extraction -> Outputs",
    colour = "#1D7A55", size = 3.2, fontface = "bold.italic", hjust = 0.5) +

  ## -- Arrows (behind boxes) --------------------------------------------------
  geom_segment(
    data = arrows_df,
    aes(x = x, y = y, xend = xend, yend = yend),
    arrow     = arrow(length = unit(0.20, "cm"), type = "closed"),
    colour    = "#555566",
    linewidth = 0.6,
    lineend   = "butt"
  ) +

  ## -- Stage header boxes (stages 1-6) ----------------------------------------
  geom_rect(
    data = hdr_solo,
    aes(xmin = xmin, xmax = xmax, ymin = ymin, ymax = ymax, fill = fill),
    colour = NA, show.legend = FALSE
  ) +
  ## Stage 7 header
  geom_rect(
    data = hdr_s7,
    aes(xmin = xmin, xmax = xmax, ymin = ymin, ymax = ymax),
    fill = COL_FUTURE, colour = NA
  ) +

  ## -- Item boxes (stages 1-6, solid) -----------------------------------------
  geom_rect(
    data = all_boxes[all_boxes$stage != 7L, ],
    aes(xmin = xmin, xmax = xmax, ymin = ymin, ymax = ymax, fill = fill),
    colour = "white", linewidth = 0.35, show.legend = FALSE
  ) +

  ## -- Stage 7 item boxes (dashed) --------------------------------------------
  geom_rect(
    data = all_boxes[all_boxes$stage == 7L, ],
    aes(xmin = xmin, xmax = xmax, ymin = ymin, ymax = ymax),
    fill = COL_FUTURE, colour = "white",
    linewidth = 0.5, linetype = "dashed", show.legend = FALSE
  ) +

  ## -- Item box labels --------------------------------------------------------
  geom_text(
    data = all_boxes,
    aes(x = xctr, y = yctr, label = label),
    colour = "white", size = 2.8, lineheight = 0.88,
    hjust = 0.5, fontface = "plain"
  ) +

  ## -- Stage header labels (1-6) ----------------------------------------------
  geom_text(
    data = hdr_solo,
    aes(x = xctr, y = yctr, label = label),
    colour = "white", size = 3.6, fontface = "bold", hjust = 0.5
  ) +
  ## Stage 7 header label
  annotate("text",
    x = hdr_s7$xctr, y = hdr_s7$yctr,
    label = "Stage 7: Future Directions",
    colour = "white", size = 3.6, fontface = "bold", hjust = 0.5
  ) +

  scale_fill_identity()

## -- Save ---------------------------------------------------------------------
out_dir <- file.path(
  "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel",
  "outputs", "figures"
)

ggsave(file.path(out_dir, "pipeline_diagram.png"), plot = p,
       width = 18, height = 14, dpi = 300, bg = "white")
ggsave(file.path(out_dir, "pipeline_diagram.pdf"), plot = p,
       width = 18, height = 14, bg = "white", device = "pdf")

cat("Saved pipeline_diagram.png and .pdf\n")
