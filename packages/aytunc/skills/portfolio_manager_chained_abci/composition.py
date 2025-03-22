
"""This package contains round behaviours of PortfolioManagerChainedSkillAbciApp."""

import packages.aytunc.skills.portfolio_manager_abci.rounds as PortfolioManagerAbci
import packages.valory.skills.registration_abci.rounds as RegistrationAbci
import packages.valory.skills.reset_pause_abci.rounds as ResetAndPauseAbci
import packages.valory.skills.transaction_settlement_abci.rounds as TxSettlementAbci
from packages.valory.skills.abstract_round_abci.abci_app_chain import (
    AbciAppTransitionMapping,
    chain,
)
from packages.valory.skills.abstract_round_abci.base import BackgroundAppConfig
from packages.valory.skills.termination_abci.rounds import (
    BackgroundRound,
    Event,
    TerminationAbciApp,
)


abci_app_transition_mapping: AbciAppTransitionMapping = {
    RegistrationAbci.FinishedRegistrationRound: PortfolioManagerAbci.DataPullRound,
    PortfolioManagerAbci.FinishedDecisionMakingRound: ResetAndPauseAbci.ResetAndPauseRound,
    PortfolioManagerAbci.FinishedTxPreparationRound: TxSettlementAbci.RandomnessTransactionSubmissionRound,
    TxSettlementAbci.FinishedTransactionSubmissionRound: ResetAndPauseAbci.ResetAndPauseRound,
    TxSettlementAbci.FailedRound: TxSettlementAbci.RandomnessTransactionSubmissionRound,
    ResetAndPauseAbci.FinishedResetAndPauseRound: PortfolioManagerAbci.DataPullRound,
    ResetAndPauseAbci.FinishedResetAndPauseErrorRound: RegistrationAbci.RegistrationRound,
}

termination_config = BackgroundAppConfig(
    round_cls=BackgroundRound,
    start_event=Event.TERMINATE,
    abci_app=TerminationAbciApp,
)

PortfolioManagerChainedSkillAbciApp = chain(
    (
        RegistrationAbci.AgentRegistrationAbciApp,
        PortfolioManagerAbci.PortfolioManagerAbciApp,
        TxSettlementAbci.TransactionSubmissionAbciApp,
        ResetAndPauseAbci.ResetPauseAbciApp,
    ),
    abci_app_transition_mapping,
).add_background_app(termination_config)
