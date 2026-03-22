#!/usr/bin/env python3
"""
RED tests for code quality fixes in server_enhanced_with_lsp.py and routes.py.

Covers 8 changes:
1. No duplicate json import in server_enhanced_with_lsp.py
2. terry() uses tf_vars not vars (builtin shadow)
3. No duplicate __version__ in server_enhanced_with_lsp.py; imports from _version
4. _resolve_lsp_paths helper extracted and used in 4 LSP functions
5. _MAX_TF_FILE_SIZE module-level constant replaces 4 local definitions
6. _check_tf_cloud_token helper extracted from 4 TF Cloud stubs
7. terraform_dir_exists removed from terry_workspace_info (redundant)
8. tool_count in routes.py is dynamic (from tools.json), not hardcoded 25
"""

import ast
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_SRC = str(Path(__file__).parent.parent / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SERVER_PATH = Path(__file__).parent.parent / "src" / "server_enhanced_with_lsp.py"
_ROUTES_PATH = Path(__file__).parent.parent / "src" / "frontend" / "routes.py"


def _server_source() -> str:
    return _SERVER_PATH.read_text()


def _routes_source() -> str:
    return _ROUTES_PATH.read_text()


def _server_ast() -> ast.Module:
    return ast.parse(_server_source())


# ---------------------------------------------------------------------------
# Fix 1: No duplicate json import (import json as _json must be removed)
# ---------------------------------------------------------------------------


class TestNoDuplicateJsonImport:
    """import json as _json must be removed; _json.dumps replaced with json.dumps."""

    def test_no_import_json_as_underscore_json(self):
        """server_enhanced_with_lsp.py must not contain 'import json as _json'."""
        src = _server_source()
        assert "import json as _json" not in src, (
            "Duplicate 'import json as _json' still present. Remove it."
        )

    def test_no_underscore_json_dumps_usage(self):
        """_json.dumps must not appear anywhere in the server file."""
        src = _server_source()
        assert "_json.dumps" not in src, (
            "_json.dumps still referenced. Replace with json.dumps."
        )

    def test_json_import_still_present(self):
        """The regular 'import json' must still be present."""
        src = _server_source()
        assert "import json\n" in src or "import json\r\n" in src, (
            "'import json' must be kept in the file."
        )


# ---------------------------------------------------------------------------
# Fix 2: terry() uses tf_vars not vars (builtin shadow)
# ---------------------------------------------------------------------------


class TestTerryParameterRename:
    """terry() must use tf_vars instead of vars."""

    def test_no_vars_parameter_in_terry_signature(self):
        """terry() function must not have 'vars' as a parameter name."""
        src = _server_source()
        # Find the terry function definition
        tree = _server_ast()
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "terry":
                param_names = [a.arg for a in node.args.args]
                assert "vars" not in param_names, (
                    "terry() still uses 'vars' as a parameter name, which shadows the built-in. "
                    "Rename to 'tf_vars'."
                )
                return
        pytest.fail("terry() function not found in server file")

    def test_tf_vars_parameter_in_terry_signature(self):
        """terry() function must have 'tf_vars' as a parameter name."""
        tree = _server_ast()
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "terry":
                param_names = [a.arg for a in node.args.args]
                assert "tf_vars" in param_names, (
                    "terry() must have 'tf_vars' as a parameter (rename from 'vars')."
                )
                return
        pytest.fail("terry() function not found in server file")

    def test_terry_docstring_references_tf_vars(self):
        """terry() docstring must reference tf_vars, not bare vars."""
        tree = _server_ast()
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "terry":
                docstring = ast.get_docstring(node) or ""
                # The old docstring had '    vars: Terraform variables'
                # (bare 'vars:' preceded only by whitespace, not by 'tf_').
                # 'tf_vars:' is acceptable; bare 'vars:' (without tf_ prefix) is not.
                import re
                bare_vars = re.search(r'(?<!tf_)(?<!\w)vars:', docstring)
                assert bare_vars is None, (
                    "terry() docstring still references bare 'vars:'. Update to 'tf_vars:'."
                )
                return
        pytest.fail("terry() function not found in server file")

    def test_terry_body_uses_tf_vars_not_bare_vars_assignment(self):
        """terry() body must use tf_vars, not assign bare 'vars'."""
        src = _server_source()
        # The old pattern was: if vars is None: vars = {}
        assert "if vars is None:" not in src, (
            "Old 'if vars is None:' guard still present. Update to 'if tf_vars is None:'."
        )


# ---------------------------------------------------------------------------
# Fix 3: No duplicate __version__ at top of server file; imports from _version
# ---------------------------------------------------------------------------


class TestNoInlineVersionDeclaration:
    """server file must not declare __version__ inline; must import from _version."""

    def test_no_inline_version_assignment(self):
        """server_enhanced_with_lsp.py must not contain '__version__ = \"3.1.0\"'."""
        src = _server_source()
        assert '__version__ = "3.1.0"' not in src, (
            "Inline __version__ = '3.1.0' still present. Remove it and import from _version."
        )

    def test_imports_from_version_module(self):
        """server_enhanced_with_lsp.py must import __version__ from _version."""
        src = _server_source()
        assert "from _version import __version__" in src, (
            "server file must contain 'from _version import __version__'."
        )


# ---------------------------------------------------------------------------
# Fix 4: _resolve_lsp_paths helper extracted
# ---------------------------------------------------------------------------


class TestResolveLspPathsHelper:
    """_resolve_lsp_paths must exist as a module-level helper."""

    def test_resolve_lsp_paths_defined_in_source(self):
        """_resolve_lsp_paths must be defined at module level in server file."""
        src = _server_source()
        assert "def _resolve_lsp_paths" in src, (
            "_resolve_lsp_paths helper function not found in server file."
        )

    def test_resolve_lsp_paths_has_correct_signature(self):
        """_resolve_lsp_paths(file_path, workspace_path) must exist."""
        tree = _server_ast()
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_resolve_lsp_paths":
                param_names = [a.arg for a in node.args.args]
                assert "file_path" in param_names, (
                    "_resolve_lsp_paths must accept 'file_path' parameter."
                )
                assert "workspace_path" in param_names, (
                    "_resolve_lsp_paths must accept 'workspace_path' parameter."
                )
                return
        pytest.fail("_resolve_lsp_paths not found in AST")

    def test_lsp_functions_use_resolve_helper(self):
        """terraform_validate_lsp, terraform_hover, terraform_complete, and terraform_format_lsp must call _resolve_lsp_paths."""
        src = _server_source()
        lsp_functions = [
            "terraform_validate_lsp",
            "terraform_hover",
            "terraform_complete",
            "terraform_format_lsp",
        ]
        tree = _server_ast()
        for func_name in lsp_functions:
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == func_name:
                    # Check that _resolve_lsp_paths is called somewhere in this function
                    func_src = ast.unparse(node)
                    assert "_resolve_lsp_paths" in func_src, (
                        f"{func_name} must call _resolve_lsp_paths() instead of inlining the path resolution block."
                    )
                    break

    def test_duplicate_path_resolution_block_removed(self):
        """The 4 LSP tool functions must not inline their own path-resolution block."""
        tree = _server_ast()
        lsp_functions = [
            "terraform_validate_lsp",
            "terraform_hover",
            "terraform_complete",
            "terraform_format_lsp",
        ]
        for func_name in lsp_functions:
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == func_name:
                    func_src = ast.unparse(node)
                    # If the function still inlines the block, it will contain this pattern
                    # (an if/else that sets full_workspace_path via workspace_path branch)
                    # without calling _resolve_lsp_paths
                    assert "if workspace_path:" not in func_src or "_resolve_lsp_paths" in func_src, (
                        f"{func_name} still inlines the path-resolution if/else block "
                        "instead of calling _resolve_lsp_paths()."
                    )
                    break


# ---------------------------------------------------------------------------
# Fix 5: _MAX_TF_FILE_SIZE promoted to module-level constant
# ---------------------------------------------------------------------------


class TestMaxTfFileSizeConstant:
    """_MAX_TF_FILE_SIZE must be a module-level constant (not local vars)."""

    def test_module_level_constant_defined(self):
        """_MAX_TF_FILE_SIZE must be defined at module level."""
        src = _server_source()
        assert "_MAX_TF_FILE_SIZE" in src, (
            "_MAX_TF_FILE_SIZE constant not found in server file."
        )

    def test_constant_value_is_10mb(self):
        """_MAX_TF_FILE_SIZE must equal 10 * 1024 * 1024 (10 MB)."""
        tree = _server_ast()
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Assign)
                and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == "_MAX_TF_FILE_SIZE"
            ):
                # ast.literal_eval cannot handle BinOp (e.g. 10 * 1024 * 1024),
                # so compile and eval the expression source text directly.
                expr_src = ast.unparse(node.value)
                val = eval(compile(expr_src, "<string>", "eval"))  # noqa: S307
                assert val == 10 * 1024 * 1024, (
                    f"_MAX_TF_FILE_SIZE should be 10485760 (10 MB), got {val}."
                )
                return
        pytest.fail("_MAX_TF_FILE_SIZE module-level assignment not found")

    def test_no_local_max_tf_file_size_definitions(self):
        """MAX_TF_FILE_SIZE must not be defined as a local variable in any function."""
        src = _server_source()
        # Old pattern was: MAX_TF_FILE_SIZE = 10 * 1024 * 1024  # 10MB
        # After fix, only _MAX_TF_FILE_SIZE at module level should exist
        # Count local (non-underscored) MAX_TF_FILE_SIZE assignments
        import re
        # Match lines with MAX_TF_FILE_SIZE = (without leading underscore)
        local_defs = re.findall(r"^\s+MAX_TF_FILE_SIZE\s*=", src, re.MULTILINE)
        assert len(local_defs) == 0, (
            f"Found {len(local_defs)} local MAX_TF_FILE_SIZE definition(s) inside functions. "
            "Promote to module-level _MAX_TF_FILE_SIZE constant."
        )


# ---------------------------------------------------------------------------
# Fix 6: _check_tf_cloud_token helper preserved in commented-out block
#
# The 4 tf_cloud_* tools and their _check_tf_cloud_token helper have been
# removed from the MCP tool registry (decorators commented out, planned for
# v3.2.0). The implementation is preserved as a comment block. These tests
# verify the comment block is present rather than the live AST nodes.
# ---------------------------------------------------------------------------


class TestCheckTfCloudTokenHelper:
    """_check_tf_cloud_token and the tf_cloud block must be in the source as comments."""

    def test_helper_preserved_in_comments(self):
        """_check_tf_cloud_token must be present in the commented-out block."""
        src = _server_source()
        assert "_check_tf_cloud_token" in src, (
            "_check_tf_cloud_token is not present anywhere in server file. "
            "It should be preserved in the commented-out tf_cloud block."
        )

    def test_tf_cloud_block_comment_marker_present(self):
        """The tf_cloud removal marker comment must be in the file."""
        src = _server_source()
        assert "Terraform Cloud tools (planned for v3.2.0)" in src, (
            "Removal marker 'Terraform Cloud tools (planned for v3.2.0)' "
            "not found. Add the prescribed comment header above the commented-out block."
        )

    def test_tf_cloud_functions_not_active_in_ast(self):
        """The 4 tf_cloud_* function names must not appear as live AST nodes."""
        tf_cloud_functions = {
            "tf_cloud_list_workspaces",
            "tf_cloud_get_workspace",
            "tf_cloud_list_runs",
            "tf_cloud_get_state_outputs",
        }
        tree = _server_ast()
        active_names = {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        still_active = tf_cloud_functions & active_names
        assert len(still_active) == 0, (
            f"These tf_cloud functions are still active in the AST: {still_active}. "
            "Comment out the @mcp.tool() decorators and function bodies."
        )

    def test_inline_token_checks_not_in_active_code(self):
        """No active (non-commented) tf_cloud function body should inline TF_API_TOKEN checks."""
        import re as _re
        src = _server_source()
        # Strip comment lines to count only active occurrences
        active_lines = [
            line for line in src.splitlines() if not line.lstrip().startswith("#")
        ]
        active_src = "\n".join(active_lines)
        matches = _re.findall(r'token\s*=\s*os\.environ\.get\("TF_API_TOKEN"\)', active_src)
        assert len(matches) == 0, (
            f"Found {len(matches)} active (non-commented) TF_API_TOKEN inline checks. "
            "These must only exist inside the commented-out tf_cloud block."
        )


# ---------------------------------------------------------------------------
# Fix 7: terraform_dir_exists removed from terry_workspace_info
# ---------------------------------------------------------------------------


class TestNoRedundantTerraformDirExists:
    """terraform_dir_exists key is identical to initialized and must be removed."""

    def test_terraform_dir_exists_not_in_workspace_info_source(self):
        """'terraform_dir_exists' must not appear in terry_workspace_info function body."""
        src = _server_source()
        tree = _server_ast()
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "terry_workspace_info":
                func_src = ast.unparse(node)
                assert "terraform_dir_exists" not in func_src, (
                    "terraform_dir_exists key is redundant (identical to initialized). "
                    "Remove it from terry_workspace_info."
                )
                return
        pytest.fail("terry_workspace_info not found in AST")


# ---------------------------------------------------------------------------
# Fix 8: tool_count in _get_server_status is dynamic
# ---------------------------------------------------------------------------


class TestDynamicToolCount:
    """tool_count in routes.py _get_server_status must be dynamic, not hardcoded 25."""

    def test_no_hardcoded_tool_count_25_in_get_server_status(self):
        """_get_server_status in routes.py must not hardcode 'tool_count': 25."""
        src = _routes_source()
        # Look for the literal integer 25 in the context of tool_count
        import re
        hardcoded = re.findall(r'"tool_count"\s*:\s*25\b', src)
        assert len(hardcoded) == 0, (
            "routes.py _get_server_status hardcodes 'tool_count': 25. "
            "Make it dynamic (read from tools.json or compute from tool registry)."
        )

    def test_tool_count_uses_tools_json_data(self):
        """_get_server_status must derive tool_count from _load_tools_json() or similar."""
        src = _routes_source()
        # After fix, tool_count should come from the loaded tools.json data
        # Accept either _load_tools_json() call or tools_data["tool_count"]
        uses_dynamic = (
            "_load_tools_json" in src or
            'tools_data["tool_count"]' in src or
            "tool_count" in src and "tools_json" in src
        )
        assert uses_dynamic, (
            "_get_server_status in routes.py must compute tool_count dynamically "
            "from tools.json data rather than hardcoding 25."
        )
