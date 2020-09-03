# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------
import json
import requests

from azure.cli.core import telemetry as telemetry_core
from azure.cli.core import __version__ as core_version
from pkg_resources import parse_version

API_URL = 'https://app.aladdin.microsoft.com/api/{}/{}'
API_VERSION = 'v1.0'
HEADERS = {'Content-Type': 'application/json'}

def get_context():
    version = str(parse_version(core_version))
    correlation_id = telemetry_core._session.correlation_id   # pylint: disable=protected-access
    subscription_id = telemetry_core._get_azure_subscription_id()  # pylint: disable=protected-access
    user_id = telemetry_core._get_user_azure_id()  # pylint: disable=protected-access

    context = {
        "versionNumber": version,
        "userId": user_id
    }

    # Only pull in the contextual values if we have consent
    if telemetry_core.is_telemetry_enabled():
        context['correlationId'] = correlation_id

    if telemetry_core.is_telemetry_enabled() and subscription_id is not None:
        context['subscriptionId'] = subscription_id

    return context


def call_aladdin_service(version, endpoint, additonal_params={}): # pylint: disable=dangerous-default-value
    context = get_context()
    api_url = API_URL.format(version, endpoint)
    standard_params = {
        'clientType': 'AzureCli',
        'context': json.dumps(context)
    }
    params = {**standard_params, **additonal_params}

    response = requests.get(
        api_url,
        params=params,
        headers=HEADERS)

    return response


def ping_aladdin_service():
    return call_aladdin_service(API_VERSION, 'monitor')
