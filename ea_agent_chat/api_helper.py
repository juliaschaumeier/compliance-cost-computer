import json
import os
import logging

from google import genai
from openai import OpenAI

from ea_agent_chat.current_config import current_config


logger = logging.getLogger("ea_agent")


class Response:
    def __init__(self, response_id, response_text, response_file_stem, response_file_type):
        self.id = response_id
        self.output_text = response_text # TODO rename output_text to response_text or text for consistency
        self.file_stem = response_file_stem
        self.file_type = response_file_type


class BaseAPI:
    def __init__(self, client):
        self.client = client
        self.current_response_object = None

    @staticmethod
    def get_model_parameters(task_type):
        if task_type == 'reasoning':
            return current_config.MODEL_PARAMETERS_REASONING
        elif task_type == 'verification':
            return current_config.MODEL_PARAMETERS_VERIFICATION
        else:
            raise ValueError('Invalid task description in construct_call().')

    def get_client(self):
        raise NotImplementedError('get_client() must be implemented in subclasses.')
    def construct_call(self, instruction_text, prompt_text, task_type, previous_response_id=None):
        raise NotImplementedError('construct_call() must be implemented in subclasses.')
    def save_current_response_text_to_file(self, file_stem, file_type):
        raise NotImplementedError('save_current_response_text_to_file() must be implemented in subclasses.')
    def save_current_response_object_to_file(self, file_stem):
        raise NotImplementedError('handle_response() must be implemented in subclasses.')
    def get_response_object(self, file_stem=None, file_type=None):
        raise NotImplementedError('create_response_object() must be implemented in subclasses.')

    def ask_question(self, instruction_text, prompt, file_stem=None, previous_response_id=None):
        self.construct_call(instruction_text, prompt.text, prompt.task_type, previous_response_id=previous_response_id)
        # if not self.current_response_object:
        #     print('No response object received from API.')
        #     return Response(None, None, None, None)
        if file_stem and prompt.expected_answer_file_type:
            self.save_current_response_text_to_file(file_stem, prompt.expected_answer_file_type)
        if current_config.SAVE_ENTIRE_RESPONSES:
            self.save_current_response_object_to_file(file_stem)
        return self.get_response_object(file_stem, prompt.expected_answer_file_type)


class OpenAiApi(BaseAPI):
    def __init__(self, client=OpenAI(api_key=os.environ['OPENAI_API_KEY'])):
        super().__init__(client)

    def construct_call(self, instruction_text, prompt_text, task_type, previous_response_id=None):

        model_parameters = BaseAPI.get_model_parameters(task_type)
        kwargs = {
            "model": model_parameters.get('model'),
            "instructions": instruction_text,
            "reasoning": { "effort": model_parameters.get('reasoning_effort')}, # todo: set default if not set???
            "text": { "verbosity": model_parameters.get('verbosity')},
            "tools": [{"type": "web_search"}],
            "input": [{'role': 'user', 'content': [{"type": "input_text", "text": prompt_text}]}]
        }

        # Even when using previous_response_id, all previous input tokens for responses in the chain are billed as
        # input tokens in the API. Only send the parameter when you have an ID (passing "" can trigger a BadRequest).
        if previous_response_id:
            kwargs["previous_response_id"] = previous_response_id

        self.current_response_object = self.client.responses.create(**kwargs)

    def save_current_response_text_to_file(self, file_stem, file_type):
        if self.current_response_object and file_stem:
            with open(os.path.join(current_config.RESULT_FOLDER, '{}.{}'.format(file_stem, file_type)),
                      'w', encoding='utf-8') as f:
                f.write(self.current_response_object.output_text)
        else:
            logger.warning("No answer was saved for question %s.", file_stem)

    def save_current_response_object_to_file(self, file_stem):
        """
        Save the full OpenAI response object to `file_path` as JSON.
        Uses .to_dict() if available, otherwise falls back to __dict__ or str().
        """

        def _default(o):
            if hasattr(o, "to_dict"):
                return o.to_dict()
            if hasattr(o, "__dict__"):
                return o.__dict__
            return str(o)

        file_path = os.path.join(current_config.RESULT_FOLDER, f'response_{file_stem}.json')
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.current_response_object, f, default=_default, ensure_ascii=False, indent=2)
        return

    def get_response_object(self, file_stem=None, file_type=None):
        return Response(response_id=self.current_response_object.id,
                        response_text=self.current_response_object.output_text if self.current_response_object.output_text else '',
                        response_file_stem=file_stem, response_file_type=file_type)


class GeminiApi(BaseAPI):
    def __init__(self, client=genai.Client(api_key=os.environ['GEMINI_API_KEY'])):
        super().__init__(client)

    def construct_call(self, instruction_text, prompt_text, task_type, previous_response_id=None):

        model_parameters = BaseAPI.get_model_parameters(task_type)

        kwargs = {
            "model": model_parameters,
            "instructions": instruction_text,
            "contents": prompt_text,
            "tools": ["google_search"],
        }

        self.current_response_object = self.client.models.generate_content(
            model=model_parameters,
            contents="Explain how AI works in a few words",
        )

        from google import genai
        from google.genai import types

        client = genai.Client()

        grounding_tool = types.Tool(
            google_search=types.GoogleSearch()
        )

        config = types.GenerateContentConfig(
            tools=[grounding_tool]
        )

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents="Who won the euro 2024?",
            config=config,
        )

        logger.info("Gemini response: %s", response.text)

        pass

    def save_current_response_text_to_file(self, file_stem, file_type):
        # Logic to save current response text to file
        pass

    def save_current_response_object_to_file(self, file_stem):
        # Logic to save current response object to file
        pass

    def get_response_object(self, file_stem=None, file_type=None):
        return Response(response_id=self.current_response_object.name,
                        response_text=self.current_response_object.text if self.current_response_object.text else '',
                        response_file_stem=file_stem, response_file_type=file_type)
    pass


# Factory function to get the appropriate API instance based on current_config
def API():
    if current_config.API_TYPE == 'openai':
       return OpenAiApi()
    elif current_config.API_TYPE == 'gemini':
        return GeminiApi()
    elif current_config.API_TYPE == 'openai_with_gemini':
        return OpenAiApi(client=OpenAI(api_key=os.environ['GEMINI_API_KEY'],
                                base_url="https://generativelanguage.googleapis.com/v1beta/openai/"))
    else:
        raise ValueError(f"Unsupported API_TYPE: {current_config.API_TYPE}")
