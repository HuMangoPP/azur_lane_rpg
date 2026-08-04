import os
import sys
import argparse
import json
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from live2d.live2d import (
    FACIAL_EXPRESSION_KEY,
    KEYFRAME_DURATION_KEY,
    KEYFRAMES_KEY,
    NEXT_ANIMATION_KEY,
    NO_LOOP_KEY,
    PART_NAMES,
)

MODEL_DIR = Path("live2d")

ANIMATION_METADATA_KEYS = {
    KEYFRAMES_KEY,
    NO_LOOP_KEY,
    NEXT_ANIMATION_KEY,
    KEYFRAME_DURATION_KEY,
    FACIAL_EXPRESSION_KEY,
}


def load_json(path):
    with path.open("r") as f:
        return json.load(f)


def save_json(path, data):
    with path.open("w") as f:
        json.dump(data, f, indent=4)
        f.write("\n")


def is_model_file(data):
    return isinstance(data, dict) and "spritesheet" in data


def migrate_animation(animation):
    if not isinstance(animation, dict):
        return {"keyframes": {"0": {}}}

    migrated = {}
    keyframes = animation.get(KEYFRAMES_KEY)
    if not isinstance(keyframes, dict):
        keyframes = {
            key: value for key, value in animation.items()
            if key not in ANIMATION_METADATA_KEYS
        }

    migrated[KEYFRAMES_KEY] = keyframes
    for metadata_key in ANIMATION_METADATA_KEYS - {KEYFRAMES_KEY}:
        if metadata_key in animation:
            migrated[metadata_key] = animation[metadata_key]
    return migrated


def migrate_animations(animations):
    if not isinstance(animations, dict):
        return {}

    return {
        animation_key: migrate_animation(animation)
        for animation_key, animation in animations.items()
    }


def migrate_model(data):
    migrated = {}

    for key, value in data.items():
        if key in PART_NAMES or key in {"parts", "animations"}:
            continue
        migrated[key] = value

    existing_parts = data.get("parts", {})
    if not isinstance(existing_parts, dict):
        existing_parts = {}

    parts = {}
    for part_name in PART_NAMES:
        part_data = existing_parts.get(part_name, data.get(part_name, {}))
        if not isinstance(part_data, dict):
            part_data = {}
        parts[part_name] = {"pivot": part_data.get("pivot", [0, 0])}

    migrated["parts"] = parts
    migrated["animations"] = migrate_animations(data.get("animations", {}))

    return migrated


def needs_migration(data):
    if not is_model_file(data):
        return False

    if "parts" not in data or "animations" not in data:
        return True

    parts = data.get("parts")
    if not isinstance(parts, dict):
        return True

    for part_name in PART_NAMES:
        part_data = parts.get(part_name)
        if not isinstance(part_data, dict):
            return True
        if set(part_data.keys()) != {"pivot"}:
            return True

    for part_name in PART_NAMES:
        part_data = data.get(part_name)
        if isinstance(part_data, dict) and "pivot" in part_data:
            return True

    animations = data.get("animations")
    if isinstance(animations, dict):
        for animation in animations.values():
            if isinstance(animation, dict) and "keyframes" not in animation:
                return True

    return False


def migrate_file(path, dry_run=False):
    data = load_json(path)
    if not is_model_file(data):
        return "skipped"
    if not needs_migration(data):
        return "unchanged"

    if not dry_run:
        save_json(path, migrate_model(data))
    return "migrated"


def main():
    parser = argparse.ArgumentParser(
        description="Migrate Live2D model JSON files to the parts/animations schema."
    )
    parser.add_argument(
        "--model-dir",
        default=MODEL_DIR,
        type=Path,
        help="Directory containing Live2D JSON files.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be migrated without writing files.",
    )
    args = parser.parse_args()

    counts = {"migrated": 0, "unchanged": 0, "skipped": 0}
    for path in sorted(args.model_dir.glob("*.json")):
        status = migrate_file(path, args.dry_run)
        counts[status] += 1
        print(f"{status}: {path}")

    print(
        "Done: "
        f"{counts['migrated']} migrated, "
        f"{counts['unchanged']} unchanged, "
        f"{counts['skipped']} skipped."
    )


if __name__ == "__main__":
    main()
