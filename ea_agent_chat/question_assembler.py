import os

from datetime import datetime, timedelta
from openai import BadRequestError
from time import sleep

from ea_agent_chat import parser
from ea_agent_chat import prompt_templates
from ea_agent_chat.current_config import current_config


def construct_call(client, instruction_text, prompt_text, task_type, previous_response_id=None):
    if task_type == 'reasoning':
        model_parameters = current_config.MODEL_PARAMETERS_REASONING
    elif task_type == 'verification':
        model_parameters = current_config.MODEL_PARAMETERS_VERIFICATION
    else:
        raise ValueError('Invalid task description in construct_call().')

    kwargs = {
        "model": model_parameters.get('model'),
        "instructions": instruction_text,
        "reasoning": { "effort": model_parameters.get('reasoning_effort')},
        "text": { "verbosity": model_parameters.get('verbosity')},
        "input": [{'role': 'user', 'content': [{"type": "input_text", "text": prompt_text}]}]
    }
    # Even when using previous_response_id, all previous input tokens for responses in the chain are billed as
    # input tokens in the API. Only send the parameter when you have an ID (passing "" can trigger a BadRequest).
    if previous_response_id:
        kwargs["previous_response_id"] = previous_response_id

    return client.responses.create(**kwargs)


#  When called, each call should only retrieve one file at a time for simplicity
class Question:
    def __init__(self, client, instructions, prompt, previous_response_id=None):
        self.client = client
        self.instructions = instructions
        self.prompt = prompt
        self.answer_file_stem = f"{prompt.name}{'_' + prompt.regelung_kurzform if prompt.regelung_kurzform else ''}"
        self.previous_response_id = previous_response_id
        self.responses = []
        self.best_response = None
        self.verified_sources = None

    def add_current_response(self, response):
        self.responses.append(response)

    def save_current_answer_to_file(self, folder, filenumber=None):
        if self.responses and os.path.isdir(folder) and self.answer_file_stem:
            with open(os.path.join(folder, '{}{}.json'.format(self.answer_file_stem,
                    f'_{filenumber:02}' if filenumber else '')), 'w', encoding='utf-8') as f:
                f.write(self.responses[-1].output_text)
        else:
            print(f'No answer was saved for question {self.answer_file_stem} ({filenumber=}).')

    def save_best_answer_to_file(self, folder):
        if self.best_response and os.path.isdir(folder) and self.answer_file_stem:
            with open(os.path.join(folder, f'{self.answer_file_stem}_best.json'), 'w', encoding='utf-8') as f:
                f.write(self.best_response.output_text)
        else:
            print(f'No best answer was saved for question {self.answer_file_stem}.')

    def create_single_response(self, task_type):
        response  = construct_call(self.client, self.instructions.text, self.prompt.text, task_type,
                                   self.previous_response_id)
        self.add_current_response(response)
        return response

    def run_and_save_multiple_questions(self, task_type='reasoning',
                                        timeout_in_minutes=current_config.TIMEOUT_IN_MINUTES):
        start_time = datetime.now()
        max_duration = timedelta(minutes=timeout_in_minutes) if timeout_in_minutes else None

        print('Starting queries at {}'.format(start_time.strftime("%H:%M")))

        # Loop through conversation
        for i in range(current_config.CHOOSE_BEST_OF):

            while True:
                if max_duration and datetime.now() - start_time > max_duration:
                    print(f"{max_duration} minutes elapsed. Stopping.")
                    break
                try:
                    self.create_single_response(task_type)
                    break
                except BadRequestError as e:
                    print(f'Sleeping for 10 seconds due to bad request: {e}')
                    sleep(10)
                    continue
                except Exception as e:
                    # Stop for any other errors. Examples that happened so far: "Error code: 403", APIRequestTimeoutError
                    print(f"Unexpected error occurred: {e}")
                    break

            print('Question {} answered at {}'.format(i, datetime.now().strftime("%H:%M")))
            self.save_current_answer_to_file(current_config.RESULT_FOLDER, i+1)

    def choose_best_answer(self, task_type='reasoning'):
        response = construct_call(self.client, self.instructions.text,
                                  prompt_templates.ChooseBestAnswerFromList(self.prompt.text,
                                  [r.output_text for r in self.responses]).text, task_type)
        self.best_response = response
        return response

    def choose_and_save_best_answer(self, task_type='reasoning'):

        # Should be outside this function really?
        self.choose_best_answer(task_type)
        self.save_best_answer_to_file(current_config.RESULT_FOLDER)
        print('Best answer file chosen at {}'.format(datetime.now().strftime("%H:%M")))
        return

    def save_answers_as_csvs(self):
        for i, r in enumerate(self.responses):
            if r:
                answer_csv = os.path.join(current_config.RESULT_FOLDER, f'{self.answer_file_stem}_{i+1:02}.csv')
                parser.parse_single_answer_to_df(r.output_text,
                                                 self.prompt.json_template_name).to_csv(answer_csv, index=False)

    def save_best_answer_as_csv(self):
        if self.best_response:
            answer_csv = os.path.join(current_config.RESULT_FOLDER, f'{self.answer_file_stem}_best.csv')
            parser.parse_single_answer_to_df(self.best_response.output_text,
                                             self.prompt.json_template_name).to_csv(answer_csv, index=False)

    def verify_and_save_sources(self):
        source_list = parser.list_of_sources_from_multiple_responses(self.responses, self.prompt.json_template_name)
        self.verified_sources = construct_call(self.client, self.instructions.text,
                                               prompt_templates.VerifyWebSources(source_list).text,
                                               task_type='verification', previous_response_id=None)
        output_file = os.path.join(current_config.RESULT_FOLDER, f'{self.answer_file_stem}_verified_sources.csv')
        parser.parse_single_answer_to_csv(self.verified_sources.output_text, output_file, self.prompt.json_template_name)