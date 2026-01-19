import os
from datetime import datetime


this_directory = os.path.dirname(__file__)

class DefaultConfig:

    def __init__(self, regulation_1_descriptor=None, regulation_1_filename=None, regulation_2_descriptor=None,
                 regulation_2_filename=None, choose_best_of=None, save_entire_responses=False, timeout_in_minutes=120,
                 log_level_console='INFO', log_level_file='INFO'):

        self.REGULATION_1_DESCRIPTOR = regulation_1_descriptor
        self.REGULATION_2_DESCRIPTOR = regulation_2_descriptor
        self.REGULATION_1_FILENAME = regulation_1_filename
        self.REGULATION_2_FILENAME = regulation_2_filename
        self.REGULATION_1_TEXT = None
        self.REGULATION_2_TEXT = None
        self.CHOOSE_BEST_OF = choose_best_of
        self.SAVE_ENTIRE_RESPONSES = save_entire_responses
        self.LOG_LEVEL_CONSOLE = log_level_console
        self.LOG_LEVEL_FILE = log_level_file
        self.RESULT_FOLDER = os.path.join(
            this_directory,
            "..",
            "..",
            "results",
            f'chat_{datetime.now().strftime("%Y%m%d-%H%M")}',
        )
        os.makedirs(self.RESULT_FOLDER, exist_ok=True)
        self.TIMEOUT_IN_MINUTES = timeout_in_minutes
        if self.REGULATION_1_FILENAME:
            with open(os.path.join(this_directory, "..", "..", "regulations", self.REGULATION_1_FILENAME), 'r',
                      encoding='utf-8') as file:
                self.REGULATION_1_TEXT = file.read()
        if self.REGULATION_2_FILENAME:
            with open(os.path.join(this_directory, "..", "..", "regulations", self.REGULATION_2_FILENAME), 'r',
                      encoding='utf-8') as file:
                self.REGULATION_2_TEXT = file.read()

    def write_config(self, filename='config_parameters.txt'):
        """ Write all config parameters (instance and class attributes) to a text file.

        Collects instance attributes (vars(self)) and class attributes from the MRO up to DefaultConfig,
        merges them (instance wins), then writes sorted key: json_value lines for readability and robustness.
        """
        import json
        # collect instance attributes
        data = {}
        for k, v in vars(self).items():
            if k.startswith('_') or callable(v):
                continue
            data[k] = v

        # collect class attributes from the MRO (child class first), stop at DefaultConfig
        for cls in self.__class__.__mro__:
            if cls is object:
                break
            for k, v in vars(cls).items():
                if k.startswith('_') or callable(v):
                    continue
                if k not in data:
                    data[k] = v
            if cls is DefaultConfig:
                break

        # write sorted key / json-serialized value lines
        with open(os.path.join(self.RESULT_FOLDER, filename), 'w', encoding='utf-8') as f:
            for k in sorted(data):
                v = data[k]
                try:
                    serialized = json.dumps(v, ensure_ascii=False, default=str)
                except Exception:
                    serialized = str(v)
                f.write(f'{k}: {serialized}\n')


class OpenAiConfig(DefaultConfig):
    _DEFAULT_MODEL_PARAMETERS_REASONING = {
        'model': 'gpt-5',
        'reasoning_effort': 'high', # "minimal" | "low" | "medium" | "high"
        'verbosity': 'medium'  # low → terse UX, minimal prose / medium (default) → balanced detail /
                               # high → verbose, great for audits, teaching, or hand-offs.
    }
    _DEFAULT_MODEL_PARAMETERS_VERIFICATION = {
        'model': 'gpt-5',
        'reasoning_effort': 'low',
        'verbosity': 'low'
    }


    def __init__(self, regulation_1_descriptor=None, regulation_1_filename=None, regulation_2_descriptor=None,
                 regulation_2_filename=None, choose_best_of=None, save_entire_responses=False,
                 model_parameters_reasoning = None, model_parameters_verification = None, api_type='openai',
                 log_level_console='INFO', log_level_file='INFO'):
        # forward regulation filenames to the base class
        super().__init__(regulation_1_descriptor=regulation_1_descriptor,
                         regulation_1_filename=regulation_1_filename,
                         regulation_2_descriptor=regulation_2_descriptor,
                         regulation_2_filename=regulation_2_filename,
                         choose_best_of=choose_best_of,
                         save_entire_responses=save_entire_responses,
                         log_level_console=log_level_console,
                         log_level_file=log_level_file)

        # accept provided model parameters or use defaults
        self.MODEL_PARAMETERS_REASONING = model_parameters_reasoning if model_parameters_reasoning is not None \
            else self._DEFAULT_MODEL_PARAMETERS_REASONING
        self.MODEL_PARAMETERS_VERIFICATION = model_parameters_verification if model_parameters_verification is not None \
            else self._DEFAULT_MODEL_PARAMETERS_VERIFICATION
        self.API_TYPE = api_type

        # write config parameters to file for reference
        self.write_config()  # writes `config_parameters.txt` under `self.RESULT_FOLDER`

class GeminiConfig(DefaultConfig):

    _DEFAULT_MODEL_PARAMETERS_REASONING = 'gemini-2.5-pro'
    _DEFAULT_MODEL_PARAMETERS_VERIFICATION = 'gemini-2.5-flash'

    def __init__(self, regulation_1_descriptor=None, regulation_1_filename=None, regulation_2_descriptor=None,
                 regulation_2_filename=None, choose_best_of=None, save_entire_responses=False,
                 model_parameters_reasoning = None, model_parameters_verification = None,
                 log_level_console='INFO', log_level_file='INFO'):
        # forward regulation filenames to the base class
        super().__init__(regulation_1_descriptor=regulation_1_descriptor,
                         regulation_1_filename=regulation_1_filename,
                         regulation_2_descriptor=regulation_2_descriptor,
                         regulation_2_filename=regulation_2_filename,
                         choose_best_of=choose_best_of,
                         save_entire_responses=save_entire_responses,
                         log_level_console=log_level_console,
                         log_level_file=log_level_file)

        # accept provided model parameters or use defaults
        self.MODEL_PARAMETERS_REASONING = model_parameters_reasoning if model_parameters_reasoning is not None \
            else self._DEFAULT_MODEL_PARAMETERS_REASONING
        self.MODEL_PARAMETERS_VERIFICATION = model_parameters_verification if model_parameters_verification is not None \
            else self._DEFAULT_MODEL_PARAMETERS_VERIFICATION
        self.API_TYPE = 'gemini'

        # write config parameters to file for reference
        self.write_config()  # writes `config_parameters.txt` under `self.RESULT_FOLDER`
