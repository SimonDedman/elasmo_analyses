## viz_pipeline_diagram.R
## Shark Oracle / EEA Data Panel: project pipeline diagram, 16:9 slide format.
## Numbers come from outputs/corpus_stats.json (report_corpus_stats.py), except
## those marked DB (database/conference_abstracts.db, newer than the json) and
## the validation label counts (gold/silver; 2026-10-07 session figures).
## Output: outputs/figures/pipeline_diagram.{png,pdf}  (3200 x 1800 px)

library(ggplot2)
library(jsonlite)

ROOT <- "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"
st <- fromJSON(file.path(ROOT, "outputs/corpus_stats.json"))
fmt <- function(x) format(x, big.mark = ",", scientific = FALSE, trim = TRUE)

N_PAPERS   <- st$parquet$papers
N_COLS     <- st$parquet$columns
N_PDFS     <- st$pdfs$pdf_files_on_disk
N_AUTHORS  <- st$authors$unique_authors
N_EVID     <- st$evidence$rows
N_TECH     <- st$techniques$techniques
N_ORACLE   <- st$rag$papers_indexed
N_ABS      <- 23491   # DB: database/conference_abstracts.db (json lags: 23,408)
N_MEET     <- 124     # DB
N_GOLD     <- 190     # expert labels
N_SILVER   <- 48306   # Fable silver labels
N_TOPICS   <- 22

## Palette: stage colours (kept from earlier versions)
COL <- c(src = "#2E86AB", acq = "#2E9E77", ext = "#C0392B",
         enr = "#7B2D8B", val = "#D4711A", out = "#1A7A6E")
COL_BG <- "#FFFFFF"

cols <- list(
  list(id = "src", title = "1  Sources", items = c(
    paste0("Shark-References\nmonthly sync\n(", fmt(N_PAPERS), " records)"),
    "Coauthor libraries +\ndrop folders",
    paste0("Conference abstract\nbooks (", N_MEET, " meetings)"),
    "OpenAlex\n(authors, citations)",
    "NamSor\n(gender, origin)",
    "Sharkipedia traits +\nIUCN Red List",
    "Unpaywall, SciMago\n(OA, journal rank)")),
  list(id = "acq", title = "2  Acquire, Extract", items = c(
    paste0("PDF library\n(", fmt(N_PDFS), " PDFs)"),
    "Download hub:\nteam push to fill gaps",
    "PDF id map\n(literature_id to file)",
    "Text extraction +\nkeyword scoring",
    paste0(fmt(N_COLS), " schema columns\nin 8 groups"),
    paste0("Evidence audit trail\n(", fmt(round(N_EVID, -3)), " rows)"))),
  list(id = "enr", title = "3  Enrich", items = c(
    paste0(fmt(N_AUTHORS), "\nunique authors"),
    "Gender: NamSor\n(Genderize retired)",
    "Institution country,\nNorth / South",
    "Study country,\nocean basin",
    paste0(N_TECH, " analytical\ntechniques"),
    "Species, bycatch,\nlife-history links")),
  list(id = "val", title = "4  Validate", items = c(
    paste0(N_GOLD, " expert\n(gold) labels"),
    paste0(fmt(N_SILVER), " Fable\n(silver) labels"),
    "Rule-improvement\nloop: score, propose,\nretest",
    "Per-discipline\nreview pages",
    "Per-author\nvalidation pages")),
  list(id = "out", title = "5  Outputs", items = c(
    paste0("Shark Oracle: cited\nanswers, ", fmt(N_ORACLE), "\npapers indexed"),
    paste0("Abstracts browser\n(", fmt(N_ABS), " abstracts)"),
    paste0(N_TOPICS, " topic expert\nreview pages"),
    "Researcher\nnetwork atlas",
    "Download hub +\nremaining papers",
    paste0("Enriched parquet,\n118+ figures")))
)

## -- Geometry (canvas 32 x 18 units = 16:9) -----------------------------------
W <- 32; H <- 18
NC <- length(cols)
GAP <- 0.9                          # gap between columns (arrows live here)
MX <- 0.15; MY <- 0.15
CW <- (W - 2 * MX - (NC - 1) * GAP) / NC
TITLE_H <- 1.55
HDR_H <- 1.0
BGAP <- 0.12
y_top <- H - MY - TITLE_H
y_bot <- MY

boxes <- list(); hdrs <- list()
for (i in seq_len(NC)) {
  c <- cols[[i]]; n <- length(c$items)
  x0 <- MX + (i - 1) * (CW + GAP)
  hdrs[[i]] <- data.frame(label = c$title, xmin = x0, xmax = x0 + CW,
                          ymin = y_top - HDR_H, ymax = y_top, fill = COL[[c$id]])
  avail <- (y_top - HDR_H - BGAP) - y_bot
  bh <- (avail - (n - 1) * BGAP) / n
  tops <- (y_top - HDR_H - BGAP) - (seq_len(n) - 1) * (bh + BGAP)
  boxes[[i]] <- data.frame(label = c$items, xmin = x0, xmax = x0 + CW,
                           ymin = tops - bh, ymax = tops, fill = COL[[c$id]])
}
boxes <- do.call(rbind, boxes); hdrs <- do.call(rbind, hdrs)
boxes$xc <- (boxes$xmin + boxes$xmax) / 2; boxes$yc <- (boxes$ymin + boxes$ymax) / 2
hdrs$xc  <- (hdrs$xmin + hdrs$xmax) / 2;   hdrs$yc  <- (hdrs$ymin + hdrs$ymax) / 2

## Column-to-column arrows, centred in each gap, at mid body height
ymid <- (y_top - HDR_H + y_bot) / 2
arrows <- data.frame(
  x = hdrs$xmax[-NC] + 0.08, xend = hdrs$xmin[-1] - 0.08, y = ymid, yend = ymid)
## Feedback arrow: Validate -> Extract (rule loop), drawn above the columns
fb <- data.frame(x = hdrs$xc[4], xend = hdrs$xc[2],
                 y = y_top + 0.38, yend = y_top + 0.38)

sub <- paste0(fmt(N_PAPERS), " papers  |  ", fmt(N_PDFS), " PDFs  |  ",
              fmt(N_ORACLE), " in the Oracle index  |  ", fmt(N_ABS),
              " abstracts from ", N_MEET, " meetings  |  ", N_TOPICS, " topics")

p <- ggplot() +
  theme_void() +
  theme(plot.margin = margin(0, 0, 0, 0),
        plot.background = element_rect(fill = COL_BG, colour = NA)) +
  coord_cartesian(xlim = c(0, W), ylim = c(0, H), expand = FALSE) +
  annotate("text", x = W / 2, y = H - MY - 0.45, label = "Shark Oracle: data pipeline",
           size = 11, fontface = "bold", colour = "#081E3F") +
  annotate("text", x = W / 2, y = H - MY - 1.12, label = sub,
           size = 6.6, colour = "#B6862C", fontface = "bold") +
  geom_segment(data = arrows, aes(x = x, xend = xend, y = y, yend = yend),
               arrow = arrow(length = unit(0.42, "cm"), type = "closed"),
               colour = "#081E3F", linewidth = 2.2) +
  geom_rect(data = hdrs, aes(xmin = xmin, xmax = xmax, ymin = ymin, ymax = ymax, fill = fill),
            show.legend = FALSE) +
  geom_rect(data = boxes, aes(xmin = xmin, xmax = xmax, ymin = ymin, ymax = ymax, fill = fill),
            colour = "white", linewidth = 0.4, show.legend = FALSE) +
  geom_text(data = boxes, aes(x = xc, y = yc, label = label),
            colour = "white", size = 6.5, lineheight = 0.92) +
  geom_text(data = hdrs, aes(x = xc, y = yc, label = label),
            colour = "white", size = 7.4, fontface = "bold") +
  scale_fill_identity()

out_dir <- file.path(ROOT, "outputs", "figures")
ggsave(file.path(out_dir, "pipeline_diagram.png"), p, width = 16, height = 9, dpi = 200, bg = "white")
ggsave(file.path(out_dir, "pipeline_diagram.pdf"), p, width = 16, height = 9, bg = "white", device = "pdf")
cat("Saved pipeline_diagram.png and .pdf\n")
