# Transaction Handling Improvements

This document describes the improvements made to transaction handling in the Self-Promise platform, particularly focusing on the Oasis Sapphire integration.

## Problem

The platform was experiencing issues with transactions being submitted but not confirmed. This was happening because:

1. The blockchain node was still in "slow-sync" mode
2. Transaction receipts were not being retrieved due to timeouts
3. There was no robust retry mechanism for failed transactions
4. The system couldn't detect when the network wasn't ready for transactions
5. **Gas limits were too low** for complex contract operations

## Solution

Several improvements have been implemented to address these issues:

### 1. Network Readiness Check

A new method `is_network_ready()` has been added to the `SapphireClient` class that checks:
- If the node is still syncing
- If the latest block is recent enough
- If there are too many pending transactions

This helps prevent submitting transactions when the network isn't ready to process them.

### 2. Improved Transaction Receipt Handling

The `get_event_from_receipt()` method has been enhanced with:
- Exponential backoff retry mechanism
- Better error handling
- Transaction existence checks
- More detailed logging

### 3. Robust Promise Creation

The `create_promise()` method in the service now includes:
- Multiple attempts with retry logic
- Network readiness checks before sending transactions
- Graceful handling of transaction failures
- More detailed error information

### 4. Transaction Status Checker

A new utility has been added to help debug transaction issues:
- `tx_status_checker.py`: A Python script to check transaction status
- `check_tx.sh`: A shell script wrapper for easier use

### 5. Default High Gas Limits

A significant issue was that transactions weren't being mined due to insufficient gas limits. We've implemented:

- A default high gas limit (6,000,000) for all transactions
- Ability to customize gas limits when initializing the SapphireClient
- Option to override gas limits on a per-transaction basis
- More detailed logging of gas usage

```python
# Initialize SapphireClient with custom gas limit
client = SapphireClient(
    private_key="0x...",
    default_gas_limit=8000000  # 8 million gas units
)

# Or override gas limit for a specific transaction
tx_hash = await client.send_transaction(
    contract_address="0x...",
    method_name="createPromise",
    args=[...],
    gas_limit=10000000  # 10 million gas units for complex operations
)
```

#### Recommended Gas Limits for Different Operations

Based on extensive testing, we recommend the following gas limits for different contract operations:

| Operation | Contract | Recommended Gas Limit | Notes |
|-----------|----------|----------------------|-------|
| Contract Deployment | PromiseDeposit | 6,000,000 | Simple contract deployment |
| Contract Deployment | PromiseKeeper | 8,000,000 | Complex due to template initialization |
| Promise Creation | PromiseKeeper.createPromise | 8,000,000 | Higher limit needed for complex promise parameters |
| Promise Evaluation | PromiseKeeper.recordEvaluation | 7,000,000 | Gas usage depends on evidence size |
| Token Deposit | PromiseDeposit.deposit | 6,000,000 | Standard token transfer with state updates |
| Token Withdrawal | PromiseDeposit.withdraw | 6,000,000 | Standard token transfer with state updates |
| Setting Deposit Contract | PromiseKeeper.setDepositContract | 6,000,000 | Simple state update |

For all operations, we monitor gas efficiency (percentage of gas limit actually used) to help optimize future transactions. In our service layer implementation, we've already configured these recommended values as defaults.

#### Gas Usage Monitoring

Our implementation now includes gas usage monitoring to help optimize gas limits over time:

```python
# Get gas usage from receipt
receipt = await sapphire_client.w3.eth.get_transaction_receipt(tx_hash)
gas_used = receipt.gasUsed
gas_limit = 8000000  # The limit used for this transaction
efficiency = (gas_used / gas_limit) * 100

logger.info("Transaction %s gas used: %d", tx_hash, gas_used)
logger.info("Gas efficiency: %.2f%%", efficiency)
```

This monitoring helps us understand the actual gas requirements of different operations and adjust our recommended limits accordingly.

#### Gas Optimization Resources

For optimizing contract gas usage, refer to these resources:
- [Hacken.io Solidity Gas Optimization](https://hacken.io/discover/solidity-gas-optimization/)
- [Blockchain Oodles Gas Profile Optimization](https://blockchain.oodles.io/dev-blog/gas-profile-optimization-solidity-insights/)
- [GitHub: Solidity Gas Optimization Techniques](https://github.com/harendra-shakya/solidity-gas-optimization)

## Usage

### Transaction Status Checker

The transaction status checker can be used to check the status of transactions and monitor the network:

```bash
# Check the status of a transaction
./check_tx.sh 0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef

# Poll the status of a transaction until it's mined
./check_tx.sh -p 0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef

# Check network status
./check_tx.sh -s

# Check both network status and transaction status
./check_tx.sh -s 0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef

# Save results to a file
./check_tx.sh -o results.json 0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef
```

For more options, run:
```bash
./check_tx.sh --help
```

### Python API

You can also use the transaction status checker programmatically:

```python
import asyncio
from tx_status_checker import TransactionChecker

async def check_tx():
    checker = TransactionChecker()
    
    # Check network status
    network_status = await checker.check_network_status()
    print(f"Network status: {network_status}")
    
    # Check transaction status
    tx_hash = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
    tx_status = await checker.check_transaction_status(tx_hash)
    print(f"Transaction status: {tx_status}")
    
    # Poll transaction status
    final_status = await checker.poll_transaction_status(tx_hash, interval=5, max_attempts=12)
    print(f"Final status: {final_status}")

asyncio.run(check_tx())
```

## Best Practices

1. **Always check network readiness** before submitting transactions
2. **Implement retry logic** for transaction submission and receipt retrieval
3. **Use exponential backoff** for retries to avoid overwhelming the network
4. **Check transaction existence** before waiting for a receipt
5. **Provide detailed error information** to help debug issues
6. **Use the transaction status checker** to monitor transactions and network status
7. **Set appropriate gas limits** for your contract operations (defaults: 6-8 million for complex operations)
8. **Monitor gas usage** and optimize your contracts where possible

## Future Improvements

1. Implement a transaction queue to manage transaction submission
2. Add support for transaction replacement (gas price bumping)
3. Implement a transaction monitoring service
4. Add support for transaction batching
5. Improve error handling and recovery mechanisms
