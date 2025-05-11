"""
Test script to demonstrate the self-promise platform functionality.
Focuses on PromiseKeeper methods one by one.
"""

import logging
import sys
import datetime
import asyncio
from dotenv import load_dotenv

# Get the root logger
root_logger = logging.getLogger()
# Set its level to INFO
root_logger.setLevel(logging.INFO)
# Create a handler (e.g., StreamHandler to output to console)
handler = logging.StreamHandler(sys.stdout)
# Set the formatter for the handler
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
# Add the handler to the root logger
root_logger.addHandler(handler)

logger = logging.getLogger(__name__)

load_dotenv()

# Assuming your service and SapphireClient are structured as before
from src.service import create_service  # Or directly use SapphireClient if service layer is too complex for this test


async def main():
    """
    Main function to test PromiseKeeper methods incrementally.
    """

    logger.info("PromiseKeeper Incremental Test")
    print("=========================")
    print()

    # Create a service or SapphireClient directly
    # For simplicity, let's assume we use the service which wraps SapphireClient
    # If this fails, we can simplify further to use SapphireClient directly
    try:
        # service = create_service(evaluator_type="rule_based") # Using service for convenience
        # Let's use SapphireClient directly for more granular control in this test
        from src.tee.sapphire import SapphireClient
        sapphire_client = SapphireClient()
        logger.info("SapphireClient initialized directly.")

    except Exception as e:
        logger.error("Failed to initialize SapphireClient: %s", e, exc_info=True)
        return

    deposit_address = None
    promise_keeper_address = None
    test_promise_id = None

    try:
        # Step 1: Deploy PromiseDeposit
        logger.info("Step 1: Deploying PromiseDeposit contract...")
        deposit_address = await sapphire_client.deploy_contract(
            contract_name="PromiseDeposit",
            constructor_args=[]
        )
        logger.info("PromiseDeposit deployed at: %s", deposit_address)
        print("-------------------------")

        # Step 2: Deploy PromiseKeeper
        logger.info("Step 2: Deploying PromiseKeeper contract...")
        # PromiseKeeper constructor calls _createDefaultTemplates(), which is gas-intensive.
        promise_keeper_address = await sapphire_client.deploy_contract(
            contract_name="PromiseKeeper",
            constructor_args=None,  # PromiseKeeper constructor takes no args
            # Default gas limit of 6,000,000 is used from SapphireClient
        )
        logger.info("PromiseKeeper deployed at: %s", promise_keeper_address)
        print("-------------------------")

        # Step 3: Call setDepositContract on PromiseKeeper
        logger.info(
            "Step 3: Calling setDepositContract on PromiseKeeper (%s) with deposit address (%s)...", 
            promise_keeper_address, deposit_address
        )
        
        tx_hash_set_deposit = await sapphire_client.send_transaction(
            contract_address=promise_keeper_address,
            method_name="setDepositContract",
            args=[deposit_address],
            # gas_limit parameter uses default from SapphireClient (6,000,000)
        )
        logger.info("Transaction sent for setDepositContract: %s", tx_hash_set_deposit)

        # Wait for receipt (optional for this step if just checking if tx is sent, but good for confirmation)
        logger.info("Waiting for receipt of setDepositContract transaction: %s...", tx_hash_set_deposit)
        # We need the ABI for PromiseKeeper to process its events
        if "PromiseKeeper" not in sapphire_client.contracts:
            pk_abi, _ = await sapphire_client.compile_contract("PromiseKeeper")
            sapphire_client.contracts["PromiseKeeper"] = {"address": promise_keeper_address, "abi": pk_abi}

        event_args_deposit_updated = await sapphire_client.get_event_from_receipt(
            tx_hash=tx_hash_set_deposit,
            contract_name_for_abi="PromiseKeeper",
            event_name="DepositContractUpdated"
        )
        if event_args_deposit_updated:
            logger.info("DepositContractUpdated event: %s", event_args_deposit_updated)
            assert event_args_deposit_updated['newAddress'] == deposit_address
        else:
            logger.warning(
                "DepositContractUpdated event not found. Transaction might have failed or event processing issue.")
        print("-------------------------")

        # Step 4: Call createPromise on PromiseKeeper with minimal parameters
        logger.info("Step 4: Calling createPromise on PromiseKeeper (%s)...", promise_keeper_address)
        user_id_for_promise = sapphire_client.account.address  # Use the deployer's address as owner

        # Minimal parameters
        template_id = 1  # Assuming template ID 1 (Exercise Frequency) exists from _createDefaultTemplates
        param_keys = []  # Empty arrays for minimal gas
        param_values = []

        # Valid start and end dates
        start_date_ts = int(datetime.datetime.now().timestamp())
        end_date_ts = int((datetime.datetime.now() + datetime.timedelta(days=7)).timestamp())
        failure_recipient = "0x000000000000000000000000000000000000dEaD"  # Burn address

        logger.info(
            "createPromise parameters: templateId=%s, owner=%s, startDate=%s, endDate=%s",
            template_id, user_id_for_promise, start_date_ts, end_date_ts
        )

        tx_hash_create_promise = await sapphire_client.send_transaction(
            contract_address=promise_keeper_address,
            method_name="createPromise",
            args=[
                template_id,
                param_keys,
                param_values,
                start_date_ts,
                end_date_ts,
                failure_recipient
            ],
            gas_limit=8000000,  # Use higher gas limit for createPromise as it's more complex
        )
        logger.info("Transaction sent for createPromise: %s", tx_hash_create_promise)

        logger.info("Waiting for receipt of createPromise transaction: %s...", tx_hash_create_promise)
        event_args_promise_created = await sapphire_client.get_event_from_receipt(
            tx_hash=tx_hash_create_promise,
            contract_name_for_abi="PromiseKeeper",
            event_name="PromiseCreated"
        )

        if event_args_promise_created:
            logger.info("PromiseCreated event: %s", event_args_promise_created)
            test_promise_id = event_args_promise_created['promiseId']  # Capture promiseId if successful
            logger.info(
                "Promise created successfully with ID: %s",
                test_promise_id.hex() if isinstance(test_promise_id, bytes) else test_promise_id
            )
        else:
            logger.error(
                "PromiseCreated event not found. createPromise transaction likely failed or event not processed.")

        print("-------------------------")
        if test_promise_id:
            logger.info("SUCCESS: All tested PromiseKeeper methods seem to have executed.")
        else:
            logger.warning("PARTIAL SUCCESS or FAILURE: Not all PromiseKeeper methods completed successfully.")

    except Exception as e:
        logger.error("An error occurred during the PromiseKeeper incremental test: %s", e, exc_info=True)
    finally:
        logger.info("PromiseKeeper Incremental Test Finished.")
        print("=========================")


if __name__ == "__main__":
    import os

    if not os.getenv("OASIS_PRIVATE_KEY"):
        print("Error: OASIS_PRIVATE_KEY not found. Please set it in your .env file or environment variables.")
    else:
        asyncio.run(main())
