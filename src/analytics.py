"""Pure, vectorized analytics functions used by the Streamlit UI."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Collection

import pandas as pd

from .config import SENTIMENT_ORDER
from .models import DashboardSummary


def filter_comments(
    frame: pd.DataFrame,
    sentiments: Collection[str],
    minimum_confidence: float = 0.0,
    query: str = "",
    start_date: date | None = None,
    end_date: date | None = None,
) -> pd.DataFrame:
    mask = frame["Sentiment Label"].isin(sentiments)
    if minimum_confidence > 0:
        mask &= frame["Confidence Score"].ge(minimum_confidence).fillna(False)
    if query:
        needle = query.strip()[:100]
        if needle:
            mask &= (
                frame["Cleaned Text"].str.contains(needle, case=False, regex=False, na=False)
                | frame["Author"].str.contains(needle, case=False, regex=False, na=False)
            )
    if start_date:
        mask &= frame["Published At"].ge(pd.Timestamp(start_date, tz="UTC")).fillna(False)
    if end_date:
        exclusive_end = pd.Timestamp(end_date + timedelta(days=1), tz="UTC")
        mask &= frame["Published At"].lt(exclusive_end).fillna(False)
    return frame.loc[mask].copy()


def summarize(frame: pd.DataFrame) -> DashboardSummary:
    counts = frame["Sentiment Label"].value_counts()
    confidence = frame["Confidence Score"].dropna()
    return DashboardSummary(
        total_comments=len(frame),
        positive=int(counts.get("POSITIVE", 0)),
        negative=int(counts.get("NEGATIVE", 0)),
        neutral=int(counts.get("NEUTRAL", 0)),
        unknown=int(counts.get("UNKNOWN", 0)),
        total_likes=int(frame["Likes"].sum()),
        average_confidence=float(confidence.mean()) if not confidence.empty else None,
    )


def sentiment_counts(frame: pd.DataFrame) -> pd.DataFrame:
    counts = frame["Sentiment Label"].value_counts().reindex(SENTIMENT_ORDER, fill_value=0)
    return counts.rename_axis("Sentiment").reset_index(name="Comments").query("Comments > 0")


def sentiment_timeline(frame: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    dated = frame.dropna(subset=["Published At"])
    if dated.empty:
        return pd.DataFrame(columns=["Period", "Sentiment", "Comments"]), "day"

    span_days = int((dated["Published At"].max() - dated["Published At"].min()).days)
    if span_days > 120:
        period = dated["Published At"].dt.tz_convert(None).dt.to_period("M").dt.to_timestamp()
        granularity = "month"
    else:
        period = dated["Published At"].dt.floor("D").dt.tz_localize(None)
        granularity = "day"

    timeline = (
        dated.assign(Period=period)
        .groupby(["Period", "Sentiment Label"], observed=True)
        .size()
        .rename("Comments")
        .reset_index()
        .rename(columns={"Sentiment Label": "Sentiment"})
    )
    return timeline, granularity


def engagement_by_sentiment(frame: pd.DataFrame) -> pd.DataFrame:
    return (
        frame.groupby("Sentiment Label", observed=True)
        .agg(Comments=("Sentiment Label", "size"), Total_Likes=("Likes", "sum"), Median_Likes=("Likes", "median"))
        .reindex(SENTIMENT_ORDER)
        .dropna(subset=["Comments"])
        .reset_index()
        .rename(columns={"Sentiment Label": "Sentiment", "Total_Likes": "Total Likes", "Median_Likes": "Median Likes"})
    )
