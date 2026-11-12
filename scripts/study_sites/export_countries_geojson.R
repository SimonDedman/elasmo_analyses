# Natural Earth 1:50m countries, simplified, for the coarse Species Atlas (docs/species_atlas/countries.json).
# 50m, not 110m: 110m drops the small island states (Maldives, Seychelles, Mauritius) that matter for shark work.
# Run: Rscript scripts/study_sites/export_countries_geojson.R
library(sf)
sf_use_s2(FALSE)
w <- rnaturalearth::ne_countries(scale = 50, returnclass = "sf")
w <- w[, c("admin", "name", "name_long", "adm0_a3", "iso_a3", "label_x", "label_y")]
w <- suppressWarnings(st_simplify(w, dTolerance = 0.08, preserveTopology = TRUE))
w <- w[!st_is_empty(w), ]
out <- "docs/species_atlas/countries.json"
if (file.exists(out)) file.remove(out)
st_write(w, out, driver = "GeoJSON", layer_options = "COORDINATE_PRECISION=2", quiet = TRUE)
cat("OK", nrow(w), "countries,", round(file.size(out) / 1024), "KB ->", out, "\n")
