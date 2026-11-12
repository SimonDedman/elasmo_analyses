# Nine ocean basins for the Species Atlas, dissolved from Natural Earth 1:50m named sea polygons
# (docs/species_atlas/basins.json). Basin names match the b_* / bd_* columns.
# Run: Rscript scripts/study_sites/export_basins_geojson.R
# INFERRED conventions, chosen to match the b_* term lists: the Gulf of Mexico sits with the Caribbean; the
# Black Sea and Strait of Gibraltar with the Mediterranean; Hudson Bay with the Arctic; the Indonesian seas are
# split north and south of Sulawesi; the Gulf of Guinea goes to the South Atlantic.
suppressMessages(library(sf))
sf_use_s2(FALSE)
m <- rnaturalearth::ne_download(scale = 50, type = "geography_marine_polys", category = "physical",
                               destdir = "outputs/study_sites/ne_cache", returnclass = "sf")
basin <- list(
  north_atlantic = c("North Atlantic Ocean", "Baltic Sea", "Bay of Biscay", "Bay of Fundy", "Bristol Channel", "Chesapeake Bay",
                     "Davis Strait", "English Channel", "Gulf of Bothnia", "Gulf of Finland", "Gulf of Maine", "Gulf of Saint Lawrence",
                     "Irish Sea", "Inner Seas", "Labrador Sea", "North Sea", "Norwegian Sea", "Sargasso Sea"),
  caribbean = c("Caribbean Sea", "Gulf of Mexico", "Bahía de Campeche", "Gulf of Honduras", "Straits of Florida"),
  mediterranean = c("Mediterranean Sea", "Adriatic Sea", "Aegean Sea", "Balearic Sea", "Golfe du Lion", "Ionian Sea",
                    "Tyrrhenian Sea", "Black Sea", "Strait of Gibraltar"),
  south_atlantic = c("South Atlantic Ocean", "Río de la Plata", "Golfo San Jorge", "Gulf of Guinea"),
  indian_ocean = c("INDIAN OCEAN", "Andaman Sea", "Arabian Sea", "Bay of Bengal", "Great Australian Bight", "Gulf of Aden",
                   "Gulf of Kutch", "Gulf of Mannar", "Gulf of Oman", "Laccadive Sea", "Mozambique Channel", "Persian Gulf",
                   "Red Sea", "Strait of Malacca", "Timor Sea"),
  north_pacific = c("North Pacific Ocean", "Bering Sea", "Bo Hai", "Bristol Bay", "Celebes Sea", "Cook Inlet", "East China Sea",
                    "Golfo de California", "Golfo de Panamá", "Gulf of Alaska", "Gulf of Thailand", "Gulf of Tonkin", "Inner Sea",
                    "Korea Strait", "Luzon Strait", "Philippine Sea", "Sea of Japan", "Sea of Okhotsk", "Shelikhova Gulf",
                    "South China Sea", "Sulu Sea", "Taiwan Strait", "Yellow Sea", "Strait of Singapore", "Molucca Sea", "Makassar Strait"),
  south_pacific = c("South Pacific Ocean", "Banda Sea", "Bay of Plenty", "Bismarck Sea", "Ceram Sea", "Coral Sea", "Great Barrier Reef",
                    "Gulf of Carpentaria", "Java Sea", "Solomon Sea", "Tasman Sea", "Arafura Sea"),
  southern_ocean = c("SOUTHERN OCEAN", "Amundsen Sea", "Bellingshausen Sea", "Ross Sea", "Weddell Sea", "Scotia Sea", "Drake Passage"),
  arctic_ocean = c("Arctic Ocean", "Amundsen Gulf", "Baffin Bay", "Barents Sea", "Beaufort Sea", "Chukchi Sea", "Greenland Sea",
                   "Hudson Bay", "Hudson Strait", "James Bay", "Kara Sea", "Laptev Sea", "Melville Bay", "The North Western Passages",
                   "Ungava Bay", "Viscount Melville Sound", "White Sea")
)
not_sea <- c("Amazon River", "Columbia River", "Yangtze River", "Caspian Sea")
lookup <- stack(basin)
unmapped <- setdiff(m$name, c(lookup$values, not_sea))
if (length(unmapped)) stop("unmapped sea names: ", paste(unmapped, collapse = ", "))
missing <- setdiff(lookup$values, m$name)
if (length(missing)) stop("names in the table but not in Natural Earth: ", paste(missing, collapse = ", "))
m <- m[m$name %in% lookup$values, ]
m$basin <- as.character(lookup$ind[match(m$name, lookup$values)])
m <- suppressWarnings(st_make_valid(m))
b <- suppressMessages(aggregate(m["basin"], by = list(basin = m$basin), FUN = function(x) x[1]))[, "basin"]
b <- suppressWarnings(st_simplify(b, dTolerance = 0.12, preserveTopology = TRUE))
out <- "docs/species_atlas/basins.json"
if (file.exists(out)) file.remove(out)
st_write(b, out, driver = "GeoJSON", layer_options = "COORDINATE_PRECISION=2", quiet = TRUE)
cat("OK", nrow(b), "basins from", nrow(m), "sea polygons,", round(file.size(out) / 1024), "KB ->", out, "\n")
