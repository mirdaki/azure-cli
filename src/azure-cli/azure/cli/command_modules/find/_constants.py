# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------
ACR_LATEST_TAG = 'latest'
ACR_NAME = 'aladdinmodel'
ARTIFACT_PATH = 'aladdin/cli'
ARTIFACT_TYPE = 'application/vnd.microsoft.aladdin-model.cli.layer.v1.json'
EXAMPLE_MODEL_NAME_PATTERN = 'aladdinExamplesModel{}.json'
MODEL_FOLDER_NAME = 'aladdin'
CLI_VERSION_FORMAT = 'v{}'

CONFIG_DISABLE_VALUE = 'False'
CONFIG_ENABLE_VALUE = 'True'
CONFIG_HEADER = 'aladdin'
CONFIG_LAST_CHECKED_DATE = 'last_checked_date'
CONFIG_SHOULD_DOWNLOAD_ARTIFACT = 'should_download_artifact'

MESSAGE_PRINT_CALL_SUGGESTION = 'Try typing the beginning of a command e.g. {}."'
MESSAGE_PRINT_NO_EXAMPLES = 'Sorry I am not able to help with [{}].'
MESSAGE_PRINT_PRUNED_EXAMPLE = 'More commands and examples are available in the latest version of the CLI. Please update for the best experience.'  # pylint: disable=line-too-long
MESSAGE_PRINT_UNEXPECTED_ERROR = 'Unexpected Error: If it persists, please file a bug.'
MESSAGE_PRINT_USAGE_TITLE = 'Here are the most common ways to use [{}]:'
MESSAGE_TERM_NOT_PROVIDED_ERROR = 'Please provide a search term e.g. az find "vm"'

MESSAGE_AIR_GAPPED_MODEL_NEEDED = 'A model needs to be downloaded for this command to function.'
MESSAGE_CHANGE_MODEL_DOWNLOAD_CONFIG = 'To change the model download setting, go to the config file at "{}" and change "{}" under "{}".'  # pylint: disable=line-too-long
MESSAGE_MODEL_DOWNLOAD_END = 'Model successfully downloaded.'
MESSAGE_MODEL_DOWNLOAD_ERROR = 'Something went wrong. Please try again later. Please report the problem if it persist.'
MESSAGE_MODEL_DOWNLOAD_START = 'Downloading, this may take a moment.'
MESSAGE_WAIT = 'Finding examples...'

MESSAGE_OFFLINE_UPDATE = 'Attempting to update to the latest available offline model.'
MESSAGE_OFFLINE_UPDATE_SUCCESS = 'Successfully updated.'
MESSAGE_OFFLINE_UPDATE_FAIL = 'Update failed.'
MESSAGE_OFFLINE_DELETE = 'Deleting all downloaded offline models.'
MESSAGE_OFFLINE_ENABLE = 'Enabling offline model. To download the latest model, use the `find offline update` command.'
MESSAGE_OFFLINE_DISABLE = 'Disabling offline model.'


PROMPT_DOWNLOAD_MODEL = 'Would you like to download a model for offline use (option can be changed in the config file) (y/n): '  # pylint: disable=line-too-long
