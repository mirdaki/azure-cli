# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------
from __future__ import print_function

from collections import namedtuple
import random
import json
import re
import sys
import platform
import os.path
import requests
import colorama


from azure.cli.core import telemetry as telemetry_core
from azure.cli.core import __version__ as core_version
# from azure.cli.core.cloud import CLOUDS_FORBIDDING_ALADDIN_REQUEST
from azure.cli.core.commands.constants import SURVEY_PROMPT
from azure.cli.command_modules.find.acr_artifacts import download_artifact
from azure.cli.command_modules.find.model_file import get_model_file
from pkg_resources import parse_version
from knack.log import get_logger
logger = get_logger(__name__)

WAIT_MESSAGE = ['Finding examples...']

EXTENSION_NAME = 'find'

ACR_NAME = 'aladdinmodel'
ARTIFACT_PATH = 'aladdin/cli'
ARTIFACT_TYPE = 'application/vnd.microsoft.aladdin-model.cli.layer.v1.json'
ARTIFACT_FILE_NAME = 'aladdinExamplesModel{}.json'
ARTIFACT_FORMAT_VERSION = 'v1.0'

CONFIG_HEADER = 'aladdin'
CONFIG_SHOULD_DOWNLOAD_ARTIFACT = 'should_download_artifact'

OFFLINE_MODEL_MESSAGE = 'A model can be downloaded for faster results from the `az find` command.'
AIR_GAPPED_MODEL_MESSAGE = 'A model needs to be downloaded for this command to function.'
DOWNLOAD_MODEL_PROMPT = 'Would you like to enable this behavior (option can be changed in the config file) (y/n): '
MODEL_DOWNLOAD_START_MESSAGE = 'Downloading, this may take a movement.'
MODEL_DOWNLOAD_END_MESSAGE = 'Model successfully downloaded.'
MODEL_DOWNLOAD_ERROR_MESSAGE = 'Something went wrong. Please try again later. Please report the problem if it persist.'
CHANGE_MODEL_DOWNLOAD_CONFIG_MESSAGE = '\nTo change the model download setting, go to the config file at "{}" and change "{}" under "{}".'


Example = namedtuple("Example", "title snippet")

# TODO: Add a -y/--yes (and possibly no) flag for the command
# TODO: Break up find module (acr, model file, generic service, examples service) look at the task for more. Use this to call into others and do the CLI printing, formating, etc
# TODO: Upload a larger file to see how perf works

# TODO: Test these paths for both air-gapped and public clouds
#   1. First run
#   2. Run after disabling offline
#   3. Run after enabling offline
#   4. Run with -y as first run

def process_query(cmd, cli_term):
    if not cli_term:
        logger.error('Please provide a search term e.g. az find "vm"')
    else:
        # Collect values for model version
        config = cmd.cli_ctx.config
        cli_version = 'v{}'.format(telemetry_core._get_core_version())  # pylint: disable=protected-access
        artifact_file_name = ARTIFACT_FILE_NAME.format(cli_version)
        artifact_file_path = config.config_dir

        # Use this to check if we are in an air-gapped cloud or not
        # is_air_gapped_cloud = cmd.cli_ctx and cmd.cli_ctx.cloud and cmd.cli_ctx.cloud.name not in CLOUDS_FORBIDDING_ALADDIN_REQUEST # TODO: Enable this once available in codebase
        is_air_gapped_cloud = False

        # Check if the offline model is enabled and exists, even a prior version
        model_file_path = get_model_file(artifact_file_path, ARTIFACT_FILE_NAME, cli_version)
        is_offline_config_set = config.has_option(CONFIG_HEADER, CONFIG_SHOULD_DOWNLOAD_ARTIFACT)
        is_offline_enabled = is_offline_config_set and config.get(CONFIG_HEADER, CONFIG_SHOULD_DOWNLOAD_ARTIFACT)

        if is_offline_enabled.lower() == 'true' and model_file_path:
            # TODO: Call the model
            print("TODO")
        elif not is_air_gapped_cloud:
            # Query Service
            query_examples(cli_term)
        else:
            print(AIR_GAPPED_MODEL_MESSAGE)

    # Ask about enabling the model
    if not is_offline_config_set:
        if not is_air_gapped_cloud:
            print(OFFLINE_MODEL_MESSAGE)
        user_input = input(DOWNLOAD_MODEL_PROMPT)
        if user_input.lower() == 'y' or user_input.lower() == 'yes':
            download_path = os.path.join(artifact_file_path, artifact_file_name)
            download_success = download_artifact(download_path, ACR_NAME, ARTIFACT_PATH, ARTIFACT_FORMAT_VERSION, ARTIFACT_TYPE)
            if download_success:
                config.set_value(CONFIG_HEADER, CONFIG_SHOULD_DOWNLOAD_ARTIFACT, 'True')
                print(MODEL_DOWNLOAD_END_MESSAGE)
            else:
                print(MODEL_DOWNLOAD_ERROR_MESSAGE)
        else:
            config.set_value(CONFIG_HEADER, CONFIG_SHOULD_DOWNLOAD_ARTIFACT, 'False')

    # Wrap up message
    print(CHANGE_MODEL_DOWNLOAD_CONFIG_MESSAGE.format(config.config_path, CONFIG_SHOULD_DOWNLOAD_ARTIFACT, CONFIG_HEADER))
    from azure.cli.core.util import show_updates_available
    show_updates_available(new_line_after=True)
    print(SURVEY_PROMPT)


def query_examples(cli_term):
    print(random.choice(WAIT_MESSAGE), file=sys.stderr)
    response = call_aladdin_service(cli_term)

    if response.status_code != 200:
        logger.error('Unexpected Error: If it persists, please file a bug.')
    else:
        if (platform.system() == 'Windows' and should_enable_styling()):
            colorama.init(convert=True)
        has_pruned_answer = False
        answer_list = json.loads(response.content)
        if not answer_list:
            print("\nSorry I am not able to help with [" + cli_term + "]."
                "\nTry typing the beginning of a command e.g. " + style_message('az vm') + ".", file=sys.stderr)
        else:
            if answer_list[0]['source'] == 'pruned':
                has_pruned_answer = True
                answer_list.pop(0)
            print("\nHere are the most common ways to use [" + cli_term + "]: \n", file=sys.stderr)

            for answer in answer_list:
                cleaned_answer = clean_from_http_answer(answer)
                print(style_message(cleaned_answer.title))
                print(cleaned_answer.snippet + '\n')
            if has_pruned_answer:
                print(style_message("More commands and examples are available in the latest version of the CLI. "
                                    "Please update for the best experience.\n"))


def get_generated_examples(cli_term):
    examples = []
    response = call_aladdin_service(cli_term)

    if response.status_code == 200:
        for answer in json.loads(response.content):
            examples.append(clean_from_http_answer(answer))

    return examples


def style_message(msg):
    if should_enable_styling():
        try:
            msg = colorama.Style.BRIGHT + msg + colorama.Style.RESET_ALL
        except KeyError:
            pass
    return msg


def should_enable_styling():
    try:
        # Style if tty stream is available
        if sys.stdout.isatty():
            return True
    except AttributeError:
        pass
    return False


def call_aladdin_service(query):
    version = str(parse_version(core_version))
    correlation_id = telemetry_core._session.correlation_id   # pylint: disable=protected-access
    subscription_id = telemetry_core._get_azure_subscription_id()  # pylint: disable=protected-access

    context = {
        "versionNumber": version,
    }

    # Only pull in the contextual values if we have consent
    if telemetry_core.is_telemetry_enabled():
        context['correlationId'] = correlation_id

    if telemetry_core.is_telemetry_enabled() and subscription_id is not None:
        context['subscriptionId'] = subscription_id

    api_url = 'https://app.aladdin.microsoft.com/api/v1.0/examples'
    headers = {'Content-Type': 'application/json'}

    response = requests.get(
        api_url,
        params={
            'query': query,
            'clientType': 'AzureCli',
            'context': json.dumps(context)
        },
        headers=headers)

    return response


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
