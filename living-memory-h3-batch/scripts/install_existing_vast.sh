#!/usr/bin/env bash
# Install on an EXISTING Vast.ai instance which already has ComfyUI + H3 models.
set -euo pipefail
COMFYUI="${COMFYUI:-/workspace/ComfyUI}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "$COMFYUI/custom_nodes" "$COMFYUI/user/default/workflows" /workspace/living_memory/input
if [[ ! -d "$COMFYUI/custom_nodes/ComfyUI-FolderBatch/.git" ]]; then
  git clone https://github.com/aiai-r/ComfyUI-FolderBatch "$COMFYUI/custom_nodes/ComfyUI-FolderBatch"
else
  echo "FolderBatch already installed: $COMFYUI/custom_nodes/ComfyUI-FolderBatch"
fi
python3 "$ROOT/scripts/build_workflow.py" \
  --output "$COMFYUI/user/default/workflows/video_minimax_h3_i2v_batch.json"
echo "Workflow installed. Restart ComfyUI using the Vast.ai portal / supervisor,"
echo "then open Workflows -> video_minimax_h3_i2v_batch."
echo "Photo/TXT folder: /workspace/living_memory/input"
