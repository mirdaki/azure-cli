# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------
from azure.cli.core.commands.parameters import get_three_state_flag


def load_arguments(self, _):
    with self.argument_context('find') as c:
        c.positional('cli_term', help='An Azure CLI command or group for which you need an example.')
        c.argument('yes', help='Agree to enable downloading the artifact for local searches.', arg_type=get_three_state_flag())  # pylint: disable=line-too-long
