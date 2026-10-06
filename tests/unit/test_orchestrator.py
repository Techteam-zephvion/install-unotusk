"""
tests/unit/test_orchestrator.py

Unit tests for OrchestratorService port allocation and container lifecycle logic.
"""

import socket

from apps.api.src.services.orchestrator_service import OrchestratorService


def test_find_available_port_default_range():
    """Verify that default port allocation starts in the 28100 series."""
    port = OrchestratorService._find_available_port()
    assert 28100 <= port <= 28999


def test_find_available_port_skips_occupied():
    """Verify that occupied ports are skipped gracefully."""
    # Bind to 28100 temporarily
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("0.0.0.0", 28100))
        except OSError:
            # If 28100 is already in use by another process, test still holds
            pass

        # Allocator should skip 28100 and allocate 28101 or higher
        port = OrchestratorService._find_available_port(start_port=28100, max_port=28999)
        assert port > 28100
        assert port <= 28999
