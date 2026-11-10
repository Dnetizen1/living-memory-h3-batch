#!/usr/bin/env python3
"""Generate a ready-wired MiniMax H3 Living Memory batch UI workflow.

Uses the current official Comfy-Org workflow as source of truth, preserving its
complete H3 subgraph, models, audio, duration, and resolution settings.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import sys
from urllib.request import Request, urlopen

OFFICIAL_URL = (
    "https://raw.githubusercontent.com/Comfy-Org/workflow_templates/"
    "refs/heads/main/templates/video_minimax_h3_i2v.json"
)
SUBGRAPH_NAME = "Image to Video (MiniMax H3)"
SYNC_TYPE = "FolderBatch Sync Queue"
IMAGE_TYPE = "FolderBatch Load Image"
TEXT_TYPE = "FolderBatch Load Text"
DEFAULT_FOLDER = "/workspace/living_memory/input"


def fetch_source(source: str) -> dict:
    if source.startswith(("http://", "https://")):
        request = Request(source, headers={"User-Agent": "living-memory-batch-builder/1.0"})
        with urlopen(request, timeout=90) as response:
            return json.load(response)
    with open(source, encoding="utf-8") as handle:
        return json.load(handle)


def add_link(graph: dict, source: dict, source_index: int, dest: dict,
             dest_index: int, signal_type: str, link_id: int) -> None:
    source_out = source["outputs"][source_index]
    dest_in = dest["inputs"][dest_index]
    if source_out["type"] != signal_type or dest_in["type"] != signal_type:
        raise ValueError(f"Type mismatch: {source_out['type']} -> {dest_in['type']}")
    if dest_in.get("link") is not None:
        raise ValueError(f"Input {dest['id']}:{dest_index} is already connected")
    source_out.setdefault("links", [])
    if source_out["links"] is None:
        source_out["links"] = []
    source_out["links"].append(link_id)
    dest_in["link"] = link_id
    graph["links"].append([link_id, source["id"], source_index, dest["id"], dest_index, signal_type])


def node_base(node_id: int, kind: str, pos: list[int], size: list[int], order: int) -> dict:
    return {
        "id": node_id, "type": kind, "pos": pos, "size": size, "flags": {},
        "order": order, "mode": 0, "inputs": [], "outputs": [],
        "properties": {"Node name for S&R": kind}, "widgets_values": [],
    }


def modify(original: dict, folder: str = DEFAULT_FOLDER) -> dict:
    graph = copy.deepcopy(original)
    nodes = graph.get("nodes", [])
    matches = [n for n in nodes if n.get("type") == SYNC_TYPE]
    if matches:
        validate(graph)
        return graph  # Safe to re-run on our generated workflow.

    subgraph_defs = graph.get("definitions", {}).get("subgraphs", [])
    defs = [s for s in subgraph_defs if s.get("name") == SUBGRAPH_NAME]
    if len(defs) != 1 or not any(i.get("name") == "prompt" for i in defs[0].get("inputs", [])):
        raise ValueError("Expected official MiniMax H3 I2V subgraph and prompt input are missing")
    sub_id = defs[0]["id"]
    subs = [n for n in nodes if n.get("type") == sub_id]
    if len(subs) != 1:
        raise ValueError("Expected exactly one official H3 I2V subgraph node")
    h3 = subs[0]
    images = [n for n in nodes if n.get("type") == "LoadImage" and any(
        link[1] == n["id"] and link[3] == h3["id"] and link[5] == "IMAGE"
        for link in graph.get("links", []))]
    if len(images) != 1:
        raise ValueError("Cannot uniquely find original LoadImage feeding H3 first_frame")
    load_image = images[0]
    saves = [n for n in nodes if n.get("type") == "SaveVideo" and any(
        link[1] == h3["id"] and link[3] == n["id"] for link in graph.get("links", []))]
    if len(saves) != 1:
        raise ValueError("Cannot find SaveVideo output linked to H3")
    save = saves[0]

    def require_slot(node: dict, name: str, type_name: str) -> int:
        found = [i for i, slot in enumerate(node.get("inputs", []))
                 if slot.get("name") == name and slot.get("type") == type_name]
        if len(found) != 1:
            raise ValueError(f"Expected input {name}:{type_name} on node {node['id']}")
        return found[0]

    require_slot(h3, "first_frame", "IMAGE")
    require_slot(h3, "last_frame", "IMAGE")
    prompt_slots = [i for i, entry in enumerate(h3["inputs"]) if entry.get("name") == "prompt"]
    if prompt_slots:
        prompt_index = prompt_slots[0]
        if h3["inputs"][prompt_index]["type"] != "STRING":
            raise ValueError("H3 prompt slot is not STRING")
    else:
        prompt_index = require_slot(h3, "last_frame", "IMAGE") + 1
        # In the official JSON the prompt is already exposed as a *widget* but
        # not a wired input. Convert that widget to an input while keeping its
        # existing value as a fallback. The subgraph definition already declares
        # input #2 (`prompt`), so no changes to its internals are necessary.
        h3["inputs"].insert(prompt_index, {
            "name": "prompt", "type": "STRING", "widget": {"name": "prompt"}, "link": None,
        })
        # LiteGraph indexes target slots positionally, unlike named API inputs.
        for link in graph["links"]:
            if link[3] == h3["id"] and link[4] >= prompt_index:
                link[4] += 1

    if not any(l[1] == load_image["id"] and l[3] == h3["id"] and l[4] == 0 for l in graph["links"]):
        raise ValueError("Unexpected first-frame wiring in official template")
    # Reuse the original image loader ID and first-frame link to preserve the
    # rest of the official graph completely.
    prior_image_links = load_image["outputs"][0].get("links")
    load_image.update({
        "type": IMAGE_TYPE, "size": [325, 150], "pos": [-1730, 6050],
        "inputs": [{"name": "image_path", "type": "STRING", "link": None}],
        "outputs": [
            {"name": "image", "type": "IMAGE", "links": prior_image_links},
            {"name": "mask", "type": "MASK", "links": None},
            {"name": "positive", "type": "STRING", "links": None},
            {"name": "negative", "type": "STRING", "links": None},
        ],
        "properties": {"Node name for S&R": IMAGE_TYPE},
        "widgets_values": [],
    })
    load_image.pop("widgets_values_named", None)

    existing_node_ids = [n["id"] for n in nodes if isinstance(n.get("id"), int)]
    next_node = max(existing_node_ids + [graph.get("last_node_id", 0)]) + 1
    existing_link_ids = [l[0] for l in graph["links"]]
    next_link = max(existing_link_ids + [graph.get("last_link_id", 0)]) + 1

    queue = node_base(next_node, SYNC_TYPE, [-2260, 5870], [460, 630], 0)
    # Order matches FB_FolderSyncQueue.INPUT_TYPES required + optional fields.
    queue_widgets = {
        "common_folder": folder,
        "sync_mode": "By Name",
        "missing_policy": "Error",  # Never silently mismatch or drop photos.
        "start_at": 0,
        "auto_queue": True,
        "sort_by": "Name", "order_by": "A-Z",
        "use_image": True,
        "image_folder": "",
        "image_extension": "*.jpg;*.jpeg;*.png;*.webp;*.bmp",
        "use_video": False, "video_folder": "", "video_extension": "*.mp4",
        "use_text": True, "text_folder": "", "text_extension": "*.txt",
        "text_unit_mode": "file", "skip_empty_lines": True,
        "use_audio": False, "audio_folder": "", "audio_extension": "*.mp3;*.wav;*.flac;*.m4a;*.ogg;*.aac",
        "item_count": 0, "progress": 0.0,
    }
    queue["widgets_values"] = list(queue_widgets.values())
    queue["widgets_values_named"] = queue_widgets
    queue["outputs"] = [
        {"name": name, "type": kind, "links": None}
        for name, kind in [
            ("base_name", "STRING"), ("image_path", "STRING"),
            ("video_path", "STRING"), ("text_path", "STRING"),
            ("line_index", "INT"), ("audio_path", "STRING"),
            ("item_count", "INT"),
        ]
    ]
    load_text = node_base(next_node + 1, TEXT_TYPE, [-1350, 6050], [310, 170], 2)
    load_text["inputs"] = [
        {"name": "text_path", "type": "STRING", "link": None},
        # File mode uses the full TXT, so do not wire optional line_index.
    ]
    load_text["outputs"] = [{"name": "text", "type": "STRING", "links": None}]
    load_text["widgets_values"] = [True]
    load_text["widgets_values_named"] = {"skip_empty_lines": True}

    # One independent queue execution per pair. The FolderBatch frontend
    # advances start_at and queues the next item after completion.
    for src, si, dst, di, kind in [
        (queue, 1, load_image, 0, "STRING"),
        (queue, 3, load_text, 0, "STRING"),
        (load_text, 0, h3, prompt_index, "STRING"),
    ]:
        add_link(graph, src, si, dst, di, kind, next_link)
        next_link += 1

    # Convert the SaveVideo filename_prefix widget to an input so each MP4
    # begins with the image's basename (e.g. photo_001_00001.mp4).
    if not any(i.get("name") == "filename_prefix" for i in save.get("inputs", [])):
        save["inputs"].append({
            "name": "filename_prefix", "type": "STRING",
            "widget": {"name": "filename_prefix"}, "link": None,
        })
    prefix_index = require_slot(save, "filename_prefix", "STRING")
    if save["inputs"][prefix_index]["link"] is not None:
        raise ValueError("SaveVideo filename_prefix input already in use")
    add_link(graph, queue, 0, save, prefix_index, "STRING", next_link)
    next_link += 1
    # Explicit MP4 container; leave codec on auto to preserve native audio.
    if len(save.get("widgets_values", [])) >= 2:
        save["widgets_values"][1] = "mp4"
    save.setdefault("widgets_values_named", {})["format"] = "mp4"

    help_node = node_base(next_node + 2, "MarkdownNote", [-2260, 6550], [780, 265], 99)
    help_node["title"] = "Living Memory — Batch I2V"
    help_text = (
        "### Living Memory — batch mode (image + matching prompt)\n\n"
        f"Put `photo_001.jpg` + `photo_001.txt` in `{folder}`. "
        "More pairs: `photo_002.png` + `photo_002.txt`, etc.\n\n"
        "FolderBatch Sync Queue: By Name / Error / auto_queue=True. "
        "Press Queue once in the ComfyUI browser. A new job should be "
        "queued after each completed job while the frontend is connected.\n\n"
        "Prompt comes from the paired TXT. H3 duration/resolution/audio/model "
        "settings remain from the official I2V template. "
        "SaveVideo filename prefix uses the photo basename."
    )
    help_node["widgets_values"] = [help_text]
    help_node["widgets_values_named"] = {"text": help_text}

    nodes.extend([queue, load_text, help_node])
    graph["last_node_id"] = next_node + 2
    graph["last_link_id"] = next_link - 1
    graph["revision"] = graph.get("revision", 0) + 1
    validate(graph)
    return graph


def validate(graph: dict) -> None:
    nodes = graph["nodes"]
    by_id = {n["id"]: n for n in nodes}
    if len(by_id) != len(nodes):
        raise ValueError("Duplicate top-level node IDs")
    link_ids = []
    for entry in graph["links"]:
        link_id, a, a_index, b, b_index, kind = entry
        link_ids.append(link_id)
        src, dest = by_id[a], by_id[b]
        assert src["outputs"][a_index]["type"] == kind, (a, kind)
        assert dest["inputs"][b_index]["type"] == kind, (b, kind)
        assert link_id in (src["outputs"][a_index].get("links") or []), (a, link_id)
        assert dest["inputs"][b_index]["link"] == link_id, (b, link_id)
    if len(link_ids) != len(set(link_ids)):
        raise ValueError("Duplicate top-level link IDs")
    types = [n["type"] for n in nodes]
    for node_type in (SYNC_TYPE, IMAGE_TYPE, TEXT_TYPE, "SaveVideo"):
        if node_type not in types:
            raise ValueError(f"Missing {node_type}")
    queue = next(n for n in nodes if n["type"] == SYNC_TYPE)
    assert queue["widgets_values_named"]["sync_mode"] == "By Name"
    assert queue["widgets_values_named"]["use_image"] is True
    assert queue["widgets_values_named"]["use_text"] is True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=OFFICIAL_URL, help="Official JSON URL or local file")
    parser.add_argument("--output", "-o", default="workflows/video_minimax_h3_i2v_batch.json")
    parser.add_argument("--folder", default=DEFAULT_FOLDER,
                        help="Absolute folder path on the Vast.ai instance")
    args = parser.parse_args()
    try:
        source = fetch_source(args.source)
        modified = modify(source, folder=args.folder)
        dest = Path(args.output)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(modified, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"OK: {dest} ({len(modified['nodes'])} top-level nodes; "
              f"{len(modified['links'])} top-level links)")
    except Exception as exc:
        print(f"ERROR: Could not build workflow: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
