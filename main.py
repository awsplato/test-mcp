import os
import logging
from typing import Optional, Dict, Any
from fastmcp import FastMCP
import httpx
from pydantic import BaseModel
from dotenv import load_dotenv
from fastmcp.server.auth import OAuthProxy
from fastmcp.server.auth.providers.jwt import JWTVerifier
from fastmcp.server.dependencies import get_access_token

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("ittwist-mcp")

# Enterprise OIDC settings
OIDC_CLIENT_ID = os.getenv("OIDC_CLIENT_ID")
OIDC_CLIENT_SECRET = os.getenv("OIDC_CLIENT_SECRET")
# For Keycloak, this looks like: https://<domain>/realms/<realm>/protocol/openid-connect/token
OIDC_TOKEN_URL = os.getenv("OIDC_TOKEN_URL", "http://localhost:8080/realms/master/protocol/openid-connect/token")

# Keycloak OAuthProxy Configuration (No DCR required)
KEYCLOAK_REALM_URL = os.getenv("KEYCLOAK_REALM_URL", "http://localhost:8080/realms/master")
FASTMCP_BASE_URL = os.getenv("FASTMCP_BASE_URL", "http://localhost:3000")

jwt_verifier = JWTVerifier(
    jwks_uri=f"{KEYCLOAK_REALM_URL}/protocol/openid-connect/certs",
    # Set audience if your tokens are issued with a specific audience
    audience=os.getenv("OIDC_AUDIENCE")
)

auth_provider = OAuthProxy(
    upstream_authorization_endpoint=f"{KEYCLOAK_REALM_URL}/protocol/openid-connect/auth",
    upstream_token_endpoint=f"{KEYCLOAK_REALM_URL}/protocol/openid-connect/token",
    upstream_client_id=OIDC_CLIENT_ID or "",
    upstream_client_secret=OIDC_CLIENT_SECRET,
    base_url=FASTMCP_BASE_URL,
    token_verifier=jwt_verifier
)

class OIDCClient:
    """Enterprise OIDC Client for fetching OAuth tokens via Client Credentials flow."""
    def __init__(self, client_id: str, client_secret: str, token_url: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_url = token_url
        self._token: Optional[str] = None
    
    async def get_token(self) -> str:
        """Fetch or return a cached OIDC token."""
        # In a real enterprise app, you'd cache the token and check expiration
        if self._token:
            return self._token
            
        if not self.client_id or not self.client_secret:
            logger.warning("OIDC credentials not fully configured.")
            return ""
            
        async with httpx.AsyncClient() as client:
            try:
                logger.info(f"Fetching OIDC token from {self.token_url}")
                # Keycloak and compliant OIDC providers prefer Basic Auth for client credentials
                response = await client.post(
                    self.token_url,
                    auth=(self.client_id, self.client_secret),
                    data={
                        "grant_type": "client_credentials"
                    }
                )
                response.raise_for_status()
                data = response.json()
                self._token = data.get("access_token", "")
                return self._token
            except Exception as e:
                logger.error(f"Failed to fetch OIDC token: {e}")
                raise

# Initialize OIDC client singleton
oidc_client = OIDCClient(
    client_id=OIDC_CLIENT_ID or "",
    client_secret=OIDC_CLIENT_SECRET or "",
    token_url=OIDC_TOKEN_URL
)

# Initialize Enterprise FastMCP Server with Native Authentication
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

def main():
    logger.info("Starting Enterprise FastMCP Server with OIDC support...")
    if not OIDC_CLIENT_ID or not OIDC_CLIENT_SECRET:
        logger.warning("OIDC_CLIENT_ID and/or OIDC_CLIENT_SECRET are missing. Secure endpoints may fail.")
    
    mcp.run(transport="http", host="0.0.0.0", port=3000)

if __name__ == "__main__":
    main()
