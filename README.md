# Dedupe CLI

Remove duplicate lines from text input while preserving first-seen order.

`dedupe.py` is a small Python CLI for cleaning text files, pipes, and stdin.

## Quick Install

```bash
python -m pip install -e . && dedupe input.txt
```

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
