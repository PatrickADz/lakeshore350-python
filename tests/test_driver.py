"""
Basic tests using a mocked socket, so they run without a physical instrument.
"""

import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from lakeshore350_driver import LakeShore350  # noqa: E402
from exceptions import LakeShore350Error  # noqa: E402


def _make_mock_socket(responses):
    """Returns a MagicMock socket that yields `responses` in order on recv()."""
    mock_sock = MagicMock()
    encoded = [r.encode() for r in responses]
    mock_sock.recv.side_effect = encoded
    return mock_sock


@patch("socket.socket")
def test_connect_reads_idn(mock_socket_cls):
    mock_socket_cls.return_value = _make_mock_socket(["LSCI,MODEL350,123456,1.0\n"])
    ls = LakeShore350("192.0.2.1")
    assert ls.sock is not None


@patch("socket.socket")
def test_read_temperature_k(mock_socket_cls):
    mock_socket_cls.return_value = _make_mock_socket(["LSCI,MODEL350,123456,1.0\n", "77.350\n"])
    ls = LakeShore350("192.0.2.1")
    temp = ls.read_temperature_K("A")
    assert temp == 77.350


@patch("socket.socket")
def test_invalid_channel_raises(mock_socket_cls):
    mock_socket_cls.return_value = _make_mock_socket(["LSCI,MODEL350,123456,1.0\n"])
    ls = LakeShore350("192.0.2.1")
    try:
        ls.read_temperature_K("Z")
        assert False, "expected ValueError"
    except ValueError:
        pass


@patch("socket.socket")
def test_empty_response_raises_driver_error(mock_socket_cls):
    mock_socket_cls.return_value = _make_mock_socket(["LSCI,MODEL350,123456,1.0\n", ""])
    ls = LakeShore350("192.0.2.1")
    try:
        ls.read_temperature_K("A")
        assert False, "expected LakeShore350Error"
    except LakeShore350Error:
        pass


@patch("socket.socket")
def test_get_setpoint(mock_socket_cls):
    mock_socket_cls.return_value = _make_mock_socket(["LSCI,MODEL350,123456,1.0\n", "77.000\n"])
    ls = LakeShore350("192.0.2.1")
    assert ls.get_setpoint(1) == 77.0


@patch("socket.socket")
def test_get_pid(mock_socket_cls):
    mock_socket_cls.return_value = _make_mock_socket(["LSCI,MODEL350,123456,1.0\n", "50.0,20.0,0.0\n"])
    ls = LakeShore350("192.0.2.1")
    pid = ls.get_pid(1)
    assert pid == {"P": 50.0, "I": 20.0, "D": 0.0}


@patch("socket.socket")
def test_get_output_mode(mock_socket_cls):
    mock_socket_cls.return_value = _make_mock_socket(["LSCI,MODEL350,123456,1.0\n", "1,A,0\n"])
    ls = LakeShore350("192.0.2.1")
    mode = ls.get_output_mode(1)
    assert mode["mode"] == "Closed Loop PID"
    assert mode["input_channel"] == "A"
    assert mode["powerup_enable"] is False


@patch("socket.socket")
def test_invalid_loop_raises(mock_socket_cls):
    mock_socket_cls.return_value = _make_mock_socket(["LSCI,MODEL350,123456,1.0\n"])
    ls = LakeShore350("192.0.2.1")
    try:
        ls.get_setpoint(3)
        assert False, "expected ValueError"
    except ValueError:
        pass


if __name__ == "__main__":
    test_connect_reads_idn()
    test_read_temperature_k()
    test_invalid_channel_raises()
    test_empty_response_raises_driver_error()
    test_get_setpoint()
    test_get_pid()
    test_get_output_mode()
    test_invalid_loop_raises()
    print("All tests passed.")
