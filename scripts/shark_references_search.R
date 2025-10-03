#!/usr/bin/env Rscript
#
# Shark-References Automated Literature Search (R implementation)
# EEA 2025 Data Panel Project
#
# This script automates literature searches on shark-references.com
# and processes results into a structured database.
#
# Usage:
#   Rscript shark_references_search.R --test
#   Rscript shark_references_search.R --discipline "Movement_Spatial"
#   Rscript shark_references_search.R --all
#
# Author: Simon Dedman
# Date: 2025-10-02

# Load required libraries
suppressPackageStartupMessages({
  library(httr)
  library(jsonlite)
  library(RSQLite)
  library(dplyr)
  library(readr)
  library(stringr)
  library(rvest)
  library(lubridate)
})

# Search terms by discipline
SEARCH_TERMS <- list(
  Biology_Health = c(
    "+reproduct* +matur*",
    "+growth +age",
    "+telomere* +aging",
    "+stress +physiol*",
    "+parasit* +disease",
    "+endocrin* +hormone",
    "+metabol* +energetic*"
  ),
  Behaviour_Sensory = c(
    "+behav* +predation",
    "+vision +visual",
    "+electr* +sensory",
    "+olfact* +chemosens*",
    "+magnet* +navigation",
    "+social +aggregation",
    "+learning +cognition"
  ),
  Trophic_Ecology = c(
    "+stable +isotop*",
    "+diet +prey",
    "+trophic +level",
    "+food +web",
    "+stomach +content",
    "+energy +flow",
    "+niche +partition*"
  ),
  Genetics_Genomics = c(
    "+population +geneti*",
    "+genom* +sequenc*",
    "+eDNA +environmental",
    "+phylogeny +molecular",
    "+microsatellite +SNP",
    "+transcriptom* +gene",
    "+conservation +genetic*"
  ),
  Movement_Spatial = c(
    "+telemetry +acoustic",
    "+satellite +tracking",
    "+habitat +model*",
    "+home +range",
    "+SDM +distribution",
    "+spatial +ecology",
    "+migration +movement",
    "+circuit* +connectivity"
  ),
  Fisheries_Management = c(
    "+stock +assessment",
    "+fishery +CPUE",
    "+bycatch +discard*",
    "+mortality +fishing",
    "+catch +per +unit",
    "+surplus +production",
    "+harvest +strategy"
  ),
  Conservation_Policy = c(
    "+conservation +status",
    "+CITES +protection",
    "+MPA +marine +protected",
    "+policy +management",
    "+stakeholder +community",
    "+ecosystem +service*",
    "+human +dimension*"
  ),
  Data_Science = c(
    "+machine +learning",
    "+random +forest",
    "+neural +network",
    "+Bayesian +model*",
    "+AI +artificial",
    "+ensemble +model*",
    "+data +integration",
    "+GAM +generalized"
  )
)


#' Shark-References Searcher Class (R6 alternative using lists)
#'
#' Handler for Shark-References database searches
#'
#' @param delay Seconds between requests (default 10)
#' @param output_dir Directory for CSV outputs
#' @return List with search methods
shark_references_searcher <- function(delay = 10, output_dir = "./shark_refs_data") {

  # Create output directory
  if (!dir.exists(output_dir)) {
    dir.create(output_dir, recursive = TRUE)
  }

  base_url <- "https://shark-references.com/search"

  # Search method
  search <- function(query_fulltext, year_from = NULL, year_to = NULL) {

    # Prepare POST data
    body_data <- list(
      query_fulltext = query_fulltext,
      clicked_button = "export"
    )

    if (!is.null(year_from)) {
      body_data$year_from <- as.character(year_from)
    }
    if (!is.null(year_to)) {
      body_data$year_to <- as.character(year_to)
    }

    message(sprintf("[%s] Searching: %s", Sys.time(), query_fulltext))

    # Execute POST request
    response <- tryCatch({
      POST(
        url = base_url,
        body = body_data,
        encode = "form",
        timeout(30)
      )
    }, error = function(e) {
      warning(sprintf("Request failed: %s", e$message))
      return(NULL)
    })

    # Delay to avoid overwhelming server
    Sys.sleep(delay)

    return(response)
  }

  # Parse HTML results
  parse_html_results <- function(response) {

    if (is.null(response)) {
      return(data.frame())
    }

    # Parse HTML content
    html_content <- content(response, "text", encoding = "UTF-8")
    page <- read_html(html_content)

    # Extract reference items (adjust selectors based on actual HTML)
    # This is a placeholder - actual selectors need verification
    references <- data.frame()

    # Example parsing logic
    items <- html_nodes(page, ".literature-item")

    if (length(items) > 0) {
      references <- data.frame(
        title = html_text(html_nodes(items, "h3")),
        authors = html_text(html_nodes(items, ".authors")),
        year = html_text(html_nodes(items, ".year")),
        journal = html_text(html_nodes(items, ".journal")),
        stringsAsFactors = FALSE
      )
    } else {
      warning("No references found in HTML response")
    }

    return(references)
  }

  # Save response to file
  save_response <- function(response, filename) {

    if (is.null(response)) {
      warning("Cannot save NULL response")
      return(NULL)
    }

    # Determine file extension based on content type
    content_type <- headers(response)$`content-type` %||% ""

    if (grepl("csv", content_type, ignore.case = TRUE)) {
      filepath <- file.path(output_dir, paste0(filename, ".csv"))
    } else {
      filepath <- file.path(output_dir, paste0(filename, ".html"))
    }

    # Write content
    write_file(content(response, "text", encoding = "UTF-8"), filepath)

    message(sprintf("Saved to: %s", filepath))
    return(filepath)
  }

  # Return list of methods
  return(list(
    search = search,
    parse_html_results = parse_html_results,
    save_response = save_response,
    output_dir = output_dir,
    delay = delay
  ))
}


#' Shark-References Database Handler
#'
#' Handler for SQLite database operations
#'
#' @param db_path Path to SQLite database file
#' @return List with database methods
shark_references_database <- function(db_path = "shark_literature.db") {

  conn <- NULL

  # Connect and create schema
  connect <- function() {
    conn <<- dbConnect(SQLite(), db_path)
    create_schema()
    message(sprintf("Database initialized: %s", db_path))
  }

  # Create database schema
  create_schema <- function() {

    # Main references table
    dbExecute(conn, "
      CREATE TABLE IF NOT EXISTS shark_references (
        ref_id INTEGER PRIMARY KEY AUTOINCREMENT,
        search_term VARCHAR(255),
        discipline VARCHAR(100),
        method_category VARCHAR(100),
        authors TEXT,
        year INTEGER,
        title TEXT,
        journal VARCHAR(255),
        volume VARCHAR(50),
        issue VARCHAR(50),
        pages VARCHAR(50),
        doi VARCHAR(100),
        abstract TEXT,
        keywords TEXT,
        date_retrieved DATE,
        shark_ref_id VARCHAR(100),
        citation_count INTEGER,
        scholar_url TEXT,
        UNIQUE(doi, title)
      )
    ")

    # Search log table
    dbExecute(conn, "
      CREATE TABLE IF NOT EXISTS search_log (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        search_term VARCHAR(255),
        discipline VARCHAR(100),
        result_count INTEGER,
        timestamp DATETIME,
        status VARCHAR(50),
        error_message TEXT
      )
    ")

    # Create indexes
    dbExecute(conn, "
      CREATE INDEX IF NOT EXISTS idx_discipline
      ON shark_references(discipline)
    ")
    dbExecute(conn, "
      CREATE INDEX IF NOT EXISTS idx_year
      ON shark_references(year)
    ")
    dbExecute(conn, "
      CREATE INDEX IF NOT EXISTS idx_method
      ON shark_references(method_category)
    ")
  }

  # Import references to database
  import_references <- function(df, discipline, search_term) {

    if (nrow(df) == 0) {
      warning("Empty data frame, nothing to import")
      return()
    }

    # Add metadata columns
    df$discipline <- discipline
    df$search_term <- search_term
    df$date_retrieved <- as.character(Sys.Date())

    # Write to database
    tryCatch({
      dbWriteTable(conn, "shark_references", df,
                   append = TRUE, row.names = FALSE)
      message(sprintf("Imported %d references for %s", nrow(df), discipline))
    }, error = function(e) {
      warning(sprintf("Some duplicates skipped: %s", e$message))
    })
  }

  # Log search to database
  log_search <- function(search_term, discipline, result_count,
                        status = "success", error_message = NULL) {

    log_entry <- data.frame(
      search_term = search_term,
      discipline = discipline,
      result_count = result_count,
      timestamp = as.character(Sys.time()),
      status = status,
      error_message = ifelse(is.null(error_message), NA, error_message),
      stringsAsFactors = FALSE
    )

    dbWriteTable(conn, "search_log", log_entry,
                 append = TRUE, row.names = FALSE)
  }

  # Deduplicate database
  deduplicate <- function() {

    result <- dbExecute(conn, "
      DELETE FROM shark_references
      WHERE ref_id NOT IN (
        SELECT MIN(ref_id)
        FROM shark_references
        GROUP BY COALESCE(doi, ''), COALESCE(title, '')
      )
    ")

    message(sprintf("Removed %d duplicate entries", result))
  }

  # Get statistics
  get_statistics <- function() {

    stats <- list()

    # Total references
    stats$total_refs <- dbGetQuery(conn,
      "SELECT COUNT(*) as count FROM shark_references")$count

    # By discipline
    stats$by_discipline <- dbGetQuery(conn, "
      SELECT discipline, COUNT(*) as count
      FROM shark_references
      GROUP BY discipline
      ORDER BY count DESC
    ")

    # By year
    stats$by_year <- dbGetQuery(conn, "
      SELECT year, COUNT(*) as count
      FROM shark_references
      WHERE year IS NOT NULL
      GROUP BY year
      ORDER BY year DESC
      LIMIT 20
    ")

    # Search log summary
    stats$search_log <- dbGetQuery(conn, "
      SELECT discipline, COUNT(*) as searches,
             SUM(result_count) as total_results,
             AVG(result_count) as avg_results
      FROM search_log
      WHERE status = 'success'
      GROUP BY discipline
    ")

    return(stats)
  }

  # Close database
  close_db <- function() {
    if (!is.null(conn)) {
      dbDisconnect(conn)
    }
  }

  # Return list of methods
  return(list(
    connect = connect,
    import_references = import_references,
    log_search = log_search,
    deduplicate = deduplicate,
    get_statistics = get_statistics,
    close = close_db,
    conn = function() conn
  ))
}


#' Run batch searches across disciplines
#'
#' @param disciplines Character vector of discipline names (NULL = all)
#' @param searcher Searcher object
#' @param database Database object
run_batch_search <- function(disciplines = NULL, searcher = NULL,
                             database = NULL) {

  if (is.null(searcher)) {
    searcher <- shark_references_searcher()
  }
  if (is.null(database)) {
    database <- shark_references_database()
    database$connect()
  }

  # Select disciplines
  if (is.null(disciplines)) {
    disciplines <- names(SEARCH_TERMS)
  } else if (length(disciplines) == 1 && disciplines == "all") {
    disciplines <- names(SEARCH_TERMS)
  }

  message(sprintf("Starting batch search for %d disciplines",
                  length(disciplines)))

  for (discipline in disciplines) {

    if (!discipline %in% names(SEARCH_TERMS)) {
      warning(sprintf("Unknown discipline: %s", discipline))
      next
    }

    message(sprintf("\n%s", strrep("=", 60)))
    message(sprintf("Discipline: %s", discipline))
    message(sprintf("%s", strrep("=", 60)))

    terms <- SEARCH_TERMS[[discipline]]

    for (i in seq_along(terms)) {
      term <- terms[i]
      message(sprintf("\n[%d/%d] Search term: %s", i, length(terms), term))

      tryCatch({
        # Execute search
        response <- searcher$search(term)

        if (is.null(response)) {
          database$log_search(term, discipline, 0, "error", "Request failed")
          next
        }

        # Save raw response
        filename <- sprintf("%s_%02d", discipline, i)
        filepath <- searcher$save_response(response, filename)

        # Log success (parsing to be implemented)
        database$log_search(term, discipline, 0, "success")

        message(sprintf("Completed: %s", term))

      }, error = function(e) {
        warning(sprintf("Error processing %s: %s", term, e$message))
        database$log_search(term, discipline, 0, "error", e$message)
      })
    }
  }

  message("\nBatch search completed")

  # Show statistics
  stats <- database$get_statistics()
  message(sprintf("\nTotal references: %d", stats$total_refs))
  message("\nBy discipline:")
  print(stats$by_discipline)
}


#' Test single search
test_single_search <- function() {

  message("Running test search...")

  searcher <- shark_references_searcher(delay = 5)
  database <- shark_references_database("test_shark_literature.db")
  database$connect()

  # Test with simple query
  test_term <- "+telemetry +acoustic"
  response <- searcher$search(test_term)

  if (!is.null(response)) {
    filename <- "test_search"
    filepath <- searcher$save_response(response, filename)
    message(sprintf("Test search saved to: %s", filepath))
    message("Please inspect this file to understand the response format")

    database$log_search(test_term, "TEST", 0, "success")
  } else {
    warning("Test search failed")
    database$log_search(test_term, "TEST", 0, "error", "Request returned NULL")
  }

  database$close()
}


#' Main function
main <- function() {

  # Parse command line arguments
  args <- commandArgs(trailingOnly = TRUE)

  # Default parameters
  test_mode <- FALSE
  discipline <- NULL
  all_disciplines <- FALSE
  delay <- 10
  output_dir <- "./shark_refs_data"
  db_path <- "shark_literature.db"

  # Parse arguments
  i <- 1
  while (i <= length(args)) {
    arg <- args[i]

    if (arg == "--test") {
      test_mode <- TRUE
    } else if (arg == "--all") {
      all_disciplines <- TRUE
    } else if (arg == "--discipline") {
      i <- i + 1
      discipline <- args[i]
    } else if (arg == "--delay") {
      i <- i + 1
      delay <- as.numeric(args[i])
    } else if (arg == "--output-dir") {
      i <- i + 1
      output_dir <- args[i]
    } else if (arg == "--database") {
      i <- i + 1
      db_path <- args[i]
    } else if (arg == "--help") {
      cat("
Shark-References Automated Literature Search (R)

Usage:
  Rscript shark_references_search.R [options]

Options:
  --test              Run test search only
  --all               Search all disciplines
  --discipline NAME   Search specific discipline
  --delay N           Delay between requests (default: 10 seconds)
  --output-dir DIR    Output directory (default: ./shark_refs_data)
  --database PATH     Database file path (default: shark_literature.db)
  --help              Show this help message

Examples:
  Rscript shark_references_search.R --test
  Rscript shark_references_search.R --discipline Movement_Spatial
  Rscript shark_references_search.R --all --delay 15
")
      return()
    }

    i <- i + 1
  }

  # Execute based on arguments
  if (test_mode) {
    test_single_search()
  } else if (all_disciplines) {
    searcher <- shark_references_searcher(delay = delay,
                                          output_dir = output_dir)
    database <- shark_references_database(db_path)
    database$connect()
    run_batch_search(disciplines = "all", searcher = searcher,
                    database = database)
    database$close()
  } else if (!is.null(discipline)) {
    searcher <- shark_references_searcher(delay = delay,
                                          output_dir = output_dir)
    database <- shark_references_database(db_path)
    database$connect()
    run_batch_search(disciplines = discipline, searcher = searcher,
                    database = database)
    database$close()
  } else {
    cat("No action specified. Use --help for usage information.\n")
  }
}


# Run main function if script is executed directly
if (!interactive()) {
  main()
}
