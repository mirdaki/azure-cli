# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

ACR_NAME = (
    'aladdinmodel'
)
ARTIFACT_PATH = (
    'aladdin/cli'
)
ARTIFACT_TYPE = (
    'application/vnd.microsoft.aladdin-model.cli.layer.v1.json'
)
ARTIFACT_FILE_NAME = (
    'aladdinExamplesModel{}.json'
)
ARTIFACT_FORMAT_VERSION = (
    'v1.1'
)

CONFIG_HEADER = (
    'aladdin'
)
CONFIG_SHOULD_DOWNLOAD_ARTIFACT = (
    'should_download_artifact'
)
CONFIG_ENABLE_VALUE = (
    'true'
)
CONFIG_DISABLE_VALUE = (
    'false'
)

EXTENSION_NAME = (
    'find'
)

MESSAGE_OFFLINE_MODEL = (
    'A model can be downloaded for faster results from the `az find` command.'
)
MESSAGE_AIR_GAPPED_MODEL = (
    'A model needs to be downloaded for this command to function.'
)
MESSAGE_MODEL_DOWNLOAD_START = (
    'Downloading, this may take a movement.'
)
MESSAGE_MODEL_DOWNLOAD_END = (
    'Model successfully downloaded.'
)
MESSAGE_MODEL_DOWNLOAD_ERROR = (
    'Something went wrong. Please try again later. Please report the problem if it persist.'
)
MESSAGE_CHANGE_MODEL_DOWNLOAD_CONFIG = (
    '\nTo change the model download setting, go to the config file at "{}" and change "{}" under "{}".'
)
MESSAGE_WAIT = (
    'Finding examples...'
)

PROMPT_DOWNLOAD_MODEL = (
    'Would you like to enable this behavior (option can be changed in the config file) (y/n): '
)
