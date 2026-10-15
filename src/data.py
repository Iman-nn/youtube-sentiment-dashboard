"""Bounded CSV ingestion, schema validation, and export hardening."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .config import (
    MAX_AUTHOR_LENGTH,
    MAX_DATASET_BYTES,
    MAX_DATASET_ROWS,
    MAX_TEXT_LENGTH,
    REQUIRED_COLUMNS,
    SENTIMENT_ORDER,
)
from .errors import DataSourceError, DataValidationError
from .models import DataQuality, DatasetBundle


@dataclass(frozen=True)
class DatasetSignature:
    path: Path
    modified_ns: int
    size_bytes: int


def inspect_dataset(path: Path) -> DatasetSignature:
    """Resolve and bound a configured CSV before Pandas allocates memory."""
    try:
        resolved = path.resolve(strict=True)
        stat = resolved.stat()
    except (FileNotFoundError, OSError) as exc:
        raise DataSourceError(
            "The sentiment dataset is unavailable. Contact the dashboard administrator.",
            f"Unable to inspect dataset {path!s}: {exc}",
        ) from exc

    if not resolved.is_file() or resolved.suffix.lower() != ".csv":
        raise DataSourceError(
            "The configured sentiment dataset is not a valid CSV file.",
            f"Rejected non-CSV dataset path: {resolved!s}",
        )
    if stat.st_size <= 0:
        raise DataValidationError("The sentiment dataset is empty.")
    if stat.st_size > MAX_DATASET_BYTES:
        raise DataValidationError(
            f"The dataset exceeds the {MAX_DATASET_BYTES // (1024 * 1024)} MiB safety limit."
        )
    return DatasetSignature(resolved, stat.st_mtime_ns, stat.st_size)


def _read_header(path: Path) -> list[str]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return next(csv.reader(handle), [])
    except UnicodeDecodeError as exc:
        raise DataValidationError(
            "The dataset must be UTF-8 encoded.",
            f"CSV encoding error: {exc}",
        ) from exc
    except (csv.Error, OSError) as exc:
        raise DataValidationError(
            "The dataset header could not be read.",
            f"CSV header error: {exc}",
        ) from exc


def _validate_header(header: list[str]) -> None:
    if not header:
        raise DataValidationError("The dataset does not contain a header row.")
    duplicates = sorted({name for name in header if header.count(name) > 1})
    if duplicates:
        raise DataValidationError(
            "The dataset contains duplicate column names.",
            f"Duplicate CSV columns: {duplicates!r}",
        )
    missing = sorted(set(REQUIRED_COLUMNS) - set(header))
    if missing:
        raise DataValidationError(
            "The dataset schema is incomplete. Ask the administrator to regenerate it.",
            f"Missing required CSV columns: {missing!r}",
        )


def _normalise_text(series: pd.Series, fallback: str, limit: int) -> pd.Series:
    return series.astype("string").fillna(fallback).str.strip().str.slice(0, limit)


def load_dataset(path: Path) -> DatasetBundle:
    """Load and normalize a validated file without silently falsifying metrics."""
    # Re-check at the parser boundary to narrow the window for a replaced file.
    inspect_dataset(path)
    _validate_header(_read_header(path))
    try:
        frame = pd.read_csv(
            path,
            encoding="utf-8-sig",
            dtype="string",
            keep_default_na=True,
            nrows=MAX_DATASET_ROWS + 1,
            on_bad_lines="error",
            usecols=list(REQUIRED_COLUMNS),
        )
    except (pd.errors.ParserError, UnicodeDecodeError, ValueError, OSError) as exc:
        raise DataValidationError(
            "The sentiment dataset is malformed and cannot be displayed safely.",
            f"CSV parse error: {exc}",
        ) from exc

    if len(frame) > MAX_DATASET_ROWS:
        raise DataValidationError(
            f"The dataset exceeds the {MAX_DATASET_ROWS:,}-row safety limit. Use a database-backed pipeline for larger loads."
        )
    if frame.empty:
        raise DataValidationError("The sentiment dataset contains no comment rows.")

    raw_author = frame["Author"].astype("string")
    raw_comment = frame["Comment Text"].astype("string")
    raw_cleaned = frame["Cleaned Text"].astype("string")
    truncated_text = int(
        (raw_author.str.len().fillna(0) > MAX_AUTHOR_LENGTH).sum()
        + (raw_comment.str.len().fillna(0) > MAX_TEXT_LENGTH).sum()
        + (raw_cleaned.str.len().fillna(0) > MAX_TEXT_LENGTH).sum()
    )

    frame["Author"] = _normalise_text(raw_author, "Unknown author", MAX_AUTHOR_LENGTH)
    frame["Comment Text"] = _normalise_text(raw_comment, "", MAX_TEXT_LENGTH)
    frame["Cleaned Text"] = _normalise_text(raw_cleaned, "", MAX_TEXT_LENGTH)
    cleaned_empty = frame["Cleaned Text"].str.len().eq(0)
    frame.loc[cleaned_empty, "Cleaned Text"] = frame.loc[cleaned_empty, "Comment Text"]
    empty_comments = int(frame["Cleaned Text"].str.len().eq(0).sum())

    raw_sentiment = frame["Sentiment Label"].astype("string").fillna("").str.strip().str.upper()
    known_sentiments = set(SENTIMENT_ORDER) - {"UNKNOWN"}
    unknown_mask = ~raw_sentiment.isin(known_sentiments)
    frame["Sentiment Label"] = raw_sentiment.mask(unknown_mask, "UNKNOWN")

    raw_confidence = frame["Confidence Score"].astype("string")
    confidence_missing = raw_confidence.isna() | raw_confidence.fillna("").str.strip().eq("")
    confidence = pd.to_numeric(raw_confidence, errors="coerce")
    confidence_valid = confidence.between(0.0, 1.0, inclusive="both")
    invalid_confidence = int((~confidence_missing & ~confidence_valid).sum())
    frame["Confidence Score"] = confidence.where(confidence_valid).astype("Float64")

    raw_likes = frame["Likes"].astype("string")
    likes = pd.to_numeric(raw_likes, errors="coerce")
    likes_valid = likes.notna() & likes.ge(0) & likes.mod(1).eq(0)
    invalid_likes = int((~likes_valid).sum())
    frame["Likes"] = likes.where(likes_valid, 0).astype("Int64")

    raw_dates = frame["Published At"].astype("string")
    published_at = pd.to_datetime(raw_dates, errors="coerce", utc=True)
    invalid_dates = int((raw_dates.notna() & published_at.isna()).sum())
    frame["Published At"] = published_at

    quality = DataQuality(
        row_count=len(frame),
        missing_confidence=int(confidence_missing.sum()),
        invalid_confidence=invalid_confidence,
        invalid_dates=invalid_dates,
        invalid_likes=invalid_likes,
        unknown_sentiment=int(unknown_mask.sum()),
        empty_comments=empty_comments,
        truncated_text=truncated_text,
    )
    return DatasetBundle(frame=frame, quality=quality)


def _neutralize_spreadsheet_formula(value: object) -> object:
    if not isinstance(value, str):
        return value
    stripped = value.lstrip()
    if stripped.startswith(("=", "+", "-", "@")) or value.startswith(("\t", "\r")):
        return "'" + value
    return value


def safe_csv_export(frame: pd.DataFrame) -> bytes:
    """Create a UTF-8 CSV that cannot execute comment text as a formula."""
    export = frame.loc[:, list(REQUIRED_COLUMNS)].copy()
    for column in ("Author", "Comment Text", "Cleaned Text", "Sentiment Label"):
        export[column] = export[column].map(_neutralize_spreadsheet_formula)
    export["Published At"] = export["Published At"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    return export.to_csv(index=False, lineterminator="\n").encode("utf-8-sig")
