# Sortie Encounter Balancing Guide

This document records the heuristics used to build and revise encounters in `data/sorties.json`. They are starting points for encounter design, not strict balance rules. Playtesting should override any guideline here.

## Data format and basic constraints

Each enemy is encoded as `type:level`, for example `"breaker:7"`. An encounter divides enemies between `front` and `back`. Ordering within either list is not meaningful.

Use no more than three enemies in either row. Six enemies is therefore the practical encounter maximum.

Keep `lurker` out of the frontline under normal circumstances. Its low durability and long attack windup mean that an exposed lurker will often die before contributing. A frontline lurker may be used as a deliberate distraction, but it should be a rare, playtested exception.

Treat `tester` as a boss rather than a normal composition tool:

- Do not use `tester` as a replacement for another enemy.
- Do not casually move an existing `tester` between rows or encounters.
- In a newly authored chapter, reserve it for the final encounter unless the chapter design explicitly says otherwise.
- Evaluate its difficulty separately from regular enemies because its base stats are substantially higher.

## Enemy roles

| Enemy | Targeting | Typical row | Encounter purpose |
| --- | --- | --- | --- |
| `explorer` | Foremost shipgirl | Front | Durable screen and basic damage sponge |
| `tracer` | Foremost shipgirl | Front | Screen with somewhat greater offensive pressure |
| `oceana` | Highest-HP shipgirl | Either | Flexible threat that spreads damage away from the foremost target |
| `breaker` | Entire fleet | Back, occasionally front | High-priority fleet-wide damage dealer; useful as an exposed mini-boss |
| `strategist` | Entire fleet | Back | Protected fleet-wide damage dealer and mini-boss threat |
| `lurker` | Single/foremost target | Back | Fragile, slow-windup damage dealer that needs protection |
| `tester` | Entire fleet | Boss-dependent | Major boss threat |

Frontline `breaker` and `strategist` placements change the encounter's texture by exposing a priority target. A breaker can flex forward fairly often; a frontline strategist should be less common. `explorer` and `tracer` can occasionally appear in back, but this should remain unusual so that the rows retain distinct purposes.

## Build around targeting distribution

Enemy count alone does not determine difficulty. Concentrating several enemies on the same target can sink one shipgirl unexpectedly, while stacking fleet-wide attackers can make damage feel unavoidable.

For a four-enemy encounter, a reliable balanced distribution is:

- Two enemies that attack the foremost shipgirl.
- One `oceana` that attacks the highest-HP shipgirl.
- One `breaker` or `strategist` that attacks the entire fleet.

Useful variations include one foremost attacker, one highest-HP attacker, and two fleet-wide attackers for a harder encounter, or replacing one foremost attacker with a second `oceana` to spread pressure differently.

Avoid routinely using three or more fleet-wide attackers in a small encounter. Also avoid filling a formation with only `explorer`, `tracer`, and `lurker`; all of their pressure tends to converge on the same shipgirl. Duplicate types are valid when they create an intentional identity, such as a double-lurker ambush or double-oceana pressure, but should not become the default template.

## Front and back composition

The usual formation is a frontline screen protecting one or more priority threats. Do not use that shape for every encounter.

Rotate among several tactical shapes:

- **Conventional screen:** two or three `explorer`/`tracer`/`oceana` in front, with damage dealers behind them.
- **Thin front:** two front enemies protecting two or three back enemies. This creates an urgent damage race.
- **Exposed priority target:** place a `breaker`, or rarely a `strategist`, in front so the player can remove dangerous damage early.
- **Split priority threats:** place one damage dealer in front and another in back, forcing a target-selection decision.
- **Unprotected strike group:** put every enemy in front and leave the back empty. Use sparingly as a fast, aggressive change of pace.
- **Rear-line meat shield:** put an `explorer` or `tracer` in back. This is an occasional surprise, not a standard formation.
- **Specialized formation:** use duplicate `oceana`, `breaker`, `strategist`, or `lurker` enemies to give an encounter a distinct identity.

When auditing variety, compare enemy types and rows without considering list order or level. Two encounters with the same type distribution are mechanically the same layout even if their list order differs.

## Encounter counts and sizes

The current general structure is:

- Three encounters for a normal sortie.
- Four encounters for a mini-boss sortie, normally identified by having three or more map coordinates.
- A chapter-ending boss sortie may also use four encounters.

Local pacing requirements can override this. When a sortie is specifically structured as `4, 4, 4, 5`, the first three encounters should each contain four enemies and the last should contain five.

Adding enemies is a stronger difficulty increase than adding one level. When expanding an encounter, choose the new enemy to complement its targeting distribution rather than simply adding the strongest available damage dealer.

## Difficulty progression within a sortie

Every successive encounter should be at least as threatening as the preceding one. Increase difficulty using one or more of these levers:

1. Add an enemy.
2. Raise one or two existing enemies by one level.
3. Replace a screen enemy with `oceana`, `breaker`, `strategist`, or `lurker`.
4. Move a damage dealer behind protection.
5. Introduce a second priority threat.

Prefer changing one major lever at a time. This makes the curve easier to reason about and helps identify the cause of a playtest difficulty spike.

A common three-encounter progression is:

1. Four enemies with balanced targeting.
2. Four or five enemies with slightly higher levels or a more dangerous role mix.
3. Five or six enemies with another damage dealer or a protected mini-boss.

For four encounters, insert another intermediate step instead of making the final jump disproportionately large.

## Difficulty progression between sorties

The last encounter of one sortie should be roughly equivalent to, or slightly harder than, the first encounter of the next sortie. The new sortie can briefly relax composition complexity, but it should compensate with higher levels or stronger enemy roles.

Current regular-enemy level ranges provide a rough reference:

| Chapter | Approximate regular-enemy levels |
| --- | --- |
| 0 | 0–1 |
| 1 | 1–3 |
| 2 | 3–9 |
| 3 | 8–20 |

The overlaps are intentional. Levels are only one part of difficulty; enemy count, targeting distribution, role strength, and row placement also matter. In chapter 3, regular enemy levels generally rise by about one every few sorties rather than every encounter.

Do not compare `tester` levels directly with regular enemy levels. The current chapter bosses use `tester:0`, `tester:2`, `tester:3`, and `tester:5`, but their much higher base stats make these values non-equivalent to regular siren levels.

## Lightweight difficulty audit

A rough score can catch obvious regressions before playtesting:

```text
enemy score = 10 + level + role modifier

explorer:   0
tracer:     1
oceana:     2
lurker:     3
breaker:    4
strategist: 4
```

Sum the enemy scores for each encounter and confirm that the values do not decrease within a sortie. Give `tester` a much larger special modifier, such as 40, or exclude boss encounters from the calculation.

This score is deliberately crude. It does not model attack timing, protection, target concentration, actual DPS, or effective HP. Use `devtools/balance_stats.py` when stat-level analysis is useful, and use actual playtests as the final authority.

## Validation checklist

After editing `sorties.json`, verify all of the following:

- The file parses as valid JSON.
- Only the intended sorties changed.
- Normal sorties and mini-boss sorties have the intended encounter counts.
- Each requested encounter has the correct total enemy count.
- Neither `front` nor `back` contains more than three enemies.
- No `lurker` is accidentally placed in front.
- Enemy encodings match `type:integer` with no stray spaces.
- `tester` occurs only where intended, in the intended row and encounter.
- Difficulty does not visibly regress within a sortie.
- The last encounter of one sortie transitions reasonably into the first encounter of the next.
- Repeated layouts are intentional rather than copy-and-paste artifacts.
- Targeting is not unintentionally concentrated on one shipgirl or overloaded with fleet-wide attackers.

Finally, playtest for outcomes that static checks cannot reveal: whether a lurker gets an attack off, whether a protected fleet-wide attacker lives too long, whether one shipgirl absorbs nearly all incoming damage, and whether an exposed priority target creates an interesting decision instead of an easy encounter.
