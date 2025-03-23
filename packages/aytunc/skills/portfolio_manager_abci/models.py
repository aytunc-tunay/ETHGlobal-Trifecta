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

"""This module contains the shared state for the abci skill of PortfolioManagerAbciApp."""

from typing import Any


from packages.valory.skills.abstract_round_abci.models import ApiSpecs,BaseParams
from packages.valory.skills.abstract_round_abci.models import (
    BenchmarkTool as BaseBenchmarkTool,
)
from packages.valory.skills.abstract_round_abci.models import Requests as BaseRequests
from packages.valory.skills.abstract_round_abci.models import (
    SharedState as BaseSharedState,
)
from packages.aytunc.skills.portfolio_manager_abci.rounds import PortfolioManagerAbciApp


class SharedState(BaseSharedState):
    """Keep the current shared state of the skill."""

    abci_app_cls = PortfolioManagerAbciApp


Requests = BaseRequests
BenchmarkTool = BaseBenchmarkTool

class Params(BaseParams):
    """Parameters."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the parameters object."""

        self.coinmarketcap_api_key = kwargs.get("coinmarketcap_api_key", None)
        self.thegraph_api_key = kwargs.get("thegraph_api_key", None)
        self.openai_api_key = kwargs.get("openai_api_key", None)

        self.llm_selection = kwargs.get("llm_selection", None)

        # self.transfer_target_address = self._ensure(
        #     "transfer_target_address", kwargs, str
        # )
        # self.olas_token_address = self._ensure("olas_token_address", kwargs, str)

        # multisend address is used in other skills, so we cannot pop it using _ensure
        self.multisend_address = kwargs.get("multisend_address", None)

        # Rebalancing settings
        self.portfolio_address_string: str = self._ensure("portfolio_address", kwargs, str)
        self.portfolio_manager_contract_address_string: str = self._ensure("portfolio_manager_contract_address", kwargs, str)

        
        #Neeed for from field while interacting with protected contract of MockTrade.
        self.safe_address: str = kwargs.get("setup", {}).get("safe_contract_address", "")



        super().__init__(*args, **kwargs)



class CoinMarketCapSpecs(ApiSpecs):
    """A model that wraps ApiSpecs for CoinMarketCap API."""

class TheGraphSpecs(ApiSpecs):
    """A model that wraps ApiSpecs for TheGraph API."""

class OpenAISpecs(ApiSpecs):
    """A model that wraps ApiSpecs for Coinmarketcap API."""

class NillionSpecs(ApiSpecs):
    """A model that wraps ApiSpecs for Nillion API."""
