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
    else:
        # Check if an old version of the file exists
        glob_path = os.path.join(file_path, file_name_pattern.format('*'))
        matches = glob.glob(glob_path)
        matches = natural_sort(matches)
        if matches and os.path.isfile(matches[-1]):
            return matches[-1]
        else:
            return ""

# Consider using an incremental JSON loading library for searching through the model https://pypi.org/project/ijson/


def natural_sort(l): 
    convert = lambda text: int(text) if text.isdigit() else text.lower() 
    alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)]
    return sorted(l, key=alphanum_key)
