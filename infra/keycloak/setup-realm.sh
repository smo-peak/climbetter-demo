#!/bin/bash
# =============================================================
# ClimBetter — Keycloak Realm Setup (idempotent)
# Execute: ssh climbetter 'bash /opt/climbetter/infra/keycloak/setup-realm.sh'
# =============================================================
set -euo pipefail

KC_URL="https://auth.climbetter.com"
REALM="climbetter"

# Load credentials from .env
source /opt/climbetter/infra/.env

echo "=== 1/7 — Obtain admin token ==="
TOKEN_RESPONSE=$(curl -sk -X POST "${KC_URL}/realms/master/protocol/openid-connect/token" \
  --data-urlencode "client_id=admin-cli" \
  --data-urlencode "username=${KEYCLOAK_ADMIN}" \
  --data-urlencode "password=${KEYCLOAK_ADMIN_PASSWORD}" \
  --data-urlencode "grant_type=password")
TOKEN=$(echo "${TOKEN_RESPONSE}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('access_token','FAILED: '+str(d)))")
echo "Token obtained (${#TOKEN} chars)"

# Helper: authenticated curl
kc() {
  curl -sk -H "Authorization: Bearer ${TOKEN}" -H "Content-Type: application/json" "$@"
}

echo ""
echo "=== 2/7 — Create realm '${REALM}' ==="
EXISTS=$(kc "${KC_URL}/admin/realms/${REALM}" -o /dev/null -w "%{http_code}")
if [ "$EXISTS" = "200" ]; then
  echo "Realm already exists — skipping"
else
  kc -X POST "${KC_URL}/admin/realms" -d '{
    "realm": "'"${REALM}"'",
    "displayName": "ClimBetter",
    "enabled": true,
    "registrationAllowed": false,
    "loginWithEmailAllowed": true,
    "internationalizationEnabled": true,
    "supportedLocales": ["fr", "en"],
    "defaultLocale": "fr"
  }'
  echo "Realm created"
fi

echo ""
echo "=== 3/7 — Create client 'mobile-app' (public, PKCE) ==="
MOBILE_EXISTS=$(kc "${KC_URL}/admin/realms/${REALM}/clients?clientId=mobile-app" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d))")
if [ "$MOBILE_EXISTS" != "0" ]; then
  echo "Client mobile-app already exists — skipping"
else
  kc -X POST "${KC_URL}/admin/realms/${REALM}/clients" -d '{
    "clientId": "mobile-app",
    "name": "ClimBetter Mobile App",
    "publicClient": true,
    "standardFlowEnabled": true,
    "directAccessGrantsEnabled": true,
    "redirectUris": ["climbetter://*", "https://app.climbetter.com/*"],
    "webOrigins": ["+"],
    "attributes": {
      "pkce.code.challenge.method": "S256"
    }
  }'
  echo "Client mobile-app created"
fi

echo ""
echo "=== 4/7 — Create client 'api-backend' (confidential, service account) ==="
API_EXISTS=$(kc "${KC_URL}/admin/realms/${REALM}/clients?clientId=api-backend" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d))")
if [ "$API_EXISTS" != "0" ]; then
  echo "Client api-backend already exists — skipping"
else
  kc -X POST "${KC_URL}/admin/realms/${REALM}/clients" -d '{
    "clientId": "api-backend",
    "name": "ClimBetter API Backend",
    "publicClient": false,
    "standardFlowEnabled": false,
    "serviceAccountsEnabled": true,
    "directAccessGrantsEnabled": false
  }'
  echo "Client api-backend created"

  # Retrieve generated secret
  API_ID=$(kc "${KC_URL}/admin/realms/${REALM}/clients?clientId=api-backend" | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['id'])")
  SECRET=$(kc "${KC_URL}/admin/realms/${REALM}/clients/${API_ID}/client-secret" | python3 -c "import sys,json; print(json.load(sys.stdin)['value'])")
  echo "Client secret: ${SECRET}"
  echo ">> Save this secret in your .env as API_BACKEND_SECRET"
fi

echo ""
echo "=== 5/7 — Create realm roles ==="
for ROLE in climber-free climber-premium climber-elite coach gym-admin; do
  ROLE_EXISTS=$(kc "${KC_URL}/admin/realms/${REALM}/roles/${ROLE}" -o /dev/null -w "%{http_code}")
  if [ "$ROLE_EXISTS" = "200" ]; then
    echo "  Role '${ROLE}' already exists — skipping"
  else
    kc -X POST "${KC_URL}/admin/realms/${REALM}/roles" -d '{
      "name": "'"${ROLE}"'",
      "description": "ClimBetter role: '"${ROLE}"'"
    }'
    echo "  Role '${ROLE}' created"
  fi
done

echo ""
echo "=== 6/7 — Create user 'stephane' (climber-elite) ==="
STEPH_EXISTS=$(kc "${KC_URL}/admin/realms/${REALM}/users?username=stephane&exact=true" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d))")
if [ "$STEPH_EXISTS" != "0" ]; then
  echo "User stephane already exists — skipping"
else
  # Create user
  kc -X POST "${KC_URL}/admin/realms/${REALM}/users" -d '{
    "username": "stephane",
    "email": "stephane@climbetter.com",
    "emailVerified": true,
    "enabled": true,
    "firstName": "Stéphane",
    "credentials": [{
      "type": "password",
      "value": "Change1t!",
      "temporary": true
    }]
  }'
  echo "User stephane created"

  # Assign role
  STEPH_ID=$(kc "${KC_URL}/admin/realms/${REALM}/users?username=stephane&exact=true" | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['id'])")
  ROLE_REP=$(kc "${KC_URL}/admin/realms/${REALM}/roles/climber-elite")
  kc -X POST "${KC_URL}/admin/realms/${REALM}/users/${STEPH_ID}/role-mappings/realm" -d "[${ROLE_REP}]"
  echo "  Role climber-elite assigned to stephane"
fi

echo ""
echo "=== 7/7 — Create user 'jacopo' (coach) ==="
JACOPO_EXISTS=$(kc "${KC_URL}/admin/realms/${REALM}/users?username=jacopo&exact=true" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d))")
if [ "$JACOPO_EXISTS" != "0" ]; then
  echo "User jacopo already exists — skipping"
else
  # Create user
  kc -X POST "${KC_URL}/admin/realms/${REALM}/users" -d '{
    "username": "jacopo",
    "email": "jacopo@climbetter.com",
    "emailVerified": true,
    "enabled": true,
    "firstName": "Jacopo",
    "credentials": [{
      "type": "password",
      "value": "Change1t!",
      "temporary": true
    }]
  }'
  echo "User jacopo created"

  # Assign role
  JACOPO_ID=$(kc "${KC_URL}/admin/realms/${REALM}/users?username=jacopo&exact=true" | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['id'])")
  ROLE_REP=$(kc "${KC_URL}/admin/realms/${REALM}/roles/coach")
  kc -X POST "${KC_URL}/admin/realms/${REALM}/users/${JACOPO_ID}/role-mappings/realm" -d "[${ROLE_REP}]"
  echo "  Role coach assigned to jacopo"
fi

echo ""
echo "=== SETUP COMPLETE ==="
