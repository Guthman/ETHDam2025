#!/usr/bin/env python
"""
Self-Promise CLI: Make and keep promises with financial accountability on Oasis Sapphire.
"""
import click
import json
import os
import time
import webbrowser
import http.server
import socketserver
import threading
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime, timedelta
import urllib.parse
import socket
from typing import Optional, Dict, Any, Tuple

# --- Configuration and Service Initialization ---

_CLI_TEST_CONFIG_DIR_OVERRIDE = None

_service_instance = None

# --- Mock Authorization Server ---
class MockAuthHandler(http.server.SimpleHTTPRequestHandler):
    """Handler for mock authorization page and callbacks."""
    
    # Class variable to store authorization result across instances
    auth_result = {"status": "pending", "decision": None}
    
    # Simple template for the authorization page based on the Fitbit screenshot
    AUTH_PAGE_TEMPLATE = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Mock Fitbit Authorization</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
                line-height: 1.6;
            }}
            .logo {{
                color: #00B0B9;
                font-size: 2.5em;
                font-weight: bold;
                margin-bottom: 20px;
            }}
            .logo span {{
                color: #192743;
            }}
            h2 {{
                color: #333;
                margin-top: 30px;
            }}
            .permission-list {{
                list-style-type: none;
                padding-left: 0;
            }}
            .permission-list li {{
                margin: 10px 0;
                padding-left: 25px;
                position: relative;
            }}
            .permission-list li:before {{
                content: "☐";
                position: absolute;
                left: 0;
            }}
            .buttons {{
                margin-top: 30px;
                display: flex;
                justify-content: space-between;
            }}
            .deny {{
                background-color: #F06292;
                color: white;
                padding: 12px 30px;
                border: none;
                border-radius: 30px;
                cursor: pointer;
                font-size: 1em;
            }}
            .allow {{
                background-color: #F8BBD0;
                color: white;
                padding: 12px 30px;
                border: none;
                border-radius: 30px;
                cursor: pointer;
                font-size: 1em;
            }}
            .note {{
                font-size: 0.9em;
                margin-top: 30px;
                color: #666;
            }}
        </style>
    </head>
    <body>
        <div class="logo">fit<span>bit</span></div>
        
        <h2>Web API Demo application by My Company would like the ability to access the following data in your Fitbit account.</h2>
        
        <ul class="permission-list">
            <li>sleep</li>
            <li>activity and exercise</li>
            <li>heart rate</li>
            <li>profile</li>
            <li>weight</li>
        </ul>
        
        <div class="note">
            If you allow only some of this data, Web API Demo application may not function as intended. 
            Learn more about these permissions <a href="#">here</a>.
        </div>
        
        <div class="buttons">
            <a href="/callback?decision=deny"><button class="deny">Deny</button></a>
            <a href="/callback?decision=allow"><button class="allow">Allow</button></a>
        </div>
        
        <div class="note">
            The data you share with Web API Demo application will be governed by My Company's Privacy Policy and Terms of Service. 
            You can revoke this consent at any time in your Fitbit account settings.
        </div>
    </body>
    </html>
    """
    
    def do_GET(self):
        """Handle GET requests for authorization page and callbacks."""
        parsed_path = urllib.parse.urlparse(self.path)
        
        # Serve the mock authorization page
        if self.path == '/' or self.path == '/auth':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(self.AUTH_PAGE_TEMPLATE.encode())
            return
            
        # Handle callback with user decision
        elif parsed_path.path == '/callback':
            query = urllib.parse.parse_qs(parsed_path.query)
            decision = query.get('decision', ['unknown'])[0]
            
            # Store the result in the class variable
            MockAuthHandler.auth_result = {
                "status": "completed",
                "decision": decision
            }
            
            # Return a simple confirmation page
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            response = f"""
            <!DOCTYPE html>
            <html>
            <head><title>Authorization {decision.title()}</title></head>
            <body>
                <h1>Authorization {decision.title()}</h1>
                <p>You have {decision}ed the authorization request.</p>
                <p>You can close this window and return to the CLI.</p>
            </body>
            </html>
            """
            self.wfile.write(response.encode())
            return
            
        # Handle other paths (404)
        else:
            self.send_response(404)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'Not Found')
            return
    
    def log_message(self, format, *args):
        """Override to suppress server logs in CLI output."""
        return


def find_available_port() -> int:
    """Find an available port to run the mock server on."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('localhost', 0))
        return s.getsockname()[1]


def start_mock_auth_server() -> Tuple[int, threading.Thread]:
    """
    Start the mock authorization server in a separate thread.
    
    Returns:
        Tuple containing (port_number, server_thread)
    """
    port = find_available_port()
    
    # Reset the auth result before starting a new server
    MockAuthHandler.auth_result = {"status": "pending", "decision": None}
    
    # Create and start the server in a separate thread
    server = socketserver.TCPServer(("localhost", port), MockAuthHandler)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True  # So the thread will exit when the main program exits
    server_thread.start()
    
    return port, server_thread, server


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


def save_tracker_config(data: dict) -> None:
    """Saves tracker configuration."""
    config_file = get_config_dir() / "trackers.json"
    with open(config_file, "w") as f:
        json.dump(data, f, indent=2)
    click.echo(f"Tracker configuration saved to {config_file}")


def load_tracker_config() -> Optional[Dict[str, Any]]:
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
        try:
            # Start the mock authorization server
            port, server_thread, server = start_mock_auth_server()
            auth_url = f"http://localhost:{port}/auth"
            
            click.echo("\n==============================================================")
            click.echo("               MOCK FITBIT AUTHORIZATION PAGE")
            click.echo("==============================================================")
            click.echo("  COPY & PASTE THIS URL IF YOUR BROWSER DOESN'T OPEN:")
            click.echo(f"  {auth_url}")
            click.echo("==============================================================\n")
            
            # Try to open the browser to the mock authorization page
            click.echo("Attempting to open the authorization page in your default browser...")
            browser_opened = webbrowser.open(auth_url)
            
            if not browser_opened:
                click.echo("\n!!! BROWSER DID NOT OPEN AUTOMATICALLY !!!", err=True)
                click.echo("Please manually copy and paste the URL above into your browser")
                click.echo(f"URL: {auth_url}")
            else:
                click.echo("Browser opened successfully!")
            
            click.echo("\n--- Fitbit Authorization Process ---")
            click.echo("1. Review the permissions in the browser window")
            click.echo("2. Click 'Allow' to authorize the application")
            click.echo("3. You'll be redirected to a confirmation page")
            click.echo("4. Return to this terminal after completing authorization\n")
            
            # Poll for the authorization result
            max_wait_time = 120  # seconds
            poll_interval = 1  # seconds
            elapsed_time = 0
            
            # Show a spinner while waiting
            spinner = ['|', '/', '-', '\\']
            spinner_idx = 0
            
            click.echo("Waiting for your authorization decision...")
            while elapsed_time < max_wait_time:
                if MockAuthHandler.auth_result["status"] == "completed":
                    break
                    
                # Show spinner
                click.echo(f"\rWaiting for authorization... {spinner[spinner_idx]} (URL: {auth_url})", nl=False)
                spinner_idx = (spinner_idx + 1) % len(spinner)
                
                time.sleep(poll_interval)
                elapsed_time += poll_interval
                
                # Reminder every 15 seconds
                if elapsed_time % 15 == 0 and elapsed_time > 0:
                    click.echo("\r" + " " * 100, nl=False)  # Clear current line
                    click.echo(f"\rReminder - Authorization URL: {auth_url}")
                    click.echo("Waiting for your authorization decision...")
            
            # Clear the spinner line
            click.echo("\r" + " " * 100, nl=False)
            
            # Process the result
            if MockAuthHandler.auth_result["status"] == "completed":
                if MockAuthHandler.auth_result["decision"] == "allow":
                    click.echo("\rAuthorization successful! Fitbit access granted.")
                    
                    # Create and save token data
                    token_data = {
                        "access_token": f"mock_fitbit_access_token_{int(time.time())}",
                        "refresh_token": f"mock_fitbit_refresh_token_{int(time.time())}",
                        "expires_at": int(time.time()) + 28800,  # Fitbit tokens typically last 8 hours
                        "provider": "fitbit",
                        "user_id": "mock_fitbit_user_id"  # From Fitbit OAuth response
                    }
                    save_tracker_config(token_data)
                    click.echo(f"SUCCESS: Fitbit tracker connected successfully!")
                else:
                    click.echo("\rAuthorization denied. Fitbit access was not granted.")
            else:
                click.echo("\rAuthorization timed out or was cancelled. Please try again.")
            
            # Shutdown the server
            try:
                server.shutdown()
                server.server_close()
                server_thread.join(timeout=5)
                click.echo("Authorization server stopped.")
            except Exception as e:
                click.echo(f"Note: Could not cleanly shut down server: {e}", err=True)
        
        except Exception as e:
            click.echo(f"Error during Fitbit authorization process: {e}", err=True)
            click.echo("Falling back to mockfit tracker instead.")
            # Fallback to mockfit in case of any errors
            token_data = {
                "access_token": f"mock_access_token_{int(time.time())}",
                "refresh_token": f"mock_refresh_token_{int(time.time())}",
                "expires_at": int(time.time()) + 86400,  # 24 hours from now
                "provider": "mockfit"
            }
            save_tracker_config(token_data)
            click.echo(f"SUCCESS: Mockfit tracker connected successfully as fallback!")

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
