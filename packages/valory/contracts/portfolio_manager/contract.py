from typing import List
from aea.common import JSONLike
from aea.configurations.base import PublicId
from aea.contracts.base import Contract
from aea.crypto.base import LedgerApi
from aea_ledger_ethereum import EthereumApi

PUBLIC_ID = PublicId.from_str("valory/portfolio_manager:0.1.0")

class PORTFOLIOMANAGER(Contract):
    """Wrapper class for interacting with the Portfolio Manager contract."""

    contract_id = PUBLIC_ID

    @classmethod
    def deposit(
        cls,
        ledger_api: EthereumApi,
        contract_address: str,
        token: str,
        amount: int,
        from_address: str,
    ) -> JSONLike:
        """
        Deposit tokens into the contract.

        :param ledger_api: Ethereum API instance for contract interaction.
        :param contract_address: Address of the deployed contract.
        :param token: Token address to deposit.
        :param amount: Amount of tokens to deposit.
        :param from_address: Address initiating the transaction.
        :return: Transaction dictionary.
        """
        contract_instance = cls.get_instance(ledger_api, contract_address)
        transaction = contract_instance.functions.deposit(token, amount).build_transaction({
            "from": from_address
        })
        return transaction

    @classmethod
    def withdraw(
        cls,
        ledger_api: EthereumApi,
        contract_address: str,
        token: str,
        amount: int,
        from_address: str,
    ) -> JSONLike:
        """
        Withdraw tokens from the contract.

        :param ledger_api: Ethereum API instance for contract interaction.
        :param contract_address: Address of the deployed contract.
        :param token: Token address to withdraw.
        :param amount: Amount of tokens to withdraw.
        :param from_address: Address initiating the transaction.
        :return: Transaction dictionary.
        """
        contract_instance = cls.get_instance(ledger_api, contract_address)
        transaction = contract_instance.functions.withdraw(token, amount).build_transaction({
            "from": from_address
        })
        return transaction

    @classmethod
    def execute_rebalance(
        cls,
        ledger_api: EthereumApi,
        contract_address: str,
        user: str,
        swaps: List[tuple],
        from_address: str,
    ) -> JSONLike:
        """
        Execute a rebalance operation with multiple swaps.

        :param ledger_api: Ethereum API instance for contract interaction.
        :param contract_address: Address of the deployed contract.
        :param user: Address of the user.
        :param swaps: List of swap parameter tuples (tokenToSell, tokenToBuy, amountToSell, amountOutMin, poolFee).
        :param from_address: Address initiating the transaction.
        :return: Transaction dictionary.
        """
        contract_instance = cls.get_instance(ledger_api, contract_address)
        transaction = contract_instance.functions.executeRebalance(user, swaps).build_transaction({
            "from": from_address
        })
        return transaction

    @classmethod
    def check_allowance(
        cls,
        ledger_api: EthereumApi,
        contract_address: str,
        token: str,
        user: str,
    ) -> JSONLike:
        """
        Check token allowance for a user.

        :param ledger_api: Ethereum API instance for contract interaction.
        :param contract_address: Address of the deployed contract.
        :param token: Token address to check allowance for.
        :param user: User address to check allowance for.
        :return: Dictionary containing the allowance amount.
        """
        contract_instance = cls.get_instance(ledger_api, contract_address)
        allowance = contract_instance.functions.checkAllowance(token, user).call()
        return {"allowance": allowance}

    @classmethod
    def get_user_balances(
        cls,
        ledger_api: EthereumApi,
        contract_address: str,
        user: str,
        tokens: List[str],
    ) -> JSONLike:
        """
        Get balances for multiple tokens for a user.

        :param ledger_api: Ethereum API instance for contract interaction.
        :param contract_address: Address of the deployed contract.
        :param user: User address to check balances for.
        :param tokens: List of token addresses to check balances for.
        :return: Dictionary containing the token balances.
        """
        contract_instance = cls.get_instance(ledger_api, contract_address)
        balances = contract_instance.functions.getUserBalances(user, tokens).call()
        return {"balances": balances}

    @classmethod
    def get_portfolio_status(
        cls,
        ledger_api: EthereumApi,
        contract_address: str,
        user: str,
    ) -> JSONLike:
        """
        Check if a user's portfolio is registered.

        :param ledger_api: Ethereum API instance for contract interaction.
        :param contract_address: Address of the deployed contract.
        :param user: User address to check portfolio status.
        :return: Dictionary containing the portfolio registration status.
        """
        contract_instance = cls.get_instance(ledger_api, contract_address)
        status = contract_instance.functions.portfolios(user).call()
        return {"registered": status}

    @classmethod
    def get_safe_address(
        cls,
        ledger_api: EthereumApi,
        contract_address: str,
    ) -> JSONLike:
        """
        Get the safe address associated with the contract.

        :param ledger_api: Ethereum API instance for contract interaction.
        :param contract_address: Address of the deployed contract.
        :return: Dictionary containing the safe address.
        """
        contract_instance = cls.get_instance(ledger_api, contract_address)
        safe_address = contract_instance.functions.safeAddress().call()
        return {"safe_address": safe_address}

    @classmethod
    def get_swap_router(
        cls,
        ledger_api: EthereumApi,
        contract_address: str,
    ) -> JSONLike:
        """
        Get the swap router address.

        :param ledger_api: Ethereum API instance for contract interaction.
        :param contract_address: Address of the deployed contract.
        :return: Dictionary containing the swap router address.
        """
        contract_instance = cls.get_instance(ledger_api, contract_address)
        router_address = contract_instance.functions.swapRouter().call()
        return {"swap_router": router_address}
