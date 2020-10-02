# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------
from __future__ import print_function

import os.path
import httpx
# TODO: See if a newer version of the request library gets this to work

_ACR_BLOB_URL = 'https://{}.azurecr.io/v2/public/{}/blobs/{}'
_ACR_MANIFEST_URL = 'https://{}.azurecr.io/v2/public/{}/manifests/{}'
_ACR_TOKEN_URL = '{}?service={}&scope={}'
_ACR_ACCEPT_ENCODING_HEADER = 'gzip'
_ACR_AUTHORIZATION_HEADER = 'Bearer {}'
_ACR_HOST_HEADER = '{}.azurecr.io'

_ACCEPT = 'Accept'
_ACCEPT_ENCODING = 'Accept-Encoding'
_APPLICATION_JSON = 'application/json'
_AUTHORIZATION = 'Authorization'
_CONTENT_TYPE = 'Content-Type'
_HOST = 'Host'
_TOKEN_DEFAULT = 'default'


def download_artifact(model_directory, model_name_pattern, artifact_version, acr_name, artifact_path, artifact_type):
    '''Download an artifact from an ACR. Return True if successful.'''
    try:
        (ping_response_auth, bearer_token) = _get_artifact_status(acr_name, artifact_path, artifact_version)
        if ping_response_auth.status_code != 200:
            return False
        manifest_sha = _extract_manifest_sha(ping_response_auth)
        manifest_response = _get_manifest(acr_name, artifact_path, manifest_sha, bearer_token)
        artifact_sha = _extract_artifact_sha(manifest_response)
        _download_file(model_directory, model_name_pattern.format(artifact_version), acr_name, artifact_path, artifact_sha, artifact_type, bearer_token)  # pylint: disable=line-too-long
        return True
    except httpx.RequestError as exc:
        # TODO: Add some sort of logging and consider checking for other failures and exceptions
        print("Aladdin download failed {}".format(exc))
        return False


def does_current_cli_artifact_exist(acr_name, artifact_path, artifact_version):
    '''Check if an artifact exists in an ACR. True if successful.'''
    try:
        (ping_response_auth, _) = _get_artifact_status(acr_name, artifact_path, artifact_version)
        if ping_response_auth.status_code == 200:
            return True
    except httpx.RequestError:
        pass
    return False


def _get_artifact_status(acr_name, artifact_path, artifact_version):
    # Follows the Docker authentication specification https://docs.docker.com/registry/spec/auth/token/
    ping_response = _ping_acr(acr_name, artifact_path, artifact_version)
    (realm, service, scope) = _extract_auth_values(ping_response)
    auth_response = _get_auth_token(realm, service, scope)
    bearer_token = _extract_auth_token(auth_response)
    ping_response_auth = _ping_acr(acr_name, artifact_path, artifact_version, bearer_token)
    return (ping_response_auth, bearer_token)


def _ping_acr(acr_name, artifact_path, artifact_version, acr_token=_TOKEN_DEFAULT):
    api_url = _ACR_MANIFEST_URL.format(acr_name, artifact_path, artifact_version)
    headers = {
        _ACCEPT: 'application/vnd.docker.distribution.manifest.v2+json, application/vnd.docker.distribution.manifest.list.v2+json, application/vnd.oci.image.manifest.v1+json, application/vnd.oci.image.index.v1+json, */*',  # pylint: disable=line-too-long
        _ACCEPT_ENCODING: _ACR_ACCEPT_ENCODING_HEADER,
        _HOST: _ACR_HOST_HEADER.format(acr_name),
        _AUTHORIZATION: _ACR_AUTHORIZATION_HEADER.format(acr_token)
    }
    return httpx.head(api_url, headers=headers)


def _get_auth_token(realm, service, scope):
    api_url = _ACR_TOKEN_URL.format(realm, service, scope)
    headers = {
        _ACCEPT_ENCODING: _ACR_ACCEPT_ENCODING_HEADER
    }
    return httpx.get(api_url, headers=headers)


def _get_manifest(acr_name, artifact_path, manifest_sha, acr_token=_TOKEN_DEFAULT):
    api_url = _ACR_MANIFEST_URL.format(acr_name, artifact_path, manifest_sha)
    headers = {
        _ACCEPT: 'application/vnd.oci.image.manifest.v1+json, */*',
        _ACCEPT_ENCODING: _ACR_ACCEPT_ENCODING_HEADER,
        _HOST: _ACR_HOST_HEADER.format(acr_name),
        _AUTHORIZATION: _ACR_AUTHORIZATION_HEADER.format(acr_token)
    }
    return httpx.get(api_url, headers=headers)


def _get_artifact(acr_name, artifact_path, artifact_sha, artifact_type, acr_token=_TOKEN_DEFAULT):
    api_url = _ACR_BLOB_URL.format(acr_name, artifact_path, artifact_sha)
    headers = {
        _ACCEPT: '{}, */*'.format(artifact_type),
        _ACCEPT_ENCODING: _ACR_ACCEPT_ENCODING_HEADER,
        _CONTENT_TYPE: _APPLICATION_JSON,
        _HOST: _ACR_HOST_HEADER.format(acr_name),
        _AUTHORIZATION: _ACR_AUTHORIZATION_HEADER.format(acr_token)
    }
    return httpx.get(api_url, headers=headers)


def _download_file(model_directory, model_name, acr_name, artifact_path, artifact_sha, artifact_type, acr_token=_TOKEN_DEFAULT):  # pylint: disable=line-too-long
    api_url = _ACR_BLOB_URL.format(acr_name, artifact_path, artifact_sha)
    headers = {
        _ACCEPT: '{}, */*'.format(artifact_type),
        _ACCEPT_ENCODING: _ACR_ACCEPT_ENCODING_HEADER,
        _CONTENT_TYPE: _APPLICATION_JSON,
        _HOST: _ACR_HOST_HEADER.format(acr_name),
        _AUTHORIZATION: _ACR_AUTHORIZATION_HEADER.format(acr_token)
    }

    if not os.path.exists(model_directory):
        os.makedirs(model_directory)
    full_path = os.path.join(model_directory, model_name)

    with httpx.stream("GET", api_url, headers=headers) as r:
        r.raise_for_status()
        with open(full_path, 'wb') as f:
            for chunk in r.iter_bytes():
                f.write(chunk)


def _extract_auth_values(response):
    auth_info = response.headers.get('Www-Authenticate').split('"')
    realm = auth_info[1]
    service = auth_info[3]
    scope = auth_info[5]
    return (realm, service, scope)


def _extract_auth_token(response):
    return response.json()['access_token']


def _extract_manifest_sha(response):
    return response.headers.get('Docker-Content-Digest')


def _extract_artifact_sha(response):
    return response.json()['layers'][0]['digest']
