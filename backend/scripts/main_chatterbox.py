import os
# TODO: implement warnings and logging

from datetime import datetime
from openai import OpenAI

from backend.legacy import prompt_templates
from backend.legacy import question_assembler
from backend.legacy.current_config import current_config
from backend.legacy import api_helper
from backend.legacy.logging_utils import setup_logger


logger = setup_logger()

logger.info("Starting chatterbox at %s", datetime.now().strftime("%H:%M"))
logger.info(
    "REASONING effort=%s verbosity=%s | VERIFICATION effort=%s verbosity=%s",
    current_config.MODEL_PARAMETERS_REASONING.get("reasoning_effort", "N/A"),
    current_config.MODEL_PARAMETERS_REASONING.get("verbosity", "N/A"),
    current_config.MODEL_PARAMETERS_VERIFICATION.get("reasoning_effort", "N/A"),
    current_config.MODEL_PARAMETERS_VERIFICATION.get("verbosity", "N/A"),
)

# client = OpenAI(api_key=os.environ['OPENAI_API_KEY'])
#
# #---------------
#
# instructions = prompt_templates.Instructions()
#
# # --------- run aktuell ----------
# print('Start running multiple questions for {} at {}'.format(current_config.REGULATION_1_DESCRIPTOR, datetime.now().strftime("%H:%M")))
#
# prompt = prompt_templates.JaehrlicherErfuellungsaufwand(current_config.REGULATION_1_DESCRIPTOR,
#                                                         current_config.REGULATION_1_TEXT)
# question_ea_sq_json = question_assembler.Question(client, instructions, prompt)
# question_ea_sq_json.run_and_save_multiple_questions()
# print('Finished running multiple questions {}'.format(datetime.now().strftime("%H:%M")))
# question_ea_sq_json.verify_and_save_sources()
# question_ea_sq_json.choose_and_save_best_answer()
# print('Finished running choosing best answer {}'.format(datetime.now().strftime("%H:%M")))
# question_ea_sq_json.save_answers_as_csvs()
# question_ea_sq_json.save_best_answer_as_csv()
#
# prompt = prompt_templates.VisualiseProcess()
# question_ea_sq_md = question_assembler.Question(client, instructions, prompt, previous_question=question_ea_sq_json)
# question_ea_sq_md.run_and_save_multiple_questions()
# question_ea_sq_md.choose_and_save_best_answer()
# print('Finished running visualising process {}'.format(datetime.now().strftime("%H:%M")))
#
# # --------- run reform ----------
# print('Start running multiple questions for {} at {}'.format(current_config.REGULATION_2_DESCRIPTOR, datetime.now().strftime("%H:%M")))
# prompt = prompt_templates.JaehrlicherErfuellungsaufwand(current_config.REGULATION_2_DESCRIPTOR,
#                                                         current_config.REGULATION_2_TEXT)
# question_ea_rf_json = question_assembler.Question(client, instructions, prompt)
# question_ea_rf_json.run_and_save_multiple_questions()
# print('Finished running multiple questions {}'.format(datetime.now().strftime("%H:%M")))
# question_ea_rf_json.verify_and_save_sources()
# question_ea_rf_json.choose_and_save_best_answer()
# print('Finished running choosing best answer {}'.format(datetime.now().strftime("%H:%M")))
# question_ea_rf_json.save_answers_as_csvs()
# question_ea_rf_json.save_best_answer_as_csv()
#
# prompt = prompt_templates.VisualiseProcess()
# question_ea_rf_md = question_assembler.Question(client, instructions, prompt, previous_question=question_ea_rf_json)
# question_ea_rf_md.run_and_save_multiple_questions()
# question_ea_rf_md.choose_and_save_best_answer()
# print('Finished running visualising process {}'.format(datetime.now().strftime("%H:%M")))


# ---------------

# test_instructions = prompt_templates.PromptTemplate(name='test_instructions', text='You are a mathematician.')
# test_prompt = prompt_templates.TestPrompt()
#
#
# test_question = question_assembler.Question(client, test_instructions, test_prompt)
# test_question.run_and_save_multiple_questions()
# test_question.choose_and_save_best_answer()
#
# follow_up_prompt= prompt_templates.FollowUpTestPrompt()
# follow_up_question = question_assembler.Question(client, test_instructions, follow_up_prompt,
#                                                  previous_response_id=test_question.best_response.id)
# follow_up_question.run_and_save_multiple_questions()
# follow_up_question.choose_and_save_best_answer()


# print('Finishing chatterbox at {}'.format(datetime.now().strftime("%H:%M")))


api = api_helper.API()

test_instructions = prompt_templates.WebTestInstructions()
test_prompt = prompt_templates.WebTestPrompt()
test_question = question_assembler.Question(api, test_instructions, test_prompt)
test_question.run_and_save_multiple_questions()
test_question.choose_best_answer()

logger.info("Final response:\n%s", test_question.responses[-1].output_text)
