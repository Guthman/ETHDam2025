"""
Test script to demonstrate the minimal self-promise platform functionality.
This uses the minimal versions of contracts to avoid gas issues.
"""

import logging
import sys
import asyncio
import json
from pathlib import Path
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

async def main():
    """
    Main function to test MinimalPromiseKeeper methods incrementally.
    Using contract data from build directory.
    """

    logger.info("MinimalPromiseKeeper Test")
    print("=========================")
    print()

    try:
        from src.tee.sapphire import SapphireClient
        sapphire_client = SapphireClient()
        logger.info("SapphireClient initialized directly.")

    except Exception as e:
        logger.error("Failed to initialize SapphireClient: %s", e, exc_info=True)
        return

    deposit_address = None
    promise_keeper_address = None
    test_promise_id = None

    # Load compiled contract data
    build_dir = Path("./build")
    
    try:
        # Check if build files exist, if not run the compile_minimal_contracts.py script
        if not (build_dir / "MinimalPromiseDeposit.json").exists() or not (build_dir / "MinimalPromiseKeeper.json").exists():
            logger.info("Compiled contracts not found. Running compilation script...")
            from compile_minimal_contracts import main as compile_contracts
            compile_contracts()
            
        # Load MinimalPromiseDeposit.json
        with open(build_dir / "MinimalPromiseDeposit.json", 'r') as f:
            deposit_contract_data = json.load(f)
            
        # Load MinimalPromiseKeeper.json
        with open(build_dir / "MinimalPromiseKeeper.json", 'r') as f:
            keeper_contract_data = json.load(f)
        
        # Store the loaded ABIs in the client so they can be used without additional compilation
        sapphire_client.contracts["MinimalPromiseDeposit"] = {
            "abi": deposit_contract_data["abi"], 
            "bytecode": deposit_contract_data["bytecode"]
        }
        
        sapphire_client.contracts["MinimalPromiseKeeper"] = {
            "abi": keeper_contract_data["abi"], 
            "bytecode": keeper_contract_data["bytecode"]
        }
            
        logger.info("Contract data loaded successfully")
        
        # Step 1: Deploy MinimalPromiseDeposit
        logger.info("Step 1: Deploying MinimalPromiseDeposit contract...")
        deposit_address = await sapphire_client.deploy_contract(
            contract_name="MinimalPromiseDeposit",
            constructor_args=[],
            # Use pre-loaded bytecode
            bytecode=deposit_contract_data["bytecode"]
        )
        logger.info("MinimalPromiseDeposit deployed at: %s", deposit_address)
        print("-------------------------")

        # Update contract address in the client for later use
        sapphire_client.contracts["MinimalPromiseDeposit"]["address"] = deposit_address

        # Step 2: Deploy MinimalPromiseKeeper
        logger.info("Step 2: Deploying MinimalPromiseKeeper contract...")
        promise_keeper_address = await sapphire_client.deploy_contract(
            contract_name="MinimalPromiseKeeper",
            constructor_args=[],
            # Use pre-loaded bytecode
            bytecode=keeper_contract_data["bytecode"]
        )
        logger.info("MinimalPromiseKeeper deployed at: %s", promise_keeper_address)
        print("-------------------------")

        # Update contract address in the client for later use
        sapphire_client.contracts["MinimalPromiseKeeper"]["address"] = promise_keeper_address

        # Step 3: Call setDepositContract on MinimalPromiseKeeper
        logger.info(
            "Step 3: Calling setDepositContract on MinimalPromiseKeeper (%s) with deposit address (%s)...", 
            promise_keeper_address, deposit_address
        )
        
        tx_hash_set_deposit = await sapphire_client.send_transaction(
            contract_address=promise_keeper_address,
            method_name="setDepositContract",
            args=[deposit_address]
        )
        logger.info("Transaction sent for setDepositContract: %s", tx_hash_set_deposit)

        # Wait for receipt
        logger.info("Waiting for receipt of setDepositContract transaction: %s...", tx_hash_set_deposit)

        event_args_deposit_updated = await sapphire_client.get_event_from_receipt(
            tx_hash=tx_hash_set_deposit,
            contract_name_for_abi="MinimalPromiseKeeper",
            event_name="DepositContractUpdated"
        )
        if event_args_deposit_updated:
            logger.info("DepositContractUpdated event: %s", event_args_deposit_updated)
            assert event_args_deposit_updated['newAddress'] == deposit_address
        else:
            logger.warning(
                "DepositContractUpdated event not found. Transaction might have failed or event processing issue.")
        print("-------------------------")

        # Step 4: Call createPromise on MinimalPromiseKeeper
        logger.info("Step 4: Calling createPromise on MinimalPromiseKeeper (%s)...", promise_keeper_address)
        
        tx_hash_create_promise = await sapphire_client.send_transaction(
            contract_address=promise_keeper_address,
            method_name="createPromise",
            args=[]
        )
        logger.info("Transaction sent for createPromise: %s", tx_hash_create_promise)

        logger.info("Waiting for receipt of createPromise transaction: %s...", tx_hash_create_promise)
        event_args_promise_created = await sapphire_client.get_event_from_receipt(
            tx_hash=tx_hash_create_promise,
            contract_name_for_abi="MinimalPromiseKeeper",
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
        
        # Step 5: Make a deposit
        if test_promise_id:
            logger.info("Step 5: Making a deposit to MinimalPromiseDeposit (%s)...", deposit_address)
            
            tx_hash_deposit = await sapphire_client.send_transaction(
                contract_address=deposit_address,
                method_name="deposit",
                args=[],
                value=100000000  # Small deposit value, adjust as needed
            )
            logger.info("Transaction sent for deposit: %s", tx_hash_deposit)
            
            event_args_deposit = await sapphire_client.get_event_from_receipt(
                tx_hash=tx_hash_deposit,
                contract_name_for_abi="MinimalPromiseDeposit",
                event_name="DepositReceived"
            )
            
            if event_args_deposit:
                logger.info("DepositReceived event: %s", event_args_deposit)
            else:
                logger.warning("DepositReceived event not found. Deposit transaction might have failed.")
            
            print("-------------------------")
            
            # Step 6: Resolve the promise
            logger.info("Step 6: Resolving the promise...")
            
            # For demo purposes, let's resolve as fulfilled
            tx_hash_resolve = await sapphire_client.send_transaction(
                contract_address=promise_keeper_address,
                method_name="resolvePromise",
                args=[test_promise_id, True]  # True = fulfilled
            )
            logger.info("Transaction sent for resolvePromise: %s", tx_hash_resolve)
            
            event_args_resolved = await sapphire_client.get_event_from_receipt(
                tx_hash=tx_hash_resolve,
                contract_name_for_abi="MinimalPromiseKeeper",
                event_name="PromiseResolved"
            )
            
            if event_args_resolved:
                logger.info("PromiseResolved event: %s", event_args_resolved)
                logger.info("SUCCESS: Promise resolved successfully!")
            else:
                logger.warning("PromiseResolved event not found. Resolution might have failed.")
            
            print("-------------------------")
        
        if test_promise_id:
            logger.info("SUCCESS: All tested MinimalPromiseKeeper methods executed successfully.")
        else:
            logger.warning("PARTIAL SUCCESS or FAILURE: Not all MinimalPromiseKeeper methods completed successfully.")

    except Exception as e:
        logger.error("An error occurred during the MinimalPromiseKeeper test: %s", e, exc_info=True)
    finally:
        logger.info("MinimalPromiseKeeper Test Finished.")
        print("=========================")


if __name__ == "__main__":
    import os

    if not os.getenv("OASIS_PRIVATE_KEY"):
        print("Error: OASIS_PRIVATE_KEY not found. Please set it in your .env file or environment variables.")
    else:
        asyncio.run(main()) 