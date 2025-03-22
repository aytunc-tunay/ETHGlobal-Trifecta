"""This module contains the shared state for the abci skill of PortfolioManagerChainedSkillAbciApp."""

from packages.valory.skills.abstract_round_abci.models import (
    BenchmarkTool as BaseBenchmarkTool,
)
from packages.valory.skills.abstract_round_abci.models import Requests as BaseRequests
from packages.valory.skills.abstract_round_abci.tests.data.dummy_abci.models import (
    RandomnessApi as BaseRandomnessApi,
)

from packages.aytunc.skills.portfolio_manager_abci.models import (
    TheGraphSpecs as BaseTheGraphSpecs,
    CoinMarketCapSpecs as BaseCoinMarketCapSpecs,
    OpenAISpecs as BaseOpenAISpecs


)
from packages.aytunc.skills.portfolio_manager_abci.models import Params as PortfolioManagerParams
from packages.aytunc.skills.portfolio_manager_abci.models import SharedState as BaseSharedState
from packages.aytunc.skills.portfolio_manager_abci.rounds import Event as PortfolioManagerEvent
from packages.aytunc.skills.portfolio_manager_chained_abci.composition import (
    PortfolioManagerChainedSkillAbciApp,
)
from packages.valory.skills.reset_pause_abci.rounds import Event as ResetPauseEvent
from packages.valory.skills.termination_abci.models import TerminationParams


Requests = BaseRequests
BenchmarkTool = BaseBenchmarkTool

RandomnessApi = BaseRandomnessApi

MARGIN = 5
MULTIPLIER = 10


class SharedState(BaseSharedState):
    """Keep the current shared state of the skill."""

    abci_app_cls = PortfolioManagerChainedSkillAbciApp  # type: ignore

    def setup(self) -> None:
        """Set up."""
        super().setup()

        PortfolioManagerChainedSkillAbciApp.event_to_timeout[
            ResetPauseEvent.ROUND_TIMEOUT
        ] = self.context.params.round_timeout_seconds

        PortfolioManagerChainedSkillAbciApp.event_to_timeout[
            ResetPauseEvent.RESET_AND_PAUSE_TIMEOUT
        ] = (self.context.params.reset_pause_duration + MARGIN)

        PortfolioManagerChainedSkillAbciApp.event_to_timeout[PortfolioManagerEvent.ROUND_TIMEOUT] = (
            self.context.params.round_timeout_seconds * MULTIPLIER
        )


class Params(  # pylint: disable=too-many-ancestors
    PortfolioManagerParams,
    TerminationParams,
):
    """A model to represent params for multiple abci apps."""


class CoinMarketCapSpecs(BaseCoinMarketCapSpecs):
    """A model that wraps ApiSpecs for CoinMarketCap API."""

class TheGraphSpecs(BaseTheGraphSpecs):
    """A model that wraps ApiSpecs for TheGraph API."""


class OpenAISpecs(BaseOpenAISpecs):
    """A model that wraps ApiSpecs for OpenAI API."""   