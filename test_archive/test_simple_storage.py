"""
Test script for SimpleStorage contract.
"""
import logging
import sys
import asyncio
from dotenv import load_dotenv
import os

load_dotenv()

# Basic logging setup
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
root_logger.addHandler(handler)

logger = logging.getLogger(__name__)

# Assuming your SapphireClient is in src.tee.sapphire
# Adjust the import path if it's different
try:
    from src.tee.sapphire import SapphireClient
except ImportError:
    logger.error(
        "Failed to import SapphireClient. Make sure it's in the correct path (e.g., src/tee/sapphire.py) and your PYTHONPATH is set up if needed.")
    sys.exit(1)


async def test_simple_storage():
    """
    Deploys SimpleStorage, sets a value, and gets it.
    """
    logger.info("Starting SimpleStorage Test")
    print("=========================")
    print()

    try:
        # Create SapphireClient instance
        # It will use OASIS_NETWORK and OASIS_PRIVATE_KEY from .env or environment
        sapphire_client = SapphireClient()
        logger.info("SapphireClient initialized.")
    except Exception as e:
        logger.error("Failed to initialize SapphireClient: %s", e)
        return

    initial_value = 123
    new_value = 456

    try:
        # 1. Deploy SimpleStorage contract
        logger.info(f"Deploying SimpleStorage contract with initial value: {initial_value}...")
        # Note: The constructor for SimpleStorage takes one argument: initialValue
        simple_storage_address = await sapphire_client.deploy_contract(
            contract_name="SimpleStorage",
            constructor_args=[initial_value]
        )
        logger.info(f"SimpleStorage deployed at: {simple_storage_address}")

        # Store ABI for later calls if not already cached by deploy_contract
        # (Good practice, though our current SapphireClient caches it)
        if "SimpleStorage" not in sapphire_client.contracts or \
                sapphire_client.contracts["SimpleStorage"]["address"] != simple_storage_address:
            # If deploy_contract doesn't cache or if we want to be explicit
            compiled_abi, _ = await sapphire_client.compile_contract("SimpleStorage")
            sapphire_client.contracts["SimpleStorage"] = {
                "address": simple_storage_address,
                "abi": compiled_abi,
                # Add other details if needed, like bytecode, constructor_args
            }
            logger.info("Manually cached ABI for SimpleStorage.")

        # 2. Call the 'get' method (view function)
        logger.info("Calling get() to retrieve initial value...")
        current_value = await sapphire_client.call_contract(
            contract_address=simple_storage_address,
            method_name="get",
            abi=sapphire_client.contracts["SimpleStorage"]["abi"]  # Pass ABI explicitly
        )
        logger.info(f"Initial value from contract: {current_value}")
        assert current_value == initial_value, f"Initial value mismatch: expected {initial_value}, got {current_value}"

        # 3. Call the 'set' method (state-changing transaction)
        logger.info(f"Calling set() to change value to: {new_value}...")
        tx_hash_set = await sapphire_client.send_transaction(
            contract_address=simple_storage_address,
            method_name="set",
            args=[new_value],
            abi=sapphire_client.contracts["SimpleStorage"]["abi"]  # Pass ABI
        )
        logger.info(f"Transaction sent for set(): {tx_hash_set}")

        # 4. Wait for the transaction receipt and check for the event
        logger.info(f"Waiting for receipt of set() transaction: {tx_hash_set}...")
        event_args = await sapphire_client.get_event_from_receipt(
            tx_hash=tx_hash_set,
            contract_name_for_abi="SimpleStorage",  # Use the name under which ABI is cached
            event_name="ValueChanged"
        )

        if event_args:
            logger.info(f"ValueChanged event emitted: {event_args}")
            assert event_args['newValue'] == new_value, "Event value mismatch"
        else:
            logger.warning(
                "ValueChanged event not found in receipt. Transaction might have failed or event not processed.")
            # We will still try to get the value to see if state changed

        # 5. Call 'get' again to verify the new value
        logger.info("Calling get() again to retrieve updated value...")
        updated_value = await sapphire_client.call_contract(
            contract_address=simple_storage_address,
            method_name="get",
            abi=sapphire_client.contracts["SimpleStorage"]["abi"]  # Pass ABI
        )
        logger.info(f"Updated value from contract: {updated_value}")

        if updated_value == new_value:
            logger.info("SUCCESS: Value successfully updated in SimpleStorage contract!")
        else:
            logger.error(f"FAILURE: Value not updated. Expected {new_value}, got {updated_value}")

    except Exception as e:
        logger.error(f"An error occurred during the SimpleStorage test: {e}", exc_info=True)
        # If you have a traceback, exc_info=True will log it.
    finally:
        logger.info("SimpleStorage Test Finished.")
        print("=========================")


if __name__ == "__main__":
    # Ensure OASIS_PRIVATE_KEY is set in your .env file or environment variables
    if not os.getenv("OASIS_PRIVATE_KEY"):
        print("Error: OASIS_PRIVATE_KEY not found. Please set it in your .env file or environment variables.")
    else:
        asyncio.run(test_simple_storage())
