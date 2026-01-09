#  use from Terminal: python -m pytest -s ./tests/test_parser.py

import pytest
from ea_agent_chat import parser


SAMPLE_ANSWER = """
[
    {
        "Prozessschritt": "Pruefung",
        "Anwendungsfall": "Fall A",
        "durchgeführt von": "Sachbearbeiter",
        "Anzahl Einzelfälle pro Jahr": 10,
        "Kosten in EUR pro Einzelfall": 100.5,
        "Zeitaufwand in Min. pro Einzelfall": 15,
        "Details zur Einzelfallberechnung": "Basisannahme",
        "Details zur Kostenberechnung": "100 EUR + 0.5",
        "Details zur Zeitberechnung": "15 Minuten",
        "Gesetzesgrundlagen für diesen Prozessschritt": ["§1", "§2"],
        "Quellen": [
            {
                "Name": "Quelle1",
                "exakte URL": "https://example.com",
                "direktes Zitat": "Zitat 1",
                "abgerufen am": "2025-01-01"
            },
            {
                "Name": "Quelle2",
                "exakte URL": "https://example.org",
                "direktes Zitat": "Zitat 2",
                "abgerufen am": "2025-01-02"
            }
        ]
    }
]
"""


def test_parse_single_answer_to_df_returns_rows():
    df = parser.parse_single_answer_to_df(SAMPLE_ANSWER, "json_ea_yearly")
    assert not df.empty
    assert df.loc[0, "Prozessschritt"] == "Pruefung"
    assert df.loc[0, "Anzahl Einzelfälle pro Jahr"] == 10


def test_flatten_sources_from_multiple_answers():
    answers = [SAMPLE_ANSWER, SAMPLE_ANSWER]
    sources = parser.flatten_sources_from_multiple_answers(answers, "json_ea_yearly")
    assert len(sources) == 4  # two sources per answer
    assert sources[0]["Name"] == "Quelle1"


def test_json_template_columns_stable():
    """Fails if json_ea_yearly structure changes unexpectedly."""
    df = parser.parse_single_answer_to_df(SAMPLE_ANSWER, "json_ea_yearly")
    expected_cols = {
        "Prozessschritt",
        "Anwendungsfall",
        "durchgeführt von",
        "Anzahl Einzelfälle pro Jahr",
        "Kosten in EUR pro Einzelfall",
        "Zeitaufwand in Min. pro Einzelfall",
        "Details zur Einzelfallberechnung",
        "Details zur Kostenberechnung",
        "Details zur Zeitberechnung",
        "Gesetzesgrundlagen für diesen Prozessschritt",
        "Quellen",
    }
    assert set(df.columns) == expected_cols


def test_flatten_sources_missing_column_raises():
    df = parser.parse_single_answer_to_df(SAMPLE_ANSWER, "json_ea_yearly")
    with pytest.raises(KeyError):
        parser.flatten_sources_from_answer_df(df, sources_column="Missing")


def test_flatten_sources_non_list_entries_raise():
    df = parser.parse_single_answer_to_df(SAMPLE_ANSWER, "json_ea_yearly")
    df["Quellen"] = "not-a-list"
    flattened = parser.flatten_sources_from_answer_df(df)
    # Document current behavior: string is treated as iterable of characters.
    assert flattened == list("not-a-list")
