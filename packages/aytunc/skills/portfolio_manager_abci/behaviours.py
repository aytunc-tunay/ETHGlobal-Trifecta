# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
#
#   Copyright 2025 Valory AG
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
# ------------------------------------------------------------------------------

"""This package contains round behaviours of PortfolioManagerAbciApp."""

import json
import requests
from abc import ABC
from pathlib import Path
from tempfile import mkdtemp
from typing import Union, Tuple, Dict, Generator, Optional, Set, Type, cast
from datetime import datetime

from packages.valory.contracts.portfolio_manager.contract import PORTFOLIOMANAGER

from packages.valory.contracts.gnosis_safe.contract import (
    GnosisSafeContract,
    SafeOperation,
)
from packages.valory.contracts.multisend.contract import (
    MultiSendContract,
    MultiSendOperation,
)

from packages.valory.protocols.contract_api import ContractApiMessage
from packages.valory.protocols.ledger_api import LedgerApiMessage

from packages.valory.skills.abstract_round_abci.base import AbstractRound
from packages.valory.skills.abstract_round_abci.behaviours import (
    AbstractRoundBehaviour,
    BaseBehaviour,
)

from packages.valory.skills.abstract_round_abci.io_.store import SupportedFiletype



from packages.aytunc.skills.portfolio_manager_abci.models import (
    CoinMarketCapSpecs,
    TheGraphSpecs,
    Params,
    SharedState,
    OpenAISpecs,
)

from packages.aytunc.skills.portfolio_manager_abci.rounds import (
    SynchronizedData,
    PortfolioManagerAbciApp,
    DataPullRound,
    DecisionMakingRound,
    TxPreparationRound,
    Event,
)
from packages.aytunc.skills.portfolio_manager_abci.payloads import (
    DataPullPayload,
    DecisionMakingPayload,
    TxPreparationPayload,
)

from packages.valory.skills.transaction_settlement_abci.payload_tools import (
    hash_payload_to_hex,
)
from packages.valory.skills.transaction_settlement_abci.rounds import TX_HASH_LENGTH

# Define some constants
ZERO_VALUE = 0
ETHEREUM_CHAIN_ID = "ethereum"
EMPTY_CALL_DATA = b"0x"
SAFE_GAS = 0
METADATA_FILENAME = "metadata.json"
USDC_ADDRESS = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
WETH_ADDRESS = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2" 

class PortfolioManagerBaseBehaviour(BaseBehaviour, ABC):
    """Base behaviour for the portfolio_manager_abci skill."""

    @property
    def synchronized_data(self) -> SynchronizedData:
        """Return the synchronized data."""
        return cast(SynchronizedData, super().synchronized_data)

    @property
    def params(self) -> Params:
        """Return the params."""
        return cast(Params, super().params)

    @property
    def local_state(self) -> SharedState:
        """Return the local state of this particular agent."""
        return cast(SharedState, self.context.state)

    @property
    def openai_specs(self) -> OpenAISpecs:
        """Get the OpenAI api specs."""
        return self.context.openai_specs

    @property
    def coinmarketcap_specs(self) -> CoinMarketCapSpecs:
        """Get the CoinMarketCap api specs."""
        return self.context.coinmarketcap_specs
    
    @property
    def thegraph_specs(self) -> TheGraphSpecs:
        """Get the TheGraph api specs."""
        return self.context.thegraph_specs


class DataPullBehaviour(PortfolioManagerBaseBehaviour):
    """DataPullBehaviour - Pulls portfolio data and synchronizes it across agents."""

    matching_round: Type[AbstractRound] = DataPullRound

    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""
        with self.context.benchmark_tool.measure(self.behaviour_id).local():
            sender = self.context.agent_address

            # Dummy data for testing
            token_values = {
                "WETH": 1000.0,
                "USDC": 500.0
            }
            total_portfolio_value = 1500.0

            # Convert token values to JSON
            token_values_json = json.dumps(token_values, sort_keys=True)
            
            payload = DataPullPayload(
                sender=sender,
                token_values=token_values_json,
                total_portfolio_value=total_portfolio_value,
            )

        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()


class DecisionMakingBehaviour(PortfolioManagerBaseBehaviour):
    """DecisionMakingBehaviour - Makes rebalancing decisions based on portfolio data."""

    matching_round: Type[AbstractRound] = DecisionMakingRound

    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""
        with self.context.benchmark_tool.measure(self.behaviour_id).local():
            sender = self.context.agent_address

            # Dummy decision for testing
            rebalancing_actions = {
                "action": "swap 5% of weth to usdc",
                "reason": "market conditions suggest rebalancing"
            }
            rebalancing_actions_json = json.dumps(rebalancing_actions, sort_keys=True)

            # Create payload with only required fields
            payload = DecisionMakingPayload(
                sender=sender,
                event=Event.DONE.value,
                adjustment_balances=rebalancing_actions_json
            )

        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()


class TxPreparationBehaviour(PortfolioManagerBaseBehaviour):
    """TxPreparationBehaviour - Prepares transaction data for portfolio rebalancing."""

    matching_round: Type[AbstractRound] = TxPreparationRound

    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""
        with self.context.benchmark_tool.measure(self.behaviour_id).local():
            sender = self.context.agent_address

            # Dummy transaction hash for testing
            tx_hash = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"

            payload = TxPreparationPayload(
                sender=sender,
                tx_submitter=self.auto_behaviour_id(),
                tx_hash=tx_hash
            )

        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()


class PortfolioManagerRoundBehaviour(AbstractRoundBehaviour):
    """PortfolioManagerRoundBehaviour - Manages the portfolio manager round state machine."""

    initial_behaviour_cls = DataPullBehaviour
    abci_app_cls = PortfolioManagerAbciApp
    behaviours: Set[Type[BaseBehaviour]] = {
        DataPullBehaviour,
        DecisionMakingBehaviour,
        TxPreparationBehaviour,
    }
    late_arriving_toons: Set[str] = set()
