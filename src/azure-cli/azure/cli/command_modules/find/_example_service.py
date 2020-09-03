# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------
from collections import namedtuple
import re
import json


from azure.cli.command_modules.find.aladdin_service import call_aladdin_service
from azure.cli.command_modules.find.aladdin_service import API_VERSION


EXAMPLE_ENDPOINT = 'examples'


Example = namedtuple("Example", "title snippet")


def get_lenient_examples(cli_term):
    params = {
        'query': json.dumps(cli_term)
    }
    return call_aladdin_service(API_VERSION, EXAMPLE_ENDPOINT, params)


# TODO: Should add json.dumps(cli_term) for all params?
def get_strict_examples(cli_term):
    params = {
        'query': json.dumps(cli_term),
        'commandOnly': True,
        'numberOfExamples': 5
    }
    return call_aladdin_service(API_VERSION, EXAMPLE_ENDPOINT, params)


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
