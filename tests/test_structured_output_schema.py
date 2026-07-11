import json

from backend.core.norm_addressees import ADMINISTRATION, BUSINESS, CITIZENS
import pytest

from backend.core.payload_builders import (
    _CASES_METRIC_KEYS,
    build_case_group_development_output_schema,
    build_cases_calculation_output_schema,
    build_cases_calculation_output_skeleton,
    build_effort_calculation_output_schema,
    build_effort_calculation_output_skeleton,
    build_process_compilation_output_schema,
    build_step_analysis_output_schema,
    build_step_analysis_output_skeleton,
)
from backend.core.prompts import PromptId, render_prompt
from backend.routers.case_groups import _parse_case_groups
from backend.routers.effort import _parse_cases_payload, _parse_effort_payload
from backend.routers.process_steps import _parse_process_steps
from backend.routers.processes import _parse_processes

_FORBIDDEN_KEYWORDS = {
    "minItems",
    "maxItems",
    "minimum",
    "maximum",
    "exclusiveMinimum",
    "exclusiveMaximum",
    "pattern",
    "format",
    "minLength",
    "maxLength",
    "minProperties",
    "maxProperties",
    "patternProperties",
    "oneOf",
    "allOf",
}


def _node_type(node: dict) -> object:
    return node.get("type")


def _is_object(node: dict) -> bool:
    node_type = _node_type(node)
    return node_type == "object" or (
        isinstance(node_type, list) and "object" in node_type
    )


def _is_array(node: dict) -> bool:
    node_type = _node_type(node)
    return node_type == "array" or (isinstance(node_type, list) and "array" in node_type)


def _assert_strict_subset(node: dict, object_depth: int = 0) -> None:
    assert isinstance(node, dict)
    for keyword in _FORBIDDEN_KEYWORDS:
        assert keyword not in node, keyword
    if _is_object(node):
        current_depth = object_depth + 1
        assert current_depth <= 5
        assert node.get("additionalProperties") is False
        properties = node.get("properties", {})
        assert set(node.get("required", [])) == set(properties.keys())
        for child in properties.values():
            _assert_strict_subset(child, current_depth)
    elif _is_array(node):
        items = node.get("items")
        assert isinstance(items, dict)
        _assert_strict_subset(items, object_depth)


def test_cases_schema_is_strict_subset_compliant_for_all_addressees():
    for addressee in (ADMINISTRATION, BUSINESS, CITIZENS):
        _assert_strict_subset(build_cases_calculation_output_schema(addressee))


def test_effort_schema_is_strict_subset_compliant_for_all_addressees():
    for addressee in (ADMINISTRATION, BUSINESS, CITIZENS):
        _assert_strict_subset(build_effort_calculation_output_schema(addressee))


def test_cases_schema_matches_skeleton_keys():
    skeleton = build_cases_calculation_output_skeleton(
        [{"fallgruppen": [{"fallgruppen_id": 1}]}],
        norm_addressee=ADMINISTRATION,
    )
    skeleton_fallgruppe = skeleton["fallgruppen"][0]
    schema = build_cases_calculation_output_schema(ADMINISTRATION)
    schema_fallgruppe = schema["properties"]["fallgruppen"]["items"]["properties"]

    assert set(schema_fallgruppe.keys()) == set(skeleton_fallgruppe.keys())
    assert set(schema_fallgruppe["erklaerungen"]["properties"].keys()) == set(
        skeleton_fallgruppe["erklaerungen"].keys()
    )
    assert set(schema_fallgruppe["confidence"]["properties"].keys()) == set(
        skeleton_fallgruppe["confidence"].keys()
    )
    for metric_key in _CASES_METRIC_KEYS:
        assert schema_fallgruppe["confidence"]["properties"][metric_key]["enum"] == [
            "high",
            "medium",
            "low",
        ]


def test_effort_citizens_schema_matches_skeleton_keys():
    skeleton = build_effort_calculation_output_skeleton(
        [{"fallgruppen": [{"fallgruppen_id": 1, "taetigkeiten": [{"taetigkeiten_id": 9}]}]}],
        norm_addressee=CITIZENS,
    )
    skeleton_taetigkeit = skeleton["fallgruppen"][0]["taetigkeiten"][0]
    schema = build_effort_calculation_output_schema(CITIZENS)
    schema_taetigkeit = schema["properties"]["fallgruppen"]["items"]["properties"][
        "taetigkeiten"
    ]["items"]["properties"]

    assert set(schema_taetigkeit.keys()) == set(skeleton_taetigkeit.keys())
    assert "personalaufwand_gueltig" not in schema_taetigkeit


def test_effort_org_schema_matches_skeleton_keys():
    skeleton = build_effort_calculation_output_skeleton(
        [{"fallgruppen": [{"fallgruppen_id": 1, "taetigkeiten": [{"taetigkeiten_id": 9}]}]}],
        norm_addressee=BUSINESS,
    )
    skeleton_taetigkeit = skeleton["fallgruppen"][0]["taetigkeiten"][0]
    schema = build_effort_calculation_output_schema(BUSINESS)
    schema_taetigkeit = schema["properties"]["fallgruppen"]["items"]["properties"][
        "taetigkeiten"
    ]["items"]["properties"]

    assert set(schema_taetigkeit.keys()) == set(skeleton_taetigkeit.keys())

    skeleton_item = skeleton_taetigkeit["personalaufwand_gueltig"][0]
    schema_item = schema_taetigkeit["personalaufwand_gueltig"]["items"]["properties"]
    assert set(schema_item.keys()) == set(skeleton_item.keys())


def test_normadressat_enum_is_pinned_to_run_addressee():
    schema = build_cases_calculation_output_schema(BUSINESS)
    assert schema["properties"]["normadressat"]["enum"] == [BUSINESS]


def test_schema_conformant_cases_example_parses():
    example = {
        "normadressat": ADMINISTRATION,
        "fallgruppen": [
            {
                "fallgruppen_id": 501,
                "anzahl_betroffene_gueltig": 100,
                "haeufigkeit_pro_jahr_gueltig": 1,
                "anzahl_betroffene_vorschlag": 120,
                "haeufigkeit_pro_jahr_vorschlag": 1,
                "erklaerungen": {key: "Herleitung" for key in _CASES_METRIC_KEYS},
                "confidence": {key: "high" for key in _CASES_METRIC_KEYS},
            }
        ],
    }

    parsed, fallback_kinds = _parse_cases_payload(json.dumps(example), ADMINISTRATION)

    assert fallback_kinds == set()
    assert len(parsed) == 1
    assert parsed[0]["case_group_id"] == 501
    assert parsed[0]["addressees_current"] == 100.0
    assert parsed[0]["addressees_proposed"] == 120.0
    assert parsed[0]["case_metric_research_json"]["confidence"][
        "anzahl_betroffene_gueltig"
    ] == "high"


def test_schema_conformant_cases_example_allows_null_side():
    example = {
        "normadressat": ADMINISTRATION,
        "fallgruppen": [
            {
                "fallgruppen_id": 501,
                "anzahl_betroffene_gueltig": None,
                "haeufigkeit_pro_jahr_gueltig": None,
                "anzahl_betroffene_vorschlag": 120,
                "haeufigkeit_pro_jahr_vorschlag": 1,
                "erklaerungen": {key: "Herleitung" for key in _CASES_METRIC_KEYS},
                "confidence": {key: "medium" for key in _CASES_METRIC_KEYS},
            }
        ],
    }

    parsed, fallback_kinds = _parse_cases_payload(json.dumps(example), ADMINISTRATION)

    assert fallback_kinds == set()
    assert parsed[0]["addressees_current"] is None
    assert parsed[0]["addressees_proposed"] == 120.0


def test_schema_conformant_effort_citizens_example_parses():
    example = {
        "normadressat": CITIZENS,
        "fallgruppen": [
            {
                "fallgruppen_id": 501,
                "taetigkeiten": [
                    {
                        "taetigkeiten_id": 9001,
                        "zeitaufwand_in_min_gueltig": 30,
                        "sachaufwand_gueltig": 0,
                        "zeitaufwand_in_min_vorschlag": 45,
                        "sachaufwand_vorschlag": 5,
                    }
                ],
            }
        ],
    }

    parsed, fallback_kinds = _parse_effort_payload(json.dumps(example), CITIZENS)

    assert fallback_kinds == set()
    assert len(parsed) == 1
    assert parsed[0]["step_id"] == 9001
    assert parsed[0]["time_required_current"]["a"] == 30.0
    assert parsed[0]["time_required_proposed"]["a"] == 45.0
    assert parsed[0]["expenses_proposed"] == 5.0


# --- Drift-Schutz: Prompt-Beispielblock <-> generiertes Schema ---
#
# Die Prompt-Texte sind handgetippt, die Schemata werden generiert. Damit die
# beiden Seiten nicht auseinanderlaufen, wird der JSON-Beispielblock aus dem
# gerenderten Prompt extrahiert und gegen das Schema geprueft: gleiche
# Feldnamen auf jeder Ebene, gleiche Verschachtelung.

_RENDER_KWARGS = {
    PromptId.PROCESS_COMPILATION: {"vorgaben_json": "[]"},
    PromptId.CASE_GROUP_DEVELOPMENT: {"prozesse_json": "[]"},
    PromptId.PROCESS_STEP_ANALYSIS: {"case_groups_json": "[]"},
    PromptId.CASES_CALCULATION: {"case_groups_json": "[]"},
    PromptId.EFFORT_CALCULATION: {"step_analysis_json": "[]"},
}

_FORM_ANCHORS = {
    PromptId.PROCESS_COMPILATION: "Geben Sie nur und ausschliesslich JSON im folgenden Format zurueck:",
    PromptId.CASE_GROUP_DEVELOPMENT: "Geben Sie nur und ausschliesslich JSON im folgenden Format zurueck:",
    PromptId.PROCESS_STEP_ANALYSIS: "Jedes Element von `taetigkeiten` hat folgende Form:",
    PromptId.CASES_CALCULATION: "Jede Fallgruppe hat folgende Kennzahlenform:",
    PromptId.EFFORT_CALCULATION: "Jede Taetigkeit hat folgende Aufwandsform:",
}

# Wo im Schema die extrahierte Beispielform haengt.
_SCHEMA_SUBTREE = {
    PromptId.PROCESS_COMPILATION: (),
    PromptId.CASE_GROUP_DEVELOPMENT: (),
    PromptId.PROCESS_STEP_ANALYSIS: ("fallgruppen", "taetigkeiten"),
    PromptId.CASES_CALCULATION: ("fallgruppen",),
    PromptId.EFFORT_CALCULATION: ("fallgruppen", "taetigkeiten"),
}

_SCHEMA_BUILDERS = {
    PromptId.PROCESS_COMPILATION: build_process_compilation_output_schema,
    PromptId.CASE_GROUP_DEVELOPMENT: build_case_group_development_output_schema,
    PromptId.PROCESS_STEP_ANALYSIS: build_step_analysis_output_schema,
    PromptId.CASES_CALCULATION: build_cases_calculation_output_schema,
    PromptId.EFFORT_CALCULATION: build_effort_calculation_output_schema,
}

_STRUCTURED_PROMPT_IDS = list(_SCHEMA_BUILDERS)


def _json_block_after(text: str, anchor: str) -> dict:
    start = text.index(anchor) + len(anchor)
    start = text.index("{", start)
    depth = 0
    for index in range(start, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start : index + 1])
    raise AssertionError(f"no balanced JSON block after anchor: {anchor}")


def _example_form(prompt_id: str, norm_addressee: str) -> dict:
    prompt = render_prompt(
        prompt_id,
        norm_addressee=norm_addressee,
        law_summary="x",
        **_RENDER_KWARGS[prompt_id],
    )
    return _json_block_after(prompt, _FORM_ANCHORS[prompt_id])


def _schema_form(prompt_id: str, norm_addressee: str) -> dict:
    node = _SCHEMA_BUILDERS[prompt_id](norm_addressee)
    for key in _SCHEMA_SUBTREE[prompt_id]:
        node = node["properties"][key]["items"]
    return node


def _example_paths(value, prefix: str = "") -> set[str]:
    paths: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else key
            paths.add(path)
            paths |= _example_paths(child, path)
    elif isinstance(value, list):
        for child in value:
            paths |= _example_paths(child, f"{prefix}[]")
    return paths


def _schema_paths(node: dict, prefix: str = "") -> set[str]:
    paths: set[str] = set()
    if _is_object(node):
        for key, child in node.get("properties", {}).items():
            path = f"{prefix}.{key}" if prefix else key
            paths.add(path)
            paths |= _schema_paths(child, path)
    elif _is_array(node):
        paths |= _schema_paths(node["items"], f"{prefix}[]")
    return paths


@pytest.mark.parametrize("prompt_id", _STRUCTURED_PROMPT_IDS)
@pytest.mark.parametrize("norm_addressee", [ADMINISTRATION, BUSINESS, CITIZENS])
def test_prompt_example_and_schema_have_identical_field_tree(prompt_id, norm_addressee):
    example = _example_paths(_example_form(prompt_id, norm_addressee))
    schema = _schema_paths(_schema_form(prompt_id, norm_addressee))

    assert example == schema, (
        f"{prompt_id}/{norm_addressee}: "
        f"nur im Prompt={sorted(example - schema)}, nur im Schema={sorted(schema - example)}"
    )


@pytest.mark.parametrize("prompt_id", _STRUCTURED_PROMPT_IDS)
def test_all_structured_schemas_are_strict_subset_compliant(prompt_id):
    for addressee in (ADMINISTRATION, BUSINESS, CITIZENS):
        _assert_strict_subset(_SCHEMA_BUILDERS[prompt_id](addressee))


@pytest.mark.parametrize("prompt_id", _STRUCTURED_PROMPT_IDS)
def test_all_structured_schemas_pin_normadressat(prompt_id):
    schema = _SCHEMA_BUILDERS[prompt_id](BUSINESS)
    assert schema["properties"]["normadressat"]["enum"] == [BUSINESS]
