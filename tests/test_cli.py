import json
import os
from pathlib import Path
from click.testing import CliRunner
import pytest
import click

# Import the CLI module - this should work now that we have conftest.py setting up the path
# and the package is installed in development mode
from self_promise.self_promise_cli import cli, _CLI_TEST_CONFIG_DIR_OVERRIDE


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_config_dir(tmp_path, monkeypatch):
    """Overrides the CLI's config directory to use a temporary directory."""
    test_config_path = tmp_path / ".self-promise-test-config"
    test_config_path.mkdir()
    monkeypatch.setattr("self_promise.self_promise_cli._CLI_TEST_CONFIG_DIR_OVERRIDE", str(test_config_path))
    return test_config_path


@pytest.fixture
def mock_deployed_addresses(tmp_path, monkeypatch):
    """Creates a mock deployed_addresses.json in the current working directory for tests."""
    # Change current working directory to tmp_path for the duration of the test
    # so that deployed_addresses.json is found by the CLI's get_service()
    monkeypatch.chdir(tmp_path)

    deployed_data = {
        "MinimalPromiseDeposit": "0xMockMinimalDeposit",
        "MinimalPromiseKeeper": "0xMockMinimalKeeper",
        "RoflPromiseEvaluator": "mockRoflId123"
    }
    deployed_file = tmp_path / "deployed_addresses.json"
    with open(deployed_file, 'w') as f:
        json.dump(deployed_data, f)
    return deployed_file


@pytest.fixture
def mock_webbrowser_open(monkeypatch):
    """Mocks webbrowser.open to prevent actual browser windows during tests."""
    opened_urls = []

    def mock_open(url, new=0, autoraise=True):
        opened_urls.append(url)
        print(f"Mocked webbrowser.open called with URL: {url}")
        return True

    monkeypatch.setattr("webbrowser.open", mock_open)
    return opened_urls


# --- Test Cases ---

def test_cli_invokes(runner):
    """Test that the CLI runs and shows help."""
    result = runner.invoke(cli, ['--help'])
    assert result.exit_code == 0
    assert "Self-Promise: Make and keep promises" in result.output


def test_connect_tracker_mockfit(runner, mock_config_dir):
    """Test connecting the mockfit tracker."""
    result = runner.invoke(cli, ['connect-tracker', '--provider', 'mockfit'])
    assert result.exit_code == 0
    assert "SUCCESS: Mockfit tracker connected successfully!" in result.output
    tracker_file = mock_config_dir / "trackers.json"
    assert tracker_file.exists()
    with open(tracker_file, 'r') as f:
        config = json.load(f)
    assert config["provider"] == "mockfit"
    assert "mock_access_token" in config["access_token"]


def test_connect_tracker_fitbit_mocked(runner, mock_config_dir, mock_webbrowser_open, mock_deployed_addresses):
    """Test connecting the Fitbit tracker (mocked flow)."""
    # mock_deployed_addresses ensures that get_service() can load something
    result = runner.invoke(cli, ['connect-tracker', '--provider', 'fitbit'])
    assert result.exit_code == 0
    assert "SUCCESS: Fitbit tracker (mock) connected successfully!" in result.output
    tracker_file = mock_config_dir / "trackers.json"
    assert tracker_file.exists()
    with open(tracker_file, 'r') as f:
        config = json.load(f)
    assert config["provider"] == "fitbit"
    assert "mock_fitbit_access_token" in config["access_token"]
    assert len(mock_webbrowser_open) == 1
    assert "https://www.fitbit.com/oauth2/authorize" in mock_webbrowser_open[0]


def test_create_promise_manual_evidence(runner, mock_deployed_addresses):
    """Test creating a promise with manual evidence."""
    params = '{"activity": "run 5k"}'
    result = runner.invoke(cli, [
        'create-promise',
        '--template-id', '1',
        '--parameters', params,
        '--start-date', '2024-01-01',
        '--end-date', '2024-01-07',
        '--deposit-amount', '10',
        '--no-auto-evidence'
    ])
    assert result.exit_code == 0
    assert "SUCCESS: Promise created successfully!" in result.output
    assert "You will need to manually submit evidence" in result.output
    assert "Auto-Evidence: False" in result.output


def test_create_promise_auto_evidence_no_tracker_connect_yes(runner, mock_config_dir, mock_deployed_addresses,
                                                             mock_webbrowser_open):
    """Test create promise with auto-evidence, no tracker, user says yes to connect."""
    params = '{"activity": "read a book"}'
    # Simulate user input 'y' for the confirmation prompt
    result = runner.invoke(cli, [
        'create-promise',
        '--template-id', '2',
        '--parameters', params,
        '--start-date', '2024-02-01',
        '--end-date', '2024-02-07',
        '--deposit-amount', '20',
        '--auto-evidence'
    ], input='y\n')  # Provide 'y' then newline for the click.confirm

    assert result.exit_code == 0
    assert "SUCCESS: Promise created successfully!" in result.output
    assert "Tracker connected. This promise will use auto-evidence." in result.output
    assert "Auto-Evidence: True" in result.output
    # Check if tracker config was created (connect_tracker with mockfit is called by default)
    tracker_file = mock_config_dir / "trackers.json"
    assert tracker_file.exists()
    with open(tracker_file, 'r') as f:
        config = json.load(f)
    assert config["provider"] == "mockfit"


def test_create_promise_auto_evidence_no_tracker_connect_no(runner, mock_config_dir, mock_deployed_addresses):
    """Test create promise with auto-evidence, no tracker, user says no to connect."""
    params = '{"activity": "learn python"}'
    result = runner.invoke(cli, [
        'create-promise',
        '--template-id', '3',
        '--parameters', params,
        '--start-date', '2024-03-01',
        '--end-date', '2024-03-07',
        '--deposit-amount', '30',
        '--auto-evidence'
    ], input='n\n')  # Provide 'n' for the click.confirm

    assert result.exit_code == 0
    assert "SUCCESS: Promise created successfully!" in result.output
    assert "Proceeding with manual evidence submission for this promise." in result.output
    assert "Auto-Evidence: False" in result.output  # It should switch to False
    tracker_file = mock_config_dir / "trackers.json"
    assert not tracker_file.exists()  # Tracker should not have been connected


def test_create_promise_auto_evidence_with_tracker(runner, mock_config_dir, mock_deployed_addresses):
    """Test create promise with auto-evidence when a tracker is already connected."""
    # First, connect a tracker
    runner.invoke(cli, ['connect-tracker', '--provider', 'mockfit'])
    assert (mock_config_dir / "trackers.json").exists()

    params = '{"activity": "meditate daily"}'
    result = runner.invoke(cli, [
        'create-promise',
        '--template-id', '4',
        '--parameters', params,
        '--start-date', '2024-04-01',
        '--end-date', '2024-04-07',
        '--deposit-amount', '40',
        '--auto-evidence'
    ])
    assert result.exit_code == 0
    assert "SUCCESS: Promise created successfully!" in result.output
    assert "Using connected tracker (mockfit) for automatic evidence." in result.output
    assert "Auto-Evidence: True" in result.output


def test_view_promise(runner, mock_deployed_addresses):
    """Test the view-promise command."""
    result = runner.invoke(cli, ['view-promise', '--promise-id', 'mock_promise_123'])
    assert result.exit_code == 0
    assert "MockService: Fetching details for promise 'mock_promise_123'" in result.output
    # Check for JSON output (basic check)
    try:
        json.loads(result.output.split("MockService: Fetching details for promise 'mock_promise_123'.")[-1].strip())
        assert True
    except json.JSONDecodeError:
        assert False, "Output after mock service message was not valid JSON"


def test_submit_evidence(runner, tmp_path, mock_deployed_addresses):
    """Test the submit-evidence command."""
    evidence_content = {"data": "some evidence"}
    evidence_file = tmp_path / "evidence.json"
    with open(evidence_file, 'w') as f:
        json.dump(evidence_content, f)

    result = runner.invoke(cli, ['submit-evidence', '--promise-id', 'mock_promise_456', '--evidence-file',
                                 str(evidence_file)])
    assert result.exit_code == 0
    assert "Submitting evidence from" in result.output
    assert "ROFL call result/ID:" in result.output


def test_trigger_auto_evaluation_no_tracker(runner, mock_config_dir, mock_deployed_addresses):
    """Test trigger-auto-evaluation when no tracker is connected."""
    # Ensure no tracker file exists from previous tests in this specific scenario
    tracker_file = mock_config_dir / "trackers.json"
    if tracker_file.exists():
        tracker_file.unlink()

    result = runner.invoke(cli, ['trigger-auto-evaluation', '--promise-id', 'any_promise'])
    assert result.exit_code == 0  # Command itself doesn't fail, but prints error
    assert "No fitness tracker connected. Cannot perform automatic evaluation." in result.output


def test_trigger_auto_evaluation_with_tracker(runner, mock_config_dir, mock_deployed_addresses):
    """Test trigger-auto-evaluation when a tracker is connected."""
    runner.invoke(cli, ['connect-tracker', '--provider', 'mockfit'])
    assert (mock_config_dir / "trackers.json").exists()

    result = runner.invoke(cli, ['trigger-auto-evaluation', '--promise-id', 'mock_promise_789'])
    assert result.exit_code == 0
    assert "SUCCESS: Automatic evaluation triggered" in result.output
    assert "Using mock fitness data:" in result.output


def test_status(runner, mock_deployed_addresses):
    """Test the status command."""
    result = runner.invoke(cli, ['status', '--promise-id', 'mock_promise_abc'])
    assert result.exit_code == 0
    assert "MockService: Getting status for promise 'mock_promise_abc'" in result.output
    try:
        json.loads(result.output.split("MockService: Getting status for promise 'mock_promise_abc'.")[-1].strip())
        assert True
    except json.JSONDecodeError:
        assert False, "Output after mock service message was not valid JSON for status"


def test_withdraw(runner, mock_deployed_addresses):
    """Test the withdraw command."""
    result = runner.invoke(cli, ['withdraw', '--promise-id', 'mock_promise_def'])
    assert result.exit_code == 0
    assert "Withdrawal transaction submitted" in result.output
    assert "Transaction Hash: mock_tx_hash_withdraw_" in result.output
