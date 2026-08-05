import unittest
from pathlib import Path
import json
import tempfile

import adjudication
import common
import historical_quality as hq
import issues
import reporting


class HistoricalQualityTests(unittest.TestCase):
    def test_default_analysis_scope_filters_to_meaningful_law_pairs(self):
        tables = {
            "sessions": [
                {"session_id": 1, "current_law_id": 1, "proposed_law_id": 2},
                {"session_id": 2, "current_law_id": 2, "proposed_law_id": 1},
                {"session_id": 3, "current_law_id": 3, "proposed_law_id": 4},
                {"session_id": 4, "current_law_id": 7, "proposed_law_id": 8},
                {"session_id": 5, "current_law_id": None, "proposed_law_id": 4},
            ],
            "laws": [{"document_id": 1}, {"document_id": 2}],
            "llm_answers": [
                {"session_id": 1, "answer_id": 10},
                {"session_id": 2, "answer_id": 20},
                {"session_id": 3, "answer_id": 30},
                {"session_id": 4, "answer_id": 40},
            ],
            "regulations": [{"session_id": 1}, {"session_id": 2}, {"session_id": 3}, {"session_id": 4}],
        }

        filtered = common.filter_analysis_scope(tables)

        self.assertEqual([row["session_id"] for row in filtered["sessions"]], [1, 3, 4])
        self.assertEqual([row["answer_id"] for row in filtered["llm_answers"]], [10, 30, 40])
        self.assertEqual(len(filtered["regulations"]), 3)
        self.assertEqual(len(filtered["laws"]), 2)
        self.assertEqual([row["law_pair"] for row in filtered["excluded_sessions"]], ["2->1", "none->4"])
        self.assertEqual(filtered["analysis_scope"][0]["included_session_count"], 3)

    def test_analysis_scope_can_be_configured_for_local_law_ids(self):
        tables = {
            "sessions": [
                {"session_id": 1, "current_law_id": 20, "proposed_law_id": 21},
                {"session_id": 2, "current_law_id": 1, "proposed_law_id": 2},
            ],
            "llm_answers": [{"session_id": 1, "answer_id": 10}, {"session_id": 2, "answer_id": 20}],
        }
        config = common.normalize_analysis_config({
            "law_pair_groups": [{"name": "local benchmark", "pairs": ["20->21"]}],
        })

        try:
            filtered = common.filter_analysis_scope(tables, config)
            self.assertEqual([row["session_id"] for row in filtered["sessions"]], [1])
            self.assertEqual([row["answer_id"] for row in filtered["llm_answers"]], [10])
            self.assertEqual(filtered["analysis_scope"][0]["included_law_pair_labels"], {"20->21": "local benchmark"})
        finally:
            common.configure_analysis(common.default_analysis_config())

    def test_json_missing_bracket_is_near_complete(self):
        result = hq.classify_json_answer('{"prozesse": [{"x": 1}]', "process_compilation")
        self.assertEqual(result["parse_class"], "near_complete_missing_closer")
        self.assertEqual(result["repair_suffix"], "}")

    def test_json_missing_quote_is_hard_truncation(self):
        result = hq.classify_json_answer('{"prozesse": [{"name": "halb', "process_compilation")
        self.assertEqual(result["parse_class"], "hard_mid_content_truncation")

    def test_empty_required_top_level_is_schema_failure(self):
        result = hq.classify_json_answer('{"prozesse": []}', "process_compilation")
        self.assertEqual(result["parse_class"], "empty_or_invalid_top_level")

    def test_prompt_contract_infers_prozesse_from_prompt_format_block(self):
        answer = {
            "prompt_id": "process_step_analysis",
            "prompt_text": """
                Geben Sie nur und ausschliesslich JSON im folgenden Format zurueck:
                {{
                  "normadressat": "business",
                  "prozesse": [{{"fallgruppen": []}}]
                }}
            """,
            "metadata": None,
        }
        contract = issues.prompt_contract_info(answer)
        self.assertEqual(contract["prompt_required_root_key"], "prozesse")
        self.assertEqual(contract["prompt_contract_kind"], "prompt_level_json_object")
        self.assertEqual(contract["prompt_requests_json_only"], 1)

    def test_prompt_contract_uses_provider_response_format_metadata(self):
        answer = {
            "prompt_id": "case_group_development",
            "prompt_text": '{"prozesse": []}',
            "metadata": '{"response_format_requested": {"type": "json_object"}, "response_format_used": {"type": "json_object"}}',
        }
        contract = issues.prompt_contract_info(answer)
        self.assertEqual(contract["prompt_contract_kind"], "provider_json_object")
        self.assertEqual(contract["provider_response_format_used"], '{"type": "json_object"}')

    def test_prompt_contract_uses_last_json_instruction_not_input_payload(self):
        prompt = """
            Eingabe: {"vorgaben": [{"beschreibung": "x"}]}
            Geben Sie nur und ausschliesslich JSON zurueck. Fuellen Sie ausschliesslich
            das Feld `taetigkeiten` im folgenden vorbefuellten Skelett aus.
            {"normadressat": "business", "fallgruppen": [{"fallgruppen_id": 1, "taetigkeiten": []}]}
        """
        contract = issues.prompt_contract_info({
            "prompt_id": "process_step_analysis",
            "prompt_text": prompt,
            "metadata": '{"response_format_requested": "json_schema", "response_format_used": "json_schema"}',
        })
        self.assertEqual(contract["prompt_required_root_key"], "fallgruppen")
        self.assertEqual(contract["prompt_contract_kind"], "provider_json_schema")

    def test_prompt_contract_infers_current_flat_structure_wording(self):
        prompt = """
            Eingabe: {"vorgaben": [{"beschreibung": "x"}]}
            Geben Sie nur und ausschliesslich JSON in genau dieser Struktur zurueck:
            {"normadressat": "business", "fallgruppen": [{"fallgruppen_id": 1, "kennzahlen": {}}]}
        """
        contract = issues.prompt_contract_info({
            "prompt_id": "cases_calculation",
            "prompt_text": prompt,
            "metadata": None,
        })
        self.assertEqual(contract["prompt_required_root_key"], "fallgruppen")

    def test_addressee_detection_does_not_guess_from_generic_prompt(self):
        answer = {
            "prompt_id": "process_compilation",
            "prompt_text": "Analysieren Sie Bürger, Wirtschaft und Verwaltung.",
            "answer_text": "{}",
            "metadata": None,
            "norm_addressee": None,
        }
        self.assertIsNone(hq.answer_addressee(answer))

    def test_addressee_detection_uses_explicit_prompt_marker(self):
        answer = {
            "prompt_id": "process_compilation",
            "prompt_text": "Dieser Lauf betrifft nur den Normadressaten Wirtschaft.",
            "answer_text": "{}",
            "metadata": None,
            "norm_addressee": None,
        }
        self.assertEqual(hq.answer_addressee(answer), "business")

    def test_structure_fingerprint_ignores_db_ids(self):
        data = {
            "regulations": [
                {"session_id": 1, "legal_citation": "§ 1", "description": "Pflicht"},
                {"session_id": 2, "legal_citation": "§ 1", "description": "Pflicht"},
            ],
            "processes": [
                {"session_id": 1, "process_id": 10, "norm_addressee": "business", "process": "Meldung"},
                {"session_id": 2, "process_id": 99, "norm_addressee": "business", "process": "Meldung"},
            ],
            "case_groups": [
                {"session_id": 1, "case_group_id": 20, "process_id": 10, "norm_addressee": "business", "case_group": "Standardfall"},
                {"session_id": 2, "case_group_id": 88, "process_id": 99, "norm_addressee": "business", "case_group": "Standardfall"},
            ],
            "process_steps": [
                {"session_id": 1, "case_group_id": 20, "norm_addressee": "business", "step": "Daten erfassen"},
                {"session_id": 2, "case_group_id": 88, "norm_addressee": "business", "step": "Daten erfassen"},
            ],
        }
        self.assertEqual(hq.structure_fingerprint(data, 1), hq.structure_fingerprint(data, 2))

    def test_repeated_run_structure_groups_split_deep_research_mode(self):
        sessions = [
            {"session_id": 1, "created_at": "2026-01-01", "current_law_id": 1, "proposed_law_id": 2, "llm_model": "m"},
            {"session_id": 2, "created_at": "2026-01-02", "current_law_id": 1, "proposed_law_id": 2, "llm_model": "m"},
            {"session_id": 3, "created_at": "2026-01-03", "current_law_id": 1, "proposed_law_id": 2, "llm_model": "m", "case_group_research_enabled": True},
            {"session_id": 4, "created_at": "2026-01-04", "current_law_id": 1, "proposed_law_id": 2, "llm_model": "m", "case_group_research_enabled": True},
        ]
        data = {
            "sessions": sessions,
            "regulations": [{"session_id": session["session_id"], "legal_citation": f"§ {session['session_id']}", "description": "x"} for session in sessions],
            "processes": [],
            "case_groups": [],
            "process_steps": [],
            "costs": [],
        }

        groups = issues.repeated_session_groups(data)

        self.assertEqual(sorted(groups), [("1->2", "m", "dr"), ("1->2", "m", "no_dr")])
        self.assertEqual([row["session_id"] for row in groups[("1->2", "m", "no_dr")]], [1, 2])
        self.assertEqual([row["session_id"] for row in groups[("1->2", "m", "dr")]], [3, 4])

    def test_session_cost_case_points_marks_deep_research_sessions(self):
        data = {
            "sessions": [
                {
                    "session_id": 1,
                    "app_session_id": "A",
                    "created_at": "2026-07-30 10:00:00",
                    "current_law_id": 1,
                    "proposed_law_id": 2,
                    "llm_model": "gemini-3.5-flash",
                },
                {
                    "session_id": 2,
                    "app_session_id": "B",
                    "created_at": "2026-07-30 11:00:00",
                    "current_law_id": 1,
                    "proposed_law_id": 2,
                    "llm_model": "gemini-3.5-flash",
                },
            ],
            "costs": [
                {"session_id": 1, "total_cost": 10},
                {"session_id": 2, "total_cost": 20},
            ],
            "case_groups": [
                {
                    "session_id": 1,
                    "cases_proposed": 100,
                },
                {
                    "session_id": 2,
                    "cases_proposed": 100,
                },
            ],
            "deep_research_runs": [
                {
                    "session_id": 1,
                    "purpose": "case_group_metrics",
                    "status": "parsed",
                }
            ],
        }

        rows = reporting.session_cost_case_points(data)

        self.assertEqual(
            {row["app_session_id"]: row["deep_research_enabled"] for row in rows},
            {"A": 1, "B": 0},
        )

    def test_scatter_svg_outlines_deep_research_points(self):
        rows = [
            {
                "session_id": 1,
                "created_at": "2026-07-30 10:00:00",
                "week": "2026-W31",
                "law_pair": "1->2",
                "model": "gemini-3.5-flash",
                "total_cost": 10,
                "deep_research_enabled": 1,
            },
            {
                "session_id": 2,
                "created_at": "2026-07-30 11:00:00",
                "week": "2026-W31",
                "law_pair": "1->2",
                "model": "gemini-3.5-flash",
                "total_cost": 20,
                "deep_research_enabled": 0,
            },
        ]

        svg = reporting.scatter_svg("Cost", "desc", rows, "total_cost", "cost")

        self.assertIn("Deep Research", svg)
        self.assertIn("stroke='#000' stroke-width='2.1'", svg)
        self.assertEqual(svg.count("stroke='#000' stroke-width='2.1'"), 1)

    def test_issue_02_old_schema_is_not_no_applies_failure(self):
        data = {
            "_schema_capabilities": {"regulations": ["session_id", "legal_citation"]},
            "sessions": [{"session_id": 1, "created_at": "2026-01-01", "app_session_id": "s1"}],
            "regulations": [{"session_id": 1, "legal_citation": "§ 1"}],
            "llm_answers": [
                {
                    "answer_id": 1,
                    "session_id": 1,
                    "prompt_id": "process_compilation",
                    "prompt_text": "Dieser Lauf betrifft nur den Normadressaten Wirtschaft.",
                    "answer_text": '{"prozesse": [{"prozess_bezeichnung": "X"}]}',
                    "metadata": None,
                    "norm_addressee": None,
                }
            ],
            "processes": [],
            "case_groups": [],
            "process_steps": [],
            "costs": [],
            "tiles": [],
        }
        self.assertEqual(hq.analyze_issue_02(data, out_dir=None), [])

    def test_issue_02_missing_regulation_context_is_ambiguous(self):
        data = {
            "_schema_capabilities": {"regulations": ["session_id", "applies_to_business", "applies_to_administration", "applies_to_citizens"]},
            "sessions": [{"session_id": 1, "created_at": "2026-01-01", "app_session_id": "s1"}],
            "regulations": [],
            "llm_answers": [
                {
                    "answer_id": 1,
                    "session_id": 1,
                    "prompt_id": "process_compilation",
                    "answer_text": '{"prozesse": [{"prozess_bezeichnung": "X"}]}',
                    "answer_state": "active",
                    "state_reason": "session_updated",
                    "norm_addressee": "business",
                }
            ],
            "processes": [],
            "case_groups": [],
            "process_steps": [],
            "costs": [],
            "tiles": [],
        }
        findings = hq.analyze_issue_02(data, out_dir=None)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["classification"], "ambiguous")
        self.assertEqual(findings[0]["evidence"]["classification_bucket"], "missing_regulation_context_but_downstream_work")

    def test_issue_02_zero_applies_prompt_only_form_failure_bucket(self):
        data = {
            "_schema_capabilities": {"regulations": ["session_id", "applies_to_business", "applies_to_administration", "applies_to_citizens"]},
            "sessions": [{"session_id": 1, "created_at": "2026-01-01", "app_session_id": "s1"}],
            "regulations": [{"session_id": 1, "applies_to_business": 0, "applies_to_administration": 1, "applies_to_citizens": 0}],
            "llm_answers": [
                {
                    "answer_id": 1,
                    "session_id": 1,
                    "prompt_id": "process_compilation",
                    "answer_text": "",
                    "answer_state": "invalid",
                    "state_reason": "query_failed",
                    "norm_addressee": "business",
                }
            ],
            "processes": [],
            "case_groups": [],
            "process_steps": [],
            "costs": [],
            "tiles": [],
        }
        findings = hq.analyze_issue_02(data, out_dir=None)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["evidence"]["classification_bucket"], "no_applies_prompt_only_query_or_form_failure")

    def test_issue_02_metric_period_not_applicable_is_not_nothing_to_do(self):
        answer = {
            "prompt_id": "cases_calculation",
            "answer_text": (
                '{"prozesse": [{"fallgruppen": [{"fallgruppen_id": 1, '
                '"anzahl_betroffene_gueltig": "", '
                '"anzahl_betroffene_vorschlag": "500", '
                '"erklaerungen": {"anzahl_betroffene_gueltig": "Nicht anwendbar, da neu eingefuehrt."}}]}]}'
            ),
        }
        self.assertFalse(issues.answer_indicates_no_downstream_work(answer))

    def test_issue_02_structural_no_case_group_is_nothing_to_do(self):
        answer = {
            "prompt_id": "case_group_development",
            "answer_text": (
                '{"prozesse": [{"prozess_id": 1, "fallgruppen": ['
                '{"fallgruppe_bezeichnung": "Keine Fallgruppe", '
                '"fallgruppe_beschreibung": "Keine fallgruppenbezogene Differenzierung erforderlich."}'
                ']}]}'
            ),
        }
        self.assertTrue(issues.answer_indicates_no_downstream_work(answer))

    def test_issue_02_metric_explanation_wording_is_separate_bucket(self):
        raw = '{"erklaerungen": {"anzahl_betroffene_gueltig": "Kein Erfüllungsaufwand in der geltenden Rechtslage."}}'
        rows = issues.not_applicable_wording_rows(
            session={"session_id": 1, "created_at": "2026-01-01"},
            addressee="business",
            applicable_regulation_count=1,
            applicability_context="positive_applicable_regulations",
            source_type="llm_answer",
            source_id=1,
            prompt_id="cases_calculation",
            model="m",
            title="",
            text=raw,
        )
        self.assertEqual(rows[0]["wording_bucket"], "metric_explanation_wording")
        self.assertIn("erklaerungen", rows[0]["match_path"])

    def test_issue_02_phrase_excerpt_uses_normalized_offsets(self):
        excerpt = issues.phrase_excerpt("Änderung mit viel Text. Keine Tätigkeiten erforderlich.", "keine taetigkeiten", radius=8)
        self.assertIn("keine taetigkeiten", excerpt)

    def test_issue_02_wording_ignores_reasoning_when_json_is_extractable(self):
        raw = '<think>Wir haben keine Taetigkeiten, die wegfallen. Beispiel: {"x": 1}</think>```json\n{"prozesse": [{"fallgruppen": [{"taetigkeiten": [{"taetigkeit": "Pruefen"}]}]}]}\n```'
        rows = issues.not_applicable_wording_rows(
            session={"session_id": 1, "created_at": "2026-01-01"},
            addressee="administration",
            applicable_regulation_count=1,
            applicability_context="positive_applicable_regulations",
            source_type="llm_answer",
            source_id=1,
            prompt_id="process_step_analysis",
            model="m",
            title="",
            text=raw,
        )
        self.assertEqual(rows, [])

    def test_adjudication_no_packets_writes_noop_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            summary = adjudication.adjudicate(root / "review_packets", root / "adjudication")
            self.assertEqual(summary["status"], "no_packets")
            self.assertEqual(summary["packet_count"], 0)
            self.assertTrue((root / "adjudication" / "summary.md").exists())
            self.assertTrue((root / "adjudication" / "decisions.csv").exists())

    def test_rules_adjudication_reviews_clear_json_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            packet_dir = root / "review_packets"
            packet_dir.mkdir()
            packet = {
                "packet_id": "p1",
                "issue_id": "issue_03_json_truncation",
                "session": {"session_id": 1},
                "rule_based_classification": "bad",
                "deterministic_evidence_hash": "abc",
                "question_for_reviewer": "q",
                "payload": {
                    "judgement": "hard_failure",
                    "evidence": {"parse_class": "invalid_json"},
                },
            }
            (packet_dir / "p1.json").write_text(json.dumps(packet), encoding="utf-8")
            summary = adjudication.adjudicate(packet_dir, root / "adjudication", mode="rules")
            self.assertEqual(summary["status"], "complete")
            self.assertEqual(summary["reviewed_count"], 1)
            self.assertEqual(summary["decision_counts"], {"quality_issue": 1})

    def test_rules_adjudication_reviews_changed_equal_values_as_signal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            packet_dir = root / "review_packets"
            packet_dir.mkdir()
            packet = {
                "packet_id": "p1",
                "issue_id": "issue_04_change_status_inconsistency",
                "session": {"session_id": 1},
                "rule_based_classification": "bad",
                "deterministic_evidence_hash": "abc",
                "question_for_reviewer": "q",
                "payload": {
                    "judgement": "review_signal",
                    "evidence": {"reason": "changed_but_values_equal"},
                },
            }
            (packet_dir / "p1.json").write_text(json.dumps(packet), encoding="utf-8")
            summary = adjudication.adjudicate(packet_dir, root / "adjudication", mode="rules")
            self.assertEqual(summary["status"], "complete")
            self.assertEqual(summary["pending_count"], 0)
            self.assertEqual(summary["decision_counts"], {"status_value_review_signal": 1})

    def test_variance_findings_are_diagnostic_not_hard_failure(self):
        row = {"issue_id": "issue_05_structure_consistency", "evidence": {}}
        self.assertEqual(reporting.finding_session_judgement(row), "instability_signal")

    def test_broken_json_is_hard_failure(self):
        row = {"issue_id": "issue_03_json_truncation", "evidence": {"parse_class": "invalid_json"}}
        self.assertEqual(reporting.finding_session_judgement(row), "hard_failure")

    def test_process_step_flat_fallgruppen_shape_is_current_contract(self):
        answer = {
            "answer_id": 1,
            "session_id": 1,
            "prompt_id": "process_step_analysis",
            "answer_text": '{"fallgruppen": [{"fallgruppen_id": 12, "taetigkeiten": [{"taetigkeit": "A"}]}]}',
            "answer_state": "active",
            "state_reason": "session_updated",
            "norm_addressee": "business",
        }
        session = {"session_id": 1, "app_session_id": "s1"}
        cls = hq.classify_json_answer(answer["answer_text"], "process_step_analysis")
        row = issues.process_step_shape_row(answer, session, cls)
        self.assertEqual(cls["parse_class"], "valid_json")
        self.assertEqual(cls["required_key"], "fallgruppen")
        self.assertEqual(row["shape_class"], "expected_flat_fallgruppen")
        self.assertEqual(row["current_code_acceptance"], "accept")
        self.assertEqual(row["top_level_flat_step_count"], 1)

    def test_analyze_issue_03_accepts_current_flat_contract(self):
        data = {
            "sessions": [{"session_id": 1, "app_session_id": "s1", "created_at": "2026-01-01"}],
            "llm_answers": [
                {
                    "answer_id": 1,
                    "session_id": 1,
                    "prompt_id": "cases_calculation",
                    "created_at": "2026-01-01 10:00:00",
                    "answer_state": "active",
                    "state_reason": "session_updated",
                    "model": "m",
                    "norm_addressee": "business",
                    "prompt_text": """
                        Eingabe: {"prozesse": [{"fallgruppen": [{"fallgruppen_id": 1}]}]}
                        Geben Sie nur und ausschliesslich JSON in genau dieser Struktur zurueck:
                        {"normadressat": "business", "fallgruppen": [{"fallgruppen_id": 1, "kennzahlen": {}}]}
                    """,
                    "answer_text": '{"normadressat": "business", "fallgruppen": [{"fallgruppen_id": 1, "kennzahlen": {"cases_current": 0}}]}',
                    "metadata": None,
                }
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            findings = issues.analyze_issue_03(data, Path(tmp))
            rows = common.read_csv_dicts(Path(tmp) / "findings" / "issue_03_answer_quality.csv")
        self.assertEqual(findings, [])
        self.assertNotIn("expected_entity_count", rows[0])
        self.assertNotIn("returned_entity_count", rows[0])

    def test_analyze_issue_03_includes_law_summary_contract(self):
        data = {
            "sessions": [{"session_id": 1, "app_session_id": "s1", "created_at": "2026-01-01"}],
            "llm_answers": [
                {
                    "answer_id": 1,
                    "session_id": 1,
                    "prompt_id": "law_summary",
                    "created_at": "2026-01-01 10:00:00",
                    "answer_state": "active",
                    "state_reason": "session_updated",
                    "model": "m",
                    "answer_text": json.dumps({
                        "title": "Kurztitel",
                        "blurb": "Ein Satz.",
                        "summary": "Ausfuehrliche Zusammenfassung.",
                    }),
                    "metadata": None,
                },
                {
                    "answer_id": 2,
                    "session_id": 1,
                    "prompt_id": "law_summary",
                    "created_at": "2026-01-01 10:01:00",
                    "answer_state": "invalid",
                    "state_reason": "session_update_failed: expected summary fields",
                    "model": "m",
                    "answer_text": json.dumps({
                        "title": "Kurztitel",
                        "summary": "Ausfuehrliche Zusammenfassung.",
                    }),
                    "metadata": None,
                },
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            findings = issues.analyze_issue_03(data, Path(tmp))
            rows = common.read_csv_dicts(Path(tmp) / "findings" / "issue_03_answer_quality.csv")

        self.assertEqual([row["answer_id"] for row in rows], ["1", "2"])
        self.assertEqual(rows[0]["parse_class"], "valid_json")
        self.assertEqual(rows[0]["prompt_required_root_key"], "summary")
        self.assertEqual(rows[1]["parse_class"], "wrong_top_level_key")
        self.assertEqual(len(findings), 1)

    def test_analyze_issue_03_writes_raw_change_status_diagnostic(self):
        data = {
            "sessions": [{"session_id": 1, "app_session_id": "s1", "created_at": "2026-01-01"}],
            "llm_answers": [
                {
                    "answer_id": 1,
                    "session_id": 1,
                    "prompt_id": "process_step_analysis",
                    "created_at": "2026-01-01 10:00:00",
                    "answer_state": "active",
                    "state_reason": "session_updated",
                    "model": "m",
                    "norm_addressee": "business",
                    "answer_text": json.dumps({
                        "normadressat": "business",
                        "fallgruppen": [
                            {
                                "fallgruppen_id": 1,
                                "taetigkeiten": [
                                    {"taetigkeit": "A", "aenderungsstatus": "eingefuehrt"},
                                    {"taetigkeit": "B", "aenderungsstatus": "geandert"},
                                    {"taetigkeit": "C"},
                                ],
                            }
                        ],
                    }),
                    "metadata": None,
                }
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            issues.analyze_issue_03(data, Path(tmp))
            rows = common.read_csv_dicts(Path(tmp) / "findings" / "issue_04_raw_change_status_quality.csv")

        self.assertEqual([row["entity_name"] for row in rows], ["A", "B", "C"])
        self.assertEqual([row["status_bucket"] for row in rows], ["present_valid", "present_unrecognized", "missing"])
        self.assertEqual(rows[1]["raw_status_value"], "geandert")
        self.assertEqual(rows[2]["raw_status_key"], "")

    def test_raw_change_status_diagnostic_reads_case_group_singular_name_key(self):
        answer = {
            "answer_id": 1,
            "session_id": 1,
            "prompt_id": "case_group_development",
            "created_at": "2026-01-01 10:00:00",
            "answer_state": "active",
            "state_reason": "session_updated",
            "model": "m",
            "norm_addressee": "business",
            "answer_text": json.dumps({
                "normadressat": "business",
                "prozesse": [
                    {
                        "prozess_id": 1,
                        "fallgruppen": [
                            {
                                "fallgruppe_bezeichnung": "Standardfall",
                                "fallgruppe_beschreibung": "x",
                                "aenderungsstatus": "geaendert",
                            }
                        ],
                    }
                ],
            }),
            "metadata": None,
        }
        cls, _contract = issues.classify_answer_by_prompt_contract(answer)
        rows = issues.raw_change_status_quality_rows(answer, {"app_session_id": "s1"}, cls)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["entity_type"], "case_group")
        self.assertEqual(rows[0]["entity_name"], "Standardfall")
        self.assertEqual(rows[0]["status_bucket"], "present_valid")

    def test_analyze_issue_03_ignores_markdown_export_as_json_failure(self):
        data = {
            "sessions": [{"session_id": 1, "app_session_id": "s1", "created_at": "2026-01-01"}],
            "llm_answers": [
                {
                    "answer_id": 1,
                    "session_id": 1,
                    "prompt_id": "compliance_text_extraction",
                    "created_at": "2026-01-01 10:00:00",
                    "answer_state": "active",
                    "state_reason": "session_updated",
                    "model": "m",
                    "answer_text": "# E. Erfuellungsaufwand\n\nMarkdown text",
                    "metadata": None,
                }
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            findings = issues.analyze_issue_03(data, Path(tmp))
        self.assertEqual(findings, [])

    def test_backend_rejection_group_summarizes_state_reason(self):
        answer = {
            "answer_state": "invalid",
            "state_reason": "session_update_failed: Missing process steps for fallgruppen_id values: 536, 537",
        }
        self.assertEqual(issues.answer_db_outcome(answer), "rejected_by_session_update")
        self.assertEqual(issues.backend_rejection_group(answer["state_reason"]), "missing_case_group_ids")

    def test_step_6_flat_fallgruppen_shape_is_current_contract(self):
        answer = {
            "answer_id": 1,
            "session_id": 1,
            "prompt_id": "effort_calculation",
            "answer_text": '{"fallgruppen": [{"fallgruppen_id": 12, "taetigkeiten": [{"taetigkeiten_id": 3, "zeitaufwand_vorschlag": 5}]}]}',
            "answer_state": "active",
            "state_reason": "session_updated",
            "norm_addressee": "business",
        }
        session = {"session_id": 1, "app_session_id": "s1"}
        cls, _contract = issues.classify_answer_by_prompt_contract(answer)
        row = issues.step_6_shape_row(answer, session, cls)
        self.assertEqual(cls["parse_class"], "valid_json")
        self.assertEqual(row["shape_class"], "expected_flat_fallgruppen")
        self.assertEqual(row["current_code_acceptance"], "accept")
        self.assertEqual(row["metric_entity_count"], 1)

    def test_compliance_export_quality_is_markdown_specific(self):
        answer = {
            "answer_id": 7,
            "session_id": 1,
            "prompt_id": "compliance_text_extraction",
            "answer_text": "# E. Erfuellungsaufwand\n\n| lfd. Nr. | Norm |\n| --- | --- |\n| 1 | § 1 |",
            "answer_state": "active",
            "state_reason": "session_updated",
        }
        row = issues.compliance_export_quality_row(answer, {"session_id": 1, "app_session_id": "s1"})
        self.assertEqual(row["quality_class"], "expected_markdown")
        self.assertTrue(row["has_markdown_table"])

    def test_raw_change_status_summary_keeps_prompt_and_entity_context(self):
        rows = [
            {"prompt_id": "process_step_analysis", "entity_type": "process_step", "status_bucket": "missing", "answer_id": 1},
            {"prompt_id": "process_step_analysis", "entity_type": "process_step", "status_bucket": "present_valid", "answer_id": 2, "raw_status_value": "geaendert"},
        ]
        summary = reporting.raw_change_status_summary(rows)
        self.assertEqual(
            [(row["prompt_id"], row["entity_type"], row["status_bucket"], row["count"]) for row in summary],
            [
                ("process_step_analysis", "process_step", "missing", 1),
                ("process_step_analysis", "process_step", "present_valid", 1),
            ],
        )

    def test_compliance_export_quality_flags_leaked_json(self):
        answer = {
            "answer_id": 8,
            "session_id": 1,
            "prompt_id": "compliance_text_extraction",
            "answer_text": '```json\n{"session_json": {}}\n```',
            "answer_state": "active",
            "state_reason": "session_updated",
        }
        row = issues.compliance_export_quality_row(answer, {"session_id": 1})
        self.assertEqual(row["quality_class"], "leaked_prompt_or_json_artifact")

    def test_compliance_export_quality_allows_table_line_break_tags(self):
        answer = {
            "answer_id": 9,
            "session_id": 1,
            "prompt_id": "compliance_text_extraction",
            "answer_text": "# E. Erfuellungsaufwand\n\n| lfd. Nr. | Norm |\n| --- | --- |\n| 1 | § 1<br>§ 2 |",
            "answer_state": "active",
            "state_reason": "session_updated",
        }
        row = issues.compliance_export_quality_row(answer, {"session_id": 1})
        self.assertEqual(row["quality_class"], "expected_markdown")

    def test_retry_pressure_splits_user_rollbacks_and_counts_step_five_retries(self):
        data = {
            "sessions": [{"session_id": 1, "created_at": "2026-01-01", "app_session_id": "s1"}],
            "llm_answers": [
                {
                    "answer_id": 1,
                    "session_id": 1,
                    "prompt_id": "process_step_analysis",
                    "created_at": "2026-01-01 10:00:00",
                    "answer_state": "invalid",
                    "state_reason": "session_reverted",
                    "norm_addressee": "business",
                },
                {
                    "answer_id": 2,
                    "session_id": 1,
                    "prompt_id": "process_step_analysis",
                    "created_at": "2026-01-01 10:01:00",
                    "answer_state": "invalid",
                    "state_reason": "session_update_failed",
                    "norm_addressee": "business",
                    "answer_text": '{"prozesse": []}',
                },
                {
                    "answer_id": 3,
                    "session_id": 1,
                    "prompt_id": "process_step_analysis",
                    "created_at": "2026-01-01 10:02:00",
                    "answer_state": "active",
                    "state_reason": "session_updated",
                    "norm_addressee": "business",
                    "answer_text": '{"prozesse": [{"fallgruppen": [{"taetigkeiten": [{"taetigkeit": "A"}]}]}]}',
                },
            ],
            "regulations": [],
            "processes": [],
            "case_groups": [],
            "process_steps": [{"session_id": 1, "norm_addressee": "business", "step": "A"}],
            "costs": [],
            "tiles": [],
        }
        rows = issues.analyze_retry_pressure(data, out_dir=None)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["prompt_attempt_count"], 2)
        self.assertEqual(rows[0]["retry_rounds_to_success"], 1)
        self.assertEqual(rows[0]["terminal_state"], "succeeded_after_retry")

    def test_retry_pressure_counts_effort_pair_as_one_round(self):
        data = {
            "sessions": [{"session_id": 1, "created_at": "2026-01-01", "app_session_id": "s1"}],
            "llm_answers": [
                {
                    "answer_id": 1,
                    "session_id": 1,
                    "prompt_id": "cases_calculation",
                    "created_at": "2026-01-01 10:00:00",
                    "answer_state": "invalid",
                    "state_reason": "session_update_failed",
                    "norm_addressee": "business",
                },
                {
                    "answer_id": 2,
                    "session_id": 1,
                    "prompt_id": "effort_calculation",
                    "created_at": "2026-01-01 10:00:01",
                    "answer_state": "invalid",
                    "state_reason": "waiting_for_paired_retry",
                    "norm_addressee": "business",
                },
                {
                    "answer_id": 3,
                    "session_id": 1,
                    "prompt_id": "cases_calculation",
                    "created_at": "2026-01-01 10:01:00",
                    "answer_state": "active",
                    "state_reason": "session_updated",
                    "norm_addressee": "business",
                },
                {
                    "answer_id": 4,
                    "session_id": 1,
                    "prompt_id": "effort_calculation",
                    "created_at": "2026-01-01 10:01:01",
                    "answer_state": "active",
                    "state_reason": "session_updated",
                    "norm_addressee": "business",
                },
            ],
            "regulations": [],
            "processes": [],
            "case_groups": [],
            "process_steps": [{"session_id": 1, "norm_addressee": "business", "cost_current": 1}],
            "costs": [{"session_id": 1, "norm_addressee": "business", "total_cost": 1}],
            "tiles": [],
        }
        rows = issues.analyze_retry_pressure(data, out_dir=None)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["required_prompt_count"], 2)
        self.assertEqual(rows[0]["attempt_rounds_to_success_or_terminal"], 2)
        self.assertEqual(rows[0]["retry_rounds_to_success"], 1)

    def test_retry_cause_prefers_raw_step_shape_over_db_missing_steps_symptom(self):
        data = {
            "sessions": [{"session_id": 1, "created_at": "2026-01-01", "app_session_id": "s1"}],
            "llm_answers": [
                {
                    "answer_id": 1,
                    "session_id": 1,
                    "prompt_id": "process_step_analysis",
                    "created_at": "2026-01-01 10:00:00",
                    "answer_state": "invalid",
                    "state_reason": "session_update_failed: Missing process steps for fallgruppen_id values: 1",
                    "norm_addressee": "business",
                    "answer_text": '{"fallgruppen": [{"fallgruppen_id": 1, "taetigkeiten": [{"taetigkeit": "A"}]}]}',
                },
                {
                    "answer_id": 2,
                    "session_id": 1,
                    "prompt_id": "process_step_analysis",
                    "created_at": "2026-01-01 10:01:00",
                    "answer_state": "active",
                    "state_reason": "session_updated",
                    "norm_addressee": "business",
                    "answer_text": '{"prozesse": [{"fallgruppen": [{"taetigkeiten": [{"taetigkeit": "A"}]}]}]}',
                },
            ],
            "regulations": [],
            "processes": [],
            "case_groups": [],
            "process_steps": [{"session_id": 1, "norm_addressee": "business", "step": "A"}],
            "costs": [],
            "tiles": [],
        }
        rows = issues.analyze_retry_pressure(data, out_dir=None)
        self.assertEqual(rows[0]["primary_retry_cause"], "process_step_missing_expected_steps")
        self.assertIn("process_step_missing_expected_steps", rows[0]["retry_cause_groups"])

    def test_retry_cause_classifies_unknown_qualification_value(self):
        data = {
            "sessions": [{"session_id": 1, "created_at": "2026-01-01", "app_session_id": "s1"}],
            "llm_answers": [
                {
                    "answer_id": 1,
                    "session_id": 1,
                    "prompt_id": "effort_calculation",
                    "created_at": "2026-01-01 10:00:00",
                    "answer_state": "invalid",
                    "state_reason": "session_update_failed: effort_calculation: Unbekannte `qualifikation` 'gehoehter_dienst'",
                    "norm_addressee": "administration",
                    "answer_text": '{"fallgruppen": [{"fallgruppen_id": 1}]}',
                },
                {
                    "answer_id": 2,
                    "session_id": 1,
                    "prompt_id": "cases_calculation",
                    "created_at": "2026-01-01 10:01:00",
                    "answer_state": "active",
                    "state_reason": "session_updated",
                    "norm_addressee": "administration",
                    "answer_text": '{"fallgruppen": [{"fallgruppen_id": 1}]}',
                },
                {
                    "answer_id": 3,
                    "session_id": 1,
                    "prompt_id": "effort_calculation",
                    "created_at": "2026-01-01 10:01:01",
                    "answer_state": "active",
                    "state_reason": "session_updated",
                    "norm_addressee": "administration",
                    "answer_text": '{"fallgruppen": [{"fallgruppen_id": 1}]}',
                },
            ],
            "regulations": [],
            "processes": [],
            "case_groups": [],
            "process_steps": [{"session_id": 1, "norm_addressee": "administration", "cost_current": 1}],
            "costs": [],
            "tiles": [],
        }
        rows = issues.analyze_retry_pressure(data, out_dir=None)
        self.assertEqual(rows[0]["primary_retry_cause"], "unknown_qualification_value")

    def test_bureaucracy_quality_treats_negative_ip_cost_as_evaluable_relief(self):
        row = issues.bureaucracy_cost_quality_row(
            data={},
            session={"session_id": 1, "created_at": "2026-01-01", "app_session_id": "s1"},
            raw_business_ip=[{"legal_citation": "§ 1"}],
            business_ip=[{"regulation_id": 10}],
            business_regs=[{"regulation_id": 10}],
            business_cost={"total_cost": -100.0, "bureaucracy_cost": -80.0},
            linked_steps=[{"step_id": 20}],
        )

        self.assertEqual(row["bureaucracy_sign"], "negative")
        self.assertEqual(row["cost_bucket"], "ip_present_negative_bureaucracy_cost")
        self.assertEqual(row["chart_bucket"], "ip_present_negative_bureaucracy_cost")

    def test_bureaucracy_quality_reports_zero_ip_cost_as_zero_delta(self):
        row = issues.bureaucracy_cost_quality_row(
            data={},
            session={"session_id": 1, "created_at": "2026-01-01", "app_session_id": "s1"},
            raw_business_ip=[{"legal_citation": "§ 1"}],
            business_ip=[{"regulation_id": 10}],
            business_regs=[{"regulation_id": 10}],
            business_cost={"total_cost": -100.0, "bureaucracy_cost": 0.0},
            linked_steps=[{"step_id": 20}],
        )

        self.assertEqual(row["bureaucracy_sign"], "zero")
        self.assertEqual(row["cost_bucket"], "ip_present_zero_bureaucracy_cost")
        self.assertEqual(row["chart_bucket"], "ip_present_zero_bureaucracy_cost")

    def test_weekly_session_retry_pressure_categories_and_average(self):
        rows = [
            {"session_id": 1, "session_created_week": "2026-W01", "step_key": "step_5_process_steps", "succeeded": True, "retry_rounds_to_success": 2},
            {"session_id": 1, "session_created_week": "2026-W01", "step_key": "step_6_effort", "succeeded": True, "retry_rounds_to_success": 1},
            {"session_id": 2, "session_created_week": "2026-W01", "step_key": "step_6_effort", "succeeded": True, "retry_rounds_to_success": 0},
            {"session_id": 3, "session_created_week": "2026-W01", "step_key": "step_3_processes", "succeeded": True, "retry_rounds_to_success": 1},
        ]
        weekly = reporting.weekly_session_retry_pressure(rows)
        self.assertEqual(len(weekly), 1)
        self.assertEqual(weekly[0]["total_sessions"], 3)
        self.assertEqual(weekly[0]["step_5_and_6_retry_sessions"], 1)
        self.assertEqual(weekly[0]["other_step_retry_sessions"], 1)
        self.assertEqual(weekly[0]["no_retry_sessions"], 1)
        self.assertEqual(weekly[0]["avg_retry_rounds_per_session"], 1.333)

    def test_deep_research_retry_summary_uses_db_run_history(self):
        data = {
            "sessions": [
                {
                    "session_id": 1,
                    "app_session_id": "KMQW0R",
                    "created_at": "2026-08-04 19:40:00",
                    "current_law_id": 7,
                    "proposed_law_id": 8,
                    "llm_model": "gemini-3.5-flash",
                }
            ],
            "deep_research_runs": [
                {
                    "research_run_id": 10,
                    "session_id": 1,
                    "purpose": "case_group_metrics",
                    "status": "failed",
                    "created_at": "2026-08-04 19:40:54",
                    "completed_at": "2026-08-04 20:10:58",
                    "error": "Gemini Deep Research timed out after 1800 seconds",
                    "estimated_cost_usd": 0,
                },
                {
                    "research_run_id": 11,
                    "session_id": 1,
                    "purpose": "case_group_metrics",
                    "status": "parsed",
                    "created_at": "2026-08-05 09:20:00",
                    "completed_at": "2026-08-05 09:38:01",
                    "estimated_cost_usd": 1.25,
                },
            ],
        }

        rows = reporting.deep_research_retry_summary(data)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["app_session_id"], "KMQW0R")
        self.assertEqual(rows[0]["workflow_step"], "Step 6 effort")
        self.assertEqual(rows[0]["run_type"], "Deep Research")
        self.assertEqual(rows[0]["status_history"], "failed -> parsed")
        self.assertEqual(rows[0]["failed_runs"], 1)
        self.assertEqual(rows[0]["parsed_runs"], 1)
        self.assertEqual(rows[0]["retried_before_success"], 1)
        self.assertIn("timed out", rows[0]["error_excerpt"])

    def test_weekly_deep_research_attempts_splits_first_try_retry_and_failure(self):
        rows = [
            {"week": "2026-W32", "total_runs": 1, "failed_runs": 0, "parsed_runs": 1},
            {"week": "2026-W32", "total_runs": 2, "failed_runs": 1, "parsed_runs": 1},
            {"week": "2026-W32", "total_runs": 1, "failed_runs": 1, "parsed_runs": 0},
            {"week": "2026-W32", "total_runs": 1, "failed_runs": 0, "parsed_runs": 0},
        ]

        weekly = reporting.weekly_deep_research_attempts(rows)

        self.assertEqual(len(weekly), 1)
        self.assertEqual(weekly[0]["total_deep_research_pairs"], 4)
        self.assertEqual(weekly[0]["total_deep_research_runs"], 5)
        self.assertEqual(weekly[0]["deep_research_success_first_try"], 1)
        self.assertEqual(weekly[0]["deep_research_failed_then_success"], 1)
        self.assertEqual(weekly[0]["deep_research_failed_without_success"], 1)
        self.assertEqual(weekly[0]["deep_research_other"], 1)

    def test_hard_failure_session_rows_explains_red_sessions(self):
        session_rows = [
            {
                "session_id": 1,
                "app_session_id": "BAD001",
                "week": "2026-W32",
                "law_pair": "1->2",
                "model": "gemini-3.5-flash",
                "completion_depth": "total_cost_ready",
                "quality_label": "bad",
            },
            {
                "session_id": 2,
                "app_session_id": "OK001",
                "quality_label": "good",
            },
        ]
        findings = [
            {
                "session_id": 1,
                "app_session_id": "BAD001",
                "issue_id": "issue_03_json_truncation",
                "classification": "bad",
                "prompt_id": "case_group_development",
                "evidence_summary": "expected top-level key fallgruppen",
                "evidence": {"parse_class": "wrong_top_level_key"},
            },
            {
                "session_id": 1,
                "app_session_id": "BAD001",
                "issue_id": "issue_05_structure_consistency",
                "classification": "bad",
                "evidence_summary": "diagnostic only",
                "evidence": {},
            },
        ]

        rows = reporting.hard_failure_session_rows(session_rows, findings)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["app_session_id"], "BAD001")
        self.assertEqual(rows[0]["hard_issues"], "issue_03_json_truncation")
        self.assertIn("expected top-level key", rows[0]["evidence_summary"])


if __name__ == "__main__":
    unittest.main()
