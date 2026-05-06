#!/usr/bin/env python3
"""Post-process and merge actions CSVs into one cleaned dataset."""

from __future__ import annotations

import ast
import csv
import json
from pathlib import Path
from typing import Iterable

LIST_FIELDS = {"hand_before", "legal_moves"}
CARDS_IN_TRICK_FIELD = "cards_in_trick"
DICT_FIELDS = {"team_scores"}
INT_FIELDS = {"round", "position_in_trick", "card_played"}

PREFERRED_ORDER = [
	"game_id",
	"round",
	"player",
	"position",
	"card_played",
	"cards_in_trick",
	"position_in_trick",
	"lead_suit",
	"trump",
	"team_scores",
	"hand_before",
	"legal_moves",
]


def find_action_csvs(batch_root: Path) -> list[Path]:
	"""Find all actions_*.csv under any games/ folder."""
	return sorted(batch_root.rglob("games/actions_*.csv"))


def collect_schema(csv_paths: Iterable[Path]) -> tuple[list[str], bool]:
	"""Collect a union of headers and detect extra unnamed columns."""
	fieldnames: list[str] = []
	extra_detected = False

	for path in csv_paths:
		with path.open("r", newline="", encoding="utf-8-sig") as handle:
			reader = csv.reader(handle)
			header = next(reader, None)
			if not header:
				continue

			for name in header:
				if name not in fieldnames:
					fieldnames.append(name)

			if not extra_detected:
				for row in reader:
					if len(row) > len(header):
						extra_detected = True
						break

	return fieldnames, extra_detected


def build_output_schema(fieldnames: list[str], include_extra: bool) -> list[str]:
	output_fields: list[str] = []

	for name in PREFERRED_ORDER:
		if name in fieldnames and name not in output_fields:
			output_fields.append(name)

	for name in fieldnames:
		if name not in output_fields:
			output_fields.append(name)

	if include_extra and "_extra" not in output_fields:
		output_fields.append("_extra")

	return output_fields


def _safe_literal_eval(value, fallback):
	if value is None:
		return fallback
	text = str(value).strip()
	if not text:
		return fallback
	try:
		return ast.literal_eval(text)
	except (ValueError, SyntaxError):
		return fallback


def _to_int(value):
	try:
		return int(value)
	except (TypeError, ValueError):
		return None


def _normalize_string(value) -> str:
	if value is None:
		return ""
	return str(value).strip()


def _normalize_position(value) -> str:
	text = _normalize_string(value)
	if "." in text:
		return text.split(".")[-1]
	return text


def _normalize_list(value) -> list[int]:
	parsed = _safe_literal_eval(value, [])
	if not isinstance(parsed, list):
		return []
	items: list[int] = []
	for item in parsed:
		card_id = _to_int(item)
		if card_id is not None:
			items.append(card_id)
	return items


def _normalize_cards_in_trick(value) -> list[int]:
	parsed = _safe_literal_eval(value, [])
	if not isinstance(parsed, list):
		return []

	cards: list[int] = []
	for item in parsed:
		if isinstance(item, dict):
			card_id = _to_int(item.get("card"))
		else:
			card_id = _to_int(item)

		if card_id is not None:
			cards.append(card_id)

	return cards[:3]


def _normalize_team_scores(value) -> dict[str, int | str]:
	parsed = _safe_literal_eval(value, {})
	if not isinstance(parsed, dict):
		return {}

	normalized: dict[str, int | str] = {}
	for key, val in parsed.items():
		score = _to_int(val)
		normalized[str(key)] = score if score is not None else str(val)
	return normalized


def _dump_json(value) -> str:
	if isinstance(value, dict):
		return json.dumps(value, separators=(",", ":"), sort_keys=True)
	return json.dumps(value, separators=(",", ":"))


def _normalize_int_field(value):
	if value is None:
		return ""
	parsed = _to_int(value)
	return parsed if parsed is not None else _normalize_string(value)


def normalize_row(
	raw_row: dict[str, str],
	output_fields: list[str],
	include_extra: bool,
	extras,
) -> dict[str, str]:
	extra_blob = ""
	if include_extra:
		if extras:
			extra_blob = "|".join(str(value) for value in extras)

	normalized: dict[str, str] = {}
	for field in output_fields:
		if field == "_extra":
			normalized[field] = extra_blob
			continue

		raw_value = raw_row.get(field, "")
		if field in INT_FIELDS:
			normalized[field] = _normalize_int_field(raw_value)
		elif field == "position":
			normalized[field] = _normalize_position(raw_value)
		elif field == CARDS_IN_TRICK_FIELD:
			cards = _normalize_cards_in_trick(raw_value)

			pos = _to_int(raw_row.get("position_in_trick"))
			if pos is not None:
				cards = cards[:pos]

				normalized[field] = _dump_json(cards)
		elif field in LIST_FIELDS:
			normalized[field] = _dump_json(_normalize_list(raw_value))
		elif field in DICT_FIELDS:
			normalized[field] = _dump_json(_normalize_team_scores(raw_value))
		else:
			normalized[field] = _normalize_string(raw_value)

	return normalized


def merge_action_csvs(
	csv_paths: Iterable[Path],
	output_path: Path,
	output_fields: list[str],
	include_extra: bool,
) -> tuple[int, dict[Path, int]]:
	"""Write merged CSV, normalizing list/dict fields along the way."""
	rows_by_file: dict[Path, int] = {}
	total_rows = 0

	with output_path.open("w", newline="", encoding="utf-8") as handle:
		writer = csv.DictWriter(handle, fieldnames=output_fields)
		writer.writeheader()

		for path in csv_paths:
			row_count = 0
			with path.open("r", newline="", encoding="utf-8-sig") as input_handle:
				reader = csv.DictReader(input_handle)
				if reader.fieldnames is None:
					rows_by_file[path] = 0
					continue

				for row in reader:
					extras = row.pop(None, None)
					output_row = normalize_row(
						row,
						output_fields,
						include_extra=include_extra,
						extras=extras,
					)
					writer.writerow(output_row)
					row_count += 1
					total_rows += 1

			rows_by_file[path] = row_count

	return total_rows, rows_by_file


def main() -> int:
	base_dir = Path(__file__).resolve().parent
	batch_root = base_dir / "batch_output"

	if not batch_root.exists():
		print(f"Batch output folder not found: {batch_root}")
		return 1

	action_csvs = find_action_csvs(batch_root)
	if not action_csvs:
		print(f"No actions_*.csv files found under: {batch_root}")
		return 1

	fieldnames, extra_detected = collect_schema(action_csvs)
	if not fieldnames:
		print("No headers found in actions CSV files.")
		return 1

	output_fields = build_output_schema(fieldnames, include_extra=extra_detected)
	output_dir = base_dir / "stat_final"
	output_dir.mkdir(parents=True, exist_ok=True)
	output_path = output_dir / "final_stats.csv"

	total_rows, rows_by_file = merge_action_csvs(
		action_csvs,
		output_path,
		output_fields,
		include_extra=extra_detected,
	)

	print(f"Found {len(action_csvs)} input files.")
	print(f"Columns ({len(output_fields)}): {', '.join(output_fields)}")
	print(f"Wrote {total_rows} rows to: {output_path}")
	for path in action_csvs:
		print(f"- {path}: {rows_by_file.get(path, 0)} rows")

	return 0


if __name__ == "__main__":
	raise SystemExit(main())
