# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------
from __future__ import print_function

import sys
import platform
import os.path
import colorama

from azure.cli.core import telemetry as telemetry_core
from azure.cli.core import __version__ as core_version
from azure.cli.core.cloud import CLOUDS_FORBIDDING_ALADDIN_REQUEST
from azure.cli.core.commands.constants import SURVEY_PROMPT

from azure.cli.command_modules.find.acr_artifacts import download_artifact, does_current_cli_artifact_exist
from azure.cli.command_modules.find._constants import (
    ACR_LATEST_TAG,
    ACR_NAME,
    ARTIFACT_PATH,
    ARTIFACT_TYPE,
    EXAMPLE_MODEL_NAME_PATTERN,
    MODEL_FOLDER_NAME,
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
from azure.cli.command_modules.find.aladdin_model_files import get_model_file, what_model_files_to_delete, delete_model_files  # pylint: disable=line-too-long
from azure.cli.command_modules.find._example_model import search_examples
from azure.cli.command_modules.find._style import style_message, should_enable_styling

from knack.log import get_logger
logger = get_logger(__name__)


# TODO: Test these paths for both air-gapped and public clouds
#   1. First run
#   2. Run after disabling offline
#   3. Run after enabling offline
#   4. Run with -y as first run

# TODO: Codify somewhere about the Artifact version policy
#  - Always download the current version if available
#       - Fall back to latest version otherwise
#  - Always use the current version if downloaded
#       - Fall back to latest version otherwise
#       - Fall back to the next highest version otherwise
#       - Fail gracefully otherwise
#  - If the current version is not downloaded, check to download
#       - If current version is successfully downloaded, delete all but the last used version

# TODO: Make sure the artifact type is specific to examples

def process_query(cmd, cli_term, yes=None):
    if not cli_term:
        logger.error('Please provide a search term e.g. az find "vm"')
    else:
        config = cmd.cli_ctx.config
        model_directory = os.path.join(config.config_dir, MODEL_FOLDER_NAME)
        cli_version = 'v{}'.format(telemetry_core._get_core_version())  # pylint: disable=protected-access
        example_model_name_for_version = EXAMPLE_MODEL_NAME_PATTERN.format(cli_version)

        # Use this to check if we are in an air-gapped cloud or not
        is_air_gapped_cloud = cmd.cli_ctx and cmd.cli_ctx.cloud and cmd.cli_ctx.cloud.name in CLOUDS_FORBIDDING_ALADDIN_REQUEST  # pylint: disable=line-too-long

        # Check if the offline model is enabled and exists, even a prior version
        active_model_path = _get_best_available_model(model_directory, EXAMPLE_MODEL_NAME_PATTERN, cli_version)
        is_offline_config_set = config.has_option(CONFIG_HEADER, CONFIG_SHOULD_DOWNLOAD_ARTIFACT)
        is_offline_enabled = is_offline_config_set and config.get(CONFIG_HEADER, CONFIG_SHOULD_DOWNLOAD_ARTIFACT)

        # TODO: This is the flow this should move to
        # NOTE: Whenever the model is used, it should do a clean up
        # If not air gapped, use service
        #   If service fails, use offline if available
        # If air gapped, offline enabled, and available, use model

        # If set, check for new model

        # If not offline not set, prompt

        # Print examples from the correct source
        if is_offline_enabled and active_model_path:
            (call_successful, examples) = search_examples(active_model_path, cli_term, False)
            _print_examples(cli_term, call_successful, False, examples)
            _clean_up_old_models(model_directory, EXAMPLE_MODEL_NAME_PATTERN, active_model_path)
        elif not is_air_gapped_cloud:
            (call_successful, pruned_examples, examples) = get_examples(cli_term, False)
            _print_examples(cli_term, call_successful, pruned_examples, examples)
        else:
            print(MESSAGE_AIR_GAPPED_MODEL)

        # Check if there is a new model available and download it
        if is_offline_config_set and active_model_path != os.path.join(model_directory, example_model_name_for_version):
            _update_model_if_available(model_directory, cli_version)

        # Ask about enabling the model
        if not is_offline_config_set:
            _offline_config_prompt(config, is_air_gapped_cloud, model_directory, cli_version, yes)

    # Wrap up message
    print(MESSAGE_CHANGE_MODEL_DOWNLOAD_CONFIG.format(config.config_path, CONFIG_SHOULD_DOWNLOAD_ARTIFACT, CONFIG_HEADER))  # pylint: disable=line-too-long
    from azure.cli.core.util import show_updates_available
    show_updates_available(new_line_after=True)
    print(SURVEY_PROMPT)


def _print_examples(cli_term, call_successful, pruned_examples, examples):
    print(MESSAGE_WAIT, file=sys.stderr)

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


def _offline_config_prompt(config, is_air_gapped_cloud, model_directory, cli_version, yes_flag):
    yes_input = False
    if not is_air_gapped_cloud:
        print(MESSAGE_OFFLINE_MODEL)
    if not yes_flag:
        user_input = input(PROMPT_DOWNLOAD_MODEL)
        yes_input = user_input.lower() == 'y' or user_input.lower() == 'yes'
    if yes_input or yes_flag:
        print(MESSAGE_MODEL_DOWNLOAD_START)
        download_success = download_artifact(model_directory, EXAMPLE_MODEL_NAME_PATTERN, cli_version, ACR_NAME, ARTIFACT_PATH, ARTIFACT_TYPE)  # pylint: disable=line-too-long
        if download_success:
            config.set_value(CONFIG_HEADER, CONFIG_SHOULD_DOWNLOAD_ARTIFACT, CONFIG_ENABLE_VALUE)
            print(MESSAGE_MODEL_DOWNLOAD_END)
        else:
            print(MESSAGE_MODEL_DOWNLOAD_ERROR)
    else:
        config.set_value(CONFIG_HEADER, CONFIG_SHOULD_DOWNLOAD_ARTIFACT, CONFIG_DISABLE_VALUE)


# TODO: Consider adding these to existing files or another utility file
def _get_best_available_model(model_directory, model_name_pattern, cli_version):
    cli_version_model = get_model_file(model_directory, model_name_pattern, cli_version)
    if cli_version_model:
        return cli_version_model
    latest_model = get_model_file(model_directory, model_name_pattern, ACR_LATEST_TAG)
    if latest_model:
        return latest_model
    other_model = get_model_file(model_directory, model_name_pattern, '*')
    if other_model:
        return other_model
    return ''


# TODO: Look into running this asynchronously
def _update_model_if_available(model_directory, cli_version):
    version_to_download = ''
    if does_current_cli_artifact_exist(ACR_NAME, ARTIFACT_PATH, cli_version):
        version_to_download = cli_version
    elif does_current_cli_artifact_exist(ACR_NAME, ARTIFACT_PATH, ACR_LATEST_TAG):
        version_to_download = ACR_LATEST_TAG
    download_artifact(model_directory, EXAMPLE_MODEL_NAME_PATTERN, version_to_download, ACR_NAME, ARTIFACT_PATH, ARTIFACT_TYPE)  # pylint: disable=line-too-long


def _clean_up_old_models(model_directory, model_name_pattern, last_used_model_path):
    models_to_delete = what_model_files_to_delete(model_directory, model_name_pattern, last_used_model_path)
    delete_model_files(models_to_delete)
