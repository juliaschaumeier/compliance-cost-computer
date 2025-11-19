from ea_agent_chat.config import OpenAiConfig

current_config = OpenAiConfig(
    regulation_1_descriptor='Arbeitstagepauschale aktuell',
    regulation_1_filename='arbeitstagepauschale_current.txt',
    choose_best_of=2,
    model_parameters_reasoning={'model': 'gpt-5', 'reasoning_effort': 'low', 'verbosity': 'low'},
    model_parameters_verification = {'model': 'gpt-5', 'reasoning_effort': 'low', 'verbosity': 'low'}
)
