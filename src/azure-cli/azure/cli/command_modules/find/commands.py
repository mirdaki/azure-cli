# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------


def load_command_table(self, _):
    with self.command_group('') as g:
        g.custom_command('find', 'process_query', is_preview=False)

    with self.command_group('find offline', is_preview=True) as g:
        g.custom_command('update', 'update_offline_model')
        g.custom_command('delete', 'delete_offline_model')
        g.custom_command('enable', 'enable_offline_model')
        g.custom_command('disable', 'disable_offline_model')

    return self.command_table
