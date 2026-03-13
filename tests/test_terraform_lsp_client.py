#!/usr/bin/env python3
"""
Comprehensive tests for terraform_lsp_client.py

Covers:
- _validate_file_path(): workspace boundary enforcement, traversal prevention
- _get_next_id(): incrementing request ID generation
- _send_request(): notification filtering, ID matching, timeout, max iteration limit
- _read_response(): Content-Length parsing, 10MB size limit, connection-closed errors
- validate_document(): path validation, uninitialized client, full LSP flow
- get_hover_info(): position params, LSP response handling
- get_completions(): list and dict result formats
- format_document(): formatting options, edit results
- _close_document(): didClose notification dispatch
- _send_notification(): JSON-RPC notification framing
- shutdown(): shutdown/exit sequence, process termination, timeout kill
- get_lsp_client(): async singleton factory, lock safety, failure reset
"""

import asyncio
import json
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from terraform_lsp_client import TerraformLSPClient, get_lsp_client


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_lsp_message(body: dict) -> bytes:
    """Encode a dict as a valid LSP JSON-RPC message (headers + body)."""
    payload = json.dumps(body).encode("utf-8")
    header = f"Content-Length: {len(payload)}\r\n\r\n".encode("utf-8")
    return header + payload


def _mock_stdout_from_messages(messages: list[dict]) -> AsyncMock:
    """Build a mock stdout that yields LSP messages in sequence.

    Each call to readline / read will return the correct bytes for the
    next LSP message in the list.
    """
    raw = b""
    for msg in messages:
        raw += _make_lsp_message(msg)

    # We need to simulate readline (for headers) and read(n) (for body).
    # The simplest approach: use an asyncio.StreamReader and feed the data.
    reader = asyncio.StreamReader()
    reader.feed_data(raw)
    reader.feed_eof()
    return reader


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client(tmp_path):
    """Create a TerraformLSPClient bound to a temporary workspace."""
    return TerraformLSPClient(workspace_root=str(tmp_path))


@pytest.fixture
def initialized_client(tmp_path):
    """Create a TerraformLSPClient that appears fully initialized."""
    c = TerraformLSPClient(workspace_root=str(tmp_path))
    c.initialized = True
    c.terraform_ls_process = MagicMock()
    c.terraform_ls_process.stdin = MagicMock()
    c.terraform_ls_process.stdin.write = MagicMock()
    c.terraform_ls_process.stdin.drain = AsyncMock()
    c.terraform_ls_process.stdout = MagicMock()
    c.terraform_ls_process.terminate = MagicMock()
    c.terraform_ls_process.kill = MagicMock()
    c.terraform_ls_process.wait = AsyncMock()
    return c


# ---------------------------------------------------------------------------
# 1. _validate_file_path()
# ---------------------------------------------------------------------------


class TestValidateFilePath:
    """Tests for the _validate_file_path method."""

    def test_valid_path_within_workspace(self, client, tmp_path):
        """A file directly under workspace_root should pass validation."""
        target = tmp_path / "main.tf"
        target.touch()
        client._validate_file_path(str(target))  # Should not raise

    def test_valid_nested_path(self, client, tmp_path):
        """A file in a subdirectory of workspace_root should pass validation."""
        subdir = tmp_path / "modules" / "vpc"
        subdir.mkdir(parents=True)
        target = subdir / "main.tf"
        target.touch()
        client._validate_file_path(str(target))  # Should not raise

    def test_rejects_absolute_path_outside_workspace(self, client):
        """An absolute path outside workspace_root should raise ValueError."""
        with pytest.raises(ValueError, match="Access denied"):
            client._validate_file_path("/etc/passwd")

    def test_rejects_relative_traversal(self, client, tmp_path):
        """Relative path traversal (../) escaping workspace should raise ValueError."""
        malicious = str(tmp_path / ".." / ".." / "etc" / "passwd")
        with pytest.raises(ValueError, match="Access denied"):
            client._validate_file_path(malicious)

    def test_rejects_symlink_escape(self, client, tmp_path):
        """A symlink pointing outside the workspace should raise ValueError."""
        link_path = tmp_path / "escape_link"
        link_path.symlink_to("/etc")
        with pytest.raises(ValueError, match="Access denied"):
            client._validate_file_path(str(link_path / "passwd"))

    def test_workspace_root_itself(self, client, tmp_path):
        """The workspace root directory itself should be valid."""
        client._validate_file_path(str(tmp_path))  # Should not raise

    def test_rejects_root_path(self, client):
        """The filesystem root should be rejected."""
        with pytest.raises(ValueError, match="Access denied"):
            client._validate_file_path("/")

    def test_rejects_home_directory(self, client):
        """User's home directory should be rejected."""
        with pytest.raises(ValueError, match="Access denied"):
            client._validate_file_path(os.path.expanduser("~"))


# ---------------------------------------------------------------------------
# 2. _get_next_id()
# ---------------------------------------------------------------------------


class TestGetNextId:
    """Tests for the _get_next_id method."""

    def test_starts_at_one(self, client):
        """First call should return 1."""
        assert client._get_next_id() == 1

    def test_increments_sequentially(self, client):
        """Successive calls should return incrementing integers."""
        ids = [client._get_next_id() for _ in range(5)]
        assert ids == [1, 2, 3, 4, 5]

    def test_independent_between_instances(self, tmp_path):
        """Different client instances should have independent counters."""
        c1 = TerraformLSPClient(workspace_root=str(tmp_path))
        c2 = TerraformLSPClient(workspace_root=str(tmp_path))
        c1._get_next_id()
        c1._get_next_id()
        assert c2._get_next_id() == 1


# ---------------------------------------------------------------------------
# 3. _send_request() — notification filtering and ID matching
# ---------------------------------------------------------------------------


class TestSendRequest:
    """Tests for the _send_request method."""

    @pytest.mark.asyncio
    async def test_raises_when_no_process(self, client):
        """Should raise RuntimeError when terraform-ls process is not started."""
        with pytest.raises(RuntimeError, match="terraform-ls process not started"):
            await client._send_request("initialize", {})

    @pytest.mark.asyncio
    async def test_skips_notifications_returns_matching_response(
        self, initialized_client
    ):
        """Notifications (messages with 'method' and no 'id') should be skipped
        until the matching response is found."""
        client = initialized_client

        # The first call to _get_next_id inside _send_request will return 1
        notification1 = {"jsonrpc": "2.0", "method": "window/logMessage", "params": {}}
        notification2 = {
            "jsonrpc": "2.0",
            "method": "textDocument/publishDiagnostics",
            "params": {},
        }
        matching_response = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"capabilities": {}},
        }

        client._read_response = AsyncMock(
            side_effect=[notification1, notification2, matching_response]
        )

        result = await client._send_request("initialize", {})
        assert result == matching_response
        assert client._read_response.call_count == 3

    @pytest.mark.asyncio
    async def test_skips_mismatched_ids(self, initialized_client):
        """Responses with a mismatched 'id' should be skipped."""
        client = initialized_client

        mismatched = {"jsonrpc": "2.0", "id": 999, "result": {}}
        matching = {"jsonrpc": "2.0", "id": 1, "result": {"data": "correct"}}

        client._read_response = AsyncMock(side_effect=[mismatched, matching])

        result = await client._send_request("textDocument/hover", {})
        assert result == matching
        assert result["result"]["data"] == "correct"

    @pytest.mark.asyncio
    async def test_mixed_notifications_and_mismatched_ids(self, initialized_client):
        """A sequence of notifications and mismatched IDs should all be skipped."""
        client = initialized_client

        messages = [
            {"jsonrpc": "2.0", "method": "window/logMessage", "params": {}},
            {"jsonrpc": "2.0", "id": 50, "result": {}},
            {"jsonrpc": "2.0", "method": "$/progress", "params": {}},
            {"jsonrpc": "2.0", "id": 1, "result": {"found": True}},
        ]
        client._read_response = AsyncMock(side_effect=messages)

        result = await client._send_request("test/method", {})
        assert result["result"]["found"] is True
        assert client._read_response.call_count == 4

    @pytest.mark.asyncio
    async def test_raises_after_max_iterations(self, initialized_client):
        """Should raise RuntimeError after 50 non-matching messages."""
        client = initialized_client

        # Generate 50 notifications — none match
        notifications = [
            {"jsonrpc": "2.0", "method": "window/logMessage", "params": {}}
            for _ in range(50)
        ]
        client._read_response = AsyncMock(side_effect=notifications)

        with pytest.raises(RuntimeError, match="No matching response"):
            await client._send_request("test/method", {})

    @pytest.mark.asyncio
    async def test_timeout_raises_runtime_error(self, initialized_client):
        """A timeout from _read_response should surface as RuntimeError."""
        client = initialized_client

        client._read_response = AsyncMock(side_effect=asyncio.TimeoutError())

        with pytest.raises(RuntimeError, match="Timeout waiting for response"):
            await client._send_request("test/method", {})

    @pytest.mark.asyncio
    async def test_sends_correct_json_rpc_frame(self, initialized_client):
        """Verify the JSON-RPC message written to stdin is correctly framed."""
        client = initialized_client
        matching = {"jsonrpc": "2.0", "id": 1, "result": {}}
        client._read_response = AsyncMock(return_value=matching)

        await client._send_request("textDocument/hover", {"key": "value"})

        written_bytes = client.terraform_ls_process.stdin.write.call_args[0][0]
        written_str = written_bytes.decode("utf-8")

        # Should have Content-Length header
        assert written_str.startswith("Content-Length: ")
        # Should contain the JSON body
        header, body = written_str.split("\r\n\r\n", 1)
        parsed = json.loads(body)
        assert parsed["jsonrpc"] == "2.0"
        assert parsed["id"] == 1
        assert parsed["method"] == "textDocument/hover"
        assert parsed["params"] == {"key": "value"}

    @pytest.mark.asyncio
    async def test_request_without_params(self, initialized_client):
        """When params is None the 'params' key should be omitted from the request."""
        client = initialized_client
        matching = {"jsonrpc": "2.0", "id": 1, "result": {}}
        client._read_response = AsyncMock(return_value=matching)

        await client._send_request("shutdown")

        written_bytes = client.terraform_ls_process.stdin.write.call_args[0][0]
        _, body = written_bytes.decode("utf-8").split("\r\n\r\n", 1)
        parsed = json.loads(body)
        assert "params" not in parsed


# ---------------------------------------------------------------------------
# 4. _read_response()
# ---------------------------------------------------------------------------


class TestReadResponse:
    """Tests for the _read_response method."""

    @pytest.mark.asyncio
    async def test_parses_valid_lsp_message(self, initialized_client):
        """A well-formed LSP message should be parsed correctly."""
        client = initialized_client
        body = {"jsonrpc": "2.0", "id": 1, "result": {"key": "value"}}
        reader = _mock_stdout_from_messages([body])
        client.terraform_ls_process.stdout = reader

        result = await client._read_response()
        assert result == body

    @pytest.mark.asyncio
    async def test_parses_multiple_headers(self, initialized_client):
        """Multiple headers (Content-Length + Content-Type) should be handled."""
        client = initialized_client
        body_dict = {"jsonrpc": "2.0", "id": 1, "result": {}}
        payload = json.dumps(body_dict).encode("utf-8")

        raw = (
            f"Content-Length: {len(payload)}\r\n"
            f"Content-Type: application/vscode-jsonrpc; charset=utf-8\r\n"
            f"\r\n"
        ).encode("utf-8") + payload

        reader = asyncio.StreamReader()
        reader.feed_data(raw)
        reader.feed_eof()
        client.terraform_ls_process.stdout = reader

        result = await client._read_response()
        assert result == body_dict

    @pytest.mark.asyncio
    async def test_rejects_oversized_content(self, initialized_client):
        """Content-Length exceeding 10MB should raise RuntimeError."""
        client = initialized_client

        # Craft a header claiming >10MB content length
        fake_header = b"Content-Length: 11000000\r\n\r\n"
        reader = asyncio.StreamReader()
        reader.feed_data(fake_header)
        reader.feed_eof()
        client.terraform_ls_process.stdout = reader

        with pytest.raises(RuntimeError, match="LSP response too large"):
            await client._read_response()

    @pytest.mark.asyncio
    async def test_exactly_10mb_is_allowed(self, initialized_client):
        """Content-Length of exactly 10MB should be allowed (boundary check)."""
        client = initialized_client
        max_size = 10 * 1024 * 1024

        header = f"Content-Length: {max_size}\r\n\r\n".encode("utf-8")
        reader = asyncio.StreamReader()
        reader.feed_data(header)
        # Feed just enough valid JSON to parse — in practice this would be
        # a huge payload, but for the boundary test we just need _read_response
        # to not raise the "too large" error. It will try to read and may fail
        # on actual content, so we verify the size check itself is OK.
        reader.feed_eof()

        client.terraform_ls_process.stdout = reader

        # Should NOT raise "too large" — will raise "Connection closed" instead
        # because we didn't actually feed 10MB of data.
        with pytest.raises(RuntimeError, match="Connection closed"):
            await client._read_response()

    @pytest.mark.asyncio
    async def test_connection_closed_during_headers(self, initialized_client):
        """Empty read during header parsing should raise RuntimeError."""
        client = initialized_client

        reader = asyncio.StreamReader()
        reader.feed_eof()  # Immediate EOF
        client.terraform_ls_process.stdout = reader

        with pytest.raises(RuntimeError, match="Connection closed while reading"):
            await client._read_response()

    @pytest.mark.asyncio
    async def test_connection_closed_during_content(self, initialized_client):
        """EOF during content read (after valid header) should raise RuntimeError."""
        client = initialized_client

        # Valid header, but no body data
        header = b"Content-Length: 100\r\n\r\n"
        reader = asyncio.StreamReader()
        reader.feed_data(header)
        reader.feed_eof()
        client.terraform_ls_process.stdout = reader

        with pytest.raises(RuntimeError, match="Connection closed"):
            await client._read_response()

    @pytest.mark.asyncio
    async def test_zero_content_length_returns_empty_dict(self, initialized_client):
        """Content-Length: 0 should return an empty dict."""
        client = initialized_client

        raw = b"Content-Length: 0\r\n\r\n"
        reader = asyncio.StreamReader()
        reader.feed_data(raw)
        reader.feed_eof()
        client.terraform_ls_process.stdout = reader

        result = await client._read_response()
        assert result == {}

    @pytest.mark.asyncio
    async def test_missing_content_length_returns_empty_dict(self, initialized_client):
        """A header block with no Content-Length should default to 0 and return {}."""
        client = initialized_client

        raw = b"X-Custom: something\r\n\r\n"
        reader = asyncio.StreamReader()
        reader.feed_data(raw)
        reader.feed_eof()
        client.terraform_ls_process.stdout = reader

        result = await client._read_response()
        assert result == {}


# ---------------------------------------------------------------------------
# 5. _send_notification()
# ---------------------------------------------------------------------------


class TestSendNotification:
    """Tests for the _send_notification method."""

    @pytest.mark.asyncio
    async def test_sends_notification_without_id(self, initialized_client):
        """Notifications should not contain an 'id' field."""
        client = initialized_client

        await client._send_notification("initialized", {})

        written_bytes = client.terraform_ls_process.stdin.write.call_args[0][0]
        _, body = written_bytes.decode("utf-8").split("\r\n\r\n", 1)
        parsed = json.loads(body)
        assert "id" not in parsed
        assert parsed["method"] == "initialized"
        assert parsed["jsonrpc"] == "2.0"

    @pytest.mark.asyncio
    async def test_sends_notification_without_params(self, initialized_client):
        """When params is None the 'params' key should be omitted."""
        client = initialized_client

        await client._send_notification("exit")

        written_bytes = client.terraform_ls_process.stdin.write.call_args[0][0]
        _, body = written_bytes.decode("utf-8").split("\r\n\r\n", 1)
        parsed = json.loads(body)
        assert "params" not in parsed
        assert parsed["method"] == "exit"

    @pytest.mark.asyncio
    async def test_correct_content_length(self, initialized_client):
        """Content-Length header should match the encoded body size."""
        client = initialized_client

        await client._send_notification("test/method", {"data": "hello"})

        written_bytes = client.terraform_ls_process.stdin.write.call_args[0][0]
        written_str = written_bytes.decode("utf-8")
        header, body = written_str.split("\r\n\r\n", 1)
        declared_length = int(header.split(":")[1].strip())
        actual_length = len(body.encode("utf-8"))
        assert declared_length == actual_length


# ---------------------------------------------------------------------------
# 6. _close_document()
# ---------------------------------------------------------------------------


class TestCloseDocument:
    """Tests for the _close_document method."""

    @pytest.mark.asyncio
    async def test_sends_did_close_notification(self, initialized_client):
        """_close_document should send a textDocument/didClose notification."""
        client = initialized_client

        await client._close_document("file:///mnt/workspace/main.tf")

        written_bytes = client.terraform_ls_process.stdin.write.call_args[0][0]
        _, body = written_bytes.decode("utf-8").split("\r\n\r\n", 1)
        parsed = json.loads(body)
        assert parsed["method"] == "textDocument/didClose"
        assert parsed["params"]["textDocument"]["uri"] == (
            "file:///mnt/workspace/main.tf"
        )
        assert "id" not in parsed


# ---------------------------------------------------------------------------
# 7. validate_document()
# ---------------------------------------------------------------------------


class TestValidateDocument:
    """Tests for the validate_document method."""

    @pytest.mark.asyncio
    async def test_returns_error_when_not_initialized(self, client, tmp_path):
        """Should return an error dict when the LSP client is not initialized."""
        target = tmp_path / "main.tf"
        target.touch()

        result = await client.validate_document(str(target))
        assert "error" in result
        assert "not initialized" in result["error"]

    @pytest.mark.asyncio
    async def test_rejects_path_outside_workspace(self, client):
        """Should return an error for paths outside the workspace."""
        result = await client.validate_document("/etc/passwd")
        assert "error" in result
        assert "Access denied" in result["error"]

    @pytest.mark.asyncio
    async def test_returns_error_for_nonexistent_file(self, initialized_client, tmp_path):
        """Should return an error when the file does not exist."""
        client = initialized_client
        client.workspace_root = tmp_path

        result = await client.validate_document(str(tmp_path / "nonexistent.tf"))
        assert "error" in result
        assert "does not exist" in result["error"]

    @pytest.mark.asyncio
    async def test_successful_validation(self, initialized_client, tmp_path):
        """Should open the document, sleep for diagnostics, close it, and return success."""
        client = initialized_client
        client.workspace_root = tmp_path

        target = tmp_path / "main.tf"
        target.write_text('resource "aws_instance" "test" {}')

        # Track notification calls
        notifications_sent = []
        original_send_notification = client._send_notification

        async def mock_send_notification(method, params=None):
            notifications_sent.append(method)

        client._send_notification = mock_send_notification

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await client.validate_document(str(target))

        assert result["success"] is True
        assert result["uri"] == f"file://{target}"
        # Should have opened and then closed the document
        assert "textDocument/didOpen" in notifications_sent
        assert "textDocument/didClose" in notifications_sent

    @pytest.mark.asyncio
    async def test_close_document_called_even_on_sleep_error(
        self, initialized_client, tmp_path
    ):
        """_close_document should be called in the finally block even if an error occurs."""
        client = initialized_client
        client.workspace_root = tmp_path

        target = tmp_path / "main.tf"
        target.write_text("# test")

        close_called = False

        async def mock_close(uri):
            nonlocal close_called
            close_called = True

        client._close_document = mock_close
        client._send_notification = AsyncMock()

        with patch("asyncio.sleep", new_callable=AsyncMock):
            await client.validate_document(str(target))

        assert close_called


# ---------------------------------------------------------------------------
# 8. get_hover_info()
# ---------------------------------------------------------------------------


class TestGetHoverInfo:
    """Tests for the get_hover_info method."""

    @pytest.mark.asyncio
    async def test_returns_error_when_not_initialized(self, client, tmp_path):
        """Should return an error dict when client is not initialized."""
        target = tmp_path / "main.tf"
        target.touch()

        result = await client.get_hover_info(str(target), 0, 0)
        assert "error" in result
        assert "not initialized" in result["error"]

    @pytest.mark.asyncio
    async def test_rejects_path_outside_workspace(self, client):
        """Should return error for paths outside workspace."""
        result = await client.get_hover_info("/etc/passwd", 0, 0)
        assert "error" in result
        assert "Access denied" in result["error"]

    @pytest.mark.asyncio
    async def test_sends_correct_position_params(self, initialized_client, tmp_path):
        """Should send the correct line and character in the hover request."""
        client = initialized_client
        client.workspace_root = tmp_path

        target = tmp_path / "main.tf"
        target.write_text('resource "aws_instance" "test" {}')

        hover_response = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "contents": {"kind": "markdown", "value": "aws_instance docs"}
            },
        }

        client._send_notification = AsyncMock()
        client._send_request = AsyncMock(return_value=hover_response)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await client.get_hover_info(str(target), 5, 10)

        # Verify the position was passed correctly
        call_args = client._send_request.call_args
        assert call_args[0][0] == "textDocument/hover"
        params = call_args[0][1]
        assert params["position"]["line"] == 5
        assert params["position"]["character"] == 10

    @pytest.mark.asyncio
    async def test_returns_hover_content(self, initialized_client, tmp_path):
        """Should return hover content from the LSP response."""
        client = initialized_client
        client.workspace_root = tmp_path

        target = tmp_path / "main.tf"
        target.write_text("# test")

        hover_response = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "contents": {"kind": "markdown", "value": "Type: string"}
            },
        }

        client._send_notification = AsyncMock()
        client._send_request = AsyncMock(return_value=hover_response)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await client.get_hover_info(str(target), 0, 0)

        assert result["success"] is True
        assert result["hover"]["kind"] == "markdown"
        assert result["hover"]["value"] == "Type: string"

    @pytest.mark.asyncio
    async def test_returns_none_hover_when_no_info(self, initialized_client, tmp_path):
        """Should return hover=None when LSP provides no hover result."""
        client = initialized_client
        client.workspace_root = tmp_path

        target = tmp_path / "main.tf"
        target.write_text("# test")

        empty_response = {"jsonrpc": "2.0", "id": 1, "result": None}

        client._send_notification = AsyncMock()
        client._send_request = AsyncMock(return_value=empty_response)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await client.get_hover_info(str(target), 0, 0)

        assert result["success"] is True
        assert result["hover"] is None
        assert "No hover information" in result["message"]

    @pytest.mark.asyncio
    async def test_handles_file_not_on_disk(self, initialized_client, tmp_path):
        """When file does not exist on disk, should skip didOpen but still send didClose."""
        client = initialized_client
        client.workspace_root = tmp_path

        target = tmp_path / "missing.tf"

        hover_response = {"jsonrpc": "2.0", "id": 1, "result": None}
        client._send_notification = AsyncMock()
        client._send_request = AsyncMock(return_value=hover_response)

        result = await client.get_hover_info(str(target), 0, 0)

        # didOpen should NOT have been called (file doesn't exist), but
        # didClose is always sent via the finally block.
        assert client._send_notification.call_count == 1
        call_method = client._send_notification.call_args[0][0]
        assert call_method == "textDocument/didClose"
        assert result["success"] is True


# ---------------------------------------------------------------------------
# 9. get_completions()
# ---------------------------------------------------------------------------


class TestGetCompletions:
    """Tests for the get_completions method."""

    @pytest.mark.asyncio
    async def test_returns_error_when_not_initialized(self, client, tmp_path):
        """Should return an error dict when client is not initialized."""
        target = tmp_path / "main.tf"
        target.touch()

        result = await client.get_completions(str(target), 0, 0)
        assert "error" in result
        assert "not initialized" in result["error"]

    @pytest.mark.asyncio
    async def test_rejects_path_outside_workspace(self, client):
        """Should return error for paths outside workspace."""
        result = await client.get_completions("/etc/passwd", 0, 0)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_handles_list_result(self, initialized_client, tmp_path):
        """When LSP returns a list of completions, should wrap them correctly."""
        client = initialized_client
        client.workspace_root = tmp_path

        target = tmp_path / "main.tf"
        target.write_text("res")

        completions_list = [
            {"label": "resource", "kind": 14},
            {"label": "required_providers", "kind": 14},
        ]
        response = {"jsonrpc": "2.0", "id": 1, "result": completions_list}

        client._send_notification = AsyncMock()
        client._send_request = AsyncMock(return_value=response)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await client.get_completions(str(target), 0, 3)

        assert result["success"] is True
        assert len(result["completions"]) == 2
        assert result["completions"][0]["label"] == "resource"

    @pytest.mark.asyncio
    async def test_handles_dict_result_with_items(self, initialized_client, tmp_path):
        """When LSP returns a CompletionList dict, should extract 'items'."""
        client = initialized_client
        client.workspace_root = tmp_path

        target = tmp_path / "main.tf"
        target.write_text("res")

        completion_list = {
            "isIncomplete": False,
            "items": [
                {"label": "resource", "kind": 14},
            ],
        }
        response = {"jsonrpc": "2.0", "id": 1, "result": completion_list}

        client._send_notification = AsyncMock()
        client._send_request = AsyncMock(return_value=response)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await client.get_completions(str(target), 0, 3)

        assert result["success"] is True
        assert len(result["completions"]) == 1
        assert result["completions"][0]["label"] == "resource"

    @pytest.mark.asyncio
    async def test_empty_result(self, initialized_client, tmp_path):
        """When LSP has no result key, should return empty completions."""
        client = initialized_client
        client.workspace_root = tmp_path

        target = tmp_path / "main.tf"
        target.write_text("")

        response = {"jsonrpc": "2.0", "id": 1}
        client._send_notification = AsyncMock()
        client._send_request = AsyncMock(return_value=response)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await client.get_completions(str(target), 0, 0)

        assert result["success"] is True
        assert result["completions"] == []

    @pytest.mark.asyncio
    async def test_sends_correct_position(self, initialized_client, tmp_path):
        """Should pass correct line and character to the LSP request."""
        client = initialized_client
        client.workspace_root = tmp_path

        target = tmp_path / "main.tf"
        target.write_text("resource")

        response = {"jsonrpc": "2.0", "id": 1, "result": []}
        client._send_notification = AsyncMock()
        client._send_request = AsyncMock(return_value=response)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            await client.get_completions(str(target), 7, 15)

        call_args = client._send_request.call_args
        assert call_args[0][0] == "textDocument/completion"
        params = call_args[0][1]
        assert params["position"]["line"] == 7
        assert params["position"]["character"] == 15


# ---------------------------------------------------------------------------
# 10. format_document()
# ---------------------------------------------------------------------------


class TestFormatDocument:
    """Tests for the format_document method."""

    @pytest.mark.asyncio
    async def test_returns_error_when_not_initialized(self, client, tmp_path):
        """Should return an error dict when client is not initialized."""
        target = tmp_path / "main.tf"
        target.touch()

        result = await client.format_document(str(target))
        assert "error" in result
        assert "not initialized" in result["error"]

    @pytest.mark.asyncio
    async def test_rejects_path_outside_workspace(self, client):
        """Should return error for paths outside workspace."""
        result = await client.format_document("/etc/passwd")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_returns_formatting_edits(self, initialized_client, tmp_path):
        """Should return text edits from the LSP formatting response."""
        client = initialized_client
        client.workspace_root = tmp_path

        target = tmp_path / "main.tf"
        target.write_text('resource "aws_instance" "test"  {}')

        edits = [
            {
                "range": {
                    "start": {"line": 0, "character": 30},
                    "end": {"line": 0, "character": 32},
                },
                "newText": " ",
            }
        ]
        response = {"jsonrpc": "2.0", "id": 1, "result": edits}

        client._send_notification = AsyncMock()
        client._send_request = AsyncMock(return_value=response)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await client.format_document(str(target))

        assert result["success"] is True
        assert len(result["edits"]) == 1
        assert result["edits"][0]["newText"] == " "

    @pytest.mark.asyncio
    async def test_empty_edits_when_already_formatted(self, initialized_client, tmp_path):
        """Should return empty edits list when document needs no changes."""
        client = initialized_client
        client.workspace_root = tmp_path

        target = tmp_path / "main.tf"
        target.write_text('resource "aws_instance" "test" {}')

        response = {"jsonrpc": "2.0", "id": 1, "result": []}
        client._send_notification = AsyncMock()
        client._send_request = AsyncMock(return_value=response)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await client.format_document(str(target))

        assert result["success"] is True
        assert result["edits"] == []

    @pytest.mark.asyncio
    async def test_sends_formatting_options(self, initialized_client, tmp_path):
        """Should send tabSize and insertSpaces in the formatting request."""
        client = initialized_client
        client.workspace_root = tmp_path

        target = tmp_path / "main.tf"
        target.write_text("# test")

        response = {"jsonrpc": "2.0", "id": 1, "result": []}
        client._send_notification = AsyncMock()
        client._send_request = AsyncMock(return_value=response)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            await client.format_document(str(target))

        call_args = client._send_request.call_args
        assert call_args[0][0] == "textDocument/formatting"
        params = call_args[0][1]
        assert params["options"]["tabSize"] == 2
        assert params["options"]["insertSpaces"] is True

    @pytest.mark.asyncio
    async def test_no_result_returns_empty_edits(self, initialized_client, tmp_path):
        """When LSP response has no 'result' key, should return empty edits."""
        client = initialized_client
        client.workspace_root = tmp_path

        target = tmp_path / "main.tf"
        target.write_text("# test")

        response = {"jsonrpc": "2.0", "id": 1}
        client._send_notification = AsyncMock()
        client._send_request = AsyncMock(return_value=response)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await client.format_document(str(target))

        assert result["success"] is True
        assert result["edits"] == []


# ---------------------------------------------------------------------------
# 11. shutdown()
# ---------------------------------------------------------------------------


class TestShutdown:
    """Tests for the shutdown method."""

    @pytest.mark.asyncio
    async def test_sends_shutdown_and_exit_when_initialized(self, initialized_client):
        """Should send shutdown request then exit notification, then terminate."""
        client = initialized_client

        requests_sent = []
        notifications_sent = []

        async def mock_send_request(method, params=None):
            requests_sent.append(method)
            return {"jsonrpc": "2.0", "id": 1, "result": None}

        async def mock_send_notification(method, params=None):
            notifications_sent.append(method)

        client._send_request = mock_send_request
        client._send_notification = mock_send_notification

        await client.shutdown()

        assert "shutdown" in requests_sent
        assert "exit" in notifications_sent
        client.terraform_ls_process.terminate.assert_called_once()

    @pytest.mark.asyncio
    async def test_kills_process_on_wait_timeout(self, initialized_client):
        """Should kill the process if it doesn't exit within 5 seconds."""
        client = initialized_client
        client._send_request = AsyncMock(
            return_value={"jsonrpc": "2.0", "id": 1, "result": None}
        )
        client._send_notification = AsyncMock()
        client.terraform_ls_process.wait = AsyncMock(
            side_effect=asyncio.TimeoutError()
        )

        await client.shutdown()

        client.terraform_ls_process.kill.assert_called_once()

    @pytest.mark.asyncio
    async def test_skips_shutdown_request_when_not_initialized(self, tmp_path):
        """When not initialized, should skip shutdown/exit but still terminate process."""
        client = TerraformLSPClient(workspace_root=str(tmp_path))
        client.initialized = False
        mock_process = MagicMock()
        mock_process.terminate = MagicMock()
        mock_process.wait = AsyncMock()
        client.terraform_ls_process = mock_process

        await client.shutdown()

        mock_process.terminate.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_no_process(self, client):
        """Should not raise when terraform_ls_process is None."""
        client.initialized = False
        client.terraform_ls_process = None

        await client.shutdown()  # Should not raise

    @pytest.mark.asyncio
    async def test_handles_exception_during_shutdown(self, initialized_client):
        """Exceptions during shutdown should be caught and logged."""
        client = initialized_client
        client._send_request = AsyncMock(side_effect=RuntimeError("connection lost"))

        # Should not raise
        await client.shutdown()


# ---------------------------------------------------------------------------
# 12. start_terraform_ls()
# ---------------------------------------------------------------------------


class TestStartTerraformLs:
    """Tests for the start_terraform_ls method."""

    @pytest.mark.asyncio
    async def test_returns_false_for_nonexistent_workspace(self, client):
        """Should return False and set initialization_error for missing workspace."""
        result = await client.start_terraform_ls("/nonexistent/path")
        assert result is False
        assert "does not exist" in client.initialization_error

    @pytest.mark.asyncio
    async def test_returns_false_when_binary_not_found(self, client, tmp_path):
        """Should return False when terraform-ls binary is not in PATH."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="")
            result = await client.start_terraform_ls(str(tmp_path))

        assert result is False
        assert "not found" in client.initialization_error

    @pytest.mark.asyncio
    async def test_returns_false_when_process_exits_immediately(self, client, tmp_path):
        """Should return False if terraform-ls process exits right away."""
        mock_which = MagicMock(returncode=0, stdout="/usr/bin/terraform-ls\n")
        mock_version = MagicMock(returncode=0, stdout="0.38.5\n")

        mock_process = MagicMock()
        mock_process.returncode = 1  # Exited immediately
        mock_process.stderr = MagicMock()
        mock_process.stderr.read = AsyncMock(return_value=b"some error")

        with patch("subprocess.run", side_effect=[mock_which, mock_version]):
            with patch("asyncio.create_subprocess_exec", return_value=mock_process):
                with patch("asyncio.sleep", new_callable=AsyncMock):
                    result = await client.start_terraform_ls(str(tmp_path))

        assert result is False
        assert "exited" in client.initialization_error

    @pytest.mark.asyncio
    async def test_calls_initialize_on_successful_start(self, client, tmp_path):
        """Should call _initialize when process starts successfully."""
        mock_which = MagicMock(returncode=0, stdout="/usr/bin/terraform-ls\n")
        mock_version = MagicMock(returncode=0, stdout="0.38.5\n")

        mock_process = MagicMock()
        mock_process.returncode = None  # Still running

        with patch("subprocess.run", side_effect=[mock_which, mock_version]):
            with patch("asyncio.create_subprocess_exec", return_value=mock_process):
                with patch("asyncio.sleep", new_callable=AsyncMock):
                    with patch.object(
                        client, "_initialize", new_callable=AsyncMock
                    ) as mock_init:
                        mock_init.return_value = True
                        result = await client.start_terraform_ls(str(tmp_path))

        assert result is True
        mock_init.assert_called_once_with(str(tmp_path))

    @pytest.mark.asyncio
    async def test_returns_false_when_initialize_fails(self, client, tmp_path):
        """Should return False when _initialize returns False."""
        mock_which = MagicMock(returncode=0, stdout="/usr/bin/terraform-ls\n")
        mock_version = MagicMock(returncode=0, stdout="0.38.5\n")

        mock_process = MagicMock()
        mock_process.returncode = None

        with patch("subprocess.run", side_effect=[mock_which, mock_version]):
            with patch("asyncio.create_subprocess_exec", return_value=mock_process):
                with patch("asyncio.sleep", new_callable=AsyncMock):
                    with patch.object(
                        client, "_initialize", new_callable=AsyncMock
                    ) as mock_init:
                        mock_init.return_value = False
                        result = await client.start_terraform_ls(str(tmp_path))

        assert result is False


# ---------------------------------------------------------------------------
# 13. _initialize()
# ---------------------------------------------------------------------------


class TestInitialize:
    """Tests for the _initialize method."""

    @pytest.mark.asyncio
    async def test_successful_initialization(self, initialized_client, tmp_path):
        """Should set initialized=True and store capabilities on success."""
        client = initialized_client
        client.initialized = False  # Reset for this test

        response = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "capabilities": {
                    "hoverProvider": True,
                    "completionProvider": {},
                    "documentFormattingProvider": True,
                }
            },
        }

        client._send_request = AsyncMock(return_value=response)
        client._send_notification = AsyncMock()

        result = await client._initialize(str(tmp_path))

        assert result is True
        assert client.initialized is True
        assert "hoverProvider" in client.capabilities
        client._send_notification.assert_called_once_with("initialized", {})

    @pytest.mark.asyncio
    async def test_initialization_error_response(self, initialized_client, tmp_path):
        """Should return False and store error when LSP returns an error."""
        client = initialized_client
        client.initialized = False

        response = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"code": -32600, "message": "Invalid request"},
        }

        client._send_request = AsyncMock(return_value=response)

        result = await client._initialize(str(tmp_path))

        assert result is False
        assert client.initialization_error is not None
        assert "LSP error" in client.initialization_error

    @pytest.mark.asyncio
    async def test_unexpected_response(self, initialized_client, tmp_path):
        """Should return False for unexpected response format."""
        client = initialized_client
        client.initialized = False

        response = {"jsonrpc": "2.0", "id": 1}  # No "result" or "error"
        client._send_request = AsyncMock(return_value=response)

        result = await client._initialize(str(tmp_path))

        assert result is False
        assert "Unexpected response" in client.initialization_error

    @pytest.mark.asyncio
    async def test_exception_during_initialization(self, initialized_client, tmp_path):
        """Should catch exceptions and return False."""
        client = initialized_client
        client.initialized = False

        client._send_request = AsyncMock(
            side_effect=RuntimeError("connection refused")
        )

        result = await client._initialize(str(tmp_path))

        assert result is False
        assert "connection refused" in client.initialization_error

    @pytest.mark.asyncio
    async def test_sends_correct_init_params(self, initialized_client, tmp_path):
        """Should include processId, clientInfo, rootUri, and capabilities."""
        client = initialized_client
        client.initialized = False

        response = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"capabilities": {}},
        }
        client._send_request = AsyncMock(return_value=response)
        client._send_notification = AsyncMock()

        await client._initialize(str(tmp_path))

        call_args = client._send_request.call_args
        assert call_args[0][0] == "initialize"
        params = call_args[0][1]
        assert params["processId"] == os.getpid()
        assert params["clientInfo"]["name"] == "terry-form-mcp"
        assert params["rootUri"] == f"file://{tmp_path}"
        assert "textDocument" in params["capabilities"]
        assert "workspace" in params["capabilities"]


# ---------------------------------------------------------------------------
# 14. get_lsp_client() — singleton factory
# ---------------------------------------------------------------------------


class TestGetLspClient:
    """Tests for the module-level get_lsp_client() async singleton factory."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset the global singleton before and after each test."""
        import terraform_lsp_client as mod

        original = mod._lsp_client
        mod._lsp_client = None
        yield
        mod._lsp_client = original

    @pytest.mark.asyncio
    async def test_returns_client_instance(self):
        """Should return a TerraformLSPClient when called without workspace_path."""
        import terraform_lsp_client as mod

        # When workspace_path is None, it creates client but doesn't start
        client = await get_lsp_client()
        assert isinstance(client, TerraformLSPClient)

    @pytest.mark.asyncio
    async def test_singleton_returns_same_instance(self):
        """Successive calls should return the same instance."""
        client1 = await get_lsp_client()
        client2 = await get_lsp_client()
        assert client1 is client2

    @pytest.mark.asyncio
    async def test_raises_on_failed_initialization(self, tmp_path):
        """Should raise RuntimeError and reset singleton on start failure."""
        import terraform_lsp_client as mod

        with patch.object(
            TerraformLSPClient,
            "start_terraform_ls",
            new_callable=AsyncMock,
            return_value=False,
        ):
            with pytest.raises(RuntimeError, match="Failed to initialize"):
                await get_lsp_client(str(tmp_path))

        # Singleton should be reset to None for retry
        assert mod._lsp_client is None

    @pytest.mark.asyncio
    async def test_captures_error_message_on_failure(self, tmp_path):
        """Should include the initialization error in the RuntimeError message."""

        async def mock_start(workspace_path):
            # Simulate setting initialization_error before returning False
            import terraform_lsp_client as mod

            if mod._lsp_client:
                mod._lsp_client.initialization_error = "terraform-ls binary not found"
            return False

        with patch.object(
            TerraformLSPClient, "start_terraform_ls", side_effect=mock_start
        ):
            with pytest.raises(RuntimeError, match="terraform-ls binary not found"):
                await get_lsp_client(str(tmp_path))

    @pytest.mark.asyncio
    async def test_concurrent_access_returns_same_instance(self):
        """Multiple concurrent calls should safely return the same instance."""
        results = await asyncio.gather(
            get_lsp_client(),
            get_lsp_client(),
            get_lsp_client(),
        )

        # All should be the same instance
        assert results[0] is results[1]
        assert results[1] is results[2]

    @pytest.mark.asyncio
    async def test_skips_start_when_no_workspace_path(self):
        """When workspace_path is None, should not call start_terraform_ls."""
        with patch.object(
            TerraformLSPClient, "start_terraform_ls", new_callable=AsyncMock
        ) as mock_start:
            await get_lsp_client(None)
            mock_start.assert_not_called()

    @pytest.mark.asyncio
    async def test_retry_after_failure(self, tmp_path):
        """After a failure resets the singleton, a subsequent call should retry."""
        import terraform_lsp_client as mod

        call_count = 0

        async def mock_start(workspace_path):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                mod._lsp_client.initialization_error = "first failure"
                return False
            return True

        with patch.object(
            TerraformLSPClient, "start_terraform_ls", side_effect=mock_start
        ):
            # First call should fail
            with pytest.raises(RuntimeError):
                await get_lsp_client(str(tmp_path))

            # Second call should succeed (singleton was reset)
            client = await get_lsp_client(str(tmp_path))
            assert isinstance(client, TerraformLSPClient)
            assert call_count == 2


# ---------------------------------------------------------------------------
# 15. __init__() — constructor defaults
# ---------------------------------------------------------------------------


class TestInit:
    """Tests for the TerraformLSPClient constructor."""

    def test_default_workspace_root(self):
        """Default workspace_root should be /mnt/workspace."""
        client = TerraformLSPClient()
        assert client.workspace_root == Path("/mnt/workspace")

    def test_custom_workspace_root(self, tmp_path):
        """Custom workspace_root should be stored as a Path."""
        client = TerraformLSPClient(workspace_root=str(tmp_path))
        assert client.workspace_root == tmp_path

    def test_initial_state(self, tmp_path):
        """Fresh client should have correct initial state."""
        client = TerraformLSPClient(workspace_root=str(tmp_path))
        assert client.terraform_ls_process is None
        assert client.request_id == 0
        assert client.initialized is False
        assert client.capabilities == {}
        assert client.initialization_error is None
