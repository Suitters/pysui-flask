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

"""Payload misc mapping module."""

from dataclasses import dataclass, field
from typing import Optional, Union
from dataclasses_json import dataclass_json


@dataclass_json
@dataclass
class MultiSig:
    """Indicates a multisig account reference.

    Optional msig_signers identifies member subset
    """

    # This is the account_key for a MultiSignature base
    msig_account: str
    # Optionally these are account_keys for the msig members who are
    # required to sign. If None, all members must sign
    msig_signers: Optional[list[str]] = None


@dataclass_json
@dataclass
class Signers:
    """Signers identifier for a transaction.

    If both sender and sponsor are None, the requestor is only signer.
    """

    # Can be multi-sig, single account or None (default to requestor)
    sender: Optional[Union[MultiSig, str]] = None
    # Can be multi-sig, single account or None (default to requestor)
    sponsor: Optional[Union[MultiSig, str]] = None


@dataclass_json
@dataclass
class TransactionIn:
    """Posting Transaction payload."""

    # Serialized SuiTransaction (builder)
    tx_builder: str
    # Should transaction be verified
    verify: Optional[bool] = None
    # Explicit gas budget option
    gas_budget: Optional[str] = None
    # Explicit gas object option (gas comes from sponsor if indicated)
    gas_object: Optional[str] = None
    # Accounts to notify, defaults to requestor
    signers: Optional[Signers] = None

    @property
    def have_signers(self) -> bool:
        """Checks if any signers else default to requestor."""
        if self.signers:
            return (
                True if self.signers.sender or self.signers.sponsor else False
            )
        return False


@dataclass_json
@dataclass
class SigningRejected:
    """."""

    cause: str


@dataclass_json
@dataclass
class SigningApproved:
    """."""

    public_key: str
    active_address: str
    signature: str


@dataclass_json
@dataclass
class SigningResponse:
    """."""

    request_id: int
    outcome: Union[SigningApproved, SigningRejected]

    @property
    def approved(self) -> bool:
        """Test whether signature approved."""
        return isinstance(self.outcome, SigningApproved)

    @property
    def rejected(self) -> bool:
        """Test whether signature approved."""
        return isinstance(self.outcome, SigningRejected)


@dataclass_json
@dataclass
class SignRequestFilter:
    """Filter for request query."""

    signing_as: Optional[str] = None
    pending: Optional[bool] = False
    signed: Optional[bool] = False
    denied: Optional[bool] = False


@dataclass_json
@dataclass
class TransactionFilter:
    """Filter for execution status."""

    request_filter: Optional[SignRequestFilter] = field(
        default_factory=SignRequestFilter
    )


if __name__ == "__main__":
    pass
