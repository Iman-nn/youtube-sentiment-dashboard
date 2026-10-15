"""Streamlit presentation layer and application orchestration."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pandas as pd
import streamlit as st

from .analytics import engagement_by_sentiment, filter_comments, sentiment_counts, sentiment_timeline, summarize
from .charts import PLOTLY_CONFIG, confidence_histogram, engagement_chart, sentiment_donut, timeline_chart
from .config import DATASET_PATH, SENTIMENT_ORDER
from .data import DatasetSignature, inspect_dataset, load_dataset, safe_csv_export
from .errors import DashboardError
from .models import DatasetBundle, DataQuality

LOGGER = logging.getLogger(__name__)

STATIC_STYLES = """
<style>
  .block-container {max-width: 1480px; padding-top: 2rem; padding-bottom: 3rem;}
  h1, h2, h3 {letter-spacing: -0.025em;}
  div[data-testid="stMetric"] {
    border: 1px solid #243244;
    border-radius: 16px;
    padding: 16px 18px;
    background: linear-gradient(145deg, rgba(15, 23, 42, .94), rgba(17, 33, 49, .92));
  }
  div[data-testid="stMetricValue"] {color: #F8FAFC;}
  div[data-testid="stMetricLabel"] {color: #94A3B8;}
  [data-testid="stSidebar"] {border-right: 1px solid #1E293B;}
  .dashboard-kicker {color:#5EEAD4; font-size:.74rem; font-weight:700; letter-spacing:.16em; text-transform:uppercase;}
  .dashboard-subtitle {color:#94A3B8; max-width:760px; line-height:1.7; margin-top:-.35rem;}
</style>
"""


@st.cache_data(show_spinner=False, max_entries=4)
def _cached_load(path: str, modified_ns: int, size_bytes: int) -> DatasetBundle:
    # mtime and size are cache-key inputs so replacing the CSV invalidates stale data.
    _ = (modified_ns, size_bytes)
    return load_dataset(Path(path))


def _load_bundle() -> tuple[DatasetSignature, DatasetBundle]:
    signature = inspect_dataset(DATASET_PATH)
    bundle = _cached_load(str(signature.path), signature.modified_ns, signature.size_bytes)
    return signature, bundle


def _render_failure(error: Exception) -> None:
    event_id = uuid4().hex[:10]
    if isinstance(error, DashboardError):
        LOGGER.exception("Dashboard data failure event_id=%s", event_id)
        message = error.user_message
    else:
        LOGGER.exception("Unexpected dashboard failure event_id=%s", event_id)
        message = "The dashboard could not be loaded. Please try again or contact the administrator."
    st.error(message)
    st.caption(f"Reference: {event_id}")
    st.stop()


def _filters(frame: pd.DataFrame) -> tuple[list[str], float, str, object, object]:
    st.sidebar.header("Filters")
    available = [label for label in SENTIMENT_ORDER if label in set(frame["Sentiment Label"])]
    sentiments = st.sidebar.multiselect(
        "Sentiment",
        available,
        default=available,
        key="sentiment_filter_" + "_".join(available),
    )
    confidence_percent = st.sidebar.slider(
        "Minimum AI confidence",
        min_value=0,
        max_value=100,
        value=0,
        step=5,
        format="%d%%",
        help="Rows without a valid confidence score are excluded when this is above 0%.",
    )
    query = st.sidebar.text_input(
        "Search author or comment",
        max_chars=100,
        placeholder="Enter plain text",
        help="Search is literal and case-insensitive; regular expressions are not executed.",
    )

    valid_dates = frame["Published At"].dropna()
    start_date = end_date = None
    if not valid_dates.empty:
        earliest = valid_dates.min().date()
        latest = valid_dates.max().date()
        selected = st.sidebar.date_input(
            "Published date",
            value=(earliest, latest),
            min_value=earliest,
            max_value=latest,
            key=f"published_date_{earliest}_{latest}",
        )
        if isinstance(selected, (tuple, list)) and len(selected) == 2:
            start_date, end_date = selected

    if st.sidebar.button("Refresh dataset", width="stretch"):
        _cached_load.clear()
        st.rerun()
    return sentiments, confidence_percent / 100, query, start_date, end_date


def _render_metrics(frame: pd.DataFrame) -> None:
    summary = summarize(frame)
    columns = st.columns(5)
    columns[0].metric("Comments", f"{summary.total_comments:,}")
    columns[1].metric("Positive share", f"{summary.positive_share:.1%}")
    columns[2].metric("Negative", f"{summary.negative:,}")
    columns[3].metric("Total likes", f"{summary.total_likes:,}")
    confidence = "N/A" if summary.average_confidence is None else f"{summary.average_confidence:.1%}"
    columns[4].metric("Average confidence", confidence)


def _render_overview(frame: pd.DataFrame) -> None:
    _render_metrics(frame)
    st.caption("Sentiment and confidence are AI model predictions and should be reviewed before making high-impact decisions.")

    left, right = st.columns(2)
    with left:
        st.subheader("Sentiment mix")
        st.plotly_chart(sentiment_donut(sentiment_counts(frame)), width="stretch", config=PLOTLY_CONFIG)
    with right:
        timeline, granularity = sentiment_timeline(frame)
        st.subheader(f"Sentiment over time · by {granularity}")
        st.plotly_chart(timeline_chart(timeline, granularity), width="stretch", config=PLOTLY_CONFIG)

    left, right = st.columns(2)
    with left:
        st.subheader("Confidence distribution")
        st.plotly_chart(confidence_histogram(frame), width="stretch", config=PLOTLY_CONFIG)
    with right:
        st.subheader("Engagement by sentiment")
        st.plotly_chart(engagement_chart(engagement_by_sentiment(frame)), width="stretch", config=PLOTLY_CONFIG)

    st.subheader("Most-liked comments")
    top = frame.nlargest(min(10, len(frame)), "Likes")[
        ["Author", "Cleaned Text", "Sentiment Label", "Confidence Score", "Likes"]
    ]
    st.dataframe(
        top,
        width="stretch",
        hide_index=True,
        column_config={
            "Cleaned Text": st.column_config.TextColumn("Comment", width="large"),
            "Confidence Score": st.column_config.NumberColumn("Confidence", format="%.3f"),
            "Likes": st.column_config.NumberColumn("Likes", format="%d"),
        },
    )


def _render_explorer(frame: pd.DataFrame) -> None:
    st.subheader("Comment explorer")
    sort_label = st.radio("Sort rows", ("Newest", "Most liked", "Highest confidence"), horizontal=True)
    sort_map = {
        "Newest": ("Published At", False),
        "Most liked": ("Likes", False),
        "Highest confidence": ("Confidence Score", False),
    }
    sort_column, ascending = sort_map[sort_label]
    ordered = frame.sort_values(sort_column, ascending=ascending, na_position="last", kind="stable")

    page_size = st.selectbox("Rows per page", (50, 100, 250), index=0)
    page_count = max(1, (len(ordered) + page_size - 1) // page_size)
    st.session_state.comment_page = min(max(st.session_state.get("comment_page", 1), 1), page_count)
    page = st.number_input("Page", min_value=1, max_value=page_count, step=1, key="comment_page")
    start = (int(page) - 1) * page_size
    view = ordered.iloc[start : start + page_size][
        ["Author", "Cleaned Text", "Sentiment Label", "Confidence Score", "Likes", "Published At"]
    ]
    st.caption(f"Showing {start + 1 if len(ordered) else 0:,}-{min(start + page_size, len(ordered)):,} of {len(ordered):,} rows")
    st.dataframe(
        view,
        width="stretch",
        height=560,
        hide_index=True,
        column_config={
            "Cleaned Text": st.column_config.TextColumn("Comment", width="large"),
            "Sentiment Label": st.column_config.TextColumn("Sentiment"),
            "Confidence Score": st.column_config.NumberColumn("Confidence", format="%.3f"),
            "Likes": st.column_config.NumberColumn("Likes", format="%d"),
            "Published At": st.column_config.DatetimeColumn("Published", format="YYYY-MM-DD HH:mm"),
        },
    )
    prepare_download = st.checkbox(
        "Prepare full filtered download",
        help="Large downloads are created in memory only when requested.",
    )
    if prepare_download:
        st.download_button(
            "Download filtered CSV",
            data=safe_csv_export(ordered),
            file_name="filtered_sentiment_comments.csv",
            mime="text/csv",
            width="stretch",
            help="Potential spreadsheet formulas in text fields are neutralized during export.",
        )


def _render_quality(quality: DataQuality) -> None:
    st.subheader("Data quality")
    columns = st.columns(4)
    columns[0].metric("Rows checked", f"{quality.row_count:,}")
    columns[1].metric("Unknown sentiment", f"{quality.unknown_sentiment:,}")
    columns[2].metric("Invalid confidence", f"{quality.invalid_confidence:,}")
    columns[3].metric("Invalid dates", f"{quality.invalid_dates:,}")

    details = pd.DataFrame(
        {
            "Check": [
                "Missing confidence",
                "Invalid confidence",
                "Invalid publication dates",
                "Invalid likes",
                "Unknown sentiment labels",
                "Empty comments",
                "Truncated oversized text fields",
            ],
            "Rows / fields affected": [
                quality.missing_confidence,
                quality.invalid_confidence,
                quality.invalid_dates,
                quality.invalid_likes,
                quality.unknown_sentiment,
                quality.empty_comments,
                quality.truncated_text,
            ],
        }
    )
    st.dataframe(details, width="stretch", hide_index=True)
    if quality.issue_count:
        st.warning("The dashboard remained available, but some source values were normalized or excluded from specific calculations.")
    else:
        st.success("No data quality problems were detected in the required fields.")


def run_dashboard() -> None:
    st.set_page_config(
        page_title="YouTube Sentiment Intelligence",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.html(STATIC_STYLES)

    try:
        signature, bundle = _load_bundle()
    except Exception as error:  # The boundary deliberately hides unexpected internals.
        _render_failure(error)
        return

    st.html('<p class="dashboard-kicker">Social intelligence · YouTube</p>')
    st.title("Audience sentiment, made actionable")
    st.html(
        '<p class="dashboard-subtitle">Explore public reaction, model confidence, engagement and trends. '
        "Filters update every insight without modifying the source dataset.</p>"
    )
    modified = datetime.fromtimestamp(signature.modified_ns / 1_000_000_000, tz=timezone.utc)
    st.caption(
        f"Source: {signature.path.name} · {bundle.quality.row_count:,} rows · "
        f"updated {modified:%Y-%m-%d %H:%M UTC}"
    )

    sentiments, confidence, query, start_date, end_date = _filters(bundle.frame)
    filtered = filter_comments(
        bundle.frame,
        sentiments=sentiments,
        minimum_confidence=confidence,
        query=query,
        start_date=start_date,
        end_date=end_date,
    )
    st.sidebar.caption(f"{len(filtered):,} of {len(bundle.frame):,} comments match")

    overview_tab, explorer_tab, quality_tab = st.tabs(("Overview", "Comments", "Data quality"))
    with overview_tab:
        if filtered.empty:
            st.info("No comments match the current filters. Adjust the sidebar to continue.")
        else:
            _render_overview(filtered)
    with explorer_tab:
        if filtered.empty:
            st.info("No rows are available for the current filters.")
        else:
            _render_explorer(filtered)
    with quality_tab:
        _render_quality(bundle.quality)
