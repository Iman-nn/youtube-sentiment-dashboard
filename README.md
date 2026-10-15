# YouTube Sentiment Intelligence Dashboard

A production-oriented Streamlit dashboard for exploring sentiment labels that were generated upstream for public YouTube comments. The application does not call Hugging Face or YouTube at runtime; it reads an already analyzed CSV and presents validated, filterable analytics.

Live deployment: <https://youtube-sentiment-dashboard-imann-nn.streamlit.app/>

## Features

- Executive sentiment, confidence, likes, and positive-share metrics.
- Sentiment mix, time-series, confidence-distribution, and engagement charts.
- Literal text search plus sentiment, confidence, and publication-date filters.
- Paginated comment explorer and a controlled CSV export.
- Data-quality dashboard for invalid dates, likes, confidence, labels, and oversized text.
- Cache invalidation when the source file timestamp or size changes.
- Safe browser errors with an event reference while details remain in server logs.

## Architecture

```text
app.py                 Streamlit entry point
src/config.py          Paths, limits, schema, labels, and colors
src/data.py            Bounded ingestion, validation, normalization, safe export
src/analytics.py       Pure vectorized filtering and aggregation
src/charts.py          Plotly figure factories
src/dashboard.py       UI composition, cache, and error boundary
src/models.py          Typed data-transfer objects
src/errors.py          User-safe application exceptions
.streamlit/config.toml Production UI and transport settings
```

The presentation layer depends on pure analytics and a bounded data adapter. This keeps business calculations reusable and prevents Streamlit-specific state from spreading through the project.

## Local setup

Python 3.10 or newer is required.

```powershell
Set-Location C:\laragon\www\youtube-sentiment-dashboard
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
streamlit run app.py
```

The default source is `smart_analyzed_comments_OqEc_169ywY.csv`. To use a different server-controlled CSV, set an environment variable before startup:

```powershell
$env:SENTIMENT_DATA_FILE = 'C:\secure-data\analyzed-comments.csv'
streamlit run app.py
```

Do not expose the source-path setting as a public UI field. It is intentionally controlled by the server operator.

## Required CSV schema

| Column | Normalized use |
| --- | --- |
| `Author` | Display name, limited to 200 characters |
| `Comment Text` | Original comment, limited to 10,000 characters |
| `Likes` | Non-negative whole number; invalid values become zero and are reported |
| `Published At` | Parsed as a UTC timestamp; invalid values are reported |
| `Cleaned Text` | Analysis/display text with original text as a fallback |
| `Sentiment Label` | `POSITIVE`, `NEGATIVE`, or `NEUTRAL`; other values become `UNKNOWN` |
| `Confidence Score` | Number from 0 to 1; invalid values are excluded from confidence metrics |

Files must be UTF-8 CSV with unique headers. The application rejects files over 50 MiB or 250,000 rows before rendering misleading partial analytics. For larger workloads, move the source to a database or analytical store and query aggregated, paginated results rather than increasing these limits indefinitely.

## Security posture

- Streamlit CORS and XSRF protections remain enabled with a `SameSite=Lax` XSRF cookie.
- Browser exception details and developer toolbar controls are hidden in production.
- WebSocket messages and uploads are bounded; static file serving and telemetry are disabled.
- Built-in dataframe export is disabled. The explicit download neutralizes cells beginning with spreadsheet formula characters before producing UTF-8 CSV.
- Search uses literal matching with a 100-character limit, so user input is not interpreted as a regular expression or executable expression.
- Untrusted comment content is rendered through `st.dataframe`; it is never interpolated into `unsafe_allow_html`.
- Dataset paths, parser exceptions, and stack traces remain in server logs and are replaced by safe browser messages.

This deployment is a public, read-only dashboard. Anyone with the URL can view the loaded comments. If the dataset becomes private or contains personal/confidential information, configure Streamlit authentication or place the app behind an identity-aware reverse proxy before deployment.

## Deployment

For Streamlit Community Cloud, select this repository and use `app.py` as the entry point. Dependencies are pinned in `requirements.txt`. Keep the CSV in the repository only when its contents are intentionally public; otherwise load it from controlled storage and restrict access to the application.

After deployment, confirm that the health endpoint responds, filters return expected totals, source replacement invalidates the cache, browser errors contain no stack trace, and the downloaded CSV opens as text without executing formula-like comment cells.

## Operational notes

- Streamlit runs the script again after widget changes. Expensive parsing is cached by file signature, while filtering and grouped calculations remain vectorized.
- The comment table is paginated to avoid sending the full dataset through the browser WebSocket on every rerun. Full CSV export is prepared in memory only after the user requests it.
- Application failures include a short event reference. Match it against server logs when diagnosing incidents.
- Model sentiment is probabilistic. Do not treat a high confidence score as proof of correctness or use the dashboard alone for high-impact decisions.
