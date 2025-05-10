# Self-Promise Platform Architecture

## System Architecture

```mermaid
graph TD
    User[User] -->|Makes Promise| UI[User Interface]
    UI -->|Creates Promise| Service[Self-Promise Service]
    
    subgraph "Smart Contracts (Blockchain)"
        PromiseDeposit[PromiseDeposit Contract]
        PromiseKeeper[PromiseKeeper Contract]
    end
    
    Service -->|Deposits Tokens| PromiseDeposit
    Service -->|Creates/Evaluates Promise| PromiseKeeper
    PromiseKeeper -->|Resolves Deposit| PromiseDeposit
    
    subgraph "Trusted Execution Environment (TEE)"
        SecureDataHandler[Secure Data Handler]
        Evaluator[Promise Evaluator]
    end
    
    Service -->|Processes Data Securely| SecureDataHandler
    SecureDataHandler -->|Evaluates Promise| Evaluator
    
    subgraph "Data Sources"
        TerraAPI[Terra API]
    end
    
    Service -->|Fetches Fitness Data| TerraAPI
    
    Evaluator -->|Returns Evaluation| Service
    Service -->|Returns Result| UI
    UI -->|Shows Result| User
```

## Data Flow

```mermaid
sequenceDiagram
    participant User
    participant UI as User Interface
    participant Service as Self-Promise Service
    participant TerraAPI as Terra API
    participant TEE as Trusted Execution Environment
    participant Contracts as Smart Contracts
    
    User->>UI: Create Promise
    UI->>Service: Submit Promise Details
    Service->>Contracts: Create Promise & Deposit Tokens
    Contracts-->>Service: Promise Created
    Service-->>UI: Confirmation
    UI-->>User: Promise Active
    
    Note over User,Contracts: Time passes...
    
    Service->>TerraAPI: Fetch Fitness Data
    TerraAPI-->>Service: Return Fitness Data
    Service->>TEE: Evaluate Promise with Data
    TEE-->>Service: Evaluation Result
    Service->>Contracts: Submit Evaluation
    Contracts->>Contracts: Resolve Promise
    Contracts-->>Service: Promise Resolved
    Service-->>UI: Show Result
    UI-->>User: Promise Result
```

## Component Relationships

```mermaid
classDiagram
    class SelfPromiseService {
        +create_promise()
        +evaluate_promise()
        +get_promise_status()
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
        +evaluatePromise()
        +resolvePromise()
    }
    
    SelfPromiseService --> TerraApiClient: uses
    SelfPromiseService --> EvaluatorInterface: uses
    SelfPromiseService --> SapphireClient: uses
    SelfPromiseService --> SecureDataHandler: uses
    
    EvaluatorInterface <|-- RuleBasedEvaluator: implements
    EvaluatorInterface <|-- LLMEvaluator: implements
    
    SapphireClient --> PromiseDeposit: interacts with
    SapphireClient --> PromiseKeeper: interacts with
    
    PromiseKeeper --> PromiseDeposit: calls
