# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------
from __future__ import print_function

import glob
import os.path
import re


def get_model_file(file_path, file_name_pattern, file_version):
    full_path = os.path.join(file_path, file_name_pattern.format(file_version))
    if os.path.isfile(full_path):
        return full_path

    # Check if an old version of the file exists
    glob_path = os.path.join(file_path, file_name_pattern.format('*'))
    matches = glob.glob(glob_path)
    matches = natural_sort(matches)
    if matches and os.path.isfile(matches[-1]):
        return matches[-1]
    return ""


def delete_model_files(files_to_delete):
    for files in files_to_delete:
        if os.path.isfile(files):
            os.remove(files)


def what_model_files_to_delete(file_path, file_name_pattern, last_used_file_full_path):
    files_to_delete = []
    glob_path = os.path.join(file_path, file_name_pattern.format('*'))
    matches = glob.glob(glob_path)
    matches = natural_sort(matches)
    for match in matches:
        if os.path.isfile(match) and match != last_used_file_full_path:
            files_to_delete.append(match)
    return files_to_delete


def natural_sort(list_to_sort):
    convert = lambda text: int(text) if text.isdigit() else text.lower()
    alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)]
    return sorted(list_to_sort, key=alphanum_key)
