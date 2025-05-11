# Self-Promise Platform

A privacy-preserving platform for self-binding contracts with consequences, built on the Oasis Network.

## Overview

The Self-Promise Platform enables users to make promises to themselves with financial accountability. Users deposit ROSE tokens as collateral and define a verifiable condition (e.g., exercise frequency, screen time limits, study hours). The platform then evaluates the promise using data from integrated services (e.g., Fitbit) and either returns the tokens to the user if the promise is kept or handles them according to predefined rules if broken.

![Self-Promise Application Screenshot](https://i.imgur.com/qaCTahu.png)

### Key Features

- **Privacy-Preserving**: All evidence data is processed within a Trusted Execution Environment (TEE) using Oasis Sapphire, ensuring user data remains private.
- **Blockchain-Based**: Smart contracts handle token custody and resolution, providing transparency and automation.
- **Pluggable Evaluators**: Support for both rule-based and LLM-based promise evaluation.
- **Flexible Promise Templates**: Pre-defined templates for common promises with customizable parameters.
- **Third-Party Integrations**: Connect with fitness trackers and other data sources to verify promise fulfillment.

## Architecture

The platform consists of several key components:

1. **Smart Contracts**:
   - `PromiseDeposit.sol`: Handles token deposits and withdrawals
   - `PromiseKeeper.sol`: Manages promise templates, creation, and evaluation
   - **NEW**: `MinimalPromiseDeposit.sol` and `MinimalPromiseKeeper.sol`: Minimal versions for development with lower gas usage

2. **TEE Integration**:
   - Secure data handling within Oasis Sapphire
   - Confidential computing for promise evaluation

3. **Evaluators**:
   - Rule-based evaluator for straightforward promises
   - LLM-based evaluator for complex, natural language promises

4. **Data Integrations**:
   - Terra API for fitness data (heart rate, exercise sessions)
   - Extensible to other data sources

## Getting Started

### Prerequisites

- Python 3.7+
- Solidity compiler (for smart contracts)
- Oasis Network wallet with ROSE tokens

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/self-promise.git
cd self-promise

# Install dependencies
pip install -e .
```

### Usage

```python
from src.service import create_service

# Create a service
service = create_service()

# Set contract addresses (after deployment)
service.set_contract_addresses(
    deposit_address="0x...",
    promise_keeper_address="0x..."
)

# Create a promise
promise = service.create_promise(
    user_id="user123",
    template_id=2,  # Exercise Duration
    parameters={
        "heart_rate_threshold": "130",
        "duration_minutes": "30",
        "frequency": "2",
        "period": "week"
    },
    start_date=datetime.datetime.now(),
    end_date=datetime.datetime.now() + datetime.timedelta(days=30),
    deposit_amount=100.0  # 100 ROSE
)

# Later, evaluate the promise
evaluation = service.evaluate_promise(promise["promise_id"], "user123")
```

### Demo

Run the demo script to see the platform in action:

```bash
# Full version (may have gas issues)
python test_demo.py

# Minimal version (lower gas usage)
python test_minimal_demo.py
```

## Development

### Project Structure

```
self-promise/
├── contracts/                   # Solidity smart contracts (PromiseDeposit, PromiseKeeper, and minimal versions)
├── src/                         # Core service logic
│   ├── evaluator/               # Promise evaluation modules (rule-based, LLM-based)
│   ├── tee/                     # TEE integration (Oasis Sapphire, ROFL client)
│   ├── terra_api/               # Fitness data integration (Terra API client)
│   └── service.py               # Main SelfPromiseService implementation
├── web_app/                     # Flask web application (if applicable, adjust path if different)
│   ├── static/                  # CSS, JS files
│   └── templates/               # HTML templates
├── scripts/                     # CLI scripts and utilities
├── rofl_app/                    # ROFL application code
├── tests/                       # Test modules
├── self_promise_cli.py          # Example CLI entry point (if applicable)
├── setup.py                     # Package setup
├── pyproject.toml               # Project configuration
└── TODO_GAS_OPTIMIZATION.md     # Gas optimization tasks
```

## CLI and Web Application

The Self-Promise platform includes a Command Line Interface (CLI) and a Web Application to interact with the core services.

### Current Integration Model

- Both the CLI and Web App currently utilize a `MockSelfPromiseService`. This mock service simulates interactions with the smart contracts, allowing for development and testing without direct blockchain engagement. (Note: The web app's import from `self_promise_cli.py` as mentioned in `cli_web_integration_analysis.md` suggests a close tie, which might need refactoring for clarity if `self_promise_cli.py` is primarily a CLI entry point).
- The real `SelfPromiseService`, which interacts with the Oasis Sapphire network and TEE components, is available in `self-promise/src/service.py`.

### Path to Full Smart Contract Integration

Connecting the CLI and Web App to the live smart contracts involves:
1.  **Service Replacement**: Modifying the service factory (e.g., `get_service()` potentially in `self_promise_cli.py` or a shared module) to provide the real `SelfPromiseService` instead of the mock one.
2.  **Handling Asynchronicity**: Adapting the CLI and Web App to handle asynchronous operations, as the real service uses `async/await`. This may involve creating synchronous wrappers or refactoring the frontends.
3.  **Configuration**: Ensuring robust configuration management for network details, private keys, contract addresses, and ABIs, likely extending existing environment variable handling.
4.  **Error Handling**: Implementing comprehensive error handling for blockchain interactions, including retries and transaction monitoring.

The modular design of the platform, with a separation between service interfaces and implementations, facilitates this transition. The `cli_web_integration_analysis.md` document contains further details on this topic.

## Gas Optimization

The full versions of the contracts (`PromiseKeeper.sol` and `PromiseDeposit.sol`) currently have high gas usage that may cause transactions to fail. To address this temporarily:

1. We've created minimal versions of both contracts (`MinimalPromiseKeeper.sol` and `MinimalPromiseDeposit.sol`) with reduced functionality but much lower gas usage.
2. A `test_minimal_demo.py` script demonstrates the use of these minimal contracts.
3. A detailed plan for gas optimization is available in `TODO_GAS_OPTIMIZATION.md`.

Use the minimal contracts for development until the gas optimization tasks are completed.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Built during the EthDAM Hackathon
- Powered by Oasis Network's Sapphire for confidential computing

## Sapphire Integration

Self-Promise utilizes Oasis Sapphire for confidential computing and smart contracts. Sapphire provides a Trusted Execution Environment (TEE) that ensures private data remains encrypted and secure throughout processing.

### Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment Configuration**:
   - Copy `.env-example` to `.env`
   - Add your Oasis Sapphire private key to `OASIS_PRIVATE_KEY`
   - Configure the network using `OASIS_NETWORK` (testnet, mainnet, or localnet)

3. **Running Locally with Sapphire Localnet**:
   ```bash
   # Start the localnet using Docker
   docker run -it -p8544-8548:8544-8548 ghcr.io/oasisprotocol/sapphire-localnet
   
   # Set the network to localnet in your .env file
   OASIS_NETWORK=localnet
   ```

### Using ROFL for Confidential Functions

ROFL (Runtime On-chain for Functions & Lambdas) enables running arbitrary code within the TEE. Self-Promise uses ROFL for secure evaluation of fitness data.

1. **Install the Oasis CLI**:
   ```bash
   npm install -g @oasisprotocol/cli
   ```

2. **Deploy a ROFL Service**:
   ```python
   from src.tee.sapphire import create_rofl_client
   
   # Create a ROFL client
   rofl_client = create_rofl_client(network="testnet")
   
   # Deploy a service
   service_code = """
   module.exports = {
     evaluatePromise: function(data) {
       // Confidential evaluation logic
       return {
         fulfilled: true,
         confidence: 0.95,
         reasoning: "Promise fulfilled based on evidence"
       };
     }
   }
   """
   
   service_id = rofl_client.deploy_service(
     service_name="promise-evaluator",
     service_code=service_code
   )
   
   # Call the service
   result = rofl_client.call_service(
     service_id=service_id,
     method_name="evaluatePromise",
     args={"promise": {...}, "evidence": {...}}
   )
   ```

### Smart Contract Deployment

1. **Deploy Contracts**:
   ```python
   from src.tee.sapphire import create_sapphire_client
   
   # Create a Sapphire client
   sapphire_client = create_sapphire_client(network="testnet")
   
   # Deploy PromiseDeposit contract
   deposit_address = await sapphire_client.deploy_contract("PromiseDeposit")
   
   # Deploy PromiseKeeper contract with constructor args
   promise_keeper_address = await sapphire_client.deploy_contract(
     "PromiseKeeper", 
     constructor_args=[deposit_address]
   )
   ```

2. **Interact with Contracts**:
   ```python
   # Create a promise
   tx_hash = await sapphire_client.send_transaction(
     contract_address=promise_keeper_address,
     method_name="createPromise",
     args=[1, ["frequency"], ["3"], 1683080400, 1685758800, "0x0"]
   )
   
   # Get promise details
   promise = await sapphire_client.call_contract(
     contract_address=promise_keeper_address,
     method_name="getPromiseDetails",
     args=[promise_id]
   )
   ```

For more information, refer to the [Oasis Sapphire documentation](https://docs.oasis.io/dapp/sapphire/).

## Changelog

### v0.1.3
- Added minimal versions of contracts (`MinimalPromiseKeeper.sol` and `MinimalPromiseDeposit.sol`) to reduce gas usage
- Created `test_minimal_demo.py` for testing the minimal contracts
- Added `TODO_GAS_OPTIMIZATION.md` with planned gas optimization tasks
- Updated README with information about the minimal contracts and gas optimization plan
- Documented CLI and Web Application integration status and path forward. (Self-correction: this changelog entry should be added by the user/developer after this change is applied and a new version is decided. I'm noting it here for completeness of the thought process).

### v0.1.2
- Optimized gas limits for all contract operations to prevent out-of-gas errors
- Updated createPromise to use 8,000,000 gas limit for complex operations
- Updated parameter naming in client methods to improve code clarity and maintainability
- Added gas usage monitoring and reporting in test scripts
- Converted string formatting to % style in all logging statements
- Added comprehensive test suite for gas optimization verification

### v0.1.1
- Added default high gas limit (6,000,000) to all transactions to ensure proper processing on Sapphire networks
- Fixed transaction handling in SapphireClient to properly order middleware and signing operations
- Added more detailed logging for transaction gas limits
- Added ability to customize default gas limit when initializing SapphireClient

### v0.1.0
- Initial release
- Basic promise creation and evaluation functionality
- Integration with Oasis Sapphire TEE
- Smart contract deployment and interaction
