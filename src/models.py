"""Typed value objects shared between the data and presentation layers."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class DataQuality:
    row_count: int
    missing_confidence: int = 0
    invalid_confidence: int = 0
    invalid_dates: int = 0
    invalid_likes: int = 0
    unknown_sentiment: int = 0
    empty_comments: int = 0
    truncated_text: int = 0

    @property
    def issue_count(self) -> int:
        return sum(
            (
                self.missing_confidence,
                self.invalid_confidence,
                self.invalid_dates,
                self.invalid_likes,
                self.unknown_sentiment,
                self.empty_comments,
                self.truncated_text,
            )
        )


@dataclass(frozen=True)
class DatasetBundle:
    frame: pd.DataFrame
    quality: DataQuality


@dataclass(frozen=True)
class DashboardSummary:
    total_comments: int
    positive: int
    negative: int
    neutral: int
    unknown: int
    total_likes: int
    average_confidence: float | None

    @property
    def positive_share(self) -> float:
        return self.positive / self.total_comments if self.total_comments else 0.0
