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
    AppState,
    BaseSynchronizedData,
    CollectSameUntilThresholdRound,
    CollectionRound,
    DegenerateRound,
    DeserializedCollection,
    EventToTimeout,
    get_name,
)

from packages.aytunc.skills.portfolio_manager_abci.payloads import (
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
    def _get_deserialized(self, key: str) -> DeserializedCollection:
        """Strictly get a collection and return it deserialized."""
        serialized = self.db.get_strict(key)
        return CollectionRound.deserialize_collection(serialized)

    @property
    def token_values(self) -> Optional[str]:
        """Get the token values."""
        return self.db.get("token_values", None)

    @property
    def total_portfolio_value(self) -> Optional[float]:
        """Get the total portfolio value."""
        return self.db.get("total_portfolio_value", None)


    @property
    def adjustment_balances(self) -> Optional[str]:
        """Get the total adjsutment balances."""
        return self.db.get("adjustment_balances", None)

    @property
    def participant_to_data_round(self) -> DeserializedCollection:
        """Agent to payload mapping for the DataPullRound."""
        return self._get_deserialized("participant_to_data_round")

    @property
    def participant_to_decision_making_round(self) -> DeserializedCollection:
        """Agent to payload mapping for the DecisionMakingRound."""
        return self._get_deserialized("participant_to_decision_making_round")

    @property
    def api_selection(self) -> str:
        """Get the api selection choice."""
        return self.db.get("api_selection", "coingecko")

    @property
    def most_voted_tx_hash(self) -> Optional[float]:
        """Get the token most_voted_tx_hash."""
        return self.db.get("most_voted_tx_hash", None)

    @property
    def participant_to_tx_round(self) -> DeserializedCollection:
        """Get the participants to the tx round."""
        return self._get_deserialized("participant_to_tx_round")

    @property
    def tx_submitter(self) -> str:
        """Get the round that submitted a tx to transaction_settlement_abci."""
        return str(self.db.get_strict("tx_submitter"))


class DataPullRound(CollectSameUntilThresholdRound):
    """DataPullRound"""

    payload_class = DataPullPayload
    # payload_attribute = ""  # TODO: update
    synchronized_data_class = SynchronizedData
    done_event = Event.DONE
    no_majority_event = Event.NO_MAJORITY

    # TODO: replace AbstractRound with one of CollectDifferentUntilAllRound,
    # CollectSameUntilAllRound, CollectSameUntilThresholdRound,
    # CollectDifferentUntilThresholdRound, OnlyKeeperSendsRound, VotingRound,
    # from packages/valory/skills/abstract_round_abci/base.py
    # or implement the methods

    # def end_block(self) -> Optional[Tuple[BaseSynchronizedData, Enum]]:
    #     """Process the end of the block."""
    #     raise NotImplementedError

    # def check_payload(self, payload: DataPullPayload) -> None:
    #     """Check payload."""
    #     raise NotImplementedError

    # def process_payload(self, payload: DataPullPayload) -> None:
    #     """Process payload."""
    #     raise NotImplementedError


    # Collection key specifies where in the synchronized data the agento to payload mapping will be stored
    collection_key = get_name(SynchronizedData.participant_to_data_round)

    # Selection key specifies how to extract all the different objects from each agent's payload
    # and where to store it in the synchronized data. Notice that the order follows the same order
    # from the payload class.
    selection_key = (
        get_name(SynchronizedData.token_values),
        get_name(SynchronizedData.total_portfolio_value),
    )

class DecisionMakingRound(CollectSameUntilThresholdRound):
    """DecisionMakingRound"""

    payload_class = DecisionMakingPayload
    # payload_attribute = ""  # TODO: update
    synchronized_data_class = SynchronizedData

    # TODO: replace AbstractRound with one of CollectDifferentUntilAllRound,
    # CollectSameUntilAllRound, CollectSameUntilThresholdRound,
    # CollectDifferentUntilThresholdRound, OnlyKeeperSendsRound, VotingRound,
    # from packages/valory/skills/abstract_round_abci/base.py
    # or implement the methods

    # def end_block(self) -> Optional[Tuple[BaseSynchronizedData, Enum]]:
    #     """Process the end of the block."""
    #     raise NotImplementedError

    # def check_payload(self, payload: DecisionMakingPayload) -> None:
    #     """Check payload."""
    #     raise NotImplementedError

    # def process_payload(self, payload: DecisionMakingPayload) -> None:
    #     """Process payload."""
    #     raise NotImplementedError

    # Define collection and selection keys
    collection_key = get_name(SynchronizedData.participant_to_decision_making_round)
    selection_key = (
        get_name(SynchronizedData.adjustment_balances),
    )

    def end_block(self) -> Optional[Tuple[BaseSynchronizedData, Event]]:
        """Process the end of the block."""

        if self.threshold_reached:
            # Search for the payload matching the most voted event
            most_voted_payload_data = None
            for payload in self.collection.values():
                if payload.event == self.most_voted_payload:
                    most_voted_payload_data = payload
                    break

            if most_voted_payload_data is None:
                self.context.logger.error("Most voted payload data not found.")
                return self.synchronized_data, Event.ERROR

            # Extract `adjustment_balances` and update synchronized data
            adjustment_balances = most_voted_payload_data.adjustment_balances
            if adjustment_balances is not None:
                new_synchronized_data = self.synchronized_data.update(
                    adjustment_balances=adjustment_balances
                )
            else:
                self.context.logger.warning("Adjustment balances not found in payload.")
                return self.synchronized_data, Event.DONE

            return new_synchronized_data, Event.TRANSACT

        if not self.is_majority_possible(
            self.collection, self.synchronized_data.nb_participants
        ):
            return self.synchronized_data, Event.NO_MAJORITY

        return None


class TxPreparationRound(CollectSameUntilThresholdRound):
    """TxPreparationRound"""

    payload_class = TxPreparationPayload
    # payload_attribute = ""  # TODO: update
    synchronized_data_class = SynchronizedData
    done_event = Event.DONE
    no_majority_event = Event.NO_MAJORITY

    # TODO: replace AbstractRound with one of CollectDifferentUntilAllRound,
    # CollectSameUntilAllRound, CollectSameUntilThresholdRound,
    # CollectDifferentUntilThresholdRound, OnlyKeeperSendsRound, VotingRound,
    # from packages/valory/skills/abstract_round_abci/base.py
    # or implement the methods

    # def end_block(self) -> Optional[Tuple[BaseSynchronizedData, Enum]]:
    #     """Process the end of the block."""
    #     raise NotImplementedError

    # def check_payload(self, payload: TxPreparationPayload) -> None:
    #     """Check payload."""
    #     raise NotImplementedError

    # def process_payload(self, payload: TxPreparationPayload) -> None:
    #     """Process payload."""
    #     raise NotImplementedError

    collection_key = get_name(SynchronizedData.participant_to_tx_round)
    selection_key = (
        get_name(SynchronizedData.tx_submitter),
        get_name(SynchronizedData.most_voted_tx_hash),
    )


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
    final_states: Set[AppState] = {
        FinishedDecisionMakingRound, 
        FinishedTxPreparationRound
    }
    event_to_timeout: EventToTimeout = {}
    cross_period_persisted_keys: FrozenSet[str] = frozenset()
    db_pre_conditions: Dict[AppState, Set[str]] = {
        DataPullRound: set(),
    }
    db_post_conditions: Dict[AppState, Set[str]] = {
        FinishedDecisionMakingRound: set(),
    	FinishedTxPreparationRound: {get_name(SynchronizedData.most_voted_tx_hash)},
    }