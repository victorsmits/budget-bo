import { NextResponse } from "next/server"

export async function GET() {
  const appUrl = process.env.NEXT_PUBLIC_APP_URL || "http://localhost:3000"
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

  return NextResponse.json(
    {
      issuer: appUrl,
      authorization_endpoint: `${appUrl}/mcp/consent`,
      token_endpoint: `${apiUrl}/mcp/oauth/token`,
      registration_endpoint: `${apiUrl}/mcp/oauth/register`,
      revocation_endpoint: `${apiUrl}/mcp/oauth/revoke`,
      response_types_supported: ["code"],
      grant_types_supported: ["authorization_code"],
      code_challenge_methods_supported: ["S256"],
      token_endpoint_auth_methods_supported: ["none"],
    },
    {
      headers: {
        "Access-Control-Allow-Origin": "*",
        "Cache-Control": "public, max-age=3600",
      },
    }
  )
}
