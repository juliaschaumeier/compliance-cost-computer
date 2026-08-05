from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

from common import clear_generated_files, stable_hash, write_csv, write_json


def adjudicate(packet_dir: Path, out_dir: Path, mode: str = "pending") -> dict[str, Any]:
    """Create a reproducible adjudication run record for review packets.

    `pending` stages one pending decision per packet.
    `rules` applies conservative deterministic decisions where the packet
    already contains enough machine-checkable evidence. Interpretation-heavy
    packets remain pending for human or fixed-prompt LLM review.
    """
    if mode not in {"pending", "rules"}:
        raise ValueError(f"Unsupported adjudication mode: {mode}")
    out_dir.mkdir(parents=True, exist_ok=True)
    clear_generated_files(out_dir, ("summary.json", "summary.md", "decisions.csv"))
    clear_generated_files(out_dir / "decisions", ("*.json",))
    packets = load_packets(packet_dir)
    decisions = [
        rule_decision(packet) if mode == "rules" else pending_decision(packet)
        for packet in packets
    ]
    reviewed_count = sum(1 for decision in decisions if decision["adjudication_status"] == "reviewed")
    pending_count = sum(1 for decision in decisions if decision["adjudication_status"] == "pending_review")

    for decision in decisions:
        write_json(out_dir / "decisions" / f"{decision['packet_id']}.json", decision)

    summary = {
        "created_at_utc": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
        "packet_dir": str(packet_dir),
        "output_dir": str(out_dir),
        "adjudicator": "none" if mode == "pending" else "deterministic_rules_v1",
        "status": "no_packets" if not packets else ("complete" if pending_count == 0 else "partial"),
        "packet_count": len(packets),
        "pending_count": pending_count,
        "reviewed_count": reviewed_count,
        "decision_counts": decision_counts(decisions),
        "notes": (
            "No review packets were present, so no LLM adjudication was needed."
            if not packets
            else adjudication_notes(mode, pending_count)
        ),
    }
    write_json(out_dir / "summary.json", summary)
    write_summary_md(out_dir, summary)
    write_csv(out_dir / "decisions.csv", decisions, decision_fields())
    return summary


def load_packets(packet_dir: Path) -> list[dict[str, Any]]:
    if not packet_dir.exists():
        return []
    packets: list[dict[str, Any]] = []
    for path in sorted(packet_dir.glob("*.json")):
        try:
            packet = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            packet = {
                "packet_id": path.stem,
                "load_error": "invalid_json_packet",
                "source_path": str(path),
            }
        packet.setdefault("packet_id", path.stem)
        packet.setdefault("source_path", str(path))
        packets.append(packet)
    return packets


def pending_decision(packet: dict[str, Any]) -> dict[str, Any]:
    packet_id = str(packet.get("packet_id") or "unknown_packet")
    return {
        "packet_id": packet_id,
        "issue_id": packet.get("issue_id"),
        "session_id": (packet.get("session") or {}).get("session_id") if isinstance(packet.get("session"), dict) else None,
        "app_session_id": (packet.get("session") or {}).get("app_session_id") if isinstance(packet.get("session"), dict) else None,
        "law_pair": (packet.get("session") or {}).get("law_pair") if isinstance(packet.get("session"), dict) else None,
        "model": (packet.get("session") or {}).get("model") if isinstance(packet.get("session"), dict) else None,
        "rule_based_classification": packet.get("rule_based_classification"),
        "deterministic_evidence_hash": packet.get("deterministic_evidence_hash"),
        "packet_hash": stable_hash(packet),
        "adjudication_status": "pending_review",
        "adjudicator": "none",
        "decision": "",
        "confidence": "",
        "rationale": "",
        "question_for_reviewer": packet.get("question_for_reviewer"),
    }

def rule_decision(packet: dict[str, Any]) -> dict[str, Any]:
    decision = pending_decision(packet)
    issue_id = str(packet.get("issue_id") or "")
    payload = packet.get("payload") if isinstance(packet.get("payload"), dict) else {}
    evidence = payload.get("evidence") if isinstance(payload.get("evidence"), dict) else {}
    judgement = str(payload.get("judgement") or "")
    detail_keys = payload.get("detail_keys") if isinstance(payload.get("detail_keys"), list) else []

    result = deterministic_decision(issue_id, judgement, evidence, detail_keys)
    if result is None:
        decision["rationale"] = "Left pending because the packet requires legal/content judgement beyond deterministic evidence."
        return decision
    decision.update({
        "adjudication_status": "reviewed",
        "adjudicator": "deterministic_rules_v1",
        "decision": result["decision"],
        "confidence": result["confidence"],
        "rationale": result["rationale"],
    })
    return decision

def deterministic_decision(
    issue_id: str,
    judgement: str,
    evidence: dict[str, Any],
    detail_keys: list[Any],
) -> dict[str, str] | None:
    if judgement == "hard_failure":
        if issue_id == "issue_02_unnecessary_addressee_steps":
            bucket = str(evidence.get("classification_bucket") or "")
            if bucket in {"no_applies_but_downstream_prompted", "no_applies_but_tiles_shown", "no_applies_prompt_and_tile"}:
                return reviewed("quality_issue", "high", "Zero-applicability addressee still had prompt and/or tile evidence.")
        if issue_id == "issue_03_json_truncation":
            parse_class = str(evidence.get("parse_class") or "")
            if parse_class in {"invalid_json", "hard_mid_content_truncation", "near_complete_missing_closer", "non_json_prose"}:
                return reviewed("quality_issue", "high", f"Raw answer has deterministic JSON quality failure: {parse_class}.")
        if issue_id == "issue_04_change_status_inconsistency":
            reason = str(evidence.get("reason") or "")
            if reason and reason != "changed_but_values_equal":
                return reviewed("quality_issue", "high", f"Deterministic current/proposed value mismatch for status rule: {reason}.")
        if issue_id == "issue_08_bureaucracy_cost":
            reason = str(evidence.get("reason") or "")
            if reason in {"raw_ip_not_persisted", "ip_present_bureaucracy_missing"}:
                return reviewed("quality_issue", "high", f"Information-obligation evidence conflicts with persisted bureaucracy-cost split: {reason}.")

    if judgement == "instability_signal":
        return reviewed(
            "instability_signal",
            "medium",
            "Repeated-run variance was confirmed as a reproducible diagnostic signal, but this does not decide which run is legally preferable.",
        )

    if judgement == "review_signal":
        if issue_id == "issue_02_unnecessary_addressee_steps":
            bucket = str(evidence.get("classification_bucket") or "")
            if bucket == "applies_but_downstream_says_not_applicable":
                return reviewed(
                    "quality_issue",
                    "high",
                    "Persisted applicability says the addressee is in scope, but downstream answer or tile content says there is nothing relevant to do.",
                )
            if bucket == "missing_regulation_context_but_downstream_work":
                return reviewed(
                    "incomplete_state_signal",
                    "medium",
                    "Downstream work exists without persisted regulation context; this is useful workflow evidence but not enough to classify the content itself as wrong.",
                )
        if issue_id == "issue_03_json_truncation":
            parse_class = str(evidence.get("parse_class") or "")
            if parse_class == "empty_or_invalid_top_level":
                return reviewed(
                    "quality_issue",
                    "high",
                    "The answer parsed as JSON but returned an empty or unusable required root payload where the workflow expected entities.",
                )
        if issue_id == "issue_04_change_status_inconsistency":
            reason = str(evidence.get("reason") or "")
            if reason == "changed_but_values_equal":
                return reviewed(
                    "status_value_review_signal",
                    "medium",
                    "The entity is marked changed while current/proposed numeric values are equal; this can reflect non-numeric legal/text changes, so it is a diagnostic signal rather than a decisive quality failure.",
                )
        if issue_id == "issue_08_bureaucracy_cost":
            reason = str(evidence.get("reason") or "")
            if reason == "suspicious_all_business_cost_marked_bureaucracy":
                return reviewed(
                    "cost_split_review_signal",
                    "medium",
                    "Nearly all business cost is marked as bureaucracy cost despite mixed regulation evidence; this is a strong cost-split diagnostic but still needs content/legal review.",
                )
            if reason == "ip_present_zero_bureaucracy_cost":
                return reviewed(
                    "cost_split_review_signal",
                    "low",
                    "Business information obligations are linked to process steps, but current/proposed effort and case values net to zero bureaucracy-cost delta.",
                )

    if issue_id == "issue_03_json_truncation" and "current_contract_mismatch" in {str(key) for key in detail_keys}:
        return reviewed(
            "historical_contract_mismatch",
            "high",
            "The answer matched the historical prompt root but not the current parser contract.",
        )
    return None

def reviewed(decision: str, confidence: str, rationale: str) -> dict[str, str]:
    return {"decision": decision, "confidence": confidence, "rationale": rationale}

def decision_counts(decisions: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for decision in decisions:
        key = str(decision.get("decision") or decision.get("adjudication_status") or "unknown")
        counts[key] = counts.get(key, 0) + 1
    return counts

def adjudication_notes(mode: str, pending_count: int) -> str:
    if mode == "pending":
        return "Packets were staged for human or fixed-prompt LLM adjudication; no LLM was called by this command."
    if pending_count:
        return "Conservative deterministic rules adjudicated clear cases; interpretive packets remain pending. No LLM was called."
    return "Conservative deterministic rules adjudicated all packets. No LLM was called."


def decision_fields() -> list[str]:
    return [
        "packet_id",
        "issue_id",
        "session_id",
        "app_session_id",
        "law_pair",
        "model",
        "rule_based_classification",
        "deterministic_evidence_hash",
        "packet_hash",
        "adjudication_status",
        "adjudicator",
        "decision",
        "confidence",
        "rationale",
        "question_for_reviewer",
    ]


def write_summary_md(out_dir: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Adjudication Summary",
        "",
        f"- Status: `{summary['status']}`",
        f"- Review packets: `{summary['packet_count']}`",
        f"- Pending decisions: `{summary['pending_count']}`",
        f"- Reviewed decisions: `{summary['reviewed_count']}`",
        f"- Adjudicator: `{summary['adjudicator']}`",
        f"- Decision counts: `{summary.get('decision_counts', {})}`",
        "",
        summary["notes"],
    ]
    (out_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
