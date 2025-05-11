# Self-Promise Platform: User Journey

This document describes the user experience and data flow through the Self-Promise platform, demonstrating how users can create and fulfill promises while maintaining privacy and security.

## Meet Alex: A User Story

Alex is a software developer who wants to improve their fitness. They have a goal to exercise regularly but struggle with consistency. Alex decides to use the Self-Promise platform to create a financial incentive for themselves.

### Setup: Getting Started

1. **Installation & Configuration**

   Alex begins by downloading the Self-Promise CLI tool from the official repository. After installation, Alex needs to configure their environment:

   ```bash
   # Create and edit .env file with private key
   cp .env-example .env
   nano .env   # Add OASIS_PRIVATE_KEY and set OASIS_NETWORK
   ```

   Alex already has an Oasis wallet with ROSE tokens. They copy their wallet's private key into the `.env` file. This private key never leaves Alex's computer—it will only be used locally to sign transactions.

   What's happening under the hood:
   - The CLI tool loads the contract addresses from `deployed_addresses.json`, which identifies the smart contracts and ROFL service deployed by the Self-Promise team.
   - The private key stays on Alex's machine, providing cryptographic proof of their identity while maintaining anonymity.

2. **Understanding the Privacy Model**

   Before proceeding, Alex reads about how their data will be protected:
   
   - Their identity is only known as their wallet address—no personal information is required.
   - The content of their promise and its parameters will be encrypted on the Oasis Sapphire blockchain.
   - Evidence data they submit will only be processed within a Trusted Execution Environment.
   - No one, not even the service operators, can see the details of their promise or their evidence data.

### Creating a Promise: Commitment with Privacy and Automation

Alex decides to make a promise to themselves: "I will achieve an average heart rate of 130bpm for at least 30 continuous minutes, 3 times per week, for the next 2 weeks."

1. **Connecting a Fitness Tracker**

   First, Alex connects their fitness tracker:

   ```bash
   self-promise connect-tracker --provider fitbit
   ```

   The CLI opens a browser window with the FitBit consent screen. Alex logs in and grants the Self-Promise application permission to access their activity and heart rate data.
   
   What's happening under the hood:
   - For the MVP, the actual OAuth flow is mocked, but in a production environment:
     - The CLI would initiate the OAuth flow by opening the FitBit authorization URL
     - After user consent, FitBit would redirect to the callback URL with an authorization code
     - The CLI would exchange this code for access and refresh tokens
     - These tokens would be securely stored locally for future API calls
   - The CLI stores mock tokens in the user's configuration directory

2. **Formulating the Promise with Automated Evidence Collection**

   Alex opens their terminal and enters:

   ```bash
   self-promise create-promise \
       --template-id 2 \
       --parameters '{"heart_rate_threshold": "130", "duration_minutes": "30", "frequency": "3", "period": "week"}' \
       --start-date "2024-07-29" \
       --end-date "2024-08-11" \
       --deposit-amount 50.0 \
       --auto-evidence
   ```

   What's happening under the hood:
   - The CLI parses these arguments and calls the local Self-Promise Service library.
   - It checks for connected fitness trackers and confirms automatic evidence collection.
   - The service prepares transactions as before, but now includes a flag indicating this promise will use automated evidence.
   - The transactions are signed locally using Alex's private key and sent to Oasis Sapphire.

3. **Confirmation and Promise ID**

   The terminal displays:

   ```
   Promise created successfully!
   Promise ID: 123
   Your promise details are confidentially stored on the Oasis Sapphire network.
   Your fitness data will be automatically collected and evaluated at the end date.
   Transaction hash: 0xabc...xyz
   ```

   Alex notes down their Promise ID: 123, knowing they won't need to manually submit evidence.

### Living the Promise: Real-World Activity with Automated Tracking

Over the next two weeks, Alex exercises regularly, using their fitness tracker to monitor their heart rate. Unlike the manual process, they don't need to export or submit any data themselves.

1. **Automatic Evidence Collection (Simulation for MVP)**

   When the promise end date arrives, Alex can trigger the automatic evaluation:

   ```bash
   self-promise trigger-auto-evaluation --promise-id 123
   ```

   What's happening under the hood:
   - For the MVP, this command simulates the automatic collection process that would normally happen in the background
   - The CLI retrieves mock fitness data (simulating a call to the FitBit API)
   - The service sends this data to the ROFL Promise Evaluator, just as with manual submission
   - The evaluation proceeds through the ROFL TEE as before, with `roflEnsureAuthorizedOrigin()` verification
   - In a production environment, this could be triggered by a scheduler or when the user checks status after the end date

   The terminal displays:

   ```
   Retrieving fitness data for promise 123...
   Sending fitness data to ROFL TEE service for evaluation...
   Automatic evaluation triggered successfully!
   Use 'self-promise status --promise-id 123' to check the evaluation results.
   ```

   The rest of the flow (checking status and withdrawal) remains the same as in the manual process.

### Checking Results and Resolution

1. **Checking the Promise Status**

   After giving the evaluation some time to process, Alex checks the status:

   ```bash
   self-promise status --promise-id 123
   ```

   What's happening under the hood:
   - The CLI calls the Self-Promise Service to query the `PromiseKeeper` smart contract.
   - The service sends a confidential query to `PromiseKeeper.getPromiseDetails(123)`.
   - The contract, running in Sapphire TEE, returns the current status.

   The terminal displays:

   ```
   Promise ID: 123
   Status: Fulfilled
   Evaluation Details: All 6 workout sessions met the criteria. Promise requirements satisfied.
   Deposit Amount: 50.0 ROSE
   ```

   Alex is pleased to see they've met their promise!

2. **Completing the Process: Getting Their Deposit Back**

   Now that the promise is fulfilled, Alex can get their deposit back:

   ```bash
   self-promise withdraw --promise-id 123
   ```

   What's happening under the hood:
   - The CLI calls the Self-Promise Service to prepare a transaction to `PromiseKeeper.resolvePromise(123)`.
   - This transaction is signed locally with Alex's private key.
   - When the Sapphire blockchain processes this:
     1. The `PromiseKeeper` contract, running in TEE, checks the promise status (Fulfilled).
     2. It instructs the `PromiseDeposit` contract to return the 50 ROSE to Alex's wallet.
     3. The funds are transferred back to Alex.

   The terminal displays:

   ```
   Withdrawal successful!
   50.0 ROSE has been returned to your wallet.
   Transaction hash: 0xdef...uvw
   ```

   Alex receives their 50 ROSE back in their wallet, rewarding them for keeping their promise.

### Alternative Scenario: If Alex Hadn't Kept Their Promise

If Alex had missed their exercise targets and the promise was evaluated as "Failed":

1. When checking status, they would see:

   ```
   Promise ID: 123
   Status: Failed
   Evaluation Details: Only 4 workout sessions met the criteria. Required 6 sessions.
   Deposit Amount: 50.0 ROSE
   ```

2. If Alex tries to withdraw:

   ```bash
   self-promise withdraw --promise-id 123
   ```

   The terminal would display:

   ```
   Promise ID: 123 has been resolved.
   Status: Failed
   As per the terms, your 50.0 ROSE deposit has been burned.
   Transaction hash: 0xghi...xyz
   ```

   The funds would be transferred to a designated burn address, permanently removing them from circulation.

## Privacy and Security Throughout

At every step of this journey, Alex's privacy and security are protected:

1. **Anonymity**: Alex never provides personal information. Their identity on the platform is solely their blockchain wallet address.

2. **Private Promise Content**: The details of what Alex promised themselves remain confidential. The smart contracts running in Sapphire's TEE can see and process this data, but it's encrypted on the blockchain.

3. **Confidential Evidence**: Alex's fitness data is processed only within the ROFL TEE. The raw evidence never leaves the secure enclave and is not visible to anyone operating the service.

4. **Cryptographic Verification**: When the ROFL evaluator updates the promise status, the Sapphire smart contract cryptographically verifies that this update truly comes from the authorized ROFL service using `roflEnsureAuthorizedOrigin()`. This prevents tampering with evaluation results.

5. **Local Key Security**: Alex's private key never leaves their device. All transactions are signed locally before being submitted to the blockchain.

This combination of TEE-based confidential computing (both on and off-chain) with cryptographic verification creates a platform where users can make private commitments with financial accountability, confident that their personal data remains confidential throughout the process. 