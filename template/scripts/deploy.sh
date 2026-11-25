#!/usr/bin/env bash
# Deployment contract used by .github/workflows/deploy.yml:
#   scripts/deploy.sh deploy    -> roll out $IMAGE to $ENVIRONMENT and wait until it is rolled out
#   scripts/deploy.sh rollback  -> revert $ENVIRONMENT to the previous release
# Default implementation: Kubernetes (Deployment "app" in namespace $ENVIRONMENT).
# Replace the two functions for ECS, Cloud Run, Fly.io, etc. Keep the contract.
set -euo pipefail

: "${ENVIRONMENT:?ENVIRONMENT is required}"
DEPLOYMENT="${DEPLOYMENT:-app}"

if [[ -n "${KUBECONFIG_DATA:-}" ]]; then
  export KUBECONFIG="${RUNNER_TEMP:-/tmp}/kubeconfig"
  printf '%s' "$KUBECONFIG_DATA" | base64 --decode > "$KUBECONFIG"
  chmod 600 "$KUBECONFIG"
fi

deploy() {
  : "${IMAGE:?IMAGE is required}"
  kubectl -n "$ENVIRONMENT" set image "deployment/$DEPLOYMENT" "app=$IMAGE"
  kubectl -n "$ENVIRONMENT" rollout status "deployment/$DEPLOYMENT" --timeout=5m
}

rollback() {
  kubectl -n "$ENVIRONMENT" rollout undo "deployment/$DEPLOYMENT"
  kubectl -n "$ENVIRONMENT" rollout status "deployment/$DEPLOYMENT" --timeout=5m
}

case "${1:-}" in
  deploy) deploy ;;
  rollback) rollback ;;
  *) echo "usage: $0 deploy|rollback" >&2; exit 2 ;;
esac
