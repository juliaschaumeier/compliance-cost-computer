#!/usr/bin/env python3
"""Historical CCC LLM quality analysis CLI."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from adjudication import adjudicate
from common import (
    DEFAULT_CONFIG_PATH,
    build_manifest,
    configure_analysis,
    default_output_dir,
    ensure_run_dirs,
    extract,
    load_analysis_config,
    load_feature_markers,
    load_run_config,
    snapshot_db,
)
# Re-exported for the focused test module and ad-hoc notebook-style inspection.
from entities import answer_addressee, classify_json_answer
from issues import analyze_issue_02, structure_fingerprint
from reporting import aggregate, analyze, run_all, visualize


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    def add_config(p: argparse.ArgumentParser) -> None:
        p.add_argument(
            "--config",
            type=Path,
            default=None,
            help="Optional JSON run config. If omitted, code_analysis/analysis_config.json is used when present.",
        )

    def add_output(p: argparse.ArgumentParser) -> None:
        p.add_argument("--output", type=Path, default=None, help="Output run directory.")

    def add_feature_markers(p: argparse.ArgumentParser) -> None:
        p.add_argument("--feature-markers", type=Path, default=None, help="Optional feature marker YAML/JSON file.")

    p = sub.add_parser("run", help="Run snapshot, extraction, analysis, aggregation, and visualization.")
    add_config(p)
    p.add_argument("--db", type=Path, help="Source SQLite DB path. Overrides config db_path.")
    add_output(p)
    add_feature_markers(p)

    p = sub.add_parser("snapshot", help="Copy a source DB into an output run folder.")
    add_config(p)
    p.add_argument("--db", type=Path, help="Source SQLite DB path. Overrides config db_path.")
    add_output(p)
    add_feature_markers(p)

    p = sub.add_parser("extract", help="Extract normalized CSV/JSONL files from a DB snapshot.")
    add_config(p)
    p.add_argument("--snapshot-db", type=Path, help="Existing copied DB snapshot.")
    add_output(p)

    p = sub.add_parser("analyze", help="Run issue checks against extracted files.")
    add_config(p)
    add_output(p)

    p = sub.add_parser("aggregate", help="Build summary tables from findings.")
    add_config(p)
    add_output(p)

    p = sub.add_parser("visualize", help="Build the HTML report from extracted findings and summaries.")
    add_config(p)
    add_output(p)
    add_feature_markers(p)

    p = sub.add_parser("adjudicate")
    p.add_argument("--input", type=Path, required=True, help="Review packet directory.")
    p.add_argument("--output", type=Path, required=True, help="Adjudication output directory.")
    p.add_argument(
        "--mode",
        choices=("pending", "rules"),
        default="pending",
        help="Use 'pending' to stage review rows or 'rules' for conservative deterministic adjudication.",
    )
    return parser.parse_args(argv)


def configured_paths(args: argparse.Namespace) -> tuple[Path, dict[str, object], Path | None]:
    output_hint = getattr(args, "output", None)
    config_arg = getattr(args, "config", None)
    if config_arg is not None or DEFAULT_CONFIG_PATH.exists():
        config = load_analysis_config(config_arg)
    elif output_hint:
        config = load_run_config(output_hint)
    else:
        config = load_analysis_config(None)
    if getattr(args, "db", None):
        config["db_path"] = str(args.db)
    if output_hint:
        config["output_dir"] = str(output_hint)
    if getattr(args, "feature_markers", None):
        config["feature_markers_path"] = str(args.feature_markers)
    out_dir_text = config.get("output_dir")
    out_dir = Path(str(out_dir_text)) if out_dir_text else default_output_dir()
    feature_text = config.get("feature_markers_path")
    feature_marker_path = Path(str(feature_text)) if feature_text else None
    return out_dir, config, feature_marker_path


def configured_db_path(args: argparse.Namespace, config: dict[str, object]) -> Path:
    db_path = getattr(args, "db", None) or config.get("db_path")
    if not db_path:
        raise SystemExit("--db is required unless db_path is set in the analysis config")
    return Path(str(db_path))


def first_snapshot(out_dir: Path) -> Path:
    candidates = sorted((out_dir / "db_snapshot").glob("*"))
    if not candidates:
        raise SystemExit("No snapshot DB found. Pass --snapshot-db or run snapshot first.")
    return candidates[0]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if args.command == "adjudicate":
        adjudicate(args.input, args.output, mode=args.mode)
        print(f"Wrote adjudication output to {args.output}")
        return 0
    out_dir, config, feature_marker_path = configured_paths(args)
    configure_analysis(config)
    ensure_run_dirs(out_dir)
    markers = load_feature_markers(feature_marker_path)
    if args.command == "run":
        run_all(configured_db_path(args, config), out_dir, feature_marker_path, config)
    elif args.command == "snapshot":
        db_path = configured_db_path(args, config)
        snapshot_path = snapshot_db(db_path, out_dir)
        build_manifest(db_path, snapshot_path, out_dir, markers, config)
    elif args.command == "extract":
        snapshot = args.snapshot_db or first_snapshot(out_dir)
        extract(snapshot, out_dir, config)
    elif args.command == "analyze":
        analyze(out_dir, config)
    elif args.command == "aggregate":
        aggregate(out_dir, config)
    elif args.command == "visualize":
        visualize(out_dir, markers, config)
    print(f"Wrote analysis output to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
