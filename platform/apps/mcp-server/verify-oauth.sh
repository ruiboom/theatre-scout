#!/usr/bin/env bash
#
# Verify the MCP server's OAuth contract end-to-end at the HTTP level.
#
# Checks exactly what Claude / ChatGPT probe when adding a connector:
#   - public routes stay open (health, info, openapi redirect)
#   - RFC 8414 authorization-server metadata is served and well-formed
#   - RFC 9728 protected-resource metadata is served and well-formed
#   - an unauthenticated /mcp call is rejected 401 with a WWW-Authenticate
#     header pointing at the protected-resource metadata (this is the signal
#     that kicks the client into the OAuth flow)
#
# Usage:
#   ./verify-oauth.sh                       # default: live workers.dev URL
#   ./verify-oauth.sh http://localhost:8787 # against `wrangler dev`
#
# Exit code is non-zero if any check fails — safe to wire into CI later.

set -u

BASE="${1:-https://platform-mcp-server.boomclick.workers.dev}"
BASE="${BASE%/}"

pass=0
fail=0

ok()   { printf '  \033[32mPASS\033[0m  %s\n' "$1"; pass=$((pass + 1)); }
bad()  { printf '  \033[31mFAIL\033[0m  %s\n' "$1"; fail=$((fail + 1)); }

echo "Verifying MCP OAuth contract at: $BASE"
echo

# --- 1. public routes must remain unauthenticated ---------------------------
echo "Public routes (must NOT require auth):"

code=$(curl -fsS -o /dev/null -w '%{http_code}' "$BASE/health" 2>/dev/null)
[ "$code" = "200" ] && ok "/health -> 200" || bad "/health -> $code (expected 200)"

code=$(curl -fsS -o /dev/null -w '%{http_code}' "$BASE/" 2>/dev/null)
[ "$code" = "200" ] && ok "/ -> 200" || bad "/ -> $code (expected 200)"

code=$(curl -sS -o /dev/null -w '%{http_code}' "$BASE/openapi.json" 2>/dev/null)
[ "$code" = "302" ] || [ "$code" = "200" ] \
  && ok "/openapi.json -> $code (redirect/ok)" \
  || bad "/openapi.json -> $code (expected 302 or 200)"

echo

# --- 2. RFC 8414: authorization server metadata -----------------------------
echo "Discovery metadata:"

as_json=$(curl -fsS "$BASE/.well-known/oauth-authorization-server" 2>/dev/null)
if [ -n "$as_json" ]; then
  ok "/.well-known/oauth-authorization-server -> 200"
  for field in issuer authorization_endpoint token_endpoint registration_endpoint; do
    echo "$as_json" | grep -q "\"$field\"" \
      && ok "  AS metadata has \"$field\"" \
      || bad "  AS metadata MISSING \"$field\""
  done
  echo "$as_json" | grep -q '"code_challenge_methods_supported"' \
    && ok "  AS metadata advertises PKCE (code_challenge_methods_supported)" \
    || bad "  AS metadata MISSING code_challenge_methods_supported (PKCE)"
else
  bad "/.well-known/oauth-authorization-server unreachable or empty"
fi

# --- 3. RFC 9728: protected resource metadata -------------------------------
pr_json=$(curl -fsS "$BASE/.well-known/oauth-protected-resource" 2>/dev/null)
if [ -n "$pr_json" ]; then
  ok "/.well-known/oauth-protected-resource -> 200"
  echo "$pr_json" | grep -q '"authorization_servers"' \
    && ok "  PR metadata has \"authorization_servers\"" \
    || bad "  PR metadata MISSING \"authorization_servers\""
else
  bad "/.well-known/oauth-protected-resource unreachable or empty"
fi

echo

# --- 4. /mcp must be protected: 401 + WWW-Authenticate ----------------------
echo "Protected MCP endpoint (unauthenticated request):"

hdrs=$(curl -sS -D - -o /dev/null -X POST "$BASE/mcp" \
  -H 'content-type: application/json' \
  -H 'accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' 2>/dev/null)

status=$(printf '%s' "$hdrs" | head -1 | tr -d '\r')
echo "$status" | grep -q ' 401' \
  && ok "/mcp unauthenticated -> 401 ($status)" \
  || bad "/mcp unauthenticated -> not 401 ($status) — endpoint may be OPEN"

wwwauth=$(printf '%s' "$hdrs" | grep -i '^www-authenticate:' | tr -d '\r')
if [ -n "$wwwauth" ]; then
  ok "  WWW-Authenticate present"
  echo "$wwwauth" | grep -qi 'resource_metadata' \
    && ok "  WWW-Authenticate points at resource_metadata (client can discover)" \
    || bad "  WWW-Authenticate present but no resource_metadata param"
else
  bad "  WWW-Authenticate header MISSING — clients won't know how to auth"
fi

echo
echo "-----------------------------------------------------------"
echo "  $pass passed, $fail failed"
echo "-----------------------------------------------------------"
[ "$fail" -eq 0 ] || exit 1
