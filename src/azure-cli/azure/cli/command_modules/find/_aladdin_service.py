# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------
import hashlib
import json
import requests

from pkg_resources import parse_version
from requests import Response
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from azure.cli.core import telemetry as telemetry_core
from azure.cli.core import __version__ as core_version

API_URL = 'https://app.aladdin.microsoft.com/api/{}/{}'
API_VERSION = 'v1.0'


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


def get_headers():
    headers = {'Content-Type': 'application/json'}

    # Used for DDOS protection and rate limiting
    user_id = telemetry_core._get_user_azure_id()  # pylint: disable=protected-access
    hashed_user_id = hashlib.sha256(user_id.encode('utf-8')).hexdigest()
    headers['X-UserId'] = hashed_user_id

    return headers


def call_aladdin_service(endpoint, additonal_params={}, version=API_VERSION, retry_count=3, timeout_seconds=360):  # pylint: disable=dangerous-default-value

    context = get_context()
    api_url = API_URL.format(version, endpoint)
    standard_params = {
        'clientType': 'AzureCli',
        'context': json.dumps(context)
    }
    params = {**standard_params, **additonal_params}

    headers = get_headers()

    retry_strategy = Retry(
        total=retry_count,
        status_forcelist=[429, 500, 502, 503, 504],
        backoff_factor=1
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    http = requests.Session()
    http.mount("https://", adapter)
    http.mount("http://", adapter)

    try:
        response = http.get(
            api_url,
            params=params,
            headers=headers,
            timeout=timeout_seconds)
    except:  # pylint: disable=bare-except
        response = Response()
        response.status_code = 503

    return response


def ping_aladdin_service():
    return call_aladdin_service('monitor')
