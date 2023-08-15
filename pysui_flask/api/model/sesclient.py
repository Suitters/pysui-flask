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

"""Session client configuration."""

from dataclasses import dataclass, field
from dataclasses_json import DataClassJsonMixin

from pysui import SuiConfig


@dataclass
class _BaseConfig(DataClassJsonMixin):
    """Base configuration dataclass.

    At a minimum requires a rpc_url
    ws_url is based on source of configuration. Admin will pop from default configuration
    """

    rpc_url: str
    active_address: str = field(default_factory=str)
    ws_url: str = field(default_factory=str)
    active_key: str = field(default_factory=str)


@dataclass
class UserConfig(_BaseConfig):
    """User configuration dataclass.

    May be updated if settings change
    """


@dataclass
class AdminConfig(_BaseConfig):
    """Admin configuration dataclass.

    Derived from default_config on SuiConfig
    """

    additional_addresses: list[str] = field(default_factory=list)
    additional_keys: list[str] = field(default_factory=list)

    @classmethod
    def from_config(cls, config: SuiConfig) -> "AdminConfig":
        """."""
        active_address = config.active_address
        cfg = cls(
            config.rpc_url,
            active_address.address,
            config.socket_url,
            config.keypair_for_address(active_address).serialize(),
        )
        addy_kp = config.addresses_and_keys
        addy_kp.pop(active_address.address)
        keys, values = zip(*addy_kp.items())
        cfg.additional_addresses = list(keys)
        cfg.additional_keys = [x.serialize() for x in values]
        return cfg


if __name__ == "__main__":
    pass
