import logging

from ea_agent_chat import api_helper
from ea_agent_chat import prompt_templates
from ea_agent_chat import question_assembler
from ea_agent_chat import logging_utils
from ea_agent_chat import current_config


class DummyAPI:
    """Minimal stand-in for API to avoid network calls."""

    def __init__(self):
        self.client = None
        self.calls = []

    def ask_question(self, instruction_text, prompt, file_stem=None, previous_response_id=None):
        self.calls.append((instruction_text, getattr(prompt, "text", ""), file_stem, previous_response_id))
        return api_helper.Response(
            response_id=f"id-{len(self.calls)}",
            response_text=f"answer-{file_stem}",
            response_file_stem=file_stem,
            response_file_type="txt",
        )


def test_question_collects_responses(monkeypatch):
    monkeypatch.setattr(question_assembler.current_config, "CHOOSE_BEST_OF", 1)
    instructions = prompt_templates.WebTestInstructions()
    prompt = prompt_templates.WebTestPrompt()
    q = question_assembler.Question(DummyAPI(), instructions, prompt, logger=logging_utils.get_logger())

    q.run_and_save_multiple_questions(timeout_in_minutes=1)

    assert len(q.responses) == 1
    assert q.responses[0].output_text.startswith("answer-")


def test_choose_best_answer_sets_best_response(monkeypatch):
    monkeypatch.setattr(question_assembler.current_config, "CHOOSE_BEST_OF", 1)
    instructions = prompt_templates.WebTestInstructions()
    prompt = prompt_templates.WebTestPrompt()
    q = question_assembler.Question(DummyAPI(), instructions, prompt, logger=logging_utils.get_logger())
    q.responses = [
        api_helper.Response("id-1", "first answer", "stem_01", "txt"),
        api_helper.Response("id-2", "second answer", "stem_02", "txt"),
    ]

    best = q.choose_best_answer()

    assert q.best_response is best
    assert best.file_stem.endswith("_best")
