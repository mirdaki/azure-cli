# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------
from collections import namedtuple
import re
import json


from azure.cli.command_modules.find._aladdin_service import call_aladdin_service


EXAMPLE_ENDPOINT = 'examples'


Example = namedtuple("Example", "title snippet")


# TODO: Should add json.dumps(cli_term) for all params?
def get_examples(cli_term, strict):
    examples = []
    pruned_examples = False
    call_successful = False

    params = {
        'query': json.dumps(cli_term)
    }
    if strict:
        params['commandOnly'] = True
        params['numberOfExamples'] = 5

    response = call_aladdin_service(EXAMPLE_ENDPOINT, params)

    if response and response.status_code == 200:
        call_successful = True
        answers = json.loads(response.content)

        if answers and answers[0]['source'] == 'pruned':
            pruned_examples = True
            answers = answers[1:]

        for answer in answers:
            examples.append(clean_from_http_answer(answer))

    return (call_successful, pruned_examples, examples)


def clean_from_http_answer(http_answer):
    current_title = http_answer['title'].strip()
    current_snippet = http_answer['snippet'].strip()
    if current_title.startswith("az "):
        current_title, current_snippet = current_snippet, current_title
        current_title = current_title.split('\r\n')[0]
    elif '```azurecli\r\n' in current_snippet:
        start_index = current_snippet.index('```azurecli\r\n') + len('```azurecli\r\n')
        current_snippet = current_snippet[start_index:]
    current_snippet = current_snippet.replace('```', '').replace(current_title, '').strip()
    current_snippet = re.sub(r'\[.*\]', '', current_snippet).strip()
    return Example(current_title, current_snippet)
