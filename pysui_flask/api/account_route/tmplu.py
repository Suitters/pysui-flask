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

import base64
from pysui_flask.api.xchange.payload import *
from pysui_flask.db_tables import (
    User,
    Template,
    TemplateVisibility,
)
from pysui_flask.api_error import ErrorCodes, APIError
import pysui_flask.api.common as cmn

from pysui import ObjectID
from pysui.sui.sui_txn import SyncTransaction
from pysui.sui.sui_txn.transaction_builder import ProgrammableTransactionBuilder
from pysui.sui.sui_types import bcs
from pysui.sui.sui_txresults.single_tx import (
    AddressOwner,
    ImmutableOwner,
    SharedOwner,
    ObjectRead,
)


def _resolve_object(in_obj: ObjectRead, expected: str) -> bcs.CallArg:
    """."""
    if isinstance(in_obj.owner, (AddressOwner, ImmutableOwner)):
        if expected not in ["ImmOrOwnedObject", "Receiving"]:
            raise APIError(
                f"Expected ImmOrOwnedObject or Receiving object type got {expected}",
                ErrorCodes.PAYLOAD_ERROR,
            )
        obj_ref = bcs.GenericRef(in_obj.object_id, in_obj.version, in_obj.digest)
        b_obj_arg = bcs.ObjectArg(
            expected,
            bcs.ObjectReference.from_generic_ref(obj_ref),
        )
    elif isinstance(in_obj.owner, SharedOwner):
        if expected not in ["SharedObject"]:
            raise APIError(
                f"Expected SharedObject type got {expected}",
                ErrorCodes.PAYLOAD_ERROR,
            )
        b_obj_arg = bcs.ObjectArg(
            "SharedObject",
            bcs.SharedObjectReference.from_object_read(in_obj),
        )
    return bcs.CallArg("Object", b_obj_arg)


def _set_ovverides(txbytes: str, user: User, ovr: list[ExecuteTemplateOverride]) -> str:
    """."""
    client, usr = cmn.client_for_account("", user)
    txer: SyncTransaction = cmn.deser_transaction(client, txbytes)
    builder: ProgrammableTransactionBuilder = txer.builder
    k_list = list(builder.inputs.keys())
    for ovr_val in ovr:
        karg = k_list[ovr_val.input_index]

        match karg.enum_name:
            case "Pure":
                karg.value = ovr_val.input_value
            case "Object":
                carg: bcs.CallArg = builder.inputs[karg]

                result = client.get_object(ObjectID(ovr_val.input_value))
                if result.is_err():
                    raise APIError(result.result_string, ErrorCodes.PYSUI_ERROR_BASE)
                # obj_carg = _resolve_object(result.result_data, carg.value.enum_name)
                # builder.inputs[karg] = obj_carg
                # Preserve old object id
                old_addy = karg.value.to_address_str()
                # Replace with new object id
                karg.value = bcs.Address.from_sui_address(
                    SuiAddress(result.result_data.object_id)
                )
                # Pop old object id from registry
                old_entry = builder.objects_registry.pop(old_addy)
                # Create new registry entry
                builder.objects_registry[
                    result.result_data.object_id
                ] = carg.value.enum_name

    return base64.b64encode(txer.serialize(False)).decode()


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

    # Decl overrides
    all_ovr: set = set([ovr.input_index for ovr in template.overrides])
    # Required decl overrides
    req_ovr: set = set(
        [ovr.input_index for ovr in template.overrides if ovr.input_required]
    )
    # Input override
    inp_ovr: set = set([x.input_index for x in loadin.input_overrides])
    # If required but not provided
    if req_ovr and not (req_ovr <= inp_ovr):
        raise APIError(
            f"Missing overrides for indexes {req_ovr - inp_ovr}",
            ErrorCodes.PYSUI_TEMPLATE_MISSING_REQUIRED_OVERRIDES,
        )
    # If what is provided is not subset
    if inp_ovr and not (inp_ovr <= all_ovr):
        raise APIError(
            f"Invalid input overrides {inp_ovr-all_ovr}",
            ErrorCodes.PYSUI_TEMPLATE_INVALID_OVERRIDES,
        )
    # If you got em, smoke em
    if inp_ovr:
        txbytes = _set_ovverides(txbytes, template.user, loadin.input_overrides)

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
