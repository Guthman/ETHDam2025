"""
Test script to verify gas limit optimizations for contract deployments and interactions.
Focuses on PromiseDeposit and PromiseKeeper contracts.
"""

import logging
import sys
import pytest
import datetime
import asyncio
from src.tee.sapphire import SapphireClient
from dotenv import load_dotenv

load_dotenv()
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_promise_deposit_deployment():
    """Test deploying PromiseDeposit contract with optimized gas limits."""
    # Initialize SapphireClient
    sapphire_client = SapphireClient()

    # Deploy PromiseDeposit with explicitly named parameters
    logger.info("Deploying PromiseDeposit contract...")

    try:
        deposit_address = await sapphire_client.deploy_contract(
            contract_name="PromiseDeposit",
            constructor_args=[],
            # Using default_gas_limit from SapphireClient (6,000,000)
        )

        # Verify deployment
        logger.info("PromiseDeposit deployed at: %s", deposit_address)
        assert deposit_address is not None
        assert deposit_address.startswith("0x")

        # Log gas usage from the transaction receipt
        for contract_name, contract_info in sapphire_client.contracts.items():
            if contract_info.get("address") == deposit_address:
                logger.info("Gas used for PromiseDeposit deployment: %d",
                            contract_info.get("deploy_gas_used", "Unknown"))
                break

    except Exception as e:
        logger.error("PromiseDeposit deployment failed: %s", e, exc_info=True)
        pytest.fail(f"PromiseDeposit deployment failed: {e}")


@pytest.mark.asyncio
async def test_promise_keeper_deployment():
    """Test deploying PromiseKeeper contract with optimized gas limits."""
    # Initialize SapphireClient
    sapphire_client = SapphireClient()

    try:
        # Deploy PromiseKeeper with explicitly named parameters
        logger.info("Deploying PromiseKeeper contract...")

        keeper_address = await sapphire_client.deploy_contract(
            contract_name="PromiseKeeper",
            constructor_args=None,  # No args needed
            # Using default_gas_limit from SapphireClient (6,000,000)
        )

        # Verify deployment
        logger.info("PromiseKeeper deployed at: %s", keeper_address)
        assert keeper_address is not None
        assert keeper_address.startswith("0x")

        # Log gas usage from the transaction receipt
        for contract_name, contract_info in sapphire_client.contracts.items():
            if contract_info.get("address") == keeper_address:
                logger.info("Gas used for PromiseKeeper deployment: %d",
                            contract_info.get("deploy_gas_used", "Unknown"))
                break

    except Exception as e:
        logger.error("PromiseKeeper deployment failed: %s", e, exc_info=True)
        pytest.fail(f"PromiseKeeper deployment failed: {e}")


@pytest.mark.asyncio
async def test_promise_creation_with_high_gas():
    """Test creating a promise with optimized gas limits."""
    # Initialize SapphireClient
    sapphire_client = SapphireClient()

    try:
        # Deploy both contracts
        deposit_address = await sapphire_client.deploy_contract(
            contract_name="PromiseDeposit",
            constructor_args=[]
        )

        keeper_address = await sapphire_client.deploy_contract(
            contract_name="PromiseKeeper",
            constructor_args=None
        )

        # Set deposit contract on keeper
        tx_hash_set_deposit = await sapphire_client.send_transaction(
            contract_address=keeper_address,
            method_name="setDepositContract",
            args=[deposit_address],
            gas_limit=6000000  # Explicitly set gas limit
        )

        # Create a promise with high gas limit
        template_id = 1  # Assuming template ID 1 exists from _createDefaultTemplates
        param_keys = []
        param_values = []
        start_date_ts = int(datetime.datetime.now().timestamp())
        end_date_ts = int((datetime.datetime.now() + datetime.timedelta(days=7)).timestamp())
        failure_recipient = "0x000000000000000000000000000000000000dEaD"

        tx_hash_create_promise = await sapphire_client.send_transaction(
            contract_address=keeper_address,
            method_name="createPromise",
            args=[
                template_id,
                param_keys,
                param_values,
                start_date_ts,
                end_date_ts,
                failure_recipient
            ],
            gas_limit=8000000  # Higher gas limit for complex operation
        )

        # Wait for receipt and get the event
        logger.info("Waiting for receipt of createPromise transaction: %s", tx_hash_create_promise)

        # Ensure we have the ABI for the PromiseKeeper contract
        if "PromiseKeeper" not in sapphire_client.contracts:
            pk_abi, _ = await sapphire_client.compile_contract("PromiseKeeper")
            sapphire_client.contracts["PromiseKeeper"] = {"address": keeper_address, "abi": pk_abi}

        event_args = await sapphire_client.get_event_from_receipt(
            tx_hash=tx_hash_create_promise,
            contract_name_for_abi="PromiseKeeper",
            event_name="PromiseCreated"
        )

        # Verify promise was created
        assert event_args is not None
        assert 'promiseId' in event_args
        promise_id = event_args['promiseId']

        logger.info("Promise created with ID: %s",
                    promise_id.hex() if isinstance(promise_id, bytes) else promise_id)

        # Verify promise details
        promise_details = await sapphire_client.call_contract(
            contract_address=keeper_address,
            method_name="getPromiseDetails",
            args=[promise_id]
        )

        assert promise_details is not None
        assert promise_details["templateId"] == template_id
        assert promise_details["startDate"] == start_date_ts
        assert promise_details["endDate"] == end_date_ts

        # Get gas usage from receipt
        receipt = await sapphire_client.w3.eth.get_transaction_receipt(tx_hash_create_promise)
        logger.info("Gas used for createPromise: %d", receipt.gasUsed)
        logger.info("Gas efficiency: %.2f%%", (receipt.gasUsed / 8000000) * 100)

    except Exception as e:
        logger.error("Promise creation test failed: %s", e, exc_info=True)
        pytest.fail(f"Promise creation test failed: {e}")


@pytest.mark.asyncio
async def test_promise_evaluation_with_high_gas():
    """Test evaluating a promise with optimized gas limits."""
    # This test will be more complex and depends on the actual evaluation logic
    # Simplified version for testing gas limits

    # Initialize SapphireClient
    sapphire_client = SapphireClient()

    try:
        # Deploy both contracts
        deposit_address = await sapphire_client.deploy_contract(
            contract_name="PromiseDeposit",
            constructor_args=[]
        )

        keeper_address = await sapphire_client.deploy_contract(
            contract_name="PromiseKeeper",
            constructor_args=None
        )

        # Set deposit contract on keeper
        await sapphire_client.send_transaction(
            contract_address=keeper_address,
            method_name="setDepositContract",
            args=[deposit_address]
        )

        # Create a promise
        template_id = 1
        param_keys = []
        param_values = []
        start_date_ts = int(datetime.datetime.now().timestamp())
        end_date_ts = int((datetime.datetime.now() + datetime.timedelta(days=7)).timestamp())
        failure_recipient = "0x000000000000000000000000000000000000dEaD"

        tx_hash_create = await sapphire_client.send_transaction(
            contract_address=keeper_address,
            method_name="createPromise",
            args=[
                template_id,
                param_keys,
                param_values,
                start_date_ts,
                end_date_ts,
                failure_recipient
            ],
            gas_limit=8000000
        )

        # Get promise ID from event
        event_args = await sapphire_client.get_event_from_receipt(
            tx_hash=tx_hash_create,
            contract_name_for_abi="PromiseKeeper",
            event_name="PromiseCreated"
        )

        promise_id = event_args['promiseId']

        # Evaluate the promise (simplified - just set a result directly)
        # In a real application, this would be more complex and involve fetching evidence
        tx_hash_evaluate = await sapphire_client.send_transaction(
            contract_address=keeper_address,
            method_name="recordEvaluation",
            args=[
                promise_id,
                True,  # Result (success)
                "ipfs://QmSampleCidForEvidence"  # Sample IPFS CID for evidence
            ],
            gas_limit=7000000  # High gas limit for evaluation
        )

        # Get receipt and check gas usage
        receipt = await sapphire_client.w3.eth.get_transaction_receipt(tx_hash_evaluate)
        logger.info("Gas used for promise evaluation: %d", receipt.gasUsed)
        logger.info("Gas efficiency: %.2f%%", (receipt.gasUsed / 7000000) * 100)

        # Verify evaluation was recorded
        is_completed = await sapphire_client.call_contract(
            contract_address=keeper_address,
            method_name="isPromiseCompleted",
            args=[promise_id]
        )

        assert is_completed is True, "Promise should be marked as completed after evaluation"

    except Exception as e:
        logger.error("Promise evaluation test failed: %s", e, exc_info=True)
        pytest.fail(f"Promise evaluation test failed: {e}")


if __name__ == "__main__":
    # This allows running the tests directly without pytest
    asyncio.run(test_promise_deposit_deployment())
    asyncio.run(test_promise_keeper_deployment())
    asyncio.run(test_promise_creation_with_high_gas())
    asyncio.run(test_promise_evaluation_with_high_gas())
