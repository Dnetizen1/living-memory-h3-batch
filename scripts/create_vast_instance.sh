#!/usr/bin/env bash
# Usage: ./scripts/create_vast_instance.sh <OFFER_ID> <GITHUB_USER/REPOSITORY> [branch]
set -euo pipefail
if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <OFFER_ID> <GITHUB_USER/REPOSITORY> [branch]" >&2
  exit 2
fi
OFFER_ID="$1"
GITHUB_REPOSITORY="$2"
BRANCH="${3:-main}"
BATCH_URL="https://raw.githubusercontent.com/${GITHUB_REPOSITORY}/${BRANCH}/workflows/video_minimax_h3_i2v_batch.json"
# A completed GitHub Actions run must publish BATCH_URL before launch.
if ! curl -fsSI --max-time 20 "$BATCH_URL" >/dev/null; then
  echo "Not found: $BATCH_URL" >&2
  echo "Push the repository, wait for GitHub Actions to publish the JSON, then retry." >&2
  exit 1
fi
ONSTART=$(cat <<EOF
export PROVISIONING_COMFYUI_WORKFLOWS="${BATCH_URL};https://raw.githubusercontent.com/Comfy-Org/workflow_templates/refs/heads/main/templates/video_minimax_h3_r2v.json;https://raw.githubusercontent.com/Comfy-Org/workflow_templates/refs/heads/main/templates/video_minimax_h3_t2v.json"
export PROVISIONING_GIT_REPOS="https://github.com/aiai-r/ComfyUI-FolderBatch|/workspace/ComfyUI/custom_nodes/ComfyUI-FolderBatch"
entrypoint.sh
EOF
)
# Keeps the source CLI's ports, image, HTTP proxy and instance flags unchanged.
# Original demo-asset PROVISIONING_DOWNLOADS are omitted; batch uses user photos.
vastai create instance "$OFFER_ID" \
  --image vastai/comfy:v0.35.0-cuda-13.2-py312 \
  --env '-p 1111:1111 -p 8080:8080 -p 8384:8384 -p 72299:72299 -p 8188:8188 -p 8288:8288 -e COMFYUI_ARGS="--disable-auto-launch --disable-xformers --port 18188 --enable-cors-header" -e COMFYUI_API_BASE="http://localhost:18188" -e OPEN_BUTTON_PORT="1111" -e OPEN_BUTTON_TOKEN="1" -e JUPYTER_DIR="/" -e DATA_DIRECTORY="/workspace/" -e PORTAL_CONFIG="localhost:1111:11111:/:Instance Portal|localhost:8188:18188:/:ComfyUI|localhost:8288:18288:/docs:API Wrapper|localhost:8188:18188:/:ComfyUI|localhost:8080:18080:/:Jupyter|localhost:8080:8080:/terminals/1:Jupyter Terminal|localhost:8384:18384:/:Syncthing"' \
  --onstart-cmd "$ONSTART" \
  --disk 65 --jupyter --ssh --direct
