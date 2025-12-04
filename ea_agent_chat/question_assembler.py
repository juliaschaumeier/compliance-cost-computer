import json
import os

from datetime import datetime, timedelta
from openai import BadRequestError
from time import sleep

from ea_agent_chat import api_helper
from ea_agent_chat import parser
from ea_agent_chat import prompt_templates
from ea_agent_chat.current_config import current_config


#  When called, each call should only retrieve one file at a time for simplicity
class Question:
    def __init__(self, api, instructions, prompt, previous_question=None):
        self.api = api
        self.client = api.client
        self.instructions = instructions.text
        self.prompt = prompt
        if previous_question:
            self.answer_file_stem = f"{previous_question.answer_file_stem}_{prompt.name}"
            self.previous_response_id = previous_question.best_response.id if previous_question.best_response else \
                previous_question.responses[-1].id # TODO: get id of original response object, not best response object
        else:
            self.answer_file_stem = f"{prompt.name}{'_' + prompt.regelung_kurzform if prompt.regelung_kurzform else ''}"
            self.previous_response_id = None
        self.responses = []
        self.best_response = None
        self.verified_sources = None

    # def save_current_answer_to_file(self, folder, filenumber=None):
    #     if self.responses and os.path.isdir(folder) and self.answer_file_stem:
    #         with open(os.path.join(folder, '{}{}.{}'.format(self.answer_file_stem,
    #                   f'_{filenumber:02}' if filenumber else '', self.prompt.expected_answer_file_type)),
    #                   'w', encoding='utf-8') as f:
    #             f.write(self.responses[-1].output_text)
    #         if current_config.save_entire_responses:
    #             save_response_to_file(self.responses[-1], os.path.join(folder, 'response_{}{}.json'.format(self.answer_file_stem,
    #                       f'_{filenumber:02}' if filenumber else '')))
    #     else:
    #         print(f'No answer was saved for question {self.answer_file_stem} ({filenumber=}).')

    # TODO: tidy up!!
    def run_and_save_multiple_questions(self, timeout_in_minutes=current_config.TIMEOUT_IN_MINUTES):
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
                    response = self.api.ask_question(self.instructions, self.prompt,
                                                     f'{self.answer_file_stem}_{(i + 1):02}',
                                                     self.previous_response_id)
                    self.responses.append(response)
                    break
                except BadRequestError as e:
                    print(f'Sleeping for 10 seconds due to bad request: {e}')
                    sleep(10)
                    continue
                # except Exception as e:
                #     # Stop for any other errors. Examples that happened so far: "Error code: 403", APIRequestTimeoutError,
                #     # openai.APIConnectionError
                #     print(f"Unexpected error occurred: {e}")
                #     # break
                #     continue
            print('Question {} answered at {}'.format(i+1, datetime.now().strftime("%H:%M")))


    def choose_best_answer(self):
        prompt = prompt_templates.ChooseBestAnswerFromList(self.prompt, [r.output_text for r in self.responses])
        response = self.api.ask_question(self.instructions, prompt, file_stem=f'{self.answer_file_stem}_best')
        self.best_response = response # TODO: This gives a new best_response object, not one of the original responses,
        # TODO: maybe always choose answer (unless best out of 1)

        print('Best answer file chosen at {}'.format(datetime.now().strftime("%H:%M")))
        return response

    def save_response_as_csv(self, response):
        if response:
            answer_csv = os.path.join(current_config.RESULT_FOLDER, f'{response.file_stem}.csv')
            parser.parse_single_answer_to_df(response.output_text,
                                             self.prompt.json_template_name).to_csv(answer_csv, index=False)
        else:
            print('No answer was saved as CSV.')

    def save_answers_as_csvs(self):
        for r in self.responses:
            self.save_response_as_csv(r)

    def save_best_answer_as_csv(self):
        self.save_response_as_csv(self.best_response)


    def verify_and_save_sources(self):
        source_list = parser.list_of_sources_from_multiple_responses(self.responses, self.prompt.json_template_name)
        prompt = prompt_templates.VerifyWebSources(source_list)
        self.verified_sources = self.api.ask_question(self.instructions, prompt,
                                                      file_stem=f'{self.answer_file_stem}_verified_sources')
        output_file = os.path.join(current_config.RESULT_FOLDER, f'{self.verified_sources.file_stem}.csv')
        parser.parse_single_answer_to_csv(self.verified_sources.output_text, output_file, self.prompt.json_template_name)
