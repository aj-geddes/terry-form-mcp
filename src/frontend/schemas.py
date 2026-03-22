"""Pydantic validation models for each configuration section."""

from pydantic import BaseModel, Field, field_validator


class ServerSettings(BaseModel):
    transport: str = Field(default="streamable-http", pattern=r"^(stdio|sse|streamable-http)$")
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000, ge=1, le=65535)
    api_key: str | None = Field(default=None)

    @field_validator("host")
    @classmethod
    def validate_host(cls, v: str) -> str:
        # Allow IP addresses and hostnames
        if not v or len(v) > 253:
            raise ValueError("Invalid host")
        return v


class GitHubSettings(BaseModel):
    app_id: str | None = Field(default=None)
    private_key_path: str | None = Field(default=None)
    installation_id: str | None = Field(default=None)
    webhook_secret: str | None = Field(default=None)


class TerraformCloudSettings(BaseModel):
    token: str | None = Field(default=None)


class AWSCredentials(BaseModel):
    access_key_id: str | None = Field(default=None)
    secret_access_key: str | None = Field(default=None)
    session_token: str | None = Field(default=None)
    region: str | None = Field(default=None)


class GCPCredentials(BaseModel):
    credentials_file: str | None = Field(default=None)
    project: str | None = Field(default=None)
    region: str | None = Field(default=None)


class AzureCredentials(BaseModel):
    subscription_id: str | None = Field(default=None)
    tenant_id: str | None = Field(default=None)
    client_id: str | None = Field(default=None)
    client_secret: str | None = Field(default=None)


class CloudCredentials(BaseModel):
    aws: AWSCredentials = Field(default_factory=AWSCredentials)
    gcp: GCPCredentials = Field(default_factory=GCPCredentials)
    azure: AzureCredentials = Field(default_factory=AzureCredentials)


class RateLimits(BaseModel):
    terraform: int = Field(default=20, ge=1, le=1000)
    github: int = Field(default=30, ge=1, le=1000)
    tf_cloud: int = Field(default=30, ge=1, le=1000)
    default: int = Field(default=100, ge=1, le=1000)


class TerraformOptions(BaseModel):
    tf_log: str = Field(default="", pattern=r"^(|TRACE|DEBUG|INFO|WARN|ERROR)$")
    max_operation_timeout: int = Field(default=300, ge=10, le=3600)


class ServerInternalConfig(BaseModel):
    """Server-internal state that is not user-configurable.

    Stored in the config file for persistence across restarts but never
    exposed in the UI or treated as a user credential.
    """

    csrf_secret: str | None = Field(default=None)


class TerryConfig(BaseModel):
    """Root configuration model."""
    server: ServerSettings = Field(default_factory=ServerSettings)
    github: GitHubSettings = Field(default_factory=GitHubSettings)
    terraform_cloud: TerraformCloudSettings = Field(default_factory=TerraformCloudSettings)
    cloud_credentials: CloudCredentials = Field(default_factory=CloudCredentials)
    rate_limits: RateLimits = Field(default_factory=RateLimits)
    terraform_options: TerraformOptions = Field(default_factory=TerraformOptions)
    server_internal: ServerInternalConfig = Field(default_factory=ServerInternalConfig)


# Map section names to their model classes
SECTION_MODELS = {
    "server": ServerSettings,
    "github": GitHubSettings,
    "terraform-cloud": TerraformCloudSettings,
    "cloud-credentials": CloudCredentials,
    "rate-limits": RateLimits,
    "terraform-options": TerraformOptions,
}

# Map URL section names to config keys
SECTION_TO_KEY = {
    "server": "server",
    "github": "github",
    "terraform-cloud": "terraform_cloud",
    "cloud-credentials": "cloud_credentials",
    "rate-limits": "rate_limits",
    "terraform-options": "terraform_options",
}

# Fields that require a server restart to take effect
RESTART_REQUIRED_FIELDS = {"server.transport", "server.host", "server.port"}

# Sensitive fields that should be masked in the UI
SENSITIVE_FIELDS = {
    "server.api_key",
    "github.webhook_secret",
    "terraform_cloud.token",
    "cloud_credentials.aws.secret_access_key",
    "cloud_credentials.aws.session_token",
    "cloud_credentials.azure.client_secret",
}
