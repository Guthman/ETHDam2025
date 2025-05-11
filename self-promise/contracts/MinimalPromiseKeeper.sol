// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

// Create an interface for MinimalPromiseDeposit instead of importing
interface IMinimalPromiseDeposit {
    function resolvePromise(address user, bool fulfilled) external;
}

/**
 * @title MinimalPromiseKeeper
 * @dev Minimal version of PromiseKeeper with reduced gas consumption
 * TODO: Replace with full implementation when gas optimizations are completed
 */
contract MinimalPromiseKeeper {
    // Address of the MinimalPromiseDeposit contract
    address public depositContractAddress;
    
    // Owner of the contract
    address public owner;
    
    // Address of the authorized ROFL application
    address public authorizedRoflApp;
    
    // Minimal Promise struct
    struct Promise {
        bytes32 id;
        address owner;
        bool resolved;
        bool fulfilled;
    }
    
    // Mappings
    mapping(bytes32 => Promise) public promises;
    
    // Events
    event PromiseCreated(bytes32 indexed promiseId, address indexed owner);
    event PromiseResolved(bytes32 indexed promiseId, bool fulfilled);
    event DepositContractUpdated(address indexed oldAddress, address indexed newAddress);
    event AuthorizedRoflAppUpdated(address indexed oldAddress, address indexed newAddress);
    event PromiseResultReceived(
        bytes32 indexed promiseId,
        bool fulfilled,
        string reasoning,
        address indexed roflAppAddress // msg.sender of the ROFL app call
    );
    
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
     * @dev Set the address of the authorized ROFL application
     * @param _roflAppAddress The address of the ROFL application
     */
    function setAuthorizedRoflApp(address _roflAppAddress) external onlyOwner {
        address oldAddress = authorizedRoflApp;
        authorizedRoflApp = _roflAppAddress;
        emit AuthorizedRoflAppUpdated(oldAddress, _roflAppAddress);
    }
    
    /**
     * @dev Set the address of the MinimalPromiseDeposit contract
     * @param _depositContractAddress The address of the MinimalPromiseDeposit contract
     */
    function setDepositContract(address _depositContractAddress) external onlyOwner {
        address oldAddress = depositContractAddress;
        depositContractAddress = _depositContractAddress;
        emit DepositContractUpdated(oldAddress, _depositContractAddress);
    }
    
    /**
     * @dev Create a minimal promise
     * @return The ID of the created promise
     */
    function createPromise() external returns (bytes32) {
        // Generate a unique promise ID
        bytes32 promiseId = keccak256(abi.encodePacked(
            msg.sender,
            block.timestamp
        ));
        
        Promise storage newPromise = promises[promiseId];
        newPromise.id = promiseId;
        newPromise.owner = msg.sender;
        newPromise.resolved = false;
        newPromise.fulfilled = false;
        
        emit PromiseCreated(promiseId, msg.sender);
        
        return promiseId;
    }
    
    /**
     * @dev Resolve a promise
     * @param promiseId The ID of the promise to resolve
     * @param fulfilled Whether the promise was fulfilled
     */
    function resolvePromise(bytes32 promiseId, bool fulfilled) external onlyOwner {
        Promise storage userPromise = promises[promiseId];
        require(userPromise.owner != address(0), "Promise does not exist");
        require(!userPromise.resolved, "Promise already resolved");
        
        // Mark the promise as resolved
        userPromise.resolved = true;
        userPromise.fulfilled = fulfilled;
        
        // Resolve the deposit
        if (depositContractAddress != address(0)) {
            IMinimalPromiseDeposit depositContract = IMinimalPromiseDeposit(depositContractAddress);
            depositContract.resolvePromise(userPromise.owner, fulfilled);
        }
        
        emit PromiseResolved(promiseId, fulfilled);
    }
    
    /**
     * @dev Called by the ROFL application to submit an evaluation result.
     * For now, only an authorized ROFL app can call this.
     * TEE attestation verification will be added later.
     * @param promiseId The ID of the promise being evaluated
     * @param fulfilled Whether the promise was fulfilled based on ROFL evaluation
     * @param reasoning A string explaining the evaluation outcome
     */
    function submitEvaluationResult(
        bytes32 promiseId,
        bool fulfilled,
        string calldata reasoning
        // bytes calldata attestation // Placeholder for TEE attestation data
    ) external {
        require(msg.sender == authorizedRoflApp, "Only authorized ROFL app can submit results");
        Promise storage userPromise = promises[promiseId];
        require(userPromise.owner != address(0), "Promise does not exist");
        require(!userPromise.resolved, "Promise already resolved"); // Or handle re-evaluation if needed

        // Update promise state based on ROFL evaluation
        // For this minimal version, we'll directly use the ROFL's decision.
        // In a more complex scenario, you might have more nuanced state updates.
        userPromise.resolved = true; 
        userPromise.fulfilled = fulfilled;

        // Call the deposit contract to release/slash funds
        if (depositContractAddress != address(0)) {
            IMinimalPromiseDeposit depositContract = IMinimalPromiseDeposit(depositContractAddress);
            // Pass the original promise owner and the ROFL's fulfillment status
            depositContract.resolvePromise(userPromise.owner, fulfilled); 
        }

        emit PromiseResultReceived(promiseId, fulfilled, reasoning, msg.sender);
        // Also emit the existing PromiseResolved event for consistency if other parts of your system use it.
        // However, this might be redundant if PromiseResultReceived is sufficient.
        // For now, let's assume PromiseResultReceived is the primary event for ROFL-driven resolution.
        // If resolvePromise is intended to be called by others (e.g. owner for manual resolution)
        // then the logic here and in resolvePromise might need to be harmonized.
        // For MVP, let's keep them separate and ROFL uses submitEvaluationResult.
    }
    
    /**
     * @dev Get promise details
     * @param promiseId The ID of the promise
     * @return The promise details: owner, resolved status, fulfilled status
     */
    function getPromiseDetails(bytes32 promiseId) external view returns (
        address,
        bool,
        bool
    ) {
        Promise storage userPromise = promises[promiseId];
        require(userPromise.owner != address(0), "Promise does not exist");
        
        return (
            userPromise.owner,
            userPromise.resolved,
            userPromise.fulfilled
        );
    }
} 