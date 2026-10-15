# Changelog

## 2026-10-16 - Production remaster

- Replaced the monolithic Streamlit script with explicit data, analytics, chart, model, error, configuration, and presentation modules.
- Added bounded file and row limits before expensive parsing to reduce denial-of-service and memory exhaustion risk.
- Added strict UTF-8 CSV schema validation, duplicate-header detection, type coercion, sentiment normalization, data-quality reporting, and safe failures.
- Made the cache depend on the dataset path, modification timestamp, and size so replacing the CSV invalidates stale results.
- Added literal search, sentiment, confidence, and date filters using vectorized Pandas operations.
- Added responsive executive metrics, sentiment distribution, time trend, confidence distribution, engagement analytics, top comments, and paginated exploration.
- Added formula-injection protection to the controlled CSV download and disabled Streamlit's unsanitized built-in table export.
- Added production Streamlit settings for generic browser errors, XSRF and CORS protection, bounded messages, viewer-only controls, and disabled telemetry.
- Reduced `app.py` to a stable entry point and removed fragile current-working-directory path loading.
- Pinned direct runtime dependencies to known versions compatible with Python 3.10+.
