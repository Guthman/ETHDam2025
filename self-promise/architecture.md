# Self-Promise Platform Architecture

## System Architecture

```mermaid
graph TD
    User[User] -->|Interacts via| CLI[CLI (Command Line Interface)]
    CLI -->|Invokes locally| Service[Self-Promise Service]
    
    subgraph "Oasis Sapphire TEE (Blockchain)"
        PromiseDeposit[PromiseDeposit Contract]
        PromiseKeeper[PromiseKeeper Contract]
    end
    
    Service -->|Signs & Sends Tx| PromiseDeposit
    Service -->|Signs & Sends Tx| PromiseKeeper
    PromiseKeeper -->|Resolves Deposit| PromiseDeposit
    
    subgraph "ROFL TEE (Off-Chain Confidential Compute)"
        RoflPromiseEvaluator[ROFL Promise Evaluator]
    end
    
    Service -->|Sends Promise ID, Evidence| RoflPromiseEvaluator
    RoflPromiseEvaluator -->|Calls updatePromiseEvaluationByRofl with TEE-verified identity| PromiseKeeper
    
    subgraph "Data Sources"
        FitnessGadget[User's Fitness Gadget Data]
    end
    
    User -->|Exports data| FitnessGadget
    FitnessGadget -->|Data supplied via CLI| Service
    
    RoflPromiseEvaluator -->|Returns result (via blockchain update)| Service
    Service -->|Reads status from blockchain| CLI
    CLI -->|Displays result| User
```

## Data Flow

```mermaid
sequenceDiagram
    participant User
    participant CLI
    participant Service as Self-Promise Service (local)
    participant RoflTEE as ROFL Promise Evaluator
    participant SapphireContracts as Smart Contracts (PromiseKeeper & PromiseDeposit)

    User->>CLI: 1. Setup: Configure .env with OASIS_PRIVATE_KEY

    User->>CLI: 2. create-promise (content, deposit)
    CLI->>Service: Prepare promise creation transaction
    Service->>SapphireContracts: PromiseKeeper.createPromise() & PromiseDeposit.deposit()
    Note right of Service: Signed with User's Private Key locally
    SapphireContracts-->>Service: Confirmation (Promise ID)
    Service-->>CLI: Display Promise ID
    CLI-->>User: Promise created (content confidential)

    Note over User,SapphireContracts: Time passes, user gathers evidence...

    User->>CLI: 3. submit-evidence --promise-id X --evidence Y
    CLI->>Service: Prepare evidence submission
    Service->>RoflTEE: call_service("evaluatePromise", {promise_id, evidence_data})
    Note right of Service: Evidence sent to ROFL TEE
    RoflTEE->>RoflTEE: 4. Confidential Evaluation (evidence & logic private)
    RoflTEE->>SapphireContracts: PromiseKeeper.updatePromiseEvaluationByRofl()
    Note right of RoflTEE: Sapphire verifies ROFL origin using roflEnsureAuthorizedOrigin
    SapphireContracts-->>RoflTEE: Confirmation
    RoflTEE-->>Service: Evaluation call acknowledged
    Service-->>CLI: Evidence submitted for evaluation
    CLI-->>User: Evaluation in progress

    User->>CLI: 5. status --promise-id X
    CLI->>Service: Get promise status
    Service->>SapphireContracts: PromiseKeeper.getPromiseDetails() (confidential query)
    SapphireContracts-->>Service: Current Promise Status
    Service-->>CLI: Display status
    CLI-->>User: Shows "Fulfilled" / "Failed" / etc.

    alt Promise Kept (Status: Fulfilled)
        User->>CLI: 6. withdraw --promise-id X
        CLI->>Service: Prepare withdrawal transaction
        Service->>SapphireContracts: PromiseKeeper.resolvePromise()
        Note right of Service: Signed with User's Private Key
        SapphireContracts->>User: Transfers ROSE back
        SapphireContracts-->>Service: Confirmation
        Service-->>CLI: Withdrawal successful
        CLI-->>User: Funds returned
    else Promise Broken (Status: Failed)
        User->>CLI: 7. withdraw --promise-id X (or automated resolution)
        CLI->>Service: Prepare resolution transaction
        Service->>SapphireContracts: PromiseKeeper.resolvePromise()
        Note right of Service: Signed with User's Private Key
        SapphireContracts->>SapphireContracts: Transfers ROSE to burn address
        SapphireContracts-->>Service: Confirmation
        Service-->>CLI: Promise resolved (funds burned)
        CLI-->>User: Funds handled as per rules
    end
```

## Component Relationships

```mermaid
classDiagram
    direction LR
    class CLI {
      +main()
      +create_promise_command()
      +submit_evidence_command()
      +status_command()
      +withdraw_command()
    }

    class SelfPromiseService {
        +create_promise()
        +submit_evidence_for_evaluation()
        +get_promise_status()
        +withdraw_collateral()
        +load_config()
    }

    class TerraApiClient {
        +get_heart_rate_data()
        +get_exercise_sessions()
        +check_continuous_elevated_heart_rate()
    }

    class EvaluatorInterface {
        <<interface>>
        +evaluate()
    }

    class RuleBasedEvaluator {
        +evaluate()
    }

    class LLMEvaluator {
        +evaluate()
    }

    class SapphireClient {
        +deploy_contract()
        +call_contract()
        +send_transaction()
    }

    class RoflClient {
        +deploy_service()
        +call_service()
    }

    class SecureDataHandler {
        +encrypt_data()
        +decrypt_data()
        +secure_compute()
    }

    class PromiseDeposit {
        +deposit()
        +resolvePromise()
    }

    class PromiseKeeper {
        +createPromise()
        +updatePromiseEvaluationByRofl() /* Called by ROFL TEE, verified with roflEnsureAuthorizedOrigin */
        +getPromiseDetails()
        +resolvePromise()
    }

    class RoflPromiseEvaluatorInstance {
        <<ROFL TEE Service>>
        +evaluatePromise(promise_id, evidence_data)
        # internally uses SapphireClient to update PromiseKeeper
    }

    CLI --> SelfPromiseService: uses
    SelfPromiseService --> TerraApiClient: uses
    SelfPromiseService --> EvaluatorInterface: uses
    SelfPromiseService --> SapphireClient: uses
    SelfPromiseService --> RoflClient: uses
    SelfPromiseService --> SecureDataHandler: uses
    
    EvaluatorInterface <|-- RuleBasedEvaluator: implements
    EvaluatorInterface <|-- LLMEvaluator: implements
    
    SapphireClient ..> PromiseDeposit: interacts with
    SapphireClient ..> PromiseKeeper: interacts with
    
    RoflClient ..> RoflPromiseEvaluatorInstance: calls

    RoflPromiseEvaluatorInstance ..> PromiseKeeper: updates with verified TEE identity
    PromiseKeeper ..> PromiseDeposit: calls
```

## User Privacy & Security Flow

```mermaid
graph TD
    subgraph "User's Computer"
        CLI[CLI Tool]
        PrivateKey[Private Key in .env]
        PromiseData[Promise Content]
        EvidenceData[Evidence Data]
    end

    subgraph "Oasis Sapphire (Privacy Layer)"
        Encryption[Encrypt Transaction Data]
        TEEContracts[Contracts Execute in TEE]
    end

    subgraph "ROFL TEE (Confidential Compute)"
        SecureEvaluation[Evidence Evaluation]
        ROFLIdentity[ROFL TEE Identity]
    end

    subgraph "Blockchain State (Public)"
        WalletAddress[User's Wallet Address]
        PromiseExistence[Promise Existence]
        PromiseStatus[Promise Status]
    end

    CLI -->|Local signing| PrivateKey
    PrivateKey -->|Signs Tx| CLI
    CLI -->|Submit Promise| Encryption
    PromiseData -->|Input to Tx| Encryption
    
    Encryption -->|Encrypted Data| TEEContracts
    TEEContracts -->|Record Existence| PromiseExistence
    TEEContracts -->|Associate with| WalletAddress
    
    CLI -->|Submit Evidence| ROFL TEE
    EvidenceData -->|Input to| SecureEvaluation
    
    SecureEvaluation -->|Result| ROFLIdentity
    ROFLIdentity -->|Verified Update| TEEContracts
    TEEContracts -->|Update| PromiseStatus
    
    classDef private fill:#f9f,stroke:#333,stroke-width:2px;
    classDef encrypted fill:#bbf,stroke:#333,stroke-width:2px;
    classDef public fill:#bfb,stroke:#333,stroke-width:2px;
    
    class PrivateKey,PromiseData,EvidenceData private;
    class Encryption,TEEContracts,SecureEvaluation,ROFLIdentity encrypted;
    class WalletAddress,PromiseExistence,PromiseStatus public;
```

## Privacy & Security Features

1. **User Privacy**
   - User identity is only their public wallet address
   - Promise content and parameters are encrypted on-chain (Sapphire TEE)
   - Evidence data is processed only within ROFL TEE
   - Private key never leaves user's device

2. **Cryptographic Guarantees**
   - Transaction data to Sapphire is encrypted in transit and at rest
   - Smart contracts execute within Sapphire TEE
   - Evidence evaluation occurs within ROFL TEE
   - ROFL-to-Sapphire communication is cryptographically verified via `roflEnsureAuthorizedOrigin`

3. **Verified Evaluation Flow**
   - User evidence is sent to ROFL TEE
   - ROFL evaluates evidence confidentially
   - ROFL signs result with its TEE identity
   - Sapphire verifies ROFL identity before accepting updates
   - This ensures no one can spoof evaluation results
