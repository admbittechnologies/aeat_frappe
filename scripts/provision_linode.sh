#!/usr/bin/env bash
# Copyright (c) 2026, BIT Technologies GmbH and contributors
# License: AGPL-3.0-or-later
#
# Drives the whole live certification on a fresh Linode:
#   create VM -> wait for SSH -> copy app + bootstrap -> install ERPNext + app
#   -> run offline regression + live check -> (optional) destroy VM.
#
# YOU run this from a machine that can reach api.linode.com and the VM (the
# sandbox that built the app cannot). Requirements on your machine:
#   - linode-cli installed and configured  (pip install linode-cli; linode-cli configure)
#     or export LINODE_CLI_TOKEN=...
#   - an SSH keypair (default ~/.ssh/id_rsa[.pub])
#   - the app zip (erpnext_es_aeat.zip)
#
# Usage:
#   ./provision_linode.sh /path/to/erpnext_es_aeat.zip [--destroy]
set -euo pipefail

APP_ZIP="${1:?Falta la ruta al zip de la app}"
DESTROY="${2:-}"

REGION="${REGION:-eu-central}"          # Frankfurt
TYPE="${TYPE:-g6-standard-4}"            # 8 GB RAM (build de assets es hambriento)
IMAGE="${IMAGE:-linode/ubuntu22.04}"
LABEL="${LABEL:-aeat-cert-$(date +%s)}"
SSH_PUB="${SSH_PUB:-$HOME/.ssh/id_rsa.pub}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/id_rsa}"
ROOT_PW="Aeat-$(openssl rand -hex 12)"
HERE="$(cd "$(dirname "$0")" && pwd)"

command -v linode-cli >/dev/null || { echo "Instala linode-cli: pip install linode-cli"; exit 1; }
[ -f "$SSH_PUB" ] || { echo "No existe la clave pública SSH: $SSH_PUB"; exit 1; }

echo "==> Creando Linode ${LABEL} (${TYPE}, ${REGION}, ${IMAGE})"
LINODE_ID=$(linode-cli linodes create \
  --label "$LABEL" --region "$REGION" --type "$TYPE" --image "$IMAGE" \
  --root_pass "$ROOT_PW" --authorized_keys "$(cat "$SSH_PUB")" \
  --text --no-headers --format id)
echo "    id=${LINODE_ID}"

cleanup() {
  if [ "$DESTROY" = "--destroy" ]; then
    echo "==> Destruyendo Linode ${LINODE_ID}"
    linode-cli linodes delete "$LINODE_ID" || true
  else
    echo "==> VM conservada (id=${LINODE_ID}). Bórrala con: linode-cli linodes delete ${LINODE_ID}"
  fi
}
trap cleanup EXIT

echo "==> Esperando IP y arranque"
IP=""
for _ in $(seq 1 30); do
  IP=$(linode-cli linodes view "$LINODE_ID" --text --no-headers --format ipv4 | awk '{print $1}')
  [ -n "$IP" ] && break
  sleep 5
done
echo "    ip=${IP}"

echo "==> Esperando SSH"
for _ in $(seq 1 60); do
  if ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -i "$SSH_KEY" "root@${IP}" true 2>/dev/null; then
    break
  fi
  sleep 5
done

echo "==> Copiando app + bootstrap"
SSH_OPTS="-o StrictHostKeyChecking=no -i ${SSH_KEY}"
scp $SSH_OPTS "$APP_ZIP" "root@${IP}:/root/erpnext_es_aeat.zip"
scp $SSH_OPTS "${HERE}/remote_bootstrap.sh" "root@${IP}:/root/remote_bootstrap.sh"

echo "==> Ejecutando bootstrap (esto tarda; ERPNext + assets)"
set +e
ssh $SSH_OPTS "root@${IP}" "chmod +x /root/remote_bootstrap.sh && /root/remote_bootstrap.sh /root/erpnext_es_aeat.zip aeat.test" \
  | tee /tmp/aeat_bootstrap.log
RC=${PIPESTATUS[0]}
set -e

echo "========================================================"
if grep -q "BOOTSTRAP_OK" /tmp/aeat_bootstrap.log && [ "$RC" -eq 0 ]; then
  echo " CERTIFICACIÓN LIVE: OK"
else
  echo " CERTIFICACIÓN LIVE: revisar log (/tmp/aeat_bootstrap.log)"
fi
echo "========================================================"
exit "$RC"
