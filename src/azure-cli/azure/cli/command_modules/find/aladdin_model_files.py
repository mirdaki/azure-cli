# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------
from __future__ import print_function

import glob
import os.path
import re


def get_model_file(model_directory, model_name_pattern, version):
    '''Get the most accurate model file based on the passed version.'''
    glob_path = os.path.join(model_directory, model_name_pattern.format(version))
    matches = glob.glob(glob_path)
    matches = _natural_sort(matches)
    if matches and os.path.isfile(matches[-1]):
        return matches[-1]
    return ''


def delete_model_files(models_to_delete):
    '''Delete the specified model files.'''
    for model in models_to_delete:
        if os.path.isfile(model):
            os.remove(model)


def what_model_files_to_delete(model_directory, model_name_pattern, last_used_model_path):
    '''Get a list of models that have not been used.'''
    files_to_delete = []
    glob_path = os.path.join(model_directory, model_name_pattern.format('*'))
    matches = glob.glob(glob_path)
    matches = _natural_sort(matches)
    for match in matches:
        if os.path.isfile(match) and match != last_used_model_path:
            files_to_delete.append(match)
    return files_to_delete


def _natural_sort(list_to_sort):
    convert = lambda text: int(text) if text.isdigit() else text.lower()
    alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)]
    return sorted(list_to_sort, key=alphanum_key)
