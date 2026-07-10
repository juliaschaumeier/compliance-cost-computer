import json

from backend.core.norm_addressees import ADMINISTRATION, BUSINESS, CITIZENS
from backend.core.payload_builders import (
    _CASES_METRIC_KEYS,
    build_cases_calculation_output_schema,
    build_cases_calculation_output_skeleton,
    build_effort_calculation_output_schema,
    build_effort_calculation_output_skeleton,
)
from backend.routers.effort import _parse_cases_payload, _parse_effort_payload

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
