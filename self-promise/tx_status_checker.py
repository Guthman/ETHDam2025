#!/usr/bin/env python
"""
Transaction Status Checker for Oasis Sapphire

This script helps check the status of transactions on the Oasis Sapphire network.
It can be used to debug transaction issues, such as when a transaction is submitted
but not confirmed.
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from typing import Optional, Dict, Any

from web3 import AsyncWeb3
from sapphirepy import sapphire
from eth_account import Account

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("tx_status_checker")


class TransactionChecker:
    """
    Utility class for checking transaction status on Oasis Sapphire.
    """

    def __init__(self, network: str = None, private_key: str = None):
        """
        Initialize the transaction checker.
        
        Args:
            network: The network to connect to (e.g., mainnet, testnet, sapphire-localnet)
            private_key: The private key for signing transactions (optional)
        """
        self.network = network or os.environ.get("OASIS_NETWORK") or "sapphire-localnet"
        self.private_key = private_key or os.environ.get("OASIS_PRIVATE_KEY")
        
        # Set up web3 with Sapphire middleware
        provider_url = sapphire.NETWORKS[self.network]
        logger.info(f"Connecting to Sapphire network '{self.network}' at URL: {provider_url}")
        
        self.w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(provider_url))
        
        # Add account if private key is provided
        if self.private_key:
            self.account = Account.from_key(self.private_key)
            self.w3.eth.default_account = self.account.address
            logger.info(f"Using account: {self.account.address}")
        
        logger.info("TransactionChecker initialized")

    async def check_transaction_status(self, tx_hash: str) -> Dict[str, Any]:
        """
        Check the status of a transaction.
        
        Args:
            tx_hash: The transaction hash to check
            
        Returns:
            A dictionary with transaction status information
        """
        logger.info(f"Checking status of transaction: {tx_hash}")
        
        # Check if the transaction exists in the mempool
        try:
            tx = await self.w3.eth.get_transaction(tx_hash)
            if tx is None:
                return {
                    "status": "not_found",
                    "message": "Transaction not found in mempool or blockchain",
                    "timestamp": int(time.time())
                }
                
            # Check if the transaction has been mined
            receipt = await self.w3.eth.get_transaction_receipt(tx_hash)
            if receipt is None:
                # Transaction exists but hasn't been mined yet
                return {
                    "status": "pending",
                    "message": "Transaction is in mempool but not yet mined",
                    "transaction": {
                        "from": tx["from"],
                        "to": tx["to"],
                        "value": tx["value"],
                        "gas": tx["gas"],
                        "gasPrice": tx["gasPrice"],
                        "nonce": tx["nonce"],
                        "blockHash": tx["blockHash"],
                        "blockNumber": tx["blockNumber"],
                        "hash": tx["hash"].hex()
                    },
                    "timestamp": int(time.time())
                }
            
            # Transaction has been mined
            status = "success" if receipt["status"] == 1 else "failed"
            return {
                "status": status,
                "message": f"Transaction has been mined and {status}",
                "transaction": {
                    "from": tx["from"],
                    "to": tx["to"],
                    "value": tx["value"],
                    "gas": tx["gas"],
                    "gasPrice": tx["gasPrice"],
                    "nonce": tx["nonce"],
                    "blockHash": tx["blockHash"],
                    "blockNumber": tx["blockNumber"],
                    "hash": tx["hash"].hex()
                },
                "receipt": {
                    "blockHash": receipt["blockHash"].hex(),
                    "blockNumber": receipt["blockNumber"],
                    "contractAddress": receipt["contractAddress"],
                    "cumulativeGasUsed": receipt["cumulativeGasUsed"],
                    "effectiveGasPrice": receipt["effectiveGasPrice"],
                    "gasUsed": receipt["gasUsed"],
                    "logs": [log.args for log in receipt.logs] if hasattr(receipt, "logs") else [],
                    "status": receipt["status"],
                    "transactionHash": receipt["transactionHash"].hex(),
                    "transactionIndex": receipt["transactionIndex"]
                },
                "timestamp": int(time.time())
            }
            
        except Exception as e:
            logger.error(f"Error checking transaction status: {e}")
            return {
                "status": "error",
                "message": f"Error checking transaction status: {str(e)}",
                "timestamp": int(time.time())
            }

    async def check_network_status(self) -> Dict[str, Any]:
        """
        Check the status of the network.
        
        Returns:
            A dictionary with network status information
        """
        logger.info("Checking network status")
        
        try:
            # Check if the node is syncing
            syncing = await self.w3.eth.syncing
            
            # Get the latest block
            latest_block = await self.w3.eth.get_block("latest")
            
            # Get the pending transaction count
            pending_count = await self.w3.eth.get_block_transaction_count("pending")
            
            # Calculate block age
            block_timestamp = latest_block.timestamp
            current_time = int(time.time())
            block_age = current_time - block_timestamp
            
            return {
                "status": "ok",
                "syncing": syncing,
                "latest_block": {
                    "number": latest_block.number,
                    "hash": latest_block.hash.hex(),
                    "timestamp": block_timestamp,
                    "age_seconds": block_age
                },
                "pending_transactions": pending_count,
                "timestamp": current_time
            }
            
        except Exception as e:
            logger.error(f"Error checking network status: {e}")
            return {
                "status": "error",
                "message": f"Error checking network status: {str(e)}",
                "timestamp": int(time.time())
            }

    async def poll_transaction_status(self, tx_hash: str, interval: int = 5, max_attempts: int = 12) -> Dict[str, Any]:
        """
        Poll the status of a transaction until it's mined or max attempts is reached.
        
        Args:
            tx_hash: The transaction hash to check
            interval: The interval between checks in seconds
            max_attempts: The maximum number of attempts
            
        Returns:
            The final transaction status
        """
        logger.info(f"Polling status of transaction: {tx_hash}")
        
        for attempt in range(1, max_attempts + 1):
            logger.info(f"Attempt {attempt}/{max_attempts} to check transaction status")
            
            status = await self.check_transaction_status(tx_hash)
            
            if status["status"] in ["success", "failed"]:
                logger.info(f"Transaction {tx_hash} has been mined with status: {status['status']}")
                return status
                
            if status["status"] == "not_found" and attempt > 3:
                logger.warning(f"Transaction {tx_hash} not found after {attempt} attempts. It may have been dropped.")
                
            logger.info(f"Transaction {tx_hash} is {status['status']}. Waiting {interval} seconds before next check...")
            await asyncio.sleep(interval)
            
        logger.warning(f"Max attempts reached. Final status of transaction {tx_hash}: {status['status']}")
        return status


async def main():
    """
    Main function to run the transaction checker.
    """
    parser = argparse.ArgumentParser(description="Check transaction status on Oasis Sapphire")
    parser.add_argument("--tx", type=str, help="Transaction hash to check")
    parser.add_argument("--network", type=str, default=None, help="Network to connect to")
    parser.add_argument("--poll", action="store_true", help="Poll transaction status until mined")
    parser.add_argument("--interval", type=int, default=5, help="Polling interval in seconds")
    parser.add_argument("--attempts", type=int, default=12, help="Maximum polling attempts")
    parser.add_argument("--network-status", action="store_true", help="Check network status")
    parser.add_argument("--output", type=str, default=None, help="Output file for results (JSON)")
    
    args = parser.parse_args()
    
    # Create the transaction checker
    checker = TransactionChecker(network=args.network)
    
    results = {}
    
    # Check network status if requested
    if args.network_status:
        network_status = await checker.check_network_status()
        print(json.dumps(network_status, indent=2))
        results["network_status"] = network_status
    
    # Check transaction status if tx hash is provided
    if args.tx:
        if args.poll:
            tx_status = await checker.poll_transaction_status(
                args.tx, 
                interval=args.interval, 
                max_attempts=args.attempts
            )
        else:
            tx_status = await checker.check_transaction_status(args.tx)
            
        print(json.dumps(tx_status, indent=2))
        results["transaction_status"] = tx_status
    
    # Save results to file if output is specified
    if args.output and results:
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)
        logger.info(f"Results saved to {args.output}")
    
    # If no specific action was requested, print help
    if not args.tx and not args.network_status:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
