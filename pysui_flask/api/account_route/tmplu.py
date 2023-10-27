#    Copyright Frank V. Castellucci
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#        http://www.apache.org/licenses/LICENSE-2.0
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

# -*- coding: utf-8 -*-

"""Template execution utilities module."""

from pysui_flask.api.xchange.payload import *
from pysui_flask.db_tables import (
    db,
    User,
    Template,
    TemplateOverride,
    TemplateVisibility,
)


def _resolve_ovverides(loadin: ExecuteTemplate, template: Template) -> TransactionIn:
    """Resolves overrides if any, in payload.

    :param loadin: The payload
    :type loadin: ExecuteTemplate
    :param template: The template
    :type template: Template
    :return: Data structure used in submitting transaction
    :rtype: TransactionIn
    """
    txbytes: str = template.serialized_builder
    # If input contains override declarations, otherwise just
    # transpose to Transaction In
    if loadin.input_overrides:
        if template.template_overrides:
            # Get the set of template overrides
            # Get the set of input overrides
            # Ensure the latter is subset of former
            # Check the 'types' in the override are equal
            pass
        else:
            # FIXME: Do we fail or just ignore?
            pass
    return TransactionIn(
        txbytes, loadin.verify, loadin.gas_budget, loadin.gas_object, loadin.signers
    )


def template_payload_to_tx(
    account: str, loadin: ExecuteTemplate, template: Template
) -> TransactionIn:
    """."""
    # Get the template owner
    user: User = template.user
    if (
        user.account_key == account
        or template.template_visibility == TemplateVisibility.shared
    ):
        # Process overrides if any
        return _resolve_ovverides(loadin, template)
    elif template.template_visibility != TemplateVisibility.shared:
        # Fail with sharing violation
        pass
