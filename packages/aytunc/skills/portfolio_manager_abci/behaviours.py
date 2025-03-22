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
    """Behaviour responsible for pulling token balances and prices to calculate portfolio allocation."""

    matching_round: Type[AbstractRound] = DataPullRound

    def async_act(self) -> Generator:
        """
        Execute the data pull behaviour asynchronously.
        
        This method:
        1. Calculates current portfolio allocation and value
        2. Creates a payload with the results
        3. Sends the payload for consensus
        """
        with self.context.benchmark_tool.measure(self.behaviour_id).local():
            # Get portfolio data
            token_values, total_portfolio_value = yield from self.calculate_portfolio_allocation()
            self.context.logger.info(f"Token values: {token_values}")
            self.context.logger.info(f"Total portfolio value: {total_portfolio_value}")

            # Convert token values to JSON for payload
            token_values_json = json.dumps(token_values, sort_keys=True) if token_values else None
            self.context.logger.info(f"Token values JSON: {token_values_json}")
            
            # Create payload with portfolio data
            payload = DataPullPayload(
                sender=self.context.agent_address,
                token_values=token_values_json,
                total_portfolio_value=total_portfolio_value,
            )

        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()
    
    def get_token_price_specs(self, symbol: str) -> Generator[None, None, Optional[float]]:
        """
        Fetch current token price from CoinMarketCap API.

        Args:
            symbol: Token symbol (e.g. "USDC", "WETH")

        Returns:
            Current token price in USD, or None if price fetch fails
        """
        # Prepare API request
        specs = self.coinmarketcap_specs.get_spec()
        specs["parameters"]["symbol"] = symbol

        # Make API call and process response
        raw_response = yield from self.get_http_response(**specs)
        response = self.coinmarketcap_specs.process_response(raw_response)

        # Extract price from response
        price = response.get(symbol, {}).get("quote", {}).get("USD", {}).get("price", None)
        self.context.logger.info(f"Got token price from CoinMarketCap: {price}")

        return price

    def get_token_balances(self) -> Generator[None, None, Optional[Dict[str, float]]]:
        """
        Fetch token balances from the deployed smart contract.

        Returns:
            Dictionary mapping token symbols to their balances, or None if fetch fails
        """
        # Get contract addresses
        portfolio_address = self.params.portfolio_address_string
        portfolio_manager_contract_address = self.params.portfolio_manager_contract_address_string

        # Define tokens to track
        tokens_to_rebalance = {
            "USDC": {"address": USDC_ADDRESS, "decimals": 6},
            "WETH": {"address": WETH_ADDRESS, "decimals": 18}
        }

        # Prepare token data for contract call
        token_addresses = [token_info["address"] for token_info in tokens_to_rebalance.values()]
        token_symbols = list(tokens_to_rebalance.keys())

        # Call contract to get balances
        response_msg = yield from self.get_contract_api_response(
            performative=ContractApiMessage.Performative.GET_RAW_TRANSACTION,  # type: ignore
            contract_address=portfolio_manager_contract_address,
            contract_id=str(PORTFOLIOMANAGER.contract_id),
            contract_callable="get_user_balances",
            user=portfolio_address,
            tokens=token_addresses,
            chain_id=ETHEREUM_CHAIN_ID,
        )

        # Validate response
        if response_msg.performative != ContractApiMessage.Performative.RAW_TRANSACTION:
            self.context.logger.error(f"Error retrieving balances: {response_msg}")
            return None

        balances_list = response_msg.raw_transaction.body.get("balances", None)
        if balances_list is None:
            self.context.logger.error("No balance data returned")
            return None

        # Process balances
        balances = {}
        for symbol, balance in zip(token_symbols, balances_list):
            if balance is not None:
                decimals = tokens_to_rebalance[symbol]["decimals"]
                readable_balance = float(balance) / (10 ** decimals)
                balances[symbol] = readable_balance
                self.context.logger.info(f"Balance for {symbol}: {readable_balance}")
            else:
                self.context.logger.error(f"No balance data returned for {symbol}")
                balances[symbol] = None

        return balances if balances else None

    def calculate_portfolio_allocation(self) -> Generator[None, None, Optional[Tuple[Dict[str, float], float]]]:
        """
        Calculate current portfolio value and allocation percentages.

        Returns:
            Tuple containing:
            - Dictionary mapping token symbols to their USD values
            - Total portfolio value in USD
            Returns None if calculation fails
        """
        # Get current token balances
        token_balances = yield from self.get_token_balances()
        if token_balances is None:
            self.context.logger.error("Failed to retrieve token balances.")
            return None

        # Calculate USD values for each token
        total_portfolio_value = 0.0
        token_values = {}

        for token_symbol, balance in token_balances.items():
            if balance is None:
                self.context.logger.error(f"No balance available for {token_symbol}")
                continue

            # Get current token price
            price = yield from self.get_token_price_specs(symbol=token_symbol)
            if price is None:
                self.context.logger.error(f"Failed to retrieve price for {token_symbol}")
                continue

            # Calculate token value in USD
            token_value = balance * price
            token_values[token_symbol] = token_value
            total_portfolio_value += token_value

            self.context.logger.info(f"Value for {token_symbol}: {token_value:.2f} USD")

        # Validate total portfolio value
        if total_portfolio_value == 0:
            self.context.logger.error("Total portfolio value is zero; cannot calculate allocation.")
            return None

        # Log allocation percentages
        for token_symbol, token_value in token_values.items():
            percentage = (token_value / total_portfolio_value) * 100
            self.context.logger.info(f"{token_symbol}: {percentage:.2f}% of portfolio (Value: {token_value:.2f} USD)")

        self.context.logger.info(f"Total Portfolio Value: {total_portfolio_value:.2f} USD")

        return token_values, total_portfolio_value


class DecisionMakingBehaviour(PortfolioManagerBaseBehaviour):
    """
    Behaviour class responsible for making portfolio rebalancing decisions.
    Analyzes market data and current portfolio allocation to determine optimal rebalancing actions.
    """

    matching_round: Type[AbstractRound] = DecisionMakingRound

    def async_act(self) -> Generator:
        """
        Main behaviour execution method that runs asynchronously.
        Generates and sends a decision payload for consensus.
        """
        # Measure local execution time
        with self.context.benchmark_tool.measure(self.behaviour_id).local():
            sender = self.context.agent_address

            # Get rebalancing decision and IPFS report
            event, rebalancing_decision, report_hash = yield from self.get_next_event()

            # Create payload with decision data
            payload = DecisionMakingPayload(
                sender=sender,
                event=event,
                adjustment_balances=rebalancing_decision,
                ipfs_hash=report_hash
            )

        # Measure consensus round time
        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()

    def get_uniswap_token_price_specs(self) -> Generator[None, None, Optional[str]]:
        """
        Fetches historical token price and volume data from Uniswap V3 via The Graph API.
        
        Returns:
            Optional[str]: JSON response containing token data, or None if request fails
        """
        # Get API specifications
        specs = self.thegraph_specs.get_spec()

        # GraphQL query to fetch 7-day price history for USDC and WETH
        graphql_query = """
        {
          USDC: tokenDayDatas(
            where: { token: "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48" }
            orderBy: date
            orderDirection: desc
            first: 7
          ) {
            date
            priceUSD
            volumeUSD
            feesUSD
          }
          WETH: tokenDayDatas(
            where: { token: "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2" }
            orderBy: date
            orderDirection: desc
            first: 7
          ) {
            date
            priceUSD
            volumeUSD
            feesUSD
          }
        }
        """

        # Prepare request parameters
        specs["parameters"].update({
            "query": graphql_query,
            "operationName": "Subgraphs",
            "variables": {}
        })

        # Encode request payload
        request_content = json.dumps(specs["parameters"]).encode("utf-8")

        try:
            # Make HTTP request to The Graph API
            raw_response = yield from self.get_http_response(
                method="POST",
                url=specs["url"],
                content=request_content,
                headers=specs["headers"]
            )

            # Extract response body based on response type
            if isinstance(raw_response, dict) and "body" in raw_response:
                response_body = raw_response["body"]
            elif hasattr(raw_response, "body"):
                response_body = raw_response.body
            else:
                self.context.logger.error(f"Unexpected response format: {raw_response}")
                return None

            # Parse JSON response
            try:
                parsed_response = json.loads(response_body.decode("utf-8"))
            except json.JSONDecodeError as e:
                self.context.logger.error(f"Error decoding JSON response: {str(e)}")
                return None

            # Log successful response
            self.context.logger.info(f"Processed Response from Uniswap V3 API: {json.dumps(parsed_response, indent=2)}")

            # Validate and return data
            if "data" not in parsed_response:
                self.context.logger.error("No data field in response")
                return None

            return parsed_response["data"]

        except Exception as e:
            self.context.logger.error(f"Error fetching price data: {str(e)}")
            return None

    def get_llm_response(self, prompt: str) -> Generator[None, None, Optional[dict]]:
        """
        Gets rebalancing recommendation from OpenAI API based on provided prompt.
        
        Args:
            prompt (str): The prompt to send to the LLM
            
        Returns:
            Optional[dict]: Parsed JSON response containing rebalancing decision, or None if request fails
        """
        # Get API specifications
        specs = self.openai_specs.get_spec()
        
        # Update prompt in message parameters
        specs['parameters']['messages'][1]['content'] = prompt

        # Prepare request payload
        request_content = json.dumps(specs['parameters']).encode('utf-8')

        # Make API request
        raw_response = yield from self.get_http_response(
            method=specs['method'],
            url=specs['url'],
            content=request_content, 
            headers=specs['headers']
        )

        try:
            # Parse response and extract decision
            response_data = json.loads(raw_response.body)
            response_text = response_data.get('choices', [])[0].get('message', {}).get('content', '').strip()
            
            # Handle markdown code blocks if present
            if '```json' in response_text:
                json_str = response_text.split('```json\n')[1].split('\n```')[0]
            else:
                json_str = response_text
                
            # Parse final decision
            decision_dict = json.loads(json_str)
            
            self.context.logger.info(f"Parsed decision: {decision_dict}")
            return decision_dict
            
        except (json.JSONDecodeError, IndexError, KeyError) as e:
            self.context.logger.error(f"Error parsing OpenAI response: {e}")
            return None

    def get_next_event(self) -> Generator[None, None, Optional[Tuple[str,Dict[str, float], str]]]:
        """
        Determines next portfolio action by calculating rebalancing needs and generating a report.
        
        Returns:
            Tuple containing:
            - Event type (str)
            - Rebalancing actions (Dict[str, float])
            - IPFS report hash (str)
        """
        # Get rebalancing recommendation
        rebalancing_actions = yield from self.calculate_rebalancing_actions()

        # Get current portfolio state
        token_values = self.synchronized_data.token_values
        total_portfolio_value = self.synchronized_data.total_portfolio_value
        
        # Convert rebalancing actions to JSON
        rebalancing_actions_json = json.dumps(rebalancing_actions, sort_keys=True) if rebalancing_actions else None

        # Generate and store report
        report_ipfs_hash = yield from self.generate_and_store_report(
            token_values, 
            total_portfolio_value, 
            rebalancing_actions_json
        )

        # Log report status
        if report_ipfs_hash:
            self.context.logger.info(f"Rebalancing report stored in IPFS: https://gateway.autonolas.tech/ipfs/{report_ipfs_hash}")
        else:
            self.context.logger.error("Failed to store rebalancing report in IPFS.")

        return Event.TRANSACT.value, rebalancing_actions_json, report_ipfs_hash

    def calculate_rebalancing_actions(self) -> Generator[None, None, Optional[Dict[str, str]]]:
        """
        Analyzes current portfolio allocation and market data to determine optimal rebalancing actions.
        
        Returns:
            Optional[Dict[str, str]]: Dictionary containing rebalancing action and reason, or None if calculation fails
        """
        self.context.logger.info("Starting rebalancing calculation...")

        # Get current token values
        token_values_json = self.synchronized_data.token_values
        self.context.logger.info(f"Token values JSON retrieved: {token_values_json}")

        # Parse token values
        token_values = {}
        if token_values_json is not None:
            try:
                token_values = json.loads(token_values_json)
                self.context.logger.info(f"Parsed token values dictionary: {token_values}")
            except json.JSONDecodeError as e:
                self.context.logger.error(f"Failed to decode token values JSON: {e}")
                return None
        else:
            self.context.logger.warning("Token values JSON is None. No tokens to rebalance.")
            return None

        # Validate portfolio value
        total_portfolio_value = self.synchronized_data.total_portfolio_value
        if total_portfolio_value is None or total_portfolio_value <= 0:
            self.context.logger.error("Total portfolio value is None or zero; cannot calculate rebalancing.")
            return None

        # Get market data
        token_data = yield from self.get_uniswap_token_price_specs()

        # Calculate current allocation percentages
        weth_percentage = (token_values.get("WETH", 0) / total_portfolio_value) * 100
        usdc_percentage = (token_values.get("USDC", 0) / total_portfolio_value) * 100

        # Get latest market data points
        weth_latest = token_data["WETH"][0]
        weth_yesterday = token_data["WETH"][1]
        usdc_latest = token_data["USDC"][0]
        usdc_yesterday = token_data["USDC"][1]

        # Prepare market summary for LLM
        market_summary = {
            "portfolio": {
                "total_value": f"${total_portfolio_value:,.2f}",
                "weth_percentage": f"{weth_percentage:.2f}%",
                "usdc_percentage": f"{usdc_percentage:.2f}%"
            },
            "market_data": {
                "weth": {
                    "current_price": f"${float(weth_latest['priceUSD']):.2f}",
                    "price_change": f"{((float(weth_latest['priceUSD']) - float(weth_yesterday['priceUSD'])) / float(weth_yesterday['priceUSD']) * 100):.2f}%",
                    "24h_volume": f"${float(weth_latest['volumeUSD']):,.2f}",
                    "volume_change": f"{((float(weth_latest['volumeUSD']) - float(weth_yesterday['volumeUSD'])) / float(weth_yesterday['volumeUSD']) * 100):.2f}%"
                }
            }
        }

        # Format market summary for prompt
        market_summary_str = json.dumps(market_summary, indent=2)

        # Construct LLM prompt
        prompt = f"""Based on the following portfolio and market data:
            {market_summary_str}

            Provide a single swap recommendation as JSON with two fields:
            1. 'action': specify direction (WETH to USDC or USDC to WETH) and percentage to swap (1-10%)
            2. 'reason': brief explanation in 10 words or less

            Response format example:
            {{
                "action": "swap 3% of weth to usdc",
                "reason": "decreasing volume suggests potential price decline"
        }}"""

        # Log prompt
        self.context.logger.info(f"Generated LLM Prompt:\n{prompt}")

        # Get LLM recommendation
        rebalance_decision = yield from self.get_llm_response(prompt)

        # Log decision
        self.context.logger.info(f"OpenAI Response: {rebalance_decision}")

        return rebalance_decision

    def get_token_price_specs(self, symbol) -> Generator[None, None, Optional[float]]:
        """
        Fetches current token price from CoinMarketCap API.
        
        Args:
            symbol (str): Token symbol to fetch price for
            
        Returns:
            Optional[float]: Current token price in USD, or None if request fails
        """
        # Get API specifications
        specs = self.coinmarketcap_specs.get_spec()
        specs["parameters"]["symbol"] = symbol

        # Make API request
        raw_response = yield from self.get_http_response(**specs)

        # Process response
        response = self.coinmarketcap_specs.process_response(raw_response)

        # Extract price from response
        token_data = response.get(symbol, {})
        price_info = token_data.get("quote", {}).get("USD", {})
        price = price_info.get("price", None)

        # Log result
        self.context.logger.info(f"Got token price from CoinMarketCap: {price}")

        return price

    def generate_and_store_report(self, token_values: str, total_portfolio_value: float, rebalancing_actions_json: str) -> Generator[None, None, Optional[str]]:
        """
        Generates a portfolio rebalancing report and stores it in IPFS.
        
        Args:
            token_values (str): JSON string of token values
            total_portfolio_value (float): Total portfolio value in USD
            rebalancing_actions_json (str): JSON string of rebalancing actions
            
        Returns:
            Optional[str]: IPFS hash of stored report, or None if storage fails
        """
        from datetime import datetime

        # Parse input JSON
        token_values_dict = json.loads(token_values)
        rebalancing_actions = json.loads(rebalancing_actions_json)

        # Calculate token allocation percentages
        token_percentages = {
            token: (value / total_portfolio_value) * 100 
            for token, value in token_values_dict.items()
        }

        # Generate report structure
        portfolio_report = {
            "timestamp": datetime.utcnow().isoformat(),
            "portfolio_status": {
                token: {
                    "value_usd": value,
                    "percentage": token_percentages[token]
                }
                for token, value in token_values_dict.items()
            },
            "total_portfolio_value": total_portfolio_value,
            "rebalancing_recommendation": {
                "action": rebalancing_actions["action"],
                "reason": rebalancing_actions["reason"]
            }
        }

        # Store report in IPFS
        self.context.logger.info("Storing portfolio report in IPFS...")
        report_ipfs_hash = yield from self.send_to_ipfs(
            filename="PortfolioRebalancer_Report.json",
            obj=portfolio_report,
            filetype=SupportedFiletype.JSON
        )

        # Log result
        if report_ipfs_hash:
            self.context.logger.info(f"Successfully stored portfolio report in IPFS with hash: {report_ipfs_hash}")
        else:
            self.context.logger.error("Failed to store portfolio report in IPFS")

        return report_ipfs_hash



class TxPreparationBehaviour(PortfolioManagerBaseBehaviour):
    """Behaviour responsible for preparing and submitting portfolio rebalancing transactions.
    
    This behaviour:
    1. Retrieves current token balances and adjustment instructions
    2. Calculates exact swap amounts based on percentage targets
    3. Prepares multisend transactions for both rebalancing and IPFS report storage
    4. Generates and submits the final Safe transaction hash
    """

    matching_round: Type[AbstractRound] = TxPreparationRound

    def async_act(self) -> Generator:
        """Execute the transaction preparation behaviour asynchronously."""

        with self.context.benchmark_tool.measure(self.behaviour_id).local():
            # Get key data from synchronized state
            sender = self.context.agent_address
            rebalancing_instructions = self.synchronized_data.adjustment_balances
            report_hash = self.synchronized_data.ipfs_hash
            
            self.context.logger.info(f"Processing rebalancing instructions: {rebalancing_instructions}")
            self.context.logger.info(f"Report IPFS hash: {report_hash}")

            # Fetch current portfolio state
            current_balances = yield from self.get_token_balances()
            if current_balances is None:
                self.context.logger.error("Failed to retrieve current token balances")
                return None

            # Log portfolio state
            self.context.logger.info("Current portfolio balances:")
            for token, amount in current_balances.items():
                self.context.logger.info(f"{token}: {amount}")

            # Process rebalancing instructions if present
            if rebalancing_instructions:
                rebalancing_data = json.loads(rebalancing_instructions)
                action = rebalancing_data.get('action', '')
                
                # Parse rebalancing action string (format: "swap X% of TOKEN_A to TOKEN_B")
                action_parts = action.split()
                try:
                    swap_percentage = float(action_parts[1].replace('%', ''))
                    source_token = action_parts[3].upper()  # Token to sell
                    target_token = action_parts[5].upper()  # Token to buy
                    
                    # Calculate exact swap amount
                    source_balance = current_balances.get(source_token)
                    if source_balance is None:
                        self.context.logger.error(f"Missing balance for source token: {source_token}")
                        return None
                        
                    swap_amount = source_balance * (swap_percentage / 100)
                    
                    # Log swap details
                    self.context.logger.info(
                        f"Swap details:\n"
                        f"- From: {source_token}\n"
                        f"- To: {target_token}\n"
                        f"- Amount: {swap_amount} {source_token}"
                    )

                    # Prepare rebalancing payload
                    rebalancing_payload = {
                        "source_token": source_token,
                        "target_token": target_token,
                        "amount": swap_amount,
                        "action": action,
                        "reason": "Rebalancing portfolio based on target allocation"
                    }

                except (IndexError, ValueError) as e:
                    self.context.logger.error(f"Failed to parse rebalancing action: {e}")
                    return None

                # Generate Safe transaction hash
                safe_tx_hash = yield from self.generate_multisend_transactions(
                    json.dumps(rebalancing_payload), 
                    report_hash
                )

            # Create and send transaction payload
            tx_payload = TxPreparationPayload(
                sender=sender,
                tx_submitter=self.auto_behaviour_id(),
                tx_hash=safe_tx_hash
            )
        
        # Submit payload and wait for consensus
        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            yield from self.send_a2a_transaction(tx_payload)
            yield from self.wait_until_round_end()

        self.set_done()

    def get_token_balances(self) -> Generator[None, None, Optional[Dict[str, float]]]:
        """
        Fetch current token balances from the portfolio contract.

        Returns:
            Dict mapping token symbols to their balances, or None if fetching fails
        """
        self.context.logger.info("Fetching current portfolio token balances")

        # Get contract addresses
        portfolio_address = self.params.portfolio_address_string
        manager_contract = self.params.portfolio_manager_contract_address_string

        # Define supported tokens and their properties
        supported_tokens = {
            "USDC": {"address": USDC_ADDRESS, "decimals": 6},
            "WETH": {"address": WETH_ADDRESS, "decimals": 18}
        }

        self.context.logger.info(
            f"Portfolio details:\n"
            f"- Address: {portfolio_address}\n"
            f"- Manager: {manager_contract}\n"
            f"- Tokens: {list(supported_tokens.keys())}"
        )

        # Extract token addresses in consistent order
        token_addresses = [token["address"] for token in supported_tokens.values()]
        token_symbols = list(supported_tokens.keys())

        # Fetch balances from contract
        response = yield from self.get_contract_api_response(
            performative=ContractApiMessage.Performative.GET_RAW_TRANSACTION,
            contract_address=manager_contract,
            contract_id=str(PORTFOLIOMANAGER.contract_id),
            contract_callable="get_user_balances",
            user=portfolio_address,
            tokens=token_addresses,
            chain_id=ETHEREUM_CHAIN_ID,
        )

        if response.performative != ContractApiMessage.Performative.RAW_TRANSACTION:
            self.context.logger.error(f"Failed to fetch balances: {response}")
            return None

        # Extract and validate balance data
        raw_balances = response.raw_transaction.body.get("balances")
        if raw_balances is None:
            self.context.logger.error("No balance data received")
            return None

        # Convert raw balances to human-readable format
        processed_balances = {}
        for symbol, raw_balance in zip(token_symbols, raw_balances):
            if raw_balance is not None:
                decimals = supported_tokens[symbol]["decimals"]
                human_readable = float(raw_balance) / (10 ** decimals)
                processed_balances[symbol] = human_readable
                self.context.logger.info(f"{symbol} balance: {human_readable}")
            else:
                self.context.logger.error(f"Missing balance for {symbol}")
                processed_balances[symbol] = None

        return processed_balances if processed_balances else None
    
    def get_adjust_balance_data(
        self, 
        user: str, 
        source_token: str, 
        amount_to_swap: float, 
        target_token: str
    ) -> Generator[None, None, Dict]:
        """
        Generate transaction data for portfolio rebalancing.

        Args:
            user: Portfolio address
            source_token: Token being sold
            amount_to_swap: Amount of source token to swap
            target_token: Token being purchased

        Returns:
            Dict containing transaction data for the rebalancing operation
        """
        # Get contract configuration
        manager_address = self.params.portfolio_manager_contract_address_string
        safe_address = self.params.safe_address

        # Token configuration
        token_config = {
            "USDC": {"address": USDC_ADDRESS, "decimals": 6},
            "WETH": {"address": WETH_ADDRESS, "decimals": 18}
        }

        # Convert amount to contract units
        source_decimals = token_config[source_token]["decimals"]
        amount_in_wei = int(amount_to_swap * (10 ** source_decimals))

        # Define swap parameters
        swap_params = [{
            "tokenToSell": token_config[source_token]["address"],
            "tokenToBuy": token_config[target_token]["address"],
            "amountToSell": amount_in_wei,
            "amountOutMin": 0,  # TODO: Add slippage protection
            "poolFee": 3000  # 0.3% fee tier
        }]

        self.context.logger.info(
            f"Preparing rebalance transaction:\n"
            f"- Manager: {manager_address}\n"
            f"- Portfolio: {user}\n"
            f"- Swap details: {swap_params}"
        )

        # Get transaction data
        response = yield from self.get_contract_api_response(
            performative=ContractApiMessage.Performative.GET_RAW_TRANSACTION,
            contract_address=manager_address,
            contract_id=str(PORTFOLIOMANAGER.contract_id),
            contract_callable="execute_rebalance",
            user=user,
            swaps=swap_params,
            chain_id=ETHEREUM_CHAIN_ID,
            from_address=safe_address,
        )

        if response.performative != ContractApiMessage.Performative.RAW_TRANSACTION:
            self.context.logger.error(f"Failed to generate rebalance transaction: {response}")
            return {}

        tx_data = response.raw_transaction.body.get("data")
        if tx_data is None:
            self.context.logger.error("Missing transaction data")
            return {}

        # Format transaction data
        formatted_data = {
            "to_address": manager_address,
            "data": bytes.fromhex(tx_data[2:] if tx_data.startswith("0x") else tx_data)
        }
        
        self.context.logger.info(f"Generated rebalance transaction: {formatted_data}")
        return formatted_data
    
    def get_set_ipfs_data(self, user: str, ipfs_hash: str) -> Generator[None, None, Dict]:
        """
        Generate transaction data for storing IPFS report hash.

        Args:
            user: Portfolio address
            ipfs_hash: IPFS hash of the rebalancing report

        Returns:
            Dict containing transaction data for IPFS hash storage
        """
        manager_address = self.params.portfolio_manager_contract_address_string
        safe_address = self.params.safe_address

        self.context.logger.info(
            f"Preparing IPFS storage transaction:\n"
            f"- Manager: {manager_address}\n"
            f"- Portfolio: {user}\n"
            f"- IPFS Hash: {ipfs_hash}"
        )

        # Get transaction data
        response = yield from self.get_contract_api_response(
            performative=ContractApiMessage.Performative.GET_RAW_TRANSACTION,
            contract_address=manager_address,
            contract_id=str(PORTFOLIOMANAGER.contract_id),
            contract_callable="store_report_hash",
            user=user,
            ipfs_hash=ipfs_hash,
            chain_id=ETHEREUM_CHAIN_ID,
            from_address=safe_address,
        )

        if response.performative != ContractApiMessage.Performative.RAW_TRANSACTION:
            self.context.logger.error(f"Failed to generate IPFS storage transaction: {response}")
            return {}

        tx_data = response.raw_transaction.body.get("data")
        if tx_data is None:
            self.context.logger.error("Missing transaction data")
            return {}

        # Format transaction data
        formatted_data = {
            "to_address": manager_address,
            "data": bytes.fromhex(tx_data[2:] if tx_data.startswith("0x") else tx_data)
        }

        self.context.logger.info(f"Generated IPFS storage transaction: {formatted_data}")
        return formatted_data
    
    def generate_multisend_transactions(
        self, 
        adjustment_balances_json: str, 
        ipfs_hash: Optional[str] = None
    ) -> Generator[None, None, Optional[str]]:
        """
        Generate a batched transaction combining rebalancing and IPFS storage operations.

        Args:
            adjustment_balances_json: JSON string containing rebalancing instructions
            ipfs_hash: Optional IPFS hash of the rebalancing report

        Returns:
            str: Safe transaction hash if successful, None otherwise
        """
        multisend_transactions = []
        adjustment_data = json.loads(adjustment_balances_json)
        portfolio_address = self.params.portfolio_address_string
        
        self.context.logger.info(
            f"Processing rebalancing request:\n"
            f"- Action: {adjustment_data['action']}\n"
            f"- Reason: {adjustment_data['reason']}"
        )

        # Generate rebalancing transaction
        rebalance_tx = yield from self.get_adjust_balance_data(
            user=portfolio_address,
            source_token=adjustment_data["source_token"],
            amount_to_swap=adjustment_data["amount"],
            target_token=adjustment_data["target_token"]
        )

        if not rebalance_tx:
            self.context.logger.error("Failed to generate rebalancing transaction")
            return None

        # Add rebalancing to batch
        multisend_transactions.append({
            "operation": MultiSendOperation.CALL,
            "to": rebalance_tx["to_address"],
            "data": rebalance_tx["data"],
            "value": ZERO_VALUE,
        })

        # Add IPFS storage if hash provided
        if ipfs_hash:
            ipfs_tx = yield from self.get_set_ipfs_data(
                user=portfolio_address,
                ipfs_hash=ipfs_hash
            )

            if not ipfs_tx:
                self.context.logger.error("Failed to generate IPFS storage transaction")
                return None

            multisend_transactions.append({
                "operation": MultiSendOperation.CALL,
                "to": ipfs_tx["to_address"],
                "data": ipfs_tx["data"],
                "value": ZERO_VALUE,
            })

        # Generate multisend transaction
        self.context.logger.info(f"Preparing batch of {len(multisend_transactions)} transactions")
        response = yield from self.get_contract_api_response(
            performative=ContractApiMessage.Performative.GET_RAW_TRANSACTION,
            contract_address=self.params.multisend_address,
            contract_id=str(MultiSendContract.contract_id),
            contract_callable="get_tx_data",
            multi_send_txs=multisend_transactions,
            chain_id=ETHEREUM_CHAIN_ID,
        )

        # Generate Safe transaction hash
        if response.performative != ContractApiMessage.Performative.RAW_TRANSACTION:
            self.context.logger.error("Failed to generate multisend transaction")
            return None

        multisend_data = response.raw_transaction.body["data"]
        data_bytes = bytes.fromhex(multisend_data[2:] if multisend_data.startswith("0x") else multisend_data)

        safe_tx_hash = yield from self._build_safe_tx_hash(
            to_address=self.params.multisend_address,
            value=ZERO_VALUE,
            data=data_bytes,
            operation=SafeOperation.DELEGATE_CALL.value,
        )

        if safe_tx_hash is None:
            self.context.logger.error("Failed to generate Safe transaction hash")
        else:
            self.context.logger.info(f"Generated Safe transaction hash: {safe_tx_hash}")

        return safe_tx_hash

    def _build_safe_tx_hash(
        self,
        to_address: str,
        value: int = ZERO_VALUE,
        data: bytes = EMPTY_CALL_DATA,
        operation: int = SafeOperation.CALL.value,
    ) -> Generator[None, None, Optional[str]]:
        """
        Generate a Safe transaction hash for the given parameters.

        Args:
            to_address: Destination contract address
            value: ETH value to send (default: 0)
            data: Transaction calldata (default: empty)
            operation: Safe operation type (default: CALL)

        Returns:
            str: Safe transaction hash if successful, None otherwise
        """
        self.context.logger.info(f"Generating Safe transaction hash for {to_address}")

        # Get raw transaction hash
        response = yield from self.get_contract_api_response(
            performative=ContractApiMessage.Performative.GET_STATE,
            contract_address=self.synchronized_data.safe_contract_address,
            contract_id=str(GnosisSafeContract.contract_id),
            contract_callable="get_raw_safe_transaction_hash",
            to_address=to_address,
            value=value,
            data=data,
            safe_tx_gas=SAFE_GAS,
            chain_id=ETHEREUM_CHAIN_ID,
            operation=operation,
        )

        if response.performative != ContractApiMessage.Performative.STATE:
            self.context.logger.error(
                f"Failed to get raw transaction hash. Expected STATE, got {response.performative}"
            )
            return None

        # Validate transaction hash
        tx_hash = response.state.body.get("tx_hash")
        if not tx_hash or len(tx_hash) != TX_HASH_LENGTH:
            self.context.logger.error(f"Invalid transaction hash: {tx_hash}")
            return None

        # Generate final Safe transaction hash
        safe_tx_hash = hash_payload_to_hex(
            safe_tx_hash=tx_hash[2:],  # Remove 0x prefix
            ether_value=value,
            safe_tx_gas=SAFE_GAS,
            to_address=to_address,
            data=data,
            operation=operation,
        )

        self.context.logger.info(f"Generated Safe transaction hash: {safe_tx_hash}")
        return safe_tx_hash


class PortfolioManagerRoundBehaviour(AbstractRoundBehaviour):
    """PortfolioManagerRoundBehaviour"""

    initial_behaviour_cls = DataPullBehaviour
    abci_app_cls = PortfolioManagerAbciApp  # type: ignore
    behaviours: Set[Type[BaseBehaviour]] = [
        DataPullBehaviour,
        DecisionMakingBehaviour,
        TxPreparationBehaviour
    ]
