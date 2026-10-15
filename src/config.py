"""Application configuration and immutable domain constants."""

from __future__ import annotations

import os
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATASET = APP_ROOT / "smart_analyzed_comments_OqEc_169ywY.csv"
DATASET_PATH = Path(os.getenv("SENTIMENT_DATA_FILE", str(DEFAULT_DATASET))).expanduser()

MAX_DATASET_BYTES = 50 * 1024 * 1024
MAX_DATASET_ROWS = 250_000
MAX_TEXT_LENGTH = 10_000
MAX_AUTHOR_LENGTH = 200

REQUIRED_COLUMNS = (
    "Author",
    "Comment Text",
    "Likes",
    "Published At",
    "Cleaned Text",
    "Sentiment Label",
    "Confidence Score",
)

SENTIMENT_ORDER = ("POSITIVE", "NEGATIVE", "NEUTRAL", "UNKNOWN")
SENTIMENT_COLORS = {
    "POSITIVE": "#14B8A6",
    "NEGATIVE": "#F43F5E",
    "NEUTRAL": "#94A3B8",
    "UNKNOWN": "#F59E0B",
}
