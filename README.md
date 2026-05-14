# Dedupe CLI

Remove duplicate lines from text input while preserving first-seen order.

`dedupe.py` is a small Python CLI for cleaning text files, pipes, and stdin.

## Data Blaster

This repo also includes a small CSV profiling entry point called `datablaster`.
It summarizes row counts, blank values, unique values, and sample values so the
same repo can support lightweight data inspection without starting a new project.

### Data Blaster features

- Profile CSV files and emit JSON summaries.
- Profile pandas DataFrames through the same summary shape.
- Profile Spark DataFrames through the same summary shape.
- Compare two profiles for schema drift, type changes, row-count deltas, and changed columns.
- Track common data quality signals such as blank values, missing values, and repeated values.

## Quick Install

```bash
python -m pip install -e . && dedupe input.txt
```

## Data Blaster usage

```bash
python datablaster.py data.csv
datablaster data.csv -o profile.json
```

## Python API

```python
from datablaster import (
	compare_profiles,
	profile_csv,
	profile_pandas_dataframe,
	profile_spark_dataframe,
)
```

- `profile_csv(path)` profiles a CSV file and returns a structured summary.
- `profile_pandas_dataframe(df)` profiles an in-memory pandas DataFrame.
- `profile_spark_dataframe(df)` profiles a Spark DataFrame by converting it to the same summary shape.
- `compare_profiles(current, baseline)` compares two profiles and reports schema drift, type changes, row-count deltas, and changed columns.

## Features

- Keeps the first occurrence of each unique line.
- Supports case-insensitive matching with `--ignore-case`.
- Supports whitespace-normalized matching with `--strip-whitespace`.
- Drops empty lines by default unless `--keep-empty` is set.

## Usage

```bash
python dedupe.py input.txt
cat input.txt | python dedupe.py
python dedupe.py input.txt -o unique.txt --ignore-case --strip-whitespace
```

## Install and run

```bash
python -m pip install -e .
dedupe input.txt
```

## Tests

```bash
python -m unittest discover -s tests
```

## Next useful steps

- Expand validation to flag duplicate rows and richer data quality checks.
