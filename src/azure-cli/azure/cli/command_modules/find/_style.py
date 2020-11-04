# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------
import sys


def style_message(msg):
    if should_enable_styling():
        import colorama  # pylint: disable=import-error

        try:
            msg = colorama.Style.BRIGHT + msg + colorama.Style.RESET_ALL
        except KeyError:
            pass
    return msg


def should_enable_styling():
    try:
        if sys.stdout.isatty():
            return True
    except AttributeError:
        pass
    return False