"""
tests/test_clean_server_reset.py

Unit tests for the clean server reset utility (scripts/clean_server_reset.py).
Verifies:
1. Target container filtering strictly isolates Unotusk-MVP containers and protects foreign ones.
2. Protection of unotusk-2, nammadharani, and supabase containers.
3. Selective data volume preservation vs wipe policies.
4. Correct invocation of docker compose down and surgical container removal.
"""

from unittest.mock import MagicMock, patch

from scripts.clean_server_reset import (
    UNOTUSK_CONTAINERS,
    UNOTUSK_DATA_VOLUMES,
    inspect_unotusk_state,
    perform_reset,
)


def test_target_containers_set():
    assert "unotusk-api" in UNOTUSK_CONTAINERS
    assert "unotusk-worker" in UNOTUSK_CONTAINERS
    assert "unotusk-postgres" in UNOTUSK_CONTAINERS
    assert "unotusk-redis" in UNOTUSK_CONTAINERS
    assert "unotusk-migration" in UNOTUSK_CONTAINERS
    # Foreign containers MUST NOT be in the target list
    assert "unotusk-2-ups-1" not in UNOTUSK_CONTAINERS
    assert "unotusk-2-ai-pie-1" not in UNOTUSK_CONTAINERS
    assert "nammadharani-backend-1" not in UNOTUSK_CONTAINERS
    assert "supabase_db" not in UNOTUSK_CONTAINERS


def test_target_volumes_set():
    assert "unotusk_postgres_data" in UNOTUSK_DATA_VOLUMES
    assert "unotusk_redis_data" in UNOTUSK_DATA_VOLUMES
    assert "server_unotusk_postgres_data" in UNOTUSK_DATA_VOLUMES
    # Foreign volumes MUST NOT be in the target list
    assert "unotusk-2_postgres_data" not in UNOTUSK_DATA_VOLUMES
    assert "nammadharani_postgres_data" not in UNOTUSK_DATA_VOLUMES


@patch("scripts.clean_server_reset.get_docker_containers")
@patch("scripts.clean_server_reset.get_docker_volumes")
@patch("scripts.clean_server_reset.is_port_in_use")
def test_inspect_unotusk_state_filters_foreign_containers(mock_port, mock_volumes, mock_containers):
    mock_containers.return_value = [
        {"name": "unotusk-api", "id": "111", "state": "running", "status": "Up"},
        {"name": "unotusk-postgres", "id": "222", "state": "running", "status": "Up"},
        {"name": "unotusk-2-ups-1", "id": "333", "state": "running", "status": "Up"},
        {"name": "nammadharani-redis-1", "id": "444", "state": "running", "status": "Up"},
        {"name": "supabase_db_GBTPA", "id": "555", "state": "running", "status": "Up"},
    ]
    mock_volumes.return_value = [
        "server_unotusk_postgres_data",
        "unotusk-2_data",
        "nammadharani_redis",
    ]
    mock_port.return_value = True

    state = inspect_unotusk_state()

    # Only unotusk-api and unotusk-postgres should be identified as Unotusk containers
    target_names = [c["name"] for c in state["unotusk_containers"]]
    assert "unotusk-api" in target_names
    assert "unotusk-postgres" in target_names
    assert "unotusk-2-ups-1" not in target_names
    assert "nammadharani-redis-1" not in target_names

    # Other containers count should be 3
    assert state["other_containers_count"] == 3

    # Only server_unotusk_postgres_data should be identified
    assert state["unotusk_volumes"] == ["server_unotusk_postgres_data"]
    assert state["port_8000_used"] is True


@patch("scripts.clean_server_reset.inspect_unotusk_state")
@patch("scripts.clean_server_reset.run_cmd")
@patch("scripts.clean_server_reset.get_docker_containers")
@patch("scripts.clean_server_reset.is_port_in_use")
def test_perform_reset_dry_run_makes_no_calls(mock_port, mock_get_containers, mock_run, mock_inspect):
    mock_inspect.return_value = {
        "unotusk_containers": [{"name": "unotusk-api", "id": "111", "state": "running"}],
        "other_containers_count": 5,
        "unotusk_volumes": ["server_unotusk_postgres_data"],
        "deployment_dir_exists": True,
        "env_file_exists": True,
        "port_8000_used": True,
    }
    mock_get_containers.return_value = []
    mock_port.return_value = False

    success = perform_reset(wipe_data=True, wipe_config=True, dry_run=True)
    assert success is True
    # In dry-run mode, run_cmd should not be called to remove or down containers
    assert mock_run.call_count == 0


@patch("scripts.clean_server_reset.inspect_unotusk_state")
@patch("scripts.clean_server_reset.run_cmd")
@patch("scripts.clean_server_reset.get_docker_containers")
@patch("scripts.clean_server_reset.is_port_in_use")
def test_perform_reset_preserve_data_does_not_remove_volumes(
    mock_port, mock_get_containers, mock_run, mock_inspect, tmp_path
):
    mock_inspect.return_value = {
        "unotusk_containers": [{"name": "unotusk-api", "id": "111", "state": "running"}],
        "other_containers_count": 5,
        "unotusk_volumes": ["server_unotusk_postgres_data"],
        "deployment_dir_exists": False,
        "env_file_exists": False,
        "port_8000_used": False,
    }
    # Remaining containers has unotusk-api to trigger surgical removal
    mock_get_containers.side_effect = [
        [{"name": "unotusk-api", "id": "111", "state": "running"}],
        [],  # after removal
    ]
    mock_port.return_value = False
    mock_run.return_value = MagicMock(returncode=0)

    with patch("scripts.clean_server_reset.DEPLOYMENT_DIR", tmp_path / "nonexistent"):
        success = perform_reset(wipe_data=False, wipe_config=False, dry_run=False, yes=True)
    assert success is True

    # run_cmd should have removed unotusk-api
    calls = [call.args[0] for call in mock_run.call_args_list]
    assert any("rm" in cmd and "unotusk-api" in cmd for cmd in calls)
    # volume rm should NOT be called
    assert not any("volume" in cmd and "rm" in cmd for cmd in calls)


@patch("scripts.clean_server_reset.inspect_unotusk_state")
@patch("builtins.input", return_value="no")
def test_perform_reset_aborts_on_rejected_wipe_confirmation(mock_input, mock_inspect):
    mock_inspect.return_value = {
        "unotusk_containers": [],
        "other_containers_count": 0,
        "unotusk_volumes": ["server_unotusk_postgres_data"],
        "deployment_dir_exists": False,
        "env_file_exists": False,
        "port_8000_used": False,
    }

    success = perform_reset(wipe_data=True, wipe_config=False, dry_run=False, yes=False)
    assert success is False
