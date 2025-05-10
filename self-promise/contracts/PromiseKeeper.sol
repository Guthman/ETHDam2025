// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

import "./PromiseDeposit.sol";

/**
 * @title PromiseKeeper
 * @dev Confidential contract for managing promises and evaluations
 * This contract is designed to run on Oasis Sapphire for confidential computing
 */
contract PromiseKeeper {
    // Address of the PromiseDeposit contract
    address public depositContractAddress;
    
    // Owner of the contract
    address public owner;
    
    // Burn address for failed promises (if no specific recipient is provided)
    address public constant BURN_ADDRESS = 0x000000000000000000000000000000000000dEaD;
    
    // Promise template struct
    struct PromiseTemplate {
        uint256 id;
        string name;
        string description;
        string promiseType;  // e.g., "exercise_frequency", "exercise_duration"
        mapping(string => string) defaultParameters;  // Default parameters for the template
        bool active;
    }
    
    // Promise struct
    struct Promise {
        bytes32 id;
        address owner;
        uint256 templateId;
        string promiseType;
        mapping(string => string) parameters;
        uint256 startDate;
        uint256 endDate;
        address failureRecipient;  // Where tokens go if promise fails
        bool resolved;
        bool fulfilled;
    }
    
    // Evaluation result struct
    struct EvaluationResult {
        bytes32 promiseId;
        bool fulfilled;
        uint256 confidence;
        string reasoning;
        uint256 timestamp;
    }
    
    // Mappings
    mapping(uint256 => PromiseTemplate) public promiseTemplates;
    mapping(bytes32 => Promise) public promises;
    mapping(bytes32 => EvaluationResult) public evaluationResults;
    
    // Counters
    uint256 public nextTemplateId;
    
    // Events
    event TemplateCreated(uint256 indexed templateId, string name, string promiseType);
    event PromiseCreated(bytes32 indexed promiseId, address indexed owner, uint256 templateId);
    event PromiseEvaluated(bytes32 indexed promiseId, bool fulfilled, uint256 confidence);
    event PromiseResolved(bytes32 indexed promiseId, bool fulfilled);
    event DepositContractUpdated(address indexed oldAddress, address indexed newAddress);
    
    /**
     * @dev Constructor
     */
    constructor() {
        owner = msg.sender;
        nextTemplateId = 1;
        
        // Initialize with some default templates
        _createDefaultTemplates();
    }
    
    /**
     * @dev Modifier to restrict function access to the owner
     */
    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can call this function");
        _;
    }
    
    /**
     * @dev Set the address of the PromiseDeposit contract
     * @param _depositContractAddress The address of the PromiseDeposit contract
     */
    function setDepositContract(address _depositContractAddress) external onlyOwner {
        address oldAddress = depositContractAddress;
        depositContractAddress = _depositContractAddress;
        emit DepositContractUpdated(oldAddress, _depositContractAddress);
    }
    
    /**
     * @dev Create a new promise template
     * @param name The name of the template
     * @param description The description of the template
     * @param promiseType The type of promise
     * @param paramKeys The keys for default parameters for the template
     * @param paramValues The values for default parameters for the template
     * @return The ID of the created template
     */
    function createTemplate(
        string calldata name,
        string calldata description,
        string calldata promiseType,
        string[] calldata paramKeys,
        string[] calldata paramValues
    ) external onlyOwner returns (uint256) {
        require(paramKeys.length == paramValues.length, "Parameter keys and values must have the same length");
        
        uint256 templateId = nextTemplateId++;
        PromiseTemplate storage template = promiseTemplates[templateId];
        
        template.id = templateId;
        template.name = name;
        template.description = description;
        template.promiseType = promiseType;
        template.active = true;
        
        // Set default parameters
        for (uint256 i = 0; i < paramKeys.length; i++) {
            template.defaultParameters[paramKeys[i]] = paramValues[i];
        }
        
        emit TemplateCreated(templateId, name, promiseType);
        
        return templateId;
    }
    
    /**
     * @dev Create a new promise from a template
     * @param templateId The ID of the template to use
     * @param paramKeys The parameter keys to override
     * @param paramValues The parameter values to override
     * @param startDate The start date of the promise (Unix timestamp)
     * @param endDate The end date of the promise (Unix timestamp)
     * @param failureRecipient The address to send tokens to if the promise fails
     * @return The ID of the created promise
     */
    function createPromise(
        uint256 templateId,
        string[] calldata paramKeys,
        string[] calldata paramValues,
        uint256 startDate,
        uint256 endDate,
        address failureRecipient
    ) external returns (bytes32) {
        require(promiseTemplates[templateId].active, "Template does not exist or is inactive");
        require(paramKeys.length == paramValues.length, "Parameter keys and values must have the same length");
        require(startDate < endDate, "Start date must be before end date");
        
        // Generate a unique promise ID
        bytes32 promiseId = keccak256(abi.encodePacked(
            msg.sender,
            templateId,
            startDate,
            endDate,
            block.timestamp
        ));
        
        Promise storage retrievedPromise = promises[promiseId];
        
        retrievedPromise.id = promiseId;
        retrievedPromise.owner = msg.sender;
        retrievedPromise.templateId = templateId;
        retrievedPromise.promiseType = promiseTemplates[templateId].promiseType;
        retrievedPromise.startDate = startDate;
        retrievedPromise.endDate = endDate;
        retrievedPromise.failureRecipient = failureRecipient == address(0) ? BURN_ADDRESS : failureRecipient;
        retrievedPromise.resolved = false;
        retrievedPromise.fulfilled = false;
        
        // Copy default parameters from template
        // Note: In Solidity, we can't iterate over mappings, so this would need to be
        // implemented differently in a real contract. For simplicity, we'll just
        // set the parameters provided by the user.
        
        // Set custom parameters
        for (uint256 i = 0; i < paramKeys.length; i++) {
            retrievedPromise.parameters[paramKeys[i]] = paramValues[i];
        }
        
        emit PromiseCreated(promiseId, msg.sender, templateId);
        
        return promiseId;
    }
    
    /**
     * @dev Evaluate a promise (called by an authorized evaluator)
     * @param promiseId The ID of the promise to evaluate
     * @param fulfilled Whether the promise was fulfilled
     * @param confidence The confidence level of the evaluation (0-100)
     * @param reasoning The reasoning behind the evaluation
     */
    function evaluatePromise(
        bytes32 promiseId,
        bool fulfilled,
        uint256 confidence,
        string calldata reasoning
    ) external {
        // In a real implementation, this would be restricted to authorized evaluators
        // For the MVP, we'll allow anyone to call it
        
        Promise storage retrievedPromise = promises[promiseId];
        require(retrievedPromise.owner != address(0), "Promise does not exist");
        require(!retrievedPromise.resolved, "Promise already resolved");
        
        // Store the evaluation result
        evaluationResults[promiseId] = EvaluationResult({
            promiseId: promiseId,
            fulfilled: fulfilled,
            confidence: confidence,
            reasoning: reasoning,
            timestamp: block.timestamp
        });
        
        emit PromiseEvaluated(promiseId, fulfilled, confidence);
    }
    
    /**
     * @dev Resolve a promise based on its evaluation
     * @param promiseId The ID of the promise to resolve
     */
    function resolvePromise(bytes32 promiseId) external {
        Promise storage retrievedPromise = promises[promiseId];
        require(retrievedPromise.owner != address(0), "Promise does not exist");
        require(!retrievedPromise.resolved, "Promise already resolved");
        
        EvaluationResult storage result = evaluationResults[promiseId];
        require(result.timestamp > 0, "Promise has not been evaluated");
        
        // Mark the promise as resolved
        retrievedPromise.resolved = true;
        retrievedPromise.fulfilled = result.fulfilled;
        
        // Resolve the deposit
        if (depositContractAddress != address(0)) {
            PromiseDeposit depositContract = PromiseDeposit(depositContractAddress);
            depositContract.resolvePromise(
                retrievedPromise.owner,
                result.fulfilled,
                retrievedPromise.failureRecipient
            );
        }
        
        emit PromiseResolved(promiseId, result.fulfilled);
    }
    
    /**
     * @dev Get promise details
     * @param promiseId The ID of the promise
     * @return owner The owner of the promise
     * @return templateId The template ID of the promise
     * @return promiseType The type of promise
     * @return startDate The start date of the promise
     * @return endDate The end date of the promise
     * @return resolved Whether the promise has been resolved
     * @return fulfilled Whether the promise was fulfilled
     */
    function getPromiseDetails(bytes32 promiseId) external view returns (
        address owner,
        uint256 templateId,
        string memory promiseType,
        uint256 startDate,
        uint256 endDate,
        bool resolved,
        bool fulfilled
    ) {
        Promise storage retrievedPromise = promises[promiseId];
        require(retrievedPromise.owner != address(0), "Promise does not exist");
        
        return (
            retrievedPromise.owner,
            retrievedPromise.templateId,
            retrievedPromise.promiseType,
            retrievedPromise.startDate,
            retrievedPromise.endDate,
            retrievedPromise.resolved,
            retrievedPromise.fulfilled
        );
    }
    
    /**
     * @dev Get evaluation result
     * @param promiseId The ID of the promise
     * @return fulfilled Whether the promise was fulfilled
     * @return confidence The confidence level of the evaluation
     * @return reasoning The reasoning behind the evaluation
     * @return timestamp The timestamp of the evaluation
     */
    function getEvaluationResult(bytes32 promiseId) external view returns (
        bool fulfilled,
        uint256 confidence,
        string memory reasoning,
        uint256 timestamp
    ) {
        EvaluationResult storage result = evaluationResults[promiseId];
        require(result.timestamp > 0, "Promise has not been evaluated");
        
        return (
            result.fulfilled,
            result.confidence,
            result.reasoning,
            result.timestamp
        );
    }
    
    /**
     * @dev Get promise parameter
     * @param promiseId The ID of the promise
     * @param key The parameter key
     * @return The parameter value
     */
    function getPromiseParameter(bytes32 promiseId, string calldata key) external view returns (string memory) {
        Promise storage retrievedPromise = promises[promiseId];
        require(retrievedPromise.owner != address(0), "Promise does not exist");
        
        return retrievedPromise.parameters[key];
    }
    
    /**
     * @dev Create default templates
     * This is a private function called by the constructor
     */
    function _createDefaultTemplates() private {
        // Template 1: Exercise Frequency
        uint256 templateId = nextTemplateId++;
        PromiseTemplate storage template1 = promiseTemplates[templateId];
        
        template1.id = templateId;
        template1.name = "Exercise Frequency";
        template1.description = "Promise to exercise a certain number of times per period";
        template1.promiseType = "exercise_frequency";
        template1.active = true;
        
        template1.defaultParameters["frequency"] = "3";  // 3 times
        template1.defaultParameters["period"] = "week";  // per week
        
        emit TemplateCreated(templateId, template1.name, template1.promiseType);
        
        // Template 2: Exercise Duration
        templateId = nextTemplateId++;
        PromiseTemplate storage template2 = promiseTemplates[templateId];
        
        template2.id = templateId;
        template2.name = "Exercise Duration";
        template2.description = "Promise to exercise with elevated heart rate for a minimum duration";
        template2.promiseType = "exercise_duration";
        template2.active = true;
        
        template2.defaultParameters["heart_rate_threshold"] = "120";  // 120 bpm
        template2.defaultParameters["duration_minutes"] = "25";  // 25 minutes
        template2.defaultParameters["frequency"] = "1";  // 1 time
        template2.defaultParameters["period"] = "week";  // per week
        
        emit TemplateCreated(templateId, template2.name, template2.promiseType);
        
        // Template 3: Exercise Consistency
        templateId = nextTemplateId++;
        PromiseTemplate storage template3 = promiseTemplates[templateId];
        
        template3.id = templateId;
        template3.name = "Exercise Consistency";
        template3.description = "Promise to never go more than a certain number of days without exercise";
        template3.promiseType = "exercise_consistency";
        template3.active = true;
        
        template3.defaultParameters["max_gap_days"] = "7";  // 7 days
        
        emit TemplateCreated(templateId, template3.name, template3.promiseType);
    }
}
