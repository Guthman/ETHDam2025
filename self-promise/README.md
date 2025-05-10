# Self-Promise Platform

A privacy-preserving platform for self-binding contracts with consequences, built on the Oasis Network.

## Overview

The Self-Promise Platform enables users to make promises to themselves with financial accountability. Users deposit ROSE tokens as collateral and define a verifiable condition (e.g., exercise frequency, screen time limits, study hours). The platform then evaluates the promise using data from integrated services (e.g., Fitbit) and either returns the tokens to the user if the promise is kept or handles them according to predefined rules if broken.

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
python test_demo.py
```

## Development

### Project Structure

```
self-promise/
├── contracts/                # Solidity smart contracts
│   ├── PromiseDeposit.sol    # Token deposit contract
│   └── PromiseKeeper.sol     # Promise management contract
├── src/
│   ├── evaluator/            # Promise evaluation modules
│   │   ├── interface.py      # Evaluator interface
│   │   ├── rule_based.py     # Rule-based evaluator
│   │   └── llm_based.py      # LLM-based evaluator
│   ├── terra_api/            # Fitness data integration
│   │   └── client.py         # Terra API client
│   ├── tee/                  # TEE integration
│   │   └── sapphire.py       # Oasis Sapphire integration
│   └── service.py            # Main service module
├── tests/                    # Test modules
├── setup.py                  # Package setup
└── pyproject.toml            # Project configuration
```

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
