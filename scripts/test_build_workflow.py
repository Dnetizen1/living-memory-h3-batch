#!/usr/bin/env python3
"""Offline structural regression tests; real H3 generation needs GPU + ComfyUI."""
from build_workflow import modify, validate


def fixture():
    return {
        "id": "official-like-mini", "revision": 0,
        "last_node_id": 126, "last_link_id": 245,
        "nodes": [
            {"id": 114, "type": "LoadImage", "pos": [0, 0], "size": [200, 300],
             "inputs": [], "outputs": [
                 {"name": "IMAGE", "type": "IMAGE", "links": [218]},
                 {"name": "MASK", "type": "MASK", "links": None}],
             "widgets_values": ["demo.png", "image"]},
            {"id": 115, "type": "ResolutionSelector", "pos": [0, 0], "size": [200, 300],
             "inputs": [], "outputs": [
                 {"name": "width", "type": "INT", "links": [219]},
                 {"name": "height", "type": "INT", "links": [220]}]},
            {"id": 105, "type": "sub-i2v", "pos": [0, 0], "size": [200, 300],
             "inputs": [
                 {"name": "first_frame", "type": "IMAGE", "link": 218},
                 {"name": "last_frame", "type": "IMAGE", "link": None},
                 {"name": "width", "type": "INT", "link": 219},
                 {"name": "height", "type": "INT", "link": 220}],
             "outputs": [{"name": "VIDEO", "type": "VIDEO", "links": [194]}],
             "widgets_values": ["Demo prompt", 1344, 768, 5],
             "widgets_values_named": {"prompt": "Demo prompt", "value_1": 5}},
            {"id": 92, "type": "SaveVideo", "pos": [0, 0], "size": [200, 300],
             "inputs": [{"name": "video", "type": "VIDEO", "link": 194}],
             "outputs": [{"name": "video", "type": "VIDEO", "links": None}],
             "widgets_values": ["video/MiniMax_H3", "auto", "auto"]},
        ],
        "links": [
            [194, 105, 0, 92, 0, "VIDEO"],
            [218, 114, 0, 105, 0, "IMAGE"],
            [219, 115, 0, 105, 2, "INT"],
            [220, 115, 1, 105, 3, "INT"],
        ],
        "definitions": {"subgraphs": [{"id": "sub-i2v", "name": "Image to Video (MiniMax H3)",
            "inputs": [{"name": "first_frame"}, {"name": "last_frame"}, {"name": "prompt"}]}]},
    }


def test_wiring():
    source = fixture()
    result = modify(source)
    validate(result)
    assert source["nodes"][0]["type"] == "LoadImage"  # no mutation
    assert len(result["nodes"]) == len(source["nodes"]) + 3
    h3 = next(n for n in result["nodes"] if n["id"] == 105)
    assert [i["name"] for i in h3["inputs"]] == ["first_frame", "last_frame", "prompt", "width", "height"]
    assert [x[4] for x in result["links"] if x[3] == 105 and x[5] == "INT"] == [3, 4]
    sync = next(n for n in result["nodes"] if n["type"] == "FolderBatch Sync Queue")
    assert sync["widgets_values_named"]["auto_queue"]
    assert sync["widgets_values_named"]["missing_policy"] == "Error"
    save = next(n for n in result["nodes"] if n["type"] == "SaveVideo")
    assert save["inputs"][1]["name"] == "filename_prefix"
    assert save["inputs"][1]["link"] is not None
    # Re-running should NOT duplicate connections or nodes.
    again = modify(result)
    assert len(again["links"]) == len(result["links"])
    assert len(again["nodes"]) == len(result["nodes"])
    # Original H3 subgraph body is copied as-is.
    assert again["definitions"] == source["definitions"]


if __name__ == "__main__":
    test_wiring()
    print("PASS: batch graph conversion and idempotency (offline fixture)")
