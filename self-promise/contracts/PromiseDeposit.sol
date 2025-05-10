// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

/**
 * @title PromiseDeposit
 * @dev Contract for handling ROSE token deposits for self-promises
 */
contract PromiseDeposit {
    // Address of the PromiseKeeper contract
    address public promiseKeeperAddress;
    
    // Owner of the contract
    address public owner;
    
    // Mapping from user address to deposit amount
    mapping(address => uint256) public deposits;
    
    // Mapping from user address to promise ID
    mapping(address => bytes32) public userPromises;
    
    // Events
    event DepositReceived(address indexed user, uint256 amount, bytes32 promiseId);
    event PromiseResolved(address indexed user, bytes32 indexed promiseId, bool fulfilled, uint256 amount);
    event PromiseKeeperUpdated(address indexed oldAddress, address indexed newAddress);
    
    /**
     * @dev Constructor
     */
    constructor() {
        owner = msg.sender;
    }
    
    /**
     * @dev Modifier to restrict function access to the owner
     */
    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can call this function");
        _;
    }
    
    /**
     * @dev Modifier to restrict function access to the PromiseKeeper contract
     */
    modifier onlyPromiseKeeper() {
        require(msg.sender == promiseKeeperAddress, "Only PromiseKeeper can call this function");
        _;
    }
    
    /**
     * @dev Set the address of the PromiseKeeper contract
     * @param _promiseKeeperAddress The address of the PromiseKeeper contract
     */
    function setPromiseKeeper(address _promiseKeeperAddress) external onlyOwner {
        address oldAddress = promiseKeeperAddress;
        promiseKeeperAddress = _promiseKeeperAddress;
        emit PromiseKeeperUpdated(oldAddress, _promiseKeeperAddress);
    }
    
    /**
     * @dev Deposit ROSE tokens for a promise
     * @param promiseId The ID of the promise
     */
    function deposit(bytes32 promiseId) external payable {
        require(msg.value > 0, "Deposit amount must be greater than 0");
        require(deposits[msg.sender] == 0, "User already has an active deposit");
        
        deposits[msg.sender] = msg.value;
        userPromises[msg.sender] = promiseId;
        
        emit DepositReceived(msg.sender, msg.value, promiseId);
    }
    
    /**
     * @dev Resolve a promise (called by the PromiseKeeper contract)
     * @param user The address of the user
     * @param fulfilled Whether the promise was fulfilled
     * @param recipient The address to send the tokens to if the promise was not fulfilled
     */
    function resolvePromise(address user, bool fulfilled, address recipient) external onlyPromiseKeeper {
        uint256 amount = deposits[user];
        require(amount > 0, "No deposit found for user");
        
        bytes32 promiseId = userPromises[user];
        
        // Clear the deposit and promise
        deposits[user] = 0;
        userPromises[user] = bytes32(0);
        
        // Transfer the tokens based on whether the promise was fulfilled
        if (fulfilled) {
            // Return the tokens to the user
            (bool success, ) = user.call{value: amount}("");
            require(success, "Transfer to user failed");
        } else {
            // Send the tokens to the recipient (burn address or charity)
            (bool success, ) = recipient.call{value: amount}("");
            require(success, "Transfer to recipient failed");
        }
        
        emit PromiseResolved(user, promiseId, fulfilled, amount);
    }
    
    /**
     * @dev Get the deposit amount for a user
     * @param user The address of the user
     * @return The deposit amount
     */
    function getDeposit(address user) external view returns (uint256) {
        return deposits[user];
    }
    
    /**
     * @dev Get the promise ID for a user
     * @param user The address of the user
     * @return The promise ID
     */
    function getPromiseId(address user) external view returns (bytes32) {
        return userPromises[user];
    }
    
    /**
     * @dev Check if a user has an active deposit
     * @param user The address of the user
     * @return Whether the user has an active deposit
     */
    function hasActiveDeposit(address user) external view returns (bool) {
        return deposits[user] > 0;
    }
}
