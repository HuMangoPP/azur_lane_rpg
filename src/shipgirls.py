from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from engine.types import CoordinateType, ColorType
    from engine.font import Font
    from src.menus.menu_manager import MenuManager
    from src.vfx import VFXManager

import math
import random
import pygame

from engine.util import get_rect, get_vec, draw_annulus

from src.constants import DataFiles, Color, Equipment, Box, Stats, screen_x, screen_y, Decorations
from src.vfx import shell_path, SHELL_SCALE
from live2d.live2d import (
    Live2D,
    PreRenderLive2D,
    LAYER_SIZE,
    get_live2d_model_file,
)


class Smokescreen:
    def __init__(self):
        num_smoke = 4
        self.offsets = [
            get_vec(length=random.uniform(16, 32), angle=math.radians(random.randint(0, 359)))
            for _ in range(num_smoke)
        ]
        self.smoke_timers = [
            math.radians(random.randint(0, 359))
            for _ in range(num_smoke)
        ]
    
    def update(self, dt: float):
        """Update the smokescreen."""
        self.smoke_timers = [
            (smoke_timer + dt) % math.radians(360)
            for smoke_timer in self.smoke_timers
        ]
    
    def draw(self, surface: pygame.Surface, rect: pygame.Rect):
        """Draw the smokescreen."""
        center = pygame.Vector2(rect.center)
        smoke_sprite = DataFiles.sprites["encounter"]["smoke"]
        smoke_rect = smoke_sprite.get_rect()
        sway_width = 16
        sway_height = 8
        for offset, smoke_timer in zip(self.offsets, self.smoke_timers):
            smoke_rect.center = (
                center
                + offset
                + pygame.Vector2(sway_width * math.sin(smoke_timer), sway_height * math.sin(2 * smoke_timer))
            )
            surface.blit(smoke_sprite, smoke_rect)


class DummyTarget:
    def __init__(self, menu_manager: MenuManager):
        self.rect = menu_manager.encounter_menu.fleet_slots[1]


class ShipgirlBattleComponent:
    SHELL_SPEED = 1000
    TORPEDO_SPEED = 100
    AIRCRAFT_SPEED = 100
    SONAR_DISTANCE = 250
    BATTLESTATION_PULSE_DURATION = 2.4
    BATTLESTATION_GLINT_CYCLE = 0.9
    BATTLESTATION_GLINT_LIFETIME = 0.7
    BATTLESTATION_GLINT_MAX_LENGTH = 5
    BATTLESTATION_GLINT_DRIFT = 12
    BATTLESTATION_GLINT_COUNT = 4
    BATTLESTATION_GLINT_MARGIN = 6

    def __init__(self, name: str, is_player: bool):
        self.active = False
        self.is_player = is_player

        if self.is_player:
            info = DataFiles.shipgirl_data[name]
            info = {
                **info,
                **DataFiles.save_file["shipgirls"][name],
                **DataFiles.stats_data[info["hull_type"]]
            }
        else:
            name, level = name.split(":")
            info = DataFiles.siren_data[name]
            info["exp"] = Stats.exp_to_level(int(level))

        self.name = name
        stat_keys = ["max_hp", "evasion", "firepower", "reload"]
        self.base_stats: dict[str, CoordinateType] = {
            stat_key: info[stat_key]
            for stat_key in stat_keys
        }
        self.hull_type: str = info["hull_type"]
        self.equipment: tuple[str | None, str | None, str | None] = info["equipment"]
        self.exp: float = info["exp"]
        if self.is_player:
            self.target_pref = None
        else:
            self.target_pref: str = info["target_pref"]
            self.reward_exp: float = info["reward_exp"]

        self.hp = self.stat("max_hp")
        self.cooldown_timer = 1
        self.attack_animation = False
        self.attack_timer = 0
        self.target: Shipgirl | DummyTarget = None
        self.evasion_gauge = 0
        self.ignite_timer = 0
        self.ignite_ticks = 0
        self.ignite_damage = 0

        self.last_exp = self.exp
        self.exp_timer = 0
        self.last_level = Stats.level(self.last_exp)
        self.level_timer = 0

        self.battlestation_effect_time = 0

        self.shake_time = 0

        self.smokescreen = Smokescreen()

    def shake(self):
        """Start a shake effect."""
        self.shake_time = 0.5

    def stat(self, stat: str) -> float:
        """Calculate the value of this stat.
        
        Combines the base stat based on the shipgirl's hull type and addtional
        stat amounts awarded by equipment.
        """
        return (
            Stats.stat(*self.base_stats[stat], exp=self.exp)
            + sum(
                DataFiles.equipment_data.get(equipment, {}).get(stat, 0)
                for equipment in self.equipment
            )
        )

    def gain_exp(self, amount: float):
        """Add exp."""
        previous_max_hp = self.stat("max_hp")
        self.exp += amount
        # If the shipgirl levels up, award them with the increase in max hp.
        # Only do so if they are still afloat.
        if self.hp > 0:
            self.hp += self.stat("max_hp") - previous_max_hp

    @property
    def _attack_speed(self) -> float:
        """The speed of the attack."""
        if self.hull_type == "CV":
            return self.AIRCRAFT_SPEED + DataFiles.equipment_data.get(self.equipment[Equipment.WEAPON], {}).get("aircraft_speed", 0)
        if self.hull_type == "SS":
            return self.TORPEDO_SPEED + DataFiles.equipment_data.get(self.equipment[Equipment.WEAPON], {}).get("torpedo_speed", 0)
        return self.SHELL_SPEED + DataFiles.equipment_data.get(self.equipment[Equipment.WEAPON], {}).get("shell_speed", 0)

    @property
    def _shell_type(self) -> str:
        """The shell type of the attack."""
        if self.hull_type in ["SS", "CV"]:
            return Equipment.TORPEDO
        weapon_config = DataFiles.equipment_data.get(self.equipment[Equipment.WEAPON], {})
        return weapon_config.get("shell_type", Equipment.NORMAL_SHELL)

    def reset(self):
        """Reset the battle component for a new sortie."""
        self.hp = self.stat("max_hp")
        self.cooldown_timer = 1
        self.attack_animation = False
        self.attack_timer = 0
        self.target = None
        self.evasion_gauge = 0
        self.ignite_timer = 0
        self.ignite_ticks = 0
        self.ignite_damage = 0
        self.shake_time = 0

    def ignite(self, damage: float, ticks: int):
        """Apply the ignite status effect."""
        self.ignite_timer = 0
        self.ignite_ticks = ticks
        self.ignite_damage = damage

    def _update_ignite(self, dt: float, rect: pygame.Surface, vfx_manager: VFXManager):
        if self.ignite_ticks <= 0:
            return

        # Update ignite timer and ticks, and aggregate ignite damage.
        self.ignite_timer += dt
        agg_ignite_damage = 0
        while self.ignite_timer >= 1:
            self.ignite_timer -= 1
            self.ignite_ticks -= 1
            agg_ignite_damage += 1

            if self.ignite_ticks <= 0:
                self.ignite_timer = 0
        # Deal aggregated ignite damage and spawn damage counter vfx.
        if agg_ignite_damage > 0:
            self.hp -= agg_ignite_damage
            vfx_manager.spawn_damage_counter(rect.midtop, agg_ignite_damage, Equipment.HE_SHELL)
            self.shake()

    def _deal_damage(self, target: Shipgirl, vfx_manager: VFXManager) -> bool:
        """Deal damage to the target."""
        if target.battle_component.evasion_gauge >= 1:
            # The target evades this attack.
            target.battle_component.evasion_gauge -= 1
            vfx_manager.spawn_miss_counter(target.rect.midtop)
            return False
        else:
            # Increase the target's evasion gauge.
            evasion_stat = target.battle_component.stat("evasion") / 1000
            target.battle_component.evasion_gauge += evasion_stat
            weapon_config = DataFiles.equipment_data.get(self.equipment[Equipment.WEAPON], {})
            shell_type = self._shell_type
            damage = self.stat("firepower")
            # AP shells can crit, which multiplies the damage dealt.
            crit = False
            if shell_type == Equipment.AP_SHELL:
                crit_chance = weapon_config.get("crit_chance", 10)
                crit_mult = weapon_config.get("crit_mult", 2)
                if random.randint(0, 99) < crit_chance:
                    crit = True
                    damage *= crit_mult
            target.battle_component.hp -= damage
            vfx_manager.spawn_damage_counter(target.rect.midtop, damage, shell_type, crit)
            # HE shells can cause ignition, causing the target to take damage over time.
            if shell_type == Equipment.HE_SHELL:
                ignite_chance = weapon_config.get("ignite_chance", 20)
                ignite_damage = weapon_config.get("ignite_damage", 1)
                ignite_ticks = weapon_config.get("ignite_ticks", 5)
                if random.randint(0, 99) < ignite_chance:
                    target.battle_component.ignite(ignite_damage, ignite_ticks)
            target.battle_component.shake()
            if target.battle_component.hp <= 0:
                target.battle_component.target = None
                target.battle_component.attack_animation = False
                target.battle_component.attack_timer = 0
            return True

    def _spawn_attacking_effects(self, rect: pygame.Rect, vfx_manager: VFXManager):
        """Spawn vfx on attack."""
        if self.hull_type == "CV":
            start_pos = pygame.Vector2(rect.center)
            target_pos = pygame.Vector2(self.target.rect.center)
            relpos = target_pos - start_pos
            launch_angle = math.atan2(relpos.y, relpos.x)
            vfx_manager.spawn_aircraft_launch(start_pos, launch_angle)
            return

        if self.hull_type == "SS":
            start_pos = pygame.Vector2((rect.centerx, rect.bottom))
            vfx_manager.spawn_torpedo_launch(start_pos)
            return

        start_pos = pygame.Vector2(rect.center)
        target_pos = pygame.Vector2(self.target.rect.center)
        shell_type = self._shell_type
        relpos = target_pos - start_pos
        distance = relpos.length()
        scale = distance * SHELL_SCALE
        shell_angle = math.atan2(relpos.y, relpos.x)
        shell_incline = math.atan(-relpos.x / abs(relpos.x) * scale)
        shell_render_angle = shell_angle + shell_incline
        vfx_manager.spawn_muzzle_flash(start_pos, shell_render_angle, shell_type)

    def _spawn_impact_effects(
        self, hit: bool, rect: pygame.Rect, target: Shipgirl, vfx_manager: VFXManager
    ) -> tuple[bool, bool]:
        """Spawn vfx on impact.
        
        The return values accumulate flags to either play or not play the hit and splash SFX,
        so that multiple SFX do not spawn when multiple impacts hit simultaneously.
        """
        if self.hull_type in ["SS", "CV"]:
            # SS and CV shipgirls produce a splash on impact and no vfx on miss.
            if hit:
                vfx_manager.spawn_splash_impact(target.rect.center)
                return False, True
            return False, False
    
        shell_type = self._shell_type
        start_pos = pygame.Vector2(rect.center)
        target_pos = pygame.Vector2(self.target.rect.center)
        relpos = target_pos - start_pos
        distance = relpos.length()
        scale = distance * SHELL_SCALE
        shell_angle = math.atan2(relpos.y, relpos.x)
        shell_incline = math.atan(relpos.x / abs(relpos.x) * scale)
        shell_render_angle = shell_angle + shell_incline
        # Shell-based shipgirls produce an explosion on hit and a splash on miss.
        if hit:
            vfx_manager.spawn_shell_impact(target.rect.center, shell_render_angle, shell_type)
            return True, False
        vfx_manager.spawn_splash_impact(target.rect.center)
        return False, True

    def _spawn_sfx(self):
        """Spawn sound effects on attack."""
        if self.hull_type == "CV":
            DataFiles.sfx["aircraft"].play()
            return
        if self.hull_type == "SS":
            return

        DataFiles.sfx["boom"].play()
        zip = DataFiles.sfx["zip"]
        zip.play(fade_ms=1000)
        zip.fadeout(1000)

    def attack(self, rect: pygame.Rect, vfx_manager: VFXManager):
        """On attack hook."""
        if not self.attack_animation:
            return
        self.cooldown_timer = 1
        self.attack_animation = False
        self.attack_timer = 1

        self._spawn_attacking_effects(rect, vfx_manager)
        self.shake()

        self._spawn_sfx()

    def update(self, dt: float, rect: pygame.Rect, fleet: PlayerFleet | SirenFleet, vfx_manager: VFXManager):
        """Update the shipgirl battle component."""
        self.shake_time = max(0, self.shake_time - dt)

        # Exp bar animation.
        if self.last_exp < self.exp:
            self.exp_timer += dt
            exp_animation = self.last_exp + (self.exp - self.last_exp) * self.exp_timer
            new_level = Stats.level(exp_animation)
            if self.last_level < new_level:
                DataFiles.sfx["scale"].play()
                self.level_timer = 1
                self.last_level = new_level
            if self.exp_timer > 1:
                self.last_exp = self.exp
                self.exp_timer = 1
        elif self.exp_timer > 0:
            self.exp_timer -= dt
            if self.exp_timer < 0:
                self.exp_timer = 0
        self.level_timer = max(self.level_timer - dt, 0)

        if not self.active:
            return
        
        self._update_ignite(dt, rect, vfx_manager)
        if self.ignite_ticks > 0:
            vfx_manager.spawn_fire(rect)

        if self.attack_animation:
            return

        # The attack is in progress.
        if self.attack_timer > 0:
            start_pos = pygame.Vector2(rect.center)
            target_pos = pygame.Vector2(self.target.rect.center)
            relpos = target_pos - start_pos
            distance = relpos.length()
            old_distance = self.attack_timer * distance
            self.attack_timer = max(0, self.attack_timer - self._attack_speed / distance * dt)
            new_distance = self.attack_timer * distance
            # Play the sonar sfx when the torpedo is a certain distance away from the target.
            if self.hull_type in ["SS", "CV"] and old_distance > self.SONAR_DISTANCE >= new_distance:
                DataFiles.sfx["sonar"].play()


            if self.attack_timer <= 0:
                if self.target_pref == "all":
                    # This siren attacks all shipgirls.
                    for shipgirl in fleet.shipgirls:
                        if shipgirl is None:
                            continue

                        hit = self._deal_damage(shipgirl, vfx_manager)
                        play_shell_impact, play_splash_impact = self._spawn_impact_effects(hit, rect, shipgirl, vfx_manager)
                else:
                    # This shipgirl/siren hits only the target.
                    hit = self._deal_damage(self.target, vfx_manager)
                    play_shell_impact, play_splash_impact = self._spawn_impact_effects(hit, rect, self.target, vfx_manager)

                # Play accumulated sfx, so they are not played multiple times if multiple
                # impacts occur simultaneously.
                if play_shell_impact:
                    DataFiles.sfx["boom2"].play()
                if play_splash_impact:
                    DataFiles.sfx["boom3"].play()
            return

        # Allow sirens to change new targets when the shipgirl they were targeting is sunk.
        if (
            self.target_pref != "all"
            and self.target is not None
            and self.target.battle_component.hp <= 0
        ):
            self.target = None

        # Automatically attack the target when off-cooldown.
        reload_speed = self.stat("reload") / 1000
        self.cooldown_timer = max(0, self.cooldown_timer - reload_speed * dt)
        if self.target is not None and self.cooldown_timer <= 0:
            self.attack_animation = True

    def _draw_attack(self, surface: pygame.Surface, rect: pygame.Rect, vfx_manager: VFXManager):
        """Helper to draw the attack based on the hull type."""
        t = 1 - self.attack_timer

        if self.hull_type == "CV":
            # CV shipgirls get a unique aircraft sprite that is launched and eventually
            # goes off-screen.
            start_pos = pygame.Vector2(rect.center)
            target_pos = pygame.Vector2(self.target.rect.center)
            relpos = target_pos - start_pos
            direction = relpos.normalize()

            aircraft_relpos = screen_x(1) * direction
            torpedo_launch_pos = target_pos - self.SONAR_DISTANCE * direction
            distance_ratio = (torpedo_launch_pos - start_pos).length() / aircraft_relpos.length()
            aircraft_sprite = pygame.transform.flip(
                DataFiles.sprites["encounter"]["aircraft"],
                flip_x=relpos.x < 0,
                flip_y=False
            )
            aircraft_rect = aircraft_sprite.get_rect()
            # Sigmoid curve.
            max_aircraft_height = 128
            horizontal_stretch = 20
            horizontal_offset = 0.1
            aircraft_height = max_aircraft_height / (1 + math.exp(-horizontal_stretch * (t - distance_ratio - horizontal_offset)))
            aircraft_rect.center = start_pos + aircraft_relpos * t - pygame.Vector2(0, aircraft_height)
            surface.blit(aircraft_sprite, aircraft_rect)

            # The aircraft will release the torpedo when it is in the sonar distance
            # and pull upwards.
            if t < distance_ratio:
                return
            # Normalize t to [0.5, 1].
            t = 0.5 * (t - distance_ratio) / (1 - distance_ratio) + 0.5
        
        if self.hull_type in ["SS", "CV"]:
            # Both SS and CV shipgirls draw a torpedo, though the CV shipgirl only
            # draws the torpedo once it has been released by the aircraft.
            # The torpedo also has a torpedo wake vfx.
            start_pos = pygame.Vector2((rect.centerx, rect.bottom))
            target_pos = pygame.Vector2((self.target.rect.centerx, self.target.rect.bottom))
            relpos = target_pos - start_pos
            torpedo_angle = math.atan2(relpos.y, relpos.x)
            torpedo_sprite = pygame.transform.rotate(DataFiles.sprites["encounter"]["torpedo"], -math.degrees(torpedo_angle))
            torpedo_rect = torpedo_sprite.get_rect()
            torpedo_pos = start_pos + relpos * t
            torpedo_rect.center = torpedo_pos
            surface.blit(torpedo_sprite, torpedo_rect)
            wake_pos = torpedo_pos - relpos.normalize() * 12
            vfx_manager.spawn_wake(wake_pos, torpedo_angle)
            return

        # Shell-based hull types draw an oval-shaped shell, colored based on the shell type.
        # The shell travels through a parabolic arc.
        start_pos = pygame.Vector2(rect.center)
        target_pos = pygame.Vector2(self.target.rect.center)
        relpos = target_pos - start_pos
        distance = relpos.length()
        scale = distance * SHELL_SCALE
        shell_pos = shell_path(start_pos, target_pos, t)
        # TODO If the shell_path helper is pulled out, this calculation can be placed there as well.
        # Even though it is not re-used, it would be nice to centralize this derivative calculation
        # so the two remain in sync.
        shell_incline = math.degrees(math.atan(relpos.x / abs(relpos.x) * scale * (2 * t - 1)))
        shell_angle = math.degrees(math.atan2(relpos.y, relpos.x))
        render_angle = shell_angle + shell_incline

        shell_type = self._shell_type
        shell_sprite = pygame.transform.flip(
            pygame.transform.rotate(DataFiles.sprites["encounter"][f"{shell_type}_shell"], render_angle),
            False, True
        )
        shell_rect = shell_sprite.get_rect()
        shell_rect.center = shell_pos
        surface.blit(shell_sprite, shell_rect)

    def draw_battlestation(self, surface: pygame.Surface, font_registry: dict[str, Font], rect: pygame.Surface):
        """Draw the shipgirl's battlestation."""
        if self.hp <= 0:
            return

        # Draw the rigging and the battlestation glow, which is a cone opening upwards
        # with a light falloff like a hologram projection.
        if self.is_player:
            rigging_sprite = DataFiles.sprites["encounter"]["shipgirl_rigging"]
            rigging_rect = rigging_sprite.get_rect()
            rigging_rect.left = rect.left
            rigging_rect.centery = rect.centery + rigging_rect.height / 3
            battlestation_glow = DataFiles.sprites["encounter"]["shipgirl_battlestation_glow"]
            battlestation_glow_rect = battlestation_glow.get_rect()
            battlestation_glow_rect.centerx = rigging_rect.centerx - Box.WIDTH / 4
        else:
            rigging_sprite = DataFiles.sprites["encounter"]["siren_rigging"]
            rigging_rect = rigging_sprite.get_rect()
            rigging_rect.right = rect.right
            rigging_rect.centery = rect.centery + rigging_rect.height / 3
            battlestation_glow = DataFiles.sprites["encounter"]["siren_battlestation_glow"]
            battlestation_glow_rect = battlestation_glow.get_rect()
            battlestation_glow_rect.centerx = rigging_rect.centerx + Box.WIDTH / 4
        battlestation_glow_rect.bottom = rigging_rect.centery
        surface.blit(rigging_sprite, rigging_rect)
        pulse = (math.sin(self.battlestation_effect_time * math.tau / self.BATTLESTATION_PULSE_DURATION) + 1) / 2
        battlestation_alpha = int(192 + 63 * pulse)
        battlestation_glow = battlestation_glow.copy()
        battlestation_glow.set_alpha(battlestation_alpha)
        pulsing_glow = pygame.Surface(battlestation_glow.get_size())
        pulsing_glow.blit(battlestation_glow, (0, 0))
        surface.blit(
            pulsing_glow,
            battlestation_glow_rect,
            special_flags=pygame.BLEND_RGB_ADD,
        )

        # TODO Consider whether or not this can be pulled into a project-scoped common or even into engine, if it is
        # useful enough.
        # Glint particle effects.
        vertical_spawn_range = (
            battlestation_glow_rect.height - 2 * self.BATTLESTATION_GLINT_MARGIN
        )
        for glint_index in range(self.BATTLESTATION_GLINT_COUNT):
            glint_time = (
                self.battlestation_effect_time
                + glint_index
                * self.BATTLESTATION_GLINT_CYCLE
                / self.BATTLESTATION_GLINT_COUNT
            )
            glint_age = glint_time % self.BATTLESTATION_GLINT_CYCLE
            if glint_age >= self.BATTLESTATION_GLINT_LIFETIME:
                continue

            cycle_index = math.floor(glint_time / self.BATTLESTATION_GLINT_CYCLE)
            glint_progress = glint_age / self.BATTLESTATION_GLINT_LIFETIME
            glint_strength = (1 - glint_progress) ** 1.5
            spawn_y = (
                self.BATTLESTATION_GLINT_MARGIN
                + (cycle_index * 19 + glint_index * 31) % vertical_spawn_range
            )
            y_ratio = spawn_y / (battlestation_glow_rect.height - 1)
            cone_width = round(
                battlestation_glow_rect.width
                - (battlestation_glow_rect.width - 2) * y_ratio
            )
            half_spawn_width = cone_width / 2 - self.BATTLESTATION_GLINT_MARGIN
            spawn_x = (
                (cycle_index * 29 + glint_index * 17) % (2 * half_spawn_width)
                - half_spawn_width
            )
            spawn_center = pygame.Vector2(
                battlestation_glow_rect.centerx + spawn_x,
                battlestation_glow_rect.top + spawn_y,
            )
            glint_center = spawn_center - pygame.Vector2(
                0,
                self.BATTLESTATION_GLINT_DRIFT * glint_progress,
            )
            if glint_center.y < battlestation_glow_rect.top:
                continue
            self._draw_battlestation_glint(
                surface,
                glint_center,
                Color.HOLOGRAM_GLOW if self.is_player else Color.SIREN_HOLOGRAM_GLOW,
                glint_strength,
            )
        if self.is_player:
            # The player battlestation includes the reload gauge, hp, and exp bar.
            reload_gauge_size = 48
            battlestation_back = pygame.Surface((battlestation_glow_rect.width, reload_gauge_size + 2 * Box.PADDING))
            battlestation_panel_color = Color.HOLOGRAM_GLOW
        else:
            # The siren battlestation includes the level, siren name, and hp bar.
            siren_id_size = 24
            hp_bar_size = 16
            battlestation_back = pygame.Surface((battlestation_glow_rect.width, siren_id_size + hp_bar_size + 3 * Box.PADDING))
            battlestation_panel_color = Color.SIREN_HOLOGRAM_GLOW
        battlestation_rect = battlestation_back.get_rect()
        battlestation_rect.midbottom = battlestation_glow_rect.midtop
        battlestation_back.fill([c // 3 for c in battlestation_panel_color])

        # This is the panel for the hp bar.
        hull_sprite = pygame.transform.flip(
            DataFiles.sprites["encounter"]["hull"],
            flip_x=not self.is_player, flip_y=False
        )
        hull_rect = hull_sprite.get_rect()
        if self.is_player:
            hull_rect.right = battlestation_rect.width - Box.PADDING
            hull_rect.bottom = battlestation_rect.height - Box.PADDING
        else:
            hull_rect.centerx = battlestation_rect.width / 2
            hull_rect.bottom = battlestation_rect.height - Box.PADDING
        hull_panel_rect = hull_rect.inflate(Box.PADDING, Box.PADDING)
        pygame.draw.rect(battlestation_back, [c // 2 for c in battlestation_panel_color], hull_panel_rect)
        pygame.draw.rect(battlestation_back, battlestation_panel_color, hull_panel_rect, width=Box.OUTLINE_WIDTH)

        if self.is_player:
            # Panel for the exp bar.
            star_icon = DataFiles.sprites["encounter"]["star"]
            star_rect = star_icon.get_rect()
            bar_width = 56
            bar_height = 8
            bar_background = get_rect(
                width=bar_width, height=bar_height,
                right=battlestation_rect.width - Box.PADDING,
                centery=Box.PADDING + star_rect.height / 2
            )
            star_rect.center = bar_background.midleft
            exp_panel_rect = bar_background.union(star_rect).inflate(Box.PADDING, Box.PADDING)
            pygame.draw.rect(battlestation_back, [c // 2 for c in battlestation_panel_color], exp_panel_rect)
            pygame.draw.rect(battlestation_back, battlestation_panel_color, exp_panel_rect, width=Box.OUTLINE_WIDTH)

            # Panel for the reload gauge.
            outer_radius = 24
            center = (
                pygame.Vector2(outer_radius, outer_radius)
                + pygame.Vector2(Box.PADDING, Box.PADDING)
            )
            reload_panel_rect = get_rect(
                width=2 * outer_radius + Box.PADDING,
                height=2 * outer_radius + Box.PADDING,
                centerx=center.x,
                centery=center.y,
            )
            pygame.draw.rect(battlestation_back, [c // 2 for c in battlestation_panel_color], reload_panel_rect)
            pygame.draw.rect(battlestation_back, battlestation_panel_color, reload_panel_rect, width=Box.OUTLINE_WIDTH)
        else:
            # Panel for the siren info i.e. level and name.
            siren_info_panel = get_rect(
                width=battlestation_rect.width - Box.PADDING,
                height=siren_id_size,
                centerx=battlestation_rect.width / 2,
                top=Box.PADDING / 2,
            )
            pygame.draw.rect(battlestation_back, [c // 2 for c in battlestation_panel_color], siren_info_panel)
            pygame.draw.rect(battlestation_back, battlestation_panel_color, siren_info_panel, width=Box.OUTLINE_WIDTH)

        battlestation_surf = pygame.Surface(battlestation_back.get_size(), flags=pygame.SRCALPHA)

        # Draw the hp bar, which is stylized as the side silhouette of a hull.
        hp_pct = self.hp / self.stat("max_hp")
        hull_back = pygame.transform.flip(
            DataFiles.recolor_sprite("encounter", "hull", Color.EXP_BAR_BG),
            flip_x=not self.is_player, flip_y=False
        )
        battlestation_surf.blit(hull_back, hull_rect)

        hp_bar_color = (0, 255, 205) if self.is_player else (255, 0, 50)
        hull_fill = pygame.transform.flip(
            DataFiles.recolor_sprite("encounter", "hull", hp_bar_color),
            flip_x=not self.is_player, flip_y=False
        )
        missing_hp_rect = get_rect(width=hull_rect.width * (1 - hp_pct), height=hull_rect.height, left=0, top=0)
        if self.is_player:
            missing_hp_rect.right = hull_rect.width
        pygame.draw.rect(hull_fill, (255, 0, 0), missing_hp_rect)
        battlestation_surf.blit(hull_fill, hull_rect)

        if not self.is_player:
            # Draw the level and name for the siren.
            star_icon = DataFiles.sprites["encounter"]["star"]
            star_rect = star_icon.get_rect(
                topleft=(Box.PADDING, Box.PADDING)
            )
            battlestation_surf.blit(star_icon, star_rect)
            font_registry["pixel"].render(
                battlestation_surf,
                str(Stats.level(self.exp)),
                star_rect.center,
                Color.WHITE,
                scale=1,
                style="center",
                outline_color=Color.BLACK,
            )
            font_registry["big_pixel"].render(
                battlestation_surf,
                f"{self.name} [{self.hull_type}]",
                (star_rect.right + Box.PADDING, star_rect.centery),
                Color.WHITE,
                scale=1,
                style="centerleft",
                outline_color=Color.BLACK,
            )

            # Use additive rendering for the battlestation panel.
            battlestation_back.set_alpha(battlestation_alpha)
            pulsing_battlestation_back = pygame.Surface(battlestation_back.get_size())
            pulsing_battlestation_back.blit(battlestation_back, (0, 0))
            surface.blit(
                pulsing_battlestation_back,
                battlestation_rect,
                special_flags=pygame.BLEND_RGB_ADD,
            )
            # The battlestation content has an opacity which matches the pulsing.
            battlestation_surf.set_alpha(battlestation_alpha)
            pulsing_battlestation_surf = pygame.Surface(battlestation_surf.get_size(), flags=pygame.SRCALPHA)
            pulsing_battlestation_surf.blit(battlestation_surf, (0, 0))
            surface.blit(
                pulsing_battlestation_surf,
                battlestation_rect,
            )
            return

        # Draw the exp bar with a sliding animation.
        exp_animation = self.last_exp + (self.exp - self.last_exp) * self.exp_timer
        bar_fill = get_rect(
            width=bar_width * Stats.level_progress(exp_animation), height=bar_background.height,
            left=bar_background.left, top=bar_background.top
        )
        pygame.draw.rect(battlestation_surf, Color.EXP_BAR_BG, bar_background)
        pygame.draw.rect(battlestation_surf, Color.EXP_BAR_FILL, bar_fill)
        battlestation_surf.blit(star_icon, star_rect)
        font_registry["pixel"].render(
            battlestation_surf,
            str(self.last_level),
            star_rect.center,
            Color.WHITE,
            scale=1,
            style="center",
            outline_color=Color.BLACK
        )

        if self.level_timer > 0:
            t = 1 - self.level_timer
            y = rect.top - rect.height * t
            font_registry["big_pixel"].render(surface, "level up!", (rect.centerx, y), Color.WHITE, scale=1, style="center")

        # Draw the reload gauge.
        inner_radius = 12
        start_angle = -90
        stop_angle = start_angle + (1 - self.cooldown_timer) * 360
        gauge_color = (50, 200, 50) if self.target is not None else (200, 50, 50)
        draw_annulus(battlestation_surf, Color.EXP_BAR_BG, center, inner_radius + 1, outer_radius - 1, start_angle=0, stop_angle=360)
        draw_annulus(battlestation_surf, gauge_color, center, inner_radius, outer_radius, start_angle, stop_angle)
        if self.hull_type == "CV":
            attack_icon = DataFiles.sprites["user_interface"]["air_attack"]
        elif self.hull_type == "SS":
            attack_icon = DataFiles.sprites["user_interface"]["torp_attack"]
        else:
            attack_icon = DataFiles.sprites["user_interface"]["shell_attack"]
        attack_icon_rect = attack_icon.get_rect()
        attack_icon_rect.center = center
        battlestation_surf.blit(attack_icon, attack_icon_rect)

        # Use additive rendering for the battlestation panel.
        battlestation_back.set_alpha(battlestation_alpha)
        pulsing_battlestation_back = pygame.Surface(battlestation_back.get_size())
        pulsing_battlestation_back.blit(battlestation_back, (0, 0))
        surface.blit(
            pulsing_battlestation_back,
            battlestation_rect,
            special_flags=pygame.BLEND_RGB_ADD,
        )
        # The battlestation content has an opacity which matches the pulsing.
        battlestation_surf.set_alpha(battlestation_alpha)
        pulsing_battlestation_surf = pygame.Surface(battlestation_surf.get_size(), flags=pygame.SRCALPHA)
        pulsing_battlestation_surf.blit(battlestation_surf, (0, 0))
        surface.blit(
            pulsing_battlestation_surf,
            battlestation_rect,
        )

    # TODO Consider whether this is repeated code and all glint drawing helpers are similar.
    def _draw_battlestation_glint(
        self, surface: pygame.Surface, center: CoordinateType, color: ColorType, strength: float
    ):
        """Draw the glint particle effects for the battlestation."""
        glint_length = 1 + round(
            (self.BATTLESTATION_GLINT_MAX_LENGTH - 1) * strength
        )
        glint_color = tuple(round(channel * strength) for channel in color)
        glint_surface = pygame.Surface(
            (
                2 * self.BATTLESTATION_GLINT_MAX_LENGTH + 1,
                2 * self.BATTLESTATION_GLINT_MAX_LENGTH + 1,
            )
        )
        glint_surface_center = pygame.Vector2(
            self.BATTLESTATION_GLINT_MAX_LENGTH,
            self.BATTLESTATION_GLINT_MAX_LENGTH,
        )
        pygame.draw.line(
            glint_surface,
            glint_color,
            glint_surface_center - pygame.Vector2(glint_length, 0),
            glint_surface_center + pygame.Vector2(glint_length, 0),
        )
        pygame.draw.line(
            glint_surface,
            glint_color,
            glint_surface_center - pygame.Vector2(0, glint_length),
            glint_surface_center + pygame.Vector2(0, glint_length),
        )
        surface.blit(
            glint_surface,
            glint_surface.get_rect(center=center),
            special_flags=pygame.BLEND_RGB_ADD,
        )

    def draw_effects(self, surface: pygame.Surface, rect: pygame.Rect, vfx_manager: VFXManager):
        """Draw battle component effects.
        
        Effects like attack and attack effects, smokescreen effects, target indicators.
        """
        if not self.active:
            return
        if self.attack_timer > 0:
            self._draw_attack(surface, rect, vfx_manager)
        if self.evasion_gauge >= 1:
            self.smokescreen.draw(surface, rect)
        if not self.is_player:
            return

        # Draw target indicator.
        if self.target is not None:
            target_color = (
                Color.TARGET_INDICATOR if self.attack_animation or self.attack_timer > 0
                else Color.MUTED_TARGET_INDICATOR
            )
            dash_length = 8
            dash_width = 2
            if self.hull_type in ["DD", "CL", "CA", "BB"]:
                # Target line is from center to center.
                start_pos = pygame.Vector2(rect.center)
                curr_pos = start_pos
                end_pos = pygame.Vector2(self.target.rect.center)
            else:
                # Target line is from midbottom to midbottom.
                start_pos = pygame.Vector2(rect.centerx, rect.bottom - rect.height / 5)
                curr_pos = start_pos
                target_rect = self.target.rect
                end_pos = pygame.Vector2(target_rect.centerx, target_rect.bottom - target_rect.height / 5)
            distance = (end_pos - start_pos).length()
            # Draw the dashed target line.
            for dash_start in range(0, round(distance), 2 * dash_length):
                start_t = dash_start / distance
                end_t = min((dash_start + dash_length) / distance, 1)
                if self.hull_type in ["DD", "CL", "CA", "BB"]:
                    # Target line is parabolic for these hull types.
                    curr_pos = shell_path(start_pos, end_pos, start_t)
                    dash_end_pos = shell_path(start_pos, end_pos, end_t)
                else:
                    # Target line is straight for these hull types.
                    curr_pos = start_pos.lerp(end_pos, start_t)
                    dash_end_pos = start_pos.lerp(end_pos, end_t)
                parallel = (dash_end_pos - curr_pos).normalize()
                perpendicular = pygame.Vector2(parallel.y, -parallel.x)
                # TODO Consider whether dash drawing helpers are repeated code.
                polygon = [
                    curr_pos + dash_width / 2 * perpendicular,
                    dash_end_pos + dash_width / 2 * perpendicular,
                    dash_end_pos - dash_width / 2 * perpendicular,
                    curr_pos - dash_width / 2 * perpendicular,
                ]
                pygame.draw.polygon(
                    surface,
                    target_color,
                    polygon,
                )

            # Draw the reticle.
            reticle_size = 24
            duplex_size = 16
            pygame.draw.circle(surface, target_color, end_pos, reticle_size, 2)
            for line_start, line_end in [
                [(end_pos.x - reticle_size, end_pos.y), (end_pos.x + reticle_size, end_pos.y)],
                [(end_pos.x, end_pos.y - reticle_size), (end_pos.x, end_pos.y + reticle_size)]
            ]:
                pygame.draw.line(surface, target_color, line_start, line_end, width=1)
            for line_start, line_end in [
                [(end_pos.x - reticle_size, end_pos.y), (end_pos.x - reticle_size + duplex_size, end_pos.y)],
                [(end_pos.x + reticle_size, end_pos.y), (end_pos.x + reticle_size - duplex_size, end_pos.y)],
                [(end_pos.x, end_pos.y - reticle_size), (end_pos.x, end_pos.y - reticle_size + duplex_size)],
                [(end_pos.x, end_pos.y + reticle_size), (end_pos.x, end_pos.y + reticle_size - duplex_size)]
            ]:
                pygame.draw.line(surface, target_color, line_start, line_end, width=3)

class Shipgirl:
    def __init__(self, name: str, is_player: bool):
        if is_player:
            self.name = name
        else:
            # Siren keys are formatted as name:level
            self.name = name.split(":")[0]

        # Wander and interaction state.
        self.pos = self._get_random_floor_pos()
        self.wander_target = self.pos.copy()
        self.pause_time = 0
        self.interacting_decoration: CoordinateType = None

        # Get the sprite if it exists and otherwise fall back to TB.
        model_file = get_live2d_model_file(self.name)
        self.sprite = PreRenderLive2D(model_file) if model_file is not None else None
        self.facing_left = False

        self.rect = get_rect(width=LAYER_SIZE, height=LAYER_SIZE, center=self.pos)

        self.battle_component = ShipgirlBattleComponent(name, is_player)

    def __repr__(self):
        return self.name

    @staticmethod
    def _get_random_floor_pos() -> pygame.Vector2:
        """Get a random position on the port floor."""
        iso_x = random.uniform(-1, Decorations.FLOOR_TILES_WIDE - 1)
        iso_y = random.uniform(-1, Decorations.FLOOR_TILES_TALL - 1)
        return pygame.Vector2(Decorations.get_isometric_floor_pos((iso_x, iso_y)))

    def clamp_to_floor_bounds(self):
        """Push the shipgirl's position inside the port wandering bounds."""
        rel_x = self.pos.x - Decorations.floor_rect.left - Decorations.floor_rect.width / 2
        rel_y = self.pos.y - Decorations.floor_rect.top
        iso_x = (
            rel_y / Decorations.ISO_HALF_TILE_HEIGHT
            + rel_x / Decorations.ISO_HALF_TILE_WIDTH
        ) / 2 - 1
        iso_y = (
            rel_y / Decorations.ISO_HALF_TILE_HEIGHT
            - rel_x / Decorations.ISO_HALF_TILE_WIDTH
        ) / 2 - 1
        iso_x = max(-1, min(iso_x, Decorations.FLOOR_TILES_WIDE - 1))
        iso_y = max(-1, min(iso_y, Decorations.FLOOR_TILES_TALL - 1))
        self.pos = Decorations.get_isometric_floor_pos((iso_x, iso_y))
        self.rect.centerx = self.pos.x
        self.rect.bottom = self.pos.y + self.rect.height / 8

    def pick_new_wander_target(self):
        """Pick a new wander target and pause time."""
        self.wander_target = self._get_random_floor_pos()
        self.pause_time = random.uniform(1, 3)

    def update(self, dt: float):
        """Update the shipgirl for the port."""
        if self.sprite.animation == Live2D.BOUNCE_ANIMATION:
            return
        
        if self.interacting_decoration is not None:
            return
        
        if self.pause_time > 0:
            self.pause_time -= dt
            self.sprite.set_animation(Live2D.IDLE_ANIMATION)
        else:
            # Wandering logic.
            to_target = self.wander_target - self.pos
            reached_target_tolerance = 10
            if to_target.length() < reached_target_tolerance:
                self.pick_new_wander_target()
            else:
                direction = to_target.normalize()
                walking_speed = 50
                self.pos += direction * walking_speed * dt
                if direction.x >= 0:
                    self.facing_left = False
                else:
                    self.facing_left = True
            
            self.sprite.set_animation(Live2D.WALK_ANIMATION)
        self.rect.centerx = self.pos.x
        self.rect.bottom = self.pos.y + self.rect.height / 8

    def animate(self, dt: float):
        """Animate the sprite."""
        self.battle_component.battlestation_effect_time += dt
        if self.battle_component.evasion_gauge >= 1:
            self.battle_component.smokescreen.update(dt)
        self.sprite.update(dt)

    def draw(self, surface: pygame.Surface, font_registry: dict[str, Font], alpha: int = 255):
        """Draw the sprite with shake."""
        shake_amt = 4
        shake_speed = 4 * math.radians(360)
        shake_offset = shake_amt * math.sin(shake_speed * self.battle_component.shake_time)
        self.sprite.draw(surface, self.rect.centerx + shake_offset, self.rect.centery, not self.facing_left, alpha=alpha)


ATTACK_ANIMATION_ATTACK_TIMING = 2.5 * Live2D.KEYFRAME_DURATION


class PlayerFleet:
    def __init__(self):
        self.shipgirls: tuple[Shipgirl | None, Shipgirl | None, Shipgirl | None] = [None, None, None]
        self.backups: tuple[Shipgirl | None, Shipgirl | None, Shipgirl | None] = [None, None, None]
    
    @property
    def afloat(self) -> bool:
        """Check if any shipgirl in the fleet is still afloat."""
        return any(
            shipgirl is not None and shipgirl.battle_component.hp > 0
            for shipgirl in self.shipgirls + self.backups
        )

    @property
    def primary_fleet_size(self) -> int:
        """Get the size of the primary fleet, ignoring None shipgirls."""
        return len([shipgirl for shipgirl in self.shipgirls if shipgirl is not None])

    @property
    def backup_fleet_size(self) -> int:
        """Get the size of the backup fleet, ignoring None shipgirls."""
        return len([shipgirl for shipgirl in self.backups if shipgirl is not None])

    @property
    def fleet(self) -> list[Shipgirl]:
        return [shipgirl for shipgirl in self.shipgirls + self.backups if shipgirl is not None]

    @property
    def front(self) -> Shipgirl | None:
        """Get the front-most shipgirl in the primary fleet."""
        for shipgirl in self.shipgirls:
            if shipgirl is not None and shipgirl.battle_component.hp > 0:
                return shipgirl
        return None

    @property
    def highest_hp(self) -> Shipgirl | None:
        """Get the shipgirl in th eprimary fleet with the highest max hp."""
        shipgirl_with_highest_hp = None
        for shipgirl in self.shipgirls:
            if shipgirl is None:
                continue
            if shipgirl.battle_component.hp <= 0:
                continue
            if shipgirl_with_highest_hp is None:
                shipgirl_with_highest_hp = shipgirl
            elif shipgirl.battle_component.stat("max_hp") > shipgirl_with_highest_hp.battle_component.stat("max_hp"):
                shipgirl_with_highest_hp = shipgirl
        return shipgirl_with_highest_hp

    def in_fleet(self, shipgirl: Shipgirl) -> bool:
        """Get whether or not the shipgirl is in the primary or backup fleet."""
        return shipgirl in self.fleet

    def clear_fleet(self):
        """Clear the primary and backup fleets."""
        self.shipgirls = [None, None, None]
        self.backups = [None, None, None]

    def begin_sortie(self):
        """Reset the battle components on sortie start."""
        for shipgirl in self.fleet:
            shipgirl.battle_component.reset()

    def begin_encounter(self):
        """Activate battle components on encounter start."""
        for shipgirl in self.shipgirls:
            if shipgirl is not None:
                shipgirl.battle_component.active = True

    def end_encounter(self):
        """Deactivate battle components on encounter end."""
        for shipgirl in self.shipgirls:
            if shipgirl is not None:
                shipgirl.battle_component.target = None
                shipgirl.battle_component.attack_animation = False
                shipgirl.battle_component.attack_timer = 0
                shipgirl.battle_component.active = False

    def animate(self, dt: float):
        """Animate the shipgirls in the player fleet.
        
        Set animations based on battle component state.
        """
        for shipgirl in self.fleet:
            if shipgirl.battle_component.hp <= 0:
                shipgirl.sprite.set_animation(Live2D.SINK_ANIMATION)
            elif shipgirl.battle_component.attack_animation:
                shipgirl.sprite.set_animation(Live2D.ATTACK_ANIMATION)
            shipgirl.animate(dt)

    def update(self, dt: float, vfx_manager: VFXManager):
        """Update the shipgirl battle components in the player fleet."""
        for shipgirl in self.fleet:
            if shipgirl.battle_component.hp <= 0:
                shipgirl.battle_component.active = False
            elif shipgirl.battle_component.attack_animation:
                if shipgirl.sprite.t > ATTACK_ANIMATION_ATTACK_TIMING:
                    shipgirl.battle_component.attack(shipgirl.rect, vfx_manager)
            shipgirl.battle_component.update(dt, shipgirl.rect, None, vfx_manager)

    def get_draw_indices(self):
        """Get the draw indices for each shipgirl in the primary and backup fleets."""
        fixed_draw_indices = [1, 3, 5]
        return [
            (fixed_index, shipgirl)
            for fixed_index, shipgirl in zip(fixed_draw_indices, self.shipgirls)
            if shipgirl is not None
        ] + [
            (fixed_index, shipgirl)
            for fixed_index, shipgirl in zip(fixed_draw_indices, self.backups)
            if shipgirl is not None
        ]


class SirenFleet:
    def __init__(self):
        self.front: list[Shipgirl] = []
        self.back: list[Shipgirl] = []

        self.dummy_target: DummyTarget | None = None
    
    @property
    def afloat(self) -> bool:
        """Check if any sirens are still afloat."""
        return any(siren.battle_component.hp > 0 for siren in self.fleet)

    @property
    def siren_names(self) -> list[str]:
        """Get the names of the sirens."""
        return [siren.name for siren in self.fleet]

    @property
    def afloat_front(self) -> list[Shipgirl]:
        """Get the front-most fleet that is afloat.
        
        If a siren from the front row is afloat, then return the front. Otherwise,
        return the back row.
        """
        return (
            [siren for siren in self.front if siren.battle_component.hp > 0]
            or [siren for siren in self.back if siren.battle_component.hp > 0]
        )

    @property
    def fleet(self) -> list[Shipgirl]:
        """Get the full front + back fleet."""
        return self.front + self.back

    def clear_fleet(self):
        """Clear the fleet."""
        self.front = []
        self.back = []

    def begin_encounter(self):
        """Activate siren battle components and align sirens to slot rects on encounter start."""
        for siren in self.fleet:
            siren.battle_component.active = True
        
        slot_size = LAYER_SIZE
        front_offset = (len(self.front) - 1) / 2
        x_anchor = screen_x(0.75)
        y_anchor = screen_y(0.5)
        for i, siren in enumerate(self.front):
            siren.rect.centerx = x_anchor - slot_size + (i - front_offset) * slot_size / 2
            siren.rect.centery = y_anchor + (i - front_offset) * slot_size
        
        back_offset = (len(self.back) - 1) / 2
        for i, siren in enumerate(self.back):
            siren.rect.centerx = x_anchor + slot_size + (i - back_offset) * slot_size / 2
            siren.rect.centery = y_anchor + (i - back_offset) * slot_size
    
    def end_encounter(self):
        """Deactivate battle components on encounter end."""
        for siren in self.fleet:
            siren.battle_component.target = None
            siren.battle_component.attack_animation = False
            siren.battle_component.attack_timer = 0
            siren.battle_component.active = False

    def animate(self, dt: float):
        """Animate the sirens in the fleet."""
        for siren in self.fleet:
            if siren.battle_component.hp <= 0:
                siren.sprite.set_animation(Live2D.SINK_ANIMATION)
            elif siren.battle_component.attack_animation:
                siren.sprite.set_animation(Live2D.ATTACK_ANIMATION)
            siren.animate(dt)

    def update(self, dt: float, menu_manager: MenuManager, vfx_manager: VFXManager):
        """Update the siren battle components."""
        # Create the dummy target if it does not exist.
        if self.dummy_target is None:
            self.dummy_target = DummyTarget(menu_manager)

        for siren in self.fleet:
            if siren.battle_component.target is None:
                # Use the siren's target pref to determine which shipgirl toa ttack
                # if the siren currently has no target.
                if siren.battle_component.target_pref == "highest_hp":
                    siren.battle_component.target = menu_manager.player_fleet.highest_hp
                elif siren.battle_component.target_pref == "all":
                    siren.battle_component.target = self.dummy_target
                else:
                    siren.battle_component.target = menu_manager.player_fleet.front
            if siren.battle_component.hp <= 0:
                siren.battle_component.active = False
            elif siren.battle_component.attack_animation:
                if siren.sprite.t > ATTACK_ANIMATION_ATTACK_TIMING:
                    siren.battle_component.attack(siren.rect, vfx_manager)
            siren.battle_component.update(dt, siren.rect, menu_manager.player_fleet, vfx_manager)

    def get_draw_indices(self):
        """Compute the draw indices of the sirens in the front and back.
        
        The sirens slot positions depend on how many sirens are in that row,
        rather than being fixed slot positions. This means that the siren will be
        rendered at different wave indices depending on how many sirens are in the
        row.
        """
        draw_indices = []
        if len(self.front) == 1:
            draw_indices.append((3, self.front[0]))
        elif len(self.front) == 2:
            draw_indices.append((2, self.front[0]))
            draw_indices.append((4, self.front[1]))
        elif len(self.front) == 3:
            draw_indices.append((1, self.front[0]))
            draw_indices.append((3, self.front[1]))
            draw_indices.append((5, self.front[2]))
        
        if len(self.back) == 1:
            draw_indices.append((3, self.back[0]))
        elif len(self.back) == 2:
            draw_indices.append((2, self.back[0]))
            draw_indices.append((4, self.back[1]))
        elif len(self.back) == 3:
            draw_indices.append((1, self.back[0]))
            draw_indices.append((3, self.back[1]))
            draw_indices.append((5, self.back[2]))
        
        return draw_indices
