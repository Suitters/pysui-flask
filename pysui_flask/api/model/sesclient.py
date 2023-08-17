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

_SUI_STANDARD_URI: dict[str, dict[str, str]] = {
    "devnet": {
        "rpc_url": "https://fullnode.devnet.sui.io:443",
        "ws_url": "wss://fullnode.devnet.sui.io:443",
    },
    "testnet": {
        "rpc_url": "https://fullnode.testnet.sui.io:443",
        "ws_url": "wss://fullnode.testnet.sui.io:443",
    },
    "mainnet": {
        "rpc_url": "https://fullnode.mainnet.sui.io:443",
        "ws_url": "wss://fullnode.mainnet.sui.io:443",
    },
}


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


if __name__ == "__main__":
    pass
