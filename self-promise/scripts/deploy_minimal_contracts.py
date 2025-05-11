import logging
import sys
import asyncio
import json
import os
from dotenv import load_dotenv

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

load_dotenv()

# Assuming SapphireClient is in src.tee.sapphire
# Adjust the import path if your SapphireClient is located elsewhere
try:
    from src.tee.sapphire import SapphireClient
except ImportError:
    logger.error("Failed to import SapphireClient. Make sure it's in src/tee/sapphire.py and your PYTHONPATH is set up if needed.")
    sys.exit(1)

ADDRESSES_FILE = "deployed_addresses.json"

async def main():
    """
    Deploys MinimalPromiseDeposit and MinimalPromiseKeeper contracts,
    links them, and saves their addresses.
    """
    logger.info("Starting deployment of minimal contracts...")
    print("==============================================")

    if not os.getenv("OASIS_PRIVATE_KEY"):
        logger.error("OASIS_PRIVATE_KEY not found in .env file or environment variables.")
        print("Please ensure OASIS_PRIVATE_KEY is set.")
        return

    try:
        # Ensure OASIS_NETWORK is set to localnet in .env or SapphireClient defaults to it
        # Forcing localnet if not specified, or ensuring the client is configured for it.
        # The SapphireClient should ideally pick this up from .env (OASIS_NETWORK=localnet)
        sapphire_client = SapphireClient() # Assumes client defaults to localnet or reads from .env
        logger.info("SapphireClient initialized.") # Simplified logging
        logger.info("Deployer account: %s", sapphire_client.account.address)

    except Exception as e:
        logger.error("Failed to initialize SapphireClient: %s", e, exc_info=True)
        return

    deployed_data = {}

    try:
        # Step 1: Deploy MinimalPromiseDeposit
        logger.info("Step 1: Deploying MinimalPromiseDeposit contract...")
        deposit_address = await sapphire_client.deploy_contract(
            contract_name="MinimalPromiseDeposit", # Ensure this matches your contract's filename/name
            constructor_args=[]
        )
        logger.info("MinimalPromiseDeposit deployed at: %s", deposit_address)
        deployed_data["MinimalPromiseDeposit"] = deposit_address
        print("----------------------------------------------")

        # Step 2: Deploy MinimalPromiseKeeper
        logger.info("Step 2: Deploying MinimalPromiseKeeper contract...")
        promise_keeper_address = await sapphire_client.deploy_contract(
            contract_name="MinimalPromiseKeeper", # Ensure this matches your contract's filename/name
            constructor_args=[] # MinimalPromiseKeeper constructor takes no args
        )
        logger.info("MinimalPromiseKeeper deployed at: %s", promise_keeper_address)
        deployed_data["MinimalPromiseKeeper"] = promise_keeper_address
        print("----------------------------------------------")

        # Step 3: Call setDepositContract on MinimalPromiseKeeper
        logger.info(
            "Step 3: Calling setDepositContract on MinimalPromiseKeeper (%s) with MinimalPromiseDeposit address (%s)...",
            promise_keeper_address, deposit_address
        )

        # Ensure ABI for MinimalPromiseKeeper is loaded for transaction and event parsing
        if "MinimalPromiseKeeper" not in sapphire_client.contracts or \
           sapphire_client.contracts["MinimalPromiseKeeper"].get("address") != promise_keeper_address:
            pk_abi, _ = await sapphire_client.compile_contract("MinimalPromiseKeeper")
            sapphire_client.contracts["MinimalPromiseKeeper"] = {"address": promise_keeper_address, "abi": pk_abi}
            logger.info("Loaded ABI for MinimalPromiseKeeper.")


        tx_hash_set_deposit = await sapphire_client.send_transaction(
            contract_address=promise_keeper_address,
            method_name="setDepositContract",
            args=[deposit_address],
        )
        logger.info("Transaction sent for setDepositContract: %s", tx_hash_set_deposit)

        logger.info("Waiting for receipt of setDepositContract transaction...")
        event_args_deposit_updated = await sapphire_client.get_event_from_receipt(
            tx_hash=tx_hash_set_deposit,
            contract_name_for_abi="MinimalPromiseKeeper",
            event_name="DepositContractUpdated"
        )

        if event_args_deposit_updated:
            logger.info("DepositContractUpdated event received: %s", event_args_deposit_updated)
            if event_args_deposit_updated.get('newAddress') == deposit_address:
                logger.info("Successfully set deposit contract on MinimalPromiseKeeper.")
            else:
                logger.error("DepositContractUpdated event shows incorrect newAddress: %s", event_args_deposit_updated)
        else:
            logger.warning(
                "DepositContractUpdated event not found. Transaction might have failed or event processing issue."
            )
        print("----------------------------------------------")

        # Save deployed addresses to a file
        with open(ADDRESSES_FILE, "w") as f:
            json.dump(deployed_data, f, indent=4)
        logger.info("Deployed contract addresses saved to %s", ADDRESSES_FILE)
        print(f"Deployed contract addresses saved to {ADDRESSES_FILE}")
        
        logger.info("Deployment script finished successfully.")

    except Exception as e:
        logger.error("An error occurred during the deployment: %s", e, exc_info=True)
        # Save any addresses that were deployed before the error
        if deployed_data:
            with open(ADDRESSES_FILE, "w") as f:
                json.dump(deployed_data, f, indent=4)
            logger.info("Partially deployed contract addresses saved to %s", ADDRESSES_FILE)


    finally:
        logger.info("Deployment script finished.")
        print("==============================================")


if __name__ == "__main__":
    asyncio.run(main()) 