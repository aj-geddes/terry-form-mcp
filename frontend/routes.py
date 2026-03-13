"""HTTP route handlers for the Terry-Form MCP configuration frontend.

Registers routes on the FastMCP server via @mcp.custom_route().
Uses Jinja2 for template rendering and HTMX for partial page updates.
"""

import hashlib
import hmac
import json
import logging
import os
import secrets
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, Response

from .config_manager import ConfigManager
from .schemas import SECTION_TO_KEY, RESTART_REQUIRED_FIELDS

logger = logging.getLogger(__name__)

# Template directory
_TEMPLATE_DIR = Path(__file__).parent / "templates"
_STATIC_DIR = Path(__file__).parent / "static"

# Jinja2 environment
_jinja_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=select_autoescape(["html"]),
    enable_async=False,
)

# Tab definitions for the config page
CONFIG_TABS = [
    {"id": "server", "label": "Server"},
    {"id": "github", "label": "GitHub"},
    {"id": "terraform-cloud", "label": "Terraform Cloud"},
    {"id": "cloud-credentials", "label": "Cloud Providers"},
    {"id": "rate-limits", "label": "Rate Limits"},
    {"id": "terraform-options", "label": "Terraform Options"},
]

# Map tab IDs to partial template filenames
_TAB_TEMPLATES = {
    "server": "partials/_server_settings.html",
    "github": "partials/_github_settings.html",
    "terraform-cloud": "partials/_terraform_cloud.html",
    "cloud-credentials": "partials/_cloud_credentials.html",
    "rate-limits": "partials/_rate_limits.html",
    "terraform-options": "partials/_terraform_options.html",
}

# CSRF secret (generated once per process)
_CSRF_SECRET = os.environ.get("TERRY_CSRF_SECRET", secrets.token_hex(32))

# Server start time for uptime calculation
_START_TIME = time.time()


def _generate_csrf_token() -> str:
    """Generate a CSRF token."""
    return secrets.token_hex(32)


def _verify_csrf_token(request: Request, token: str) -> bool:
    """Verify the CSRF token from the request header."""
    expected = request.cookies.get("csrf_token")
    if not expected or not token:
        return False
    return hmac.compare_digest(expected, token)


def _render(template_name: str, **context: Any) -> str:
    """Render a Jinja2 template with common context."""
    template = _jinja_env.get_template(template_name)
    return template.render(**context)


def _html(content: str, status_code: int = 200, headers: Optional[Dict] = None) -> HTMLResponse:
    """Create an HTMLResponse with optional headers."""
    resp = HTMLResponse(content, status_code=status_code)
    if headers:
        for k, v in headers.items():
            resp.headers[k] = v
    return resp


def _set_csrf_cookie(response: Response, token: str) -> Response:
    """Set the CSRF token cookie on a response."""
    response.set_cookie(
        "csrf_token",
        token,
        httponly=True,
        samesite="strict",
        max_age=3600,
    )
    return response


def _check_auth(request: Request, config_mgr: ConfigManager) -> Optional[Response]:
    """Check if request is authenticated when API key is configured.

    Returns None if OK, or a redirect/error response if not.
    """
    api_key = config_mgr.config.server.api_key
    if not api_key:
        return None  # No auth required

    # Check session cookie
    session = request.cookies.get("terry_session")
    if session:
        expected = hashlib.sha256(
            f"{api_key}:{_CSRF_SECRET}".encode()
        ).hexdigest()
        if hmac.compare_digest(session, expected):
            return None

    # Not authenticated — serve login page for GET, 401 for API
    if request.url.path.startswith("/api/"):
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    return _html(_render("login.html", csrf_token="", error=""), status_code=401)


def _get_server_status(config_mgr: ConfigManager) -> Dict[str, Any]:
    """Gather server status information."""
    config = config_mgr.config
    uptime_seconds = int(time.time() - _START_TIME)
    hours, remainder = divmod(uptime_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    # Check terraform version
    tf_version = None
    try:
        result = subprocess.run(
            ["terraform", "version", "-json"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            tf_data = json.loads(result.stdout)
            tf_version = tf_data.get("terraform_version")
    except Exception:
        pass

    # Check LSP availability
    lsp_available = shutil.which("terraform-ls") is not None

    return {
        "version": "3.1.0",
        "transport": config.server.transport,
        "host": config.server.host,
        "port": config.server.port,
        "tool_count": 25,
        "uptime": f"{hours}h {minutes}m {seconds}s",
        "uptime_seconds": uptime_seconds,
        "healthy": True,
        "terraform_version": tf_version,
        "lsp_available": lsp_available,
        "github_configured": bool(config.github.app_id),
        "tf_cloud_configured": bool(config.terraform_cloud.token),
    }


def _get_tool_categories() -> list:
    """Return tool category summary."""
    return [
        {"name": "Core Terraform", "prefix": "terry_*", "count": 4},
        {"name": "LSP Intelligence", "prefix": "terraform_*", "count": 5},
        {"name": "Diagnostics", "prefix": "terry_lsp_*, terry_file_*", "count": 6},
        {"name": "Security & Recommendations", "prefix": "terry_security_*", "count": 2},
        {"name": "GitHub Integration", "prefix": "github_*", "count": 4},
        {"name": "Terraform Cloud", "prefix": "tf_cloud_*", "count": 4},
    ]


def _parse_cloud_credentials_form(form_data: dict) -> dict:
    """Parse the cloud credentials form into the nested structure expected by the schema."""
    provider = form_data.get("_provider", "aws")

    # Start with empty structure
    result: Dict[str, Any] = {"aws": {}, "gcp": {}, "azure": {}}

    if provider == "aws":
        result["aws"] = {
            "access_key_id": form_data.get("aws_access_key_id", ""),
            "secret_access_key": form_data.get("aws_secret_access_key", ""),
            "session_token": form_data.get("aws_session_token", ""),
            "region": form_data.get("aws_region", ""),
        }
    elif provider == "gcp":
        result["gcp"] = {
            "credentials_file": form_data.get("gcp_credentials_file", ""),
            "project": form_data.get("gcp_project", ""),
            "region": form_data.get("gcp_region", ""),
        }
    elif provider == "azure":
        result["azure"] = {
            "subscription_id": form_data.get("azure_subscription_id", ""),
            "tenant_id": form_data.get("azure_tenant_id", ""),
            "client_id": form_data.get("azure_client_id", ""),
            "client_secret": form_data.get("azure_client_secret", ""),
        }

    return result


def register_routes(mcp_server, config_mgr: ConfigManager, rate_limiter=None):
    """Register all frontend HTTP routes on the FastMCP server.

    Args:
        mcp_server: The FastMCP server instance
        config_mgr: ConfigManager instance for reading/writing config
        rate_limiter: RateLimiter instance for live rate limit updates
    """

    # ------------------------------------------------------------------
    # Static files
    # ------------------------------------------------------------------
    @mcp_server.custom_route("/static/{path:path}", methods=["GET"])
    async def static_files(request: Request) -> Response:
        file_path = _STATIC_DIR / request.path_params["path"]
        if not file_path.resolve().is_relative_to(_STATIC_DIR.resolve()):
            return Response("Forbidden", status_code=403)
        if not file_path.is_file():
            return Response("Not Found", status_code=404)

        content_types = {
            ".css": "text/css",
            ".js": "application/javascript",
            ".svg": "image/svg+xml",
            ".png": "image/png",
            ".ico": "image/x-icon",
        }
        ct = content_types.get(file_path.suffix, "application/octet-stream")
        return Response(
            file_path.read_bytes(),
            media_type=ct,
            headers={"Cache-Control": "public, max-age=3600"},
        )

    # ------------------------------------------------------------------
    # Dashboard
    # ------------------------------------------------------------------
    @mcp_server.custom_route("/", methods=["GET"])
    async def dashboard(request: Request) -> Response:
        auth_resp = _check_auth(request, config_mgr)
        if auth_resp:
            return auth_resp

        csrf_token = _generate_csrf_token()
        status = _get_server_status(config_mgr)
        html = _render(
            "dashboard.html",
            active_page="dashboard",
            version="3.1.0",
            csrf_token=csrf_token,
            status=status,
            tool_categories=_get_tool_categories(),
        )
        resp = _html(html)
        return _set_csrf_cookie(resp, csrf_token)

    # ------------------------------------------------------------------
    # Config page (full page load)
    # ------------------------------------------------------------------
    @mcp_server.custom_route("/config", methods=["GET"])
    async def config_page(request: Request) -> Response:
        auth_resp = _check_auth(request, config_mgr)
        if auth_resp:
            return auth_resp

        csrf_token = _generate_csrf_token()
        active_tab = request.query_params.get("tab", "server")
        if active_tab not in _TAB_TEMPLATES:
            active_tab = "server"

        # Render the active tab partial
        section_data = config_mgr.get_section_masked(active_tab)
        tab_html = _render(
            _TAB_TEMPLATES[active_tab],
            config=section_data,
        )

        html = _render(
            "config.html",
            active_page="config",
            version="3.1.0",
            csrf_token=csrf_token,
            tabs=CONFIG_TABS,
            active_tab=active_tab,
            tab_content=tab_html,
        )
        resp = _html(html)
        return _set_csrf_cookie(resp, csrf_token)

    # ------------------------------------------------------------------
    # Config section GET (HTMX partial)
    # ------------------------------------------------------------------
    @mcp_server.custom_route("/config/{section}", methods=["GET"])
    async def config_section_get(request: Request) -> Response:
        auth_resp = _check_auth(request, config_mgr)
        if auth_resp:
            return auth_resp

        section = request.path_params["section"]
        if section not in _TAB_TEMPLATES:
            return _html("<p class='text-red-400'>Unknown section</p>", 404)

        section_data = config_mgr.get_section_masked(section)
        html = _render(_TAB_TEMPLATES[section], config=section_data)
        return _html(html)

    # ------------------------------------------------------------------
    # Config section POST (save)
    # ------------------------------------------------------------------
    @mcp_server.custom_route("/config/{section}", methods=["POST"])
    async def config_section_post(request: Request) -> Response:
        auth_resp = _check_auth(request, config_mgr)
        if auth_resp:
            return auth_resp

        section = request.path_params["section"]
        if section not in _TAB_TEMPLATES:
            return _html("<p class='text-red-400'>Unknown section</p>", 404)

        # CSRF check
        csrf_token = request.headers.get("X-CSRF-Token", "")
        if not _verify_csrf_token(request, csrf_token):
            return _html("<p class='text-red-400'>CSRF validation failed</p>", 403)

        # Parse form data
        form = await request.form()
        form_data = dict(form)

        # Special handling for cloud credentials (nested form)
        if section == "cloud-credentials":
            form_data = _parse_cloud_credentials_form(form_data)

        # Convert numeric strings for rate limits
        if section == "rate-limits":
            for key in ("terraform", "github", "tf_cloud", "default"):
                if key in form_data:
                    try:
                        form_data[key] = int(form_data[key])
                    except (ValueError, TypeError):
                        pass

        # Convert port to int for server settings
        if section == "server" and "port" in form_data:
            try:
                form_data["port"] = int(form_data["port"])
            except (ValueError, TypeError):
                pass

        # Convert timeout to int for terraform options
        if section == "terraform-options" and "max_operation_timeout" in form_data:
            try:
                form_data["max_operation_timeout"] = int(form_data["max_operation_timeout"])
            except (ValueError, TypeError):
                pass

        try:
            config_mgr.update_section(section, form_data, rate_limiter=rate_limiter)
        except Exception as e:
            logger.error(f"Config update failed for {section}: {e}")
            section_data = config_mgr.get_section_masked(section)
            html = _render(_TAB_TEMPLATES[section], config=section_data)
            return _html(
                html,
                headers={
                    "HX-Trigger": json.dumps({
                        "show-toast": {"message": f"Error: {e}", "type": "error"}
                    })
                },
            )

        # Check if restart is required
        config_key = SECTION_TO_KEY.get(section, section)
        restart_needed = any(
            f"{config_key}.{k}" in RESTART_REQUIRED_FIELDS
            for k in form_data
            if not k.startswith("_")
        )

        section_data = config_mgr.get_section_masked(section)
        context = {"config": section_data}
        if restart_needed:
            context["restart_required"] = True

        html = _render(_TAB_TEMPLATES[section], **context)

        toast_msg = "Settings saved successfully"
        if restart_needed:
            toast_msg += " (restart required for some changes)"

        return _html(
            html,
            headers={
                "HX-Trigger": json.dumps({
                    "show-toast": {"message": toast_msg, "type": "success"}
                })
            },
        )

    # ------------------------------------------------------------------
    # API: Health / Status JSON
    # ------------------------------------------------------------------
    @mcp_server.custom_route("/api/status", methods=["GET"])
    async def api_status(request: Request) -> Response:
        status = _get_server_status(config_mgr)
        return JSONResponse({"status": "ok", **status})

    # ------------------------------------------------------------------
    # API: Status badge (HTMX partial)
    # ------------------------------------------------------------------
    @mcp_server.custom_route("/api/status/badge", methods=["GET"])
    async def api_status_badge(request: Request) -> Response:
        status = _get_server_status(config_mgr)
        if status["healthy"]:
            html = '<span class="inline-flex items-center space-x-1"><span class="h-1.5 w-1.5 rounded-full bg-green-500"></span><span class="text-green-400">Healthy</span></span>'
        else:
            html = '<span class="inline-flex items-center space-x-1"><span class="h-1.5 w-1.5 rounded-full bg-red-500"></span><span class="text-red-400">Degraded</span></span>'
        return _html(html)

    # ------------------------------------------------------------------
    # API: Status panel (HTMX partial, polled every 5s)
    # ------------------------------------------------------------------
    @mcp_server.custom_route("/api/status/panel", methods=["GET"])
    async def api_status_panel(request: Request) -> Response:
        status = _get_server_status(config_mgr)
        html = _render("partials/_status_panel.html", status=status)
        return _html(html)

    # ------------------------------------------------------------------
    # Test connections
    # ------------------------------------------------------------------
    @mcp_server.custom_route("/config/github/test", methods=["POST"])
    async def test_github(request: Request) -> Response:
        auth_resp = _check_auth(request, config_mgr)
        if auth_resp:
            return auth_resp

        config = config_mgr.config.github
        if not config.app_id:
            return _html(
                '<div class="mt-2 text-sm text-yellow-400">GitHub App ID not configured</div>'
            )

        try:
            from github_app_auth import GitHubAppConfig, GitHubAppAuth

            gh_config = GitHubAppConfig.from_env()
            auth = GitHubAppAuth(gh_config)
            installations = auth.list_installations()
            return _html(
                f'<div class="mt-2 text-sm text-green-400">Connected. Found {len(installations)} installation(s).</div>'
            )
        except Exception as e:
            return _html(
                f'<div class="mt-2 text-sm text-red-400">Connection failed: {e}</div>'
            )

    @mcp_server.custom_route("/config/terraform-cloud/test", methods=["POST"])
    async def test_tf_cloud(request: Request) -> Response:
        auth_resp = _check_auth(request, config_mgr)
        if auth_resp:
            return auth_resp

        token = os.environ.get("TF_API_TOKEN")
        if not token:
            return _html(
                '<div class="mt-2 text-sm text-yellow-400">Terraform Cloud token not configured</div>'
            )

        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://app.terraform.io/api/v2/account/details",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/vnd.api+json",
                    },
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        username = data.get("data", {}).get("attributes", {}).get("username", "unknown")
                        return _html(
                            f'<div class="mt-2 text-sm text-green-400">Connected as {username}</div>'
                        )
                    else:
                        return _html(
                            f'<div class="mt-2 text-sm text-red-400">API returned HTTP {resp.status}</div>'
                        )
        except Exception as e:
            return _html(
                f'<div class="mt-2 text-sm text-red-400">Connection failed: {e}</div>'
            )

    # ------------------------------------------------------------------
    # Login page (only used when TERRY_FORM_API_KEY is set)
    # ------------------------------------------------------------------
    @mcp_server.custom_route("/login", methods=["GET", "POST"])
    async def login(request: Request) -> Response:
        api_key = config_mgr.config.server.api_key
        if not api_key:
            # No auth needed, redirect to dashboard
            return Response("", status_code=302, headers={"Location": "/"})

        if request.method == "GET":
            csrf_token = _generate_csrf_token()
            html = _render("login.html", csrf_token=csrf_token, error="")
            resp = _html(html)
            return _set_csrf_cookie(resp, csrf_token)

        # POST — validate credentials
        form = await request.form()
        submitted_key = form.get("api_key", "")

        if hmac.compare_digest(str(submitted_key), api_key):
            # Create session
            session_token = hashlib.sha256(
                f"{api_key}:{_CSRF_SECRET}".encode()
            ).hexdigest()
            resp = Response("", status_code=302, headers={"Location": "/"})
            resp.set_cookie(
                "terry_session",
                session_token,
                httponly=True,
                samesite="strict",
                max_age=86400,
            )
            return resp

        csrf_token = _generate_csrf_token()
        html = _render("login.html", csrf_token=csrf_token, error="Invalid API key")
        resp = _html(html, status_code=401)
        return _set_csrf_cookie(resp, csrf_token)

    logger.info("Frontend routes registered")
