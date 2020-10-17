# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------
from __future__ import print_function

import os.path
import platform
import sys
import datetime
import colorama

from azure.cli.core import telemetry as telemetry_core
from azure.cli.core import __version__ as core_version
from azure.cli.core.cloud import CLOUDS_FORBIDDING_ALADDIN_REQUEST
from azure.cli.core.commands.constants import SURVEY_PROMPT

from azure.cli.command_modules.find.acr_artifacts import download_artifact, does_current_cli_artifact_exist
from azure.cli.command_modules.find._constants import *  # pylint: disable=wildcard-import
from azure.cli.command_modules.find._example_service import get_examples
from azure.cli.command_modules.find.aladdin_model_files import get_model_file, what_model_files_to_delete, delete_model_files  # pylint: disable=line-too-long
from azure.cli.command_modules.find._example_model import search_examples
from azure.cli.command_modules.find._style import style_message, should_enable_styling

from knack.log import get_logger
logger = get_logger(__name__)


# NOTE: The model version policy
#  - Always download the current version if available
#       - Fall back to latest version otherwise
#  - Always use the current version if downloaded
#       - Fall back to latest version otherwise
#       - Fall back to the next highest version otherwise
#       - Fail gracefully otherwise
#  - If the last used model works, delete all the other ones
#  - If the current version is not downloaded and it's been long enough since the last check, check to download

# TODO: Check what happens when enabled but not downloaded and the commands if they aren't already configured

def process_query(cmd, cli_term, yes=None):
    '''Called via `az find`. Used to get example CLI commands based off of the query.'''
    if not cli_term:
        logger.error(MESSAGE_TERM_NOT_PROVIDED_ERROR)
    else:
        config = cmd.cli_ctx.config
        model_directory = os.path.join(config.config_dir, MODEL_FOLDER_NAME)
        cli_version = CLI_VERSION_FORMAT.format(telemetry_core._get_core_version())  # pylint: disable=protected-access
        example_model_name_for_version = EXAMPLE_MODEL_NAME_PATTERN.format(cli_version)

        # Use this to check if we are in an air-gapped cloud or not
        is_air_gapped_cloud = cmd.cli_ctx and cmd.cli_ctx.cloud and cmd.cli_ctx.cloud.name in CLOUDS_FORBIDDING_ALADDIN_REQUEST  # pylint: disable=line-too-long

        # Check if the offline model is enabled and exists, even a prior version
        active_model_path = _get_best_available_model(model_directory, EXAMPLE_MODEL_NAME_PATTERN, cli_version)
        is_offline_config_set = config.has_option(CONFIG_HEADER, CONFIG_SHOULD_DOWNLOAD_ARTIFACT)
        is_offline_enabled = is_offline_config_set and config.get(CONFIG_HEADER, CONFIG_SHOULD_DOWNLOAD_ARTIFACT) == 'True'  # pylint: disable=line-too-long
        last_checked_date = _get_last_checked_date_confg(config)

        # Print the examples, if available
        if not is_air_gapped_cloud:
            (call_successful, pruned_examples, examples) = get_examples(cli_term, False)
            # If the service call fails, try the local backup
            if not call_successful and is_offline_enabled and active_model_path:
                (call_successful, pruned_examples, examples) = _search_example_model_and_clean(active_model_path, cli_term, cli_version, model_directory)  # pylint: disable=line-too-long
            _print_examples(cli_term, call_successful, pruned_examples, examples)

        elif is_air_gapped_cloud and is_offline_enabled and active_model_path:
            (call_successful, pruned_examples, examples) = _search_example_model_and_clean(active_model_path, cli_term, cli_version, model_directory)  # pylint: disable=line-too-long
            _print_examples(cli_term, call_successful, pruned_examples, examples)

        else:
            print(MESSAGE_AIR_GAPPED_MODEL_NEEDED)

        # Pull in new model if it exits when the current one is not downloaded and it's past the wait period
        if is_offline_enabled and active_model_path != os.path.join(model_directory, example_model_name_for_version) and _time_to_check_for_new_model(last_checked_date):  # pylint: disable=line-too-long
            _update_model_if_available(model_directory, cli_version)

        # Ask about enabling the model
        if not is_offline_config_set:
            _offline_config_prompt(config, model_directory, cli_version, yes)

    # Wrap up message
    print('\n' + MESSAGE_CHANGE_MODEL_DOWNLOAD_CONFIG.format(config.config_path, CONFIG_SHOULD_DOWNLOAD_ARTIFACT, CONFIG_HEADER))  # pylint: disable=line-too-long
    from azure.cli.core.util import show_updates_available
    show_updates_available(new_line_after=True)
    print(SURVEY_PROMPT)


def update_offline_model(cmd):
    '''Called via `az find offline update`. Used to update to the latest available offline model.'''
    config = cmd.cli_ctx.config
    model_directory = os.path.join(config.config_dir, MODEL_FOLDER_NAME)
    cli_version = CLI_VERSION_FORMAT.format(telemetry_core._get_core_version())  # pylint: disable=protected-access

    print(MESSAGE_OFFLINE_UPDATE)
    download_success = _update_model_if_available(model_directory, cli_version)
    if download_success:
        print(MESSAGE_OFFLINE_UPDATE_SUCCESS)
    else:
        print(MESSAGE_OFFLINE_UPDATE_FAIL)


def delete_offline_model(cmd):
    '''Called via `az find offline delete`. Used to delete the locally downloaded offline models.'''
    config = cmd.cli_ctx.config
    model_directory = os.path.join(config.config_dir, MODEL_FOLDER_NAME)

    print(MESSAGE_OFFLINE_DELETE)
    _clean_up_old_models(model_directory, EXAMPLE_MODEL_NAME_PATTERN, '')


def enable_offline_model(cmd):
    '''Called via `az find offline enable`. Used to enable the use of offline models.'''
    config = cmd.cli_ctx.config

    print(MESSAGE_OFFLINE_ENABLE)
    config.set_value(CONFIG_HEADER, CONFIG_SHOULD_DOWNLOAD_ARTIFACT, CONFIG_ENABLE_VALUE)


def disable_offline_model(cmd):
    '''Called via `az find offline disable`. Used to disable the use of offline models.'''
    config = cmd.cli_ctx.config

    print(MESSAGE_OFFLINE_DISABLE)
    config.set_value(CONFIG_HEADER, CONFIG_SHOULD_DOWNLOAD_ARTIFACT, CONFIG_DISABLE_VALUE)


def _print_examples(cli_term, call_successful, pruned_examples, examples):
    print(MESSAGE_WAIT, file=sys.stderr)

    if call_successful:
        if (platform.system() == 'Windows' and should_enable_styling()):
            colorama.init(convert=True)

        if not examples:
            print('\n' + MESSAGE_PRINT_NO_EXAMPLES.format(cli_term) + '\n' + MESSAGE_PRINT_CALL_SUGGESTION.format(style_message('az vm')), file=sys.stderr)  # pylint: disable=line-too-long
        else:
            print('\n' + MESSAGE_PRINT_USAGE_TITLE.format(cli_term) + '\n', file=sys.stderr)
            for example in examples:
                print(style_message(example.title))
                print(example.snippet + '\n')
            if pruned_examples:
                print(style_message(MESSAGE_PRINT_PRUNED_EXAMPLE + '\n'))
    else:
        logger.error(MESSAGE_PRINT_UNEXPECTED_ERROR)


def _offline_config_prompt(config, model_directory, cli_version, yes_flag):
    yes_input = False
    if not yes_flag:
        user_input = input(PROMPT_DOWNLOAD_MODEL)
        yes_input = user_input.lower() == 'y' or user_input.lower() == 'yes'
    if yes_flag or yes_input:
        print(MESSAGE_MODEL_DOWNLOAD_START)
        download_success = _update_model_if_available(model_directory, cli_version)
        if download_success:
            config.set_value(CONFIG_HEADER, CONFIG_SHOULD_DOWNLOAD_ARTIFACT, CONFIG_ENABLE_VALUE)
            _set_last_checked_date_confg(config)
            print(MESSAGE_MODEL_DOWNLOAD_END)
        else:
            print(MESSAGE_MODEL_DOWNLOAD_ERROR)
    else:
        config.set_value(CONFIG_HEADER, CONFIG_SHOULD_DOWNLOAD_ARTIFACT, CONFIG_DISABLE_VALUE)


def _search_example_model_and_clean(active_model_path, cli_term, cli_version, model_directory):
    # Whenever the model is used, check to see if there are old ones to be cleaned up
    (call_successful, pruned_examples, examples) = search_examples(active_model_path, cli_term, cli_version, False)
    _clean_up_old_models(model_directory, EXAMPLE_MODEL_NAME_PATTERN, active_model_path)
    return (call_successful, pruned_examples, examples)


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
    return download_artifact(model_directory, EXAMPLE_MODEL_NAME_PATTERN, version_to_download, ACR_NAME, ARTIFACT_PATH, ARTIFACT_TYPE)  # pylint: disable=line-too-long


def _clean_up_old_models(model_directory, model_name_pattern, last_used_model_path):
    models_to_delete = what_model_files_to_delete(model_directory, model_name_pattern, last_used_model_path)
    delete_model_files(models_to_delete)


def _get_last_checked_date_confg(config):
    if config.has_option(CONFIG_HEADER, CONFIG_LAST_CHECKED_DATE):
        return datetime.datetime.strptime(config.get(CONFIG_HEADER, CONFIG_LAST_CHECKED_DATE), '%x')
    return datetime.datetime.min


def _set_last_checked_date_confg(config, current_date=datetime.datetime.now()):
    config.set_value(CONFIG_HEADER, CONFIG_LAST_CHECKED_DATE, current_date.strftime('%x'))


def _time_to_check_for_new_model(last_checked_date, current_date=datetime.datetime.now()):
    return (current_date - last_checked_date) > datetime.timedelta(days=3)
