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

from abc import ABC
from typing import Generator, Set, Type, cast

from packages.valory.skills.abstract_round_abci.base import AbstractRound
from packages.valory.skills.abstract_round_abci.behaviours import (
    AbstractRoundBehaviour,
    BaseBehaviour,
)

from packages.aytunc.skills.portfolio_manager__abci.models import Params
from packages.aytunc.skills.portfolio_manager__abci.rounds import (
    SynchronizedData,
    PortfolioManagerAbciApp,
    DataPullRound,
    DecisionMakingRound,
    TxPreparationRound,
)
from packages.aytunc.skills.portfolio_manager__abci.rounds import (
    DataPullPayload,
    DecisionMakingPayload,
    TxPreparationPayload,
)


class PortfolioManagerBaseBehaviour(BaseBehaviour, ABC):
    """Base behaviour for the portfolio_manager__abci skill."""

    @property
    def synchronized_data(self) -> SynchronizedData:
        """Return the synchronized data."""
        return cast(SynchronizedData, super().synchronized_data)

    @property
    def params(self) -> Params:
        """Return the params."""
        return cast(Params, super().params)


class DataPullBehaviour(PortfolioManagerBaseBehaviour):
    """DataPullBehaviour"""

    matching_round: Type[AbstractRound] = DataPullRound

    # TODO: implement logic required to set payload content for synchronization
    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""

        with self.context.benchmark_tool.measure(self.behaviour_id).local():
            sender = self.context.agent_address
            payload = DataPullPayload(sender=sender, content=...)

        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()


class DecisionMakingBehaviour(PortfolioManagerBaseBehaviour):
    """DecisionMakingBehaviour"""

    matching_round: Type[AbstractRound] = DecisionMakingRound

    # TODO: implement logic required to set payload content for synchronization
    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""

        with self.context.benchmark_tool.measure(self.behaviour_id).local():
            sender = self.context.agent_address
            payload = DecisionMakingPayload(sender=sender, content=...)

        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()


class TxPreparationBehaviour(PortfolioManagerBaseBehaviour):
    """TxPreparationBehaviour"""

    matching_round: Type[AbstractRound] = TxPreparationRound

    # TODO: implement logic required to set payload content for synchronization
    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""

        with self.context.benchmark_tool.measure(self.behaviour_id).local():
            sender = self.context.agent_address
            payload = TxPreparationPayload(sender=sender, content=...)

        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()


class PortfolioManagerRoundBehaviour(AbstractRoundBehaviour):
    """PortfolioManagerRoundBehaviour"""

    initial_behaviour_cls = DataPullBehaviour
    abci_app_cls = PortfolioManagerAbciApp  # type: ignore
    behaviours: Set[Type[BaseBehaviour]] = [
        DataPullBehaviour,
        DecisionMakingBehaviour,
        TxPreparationBehaviour
    ]
