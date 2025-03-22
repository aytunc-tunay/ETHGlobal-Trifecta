// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import '@uniswap/v3-periphery/contracts/libraries/TransferHelper.sol';
import '@uniswap/v3-periphery/contracts/interfaces/ISwapRouter.sol';
// 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2 weth 1000000000000000000
// 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48 usdc 1000000
// 0xE592427A0AEce92De3Edee1F18E0157C05861564 swap router
// 0x35c72A4ebcbEa3E90F3885493FB54FB896B56689 safe

contract AgenticEthereumPortfolioManager {
    struct SwapParams {
        address tokenToSell;
        address tokenToBuy;
        uint256 amountToSell;
        uint256 amountOutMin;
        uint24 poolFee;
    }

    struct UserPortfolio {
        mapping(address => uint256) balances; // User balances per token
        address[] tokens;                     // List of tokens the user has interacted with
        mapping(address => bool) tokenExists; // Prevent duplicate entries
        bool registered;                      // Registration flag
        string[] ipfsReports;                 // Report IPFS hashes (max 10; oldest removed when adding new)
    }

    address public safeAddress; // Safe Address controlled by agents
    ISwapRouter public immutable swapRouter; // Uniswap V3 Router
    
    mapping(address => UserPortfolio) public portfolios; // Mapping of user portfolios

    constructor(address _safeAddress, ISwapRouter _swapRouter) {
        safeAddress = _safeAddress;
        swapRouter = _swapRouter;
    }

    modifier onlySafe() {
        require(msg.sender == safeAddress, "Not authorized");
        _;
    }

    function deposit(address token, uint256 amount) external {
        require(amount > 0, "Amount must be > 0");
        UserPortfolio storage portfolio = portfolios[msg.sender];

        if (!portfolio.registered) {
            portfolio.registered = true;
        }

        TransferHelper.safeTransferFrom(token, msg.sender, address(this), amount);

        if (!portfolio.tokenExists[token]) {
            portfolio.tokens.push(token);
            portfolio.tokenExists[token] = true;
        }

        portfolio.balances[token] += amount;
    }

    function withdraw(address token, uint256 amount) external {
        UserPortfolio storage portfolio = portfolios[msg.sender];
        require(portfolio.registered, "User not registered");
        require(amount > 0, "Amount must be > 0");
        require(portfolio.balances[token] >= amount, "Insufficient balance");

        portfolio.balances[token] -= amount;
        TransferHelper.safeTransfer(token, msg.sender, amount);
    }

    function checkAllowance(address token, address user) external view returns (uint256) {
        return IERC20(token).allowance(user, address(this));
    }

    function getUserBalances(address user, address[] calldata tokens) external view returns (uint256[] memory) {
        require(portfolios[user].registered, "User not registered");
        uint256[] memory balances = new uint256[](tokens.length);
        for (uint256 i = 0; i < tokens.length; i++) {
            balances[i] = portfolios[user].balances[tokens[i]];
        }
        return balances;
    }

    function executeRebalance(address user, SwapParams[] calldata swaps) external onlySafe {
        require(portfolios[user].registered, "User not registered");
        for (uint256 i = 0; i < swaps.length; i++) {
            _processSwap(user, swaps[i]);
        }
    }

    function _processSwap(address user, SwapParams calldata params) internal {
        UserPortfolio storage portfolio = portfolios[user];
        require(portfolio.balances[params.tokenToSell] >= params.amountToSell, "Insufficient balance");

        TransferHelper.safeApprove(params.tokenToSell, address(swapRouter), 0);
        TransferHelper.safeApprove(params.tokenToSell, address(swapRouter), params.amountToSell);

        ISwapRouter.ExactInputSingleParams memory swapParams = ISwapRouter.ExactInputSingleParams({
            tokenIn: params.tokenToSell,
            tokenOut: params.tokenToBuy,
            fee: params.poolFee,
            recipient: address(this),
            deadline: block.timestamp,
            amountIn: params.amountToSell,
            amountOutMinimum: params.amountOutMin,
            sqrtPriceLimitX96: 0
        });
        uint256 amountOut = swapRouter.exactInputSingle(swapParams);

        portfolio.balances[params.tokenToSell] -= params.amountToSell;
        if (!portfolio.tokenExists[params.tokenToBuy]) {
            portfolio.tokens.push(params.tokenToBuy);
            portfolio.tokenExists[params.tokenToBuy] = true;
        }
        portfolio.balances[params.tokenToBuy] += amountOut;
    }
}
