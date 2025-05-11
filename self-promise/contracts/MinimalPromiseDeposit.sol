// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

/**
 * @title MinimalPromiseDeposit
 * @dev Minimal version of PromiseDeposit with reduced gas consumption
 * TODO: Replace with full implementation when gas optimizations are completed
 */
contract MinimalPromiseDeposit {
    // Owner of the contract
    address public owner;
    
    // Mapping from user address to deposit amount
    mapping(address => uint256) public deposits;
    
    // Events
    event DepositReceived(address indexed user, uint256 amount);
    event PromiseResolved(address indexed user, bool fulfilled, uint256 amount);
    
    /**
     * @dev Constructor
     */
    constructor() {
        owner = msg.sender;
    }
    
    /**
     * @dev Deposit ROSE tokens
     */
    function deposit() external payable {
        require(msg.value > 0, "Deposit amount must be greater than 0");
        
        deposits[msg.sender] = msg.value;
        
        emit DepositReceived(msg.sender, msg.value);
    }
    
    /**
     * @dev Resolve a promise (simplified for minimal gas usage)
     * @param user The address of the user
     * @param fulfilled Whether the promise was fulfilled
     */
    function resolvePromise(address user, bool fulfilled) external {
        require(msg.sender == owner, "Only owner can resolve promises");
        
        uint256 amount = deposits[user];
        require(amount > 0, "No deposit found for user");
        
        // Clear the deposit
        deposits[user] = 0;
        
        // Transfer the tokens based on whether the promise was fulfilled
        if (fulfilled) {
            // Return the tokens to the user
            (bool success, ) = user.call{value: amount}("");
            require(success, "Transfer to user failed");
        } else {
            // Send the tokens to a burn address
            address burnAddress = 0x000000000000000000000000000000000000dEaD;
            (bool success, ) = burnAddress.call{value: amount}("");
            require(success, "Transfer to burn address failed");
        }
        
        emit PromiseResolved(user, fulfilled, amount);
    }
    
    /**
     * @dev Get the deposit amount for a user
     * @param user The address of the user
     * @return The deposit amount
     */
    function getDeposit(address user) external view returns (uint256) {
        return deposits[user];
    }
} 