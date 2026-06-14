from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = ROOT / "docs" / "MATCHING_REAL_DATA.json"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from match_cities import (  # noqa: E402
    DEFAULT_CONFIG_FILENAME,
    app_root,
    apply_config,
    build_candidates,
    build_outputs,
    load_aliases,
    load_config,
    load_input,
    resolve_input_workbook,
)


def winner_for_row(row: dict[str, object]) -> str:
    scores = {
        "sequence": float(row.get("match_sequence_score") or 0.0),
        "token_sort": float(row.get("match_token_sort_score") or 0.0),
        "subset": float(row.get("match_subset_score") or 0.0),
    }
    top = max(scores.values())
    winners = [name for name, value in scores.items() if value == top and top > 0]
    if not winners:
        return "none"
    if len(winners) > 1:
        return "tie"
    return winners[0]


def example_priority(row: dict[str, object]) -> tuple[int, float, float]:
    sequence = float(row.get("match_sequence_score") or 0.0)
    token_sort = float(row.get("match_token_sort_score") or 0.0)
    subset = float(row.get("match_subset_score") or 0.0)
    final = float(row.get("match_score") or 0.0)
    span = max(sequence, token_sort, subset) - min(sequence, token_sort, subset)
    is_perfect = 1 if final >= 100.0 else 0
    return (is_perfect, -span, -final)


def choose_examples(rows: list[dict[str, object]], limit: int = 6) -> list[dict[str, object]]:
    buckets = {"sequence": [], "token_sort": [], "subset": [], "tie": []}
    for row in rows:
        buckets.setdefault(winner_for_row(row), []).append(row)

    selected: list[dict[str, object]] = []
    for bucket_name in ("sequence", "token_sort", "subset", "tie"):
        bucket = sorted(buckets.get(bucket_name, []), key=example_priority)
        selected.extend(bucket[:2])

    if len(selected) < limit:
        seen = {id(row) for row in selected}
        remaining = sorted(rows, key=example_priority)
        for row in remaining:
            if id(row) in seen:
                continue
            selected.append(row)
            if len(selected) >= limit:
                break

    unique_selected: list[dict[str, object]] = []
    seen_keys: set[tuple[object, object, object]] = set()
    for row in selected:
        key = (
            row.get("Arrival Country"),
            row.get("Delivery City"),
            row.get("matched_destination_city"),
        )
        if key in seen_keys:
            continue
        seen_keys.add(key)
        unique_selected.append(row)
        if len(unique_selected) >= limit:
            break
    return unique_selected


def compact_label(row: dict[str, object]) -> str:
    source = f"{row.get('Arrival Country') or ''}/{row.get('Delivery City') or ''}"
    target = f"{row.get('matched_destination_country') or ''}/{row.get('matched_destination_city') or ''}"
    return f"{source} -> {target}"


def pair_label(country: object, city: object) -> str:
    country_text = str(country or "").strip()
    city_text = str(city or "").strip()
    if not country_text and not city_text:
        return "/"
    return f"{country_text}/{city_text}"


def build_stats() -> dict[str, object]:
    base_dir = app_root()
    config = load_config(base_dir / DEFAULT_CONFIG_FILENAME)
    apply_config(config)
    workbook_path = resolve_input_workbook(
        explicit_input=None,
        config=config,
        base_dir=base_dir,
        input_func=lambda _: "1",
        output_func=lambda _: None,
    )

    rc, shrep = load_input(workbook_path)
    outputs = build_outputs(
        rc=rc,
        shrep=shrep,
        candidates=build_candidates(rc),
        aliases=load_aliases(base_dir / "city_aliases.csv"),
        auto_threshold=90.0,
        review_threshold=75.0,
        min_margin=3.0,
        allow_cross_country=False,
    )

    fuzzy_rows = [
        row
        for row in outputs["city_map"]
        if row.get("match_method") == "fuzzy" and row.get("matched_destination_city")
    ]
    examples = choose_examples(fuzzy_rows)

    winner_counts = {"sequence": 0, "token_sort": 0, "subset": 0, "tie": 0, "none": 0}
    for row in fuzzy_rows:
        winner_counts[winner_for_row(row)] += 1

    status_counts = {"auto_matched": 0, "review_needed": 0, "unmatched": 0, "manual_matched": 0}
    decision_points = []
    for row in outputs["city_map"]:
        status = str(row.get("match_status") or "")
        status_counts[status] = status_counts.get(status, 0) + 1
        decision_points.append(
            {
                "label": compact_label(row),
                "source": pair_label(row.get("Arrival Country"), row.get("Delivery City")),
                "top_candidate": pair_label(
                    row.get("candidate_1_country"),
                    row.get("candidate_1_city"),
                ),
                "second_candidate": pair_label(
                    row.get("candidate_2_country"),
                    row.get("candidate_2_city"),
                ),
                "status": status,
                "score": float(row.get("match_score") or 0.0),
                "second_score": float(row.get("candidate_2_score") or 0.0),
                "margin": float(row.get("match_margin") or 0.0),
            }
        )

    return {
        "source_workbook": workbook_path.name,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "thresholds": {
            "auto": 90.0,
            "review": 75.0,
            "margin": 3.0,
        },
        "examples": [
            {
                "label": compact_label(row),
                "status": row.get("match_status"),
                "winner": winner_for_row(row),
                "sequence": float(row.get("match_sequence_score") or 0.0),
                "token_sort": float(row.get("match_token_sort_score") or 0.0),
                "subset": float(row.get("match_subset_score") or 0.0),
                "final": float(row.get("match_score") or 0.0),
            }
            for row in examples
        ],
        "winner_counts": winner_counts,
        "status_counts": status_counts,
        "decision_points": decision_points,
    }


def main() -> int:
    stats = build_stats()
    OUTPUT_PATH.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    print(OUTPUT_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
