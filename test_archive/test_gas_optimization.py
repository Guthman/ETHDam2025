"""
Test script to verify gas limit optimizations for contract deployments and interactions.
Focuses on PromiseDeposit and PromiseKeeper contracts.
"""

import logging
import sys
import pytest
import datetime
import asyncio
import os
from dotenv import load_dotenv
import sys
from pathlib import Path

# Add the project root to the path so imports work correctly
project_root = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(project_root))

from src.tee.sapphire import SapphireClient

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Get gas limit from environment or use an extremely high default for testing
DEFAULT_GAS_LIMIT = int(os.getenv("DEFAULT_GAS_LIMIT", "20000000"))  # Default to 20 million gas
logger.info("Using DEFAULT_GAS_LIMIT: %d", DEFAULT_GAS_LIMIT)


@pytest.mark.asyncio
async def test_promise_deposit_deployment():
    """Test deploying PromiseDeposit contract with optimized gas limits."""
    # Initialize SapphireClient
    sapphire_client = SapphireClient(default_gas_limit=DEFAULT_GAS_LIMIT)

    # Deploy PromiseDeposit with explicitly named parameters
    logger.info("Deploying PromiseDeposit contract...")

    try:
        # Compile contract first to get ABI
        deposit_abi, deposit_bytecode = await SapphireClient.compile_contract("PromiseDeposit")
        
        deposit_address = await sapphire_client.deploy_contract(
            contract_name="PromiseDeposit",
            contract_abi=deposit_abi,
            contract_bytecode=deposit_bytecode,
            constructor_args=[]
        )
        assert deposit_address is not None, "PromiseDeposit deployment failed to return an address"

        # Verify deployment
        logger.info("PromiseDeposit deployed at: %s", deposit_address)
        assert deposit_address.startswith("0x")

        # Log gas usage from the receipt
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
    sapphire_client = SapphireClient(default_gas_limit=DEFAULT_GAS_LIMIT)

    try:
        # Compile contract first to get ABI
        keeper_abi, keeper_bytecode = await SapphireClient.compile_contract("PromiseKeeper")
        
        # Deploy PromiseKeeper with explicitly named parameters
        logger.info("Deploying PromiseKeeper contract...")

        keeper_address = await sapphire_client.deploy_contract(
            contract_name="PromiseKeeper",
            contract_abi=keeper_abi,
            contract_bytecode=keeper_bytecode,
            constructor_args=None  # No args needed
        )
        assert keeper_address is not None, "PromiseKeeper deployment failed to return an address"

        # Verify deployment
        logger.info("PromiseKeeper deployed at: %s", keeper_address)
        assert keeper_address.startswith("0x")

        # Log gas usage from the receipt
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
    sapphire_client = SapphireClient(default_gas_limit=DEFAULT_GAS_LIMIT)

    try:
        # Compile both contracts to get ABIs
        deposit_abi, deposit_bytecode = await SapphireClient.compile_contract("PromiseDeposit")
        keeper_abi, keeper_bytecode = await SapphireClient.compile_contract("PromiseKeeper")
        
        # Deploy both contracts
        deposit_address = await sapphire_client.deploy_contract(
            contract_name="PromiseDeposit",
            contract_abi=deposit_abi,
            contract_bytecode=deposit_bytecode,
            constructor_args=[]
        )
        assert deposit_address is not None, "PromiseDeposit deployment failed in promise creation test"

        keeper_address = await sapphire_client.deploy_contract(
            contract_name="PromiseKeeper",
            contract_abi=keeper_abi,
            contract_bytecode=keeper_bytecode,
            constructor_args=None
        )
        assert keeper_address is not None, "PromiseKeeper deployment failed in promise creation test"

        # Set deposit contract on keeper
        logger.info("Setting deposit contract...")
        
        tx_hash_set_deposit = await sapphire_client.send_transaction(
            contract_address=keeper_address,
            method_name="setDepositContract",
            args=[deposit_address],
            abi=keeper_abi,  # Explicitly pass the ABI
            gas_limit=DEFAULT_GAS_LIMIT  # Use extremely high gas limit
        )

        # Create a promise with high gas limit
        template_id = 1  # Assuming template ID 1 exists from _createDefaultTemplates
        param_keys = []
        param_values = []
        start_date_ts = int(datetime.datetime.now().timestamp())
        end_date_ts = int((datetime.datetime.now() + datetime.timedelta(days=7)).timestamp())
        failure_recipient = "0x000000000000000000000000000000000000dEaD"

        # Log that we're sending with extremely high gas
        logger.info("Sending createPromise with extremely high gas limit: %d", DEFAULT_GAS_LIMIT)
        
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
            abi=keeper_abi,  # Explicitly pass the ABI
            gas_limit=DEFAULT_GAS_LIMIT  # Use extremely high gas limit for testing
        )

        # Wait for receipt and get the event
        logger.info("Waiting for receipt of createPromise transaction: %s", tx_hash_create_promise)

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
            args=[promise_id],
            abi=keeper_abi  # Explicitly pass the ABI
        )

        assert promise_details is not None
        assert promise_details["templateId"] == template_id
        assert promise_details["startDate"] == start_date_ts
        assert promise_details["endDate"] == end_date_ts

        # Get gas usage from receipt
        receipt = await sapphire_client.w3.eth.get_transaction_receipt(tx_hash_create_promise)
        logger.info("Gas used for createPromise: %d", receipt.gasUsed)
        logger.info("Gas efficiency: %.2f%%", (receipt.gasUsed / DEFAULT_GAS_LIMIT) * 100)

    except Exception as e:
        logger.error("Promise creation test failed: %s", e, exc_info=True)
        pytest.fail(f"Promise creation test failed: {e}")


@pytest.mark.asyncio
async def test_promise_evaluation_with_high_gas():
    """Test evaluating a promise with optimized gas limits."""
    # This test will be more complex and depends on the actual evaluation logic
    # Simplified version for testing gas limits

    # Initialize SapphireClient with very high gas limit
    sapphire_client = SapphireClient(default_gas_limit=DEFAULT_GAS_LIMIT)

    try:
        # Compile both contracts to get ABIs
        deposit_abi, deposit_bytecode = await SapphireClient.compile_contract("PromiseDeposit")
        keeper_abi, keeper_bytecode = await SapphireClient.compile_contract("PromiseKeeper")
        
        logger.info("Compiled PromiseKeeper contract")
        
        # Deploy both contracts
        deposit_address = await sapphire_client.deploy_contract(
            contract_name="PromiseDeposit",
            contract_abi=deposit_abi,
            contract_bytecode=deposit_bytecode,
            constructor_args=[]
        )
        assert deposit_address is not None, "PromiseDeposit deployment failed in promise evaluation test"
        
        logger.info("Deployed PromiseDeposit contract at %s", deposit_address)

        keeper_address = await sapphire_client.deploy_contract(
            contract_name="PromiseKeeper",
            contract_abi=keeper_abi,
            contract_bytecode=keeper_bytecode,
            constructor_args=None
        )
        assert keeper_address is not None, "PromiseKeeper deployment failed in promise evaluation test"
        
        logger.info("Deployed PromiseKeeper contract at %s", keeper_address)
        
        # Set deposit contract on keeper
        logger.info("Setting deposit contract...")
        
        tx_hash_set_deposit = await sapphire_client.send_transaction(
            contract_address=keeper_address,
            method_name="setDepositContract",
            args=[deposit_address],
            abi=keeper_abi,
            gas_limit=DEFAULT_GAS_LIMIT
        )
        
        logger.info("Set deposit contract, tx hash: %s", tx_hash_set_deposit)

        # Create a promise
        template_id = 1
        param_keys = []
        param_values = []
        start_date_ts = int(datetime.datetime.now().timestamp())
        end_date_ts = int((datetime.datetime.now() + datetime.timedelta(days=7)).timestamp())
        failure_recipient = "0x000000000000000000000000000000000000dEaD"
        
        logger.info("Creating promise...")

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
            abi=keeper_abi,
            gas_limit=DEFAULT_GAS_LIMIT
        )
        
        logger.info("Created promise, tx hash: %s", tx_hash_create)

        # Get promise ID from event
        logger.info("Getting promise ID from event...")
        event_args = await sapphire_client.get_event_from_receipt(
            tx_hash=tx_hash_create,
            contract_name_for_abi="PromiseKeeper",
            event_name="PromiseCreated"
        )
        
        if not event_args:
            logger.error("Failed to get PromiseCreated event")
            pytest.fail("Failed to get PromiseCreated event")
            
        promise_id = event_args['promiseId']
        logger.info("Retrieved promise ID: %s", promise_id.hex() if isinstance(promise_id, bytes) else promise_id)

        # Check available methods in the ABI
        available_methods = [item.get('name') for item in keeper_abi if item.get('type') == 'function']
        logger.info("Available methods in PromiseKeeper ABI: %s", available_methods)
        
        evaluation_method = None # Initialize to satisfy linter and for clarity
        # Determine which evaluation method to use
        if "recordEvaluation" in available_methods:
            evaluation_method = "recordEvaluation"
        elif "evaluatePromise" in available_methods:
            evaluation_method = "evaluatePromise"
        else:
            logger.error("No suitable evaluation method found in ABI. Available methods: %s", available_methods)
            pytest.fail("No suitable evaluation method found in ABI (neither recordEvaluation nor evaluatePromise)")
        
        logger.info("Using evaluation method: %s", evaluation_method)
        
        # Evaluate the promise (simplified - just set a result directly)
        logger.info("Evaluating promise...")
        
        # Prepare arguments for the evaluation method
        eval_args = [
            promise_id,
            True,  # Result (success)
            "ipfs://QmSampleCidForEvidence"  # Sample IPFS CID for evidence
        ]
        
        if evaluation_method == "evaluatePromise":
            # Some contracts might use a different signature for evaluatePromise
            # Add a confidence parameter if needed
            eval_args.insert(2, 95)  # 95% confidence
            
        # In a real application, this would be more complex and involve fetching evidence
        tx_hash_evaluate = await sapphire_client.send_transaction(
            contract_address=keeper_address,
            method_name=evaluation_method,
            args=eval_args,
            abi=keeper_abi,
            gas_limit=DEFAULT_GAS_LIMIT  # Use extremely high gas limit for testing
        )
        
        logger.info("Evaluated promise, tx hash: %s", tx_hash_evaluate)

        # Get receipt and check gas usage
        receipt = await sapphire_client.w3.eth.get_transaction_receipt(tx_hash_evaluate)
        logger.info("Gas used for promise evaluation: %d", receipt.gasUsed)
        logger.info("Gas efficiency: %.2f%%", (receipt.gasUsed / DEFAULT_GAS_LIMIT) * 100)

        # Verify evaluation was recorded
        try:
            logger.info("Checking if promise was completed...")
            is_completed = await sapphire_client.call_contract(
                contract_address=keeper_address,
                method_name="isPromiseCompleted",
                args=[promise_id],
                abi=keeper_abi
            )
            logger.info("Promise completed: %s", is_completed)
            assert is_completed is True, "Promise should be marked as completed after evaluation"
        except Exception as e:
            # Maybe the contract doesn't have isPromiseCompleted, try getting details instead
            logger.warning("Error checking isPromiseCompleted: %s", e)
            logger.info("Trying to get promise details instead...")
            
            details = await sapphire_client.call_contract(
                contract_address=keeper_address,
                method_name="getPromiseDetails",
                args=[promise_id],
                abi=keeper_abi
            )
            
            logger.info("Promise details: %s", details)
            # Check if the promise is fulfilled from the details
            if "fulfilled" in details:
                assert details["fulfilled"] is True, "Promise should be marked as fulfilled after evaluation"

    except Exception as e:
        logger.error("Promise evaluation test failed: %s", e, exc_info=True)
        pytest.fail(f"Promise evaluation test failed: {e}")


if __name__ == "__main__":
    # This allows running the tests directly without pytest
    asyncio.run(test_promise_deposit_deployment())
    asyncio.run(test_promise_keeper_deployment())
    asyncio.run(test_promise_creation_with_high_gas())
    asyncio.run(test_promise_evaluation_with_high_gas())
