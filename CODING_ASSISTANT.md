# Coding Assistant Guide

- **Project goal**: Compliance-Cost Computer (CCC-App) for estimating German legislative compliance costs; LLM pipeline plus a tile-board mock UI.
- **LLM entry point**: `main_chatterbox.py` builds prompts from `ea_agent_chat/prompt_templates.py` and runs them via `ea_agent_chat/question_assembler.py` with the API from `ea_agent_chat/api_helper.py`. The full compliance workflow is commented out; the active run uses `WebTest*` prompts.
- **Config & data**: `ea_agent_chat/config.py` defines config classes; `ea_agent_chat/current_config.py` selects regulation descriptors and text files from `regulations/`, model params, `CHOOSE_BEST_OF`, timeouts, and log levels. Each run writes `config_parameters.txt` into `results/chat_YYYYMMDD-HHMM/`.
- **API layer**: `OpenAiApi` wraps the Responses API with the `web_search` tool; `GeminiApi` is a stub. `BaseAPI.ask_question` optionally saves response text to `results/` and can dump the full response JSON when `SAVE_ENTIRE_RESPONSES` is true.
- **Prompt flow**: `Question.run_and_save_multiple_questions` loops `CHOOSE_BEST_OF` times, retries on `BadRequestError`, tracks `responses`, and can `choose_best_answer()` plus `verify_and_save_sources()`.
- **Templates & parsing**: `ea_agent_chat/json_templates.py` defines JSON shapes; `ea_agent_chat/parser.py` uses pandas to parse JSON answers to DataFrame/CSV and flatten sources. It assumes valid JSON and returns empty DataFrames on parse failure.
- **Logging**: `ea_agent_chat/logging_utils.py` writes to stdout + `results/.../run.log` (levels from `current_config`). `ea_agent_chat/usage_logger.py` is optional and not wired into the main flow.
- **Backend + UI mock**: `ea_agent_chat/backend.py` is a Flask + SQLite API (`tiles.db`) with `/tiles` GET/POST and `/tiles/<id>` DELETE. `seed_from_json()` loads `ea_agent_chat/mockup_data.json` when the DB is empty. `ea_agent_chat/reactflow_mock.html` is a standalone ReactFlow UMD page that fetches `http://localhost:5000/tiles` and falls back to inline mock data.
- **Mock data**: `ea_agent_chat/mockup_data.py` generates `ea_agent_chat/mockup_data.json` via `write_json()`. Keep them aligned if you edit the schema.
- **Tests**: `tests/` covers `parser`, `question_assembler`, `logging_utils`, plus monkeypatch examples. Run with `pytest`.
- **Env**: `OPENAI_API_KEY` required for OpenAI; `GEMINI_API_KEY` for the Gemini path. There is no dotenv loader in this repo, so set env vars in your shell.
- **Run**: `python main_chatterbox.py` for the LLM pipeline; `python ea_agent_chat/backend.py` for the tiles API; open `ea_agent_chat/reactflow_mock.html` to view the UI.
- **Data folders**: `regulations/` holds law text inputs; `results/` stores run outputs and logs. Avoid editing these unless you intend to update data.

<!-- asked with prompt: analyse my codebase and give me a coding assistant markdown file. -->
