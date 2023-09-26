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

"""Execution module."""

import base64
from typing import Any, Union

from pysui_flask.db_tables import (
    db,
    User,
    MultiSignature,
    SigningAs,
    SignerStatus,
    SignatureStatus,
    SignatureRequest,
    SignatureTrack,
)
import pysui_flask.api.common as cmn
from pysui_flask.api.xchange.payload import SigningResponse

from pysui import SyncClient, SuiRpcResult
from pysui.sui.sui_builders.base_builder import SuiRequestType
from pysui.sui.sui_builders.exec_builders import ExecuteTransaction
from pysui.sui.sui_types import SuiSignature
from pysui.sui.sui_crypto import BaseMultiSig, SuiPublicKey


def _gather_msig_signature(
    *, track: SignatureTrack, msig_acct: MultiSignature
) -> str:
    """."""
    # Get member sigs
    member_sigs = [SuiSignature(req.signature) for req in track.requests]
    # Build a crypto BaseMultiSig from db
    base_msig = cmn.construct_multisig(msig_acct)
    sig_pkeys: list[SuiPublicKey] = []
    for sig_req in track.requests:
        pkb = base64.b64decode(sig_req.signer_public_key)
        for bpkey in base_msig.public_keys:
            if bpkey.key_bytes == pkb[1:]:
                sig_pkeys.append(bpkey)
                break
    if len(sig_pkeys) != len(track.requests):
        raise ValueError("Msig member mismatch")

    signature = base_msig.signature_from(sig_pkeys, member_sigs)
    return signature.value


def _gather_address_and_signatures(
    *, track: SignatureTrack
) -> tuple[User, list[str]]:
    """."""
    # With sender we also want the SuiClient specific
    # to their account and configuration
    client, sender = cmn.client_for_account_action(
        track.explicit_sender or track.requestor
    )
    # Signature list
    sigs: list[str] = []
    # If sender not multi-sig than sig is in the track list
    if sender.user_role == UserRole.user:
        for regs in track.requests:
            if regs.signing_as == SigningAs.tx_sender:
                sigs.append(regs.signature)
    # Else multisig
    elif sender.user_role == UserRole.multisig:
        sigs.append(
            _gather_msig_signature(
                track=track, msig_acct=sender.multisig_configuration
            )
        )

    # If sponsor identified
    if track.explicit_sponsor:
        sponsor = User.query.filter(
            User.account_key == track.explicit_sponsor
        ).one()
        if sponsor.user_role == UserRole.user:
            for regs in track.requests:
                if regs.signing_as == SigningAs.tx_sponsor:
                    sigs.append(regs.signature)
        # Else multisig
        elif sponsor.user_role == UserRole.multisig:
            sigs.append(
                _gather_msig_signature(
                    track=track, msig_acct=sponsor.multisig_configuration
                )
            )

    return client, sender, sigs


def _process_tracker(
    *, track: SignatureTrack, requested: SigningResponse
) -> str:
    """."""
    # Ready to execution
    if track.status == SignatureStatus.signed:
        tx_bytes: str = track.tx_bytes
        # Gather signatures and sender address
        pysui_client, sender, signatures = _gather_address_and_signatures(
            track=track
        )

        result = pysui_client.execute(
            ExecuteTransaction(
                tx_bytes=tx_bytes,
                signatures=signatures,
                request_type=SuiRequestType.WAITFORLOCALEXECUTION,
            )
        )
        # Populate transaction data
        if result.is_ok():
            track.transaction_passed = True
            track.transaction_response = result.result_data.to_json()
        else:
            track.transaction_passed = False
            track.transaction_response = result.result_string
        track.status = SignatureStatus.signed_and_executed
        db.session.commit()
    # Ready to shutdown
    elif track.status == SignatureStatus.denied:
        track.transaction_passed = False
        track.transaction_response = "Signing denied."
        db.session.commit()
    # Still waiting for signatures
    else:
        pass
    return track.status.name


def _update_tracker(
    *, session_key: str, sig_req: SignatureRequest
) -> SignatureTrack:
    """."""
    track: SignatureTrack = sig_req.signature_track
    # If already denied, signed or signed and executed... quick exit
    if (
        track.status != SignatureStatus.denied
        and track.status != SignatureStatus.signed
        and track.status != SignatureStatus.signed_and_executed
    ):
        rlen = len(track.requests)
        # If the rlen is 1 then what we are receiving is it
        # A single only indicates a non-multisig signer which may likely be
        # the requestor
        if rlen == 1:
            if sig_req.status == SignerStatus.denied:
                track.status = SignatureStatus.denied
            # All signed, ready to execute
            elif sig_req.status == SignerStatus.signed:
                track.status = SignatureStatus.signed
        else:
            scount: int = 0
            dcount: int = 0
            # Tally
            for areq in track.requests:
                # if areq.status == SignatureStatus.signed:
                #     scount += 1
                scount += 1 if areq.status == SignerStatus.signed else 0
                dcount += 1 if areq.status == SignerStatus.denied else 0
            # All denied, set and return
            if dcount == rlen:
                track.status = SignatureStatus.denied
            # All signed, execute and return
            elif scount == rlen:
                track.status = SignatureStatus.signed
            # Otherwise, more to come
            else:
                track.status = SignatureStatus.partially_completed
        db.session.commit()
    return track


def _update_signatures(
    *, session_key: str, sig_req: SignatureRequest, sig_resp: SigningResponse
) -> SignatureTrack:
    """Handles state change on signature.

    Walks up to tracker and sets status accordingly

    :param session_key: The account key of user session
    :type session_key: str
    :param siq_req: The signing request row
    :type siq_req: SignatureRequest
    :return: Some result
    :rtype: Any
    """
    # Set the request state and commit
    sig_req.status = (
        SignerStatus.signed if sig_resp.approved else SignerStatus.denied
    )
    if sig_req.status == SignerStatus.signed:
        # TODO: Validate other attributes of signature?
        sig_req.signature = sig_resp.accepted_outcome.signature
    db.session.commit()
    return _update_tracker(session_key=session_key, sig_req=sig_req)


def signature_update(
    *, session_key: str, sig_resp: SigningResponse
) -> SignatureStatus:
    """."""
    sign_request: SignatureRequest = SignatureRequest.query.filter(
        SignatureRequest.id == sig_resp.request_id
    ).one()
    # Confirm that the user session aligns with signing response
    if sign_request.signer_account_key == session_key:
        # user: User = User.query.filter(
        #     User.account_key == session["user_key"]
        # ).first()
        tracker = _update_signatures(
            session_key=session_key,
            sig_req=sign_request,
            sig_resp=sig_resp,
        )

        result = _process_tracker(track=tracker, requested=sig_resp)
    # TODO: If key's aren't matching exception
    else:
        result = SignatureStatus.partially_completed
    return result
