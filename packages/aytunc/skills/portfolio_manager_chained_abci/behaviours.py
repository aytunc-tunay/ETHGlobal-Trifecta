"""This package contains round behaviours of PortfolioManagerChainedSkillAbci."""

from typing import Set, Type

from packages.valory.skills.abstract_round_abci.behaviours import (
    AbstractRoundBehaviour,
    BaseBehaviour,
)
from packages.aytunc.skills.portfolio_manager_abci.behaviours import PortfolioManagerRoundBehaviour
from packages.aytunc.skills.portfolio_manager_chained_abci.composition import (
    PortfolioManagerChainedSkillAbciApp,
)
from packages.valory.skills.registration_abci.behaviours import (
    AgentRegistrationRoundBehaviour,
    RegistrationStartupBehaviour,
)
from packages.valory.skills.reset_pause_abci.behaviours import (
    ResetPauseABCIConsensusBehaviour,
)
from packages.valory.skills.termination_abci.behaviours import (
    BackgroundBehaviour,
    TerminationAbciBehaviours,
)
from packages.valory.skills.transaction_settlement_abci.behaviours import (
    TransactionSettlementRoundBehaviour,
)


class PortfolioManagerChainedConsensusBehaviour(AbstractRoundBehaviour):
    """Class to define the behaviours this AbciApp has."""

    initial_behaviour_cls = RegistrationStartupBehaviour
    abci_app_cls = PortfolioManagerChainedSkillAbciApp
    behaviours: Set[Type[BaseBehaviour]] = {
        *AgentRegistrationRoundBehaviour.behaviours,
        *ResetPauseABCIConsensusBehaviour.behaviours,
        *TransactionSettlementRoundBehaviour.behaviours,
        *TerminationAbciBehaviours.behaviours,
        *PortfolioManagerRoundBehaviour.behaviours,
    }
    background_behaviours_cls = {BackgroundBehaviour}
