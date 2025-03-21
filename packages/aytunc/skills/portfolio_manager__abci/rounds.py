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

"""This package contains the rounds of PortfolioManagerAbciApp."""

from enum import Enum
from typing import Dict, FrozenSet, List, Optional, Set, Tuple

from packages.valory.skills.abstract_round_abci.base import (
    AbciApp,
    AbciAppTransitionFunction,
    AbstractRound,
    AppState,
    BaseSynchronizedData,
    DegenerateRound,
    EventToTimeout,
)

from packages.aytunc.skills.portfolio_manager__abci.payloads import (
    DataPullPayload,
    DecisionMakingPayload,
    TxPreparationPayload,
)


class Event(Enum):
    """PortfolioManagerAbciApp Events"""

    ERROR = "error"
    ROUND_TIMEOUT = "round_timeout"
    TRANSACT = "transact"
    DONE = "done"
    NO_MAJORITY = "no_majority"


class SynchronizedData(BaseSynchronizedData):
    """
    Class to represent the synchronized data.

    This data is replicated by the tendermint application.
    """


class DataPullRound(AbstractRound):
    """DataPullRound"""

    payload_class = DataPullPayload
    payload_attribute = ""  # TODO: update
    synchronized_data_class = SynchronizedData

    # TODO: replace AbstractRound with one of CollectDifferentUntilAllRound,
    # CollectSameUntilAllRound, CollectSameUntilThresholdRound,
    # CollectDifferentUntilThresholdRound, OnlyKeeperSendsRound, VotingRound,
    # from packages/valory/skills/abstract_round_abci/base.py
    # or implement the methods

    def end_block(self) -> Optional[Tuple[BaseSynchronizedData, Enum]]:
        """Process the end of the block."""
        raise NotImplementedError

    def check_payload(self, payload: DataPullPayload) -> None:
        """Check payload."""
        raise NotImplementedError

    def process_payload(self, payload: DataPullPayload) -> None:
        """Process payload."""
        raise NotImplementedError


class DecisionMakingRound(AbstractRound):
    """DecisionMakingRound"""

    payload_class = DecisionMakingPayload
    payload_attribute = ""  # TODO: update
    synchronized_data_class = SynchronizedData

    # TODO: replace AbstractRound with one of CollectDifferentUntilAllRound,
    # CollectSameUntilAllRound, CollectSameUntilThresholdRound,
    # CollectDifferentUntilThresholdRound, OnlyKeeperSendsRound, VotingRound,
    # from packages/valory/skills/abstract_round_abci/base.py
    # or implement the methods

    def end_block(self) -> Optional[Tuple[BaseSynchronizedData, Enum]]:
        """Process the end of the block."""
        raise NotImplementedError

    def check_payload(self, payload: DecisionMakingPayload) -> None:
        """Check payload."""
        raise NotImplementedError

    def process_payload(self, payload: DecisionMakingPayload) -> None:
        """Process payload."""
        raise NotImplementedError


class TxPreparationRound(AbstractRound):
    """TxPreparationRound"""

    payload_class = TxPreparationPayload
    payload_attribute = ""  # TODO: update
    synchronized_data_class = SynchronizedData

    # TODO: replace AbstractRound with one of CollectDifferentUntilAllRound,
    # CollectSameUntilAllRound, CollectSameUntilThresholdRound,
    # CollectDifferentUntilThresholdRound, OnlyKeeperSendsRound, VotingRound,
    # from packages/valory/skills/abstract_round_abci/base.py
    # or implement the methods

    def end_block(self) -> Optional[Tuple[BaseSynchronizedData, Enum]]:
        """Process the end of the block."""
        raise NotImplementedError

    def check_payload(self, payload: TxPreparationPayload) -> None:
        """Check payload."""
        raise NotImplementedError

    def process_payload(self, payload: TxPreparationPayload) -> None:
        """Process payload."""
        raise NotImplementedError


class FinishedDecisionMakingRound(DegenerateRound):
    """FinishedDecisionMakingRound"""


class FinishedTxPreparationRound(DegenerateRound):
    """FinishedTxPreparationRound"""


class PortfolioManagerAbciApp(AbciApp[Event]):
    """PortfolioManagerAbciApp"""

    initial_round_cls: AppState = DataPullRound
    initial_states: Set[AppState] = {DataPullRound}
    transition_function: AbciAppTransitionFunction = {
        DataPullRound: {
            Event.DONE: DecisionMakingRound,
            Event.NO_MAJORITY: DataPullRound,
            Event.ROUND_TIMEOUT: DataPullRound
        },
        DecisionMakingRound: {
            Event.DONE: FinishedDecisionMakingRound,
            Event.ERROR: FinishedDecisionMakingRound,
            Event.NO_MAJORITY: DecisionMakingRound,
            Event.ROUND_TIMEOUT: DecisionMakingRound,
            Event.TRANSACT: TxPreparationRound
        },
        TxPreparationRound: {
            Event.DONE: FinishedTxPreparationRound,
            Event.NO_MAJORITY: TxPreparationRound,
            Event.ROUND_TIMEOUT: TxPreparationRound
        },
        FinishedDecisionMakingRound: {},
        FinishedTxPreparationRound: {}
    }
    final_states: Set[AppState] = {FinishedDecisionMakingRound, FinishedTxPreparationRound}
    event_to_timeout: EventToTimeout = {}
    cross_period_persisted_keys: FrozenSet[str] = frozenset()
    db_pre_conditions: Dict[AppState, Set[str]] = {
        DataPullRound: [],
    }
    db_post_conditions: Dict[AppState, Set[str]] = {
        FinishedDecisionMakingRound: [],
    	FinishedTxPreparationRound: [],
    }
