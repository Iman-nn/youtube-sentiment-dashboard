"""Plotly figure factories with one consistent, accessible visual system."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from .config import SENTIMENT_COLORS, SENTIMENT_ORDER

PLOTLY_CONFIG = {
    "displaylogo": False,
    "responsive": True,
    "modeBarButtonsToRemove": ["lasso2d", "select2d"],
}


def _finish(figure: go.Figure, *, height: int = 390) -> go.Figure:
    figure.update_layout(
        height=height,
        margin=dict(l=16, r=16, t=42, b=16),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#CBD5E1", family="Inter, Segoe UI, sans-serif"),
        hoverlabel=dict(bgcolor="#0F172A", font=dict(color="#F8FAFC")),
        legend_title_text="",
    )
    return figure


def empty_figure(message: str) -> go.Figure:
    figure = go.Figure()
    figure.add_annotation(text=message, x=0.5, y=0.5, showarrow=False, font=dict(color="#94A3B8"))
    figure.update_xaxes(visible=False)
    figure.update_yaxes(visible=False)
    return _finish(figure)


def sentiment_donut(counts: pd.DataFrame) -> go.Figure:
    if counts.empty:
        return empty_figure("No comments match the current filters")
    figure = px.pie(
        counts,
        values="Comments",
        names="Sentiment",
        color="Sentiment",
        category_orders={"Sentiment": list(SENTIMENT_ORDER)},
        color_discrete_map=SENTIMENT_COLORS,
        hole=0.62,
    )
    figure.update_traces(
        textinfo="percent+label",
        textposition="outside",
        hovertemplate="%{label}<br>%{value:,} comments<br>%{percent}<extra></extra>",
        marker=dict(line=dict(color="#0F172A", width=2)),
    )
    figure.update_layout(showlegend=False)
    return _finish(figure)


def timeline_chart(timeline: pd.DataFrame, granularity: str) -> go.Figure:
    if timeline.empty:
        return empty_figure("No valid publication dates are available")
    figure = px.bar(
        timeline,
        x="Period",
        y="Comments",
        color="Sentiment",
        category_orders={"Sentiment": list(SENTIMENT_ORDER)},
        color_discrete_map=SENTIMENT_COLORS,
        barmode="stack",
    )
    figure.update_traces(hovertemplate="%{x|%b %Y}<br>%{fullData.name}: %{y:,}<extra></extra>")
    figure.update_xaxes(title=None, dtick="M3" if granularity == "month" else None, gridcolor="#1E293B")
    figure.update_yaxes(title="Comments", rangemode="tozero", gridcolor="#1E293B")
    figure.update_layout(legend=dict(orientation="h", y=1.12, x=0))
    return _finish(figure)


def confidence_histogram(frame: pd.DataFrame) -> go.Figure:
    confidence = frame.dropna(subset=["Confidence Score"])
    if confidence.empty:
        return empty_figure("No valid confidence scores are available")
    figure = px.histogram(
        confidence,
        x="Confidence Score",
        color="Sentiment Label",
        category_orders={"Sentiment Label": list(SENTIMENT_ORDER)},
        color_discrete_map=SENTIMENT_COLORS,
        nbins=20,
        barmode="overlay",
        opacity=0.78,
    )
    figure.update_traces(hovertemplate="Confidence: %{x:.2f}<br>Comments: %{y:,}<extra></extra>")
    figure.update_xaxes(title="AI confidence", range=[0, 1], tickformat=".0%", gridcolor="#1E293B")
    figure.update_yaxes(title="Comments", rangemode="tozero", gridcolor="#1E293B")
    figure.update_layout(legend=dict(orientation="h", y=1.12, x=0))
    return _finish(figure)


def engagement_chart(engagement: pd.DataFrame) -> go.Figure:
    if engagement.empty:
        return empty_figure("No engagement data matches the current filters")
    figure = px.bar(
        engagement,
        x="Sentiment",
        y="Total Likes",
        color="Sentiment",
        category_orders={"Sentiment": list(SENTIMENT_ORDER)},
        color_discrete_map=SENTIMENT_COLORS,
        custom_data=["Comments", "Median Likes"],
    )
    figure.update_traces(
        hovertemplate=(
            "%{x}<br>Total likes: %{y:,}<br>Comments: %{customdata[0]:,.0f}"
            "<br>Median likes: %{customdata[1]:,.0f}<extra></extra>"
        )
    )
    figure.update_xaxes(title=None, gridcolor="#1E293B")
    figure.update_yaxes(title="Total likes", rangemode="tozero", gridcolor="#1E293B")
    figure.update_layout(showlegend=False)
    return _finish(figure)
