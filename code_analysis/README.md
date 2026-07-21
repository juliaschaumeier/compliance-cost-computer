# CCC Historical Quality Analysis

This directory contains the historical analysis suite for CCC LLM output
quality. The shippable code is in `code_analysis/code/`; generated,
DB-dependent results belong in `code_analysis/output/`.

## Gitignore Setup

If only the reusable analysis code and documentation should be pushed, use this
shape in the repository `.gitignore`:

```gitignore
# Historical CCC analysis: keep code/docs, ignore DB-dependent outputs.
code_analysis/*
!code_analysis/README.md
!code_analysis/analysis_config.example.json
!code_analysis/code/
!code_analysis/code/**
code_analysis/analysis_config.json
code_analysis/analysis_config.local.json
code_analysis/output/
code_analysis/code/__pycache__/
```

The repository already ignores common local artifacts such as `.DS_Store`,
`__pycache__/`, `*.pyc`, and `*.db`, but keeping the explicit
`code_analysis/output/` rule makes the source/output split clear.

## What To Commit

Commit:

```text
code_analysis/README.md
code_analysis/analysis_config.example.json
code_analysis/code/
```

Do not commit:

```text
code_analysis/output/
code_analysis/analysis_config.json
code_analysis/analysis_config.local.json
code_analysis/**/*.db
code_analysis/**/__pycache__/
code_analysis/**/.DS_Store
```

`code_analysis/historical_quality_test_ideas.md` is an earlier planning note.
It is useful background, but it is not required to run or reproduce the suite.

## Quick Start

From the repository root:

```bash
cp code_analysis/analysis_config.example.json code_analysis/analysis_config.json
```

Edit the local `code_analysis/analysis_config.json` so `db_path` and
`law_pair_groups` match your database.

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
  -s code_analysis/code \
  -p 'test_*.py'
```

Then run the analysis using the local config:

```bash
python3 code_analysis/code/historical_quality.py run \
  --output code_analysis/output/full_analysis_backend_ccc
```

You can also pass an explicit config path:

```bash
python3 code_analysis/code/historical_quality.py run \
  --config code_analysis/analysis_config.local.json
```

Open the generated report here:

```text
code_analysis/output/full_analysis_backend_ccc/visuals/index.html
```

## Code Layout

```text
code_analysis/code/historical_quality.py      CLI entry point
code_analysis/code/common.py                  filesystem, SQLite, extraction, CSV/JSON helpers
code_analysis/code/entities.py                JSON classification, normalization, entity parsing
code_analysis/code/issues.py                  issue-specific deterministic analyzers
code_analysis/code/reporting.py               aggregation, markdown report, HTML visualizations
code_analysis/code/adjudication.py            optional review-packet adjudication staging
code_analysis/code/test_historical_quality.py focused stdlib regression tests
```

## Analysis Scope

The current benchmark scope intentionally excludes reversed, missing-law, and
ad-hoc law-pair sessions. Included law-pair groups are:

- `1->2` and `9->10`: e-sports
- `3->4` and `7->8`: arbeitstagepauschale
- `5->6` and `11->12`: 491 bgb

Each run writes audit files so scope differences are visible:

```text
code_analysis/output/<run>/extracted/analysis_scope.csv
code_analysis/output/<run>/extracted/excluded_sessions.csv
```

To change the benchmark scope, edit `law_pair_groups` in your local
`code_analysis/analysis_config.json`. The committed
`analysis_config.example.json` documents the expected shape.

Important config fields:

- `db_path`: local SQLite DB path.
- `law_pair_groups`: named law-change groups; pairs in the same group share one
  visual symbol and are compared as the same benchmark topic.

## Outputs

A full run writes:

```text
code_analysis/output/<run>/
  db_snapshot/       local copy of the DB used for the run
  extracted/         normalized session, answer, scope, and feature data
  findings/          issue-level CSV/JSONL diagnostics
  review_packets/    compact packets for ambiguous/manual review
  reports/           markdown/CSV summaries
  visuals/           HTML report and embedded plots
```

The main report is `visuals/index.html`.

## Feature Markers

Default timeline markers for major shared feature/fix dates are built into the
report. Pass a marker file only if you want to override or extend them for a
specific local analysis:

```bash
python3 code_analysis/code/historical_quality.py run \
  --output code_analysis/output/full_analysis_backend_ccc \
  --feature-markers code_analysis/code/feature_markers.example.yml
```

The parser supports the simple YAML shape used by the example file. JSON marker
files with `{"markers": [...]}` are also supported.

## Interpretation Rules

Incomplete sessions are not bad by default. A session is marked bad only when
the available raw LLM answer or persisted partial state shows a concrete quality
failure. Missing later workflow steps are treated as depth or eligibility
limits.

Repeated-run variance findings, such as structure or final-cost variance, are
diagnostic signals. They are plotted and exported, but they do not make a
session bad by themselves unless a hard failure is also present.

JSON quality classes are based on the raw LLM answer. They are exported together
with DB `answer_state` and `state_reason`, but they are not identical to DB
parser/session-update errors.

## Optional Review/Adjudication

The deterministic suite does not call an LLM. Ambiguous cases are exported as
compact JSON review packets under `review_packets/`.

To create an adjudication run record without deciding anything:

```bash
python3 code_analysis/code/historical_quality.py adjudicate \
  --input code_analysis/output/<run>/review_packets \
  --output code_analysis/output/<run>/adjudication \
  --mode pending
```

To adjudicate high-confidence cases with deterministic rules:

```bash
python3 code_analysis/code/historical_quality.py adjudicate \
  --input code_analysis/output/<run>/review_packets \
  --output code_analysis/output/<run>/adjudication \
  --mode rules
```

Neither mode calls an LLM. Interpretation-heavy packets remain pending for
human review or a separate fixed-prompt LLM process.
