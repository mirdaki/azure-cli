# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------
from __future__ import print_function

import os.path
import httpx

ACR_MANIFEST_URL = 'https://{}.azurecr.io/v2/public/{}/manifests/{}'
ACR_TOKEN_URL = '{}?service={}&scope={}'
ACR_BLOB_URL = 'https://{}.azurecr.io/v2/public/{}/blobs/{}'

ACR_HOST_HEADER = '{}.azurecr.io'
ACR_ACCEPT_ENCODING_HEADER = 'gzip'
ACR_AUTHORIZATION_HEADER = 'Bearer {}'


def ping_acr(acr_name, artifact_path, artifact_version, acr_token='default'):
    api_url = ACR_MANIFEST_URL.format(acr_name, artifact_path, artifact_version)
    headers = {
        'Accept': 'application/vnd.docker.distribution.manifest.v2+json, application/vnd.docker.distribution.manifest.list.v2+json, application/vnd.oci.image.manifest.v1+json, application/vnd.oci.image.index.v1+json, */*',  # pylint: disable=line-too-long
        'Accept-Encoding': ACR_ACCEPT_ENCODING_HEADER,
        'Host': ACR_HOST_HEADER.format(acr_name),
        'Authorization': ACR_AUTHORIZATION_HEADER.format(acr_token)
    }
    return httpx.head(api_url, headers=headers)


def get_auth_token(realm, service, scope):
    api_url = ACR_TOKEN_URL.format(realm, service, scope)
    headers = {
        'Accept-Encoding': ACR_ACCEPT_ENCODING_HEADER
    }
    return httpx.get(api_url, headers=headers)


def get_manifest(acr_name, artifact_path, manifest_sha, acr_token='default'):
    api_url = ACR_MANIFEST_URL.format(acr_name, artifact_path, manifest_sha)
    headers = {
        'Accept': 'application/vnd.oci.image.manifest.v1+json, */*',
        'Accept-Encoding': ACR_ACCEPT_ENCODING_HEADER,
        'Host': ACR_HOST_HEADER.format(acr_name),
        'Authorization': ACR_AUTHORIZATION_HEADER.format(acr_token)
    }
    return httpx.get(api_url, headers=headers)


def get_artifact(acr_name, artifact_path, artifact_sha, artifact_type, acr_token='default'):
    api_url = ACR_BLOB_URL.format(acr_name, artifact_path, artifact_sha)
    headers = {
        'Accept': '{}, */*'.format(artifact_type),
        'Accept-Encoding': ACR_ACCEPT_ENCODING_HEADER,
        'Content-Type': 'application/json',
        'Host': ACR_HOST_HEADER.format(acr_name),
        'Authorization': ACR_AUTHORIZATION_HEADER.format(acr_token)
    }
    return httpx.get(api_url, headers=headers)


def download_file(file_path, file_name, acr_name, artifact_path, artifact_sha, artifact_type, acr_token='default'):
    api_url = ACR_BLOB_URL.format(acr_name, artifact_path, artifact_sha)
    headers = {
        'Accept': '{}, */*'.format(artifact_type),
        'Accept-Encoding': ACR_ACCEPT_ENCODING_HEADER,
        'Content-Type': 'application/json',
        'Host': ACR_HOST_HEADER.format(acr_name),
        'Authorization': ACR_AUTHORIZATION_HEADER.format(acr_token)
    }

    if not os.path.exists(file_path):
        os.makedirs(file_path)
    full_path = os.path.join(file_path, file_name)

    with httpx.stream("GET", api_url, headers=headers) as r:
        r.raise_for_status()
        with open(full_path, 'wb') as f:
            for chunk in r.iter_bytes():
                f.write(chunk)


def extract_auth_values(response):
    auth_info = response.headers.get('Www-Authenticate').split('"')
    realm = auth_info[1]
    service = auth_info[3]
    scope = auth_info[5]
    return (realm, service, scope)


def extract_auth_token(response):
    return response.json()['access_token']


def extract_manifest_sha(response):
    return response.headers.get('Docker-Content-Digest')


def extract_artifact_sha(response):
    return response.json()['layers'][0]['digest']


# Return true if successful, false otherwise
def download_artifact(file_path, file_name, acr_name, artifact_path, artifact_version, artifact_type):
    try:
        ping_response = ping_acr(acr_name, artifact_path, artifact_version)
        (realm, service, scope) = extract_auth_values(ping_response)
        auth_response = get_auth_token(realm, service, scope)
        bearer_token = extract_auth_token(auth_response)
        ping_response_auth = ping_acr(acr_name, artifact_path, artifact_version, bearer_token)
        if ping_response_auth.status_code != 200:
            return False
        manifest_sha = extract_manifest_sha(ping_response_auth)
        manifest_response = get_manifest(acr_name, artifact_path, manifest_sha, bearer_token)
        artifact_sha = extract_artifact_sha(manifest_response)
        download_file(file_path, file_name, acr_name, artifact_path, artifact_sha, artifact_type, bearer_token)
        return True
    except httpx.RequestError as exc:
        # TODO: Add some sort of logging and consider checking for other failures and exceptions
        print("Aladdin download failed {}".format(exc))
        return False


def does_current_cli_artifact_exist(acr_name, artifact_path, artifact_version):
    try:
        ping_response = ping_acr(acr_name, artifact_path, artifact_version)
        (realm, service, scope) = extract_auth_values(ping_response)
        auth_response = get_auth_token(realm, service, scope)
        bearer_token = extract_auth_token(auth_response)
        ping_response_auth = ping_acr(acr_name, artifact_path, artifact_version, bearer_token)
        if ping_response_auth.status_code == 200:
            return True
    except httpx.RequestError:
        # TODO: Add some sort of logging and consider checking for other failures and exceptions
        pass
    return False
