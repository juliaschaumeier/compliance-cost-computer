from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import shutil
import sqlite3
from typing import Any, Iterable

ADDRESSEES = ("administration", "business", "citizens")
NORM_PROMPTS = {
    "process_compilation",
    "case_group_development",
    "process_step_analysis",
    "cases_calculation",
    "effort_calculation",
}
REQUIRED_TOP_LEVEL = {
    "law_summary": "summary",
    "regulations_identification": "vorgaben",
    "process_compilation": "prozesse",
    "case_group_development": "prozesse",
    "process_step_analysis": "fallgruppen",
    "cases_calculation": "fallgruppen",
    "effort_calculation": "fallgruppen",
}
REQUIRED_OBJECT_FIELDS = {
    "law_summary": ("title", "blurb", "summary"),
}
ISSUES = {
    "issue_01_duplicate_fallgruppen": "Duplicate Fallgruppen",
    "issue_02_unnecessary_addressee_steps": "Unnecessary addressee prompts/tiles",
    "issue_03_json_truncation": "JSON/schema/truncation failures",
    "issue_04_change_status_inconsistency": "Change-status inconsistency",
    "issue_05_structure_consistency": "Repeated-run structure variance",
    "issue_06_cost_variance": "Final-cost variance",
    "issue_07_case_count_driven_variance": "Case-count-driven cost variance",
    "issue_08_bureaucracy_cost": "Business bureaucracy-cost separation",
    "issue_09_compliance_export_quality": "Compliance export Markdown quality",
}
OUTPUT_SUBDIRS = (
    "db_snapshot",
    "extracted",
    "findings",
    "review_packets",
    "reports",
    "visuals",
)
DEFAULT_INCLUDED_LAW_PAIRS = {
    "1->2",    # e-sports
    "9->10",   # e-sports
    "3->4",    # arbeitstagepauschale
    "7->8",    # arbeitstagepauschale
    "5->6",    # 491 bgb
    "11->12",  # 491 bgb
}
LAW_PAIR_LABELS = {
    "1->2": "e-sports",
    "9->10": "e-sports",
    "3->4": "arbeitstagepauschale",
    "7->8": "arbeitstagepauschale",
    "5->6": "491 bgb",
    "11->12": "491 bgb",
}
DEFAULT_CONFIG_PATH = Path("code_analysis") / "analysis_config.json"
DEFAULT_LAW_PAIR_GROUPS = [
    {"name": "e-sports", "pairs": ["1->2", "9->10"]},
    {"name": "arbeitstagepauschale", "pairs": ["3->4", "7->8"]},
    {"name": "491 bgb", "pairs": ["5->6", "11->12"]},
]
_ACTIVE_INCLUDED_LAW_PAIRS = set(DEFAULT_INCLUDED_LAW_PAIRS)
_ACTIVE_LAW_PAIR_LABELS = dict(LAW_PAIR_LABELS)
_ACTIVE_CONFIG: dict[str, Any] = {}

def default_analysis_config() -> dict[str, Any]:
    return {
        "law_pair_groups": [dict(group) for group in DEFAULT_LAW_PAIR_GROUPS],
    }

def load_analysis_config(path: Path | None = None) -> dict[str, Any]:
    """Load optional run configuration, falling back to built-in benchmark scope."""
    candidate = path
    if candidate is None and DEFAULT_CONFIG_PATH.exists():
        candidate = DEFAULT_CONFIG_PATH
    config = default_analysis_config()
    if candidate is not None and candidate.exists():
        raw = parse_json_maybe(candidate.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError(f"Analysis config must be a JSON object: {candidate}")
        config.update(raw)
        config["config_path"] = str(candidate)
    return normalize_analysis_config(config)

def normalize_analysis_config(config: dict[str, Any]) -> dict[str, Any]:
    groups = config.get("law_pair_groups")
    if not isinstance(groups, list) or not groups:
        groups = DEFAULT_LAW_PAIR_GROUPS
    normalized_groups: list[dict[str, Any]] = []
    labels: dict[str, str] = {}
    included: set[str] = set()
    for group in groups:
        if not isinstance(group, dict):
            continue
        name = str(group.get("name") or "").strip()
        pairs = group.get("pairs")
        if not name or not isinstance(pairs, list):
            continue
        clean_pairs = [str(pair).strip() for pair in pairs if str(pair).strip()]
        if not clean_pairs:
            continue
        normalized_groups.append({"name": name, "pairs": clean_pairs})
        for pair in clean_pairs:
            included.add(pair)
            labels[pair] = name
    if not normalized_groups:
        normalized_groups = [dict(group) for group in DEFAULT_LAW_PAIR_GROUPS]
        included = set(DEFAULT_INCLUDED_LAW_PAIRS)
        labels = dict(LAW_PAIR_LABELS)
    out = dict(config)
    out["law_pair_groups"] = normalized_groups
    out["included_law_pairs"] = sorted(included)
    out["law_pair_labels"] = labels
    return out

def configure_analysis(config: dict[str, Any] | None = None) -> dict[str, Any]:
    global _ACTIVE_CONFIG, _ACTIVE_INCLUDED_LAW_PAIRS, _ACTIVE_LAW_PAIR_LABELS
    normalized = normalize_analysis_config(config or default_analysis_config())
    _ACTIVE_CONFIG = normalized
    _ACTIVE_INCLUDED_LAW_PAIRS = set(normalized["included_law_pairs"])
    _ACTIVE_LAW_PAIR_LABELS = dict(normalized["law_pair_labels"])
    return normalized

def active_analysis_config() -> dict[str, Any]:
    return dict(_ACTIVE_CONFIG or normalize_analysis_config(default_analysis_config()))

def included_law_pairs() -> set[str]:
    return set(_ACTIVE_INCLUDED_LAW_PAIRS)

def law_pair_labels() -> dict[str, str]:
    return dict(_ACTIVE_LAW_PAIR_LABELS)

def law_pair_label(law_pair: str) -> str:
    return _ACTIVE_LAW_PAIR_LABELS.get(law_pair, law_pair)

def sessions_with_deep_research_case_metrics(data: dict[str, list[dict[str, Any]]]) -> set[int]:
    sessions: set[int] = set()
    terminal_statuses = {"parsed", "completed", "succeeded", "success"}
    for row in data.get("deep_research_runs", []):
        sid = int_or_none(row.get("session_id"))
        if sid is None:
            continue
        if str(row.get("purpose") or "") != "case_group_metrics":
            continue
        if str(row.get("status") or "").lower() in terminal_statuses:
            sessions.add(sid)
    for ans in data.get("llm_answers", []):
        if ans.get("prompt_id") != "deep_research_case_metrics":
            continue
        sid = int_or_none(ans.get("session_id"))
        if sid is not None:
            sessions.add(sid)
    return sessions

def session_deep_research_enabled(data: dict[str, list[dict[str, Any]]], session: dict[str, Any]) -> bool:
    sid = int_or_none(session.get("session_id"))
    if sid is not None and sid in sessions_with_deep_research_case_metrics(data):
        return True
    return truthy(session.get("case_group_research_enabled"))

def session_deep_research_mode(data: dict[str, list[dict[str, Any]]], session: dict[str, Any]) -> str:
    return "dr" if session_deep_research_enabled(data, session) else "no_dr"

def write_run_config(out_dir: Path, config: dict[str, Any]) -> None:
    write_json(out_dir / "analysis_config.json", normalize_analysis_config(config))

def load_run_config(out_dir: Path, config_path: Path | None = None) -> dict[str, Any]:
    if config_path is not None:
        return load_analysis_config(config_path)
    saved = out_dir / "analysis_config.json"
    if saved.exists():
        return load_analysis_config(saved)
    return load_analysis_config(None)

def utc_now_slug() -> str:
    return dt.datetime.now(dt.UTC).strftime("%Y%m%d_%H%M%S")

def ensure_run_dirs(out_dir: Path) -> None:
    for name in OUTPUT_SUBDIRS:
        (out_dir / name).mkdir(parents=True, exist_ok=True)

def iso_week(value: Any) -> str:
    parsed = parse_datetime(value)
    if parsed is None:
        return "unknown"
    year, week, _day = parsed.isocalendar()
    return f"{year}-W{week:02d}"

def parse_datetime(value: Any) -> dt.datetime | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    text = text.replace("Z", "+00:00")
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%d",
    ):
        try:
            return dt.datetime.strptime(text[:26], fmt)
        except ValueError:
            pass
    try:
        return dt.datetime.fromisoformat(text)
    except ValueError:
        return None

def stable_hash(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def clear_generated_files(path: Path, patterns: Iterable[str]) -> None:
    """Remove generated files matching explicit patterns inside one output dir."""
    path.mkdir(parents=True, exist_ok=True)
    for pattern in patterns:
        for candidate in path.glob(pattern):
            if candidate.is_file():
                candidate.unlink()

def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows

def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        keys: list[str] = []
        for row in rows:
            for key in row:
                if key not in keys:
                    keys.append(key)
        fieldnames = keys
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: csv_safe(row.get(key)) for key in fieldnames})

def csv_safe(value: Any) -> Any:
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return value

def quote_ident(name: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        raise ValueError(f"Unsafe SQL identifier: {name!r}")
    return f'"{name}"'

class Db:
    def __init__(self, path: Path):
        self.path = path
        uri = f"file:{path.resolve()}?mode=ro"
        self.conn = sqlite3.connect(uri, uri=True)
        self.conn.row_factory = sqlite3.Row
        self._tables: set[str] | None = None
        self._columns: dict[str, set[str]] = {}

    def close(self) -> None:
        self.conn.close()

    @property
    def tables(self) -> set[str]:
        if self._tables is None:
            rows = self.conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            self._tables = {str(row["name"]) for row in rows}
        return self._tables

    def has_table(self, table: str) -> bool:
        return table in self.tables

    def columns(self, table: str) -> set[str]:
        if table not in self._columns:
            if not self.has_table(table):
                self._columns[table] = set()
            else:
                rows = self.conn.execute(f"PRAGMA table_info({quote_ident(table)})").fetchall()
                self._columns[table] = {str(row["name"]) for row in rows}
        return self._columns[table]

    def select(self, table: str, columns: list[str]) -> list[dict[str, Any]]:
        if not self.has_table(table):
            return []
        existing = self.columns(table)
        parts = []
        for col in columns:
            if col in existing:
                parts.append(f"{quote_ident(col)} AS {quote_ident(col)}")
            else:
                parts.append(f"NULL AS {quote_ident(col)}")
        sql = f"SELECT {', '.join(parts)} FROM {quote_ident(table)}"
        return [dict(row) for row in self.conn.execute(sql).fetchall()]

    def table_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for table in sorted(self.tables):
            try:
                row = self.conn.execute(f"SELECT COUNT(*) AS n FROM {quote_ident(table)}").fetchone()
                counts[table] = int(row["n"])
            except sqlite3.Error:
                counts[table] = -1
        return counts

    def schema(self) -> dict[str, list[dict[str, Any]]]:
        schema: dict[str, list[dict[str, Any]]] = {}
        for table in sorted(self.tables):
            rows = self.conn.execute(f"PRAGMA table_info({quote_ident(table)})").fetchall()
            schema[table] = [dict(row) for row in rows]
        return schema

def default_output_dir() -> Path:
    return Path("code_analysis") / "output" / f"historical_quality_{utc_now_slug()}"

def snapshot_db(db_path: Path, out_dir: Path) -> Path:
    ensure_run_dirs(out_dir)
    target = out_dir / "db_snapshot" / db_path.name
    shutil.copy2(db_path, target)
    return target

def build_manifest(
    db_path: Path,
    snapshot_path: Path,
    out_dir: Path,
    markers: list[dict[str, Any]],
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    config = configure_analysis(config)
    db = Db(snapshot_path)
    try:
        schema = db.schema()
        manifest = {
            "source_db": str(db_path),
            "snapshot_db": str(snapshot_path),
            "created_at_utc": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
            "schema_sha256": stable_hash(schema),
            "table_counts": db.table_counts(),
            "tables": sorted(schema),
            "feature_markers_count": len(markers),
            "analysis_config": config,
            "tool_version": "0.1.0",
        }
    finally:
        db.close()
    write_json(out_dir / "manifest.json", manifest)
    write_run_config(out_dir, config)
    return manifest

def load_feature_markers(path: Path | None) -> list[dict[str, Any]]:
    if path is None or not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        data = json.loads(text)
        return list(data.get("markers", []))
    return parse_simple_markers_yaml(text)

def parse_simple_markers_yaml(text: str) -> list[dict[str, Any]]:
    markers: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    in_affects = False
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped == "markers:":
            continue
        if stripped.startswith("- ") and not raw_line.startswith("      - "):
            if current:
                markers.append(current)
            current = {}
            in_affects = False
            stripped = stripped[2:].strip()
            if stripped:
                key, value = split_yaml_key_value(stripped)
                current[key] = parse_yaml_scalar(value)
            continue
        if current is None:
            continue
        if stripped.startswith("- ") and in_affects:
            current.setdefault("affects", []).append(parse_yaml_scalar(stripped[2:].strip()))
            continue
        key, value = split_yaml_key_value(stripped)
        if key == "affects" and value == "":
            current["affects"] = []
            in_affects = True
        else:
            current[key] = parse_yaml_scalar(value)
            in_affects = False
    if current:
        markers.append(current)
    return markers

def split_yaml_key_value(text: str) -> tuple[str, str]:
    if ":" not in text:
        return text, ""
    key, value = text.split(":", 1)
    return key.strip(), value.strip()

def parse_yaml_scalar(value: str) -> Any:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    return value

def extract(snapshot_path: Path, out_dir: Path, config: dict[str, Any] | None = None) -> dict[str, list[dict[str, Any]]]:
    config = configure_analysis(config or load_run_config(out_dir))
    db = Db(snapshot_path)
    try:
        schema_capabilities = {
            table: sorted(db.columns(table))
            for table in (
                "sessions", "laws", "llm_answers", "regulations", "processes",
                "case_groups", "process_steps", "session_total_costs_by_addressee",
                "tiles", "process_step_regulation_links",
                "regulation_process_links_by_addressee", "edit_audit_log",
                "deep_research_runs",
            )
        }
        tables = {
            "sessions": db.select("sessions", [
                "session_id", "app_session_id", "created_at", "llm_model",
                "used_llm_models", "current_law_id", "proposed_law_id",
                "law_diff_title", "cc_cost", "owner_user_id",
            ]),
            "laws": db.select("laws", [
                "document_id", "file_name", "text_length", "uploaded_at",
                "owner_user_id", "is_builtin",
            ]),
            "llm_answers": db.select("llm_answers", [
                "answer_id", "session_id", "prompt_id", "model", "answer_text",
                "prompt_text", "metadata", "input_tokens", "output_tokens",
                "hidden_thinking_tokens", "estimated_cost_usd",
                "provider_response_json", "answer_state", "state_reason",
                "created_at", "norm_addressee",
            ]),
            "regulations": db.select("regulations", [
                "regulation_id", "process_id", "session_id", "legal_citation",
                "description", "change_status", "created_at",
                "applies_to_administration", "applies_to_business",
                "applies_to_citizens", "is_business_information_obligation",
            ]),
            "processes": db.select("processes", [
                "process_id", "session_id", "process", "description",
                "change_status", "created_at", "cost", "norm_addressee",
            ]),
            "case_groups": db.select("case_groups", [
                "case_group_id", "process_id", "session_id", "case_group",
                "description", "change_status", "created_at",
                "addressees_current", "annual_frequency_current", "cases_current",
                "addressees_current_edited", "annual_frequency_current_edited",
                "cases_current_edited", "addressees_proposed",
                "annual_frequency_proposed", "cases_proposed",
                "addressees_proposed_edited", "annual_frequency_proposed_edited",
                "cases_proposed_edited", "cost", "last_edited_at",
                "norm_addressee", "case_metric_research_json",
            ]),
            "process_steps": db.select("process_steps", [
                "step_id", "case_group_id", "session_id", "step", "description",
                "change_status", "created_at", "previous_id", "next_id",
                "time_required_in_min_a_current", "time_required_in_min_b_current",
                "time_required_in_min_c_current", "time_required_in_min_d_current",
                "expenses_current", "time_required_in_min_a_proposed",
                "time_required_in_min_b_proposed", "time_required_in_min_c_proposed",
                "time_required_in_min_d_proposed", "expenses_proposed",
                "cost_current", "cost_proposed", "norm_addressee",
                "execution_per_case",
            ]),
            "costs": db.select("session_total_costs_by_addressee", [
                "session_id", "norm_addressee", "total_cost", "bureaucracy_cost",
                "total_time_minutes", "total_expenses",
            ]),
            "tiles": db.select("tiles", [
                "session_id", "norm_addressee", "id", "title", "text",
                "meta", "col", "row", "deletable",
            ]),
            "step_regulation_links": db.select("process_step_regulation_links", [
                "session_id", "norm_addressee", "step_id", "regulation_id",
            ]),
            "regulation_process_links": db.select("regulation_process_links_by_addressee", [
                "session_id", "norm_addressee", "regulation_id", "process_id",
            ]),
            "edit_audit_log": db.select("edit_audit_log", [
                "audit_id", "session_id", "entity_type", "entity_id",
                "field_name", "old_value", "new_value", "edited_at",
            ]),
            "deep_research_runs": db.select("deep_research_runs", [
                "research_run_id", "session_id", "purpose", "status",
                "created_at", "finished_at", "estimated_cost_usd",
            ]),
        }
    finally:
        db.close()

    tables = filter_analysis_scope(tables, config)
    extracted_dir = out_dir / "extracted"
    write_json(extracted_dir / "schema_capabilities.json", schema_capabilities)
    for name, rows in tables.items():
        write_jsonl(extracted_dir / f"{name}.jsonl", rows)
        write_csv(extracted_dir / f"{name}.csv", rows)
    return tables

def filter_analysis_scope(
    tables: dict[str, list[dict[str, Any]]],
    config: dict[str, Any] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Limit extracted data to the current meaningful law-pair scope."""
    if config is not None:
        configure_analysis(config)
    allowed_pairs = included_law_pairs()
    labels = law_pair_labels()
    sessions = tables.get("sessions", [])
    included_sessions = [
        row for row in sessions
        if law_pair_key_from_ids(row.get("current_law_id"), row.get("proposed_law_id")) in allowed_pairs
    ]
    excluded_sessions = [
        {
            **row,
            "law_pair": law_pair_key_from_ids(row.get("current_law_id"), row.get("proposed_law_id")),
            "exclusion_reason": "outside_current_analysis_law_pair_scope",
        }
        for row in sessions
        if law_pair_key_from_ids(row.get("current_law_id"), row.get("proposed_law_id")) not in allowed_pairs
    ]
    included_ids = {
        sid for sid in (int_or_none(row.get("session_id")) for row in included_sessions)
        if sid is not None
    }
    filtered: dict[str, list[dict[str, Any]]] = {}
    for name, rows in tables.items():
        if name == "sessions":
            filtered[name] = included_sessions
        elif name == "laws":
            filtered[name] = rows
        elif rows and "session_id" in rows[0]:
            filtered[name] = [
                row for row in rows
                if int_or_none(row.get("session_id")) in included_ids
            ]
        else:
            filtered[name] = rows
    filtered["excluded_sessions"] = excluded_sessions
    filtered["analysis_scope"] = [{
        "included_law_pairs": sorted(allowed_pairs),
        "included_law_pair_labels": labels,
        "law_pair_groups": active_analysis_config().get("law_pair_groups", []),
        "included_session_count": len(included_sessions),
        "excluded_session_count": len(excluded_sessions),
        "exclusion_rule": "Only meaningful benchmark law pairs are included; reversed, missing, or ad-hoc test pairs are excluded.",
    }]
    return filtered

def law_pair_key_from_ids(current_law_id: Any, proposed_law_id: Any) -> str:
    return f"{current_law_id or 'none'}->{proposed_law_id or 'none'}"

def load_extracted(out_dir: Path, config: dict[str, Any] | None = None) -> dict[str, list[dict[str, Any]]]:
    config = configure_analysis(config or load_run_config(out_dir))
    extracted_dir = out_dir / "extracted"
    names = [
        "sessions", "laws", "llm_answers", "regulations", "processes",
        "case_groups", "process_steps", "costs", "tiles",
        "step_regulation_links", "regulation_process_links", "edit_audit_log",
        "deep_research_runs",
    ]
    data = {name: read_jsonl(extracted_dir / f"{name}.jsonl") for name in names}
    data = filter_analysis_scope(data, config)
    schema_path = extracted_dir / "schema_capabilities.json"
    data["_schema_capabilities"] = parse_json_maybe(schema_path.read_text(encoding="utf-8")) if schema_path.exists() else {}
    return data

def has_source_column(data: dict[str, Any], table: str, column: str) -> bool:
    schema = data.get("_schema_capabilities")
    if not isinstance(schema, dict):
        return False
    cols = schema.get(table)
    return isinstance(cols, list) and column in cols

def parse_json_maybe(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    if not isinstance(value, str):
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return None

def group_by(rows: list[dict[str, Any]], key: str) -> dict[Any, list[dict[str, Any]]]:
    result: dict[Any, list[dict[str, Any]]] = {}
    for row in rows:
        value = row.get(key)
        if value is not None:
            result.setdefault(value, []).append(row)
    return result

def truthy(value: Any) -> bool:
    return value in (1, "1", True, "true", "True")

def int_or_none(value: Any) -> int | None:
    try:
        if value is None:
            return None
        return int(value)
    except (TypeError, ValueError):
        return None

def read_csv_dicts(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))

def num(value: Any) -> float:
    try:
        if value in (None, ""):
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0
