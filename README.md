## ⚠️ Note for ETHGlobal Judges

This repository was flagged for having too many lines changed in a single commit ([see check failure](https://github.com/aytunc-tunay/ETHGlobal-Trifecta/commit/339d06ea78545e4dfee002efa47e82f073e8c334)). This is expected and intentional - the large initial commit is due to using the Autonolas FSM App scaffold tool which auto-generates the necessary boilerplate code and project structure.

The scaffold tool creates based on FSM (Finite State Machine) specifications:
- Base class templates
- Required handlers and behaviors
- Standard project structure

This scaffolding approach is standard practice when building on Autonolas, as it ensures consistent architecture and best practices. The generated code provides the foundation that we then customized for our specific use case.

For more details on the FSM App scaffolding process, please see the [Autonolas documentation](https://docs.olas.network/open-autonomy/guides/code_fsm_app_skill/).



# ETHGlobal-Trifecta

An advanced, decentralized portfolio management platform that combines AI, secure smart contracts, and multi-agent coordination to optimize DeFi investments. Built on Autonolas, the system features a user-friendly Agent Marketplace where investors can choose from diverse strategies—each powered by a dedicated Agent configured with its own risk tolerance, rebalancing frequency, or asset focus. Once subscribed, users deposit their tokens into a specialized portfolio manager contract, secured by a Gnosis Safe multisig to ensure only the authorized Agent can initiate transactions.

On the back end, each Agent continuously runs off-chain, gathering real-time market data, historical performance metrics, and user-specific information. This consolidated dataset is passed to an LLM—via either Nillion or OpenAI—to produce detailed recommendations for token swaps and portfolio adjustments, which are then executed through Uniswap V3. All actions are documented and published on IPFS, giving users transparent logs of every trade and the rationale behind it.

By leveraging the consensus capabilities of Open Autonomy, the project coordinates multiple Agents without relying on a central server, creating a trust-minimized environment. A pruned Tendermint-based blockchain underpins the Agents’ internal agreement on states and events. Because the system enforces multisig approvals for each on-chain operation, security is bolstered against any single point of failure. Tenderly-forked Ethereum environments enable thorough testing in near-production conditions, ensuring reliability and safety before mainnet deployment.

Overall, this project aims to simplify DeFi portfolio management through AI-driven automation, while maintaining transparency and user control. Investors retain the flexibility to withdraw at any time and can review each Agent’s performance and decision-making processes in real time. With its modular, extensible design, this platform can easily accommodate new LLMs or additional Agent strategies, providing a future-proof solution for autonomous, AI-powered DeFi optimization.


[Project Page with Demo](https://ethglobal.com/showcase/ai-portfolio-maestro-xkhzf)


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
├── fsm_specification.yaml   # Finite state machine specification for the agent
├── pyproject.toml           # Python project dependencies
├── README.md                # This documentation
├── run_agent.sh             # Agent runner script
└── sample.env               # Template for environment variables
```




