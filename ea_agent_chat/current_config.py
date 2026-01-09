from ea_agent_chat.config import OpenAiConfig

current_config = OpenAiConfig(
    regulation_1_descriptor='Arbeitstagepauschale aktuell',
    regulation_1_filename='arbeitstagepauschale_current.txt',
    regulation_2_descriptor='Arbeitstagepauschale Reformvorschlag',
    regulation_2_filename='arbeitstagepauschale_reform.txt',
    choose_best_of=2,
    model_parameters_reasoning={'model': 'gpt-5', 'reasoning_effort': 'high', 'verbosity': 'medium'},
    model_parameters_verification = {'model': 'gpt-5', 'reasoning_effort': 'low', 'verbosity': 'low'},
    save_entire_responses=True,
    # Logging levels: DEBUG < INFO < WARNING < ERROR < CRITICAL.
    # Set console/file separately; lower level = more chatter. Example: WARNING omits INFO.
    log_level_console='INFO',
    log_level_file='DEBUG'
)


# current_config = OpenAiConfig(
#     regulation_1_descriptor='Arbeitstagepauschale aktuell',
#     regulation_1_filename='arbeitstagepauschale_current.txt',
#     regulation_2_descriptor='Arbeitstagepauschale Reformvorschlag',
#     regulation_2_filename='arbeitstagepauschale_reform.txt',
#     choose_best_of=2,
#     model_parameters_reasoning={'model': 'gemini-2.5-pro', 'reasoning_effort': '24576'},
#     model_parameters_verification = {'model': 'gemini-2.5-flash', 'reasoning_effort': '1024'},
#     api_type='openai_with_gemini'
# )
