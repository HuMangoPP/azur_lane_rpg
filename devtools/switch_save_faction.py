"""Switch a save file to another faction's shipgirls.

Usage: python devtools/switch_save_faction.py SN
"""

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SHIPGIRLS_PATH = ROOT / "data" / "shipgirls.json"
SAVE_PATH = ROOT / "data" / "save_file.json"


def switch_faction(save, shipgirls, faction):
    target_by_hull = {}
    for name, info in shipgirls.items():
        if info["faction"] == faction:
            hull = info["hull_type"]
            if hull in target_by_hull:
                raise ValueError(f"Faction {faction} has multiple {hull} shipgirls")
            target_by_hull[hull] = name
    if not target_by_hull:
        raise ValueError(f"Unknown faction: {faction}")

    old_factions = save["unlocked_factions"]
    if len(old_factions) != 1:
        raise ValueError("Expected exactly one unlocked faction in the save")
    old_faction = old_factions[0]

    def replacement(name):
        if name not in shipgirls:
            raise ValueError(f"Unknown shipgirl in save: {name}")
        hull = shipgirls[name]["hull_type"]
        if hull not in target_by_hull:
            raise ValueError(f"Faction {faction} has no {hull} shipgirl")
        return target_by_hull[hull]

    # Build every mapping before changing the save, so invalid data leaves it intact.
    shipgirl_names = {name: replacement(name) for name in save["shipgirls"]}
    cube_names = {name: replacement(name) for name in save["specialized_wisdom_cubes"]}
    research = save["research_target"]
    new_research = replacement(research) if research is not None else None
    item_names = {
        info["unique_item"]: shipgirls[replacement(name)]["unique_item"]
        for name, info in shipgirls.items()
        if info["faction"] == old_faction
    }

    new_shipgirls = {}
    for name, progress in save["shipgirls"].items():
        new_name = shipgirl_names[name]
        if new_name in new_shipgirls:
            raise ValueError(f"Multiple saved shipgirls map to {new_name}")
        new_shipgirls[new_name] = progress

    new_cubes = {}
    for name, count in save["specialized_wisdom_cubes"].items():
        new_name = cube_names[name]
        new_cubes[new_name] = new_cubes.get(new_name, 0) + count

    new_inventory = {}
    for item, count in save["inventory"].items():
        new_item = item_names.get(item, item)
        new_inventory[new_item] = new_inventory.get(new_item, 0) + count

    save["unlocked_factions"] = [faction]
    save["shipgirls"] = new_shipgirls
    save["inventory"] = new_inventory
    save["specialized_wisdom_cubes"] = new_cubes
    save["research_target"] = new_research


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("faction", help="Target faction key, for example SN")
    parser.add_argument("--save-file", type=Path, default=SAVE_PATH)
    args = parser.parse_args()

    with SHIPGIRLS_PATH.open(encoding="utf-8") as file:
        shipgirls = json.load(file)
    with args.save_file.open(encoding="utf-8") as file:
        save = json.load(file)

    switch_faction(save, shipgirls, args.faction)
    with args.save_file.open("w", encoding="utf-8") as file:
        json.dump(save, file, indent="\t", ensure_ascii=False)
        file.write("\n")


if __name__ == "__main__":
    main()
