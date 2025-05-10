"""
Self-Promise Service Module.
This module ties together all components of the self-promise platform.
"""

import asyncio
import datetime
import logging
from typing import Dict, Any, List, Optional

from .terra_api.client import TerraApiClient
from .evaluator.interface import EvaluatorRegistry
from .tee.sapphire import create_sapphire_client, create_rofl_client, SecureDataHandler

# Get a logger for this module
logger = logging.getLogger(__name__)


class SelfPromiseService:
    """
    Service for managing self-promises.
    
    This service ties together all components of the self-promise platform:
    - Terra API for fitness data
    - Evaluator for promise evaluation
    - TEE for confidential computing
    - Smart contracts for token custody and resolution
    """

    def __init__(self,
                 network: Optional[str] = None,
                 private_key: Optional[str] = None,
                 evaluator_type: str = "rule_based"):
        """
        Initialize the self-promise service.
        
        Args:
            network: The network to connect to. Defaults to value from create_sapphire_client.
            private_key: The private key for signing transactions
            evaluator_type: The type of evaluator to use
        """
        # Initialize TEE clients
        self.sapphire_client = create_sapphire_client(network, private_key)
        self.rofl_client = create_rofl_client(network, private_key)
        self.secure_data_handler = SecureDataHandler(self.sapphire_client)

        # Initialize evaluator
        self.evaluator = EvaluatorRegistry.get_evaluator(evaluator_type)
        if not self.evaluator:
            raise ValueError(f"Evaluator type '{evaluator_type}' not found")

        # Contract addresses (to be set after deployment)
        self.deposit_contract_address = None
        self.promise_keeper_address = None

    def set_contract_addresses(self,
                               deposit_address: str,
                               promise_keeper_address: str) -> None:
        """
        Set the contract addresses.
        
        Args:
            deposit_address: The address of the deposit contract
            promise_keeper_address: The address of the promise keeper contract
        """
        self.deposit_contract_address = deposit_address
        self.promise_keeper_address = promise_keeper_address

    async def create_promise(self,
                       user_id: str,
                       template_id: int,
                       parameters: Dict[str, str],
                       start_date: datetime.datetime,
                       end_date: datetime.datetime,
                       deposit_amount: float,
                       failure_recipient: Optional[str] = None,
                       max_attempts: int = 3) -> Dict[str, Any]:
        """
        Create a new promise.
        
        Args:
            user_id: The ID of the user
            template_id: The ID of the template to use
            parameters: Custom parameters for the promise
            start_date: The start date of the promise
            end_date: The end date of the promise
            deposit_amount: The amount of ROSE to deposit
            failure_recipient: The address to send tokens to if the promise fails
            max_attempts: Maximum number of attempts to create the promise
            
        Returns:
            The created promise
        """
        # Convert parameters to the format expected by the contract
        param_keys = list(parameters.keys())
        param_values = [parameters[key] for key in param_keys]

        # Convert dates to Unix timestamps
        start_timestamp = int(start_date.timestamp())
        end_timestamp = int(end_date.timestamp())

        # Prepare the arguments for the createPromise transaction
        create_promise_args = [
            template_id,
            param_keys,
            param_values,
            start_timestamp,
            end_timestamp,
            failure_recipient or "0x0000000000000000000000000000000000000000"
        ]

        # Try to create the promise with multiple attempts if needed
        actual_promise_id = None
        create_promise_tx_hash = None
        
        for attempt in range(1, max_attempts + 1):
            try:
                # Check if the network is ready before sending the transaction
                network_ready = await self.sapphire_client.is_network_ready()
                if not network_ready and attempt < max_attempts:
                    # If network is not ready and we have more attempts, wait and retry
                    await asyncio.sleep(10 * attempt)  # Exponential backoff
                    continue
                
                # Create the promise in the contract
                create_promise_tx_hash = await self.sapphire_client.send_transaction(
                    contract_address=self.promise_keeper_address,
                    method_name="createPromise",
                    args=create_promise_args,
                    gas_limit=8000000,  # Increased gas limit for complex createPromise operation
                    check_network_ready=False  # We already checked above
                )

                # Get the actual promiseId from the PromiseCreated event
                event_args = await self.sapphire_client.get_event_from_receipt(
                    tx_hash=create_promise_tx_hash,
                    contract_name_for_abi="PromiseKeeper",
                    event_name="PromiseCreated",
                    max_attempts=3,  # Use fewer attempts for receipt waiting
                    initial_timeout=30  # Start with a 30-second timeout
                )

                if event_args and 'promiseId' in event_args:
                    actual_promise_id = event_args['promiseId']
                    break  # Success! Exit the retry loop
                
                # If we get here, the transaction was sent but we couldn't get the event
                # Wait before retrying
                await asyncio.sleep(5 * attempt)
                
            except Exception as e:
                if attempt == max_attempts:
                    # If this was our last attempt, re-raise the exception
                    raise
                # Otherwise log the error and retry
                logger.warning(
                    "Attempt %d/%d to create promise failed: %s. Retrying...",
                    attempt, max_attempts, e
                )
                await asyncio.sleep(5 * attempt)  # Wait before retrying
        
        # If we couldn't get a promise ID after all attempts, raise an exception
        if not actual_promise_id:
            raise Exception(
                f"Could not retrieve promiseId from PromiseCreated event after {max_attempts} attempts. "
                f"Last transaction hash: {create_promise_tx_hash}"
            )
        
        # Deposit tokens using the actual promiseId
        # Also use network readiness check and retry logic for deposit
        deposit_tx_hash = None
        for attempt in range(1, max_attempts + 1):
            try:
                deposit_tx_hash = await self.sapphire_client.send_transaction(
                    contract_address=self.deposit_contract_address,
                    method_name="deposit",
                    args=[actual_promise_id],  # Use the actual_promise_id from the event
                    value=int(deposit_amount * 10 ** 18),
                    gas_limit=6000000  # Use optimized gas limit for deposit operation
                )
                # If we get here, the deposit transaction was sent successfully
                break
            except Exception as e:
                if attempt == max_attempts:
                    # If this was our last attempt, re-raise the exception
                    raise
                # Otherwise log the error and retry
                logger.warning(
                    "Attempt %d/%d to deposit for promise failed: %s. Retrying...",
                    attempt, max_attempts, e
                )
                await asyncio.sleep(5 * attempt)  # Wait before retrying

        return {
            "promise_id": actual_promise_id,  # Return the actual bytes32 promiseId
            "user_id": user_id,
            "template_id": template_id,
            "parameters": parameters,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "deposit_amount": deposit_amount,
            "failure_recipient": failure_recipient,
            "tx_hash": deposit_tx_hash,  # This is the deposit tx_hash
            "create_tx_hash": create_promise_tx_hash  # Also return the create transaction hash for reference
        }

    async def evaluate_promise(self, promise_id: str, user_id: str) -> Dict[str, Any]:
        """
        Evaluate a promise.
        
        Args:
            promise_id: The ID of the promise to evaluate
            user_id: The ID of the user
            
        Returns:
            The evaluation result
        """
        # Get promise details from the contract
        promise_details = await self.sapphire_client.call_contract(
            contract_address=self.promise_keeper_address,
            method_name="getPromiseDetails",
            args=[promise_id]
        )

        # Extract promise parameters
        promise_type = promise_details["promiseType"]
        start_date = datetime.datetime.fromtimestamp(promise_details["startDate"])
        end_date = datetime.datetime.fromtimestamp(promise_details["endDate"])

        # Get parameters
        parameters = {}
        for key in ["frequency", "period", "heart_rate_threshold", "duration_minutes", "max_gap_days"]:
            value = await self.sapphire_client.call_contract(
                contract_address=self.promise_keeper_address,
                method_name="getPromiseParameter",
                args=[promise_id, key]
            )
            if value:
                parameters[key] = value

        # Construct the promise object
        promise = {
            "id": promise_id,
            "type": promise_type,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            **parameters
        }

        # Fetch evidence data from Terra API
        terra_client = TerraApiClient(user_id)

        evidence = {
            "heart_rate_data": terra_client.get_heart_rate_data(start_date, end_date),
            "exercise_sessions": terra_client.get_exercise_sessions(start_date, end_date),
            "elevated_hr_periods": terra_client.check_continuous_elevated_heart_rate(
                threshold=int(parameters.get("heart_rate_threshold", 120)),
                min_duration_minutes=int(parameters.get("duration_minutes", 25)),
                start_date=start_date,
                end_date=end_date
            )
        }

        # Perform the evaluation securely within the TEE
        def evaluate_in_tee(input_data):
            promise_data = input_data["promise"]
            evidence_data = input_data["evidence"]
            return self.evaluator.evaluate(promise_data, evidence_data)

        evaluation_result = await self.secure_data_handler.secure_compute(
            evaluate_in_tee,
            {
                "promise": promise,
                "evidence": evidence
            },
            attestation=True
        )

        # Submit the evaluation result to the contract
        tx_hash = await self.sapphire_client.send_transaction(
            self.promise_keeper_address,
            "evaluatePromise",
            [
                promise_id,
                evaluation_result["fulfilled"],
                int(evaluation_result["confidence"] * 100),
                evaluation_result["reasoning"]
            ]
        )

        # Resolve the promise
        resolve_tx_hash = await self.sapphire_client.send_transaction(
            self.promise_keeper_address,
            "resolvePromise",
            [promise_id]
        )

        return {
            "promise_id": promise_id,
            "user_id": user_id,
            "evaluation_result": evaluation_result,
            "evaluation_tx_hash": tx_hash,
            "resolve_tx_hash": resolve_tx_hash
        }

    async def get_promise_status(self, promise_id: str) -> Dict[str, Any]:
        """
        Get the status of a promise.
        
        Args:
            promise_id: The ID of the promise to check
            
        Returns:
            The promise status details
        """
        # Get promise details from the contract
        promise_details = await self.sapphire_client.call_contract(
            contract_address=self.promise_keeper_address,
            method_name="getPromiseDetails",
            args=[promise_id]
        )
        
        # Get evaluation history
        eval_count = await self.sapphire_client.call_contract(
            contract_address=self.promise_keeper_address,
            method_name="getPromiseEvaluationCount",
            args=[promise_id]
        )
        
        evaluation_history = []
        for i in range(eval_count):
            evaluation = await self.sapphire_client.call_contract(
                contract_address=self.promise_keeper_address,
                method_name="getPromiseEvaluation",
                args=[promise_id, i]
            )
            evaluation_history.append({
                "timestamp": datetime.datetime.fromtimestamp(evaluation["timestamp"]).isoformat(),
                "result": evaluation["result"],
                "evidence_cid": evaluation["evidenceCid"]
            })
            
        # Check if promise has been completed
        is_completed = await self.sapphire_client.call_contract(
            contract_address=self.promise_keeper_address,
            method_name="isPromiseCompleted",
            args=[promise_id]
        )
        
        # Check if promise requires evaluation
        needs_evaluation = await self.sapphire_client.call_contract(
            contract_address=self.promise_keeper_address,
            method_name="doesPromiseNeedEvaluation",
            args=[promise_id]
        )

        return {
            "promise_id": promise_id,
            "owner": promise_details["owner"],
            "template_id": promise_details["templateId"],
            "promise_type": promise_details["promiseType"],
            "start_date": datetime.datetime.fromtimestamp(promise_details["startDate"]).isoformat(),
            "end_date": datetime.datetime.fromtimestamp(promise_details["endDate"]).isoformat(),
            "resolved": promise_details["resolved"],
            "fulfilled": promise_details["fulfilled"],
            "evaluation_history": evaluation_history,
            "is_completed": is_completed,
            "needs_evaluation": needs_evaluation
        }

    @staticmethod
    def get_available_templates() -> List[Dict[str, Any]]:
        """
        Get available promise templates.
        
        Returns:
            A list of available templates
        """
        # In a real implementation, this would fetch templates from the contract
        # For the MVP, we'll return mock templates

        return [
            {
                "id": 1,
                "name": "Exercise Frequency",
                "description": "Promise to exercise a certain number of times per period",
                "promise_type": "exercise_frequency",
                "default_parameters": {
                    "frequency": "3",
                    "period": "week"
                }
            },
            {
                "id": 2,
                "name": "Exercise Duration",
                "description": "Promise to exercise with elevated heart rate for a minimum duration",
                "promise_type": "exercise_duration",
                "default_parameters": {
                    "heart_rate_threshold": "120",
                    "duration_minutes": "25",
                    "frequency": "1",
                    "period": "week"
                }
            },
            {
                "id": 3,
                "name": "Exercise Consistency",
                "description": "Promise to never go more than a certain number of days without exercise",
                "promise_type": "exercise_consistency",
                "default_parameters": {
                    "max_gap_days": "7"
                }
            }
        ]


def create_service(network: Optional[str] = None,
                   private_key: Optional[str] = None,
                   evaluator_type: str = "rule_based") -> SelfPromiseService:
    """
    Create a new self-promise service.
    
    Args:
        network: The network to connect to. Defaults to value from create_sapphire_client.
        private_key: The private key for signing transactions
        evaluator_type: The type of evaluator to use
        
    Returns:
        A new SelfPromiseService instance
    """
    # Create the service
    service = SelfPromiseService(
        network=network,
        private_key=private_key,
        evaluator_type=evaluator_type
    )
    
    return service


# Example usage
if __name__ == "__main__":
    # Create a service
    service = create_service()

    # Set mock contract addresses
    service.set_contract_addresses(
        "0x1234567890123456789012345678901234567890",
        "0x0987654321098765432109876543210987654321"
    )

    # Get available templates
    templates = service.get_available_templates()
    print(f"Available templates: {len(templates)}")

    # Create a promise
    user_id = "test_user_123"
    template_id = 2  # Exercise Duration
    parameters = {
        "heart_rate_threshold": "130",
        "duration_minutes": "30",
        "frequency": "2",
        "period": "week"
    }
    start_date = datetime.datetime.now()
    end_date = start_date + datetime.timedelta(days=30)
    deposit_amount = 100.0  # 100 ROSE

    promise = service.create_promise(
        user_id,
        template_id,
        parameters,
        start_date,
        end_date,
        deposit_amount
    )

    print(f"Created promise: {promise['promise_id']}")

    # Evaluate the promise (in a real scenario, this would happen after the end date)
    evaluation = service.evaluate_promise(promise["promise_id"], user_id)

    print(f"Evaluation result: {evaluation['evaluation_result']['fulfilled']}")
    print(f"Reasoning: {evaluation['evaluation_result']['reasoning']}")

    # Get promise status
    status = service.get_promise_status(promise["promise_id"])

    print(f"Promise status: {'Fulfilled' if status['fulfilled'] else 'Not fulfilled'}")
