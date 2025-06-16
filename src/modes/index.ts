import { SERVER_MODE, MODES, type ServerMode } from "../../config.js";

export interface ModeConfig {
  mode: ServerMode;
  features: {
    terraformCloud: boolean;
    webUI: boolean;
    mcpBridge: boolean;
  };
  displayName: string;
  description: string;
}

export function getModeConfig(): ModeConfig {
  switch (SERVER_MODE) {
    case MODES.ENTERPRISE:
      return {
        mode: MODES.ENTERPRISE,
        features: {
          terraformCloud: true,
          webUI: true,
          mcpBridge: true
        },
        displayName: "Enterprise Mode",
        description: "Full-featured deployment with Terraform Cloud integration, Web UI, and MCP Bridge"
      };
    case MODES.LOCAL:
    default:
      return {
        mode: MODES.LOCAL,
        features: {
          terraformCloud: false,
          webUI: true, // Simple status UI even in local mode
          mcpBridge: false
        },
        displayName: "Local Mode",
        description: "Lightweight Terraform Registry access for individual developers"
      };
  }
}

export function isEnterpriseMode(): boolean {
  return SERVER_MODE === MODES.ENTERPRISE;
}

export function isLocalMode(): boolean {
  return SERVER_MODE === MODES.LOCAL;
}

export function shouldEnableTerraformCloud(): boolean {
  return getModeConfig().features.terraformCloud;
}