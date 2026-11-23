from unittest.mock import Mock, patch

import pytest

from engine.editor import start


def test_launcher_api_failure_stops_child_without_starting_vite(monkeypatch):
    api = Mock()
    api.poll.return_value = 1
    with patch.object(start.subprocess, "Popen", return_value=api) as launch, patch(
        "time.sleep"
    ), patch.object(start.signal, "signal"), pytest.raises(RuntimeError, match="API server did not start"):
        start.main()
    assert launch.call_count == 1
    api.terminate.assert_called_once()
    api.wait.assert_called_once()


def test_launcher_vite_failure_stops_both_and_uses_matching_ports(monkeypatch):
    monkeypatch.setenv("CWI_PORT", "18181")
    monkeypatch.setenv("CWI_UI_PORT", "15174")
    api, vite = Mock(), Mock()
    api.poll.return_value = None
    vite.poll.return_value = 1
    with patch.object(start.subprocess, "Popen", side_effect=[api, vite]) as launch, patch(
        "time.sleep"
    ), patch.object(start.signal, "signal"), pytest.raises(RuntimeError, match="editor server stopped"):
        start.main()
    calls = launch.call_args_list
    assert calls[0].kwargs["env"]["CWI_PORT"] == "18181"
    assert calls[1].kwargs["env"]["CWI_API_PORT"] == "18181"
    assert calls[1].args[0][-3:] == ["--port", "15174", "--strictPort"]
    api.terminate.assert_called_once()
    vite.terminate.assert_called_once()


def test_launcher_sigterm_handler_follows_normal_cleanup():
    api, vite = Mock(), Mock()
    api.poll.return_value = None
    vite.poll.return_value = None
    handler = None

    def remember(sig, fn):
        nonlocal handler
        handler = fn

    def interrupt(_):
        if handler is not None:
            handler(start.signal.SIGTERM, None)

    with patch.object(start.subprocess, "Popen", side_effect=[api, vite]), patch(
        "time.sleep", side_effect=interrupt
    ), patch.object(start.signal, "signal", side_effect=remember):
        start.main()
    api.terminate.assert_called_once()
    # SIGTERM landed during API startup, before frontend creation.
    vite.terminate.assert_not_called()
