import pandas as pd

from io import StringIO


def parse_single_answer_to_df(answer, json_template):
    """ answer can be a valid JSON str, path object or file-like object"""
    if not answer.strip():
        # raise ValueError("Answer text is empty.")
        return pd.DataFrame()
    if answer.strip().startswith('{') or answer.strip().startswith('['):
        # Direct JSON string, bit crude check
        answer_to_parse = StringIO(answer.strip())
    else: # Assume file path
        answer_to_parse = answer
    if json_template == 'json_ea_yearly': # maybe this will not be necessary and the template can be removed
        try:  # TODO: implement json syntax and character checker? https://github.com/mangiucugna/json_repair/
            return pd.read_json(answer_to_parse)
        except Exception as e:
            print(f"Could not save answers as CSVs: {e}")  # TODO: logging
    return pd.DataFrame()


def parse_single_answer_to_csv(answer, output_file, json_template):
    parse_single_answer_to_df(answer, json_template).to_csv(output_file, index=False)


def flatten_sources_from_answer_df(df, sources_column='Quellen'):
    """ DataFrame df must have a column which contains lists of sources. """
    return [source for source_list in df[sources_column] for source in source_list]


def flatten_sources_from_multiple_answers(list_of_answers, json_template, sources_column='Quellen'):
    all_sources = []
    for answer in list_of_answers:
        df = parse_single_answer_to_df(answer, json_template)
        sources = flatten_sources_from_answer_df(df, sources_column)
        all_sources.extend(sources)
    return all_sources


def list_of_sources_from_multiple_responses(list_of_responses, json_template, sources_column='Quellen'):
    """  E.g. use question.responses. For now, all responses should adhere to the same template and have the same
    sources column name. """
    list_of_answers = [response.output_text for response in list_of_responses]
    return flatten_sources_from_multiple_answers(list_of_answers, json_template, sources_column)
