# AI Portfolio Manager Website

This is the web interface for the AI Portfolio Manager, built with Flask and modern web technologies.

## Directory Structure

```
website/
├── app.py              # Main Flask application
├── blockchain.py       # Blockchain interaction utilities
├── contracts/          # Smart contract ABIs and addresses
├── templates/          # HTML templates
│   └── index.html     # Main application interface
└── .env               # Environment configuration
```

## Features

- 🔐 Web3 Authentication with MetaMask
- 💼 Portfolio Management Interface
- 📊 Real-time Portfolio Analytics
- 💱 Token Deposits and Withdrawals
- 📈 Performance Tracking
- 🤖 AI-Driven Strategy Selection

## Setup

1. **Python Dependencies**
   ```bash
   pip install Flask web3 python-dotenv requests
   ```

2. **Environment Configuration**
   ```bash
   cp sample.env .env
   ```
   Edit `.env` with your configuration (see Environment Variables section below)

3. **Run the Website**
   ```bash
   cd website
   python app.py
   ```

4. **Access the Website**
   - Open your browser and navigate to `http://localhost:5000`
   - Connect your MetaMask wallet
   - Start managing your portfolio!

## Environment Variables

Required environment variables in `.env`:

- `PORTFOLIO_MANAGER_ADDRESS`: Address of the deployed Portfolio Manager contract
- `USDC_ADDRESS`: USDC token contract address
- `WETH_ADDRESS`: WETH token contract address
- `RPC_URL`: Ethereum RPC URL (e.g., Tenderly fork)
- `COINMARKETCAP_API_KEY`: API key for CoinMarketCap price data

## API Endpoints

- `/`: Main application interface
- `/api/balances`: Get user token balances
- `/api/approve_and_deposit`: Handle token deposits
- `/api/withdraw`: Handle token withdrawals
- `/api/reports`: Get AI agent reports

## Development

The website uses:
- Flask for the backend API
- Vanilla JavaScript for frontend logic
- Modern CSS with CSS variables for theming
- Chart.js for portfolio visualizations
- Web3.js for blockchain interactions
- MetaMask for wallet connection

## Smart Contract Integration

The website interacts with:
- Portfolio Manager Contract: Main contract for managing user portfolios
- ERC20 Tokens: USDC and WETH for deposits/withdrawals

The Portfolio Manager smart contract itself interacts with:
- Uniswap V3: For executing token swaps during portfolio rebalancing

## Security Notes

- Never commit `.env` file with sensitive data
- Always use checksummed addresses
- Validate all user inputs
- Use safe math operations for token amounts
- Implement proper error handling for failed transactions