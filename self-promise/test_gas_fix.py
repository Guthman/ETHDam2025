"""
Test script to verify gas limit fixes in the Sapphire client.
"""
import logging
import sys
import asyncio
from dotenv import load_dotenv

# Basic logging setup
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
root_logger.addHandler(handler)

logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

from src.tee.sapphire import SapphireClient

async def main():
    """
    Main function to test the gas limit fix.
    """
    logger.info("Starting Gas Fix Test...")
    
    # Initialize the SapphireClient with a custom gas limit
    client = SapphireClient(
        private_key=None,  # Will use OASIS_PRIVATE_KEY from .env
        default_gas_limit=8000000  # Increased from default 6,000,000
    )
    
    # 1. Deploy SimpleStorage contract
    logger.info("Step 1: Deploying SimpleStorage contract...")
    initial_value = 123
    contract_address = await client.deploy_contract(
        contract_name="SimpleStorage", 
        constructor_args=[initial_value]
    )
    logger.info("SimpleStorage deployed at: %s", contract_address)
    
    # Get the contract ABI
    contract_abi, _ = await client.compile_contract("SimpleStorage")
    
    # 2. Call get() to verify initial value
    logger.info("Step 2: Calling get() to verify initial value...")
    result = await client.call_contract(
        contract_address=contract_address, 
        abi=contract_abi, 
        method_name="get"
    )
    logger.info("Initial value: %d", result)
    assert result == initial_value, f"Expected {initial_value}, got {result}"
    
    # 3. Call set() to update the value
    new_value = 456
    logger.info("Step 3: Calling set() to update value to %d...", new_value)
    tx_hash = await client.send_transaction(
        contract_address=contract_address, 
        abi=contract_abi, 
        method_name="set", 
        args=[new_value]
    )
    logger.info("Transaction sent: %s", tx_hash)
    
    # 4. Wait for transaction receipt and ValueChanged event
    logger.info("Step 4: Waiting for transaction receipt...")
    receipt_event_args = await client.get_event_from_receipt(
        tx_hash,
        "SimpleStorage",
        "ValueChanged"
    )
    logger.info("ValueChanged event: %s", receipt_event_args)
    assert receipt_event_args is not None, "Failed to get ValueChanged event"
    assert receipt_event_args['newValue'] == new_value, "Event value mismatch"
    
    # 5. Call get() again to verify the value was updated
    logger.info("Step 5: Calling get() to verify updated value...")
    result = await client.call_contract(
        contract_address=contract_address, 
        abi=contract_abi, 
        method_name="get"
    )
    logger.info("Updated value: %d", result)
    assert result == new_value, f"Expected {new_value}, got {result}"
    
    logger.info("SUCCESS: Gas Fix Test completed successfully!")

if __name__ == "__main__":
    asyncio.run(main()) 