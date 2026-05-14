#!/usr/bin/env python3
"""Profile CSV data and emit a compact JSON summary.

Examples:
  python datablaster.py data.csv
  datablaster data.csv -o profile.json
    datablaster data.csv --compare-to baseline.csv -o report.json
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import date, datetime
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TextIO

try:
    import pandas as pd
except ImportError:  # pragma: no cover - optional dependency
    pd = None


_BOOLEAN_VALUES = {"true", "false", "yes", "no", "y", "n", "1", "0"}
_INTEGER_PATTERN = re.compile(r"^[+-]?\d+$")
_FLOAT_PATTERN = re.compile(r"^[+-]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][+-]?\d+)?$")


@dataclass
class ColumnProfile:
    name: str
    inferred_type: str
    non_null: int
    blank: int
    unique: int
    sample_values: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "inferred_type": self.inferred_type,
            "non_null": self.non_null,
            "blank": self.blank,
            "unique": self.unique,
            "sample_values": self.sample_values,
        }


@dataclass
class DatasetProfile:
    path: str
    row_count: int
    columns: list[ColumnProfile]

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "row_count": self.row_count,
            "column_count": len(self.columns),
            "columns": [column.to_dict() for column in self.columns],
        }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Profile a CSV file and write a JSON summary.",
    )
    parser.add_argument(
        "file",
        type=Path,
        help="CSV input file to profile.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Write output to a file instead of stdout.",
    )
    parser.add_argument(
        "--compare-to",
        type=Path,
        help="Compare the input file to a baseline CSV and write a drift report.",
    )
    return parser


def _profile_row_values(
    row: dict[str, str | None],
    field_names: list[str],
    seen_values: dict[str, set[str]],
    observed_values: dict[str, list[str]],
    sample_values: dict[str, list[str]],
    non_null_counts: dict[str, int],
    blank_counts: dict[str, int],
    sample_size: int,
) -> None:
    for name in field_names:
        text = row.get(name) or ""

        if text.strip() == "":
            blank_counts[name] += 1
            continue

        non_null_counts[name] += 1

        if text not in seen_values[name]:
            seen_values[name].add(text)

        observed_values[name].append(text)

        samples = sample_values[name]
        if len(samples) < sample_size and text not in samples:
            samples.append(text)


def _is_boolean_value(value: str) -> bool:
    return value.strip().lower() in _BOOLEAN_VALUES


def _is_integer_value(value: str) -> bool:
    return bool(_INTEGER_PATTERN.fullmatch(value.strip()))


def _is_float_value(value: str) -> bool:
    stripped = value.strip()
    if _INTEGER_PATTERN.fullmatch(stripped):
        return False
    return bool(_FLOAT_PATTERN.fullmatch(stripped))


def _is_date_value(value: str) -> bool:
    stripped = value.strip().replace("Z", "+00:00")
    try:
        datetime.fromisoformat(stripped)
        return True
    except ValueError:
        try:
            date.fromisoformat(stripped)
            return True
        except ValueError:
            return False


def infer_column_type(values: list[str]) -> str:
    non_empty_values = [value for value in values if value.strip()]
    if not non_empty_values:
        return "empty"

    if all(_is_boolean_value(value) for value in non_empty_values):
        return "boolean"

    if all(_is_integer_value(value) for value in non_empty_values):
        return "integer"

    if all(_is_float_value(value) for value in non_empty_values):
        return "float"

    if all(_is_date_value(value) for value in non_empty_values):
        return "datetime" if any("T" in value or ":" in value for value in non_empty_values) else "date"

    return "text"


def profile_csv(path: Path, *, sample_size: int = 3) -> DatasetProfile:
    with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle)
        field_names = list(reader.fieldnames or [])

        if not field_names:
            return DatasetProfile(path=str(path), row_count=0, columns=[])

        seen_values: dict[str, set[str]] = {name: set() for name in field_names}
        observed_values: dict[str, list[str]] = {name: [] for name in field_names}
        sample_values: dict[str, list[str]] = {name: [] for name in field_names}
        non_null_counts: dict[str, int] = {name: 0 for name in field_names}
        blank_counts: dict[str, int] = {name: 0 for name in field_names}

        row_count = 0
        for row in reader:
            row_count += 1
            _profile_row_values(
                row,
                field_names,
                seen_values,
                observed_values,
                sample_values,
                non_null_counts,
                blank_counts,
                sample_size,
            )

    columns = [
        ColumnProfile(
            name=name,
            inferred_type=infer_column_type(observed_values[name]),
            non_null=non_null_counts[name],
            blank=blank_counts[name],
            unique=len(seen_values[name]),
            sample_values=sample_values[name],
        )
        for name in field_names
    ]
    return DatasetProfile(path=str(path), row_count=row_count, columns=columns)


def profile_pandas_dataframe(dataframe: Any) -> DatasetProfile:
    if not hasattr(dataframe, "columns"):
        raise RuntimeError("pandas dataframe must provide columns")

    return _profile_dataframe_like(dataframe, path="<pandas-dataframe>")


def profile_spark_dataframe(dataframe: Any) -> DatasetProfile:
    if not hasattr(dataframe, "toPandas"):
        raise RuntimeError("spark dataframe must provide toPandas()")

    return _profile_dataframe_like(dataframe.toPandas(), path="<spark-dataframe>")


def compare_profiles(current: DatasetProfile, baseline: DatasetProfile) -> dict[str, Any]:
    current_columns = {column.name: column for column in current.columns}
    baseline_columns = {column.name: column for column in baseline.columns}

    current_names = set(current_columns)
    baseline_names = set(baseline_columns)
    added_columns = sorted(current_names - baseline_names)
    removed_columns = sorted(baseline_names - current_names)

    changed_columns: list[dict[str, Any]] = []
    type_changes: list[dict[str, Any]] = []
    for name in sorted(current_names & baseline_names):
        current_column = current_columns[name]
        baseline_column = baseline_columns[name]

        current_values = current_column.to_dict()
        baseline_values = baseline_column.to_dict()
        if current_values == baseline_values:
            continue

        type_changed = current_column.inferred_type != baseline_column.inferred_type
        if type_changed:
            type_changes.append(
                {
                    "name": name,
                    "current_type": current_column.inferred_type,
                    "baseline_type": baseline_column.inferred_type,
                }
            )

        changed_columns.append(
            {
                "name": name,
                "current": current_values,
                "baseline": baseline_values,
                "delta": {
                    "non_null": current_column.non_null - baseline_column.non_null,
                    "blank": current_column.blank - baseline_column.blank,
                    "unique": current_column.unique - baseline_column.unique,
                    "inferred_type_changed": type_changed,
                    "sample_values_changed": current_column.sample_values != baseline_column.sample_values,
                },
            }
        )

    return {
        "current": current.to_dict(),
        "baseline": baseline.to_dict(),
        "current_path": current.path,
        "baseline_path": baseline.path,
        "row_count_delta": current.row_count - baseline.row_count,
        "schema_drift": {
            "added_columns": added_columns,
            "removed_columns": removed_columns,
        },
        "type_changes": type_changes,
        "column_changes": changed_columns,
        "summary": {
            "added_column_count": len(added_columns),
            "removed_column_count": len(removed_columns),
            "changed_column_count": len(changed_columns),
            "type_changed_column_count": len(type_changes),
        },
    }


def _profile_dataframe_like(dataframe: Any, *, path: str) -> DatasetProfile:
    if not hasattr(dataframe, "columns"):
        raise RuntimeError("dataframe must provide columns")

    columns: list[ColumnProfile] = []
    for name in list(dataframe.columns):
        series = dataframe[name]
        non_null = int(series.notna().sum())
        blank = int((series.astype(str).str.strip() == "").sum())
        observed_values = [str(value) for value in series.dropna().astype(str).tolist() if str(value).strip()]
        unique = int(len(set(observed_values)))
        samples: list[str] = []
        for value in observed_values[:3]:
            text = str(value)
            if text not in samples:
                samples.append(text)
        columns.append(
            ColumnProfile(
                name=str(name),
                inferred_type=infer_column_type(observed_values),
                non_null=non_null,
                blank=blank,
                unique=unique,
                sample_values=samples,
            )
        )

    return DatasetProfile(
        path=path,
        row_count=int(len(dataframe)),
        columns=columns,
    )


def write_output(profile: DatasetProfile, handle: TextIO) -> None:
    json.dump(profile.to_dict(), handle, indent=2)
    handle.write("\n")


def write_json_report(report: dict[str, Any], handle: TextIO) -> None:
    json.dump(report, handle, indent=2)
    handle.write("\n")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    profile = profile_csv(args.file)

    if args.compare_to:
        baseline = profile_csv(args.compare_to)
        payload: dict[str, Any] = compare_profiles(profile, baseline)
        writer = write_json_report
    else:
        payload = profile
        writer = write_output

    if args.output:
        with args.output.open("w", encoding="utf-8", newline="\n") as handle:
            writer(payload, handle)
    else:
        writer(payload, sys.stdout)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())