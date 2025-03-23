# ETHGlobal-Trifecta

An AI-powered portfolio management service built with Autonolas agents.

## System Requirements

- Python `>=3.10`
- [Tendermint](https://docs.tendermint.com/v0.34/introduction/install.html) `==0.34.19`
- [IPFS node](https://docs.ipfs.io/install/command-line/#official-distributions) `==0.6.0`
- [Poetry](https://python-poetry.org/docs/#installation)
- [Docker Engine](https://docs.docker.com/engine/install/)
- [Docker Compose](https://docs.docker.com/compose/install/)
- [Set Docker permissions so you can run containers as non-root user](https://docs.docker.com/engine/install/linux-postinstall/)

## Run Your Own Agent

### Get the Code

1. Clone this repo:
    ```
    git clone git@github.com:aytunc-tunay/ETHGlobal-Trifecta.git
    ```

2. Create and activate the virtual environment:
    ```
    cd ETHGlobal-Trifecta
    poetry shell
    poetry install
    ```

3. Sync packages:
    ```
    autonomy packages sync --update-packages
    ```

### Prepare the Data

1. Generate keys for the agents:
    ```
    autonomy generate-key ethereum -n 4
    ```

2. Create `ethereum_private_key.txt` with one of the private keys (no newline at end).

3. Deploy [Safe on Ethereum mainnet](https://app.safe.global/welcome) with your agent addresses as signers.

4. Create a [Tenderly](https://tenderly.co/) fork of Ethereum mainnet.

You can explore transactions of the agent on Tenderly at: https://virtual.mainnet.rpc.tenderly.co/d681c2c4-12e5-4a78-ac2d-87544ad925c6

5. Fund your agents and Safe with ETH.

6. Copy and configure environment:
    ```
    cp sample.env .env
    ```

### Environment Variables

Autonolas agent service `.env`:
```
ALL_PARTICIPANTS='["0x4D552eeEb484A38235cDd5923438BaEF838a68A0"]'
SAFE_CONTRACT_ADDRESS=0x38245ec8f8C326152045b578132349Ebbf7a3Fb6
SAFE_CONTRACT_ADDRESS_SINGLE=0xAde2bd82cDc6662bdE8e4FDE5E727B97B2408047
ETHEREUM_LEDGER_RPC=https://virtual.mainnet.rpc.tenderly.co/api-key
COINMARKETCAP_API_KEY=xxx
THEGRAPH_API_KEY=xxx
OPENAI_API_KEY=xxx         # Required if LLM_SELECTION=openai
NILLION_API_KEY=xxx        # Required if LLM_SELECTION=nillion
TRANSFER_TARGET_ADDRESS=0x4D552eeEb484A38235cDd5923438BaEF838a68A0
PORTFOLIO_MANAGER_CONTRACT_ADDRESS=0xDA9Cd60AfB4AEAf448Cbbd1c60D839592Cdbd43D
LLM_SELECTION=nillion      # Choose 'openai' or 'nillion' for AI analysis
PORTFOLIO_ADDRESS=0x4D552eeEb484A38235cDd5923438BaEF838a68A0

ON_CHAIN_SERVICE_ID=1
RESET_PAUSE_DURATION=100
RESET_TENDERMINT_AFTER=10
```

### Run a Single Agent Locally

1. Verify `ALL_PARTICIPANTS` contains only 1 address.
2. Run:
    ```
    bash run_agent.sh
    ```

### Run Multiple Agents

1. Verify `ALL_PARTICIPANTS` contains 4 agent addresses.

2. Run the service:
    ```
    bash service.sh
    ```

This will start 4 agents running in Docker containers to form a complete autonomous service. The agents will coordinate using consensus to manage the portfolio.

The service.sh script will be provided soon. This will enable running a full service with 4 agents for production use cases.

## AI Model Selection

The portfolio manager service can use either OpenAI or Nillion for AI-powered analysis and decision making:

- **OpenAI**: Uses GPT-4 for portfolio analysis and rebalancing recommendations
- **Nillion**: Uses Llama 3.1 (8B) for secure, private computation of financial analysis

To select which AI provider to use, set the `LLM_SELECTION` environment variable to either `openai` or `nillion` and ensure you have provided the corresponding API key.

## Tools Used

- [Autonolas](https://olas.network/) - Autonomous service framework
- [TheGraph](https://thegraph.com/) - Blockchain data indexing
- [Safe](https://app.safe.global/) - Multisig wallet
- [Tenderly](https://tenderly.co/) - Development environment
- [Uniswap V3](https://docs.uniswap.org/contracts/v3/reference/deployments/) - DEX integration
- [Nillion](https://docs.nillion.com/api/nilai/overview) - Secure computation for AI analysis
- [OpenAI](https://openai.com/) - Advanced language models for portfolio recommendations

## Project Structure

```
ETHGlobal-Trifecta/
├── packages/                # Autonolas packages
├── scripts/                 # Utility scripts
├── website/                 # Frontend web interface
├── pyproject.toml           # Python project dependencies
├── README.md                # This documentation
├── run_agent.sh             # Agent runner script
└── sample.env               # Template for environment variables
```