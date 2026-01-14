# LLM Integration Documentation

This folder contains documentation for integrating Large Language Model (LLM) capabilities with the elasmo_analyses corpus, enabling conversational interaction with the shark science knowledge base.

## Overview

The goal is to create an AI-powered interface that allows researchers to "talk to" the 13,000+ paper corpus, asking questions like:
- "What techniques are used for age determination in deep-sea sharks?"
- "Which countries have published most on acoustic telemetry?"
- "Show me papers combining eDNA and stable isotope analysis"

## Documentation

### Strategy & Options
- **[notebooklm_alternatives_summary.md](notebooklm_alternatives_summary.md)** - Comprehensive comparison of:
  - Google NotebookLM (limitations for large corpora)
  - Open-source local alternatives (AnythingLLM, PrivateGPT, Open WebUI)
  - Custom RAG pipeline recommendations (Qdrant + Ollama)
  - Hardware requirements and scaling considerations

## Recommended Approach

For a corpus of 13,000+ scientific PDFs:

### Quick Start (Prototyping)
1. **AnythingLLM** - Desktop app with built-in RAG
2. **Ollama** - Local LLM runtime (Llama 3.1, Qwen2.5)
3. Import PDFs in batches, start querying

### Production-Ready (Scalable)
```
Docling (PDF extraction) → Embeddings (nomic-embed-text) → Qdrant (vector DB) → Ollama + Open WebUI (chat interface)
```

Benefits:
- Full metadata filtering (species, technique, year, nation)
- Scales to millions of documents
- 100% local and private
- No subscription costs

## Integration with Existing Database

The elasmo_analyses SQLite database contains:
- Paper metadata (authors, year, DOI, title)
- Technique assignments per paper
- Discipline classifications
- Geographic data (countries, ocean basins)
- Species mentions

This structured data can be combined with RAG to enable:
- Filtered searches ("papers about hammerheads using telemetry")
- Structured answers with citations
- Trend analysis queries

## Future Development

- [ ] Prototype with AnythingLLM
- [ ] Evaluate retrieval quality
- [ ] Build custom Qdrant pipeline if needed
- [ ] Add metadata filtering
- [ ] Create web interface for community access

---

*Created: 2026-01-14*
