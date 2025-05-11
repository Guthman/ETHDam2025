#!/usr/bin/env python
"""
Self-Promise CLI: Make and keep promises with financial accountability on Oasis Sapphire.
"""
import click
import json
import os
import time
import webbrowser
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime, timedelta

# --- Configuration and Service Initialization ---

_CLI_TEST_CONFIG_DIR_OVERRIDE = None

_service_instance = None


def get_service():
    """
    Initializes and returns the SelfPromiseService instance.
    For MVP, this might return a mock or simplified service.
    """
    global _service_instance
    if _service_instance is None:
        load_dotenv(dotenv_path=Path('.') / '.env')  # Ensure .env variables are loaded

        # --- Mock Service for CLI Development ---
        class MockSelfPromiseService:
            def __init__(self):
                self.config = {}
                self.rofl_evaluator_id = None
                self.deployed_addresses = self._load_deployed_addresses()
                self.user_private_key = os.getenv("OASIS_PRIVATE_KEY")
                self.network = os.getenv("OASIS_NETWORK", "localnet")
                click.echo(f"MockService: Initialized for network '{self.network}'.")
                if not self.user_private_key:
                    click.echo("MockService: WARNING - OASIS_PRIVATE_KEY not found in .env", err=True)

            def _load_deployed_addresses(self):
                try:
                    with open("deployed_addresses.json", "r") as f:
                        return json.load(f)
                except FileNotFoundError:
                    click.echo(
                        "MockService: WARNING - deployed_addresses.json not found. Contract interactions will fail.",
                        err=True)
                    return {}
                except json.JSONDecodeError:
                    click.echo("MockService: ERROR - Could not parse deployed_addresses.json.", err=True)
                    return {}

            def set_contract_addresses(self, deposit_address, promise_keeper_address):
                self.config['deposit_address'] = deposit_address
                self.config['promise_keeper_address'] = promise_keeper_address
                click.echo(f"MockService: Deposit Address set to {deposit_address}")
                click.echo(f"MockService: Promise Keeper Address set to {promise_keeper_address}")

            def set_rofl_evaluator_id(self, rofl_id):
                self.rofl_evaluator_id = rofl_id
                click.echo(f"MockService: ROFL Evaluator ID set to {rofl_id}")

            def create_promise(self, user_id, template_id, parameters, start_date, end_date, deposit_amount,
                               auto_evidence):
                click.echo(f"MockService: Creating promise for user '{user_id}' with template_id {template_id}.")
                click.echo(f"MockService: Parameters: {parameters}")
                click.echo(
                    f"MockService: Dates: {start_date} to {end_date}, Deposit: {deposit_amount}, Auto-Evidence: {auto_evidence}")
                # Simulate blockchain interaction
                time.sleep(1)
                promise_id = f"mock_promise_{int(time.time())}"
                click.echo(f"MockService: Promise '{promise_id}' created on mock blockchain.")
                return {"promise_id": promise_id, "status": "Pending", "auto_evidence": auto_evidence}

            def get_promise_details(self, promise_id):
                click.echo(f"MockService: Fetching details for promise '{promise_id}'.")
                # Simulate fetching
                return {"promise_id": promise_id, "status": "Pending", "details": "Mock promise details",
                        "deposit": "50 ROSE"}

            def submit_evidence_to_rofl(self, promise_id, evidence_data):
                click.echo(
                    f"MockService: Submitting evidence for promise '{promise_id}' to ROFL (ID: {self.rofl_evaluator_id}).")
                click.echo(f"MockService: Evidence: {evidence_data}")
                # Simulate ROFL call
                time.sleep(1)
                click.echo(f"MockService: ROFL evaluation triggered for '{promise_id}'.")
                return {"status": "processing", "rofl_call_id": f"mock_rofl_call_{int(time.time())}"}

            def get_promise_status(self, promise_id):
                click.echo(f"MockService: Getting status for promise '{promise_id}'.")
                # Simulate status check
                return {"promise_id": promise_id, "status": "Fulfilled",
                        "evaluation_details": "Mock evaluation: Conditions met."}

            def withdraw_collateral(self, promise_id):
                click.echo(f"MockService: Withdrawing collateral for promise '{promise_id}'.")
                time.sleep(1)
                return f"mock_tx_hash_withdraw_{int(time.time())}"

        _service_instance = MockSelfPromiseService()

        # Load contract addresses from deployed_addresses.json
        # This part would typically be handled by your actual service initialization
        # based on the current network (localnet, testnet, mainnet)
        config_path = Path("deployed_addresses.json")
        if config_path.exists():
            try:
                with open(config_path, "r") as f:
                    addresses = json.load(f)
                # Choose appropriate addresses (e.g., Minimal for dev)
                deposit_addr = addresses.get("MinimalPromiseDeposit", addresses.get("PromiseDeposit"))
                keeper_addr = addresses.get("MinimalPromiseKeeper", addresses.get("PromiseKeeper"))
                rofl_id = addresses.get("RoflPromiseEvaluator")

                if deposit_addr and keeper_addr:
                    _service_instance.set_contract_addresses(
                        deposit_address=deposit_addr,
                        promise_keeper_address=keeper_addr
                    )
                else:
                    click.echo("MockService: WARNING - Core contract addresses not found in deployed_addresses.json.",
                               err=True)

                if rofl_id:
                    _service_instance.set_rofl_evaluator_id(rofl_id)
                else:
                    click.echo("MockService: WARNING - RoflPromiseEvaluator ID not found in deployed_addresses.json.",
                               err=True)

            except json.JSONDecodeError:
                click.echo(f"ERROR: Could not parse {config_path}. Please ensure it's valid JSON.", err=True)
            except FileNotFoundError:
                click.echo(f"WARNING: {config_path} not found. Contract interactions may fail.", err=True)
        else:
            click.echo(f"WARNING: {config_path} not found. Needed for contract addresses.", err=True)

    return _service_instance


# --- Helper Functions for Tracker Management ---
def get_config_dir() -> Path:
    """Returns the path to the application's config directory."""
    global _CLI_TEST_CONFIG_DIR_OVERRIDE
    if _CLI_TEST_CONFIG_DIR_OVERRIDE:
        config_dir = Path(_CLI_TEST_CONFIG_DIR_OVERRIDE)
    else:
        config_dir = Path.home() / ".self-promise"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def save_tracker_config(data: dict):
    """Saves tracker configuration."""
    config_file = get_config_dir() / "trackers.json"
    with open(config_file, "w") as f:
        json.dump(data, f, indent=2)
    click.echo(f"Tracker configuration saved to {config_file}")


def load_tracker_config() -> dict | None:
    """Loads tracker configuration."""
    config_file = get_config_dir() / "trackers.json"
    if config_file.exists():
        with open(config_file, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                click.echo(f"Error: Could not parse tracker config at {config_file}", err=True)
                return None
    return None


# --- CLI Commands ---

@click.group()
@click.version_option(version="0.1.0", prog_name="self-promise")  # Update version as needed
def cli():
    """
    Self-Promise: Make and keep promises with financial accountability on Oasis Sapphire.
    Your private key (OASIS_PRIVATE_KEY) and network (OASIS_NETWORK)
    should be set in a .env file in the current directory.
    """
    pass  # Main CLI group


@cli.command()
@click.option('--provider', type=click.Choice(['fitbit', 'mockfit'], case_sensitive=False), default='mockfit',
              help="Fitness data provider (use 'mockfit' for the MVP). Default: mockfit.")
def connect_tracker(provider: str):
    """Connect your fitness tracker to automatically provide evidence data."""
    click.echo(f"Attempting to connect with {provider}...")

    if provider == 'fitbit':
        # For a real app, get these from config or env vars
        client_id = os.getenv("FITBIT_CLIENT_ID", "YOUR_FITBIT_CLIENT_ID_HERE")
        if client_id == "YOUR_FITBIT_CLIENT_ID_HERE":
            click.echo("WARNING: FITBIT_CLIENT_ID not set. Using placeholder.", err=True)

        redirect_uri = "http://localhost:8000/callback"  # Example callback, needs a listener for real flow
        # Define scopes based on what data your promise templates need
        scope = "activity heartrate profile"  # Add more as needed, e.g., sleep, nutrition

        auth_url = (f"https://www.fitbit.com/oauth2/authorize?response_type=code"
                    f"&client_id={client_id}&redirect_uri={redirect_uri}&scope={scope}"
                    f"&code_challenge_method=S256&code_challenge=E9Melhoa2OwvFrEMTJgCHaoeK1t8URWbuGJSstw-cM")  # Example PKCE, generate dynamically

        click.echo("Opening FitBit authorization page in your browser...")
        click.echo(f"URL: {auth_url}")
        click.echo("If your browser does not open, please copy the URL above and paste it manually.")
        webbrowser.open(auth_url)

        click.echo("\n--- Fitbit Authorization ---")
        click.echo("After authorizing in your browser, Fitbit would redirect to your local callback URI.")
        click.echo("For this MVP, we will simulate a successful authorization after a short delay.")
        click.echo(
            "In a real application, the CLI would need to listen for the callback or have the user paste the auth code.")
        time.sleep(3)  # Simulate user authorizing and callback

        # Mock successful authorization
        token_data = {
            "access_token": f"mock_fitbit_access_token_{int(time.time())}",
            "refresh_token": f"mock_fitbit_refresh_token_{int(time.time())}",
            "expires_at": int(time.time()) + 28800,  # Fitbit tokens typically last 8 hours
            "provider": "fitbit",
            "user_id": "mock_fitbit_user_id"  # From Fitbit OAuth response
        }
        save_tracker_config(token_data)
        click.echo(f"SUCCESS: Fitbit tracker (mock) connected successfully!")

    elif provider == 'mockfit':
        token_data = {
            "access_token": f"mock_access_token_{int(time.time())}",
            "refresh_token": f"mock_refresh_token_{int(time.time())}",
            "expires_at": int(time.time()) + 86400,  # 24 hours from now
            "provider": "mockfit"
        }
        save_tracker_config(token_data)
        click.echo(f"SUCCESS: Mockfit tracker connected successfully!")
    else:
        click.echo(f"Error: Unknown provider '{provider}'.", err=True)


@cli.command()
@click.option('--template-id', required=True, type=int, help="ID of the promise template.")
@click.option('--parameters', required=True,
              help='JSON string of promise parameters (e.g., "{"duration_minutes": "30"}").')
@click.option('--start-date', required=True, type=click.DateTime(formats=["%Y-%m-%d"]),
              help="Start date in YYYY-MM-DD format.")
@click.option('--end-date', required=True, type=click.DateTime(formats=["%Y-%m-%d"]),
              help="End date in YYYY-MM-DD format.")
@click.option('--deposit-amount', required=True, type=float, help="Amount of ROSE to deposit.")
@click.option('--auto-evidence/--no-auto-evidence', 'auto_evidence_flag', default=True,
              help="Attempt to use connected fitness tracker for evidence. Default: True.")
def create_promise(template_id: int, parameters: str, start_date: datetime, end_date: datetime, deposit_amount: float,
                   auto_evidence_flag: bool):
    """Creates a new self-promise."""
    service = get_service()  # Initializes service and loads .env

    # Validate JSON parameters
    try:
        params_dict = json.loads(parameters)
    except json.JSONDecodeError:
        click.echo("Error: Invalid JSON format for --parameters.", err=True)
        return

    current_auto_evidence_setting = auto_evidence_flag
    if auto_evidence_flag:
        tracker_config = load_tracker_config()
        if not tracker_config:
            click.echo("Auto-evidence requested, but no fitness tracker is connected.")
            if click.confirm("Would you like to connect one now?"):
                # In Click, to call another command, you usually get the context
                ctx = click.get_current_context()
                try:
                    # Assuming 'mockfit' is a safe default if user doesn't specify
                    ctx.invoke(connect_tracker, provider='mockfit')
                    tracker_config = load_tracker_config()  # Reload config
                    if not tracker_config:
                        click.echo(
                            "Tracker connection failed or was skipped. Proceeding with manual evidence submission for this promise.",
                            err=True)
                        current_auto_evidence_setting = False
                    else:
                        click.echo("Tracker connected. This promise will use auto-evidence.")
                except Exception as e:
                    click.echo(f"Error during tracker connection: {e}. Proceeding with manual evidence.", err=True)
                    current_auto_evidence_setting = False
            else:
                click.echo("Proceeding with manual evidence submission for this promise.")
                current_auto_evidence_setting = False
        else:
            click.echo(f"Using connected tracker ({tracker_config.get('provider')}) for automatic evidence.")

    # Add auto_evidence setting to parameters sent to service
    params_dict["_auto_evidence"] = current_auto_evidence_setting

    click.echo(f"\nCreating promise...")
    click.echo(f"  Template ID: {template_id}")
    click.echo(f"  Parameters: {params_dict}")
    click.echo(f"  Start Date: {start_date.strftime('%Y-%m-%d')}")
    click.echo(f"  End Date: {end_date.strftime('%Y-%m-%d')}")
    click.echo(f"  Deposit: {deposit_amount} ROSE")
    click.echo(f"  Auto-Evidence: {current_auto_evidence_setting}")

    try:
        # The service.create_promise should handle datetime objects correctly
        promise_details = service.create_promise(
            user_id="cli_user",  # This should ideally come from the wallet associated with OASIS_PRIVATE_KEY
            template_id=template_id,
            parameters=params_dict,
            start_date=start_date,
            end_date=end_date,
            deposit_amount=deposit_amount,
            auto_evidence=current_auto_evidence_setting  # Pass the final decision
        )
        click.echo(f"\nSUCCESS: Promise created successfully!")
        click.echo(f"  Promise ID: {promise_details.get('promise_id')}")
        click.echo(f"  Status: {promise_details.get('status')}")

        if current_auto_evidence_setting:
            click.echo("  Evidence will be collected automatically from your connected tracker.")
            click.echo("  Use 'trigger-auto-evaluation' or check status after the end date.")
        else:
            click.echo("  You will need to manually submit evidence for this promise using 'submit-evidence'.")

    except Exception as e:
        click.echo(f"\nERROR creating promise: {e}", err=True)


@cli.command()
@click.option('--promise-id', required=True, help="The ID of the promise to view.")
def view_promise(promise_id: str):
    """Views the details of a specific promise."""
    service = get_service()
    try:
        details = service.get_promise_details(promise_id)
        click.echo(json.dumps(details, indent=2))
    except Exception as e:
        click.echo(f"Error viewing promise '{promise_id}': {e}", err=True)


@cli.command()
@click.option('--promise-id', required=True, help="The ID of the promise.")
@click.option('--evidence-file', required=True, type=click.Path(exists=True, readable=True, dir_okay=False),
              help="Path to a JSON file containing the evidence data.")
def submit_evidence(promise_id: str, evidence_file: str):
    """Submits (manual) evidence for a promise to the ROFL TEE for evaluation."""
    service = get_service()
    try:
        with open(evidence_file, 'r') as f:
            evidence_data = json.load(f)

        click.echo(f"Submitting evidence from '{evidence_file}' for promise '{promise_id}'...")
        evaluation_trigger_result = service.submit_evidence_to_rofl(promise_id, evidence_data)
        click.echo(f"Evidence submitted. ROFL call result/ID: {evaluation_trigger_result}")
        click.echo(f"Use 'self-promise status --promise-id {promise_id}' to check for updates.")
    except json.JSONDecodeError:
        click.echo(f"Error: Could not parse JSON from evidence file '{evidence_file}'.", err=True)
    except FileNotFoundError:
        click.echo(f"Error: Evidence file '{evidence_file}' not found.", err=True)
    except Exception as e:
        click.echo(f"Error submitting evidence for promise '{promise_id}': {e}", err=True)


@cli.command()
@click.option('--promise-id', required=True, help="The ID of the promise to evaluate.")
def trigger_auto_evaluation(promise_id: str):
    """
    Triggers automatic evaluation for a promise using connected fitness tracker data.
    For the MVP, this uses MOCK fitness data.
    """
    service = get_service()
    tracker_config = load_tracker_config()

    if not tracker_config:
        click.echo("No fitness tracker connected. Cannot perform automatic evaluation.", err=True)
        click.echo("Please connect a tracker using 'connect-tracker' or use 'submit-evidence' for manual submission.")
        return

    # Check if the promise itself was set up for auto-evidence.
    # Your service.get_promise_details should return this info.
    # promise_info = service.get_promise_details(promise_id)
    # if not promise_info.get("auto_evidence", False) and not promise_info.get("parameters", {}).get("_auto_evidence", False): # Check both places for robustness
    #     click.echo(f"Promise {promise_id} was not set up for automatic evidence collection.", err=True)
    #     click.echo("Use 'submit-evidence' for manual submission if needed.")
    #     return

    click.echo(
        f"Triggering automatic evaluation for promise '{promise_id}' using '{tracker_config.get('provider')}' data (MVP: MOCKED).")

    # --- MVP: MOCK Fitness Data ---
    # In a real app, you would fetch data from the tracker's API using stored tokens
    mock_fitness_data = {
        "user_id_gadget": tracker_config.get("user_id", "mock_user_123"),  # Use user_id if available from OAuth
        "data_source": tracker_config.get('provider'),
        "evaluation_type": "automatic_mocked",
        "sessions": [
            {"date": (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d"), "type": "running",
             "duration_minutes": 35, "avg_heart_rate": 138},
            {"date": (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d"), "type": "cycling",
             "duration_minutes": 45, "avg_heart_rate": 142},
            {"date": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"), "type": "swimming",
             "duration_minutes": 40, "avg_heart_rate": 135}
        ],
        "summary": "Mock data representing a week of typical activity."
    }
    click.echo(f"Using mock fitness data: {json.dumps(mock_fitness_data, indent=2)}")

    try:
        evaluation_trigger_result = service.submit_evidence_to_rofl(promise_id, mock_fitness_data)
        click.echo(f"\nSUCCESS: Automatic evaluation triggered for promise '{promise_id}'.")
        click.echo(f"  ROFL Call Result/ID: {evaluation_trigger_result}")
        click.echo(f"  Use 'self-promise status --promise-id {promise_id}' to check the evaluation results soon.")
    except Exception as e:
        click.echo(f"\nERROR triggering auto-evaluation for promise '{promise_id}': {e}", err=True)


@cli.command()
@click.option('--promise-id', required=True, help="The ID of the promise to check.")
def status(promise_id: str):
    """Checks the on-chain status of a promise after evaluation."""
    service = get_service()
    try:
        current_status = service.get_promise_status(promise_id)
        click.echo(json.dumps(current_status, indent=2))
    except Exception as e:
        click.echo(f"Error checking status for promise '{promise_id}': {e}", err=True)


@cli.command()
@click.option('--promise-id', required=True, help="The ID of the promise for withdrawal.")
def withdraw(promise_id: str):
    """Attempts to withdraw collateral for a fulfilled or resolved promise."""
    service = get_service()
    try:
        tx_hash = service.withdraw_collateral(promise_id)
        click.echo(f"Withdrawal transaction submitted for promise '{promise_id}'.")
        click.echo(f"  Transaction Hash: {tx_hash}")
        click.echo("Funds will be returned to your wallet if the promise conditions were met and resolved.")
    except Exception as e:
        click.echo(f"Error withdrawing collateral for promise '{promise_id}': {e}", err=True)


if __name__ == '__main__':
    cli()
