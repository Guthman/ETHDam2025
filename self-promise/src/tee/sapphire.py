"""
Oasis Sapphire TEE integration module.
This module provides integration with Oasis Sapphire for confidential computing.
"""

import json
import os
import time
import logging
import subprocess
import asyncio
from typing import Dict, Any, List, Optional, Callable, Tuple

from web3 import AsyncWeb3
from web3.middleware import SignAndSendRawMiddlewareBuilder
from eth_account import Account
from eth_account.signers.local import LocalAccount
from sapphirepy import sapphire

try:
    from ..logger_config import get_module_logger
    logger = get_module_logger("sapphire")
except ImportError:
    # Fallback to basic logging if logger_config is not available
    logger = logging.getLogger("sapphire")
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

try:
    import solcx
except ImportError:
    logger.warning("solcx not installed. Contract compilation will not be available.")
    solcx = None

logger = logging.getLogger(__name__)


class SapphireClient:
    """
    Client for interacting with Oasis Sapphire confidential contracts.
    
    This client provides methods for deploying and interacting with
    confidential smart contracts on the Oasis Sapphire network.
    """

    def __init__(self,
                 network: Optional[str] = None,
                 private_key: Optional[str] = None,
                 provider_url: str = "http://localhost:8545",
                 contract_dir: str = None,
                 default_gas_limit: int = None):
        """
        Initialize the Sapphire client.
        
        Args:
            network: The network to connect to (e.g., mainnet, testnet, sapphire-localnet). Defaults to OASIS_NETWORK env var or "sapphire-localnet".
            private_key: The private key for signing transactions
            provider_url: URL of the Sapphire node
            contract_dir: Directory containing contract source files
            default_gas_limit: Default gas limit to use for transactions (if None, reads from DEFAULT_GAS_LIMIT env var or defaults to 6,000,000)
        """
        self.network = network or os.environ.get("OASIS_NETWORK") or "sapphire-localnet"
        self.private_key = private_key or os.environ.get("OASIS_PRIVATE_KEY")

        if not self.private_key:
            raise ValueError(
                "No private key provided. Set OASIS_PRIVATE_KEY environment variable or pass private_key parameter.")

        # Set up web3 with Sapphire middleware
        self.account: LocalAccount = Account.from_key(self.private_key)
        
        provider_url = sapphire.NETWORKS[self.network] # Get provider URL
        logger.info("Connecting to Sapphire network '%s' at URL: %s", self.network, provider_url) # Log it

        self.w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(provider_url))
        
        # Add signing middleware so that eth_sendTransaction calls are
        # automatically signed and sent as eth_sendRawTransaction.
        self.w3.middleware_onion.add(SignAndSendRawMiddlewareBuilder.build(self.account))
        
        # Now, wrap the w3 instance for Sapphire-specific functionalities.
        # sapphire.wrap modifies the w3 instance in place and returns it.
        self.w3 = sapphire.wrap(self.w3, self.account)
        
        self.w3.eth.default_account = self.account.address

        # Contract cache
        self.contracts = {}
        logger.info("SapphireClient initialized for network: %s", self.network)

        # Get default gas limit from parameter, environment, or use default
        if default_gas_limit is None:
            try:
                default_gas_limit = int(os.environ.get("DEFAULT_GAS_LIMIT", "6000000"))
            except ValueError:
                logger.warning("Invalid DEFAULT_GAS_LIMIT in environment, using default 6,000,000")
                default_gas_limit = 6000000
        
        # Store the default gas limit
        self.default_gas_limit = default_gas_limit
        logger.info("Using default gas limit for all transactions: %d", self.default_gas_limit)
        
        # Set the default contract directory
        if contract_dir is None:
            # Default to 'contracts' directory in project root
            file_dir = os.path.dirname(os.path.abspath(__file__))
            # Go up two levels from src/tee to reach project root
            project_root = os.path.abspath(os.path.join(file_dir, "..", ".."))
            self.contract_dir = os.path.join(project_root, "contracts")
        else:
            self.contract_dir = contract_dir

    @staticmethod
    async def compile_contract(contract_name: str,
                               solidity_version: str = "0.8.20") -> Tuple[Any, str]:
        """
        Compile a Solidity contract.
        
        Args:
            contract_name: The name of the contract
            solidity_version: The Solidity compiler version
            
        Returns:
            A tuple of (ABI, bytecode)
        """
        logger.info("Compiling contract %s with Solidity %s", contract_name, solidity_version)

        # Ensure the Solidity compiler is installed
        if solcx:
            solcx.install_solc(solidity_version)

        # Get the contract path
        # Get the directory of the current file (sapphire.py)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        # Go up two levels (from src/tee/ to self-promise/) and then to contracts/
        contract_dir = os.path.normpath(os.path.join(base_dir, "..", "..", "contracts"))
        contract_path = os.path.join(contract_dir, f"{contract_name}.sol")

        # logger.info("Attempting to load contract from: %s", contract_path) # This was temporarily added

        with open(contract_path, "r") as file:
            contract_source = file.read()

        # Prepare sources for solcx
        sources_input = {
            f"{contract_name}.sol": {"content": contract_source}
        }

        # If compiling PromiseKeeper, also include PromiseDeposit source for import resolution
        if contract_name == "PromiseKeeper":
            deposit_contract_path = os.path.join(contract_dir, "PromiseDeposit.sol")
            try:
                with open(deposit_contract_path, "r") as file:
                    deposit_contract_source = file.read()
                sources_input["PromiseDeposit.sol"] = {"content": deposit_contract_source}
                # logger.info("Added PromiseDeposit.sol to sources for compiling PromiseKeeper.sol") # Optional log
            except FileNotFoundError:
                logger.error("Could not find PromiseDeposit.sol to include for PromiseKeeper compilation at %s", deposit_contract_path)
                raise # Re-raise the error as it's critical for compilation

        # Compile the contract
        if solcx:
            compiled_sol = solcx.compile_standard(
                {
                    "language": "Solidity",
                    "sources": sources_input, # Use the prepared sources_input
                    "settings": {
                        "outputSelection": {
                            "*": {
                                "*": ["abi", "metadata", "evm.bytecode", "evm.sourceMap"]
                            }
                        }
                    }
                },
                solc_version=solidity_version
            )
        else:
            compiled_sol = {}

        # Extract ABI and bytecode
        contract_data = compiled_sol["contracts"][f"{contract_name}.sol"][contract_name]
        abi = contract_data["abi"]
        bytecode = contract_data["evm"]["bytecode"]["object"]

        return abi, bytecode

    async def deploy_contract(self,
                              contract_name: str,
                              contract_bytecode: Optional[str] = None,
                              contract_abi: Optional[Any] = None,
                              constructor_args: List[Any] = None) -> str:
        """
        Deploy a confidential contract to Oasis Sapphire.
        
        Args:
            contract_name: The name of the contract
            contract_bytecode: The compiled contract bytecode (optional if compiling)
            contract_abi: The contract ABI (optional if compiling)
            constructor_args: Arguments for the contract constructor
            
        Returns:
            The address of the deployed contract
        """
        logger.info("Deploying %s contract to Sapphire %s...", contract_name, self.network)

        # If bytecode and ABI weren't provided, compile the contract
        if not contract_bytecode or not contract_abi:
            logger.info("Compiling %s contract as ABI/bytecode not provided for deployment.", contract_name)
            # Ensure compile_contract is awaited correctly if it's async (it is)
            # And it's a static method, so call it on the class
            contract_abi, contract_bytecode = await SapphireClient.compile_contract(contract_name)

        # Create the contract instance
        contract = self.w3.eth.contract(abi=contract_abi, bytecode=contract_bytecode)

        # Prepare constructor arguments
        if constructor_args is None:
            constructor_args = []

        # Deploy the contract
        gas_price = await self.w3.eth.gas_price
        await self.is_network_ready()
        
        logger.info("Sending constructor transaction for %s with gas limit: %d", contract_name, self.default_gas_limit)
        tx_hash = await contract.constructor(*constructor_args).transact({
            "gasPrice": gas_price,
            "gas": self.default_gas_limit  # Use the default gas limit
        })
        logger.info("Deployment transaction for %s sent, hash: %s", contract_name, tx_hash.hex())

        # Wait for the transaction receipt
        logger.info("Waiting for transaction receipt for %s deployment...", contract_name)
        tx_receipt = await self.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        if tx_receipt.status == 0:
            logger.error("Contract %s deployment failed. Transaction status is 0. Receipt: %s", contract_name, tx_receipt)
            raise Exception(f"Contract {contract_name} deployment failed. Transaction status is 0.")

        contract_address = tx_receipt.contractAddress
        if not contract_address:
            logger.error("Contract %s deployment failed. No contract address in receipt. Receipt: %s", contract_name, tx_receipt)
            raise Exception(f"Contract {contract_name} deployment failed. No contract address in receipt.")

        logger.info("Contract %s deployed successfully at address: %s. Gas used: %d", 
                    contract_name, contract_address, tx_receipt.gasUsed)

        # Cache the contract
        self.contracts[contract_name] = {
            "address": contract_address,
            "abi": contract_abi,
            "bytecode": contract_bytecode,
            "constructor_args": constructor_args,
            "deploy_tx_hash": tx_hash.hex(),
            "deploy_gas_used": tx_receipt.gasUsed # Store gas used
        }
        
        return contract_address

    async def call_contract(self,
                            contract_address: str,
                            method_name: str,
                            args: List[Any] = None,
                            abi: Optional[Any] = None,
                            value: int = 0) -> Any:
        """
        Call a method on a confidential contract.
        
        Args:
            contract_address: The address of the contract
            method_name: The name of the method to call
            args: Arguments for the method
            abi: The contract ABI (optional if contract is cached)
            value: Amount of tokens to send with the call
            
        Returns:
            The result of the method call
        """
        logger.info("Calling %s on contract %s...", method_name, contract_address)

        # Get the contract ABI
        if not abi:
            for cached_contract in self.contracts.values():
                if cached_contract["address"].lower() == contract_address.lower():
                    abi = cached_contract["abi"]
                    break

            if not abi:
                raise ValueError(f"No ABI found for contract at {contract_address}")

        # Create the contract instance
        contract = self.w3.eth.contract(address=contract_address, abi=abi)

        # Prepare arguments
        if args is None:
            args = []

        # Call the method
        method = getattr(contract.functions, method_name)
        result = await method(*args).call({"value": value})

        return result

    async def is_network_ready(self) -> bool:
        """
        Check if the network is ready to process transactions.
        
        This method checks several conditions to determine if the network
        is in a state where transactions are likely to be processed successfully:
        1. If the node is still syncing
        2. If the latest block is recent enough
        3. If there are too many pending transactions
        
        Returns:
            True if the network appears ready, False otherwise
        """
        try:
            # Check if the node is syncing
            syncing = await self.w3.eth.syncing
            if syncing:
                logger.warning(
                    "Blockchain is still syncing. Current block: %s, Highest block: %s",
                    syncing.get('currentBlock', 'unknown'),
                    syncing.get('highestBlock', 'unknown')
                )
                return False
                
            # Check if the latest block is recent enough
            try:
                latest_block = await self.w3.eth.get_block('latest')
                block_timestamp = latest_block.timestamp
                current_time = int(time.time())
                
                # If latest block is older than 2 minutes, network may not be ready
                if current_time - block_timestamp > 120:
                    logger.warning(
                        "Latest block is too old (%s seconds). Network may not be ready.",
                        current_time - block_timestamp
                    )
                    return False
                    
                # Check block height differences between analyzers
                # This is specific to Sapphire's dual-analyzer architecture
                # In a production environment, you might query this differently
                logger.info("Latest block height: %s, timestamp: %s", latest_block.number, block_timestamp)
            except Exception as e:
                logger.warning("Error checking latest block: %s", e)
                # Continue even if this check fails
                
            # Check pending transaction count
            try:
                pending_count = await self.w3.eth.get_block_transaction_count('pending')
                if pending_count > 500:  # Arbitrary threshold
                    logger.warning("High pending transaction count: %s", pending_count)
                    return False
                logger.info("Current pending transaction count: %s", pending_count)
            except Exception as e:
                logger.warning("Error checking pending transactions: %s", e)
                # Continue even if this check fails
                
            # All checks passed or were skipped due to exceptions
            logger.info("Network appears ready for transactions")
            return True
            
        except Exception as e:
            logger.error("Error checking network status: %s", e)
            # If we can't determine readiness, assume it's not ready
            return False

    async def send_transaction(self,
                               contract_address: str,
                               method_name: str,
                               args: List[Any] = None,
                               abi: Optional[Any] = None,
                               value: int = 0,
                               gas_limit: Optional[int] = None,
                               check_network_ready: bool = True) -> str:
        """
        Send a transaction to a confidential contract.
        
        Args:
            contract_address: The address of the contract
            method_name: The name of the method to call
            args: Arguments for the method
            abi: The contract ABI (optional if contract is cached)
            value: Amount of tokens to send with the transaction
            gas_limit: Optional gas limit for the transaction
            check_network_ready: Whether to check if the network is ready before sending
            
        Returns:
            The transaction hash
        """
        logger.info("Sending transaction to %s on contract %s...", method_name, contract_address)

        # Check if the network is ready
        if check_network_ready:
            network_ready = await self.is_network_ready()
            if not network_ready:
                logger.warning("Network does not appear ready. Transaction may fail or be dropped.")
                # We continue anyway but have logged the warning

        # Get the contract ABI
        if not abi:
            for cached_contract in self.contracts.values():
                if cached_contract["address"].lower() == contract_address.lower():
                    abi = cached_contract["abi"]
                    break

            if not abi:
                raise ValueError(f"No ABI found for contract at {contract_address}")

        # Create the contract instance
        contract = self.w3.eth.contract(address=contract_address, abi=abi)

        # Prepare arguments
        if args is None:
            args = []

        # Send the transaction
        gas_price = await self.w3.eth.gas_price
        method = getattr(contract.functions, method_name)
        
        tx_params = {"gasPrice": gas_price, "value": value}
        if gas_limit:
            tx_params["gas"] = gas_limit
            logger.info("Using explicit gas limit for transaction: %s", gas_limit)
        else:
            # Use the default gas limit
            tx_params["gas"] = self.default_gas_limit
            logger.info("Using default gas limit for transaction: %s", self.default_gas_limit)

        tx_hash = await method(*args).transact(tx_params)

        logger.info("Transaction sent: %s", tx_hash.hex())
        return tx_hash.hex()

    async def get_event_from_receipt(self, tx_hash: str, contract_name_for_abi: str, event_name: str, 
                                    max_attempts: int = 5, initial_timeout: int = 30) -> Optional[Dict[str, Any]]:
        """
        Waits for a transaction receipt and extracts arguments from a specific event with improved retry logic.

        Args:
            tx_hash: The hash of the transaction.
            contract_name_for_abi: The name of the contract (as stored in self.contracts) to get ABI for event decoding.
            event_name: The name of the event to look for.
            max_attempts: Maximum number of attempts to get the receipt.
            initial_timeout: Initial timeout in seconds for the first attempt.

        Returns:
            A dictionary of event arguments if the event is found, otherwise None.
        """
        logger.info("Waiting for receipt for tx %s to get event '%s'...", tx_hash, event_name)
        
        # Check if the network is ready before waiting for receipt
        network_ready = await self.is_network_ready()
        if not network_ready:
            logger.warning("Network may not be ready. Transaction receipt retrieval might be delayed.")
        
        for attempt in range(1, max_attempts + 1):
            # Calculate timeout with exponential backoff
            timeout = initial_timeout * (2 ** (attempt - 1))
            
            try:
                logger.info("Attempt %d/%d: Waiting for receipt with timeout %d seconds...", 
                           attempt, max_attempts, timeout)
                
                # Try to get the transaction first to see if it exists
                try:
                    tx = await self.w3.eth.get_transaction(tx_hash)
                    if tx is None:
                        logger.warning("Transaction %s not found in mempool. It may have been dropped.", tx_hash)
                        # If we're on the last attempt, return None
                        if attempt == max_attempts:
                            return None
                        # Otherwise wait and try again
                        await asyncio.sleep(timeout)
                        continue
                except Exception as e:
                    logger.warning("Error checking transaction %s: %s", tx_hash, e)
                
                # Try to get the receipt
                tx_receipt = await self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=timeout)
                
                if tx_receipt.status == 0:
                    logger.error("Transaction %s failed (status 0). No events to process.", tx_hash)
                    return None
                
                # Process the receipt
                if contract_name_for_abi not in self.contracts:
                    logger.error("ABI for contract '%s' not found in cache.", contract_name_for_abi)
                    return None
                
                contract_data = self.contracts[contract_name_for_abi]
                contract_abi = contract_data["abi"]
                contract_address = contract_data["address"]
                
                contract_instance = self.w3.eth.contract(address=contract_address, abi=contract_abi)
                
                try:
                    processed_events = getattr(contract_instance.events, event_name)().process_receipt(tx_receipt)
                    if processed_events:
                        event_args = processed_events[0]['args']
                        logger.info("Found event '%s' with args: %s", event_name, event_args)
                        return event_args
                    else:
                        logger.warning("Event '%s' not found in transaction %s logs.", event_name, tx_hash)
                        # The transaction was successful but didn't emit the expected event
                        # This is a different issue than a timeout, so we return None
                        return None
                except Exception as e:
                    logger.error("Error processing event '%s' for tx %s: %s", event_name, tx_hash, e)
                    return None
                    
            except asyncio.TimeoutError:
                logger.warning("Attempt %d/%d: Timeout waiting for receipt for %s", 
                              attempt, max_attempts, tx_hash)
                
                # If this is the last attempt, give up
                if attempt == max_attempts:
                    logger.error("All attempts failed. Giving up on transaction %s", tx_hash)
                    return None
                
                # Otherwise, check if the transaction is still in the mempool
                try:
                    tx = await self.w3.eth.get_transaction(tx_hash)
                    if tx is None:
                        logger.warning("Transaction %s not found in mempool after timeout. It may have been dropped.", tx_hash)
                    else:
                        logger.info("Transaction %s is still in mempool. Will retry...", tx_hash)
                except Exception as e:
                    logger.warning("Error checking transaction %s after timeout: %s", tx_hash, e)
            
            except Exception as e:
                logger.error("Unexpected error waiting for receipt for %s: %s", tx_hash, e)
                # If this is the last attempt, give up
                if attempt == max_attempts:
                    return None
            
            # Wait before retrying
            await asyncio.sleep(5)  # Short delay between attempts
        
        # If we get here, all attempts failed
        return None


class SecureDataHandler:
    """
    Handler for secure data operations within the TEE.
    
    This class provides methods for securely handling sensitive data
    within the Trusted Execution Environment.
    """

    def __init__(self, sapphire_client: SapphireClient):
        """
        Initialize the secure data handler.
        
        Args:
            sapphire_client: The Sapphire client
        """
        self.sapphire_client = sapphire_client
        self.w3 = sapphire_client.w3
        logger.info("SecureDataHandler initialized")

    async def encrypt_data(self, data: Dict[str, Any]) -> str:
        """
        Encrypt data for secure storage or transmission using Sapphire's encryption.
        
        Args:
            data: The data to encrypt
            
        Returns:
            The encrypted data as a string
        """
        # Convert data to JSON string
        data_str = json.dumps(data)

        # Deploy a temporary contract for encryption if needed
        # In a production implementation, you'd use a dedicated encryption contract

        # For now, we'll use a simple approach with the web3 instance's encryption
        nonce = os.urandom(24).hex()  # Generate a random nonce
        context = "self-promise-encryption"

        # Use Sapphire's encryption through web3 middleware
        encrypted_data = self.w3.sapphire.encrypt(data_str, nonce, context)

        # Return the encrypted data along with the nonce for later decryption
        return json.dumps({
            "encrypted": encrypted_data.hex() if isinstance(encrypted_data, bytes) else encrypted_data,
            "nonce": nonce,
            "context": context
        })

    async def decrypt_data(self, encrypted_data: str) -> Dict[str, Any]:
        """
        Decrypt data that was encrypted with encrypt_data.
        
        Args:
            encrypted_data: The encrypted data
            
        Returns:
            The decrypted data
        """
        # Parse the encrypted data JSON
        data = json.loads(encrypted_data)
        encrypted = data["encrypted"]
        nonce = data["nonce"]
        context = data["context"]

        # Convert hex string to bytes if needed
        if isinstance(encrypted, str):
            encrypted = bytes.fromhex(encrypted)

        # Decrypt the data using Sapphire's decryption
        decrypted_data = self.w3.sapphire.decrypt(encrypted, nonce, context)

        # Parse the decrypted JSON
        return json.loads(decrypted_data)

    async def secure_compute(self,
                             function: Callable,
                             input_data: Dict[str, Any],
                             attestation: bool = True) -> Dict[str, Any]:
        """
        Execute a function securely within the TEE.
        
        Args:
            function: The function to execute
            input_data: The input data for the function
            attestation: Whether to generate an attestation for the computation
            
        Returns:
            The result of the function
        """
        # For a real TEE execution, you would:
        # 1. Deploy a ROFL service with the function code
        # 2. Send the input data to the service
        # 3. The service would execute the function in the TEE
        # 4. Return the result with an attestation

        # For now, we'll simulate the secure execution locally
        logger.info("Executing secure computation in TEE simulation")

        # Encrypt the input data
        encrypted_input = await self.encrypt_data(input_data)

        # In a real implementation, we would send the encrypted input to a ROFL service
        # and get back an encrypted result with an attestation

        # Simulate TEE execution by running the function locally
        result = function(input_data)

        if attestation:
            # Generate a simulated attestation
            # In a real implementation, this would be generated by the TEE
            attestation_data = {
                "tee_type": "Sapphire",
                "timestamp": int(time.time()),
                "signature": self.w3.keccak(text=json.dumps(result)).hex()
            }

            result["attestation"] = attestation_data
            logger.info("Added attestation to secure computation result")

        return result


class ROFLClient:
    """
    Client for Oasis ROFL (Runtime for Offchain Logic).
    
    This client provides methods for running confidential off-chain logic
    using Oasis ROFL.
    """

    def __init__(self,
                 network: Optional[str] = None,
                 private_key: Optional[str] = None):
        """
        Initialize the ROFL client.
        
        Args:
            network: The network to connect to (e.g., mainnet, testnet, sapphire-localnet). Defaults to OASIS_NETWORK env var or "sapphire-localnet".
            private_key: The private key for signing transactions
        """
        self.network = network or os.environ.get("OASIS_NETWORK") or "sapphire-localnet"
        self.private_key = private_key or os.environ.get("OASIS_PRIVATE_KEY")

        if not self.private_key:
            raise ValueError(
                "No private key provided. Set OASIS_PRIVATE_KEY environment variable or pass private_key parameter.")

        # Set environment variables for oasis CLI
        os.environ["OASIS_PRIVATE_KEY"] = self.private_key
        os.environ["OASIS_NETWORK"] = self.network

        logger.info("ROFLClient initialized for network: %s", self.network)

    @staticmethod
    def _run_oasis_command(command: List[str]) -> str:
        """
        Run an Oasis CLI command.
        
        Args:
            command: The command parts to run
            
        Returns:
            The command output
        """
        full_command = ["oasis"] + command
        logger.info("Running Oasis command: %s", " ".join(full_command))

        try:
            result = subprocess.run(
                full_command,
                check=True,
                capture_output=True,
                text=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            logger.error("Oasis command failed: %s", e.stderr)
            raise RuntimeError(f"Oasis command failed: {e.stderr}")

    def init_rofl_config(self, directory: str = "./") -> str:
        """
        Initialize ROFL configuration.
        
        Args:
            directory: The directory to initialize in
            
        Returns:
            The path to the created rofl.yaml file
        """
        os.chdir(directory)
        output = self._run_oasis_command(["rofl", "init"])
        logger.info("ROFL config initialized: %s", output)
        return os.path.join(directory, "rofl.yaml")

    def create_rofl_service(self) -> str:
        """
        Register a ROFL service on-chain.
        
        Returns:
            The service ID
        """
        output = self._run_oasis_command(["rofl", "create"])
        logger.info("ROFL service created: %s", output)

        # Extract service ID from output
        # Assuming output format contains the service ID
        service_id = output.strip().split()[-1]
        return service_id

    @staticmethod
    def set_secret(name: str, value: str) -> None:
        """
        Store a secret for ROFL.
        
        Args:
            name: The name of the secret
            value: The value of the secret
        """
        # Use echo to pipe the value to stdin
        cmd = f'echo -n "{value}" | oasis rofl secret set {name} -'

        try:
            subprocess.run(cmd, shell=True, check=True)
            logger.info("Secret %s set", name)
        except subprocess.CalledProcessError as e:
            logger.error("Failed to set secret: %s", e)
            raise RuntimeError(f"Failed to set secret: {e}")

    def build_rofl_bundle(self) -> str:
        """
        Build a ROFL bundle.
        
        Returns:
            The path to the built .orc file
        """
        output = self._run_oasis_command(["rofl", "build"])
        logger.info("ROFL bundle built: %s", output)

        # Extract file path from output
        # This is a simplification - actual output format may vary
        bundle_path = output.strip().split()[-1]
        return bundle_path

    def update_rofl_service(self) -> None:
        """
        Update ROFL service on-chain.
        """
        output = self._run_oasis_command(["rofl", "update"])
        logger.info("ROFL service updated: %s", output)

    def deploy_rofl_service(self) -> None:
        """
        Deploy ROFL service to a node.
        """
        output = self._run_oasis_command(["rofl", "deploy"])
        logger.info("ROFL service deployed: %s", output)

    def show_rofl_service(self) -> Dict[str, Any]:
        """
        Get information about a running ROFL service.
        
        Returns:
            Service information
        """
        output = self._run_oasis_command(["rofl", "show"])
        logger.info("ROFL service info: %s", output)

        # Parse output into a structured format
        # This is a simplification - actual output format may vary
        lines = output.strip().split('\n')
        info = {}

        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                info[key.strip()] = value.strip()

        return info

    def deploy_service(self,
                       service_name: str,
                       service_code: str,
                       config: Dict[str, Any] = None) -> str:
        """
        Deploy a ROFL service.
        
        Args:
            service_name: The name of the service
            service_code: The service code
            config: Service configuration
            
        Returns:
            The service ID
        """
        logger.info("Deploying ROFL service: %s", service_name)

        # Create a temporary directory for the service
        service_dir = os.path.join(os.getcwd(), f"rofl-{service_name}")
        os.makedirs(service_dir, exist_ok=True)

        # Write the service code to a file
        code_path = os.path.join(service_dir, "index.js")
        with open(code_path, "w") as f:
            f.write(service_code)

        # Initialize ROFL config
        self.init_rofl_config(service_dir)

        # Update config if provided
        if config:
            config_path = os.path.join(service_dir, "rofl.yaml")
            with open(config_path, "r") as f:
                rofl_config = f.read()

            # Update the config
            # This is a simplification - actual config format may vary
            with open(config_path, "w") as f:
                for key, value in config.items():
                    rofl_config = rofl_config.replace(f"{key}:", f"{key}: {value}")
                f.write(rofl_config)

        # Create ROFL service
        service_id = self.create_rofl_service()

        # Build the bundle
        self.build_rofl_bundle()

        # Update and deploy
        self.update_rofl_service()
        self.deploy_rofl_service()

        logger.info("ROFL service deployed with ID: %s", service_id)
        return service_id

    def call_service(self,
                     service_id: str,
                     method_name: str,
                     args: Dict[str, Any] = None) -> Any:
        """
        Call a ROFL service.
        
        Args:
            service_id: The ID of the service
            method_name: The name of the method to call
            args: Arguments for the method
            
        Returns:
            The result of the method call
        """
        logger.info("Calling %s on ROFL service %s", method_name, service_id)

        # Prepare arguments
        if args is None:
            args = {}

        # Create a JSON file with the arguments
        args_file = f"rofl-args-{int(time.time())}.json"
        with open(args_file, "w") as f:
            json.dump({
                "method": method_name,
                "args": args
            }, f)

        try:
            # Call the service
            output = self._run_oasis_command([
                "rofl", "call", service_id, "--input-file", args_file
            ])

            # Parse the result
            try:
                result = json.loads(output)
            except json.JSONDecodeError:
                # If output is not valid JSON, return as is
                result = output

            return result
        finally:
            # Clean up the arguments file
            if os.path.exists(args_file):
                os.remove(args_file)


def create_sapphire_client(network: Optional[str] = None, private_key: Optional[str] = None) -> SapphireClient:
    """
    Create a Sapphire client.
    
    Args:
        network: The network to connect to. Defaults to OASIS_NETWORK env var or "sapphire-localnet".
        private_key: The private key for signing transactions
        
    Returns:
        The Sapphire client
    """
    return SapphireClient(network=network, private_key=private_key)


def create_rofl_client(network: str = "testnet", private_key: Optional[str] = None) -> ROFLClient:
    """
    Create a ROFL client.
    
    Args:
        network: The network to connect to (testnet, mainnet, localnet)
        private_key: The private key for signing transactions
        
    Returns:
        The ROFL client
    """
    return ROFLClient(network=network, private_key=private_key)
