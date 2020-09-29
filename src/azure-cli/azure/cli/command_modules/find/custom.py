# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------
from __future__ import print_function

import json
import sys
import platform
import os.path
import colorama


from azure.cli.core import telemetry as telemetry_core
from azure.cli.core import __version__ as core_version
from azure.cli.core.cloud import CLOUDS_FORBIDDING_ALADDIN_REQUEST
from azure.cli.core.commands.constants import SURVEY_PROMPT

from azure.cli.command_modules.find._acr_artifacts import download_artifact
from azure.cli.command_modules.find._constants import (
    ACR_NAME,
    ARTIFACT_PATH,
    ARTIFACT_TYPE,
    ARTIFACT_FILE_NAME,
    ARTIFACT_FORMAT_VERSION,
    CONFIG_HEADER,
    CONFIG_SHOULD_DOWNLOAD_ARTIFACT,
    CONFIG_ENABLE_VALUE,
    CONFIG_DISABLE_VALUE,
    MESSAGE_OFFLINE_MODEL,
    MESSAGE_AIR_GAPPED_MODEL,
    MESSAGE_MODEL_DOWNLOAD_START,
    MESSAGE_MODEL_DOWNLOAD_END,
    MESSAGE_MODEL_DOWNLOAD_ERROR,
    MESSAGE_CHANGE_MODEL_DOWNLOAD_CONFIG,
    MESSAGE_WAIT,
    PROMPT_DOWNLOAD_MODEL
)
from azure.cli.command_modules.find._example_service import get_examples
from azure.cli.command_modules.find._model_file import get_model_file
from azure.cli.command_modules.find._style import style_message, should_enable_styling

from knack.log import get_logger
logger = get_logger(__name__)


# TODO: Add a -y/--yes (and possibly no) flag for the command

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
        is_air_gapped_cloud = cmd.cli_ctx and cmd.cli_ctx.cloud and cmd.cli_ctx.cloud.name in CLOUDS_FORBIDDING_ALADDIN_REQUEST

        # Check if the offline model is enabled and exists, even a prior version
        model_file_path = get_model_file(artifact_file_path, ARTIFACT_FILE_NAME, cli_version)
        is_offline_config_set = config.has_option(CONFIG_HEADER, CONFIG_SHOULD_DOWNLOAD_ARTIFACT)
        is_offline_enabled = "false" #is_offline_config_set and config.get(CONFIG_HEADER, CONFIG_SHOULD_DOWNLOAD_ARTIFACT)

        if is_offline_enabled.lower() == CONFIG_ENABLE_VALUE and model_file_path:
            print("TODO")
        elif not is_air_gapped_cloud:
            query_example_service(cli_term)
        else:
            print(MESSAGE_AIR_GAPPED_MODEL)

        # Ask about enabling the model
        if not is_offline_config_set:
            offline_config_prompt(config, is_air_gapped_cloud, artifact_file_path, artifact_file_name, False)

    # Wrap up message
    print(MESSAGE_CHANGE_MODEL_DOWNLOAD_CONFIG.format(config.config_path, CONFIG_SHOULD_DOWNLOAD_ARTIFACT, CONFIG_HEADER))
    from azure.cli.core.util import show_updates_available
    show_updates_available(new_line_after=True)
    print(SURVEY_PROMPT)


def query_example_service(cli_term):
    print(MESSAGE_WAIT, file=sys.stderr)
    (call_successful, pruned_examples, examples) = get_examples(cli_term, False)

    if call_successful:
        if (platform.system() == 'Windows' and should_enable_styling()):
            colorama.init(convert=True)

        if not examples:
            print("\nSorry I am not able to help with [" + cli_term + "]."
                  "\nTry typing the beginning of a command e.g. " + style_message('az vm') + ".", file=sys.stderr)
        else:
            print("\nHere are the most common ways to use [" + cli_term + "]: \n", file=sys.stderr)
            for example in examples:
                print(style_message(example.title))
                print(example.snippet + '\n')
            if pruned_examples:
                print(style_message("More commands and examples are available in the latest version of the CLI. "
                                    "Please update for the best experience.\n"))
    else:
        logger.error('Unexpected Error: If it persists, please file a bug.')


def offline_config_prompt(config, is_air_gapped_cloud, artifact_file_path, artifact_file_name, yes_flag):
    if not is_air_gapped_cloud:
        print(MESSAGE_OFFLINE_MODEL)
    user_input = input(PROMPT_DOWNLOAD_MODEL)
    if user_input.lower() == 'y' or user_input.lower() == 'yes' or yes_flag:
        print(MESSAGE_MODEL_DOWNLOAD_START)
        download_path = os.path.join(artifact_file_path, artifact_file_name)
        download_success = download_artifact(download_path, ACR_NAME, ARTIFACT_PATH, ARTIFACT_FORMAT_VERSION, ARTIFACT_TYPE)  # pylint: disable=line-too-long
        if download_success:
            config.set_value(CONFIG_HEADER, CONFIG_SHOULD_DOWNLOAD_ARTIFACT, CONFIG_ENABLE_VALUE)
            print(MESSAGE_MODEL_DOWNLOAD_END)
        else:
            print(MESSAGE_MODEL_DOWNLOAD_ERROR)
    else:
        config.set_value(CONFIG_HEADER, CONFIG_SHOULD_DOWNLOAD_ARTIFACT, CONFIG_DISABLE_VALUE)
