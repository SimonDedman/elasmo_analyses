## viz_basin_barchart_per_coastline.R
## Companion to viz_basin_barchart.R. Standardises elasmobranch research effort
## per basin by the LENGTH OF COASTLINE in that basin.
##
## Why geometric (not subtraction of published figures):
##   Published coastline figures for oceans vs seas come from different sources
##   at different measurement resolutions (the "coastline paradox"), so they
##   cannot be added/subtracted. Instead we measure coastline directly from ONE
##   dataset (Natural Earth 1:50m coastline) clipped to mutually-exclusive basin
##   polygons (Natural Earth marine polys). This:
##     - splits Atlantic / Pacific into North & South consistently,
##     - keeps Mediterranean & Caribbean as their own basins (so they are NOT
##       double-counted inside the Atlantic), all at a single resolution.
##
## Output:
##   outputs/basin_coastline_lengths.csv             (audit table)
##   outputs/figures/basin_barchart_per_coastline_desc.{png,pdf}

suppressPackageStartupMessages({
  library(sf)
  library(rnaturalearth)
  library(tidyverse)
  library(scales)
  library(viridis)
})

# Planar GEOS for polygon ops: s2 rejects the (slightly invalid) NE marine
# polys. Coastline LENGTH is computed by haversine from lon/lat below, so it is
# independent of this choice; basin attribution only needs nearest-polygon.
sf_use_s2(FALSE)

base_dir <- "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"
fig_dir  <- file.path(base_dir, "outputs/figures")

# ---------------------------------------------------------------------------
# 1. Paper counts per basin (same data source as viz_basin_barchart.R)
# ---------------------------------------------------------------------------
df <- read_csv(file.path(base_dir, "outputs/viz_data.csv"),
               show_col_types = FALSE, guess_max = 5000)
b_cols <- names(df)[startsWith(names(df), "b_")]
papers <- tibble(
  basin_col = b_cols,
  papers    = sapply(b_cols, function(col) sum(df[[col]] == 1, na.rm = TRUE))
)

# ---------------------------------------------------------------------------
# 2. Map the 117 Natural Earth marine polygons -> the project's 9 basins
#    Codes match the b_ columns. Equatorial / Indo-Pacific assignments are
#    judgement calls (documented); edit freely and re-run.
# ---------------------------------------------------------------------------
basin_map <- c(
  # --- North Atlantic ---
  "North Atlantic Ocean"="b_north_atlantic", "Gulf of Mexico"="b_north_atlantic",
  "Bahía de Campeche"="b_north_atlantic", "North Sea"="b_north_atlantic",
  "Baltic Sea"="b_north_atlantic", "Gulf of Bothnia"="b_north_atlantic",
  "Gulf of Finland"="b_north_atlantic", "Norwegian Sea"="b_north_atlantic",
  "Bay of Biscay"="b_north_atlantic", "English Channel"="b_north_atlantic",
  "Irish Sea"="b_north_atlantic", "Bristol Channel"="b_north_atlantic",
  "Inner Sea"="b_north_atlantic", "Inner Seas"="b_north_atlantic",
  "Gulf of Maine"="b_north_atlantic", "Bay of Fundy"="b_north_atlantic",
  "Gulf of Saint Lawrence"="b_north_atlantic", "Chesapeake Bay"="b_north_atlantic",
  "Labrador Sea"="b_north_atlantic", "Sargasso Sea"="b_north_atlantic",
  "Gulf of Guinea"="b_north_atlantic", "Straits of Florida"="b_north_atlantic",
  # --- South Atlantic ---
  "South Atlantic Ocean"="b_south_atlantic", "Río de la Plata"="b_south_atlantic",
  "Golfo San Jorge"="b_south_atlantic",
  # --- North Pacific ---
  "North Pacific Ocean"="b_north_pacific", "Bering Sea"="b_north_pacific",
  "Gulf of Alaska"="b_north_pacific", "Cook Inlet"="b_north_pacific",
  "Bristol Bay"="b_north_pacific", "Shelikhova Gulf"="b_north_pacific",
  "Sea of Okhotsk"="b_north_pacific", "Sea of Japan"="b_north_pacific",
  "Yellow Sea"="b_north_pacific", "Bo Hai"="b_north_pacific",
  "East China Sea"="b_north_pacific", "South China Sea"="b_north_pacific",
  "Philippine Sea"="b_north_pacific", "Taiwan Strait"="b_north_pacific",
  "Korea Strait"="b_north_pacific", "Luzon Strait"="b_north_pacific",
  "Gulf of Tonkin"="b_north_pacific", "Gulf of Thailand"="b_north_pacific",
  "Golfo de California"="b_north_pacific", "Golfo de Panamá"="b_north_pacific",
  "Celebes Sea"="b_north_pacific", "Molucca Sea"="b_north_pacific",
  "Sulu Sea"="b_north_pacific",
  # --- South Pacific ---
  "South Pacific Ocean"="b_south_pacific", "Coral Sea"="b_south_pacific",
  "Great Barrier Reef"="b_south_pacific", "Tasman Sea"="b_south_pacific",
  "Bay of Plenty"="b_south_pacific", "Bismarck Sea"="b_south_pacific",
  "Solomon Sea"="b_south_pacific", "Banda Sea"="b_south_pacific",
  "Ceram Sea"="b_south_pacific", "Java Sea"="b_south_pacific",
  "Makassar Strait"="b_south_pacific",
  # --- Indian Ocean ---
  "INDIAN OCEAN"="b_indian_ocean", "Arabian Sea"="b_indian_ocean",
  "Bay of Bengal"="b_indian_ocean", "Andaman Sea"="b_indian_ocean",
  "Laccadive Sea"="b_indian_ocean", "Gulf of Aden"="b_indian_ocean",
  "Gulf of Oman"="b_indian_ocean", "Persian Gulf"="b_indian_ocean",
  "Red Sea"="b_indian_ocean", "Mozambique Channel"="b_indian_ocean",
  "Gulf of Kutch"="b_indian_ocean", "Gulf of Mannar"="b_indian_ocean",
  "Timor Sea"="b_indian_ocean", "Arafura Sea"="b_indian_ocean",
  "Gulf of Carpentaria"="b_indian_ocean", "Great Australian Bight"="b_indian_ocean",
  "Strait of Malacca"="b_indian_ocean", "Strait of Singapore"="b_indian_ocean",
  # --- Southern Ocean ---
  "SOUTHERN OCEAN"="b_southern_ocean", "Ross Sea"="b_southern_ocean",
  "Weddell Sea"="b_southern_ocean", "Amundsen Sea"="b_southern_ocean",
  "Bellingshausen Sea"="b_southern_ocean", "Drake Passage"="b_southern_ocean",
  "Scotia Sea"="b_southern_ocean",
  # --- Arctic Ocean ---
  "Arctic Ocean"="b_arctic_ocean", "Barents Sea"="b_arctic_ocean",
  "Kara Sea"="b_arctic_ocean", "Laptev Sea"="b_arctic_ocean",
  "Chukchi Sea"="b_arctic_ocean", "Beaufort Sea"="b_arctic_ocean",
  "Greenland Sea"="b_arctic_ocean", "White Sea"="b_arctic_ocean",
  "Baffin Bay"="b_arctic_ocean", "Davis Strait"="b_arctic_ocean",
  "Hudson Bay"="b_arctic_ocean", "Hudson Strait"="b_arctic_ocean",
  "James Bay"="b_arctic_ocean", "Ungava Bay"="b_arctic_ocean",
  "Melville Bay"="b_arctic_ocean", "Amundsen Gulf"="b_arctic_ocean",
  "Viscount Melville Sound"="b_arctic_ocean",
  "The North Western Passages"="b_arctic_ocean",
  # --- Mediterranean (incl. its sub-seas + Black Sea) ---
  "Mediterranean Sea"="b_mediterranean", "Adriatic Sea"="b_mediterranean",
  "Aegean Sea"="b_mediterranean", "Balearic Sea"="b_mediterranean",
  "Ionian Sea"="b_mediterranean", "Tyrrhenian Sea"="b_mediterranean",
  "Golfe du Lion"="b_mediterranean", "Strait of Gibraltar"="b_mediterranean",
  "Black Sea"="b_mediterranean",
  # --- Caribbean ---
  "Caribbean Sea"="b_caribbean", "Gulf of Honduras"="b_caribbean"
  # Dropped (not ocean coastline of interest): Caspian Sea, Amazon/Columbia/Yangtze Rivers
)

# ---------------------------------------------------------------------------
# 3. Build mutually-exclusive basin polygons & measure coastline within each
# ---------------------------------------------------------------------------
cat("Downloading Natural Earth layers...\n")
mp    <- ne_download(scale = 50, category = "physical",
                     type = "geography_marine_polys", returnclass = "sf")
coast <- ne_coastline(scale = 50, returnclass = "sf")

mp <- st_make_valid(mp)
mp$basin <- basin_map[as.character(mp$name)]
mp_used  <- mp[!is.na(mp$basin), ]            # ~110 individual polys, basin-tagged

# Densify the coastline so every segment is short, then attribute each short
# segment to the basin whose polygon it is nearest to.
cat("Segmentizing coastline & attributing to basins...\n")
# Densify in a metric CRS (EPSG:4087, equidistant cylindrical) so GEOS can
# segmentize without lwgeom/s2, then back to lon/lat for haversine lengths.
coast_d <- st_geometry(coast) |>
  st_transform(4087) |>
  st_segmentize(units::set_units(20, "km")) |>
  st_transform(4326)
cc      <- st_coordinates(coast_d)              # X, Y, L1 (feature id)

# consecutive vertex pairs within the same feature
n     <- nrow(cc)
keep  <- cc[-n, "L1"] == cc[-1, "L1"]
lon1 <- cc[-n, "X"][keep]; lat1 <- cc[-n, "Y"][keep]
lon2 <- cc[-1, "X"][keep]; lat2 <- cc[-1, "Y"][keep]
mlon <- (lon1 + lon2) / 2;  mlat <- (lat1 + lat2) / 2

# haversine segment length (km) — accurate, projection-independent
R <- 6371.0088
to_rad <- pi / 180
dlat <- (lat2 - lat1) * to_rad
dlon <- (lon2 - lon1) * to_rad
a <- sin(dlat/2)^2 + cos(lat1*to_rad) * cos(lat2*to_rad) * sin(dlon/2)^2
seg_km <- 2 * R * asin(pmin(1, sqrt(a)))

# segment midpoints -> nearest marine polygon -> basin
mid <- st_as_sf(data.frame(lon = mlon, lat = mlat),
                coords = c("lon", "lat"), crs = 4326)
idx  <- st_nearest_feature(mid, mp_used)
basin_of_seg <- mp_used$basin[idx]

# drop the Caspian Sea shoreline (landlocked; not in any basin but its coast
# would otherwise snap to the nearest sea). Caspian bbox: lon 46-55, lat 36-47.
casp <- mlon > 46 & mlon < 55 & mlat > 36 & mlat < 47
basin_of_seg[casp] <- NA

coastline_tbl <- tibble(basin_col = basin_of_seg, seg_km = seg_km) |>
  filter(!is.na(basin_col)) |>
  group_by(basin_col) |>
  summarise(coastline_km = sum(seg_km), .groups = "drop")

# ---------------------------------------------------------------------------
# 4. Combine, standardise, save audit table
# ---------------------------------------------------------------------------
clean_name <- function(x) x |> str_remove("^b_") |> str_replace_all("_", " ") |>
  str_to_title()

res <- papers |>
  left_join(coastline_tbl, by = "basin_col") |>
  mutate(label = clean_name(basin_col),
         papers_per_1000km = papers / (coastline_km / 1000)) |>
  arrange(desc(papers_per_1000km))

cat("\nBasin standardisation table:\n")
print(res |> mutate(coastline_km = round(coastline_km),
                     papers_per_1000km = round(papers_per_1000km, 1)) |>
        select(label, papers, coastline_km, papers_per_1000km))

write_csv(res |> select(basin = label, papers, coastline_km, papers_per_1000km),
          file.path(base_dir, "outputs/basin_coastline_lengths.csv"))

# ---------------------------------------------------------------------------
# 5. Plot (style matches viz_basin_barchart.R)
# ---------------------------------------------------------------------------
res <- res |> mutate(label = factor(label, levels = label))   # descending

theme_eea <- theme_minimal(base_size = 13) +
  theme(
    plot.background  = element_rect(fill = "white", colour = NA),
    panel.background = element_rect(fill = "white", colour = NA),
    panel.grid.major = element_line(colour = "grey92"),
    panel.grid.minor = element_blank(),
    plot.title       = element_text(face = "bold", size = 16),
    plot.subtitle    = element_text(colour = "grey40", size = 12),
    plot.caption     = element_text(colour = "grey45", size = 9, hjust = 0),
    axis.text.x      = element_text(angle = 30, hjust = 1),
    axis.title.x     = element_blank(),
    legend.position  = "none"
  )

p <- ggplot(res, aes(x = label, y = papers_per_1000km, fill = papers_per_1000km)) +
  geom_col() +
  geom_text(aes(label = comma(round(papers_per_1000km, 1))), vjust = -0.4, size = 3.6) +
  scale_fill_viridis_c(option = "mako", direction = -1) +
  scale_y_continuous(labels = comma, expand = expansion(mult = c(0, 0.08))) +
  labs(
    title    = "Elasmobranch research effort per unit coastline, by ocean basin",
    subtitle = "Papers per 1,000 km of coastline (multi-label, papers with PDFs)",
    y        = "Papers per 1,000 km coastline",
    caption  = paste0("Coastline measured from Natural Earth 1:50m coastline clipped to ",
                      "mutually-exclusive marine-basin polygons (single resolution, no double-counting).\n",
                      "Mediterranean & Caribbean are separate basins; Atlantic/Pacific split N/S. ",
                      "Equatorial / Indo-Pacific sea assignments are documented judgement calls.")
  ) +
  theme_eea

out_png <- file.path(fig_dir, "basin_barchart_per_coastline_desc.png")
out_pdf <- file.path(fig_dir, "basin_barchart_per_coastline_desc.pdf")
ggsave(out_png, p, width = 12, height = 7, dpi = 200, bg = "white")
ggsave(out_pdf, p, width = 12, height = 7, bg = "white")
cat("\nSaved:", out_png, "\n")
cat("Saved:", out_pdf, "\n")
