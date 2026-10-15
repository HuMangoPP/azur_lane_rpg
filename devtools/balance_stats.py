import json
from pathlib import Path


LEVELS = range(10)
MAX_DPS_DEVIATION = 0.03
PROJECT_ROOT = Path(__file__).resolve().parents[1]
TIER_2_POWER_BUDGETS = {
    "CV": {"firepower": 12, "reload": 15},
    "SS": {"firepower": 11, "reload": 16},
}
TIER_2_SPECIAL_WEAPONS = (
    "type_96_torp",
    "mark_28_torp",
    "tenrai",
    "wyvern",
)


def stat_values(stats, stat):
    return [stats[stat][0] + stats[stat][1] * level for level in LEVELS]


def calculate_dps(hull_type, fp, rld, shell_type=None, damage_multiplier=1):
    if shell_type == "AP":
        fp *= 1.1
    if shell_type == "HE":
        fp += 3 * 2 * 0.2
    attack_duration = 5 if hull_type in ["SS", "CV"] else 0.5
    return fp * damage_multiplier / (1000 / rld + attack_duration)


def weapon_dps(stats, equipment):
    hull_type = equipment["equippable_by"]
    hull_stats = stats[hull_type]
    firepower = [
        value + equipment["firepower"]
        for value in stat_values(hull_stats, "firepower")
    ]
    reload = [
        value + equipment["reload"]
        for value in stat_values(hull_stats, "reload")
    ]
    shell_type = equipment.get("shell_type")
    return [
        calculate_dps(hull_type, fp, rld, shell_type)
        for fp, rld in zip(firepower, reload)
    ]


def reference_dps(stats, hull_type):
    return weapon_dps(
        stats,
        {
            "equippable_by": hull_type,
            **TIER_2_POWER_BUDGETS[hull_type],
        },
    )


def scaled(values, multiplier):
    return [value * multiplier for value in values]


def deviations(values, reference):
    return [value / baseline - 1 for value, baseline in zip(values, reference)]


def print_comparison(name, values, reference):
    percent_deviations = [100 * value for value in deviations(values, reference)]
    print(f"{name} DPS: {[round(value, 4) for value in values]}")
    print(f"{name} deviation: {[round(value, 2) for value in percent_deviations]}%")


def validate_power_budget(name, values, reference):
    max_deviation = max(abs(value) for value in deviations(values, reference))
    if max_deviation > MAX_DPS_DEVIATION:
        raise ValueError(
            f"{name} exceeds the Tier 2 power budget tolerance: "
            f"{max_deviation:.2%} > {MAX_DPS_DEVIATION:.2%}"
        )


if __name__ == "__main__":
    with (PROJECT_ROOT / "data" / "stats.json").open() as file:
        stats = json.load(file)
    with (PROJECT_ROOT / "data" / "equipment.json").open() as file:
        equipment_data = json.load(file)

    references = {
        hull_type: reference_dps(stats, hull_type)
        for hull_type in TIER_2_POWER_BUDGETS
    }

    print("Tier 2 CV and SS weapon DPS calculation (levels 0-9):")
    for weapon_name in TIER_2_SPECIAL_WEAPONS:
        equipment = equipment_data[weapon_name]
        hull_type = equipment["equippable_by"]
        baseline = references[hull_type]
        direct_dps = weapon_dps(stats, equipment)

        attack_pattern = equipment.get("attack_pattern", [100])
        if len(attack_pattern) > 1:
            dps_by_target_count = {}
            for target_count in range(1, len(attack_pattern) + 1):
                damage_multiplier = sum(attack_pattern[:target_count]) / 100
                effective_dps = scaled(direct_dps, damage_multiplier)
                dps_by_target_count[target_count] = effective_dps
                target_label = "target" if target_count == 1 else "targets"
                print_comparison(
                    f"{weapon_name} ({target_count} {target_label})",
                    effective_dps,
                    baseline,
                )
            validate_power_budget(
                f"{weapon_name} (2 targets)",
                dps_by_target_count[2],
                baseline,
            )
        else:
            effective_dps = scaled(direct_dps, attack_pattern[0] / 100)
            print_comparison(weapon_name, effective_dps, baseline)
            validate_power_budget(weapon_name, effective_dps, baseline)
