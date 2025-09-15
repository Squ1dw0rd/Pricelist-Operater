# Recommended Improvements for Supplier Price List Consolidation Tool

This document outlines potential enhancements and changes to the existing project based on a review of the current implementation (Phases 1-8 completed). The suggestions aim to improve performance, usability, maintainability, and future-proofing while preserving the core local, Python-based design. These are prioritized by impact and feasibility.

## 1. Adopt Polars Over Pandas for Core Data Processing
**Rationale**: Pandas is reliable but can be memory-intensive for large datasets (e.g., 59,890+ products). Polars offers faster processing and lower memory usage, especially beneficial for Phase 9 optimizations on medium-powered PCs.

**Changes**:
- Replace pandas with polars in `src/file_parsers.py`, `src/column_mapper.py`, and `src/main.py` for data manipulation.
- Update `requirements.txt` to include `polars` and remove `pandas` if not needed elsewhere.
- Refactor DataFrame operations to use Polars' lazy evaluation where possible.
- Test thoroughly with existing supplier files to ensure compatibility.

**Impact**: High (performance); Effort: Medium (refactoring required).

## 2. Incorporate a Simple Local Web UI (FastAPI + Jinja2)
**Rationale**: Pure CLI is functional but less intuitive for non-technical users. A local web interface would improve accessibility for file uploads, configuration, and result previews without external dependencies.

**Changes**:
- Add FastAPI and Jinja2 to `requirements.txt`.
- Create new module `src/web_ui.py` for the web server (runs on localhost).
- Integrate with existing CLI logic: Use shared functions from `src/main.py` for processing.
- Add basic HTML templates in `templates/` for upload, config management, and output preview.
- Update `src/cli.py` to optionally launch the web UI.
- Ensure no external network access; keep fully local.

**Impact**: High (usability); Effort: Medium (new module, but leverages existing code).

## 3. Enhance PDF Handling with OCR Fallback
**Rationale**: pdfplumber fails on image-based PDFs (e.g., POINTTECH). Adding OCR would improve parsing success rates.

**Changes**:
- Add `pytesseract` and `Pillow` to `requirements.txt`.
- Modify `src/file_parsers.py` PDF parser to attempt OCR extraction if pdfplumber yields empty results.
- Log OCR usage and results for transparency.
- Test with problematic PDFs and document limitations.

**Impact**: Medium (robustness); Effort: Low (extension of existing parser).

## 4. Database Integration for Intermediate Storage (SQLite)
**Rationale**: Enables better querying, debugging, and lays groundwork for historical tracking (Phase 13).

**Changes**:
- Add `sqlite3` (built-in) or `sqlalchemy` for ORM.
- Create `src/database.py` for schema (tables for parsed data, validations, sessions).
- Modify processing pipeline to store intermediate results in DB.
- Add queries for reporting and validation checks.
- Ensure DB is local and cleaned up after processing.

**Impact**: Medium (maintainability); Effort: Medium (new module).

## 5. Prioritize Performance Profiling from Phase 1
**Rationale**: Early profiling prevents bottlenecks; integrate into development workflow.

**Changes**:
- Add `cProfile`, `memory_profiler` to dev dependencies.
- Create `scripts/profile.py` for automated profiling during tests.
- Profile key functions (parsing, mapping, Excel generation) in CI/testing.
- Use results to guide optimizations (e.g., batch processing).

**Impact**: Medium (performance); Effort: Low (tool integration).

## 6. Expand Configuration with AI-Assisted Mapping Suggestions
**Rationale**: Reduces setup time for new suppliers by suggesting mappings.

**Changes**:
- Add `scikit-learn` or simple heuristics to `requirements.txt`.
- Enhance `src/column_mapper.py` with a suggestion engine based on existing configs.
- Integrate into CLI/web UI for new supplier onboarding.
- Train on historical mappings for better accuracy.

**Impact**: Medium (usability); Effort: Medium (ML integration).

## 7. Documentation and Onboarding Enhancements
**Rationale**: Addresses partial technical docs; improves user adoption.

**Changes**:
- Use MkDocs or Sphinx for interactive docs.
- Embed docs in app (accessible via CLI/web).
- Add video tutorials or step-by-step wizards.
- Update `docs/README.md` with new sections.

**Impact**: Low-Medium (adoption); Effort: Low (content creation).

## 8. Security and Portability Improvements
**Rationale**: Ensures robustness across environments.

**Changes**:
- Add input validation in parsers to prevent malicious files.
- Test PyInstaller builds on multiple Windows versions.
- Consider Docker for containerized deployment (local only).
- Update `requirements.txt` and docs accordingly.

**Impact**: Low (reliability); Effort: Low.

## Implementation Priority
1. **Polars Migration** (immediate performance gain).
2. **Web UI** (major usability boost).
3. **OCR for PDFs** (fixes known issue).
4. **Database Integration** (enables future features).
5. **Profiling** (ongoing).
6. **Mapping Suggestions** (post-UI).
7. **Docs/Security** (polish).

These changes build on the strong foundation of Phases 1-8. Start with Polars and Web UI for the most impact, testing incrementally with existing supplier data.