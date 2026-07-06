import os
import logging
from typing import Optional
from fastmcp import FastMCP
import httpx
from dotenv import load_dotenv
from fastmcp.server.auth.providers.keycloak import KeycloakAuthProvider
from fastmcp.server.dependencies import get_access_token

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("ittwist-mcp")

# Keycloak + FastMCP configuration
# Requires Keycloak 26.6.0+ with Dynamic Client Registration (DCR) enabled on the realm
KEYCLOAK_REALM_URL = os.getenv("KEYCLOAK_REALM_URL", "http://localhost:8080/realms/master")
FASTMCP_BASE_URL = os.getenv("FASTMCP_BASE_URL", "http://localhost:3000")

# Optional: restrict required OAuth scopes
REQUIRED_SCOPES: list[str] = [s for s in os.getenv("REQUIRED_SCOPES", "").split(",") if s]

# Optional: audience for production — tokens must be intended for this server.
# Set OIDC_AUDIENCE in .env (e.g. to FASTMCP_BASE_URL) to harden production.
OIDC_AUDIENCE: Optional[str] = os.getenv("OIDC_AUDIENCE") or None

# ---------------------------------------------------------------------------
# Auth: RemoteAuthProvider backed by Keycloak with native DCR support.
# MCP clients self-register via RFC 7591 Dynamic Client Registration —
# no upstream_client_id / upstream_client_secret needed anymore.
# ---------------------------------------------------------------------------
auth_provider = KeycloakAuthProvider(
    realm_url=KEYCLOAK_REALM_URL,
    base_url=FASTMCP_BASE_URL,
    # audience=OIDC_AUDIENCE,  # Uncomment and set OIDC_AUDIENCE for production
    required_scopes=REQUIRED_SCOPES if REQUIRED_SCOPES else None,
)

# ---------------------------------------------------------------------------
# FastMCP server
# ---------------------------------------------------------------------------
mcp = FastMCP("ittwist-mcp", auth=auth_provider)


@mcp.tool()
def add_numbers(a: float, b: float) -> float:
    """
    Adds two numbers together.

    Args:
        a: The first number.
        b: The second number.
    """
    return a + b


@mcp.tool()
async def whoami() -> dict:
    """
    Returns basic claims from the authenticated user's Keycloak JWT.
    Useful for verifying that DCR + token validation is working end-to-end.
    """
    token = get_access_token()
    if token is None:
        return {"error": "Not authenticated"}
    return {
        "sub": token.claims.get("sub"),
        "preferred_username": token.claims.get("preferred_username"),
        "scope": token.claims.get("scope"),
        "azp": token.claims.get("azp"),  # Authorized party (the DCR client_id)
        "realm_roles": token.claims.get("realm_access", {}).get("roles", []),
    }


def main():
    logger.info("Starting ittwist-mcp with Keycloak DCR (RemoteAuthProvider)...")
    logger.info(f"  Realm URL : {KEYCLOAK_REALM_URL}")
    logger.info(f"  Base URL  : {FASTMCP_BASE_URL}")
    logger.info(f"  Scopes    : {REQUIRED_SCOPES or 'any'}")
    logger.info(f"  Audience  : {OIDC_AUDIENCE or 'not enforced (set OIDC_AUDIENCE for production)'}")

    mcp.run(transport="http", host="0.0.0.0", port=3000, path="/")


if __name__ == "__main__":
    main()
