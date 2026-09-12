import json
import math


def stat_values(stats, stat):
    return [
        stats[stat][0] + stats[stat][1] * level
        for level in range(10)
    ]


if __name__ == "__main__":
    with open("data/stats.json") as f:
        stats = json.load(f)

    print("Shipgirl DPS calculation:")
    for hull_type, hull_stats in stats.items():
        fps = stat_values(hull_stats, "firepower")
        rlds = stat_values(hull_stats, "reload")
        print(f"{hull_type}: {[fp * rld / 1000 for fp, rld in zip(fps, rlds)]}")

    print("Shipgirl EHP calculation:")
    for hull_type, hull_stats in stats.items():
        dmgs = [5 + 3 * level for level in range(10)]
        hps = stat_values(hull_stats, "max_hp")
        evas = stat_values(hull_stats, "evasion")
        num_hits = [math.ceil(hp / dmg) for hp, dmg in zip(hps, dmgs)]
        num_evades = [math.floor(num_hit * eva / 1000) for num_hit, eva in zip(num_hits, evas)]
        print(f"{hull_type}: {[hp + dmg * num_evade for hp, dmg, num_evade in zip(hps, dmgs, num_evades)]}")

    with open("data/sirens.json") as f:
        stats = json.load(f)

    print("Siren DPS calculation:")
    for hull_type, hull_stats in stats.items():
        fps = stat_values(hull_stats, "firepower")
        rlds = stat_values(hull_stats, "reload")
        print(f"{hull_type}: {[fp * rld / 1000 for fp, rld in zip(fps, rlds)]}")

    print("Siren EHP calculation:")
    for hull_type, hull_stats in stats.items():
        dmgs = [5 + 3 * level for level in range(10)]
        hps = stat_values(hull_stats, "max_hp")
        evas = stat_values(hull_stats, "evasion")
        num_hits = [math.ceil(hp / dmg) for hp, dmg in zip(hps, dmgs)]
        num_evades = [math.floor(num_hit * eva / 1000) for num_hit, eva in zip(num_hits, evas)]
        print(f"{hull_type}: {[hp + dmg * num_evade for hp, dmg, num_evade in zip(hps, dmgs, num_evades)]}")

    with open("data/stats.json") as f:
        stats = json.load(f)

    with open("data/equipment.json") as f:
        equipment_data = json.load(f)

    equipment = [
        "twin_100",
        "tri_155",
        "tri_203",
        "quad_305",
        "type_96_torp",
        "tenrai",
    ]
    
    print("Shipgirl weapon DPS calculation:")
    for equip in equipment:
        equip_data = equipment_data[equip]
        shipgirl_stats = stats[equip_data["equippable_by"]]
        fps = stat_values(shipgirl_stats, "firepower")
        fps = [fp + equip_data["firepower"] for fp in fps]
        rlds = stat_values(shipgirl_stats, "reload")
        rlds = [rld + equip_data["reload"] for rld in rlds]
        print(f"{equip}: {[fp * rld / 1000 for fp, rld in zip(fps, rlds)]}")

    equipment = [
        "autoloader",
        "fire_control_table",
        "ap_shell",
        "fire_control_radar",
    ]

    print("Shipgirl aux DPS calculation:")
    for equip in equipment:
        equip_data = equipment_data[equip]
        for hull_type, hull_stats in stats.items():
            fps = stat_values(hull_stats, "firepower")
            fps = [fp + equip_data.get("firepower", 0) for fp in fps]
            rlds = stat_values(hull_stats, "reload")
            rlds = [rld + equip_data.get("reload", 0) for rld in rlds]
            print(f"{hull_type}-{equip}: {[fp * rld / 1000 for fp, rld in zip(fps, rlds)]}")

    equipment = [
        "steering_gear",
        "camoflauge",
        "repair_toolkit",
        "maintenance_crane",
    ]

    print("Shipgirl aux EHP calculation:")
    for equip in equipment:
        equip_data = equipment_data[equip]
        for hull_type, hull_stats in stats.items():
            dmgs = [5 + 3 * level for level in range(10)]
            hps = stat_values(hull_stats, "max_hp")
            hps = [hp + equip_data.get("max_hp", 0) for hp in hps]
            evas = stat_values(hull_stats, "evasion")
            evas = [eva + equip_data.get("evasion", 0) for eva in evas]
            num_hits = [math.ceil(hp / dmg) for hp, dmg in zip(hps, dmgs)]
            num_evades = [math.floor(num_hit * eva / 1000) for num_hit, eva in zip(num_hits, evas)]
            print(f"{hull_type}-{equip}: {[hp + dmg * num_evade for hp, dmg, num_evade in zip(hps, dmgs, num_evades)]}")
