import os
# TODO: implement warnings and logging

from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

from ea_agent_chat import prompt_templates
from ea_agent_chat import question_assembler
from ea_agent_chat.current_config import current_config


# Load environment variables
load_dotenv()


print('Starting chatterbox at {}'.format(datetime.now().strftime("%H:%M")))

print(f"REASONING reasoning: {current_config.MODEL_PARAMETERS_REASONING['reasoning_effort']}, "
      f"REASONING verbosity: {current_config.MODEL_PARAMETERS_REASONING['verbosity']}, "
      f"VERIFICATION reasoning: {current_config.MODEL_PARAMETERS_VERIFICATION['reasoning_effort']}, "
      f"VERIFICATION verbosity: {current_config.MODEL_PARAMETERS_VERIFICATION['verbosity']}")

client = OpenAI(api_key=os.environ['OPENAI_API_KEY'])

#---------------

instructions = prompt_templates.Instructions()
prompt = prompt_templates.JaehrlicherErfuellungsaufwand(current_config.REGULATION_1_DESCRIPTOR,
                                                        current_config.REGULATION_1_TEXT)

question = question_assembler.Question(client, instructions, prompt)
question.run_and_save_multiple_questions()
question.choose_and_save_best_answer()
question.save_answers_as_csvs()
question.save_best_answer_as_csv()
question.verify_and_save_sources()

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


print('Finishing chatterbox at {}'.format(datetime.now().strftime("%H:%M")))

