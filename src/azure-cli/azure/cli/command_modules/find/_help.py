# coding=utf-8
# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------
from knack.help_files import helps  # pylint: disable=unused-import
# pylint: disable=line-too-long, too-many-lines

helps['find'] = """
type: command
short-summary: I'm an AI robot, my advice is based on our Azure documentation as well as the usage patterns of Azure CLI and Azure ARM users. Using me improves Azure products and documentation.
examples:
  - name: Give me any Azure CLI group and I’ll show the most popular commands within the group.
    text: |
        az find "az storage"
  - name: Give me any Azure CLI command and I’ll show the most popular parameters and subcommands.
    text: |
        az find "az monitor activity-log list"
  - name: You can also enter a search term, and I'll try to help find the best commands.
    text: |
        az find "arm template"
"""

helps['find offline'] = """
type: group
short-summary: Manage the locally downloaded model for Azure CLI example suggestions.
examples:
  - name: Attempt to update to the latest available offline model.
    text: |
        az find offline update
  - name: Delete all downloaded offline models.
    text: |
        az find offline delete
  - name: Enabling using the offline model.
    text: |
        az find offline enable
  - name: Disable using the offline model.
    text: |
        az find offline disable
"""

helps['find offline update'] = """
type: command
short-summary: Update the locally downloaded model for Azure CLI example suggestions.
examples:
  - name: Attempt to update to the latest available offline model.
    text: |
        az find offline update
"""

helps['find offline delete'] = """
type: command
short-summary: Delete the locally downloaded models for Azure CLI example suggestions.
examples:
  - name: Delete all downloaded offline models.
    text: |
        az find offline delete
"""

helps['find offline enable'] = """
type: command
short-summary: Enable the use of locally downloaded models for Azure CLI example suggestions.
examples:
  - name: Enabling using the offline model.
    text: |
        az find offline enable
"""

helps['find offline disable'] = """
type: command
short-summary: Disable the locally downloaded models for Azure CLI example suggestions.
examples:
  - name: Disable using the offline model.
    text: |
        az find offline disable
"""
