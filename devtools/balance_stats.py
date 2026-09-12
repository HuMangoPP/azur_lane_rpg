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

