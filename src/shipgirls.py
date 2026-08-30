import os
import math
import random
import pygame

from engine.util import get_rect, get_vec, draw_annulus

from src.constants import DataFiles, Color, Equipment, Box, Stats, screen_x, screen_y, Decorations
from src.vfx import shell_path, SHELL_SCALE
from live2d.live2d import Live2D

class Smoke:
    def __init__(self):
        num_smoke = 4
        self.offsets = [
            get_vec(random.uniform(16, 32), math.radians(random.randint(0, 359)))
            for _ in range(num_smoke)
        ]
        self.smoke_timers = [
            math.radians(random.randint(0, 359))
            for _ in range(num_smoke)
        ]
    
    def update(self, dt):
        self.smoke_timers = [
            (smoke_timer + dt)%math.radians(360)
            for smoke_timer in self.smoke_timers
        ]
    
    def draw(self, surface, rect):
        center = pygame.Vector2(rect.center)
        smoke_sprite = DataFiles.sprites["encounter"]["smoke"]
        smoke_rect = smoke_sprite.get_rect()
        for offset, smoke_timer in zip(self.offsets, self.smoke_timers):
            smoke_rect.center = (
                center
                + offset
                + pygame.Vector2(16*math.sin(smoke_timer), 8*math.sin(2*smoke_timer))
            )
            surface.blit(smoke_sprite, smoke_rect)

class DummyTarget:
    def __init__(self, menu_manager):
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

    def __init__(self, name, is_player):
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
            info["exp"] = int(Stats.EXP_BASE * (1 - Stats.EXP_GROWTH**int(level)) / (1 - Stats.EXP_GROWTH))

        self.name = name
        stat_keys = ["max_hp", "evasion", "firepower", "reload"]
        self.base_stats = {
            stat_key: info[stat_key]
            for stat_key in stat_keys
        }
        self.hull_type = info["hull_type"]
        self.equipment = info["equipment"]
        self.exp = info["exp"]
        if self.is_player:
            self.target_pref = None
        else:
            self.target_pref = info["target_pref"]
            self.reward_exp = info["reward_exp"]

        self.hp = self.stat("max_hp")
        self.cooldown_timer = 1
        self.attack_animation = False
        self.attack_timer = 0
        self.target = None
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

        self.evasion_smoke = Smoke()

    def shake(self):
        self.shake_time = 0.5

    def stat(self, stat):
        return (
            Stats.stat(*self.base_stats[stat], exp=self.exp)
            + sum(
                DataFiles.equipment_data.get(equipment, {}).get(stat, 0)
                for equipment in self.equipment
            )
        )

    def gain_exp(self, amount):
        previous_max_hp = self.stat("max_hp")
        self.exp += amount
        self.hp += self.stat("max_hp") - previous_max_hp

    def attack_speed(self):
        if self.hull_type == "CV":
            return self.AIRCRAFT_SPEED + DataFiles.equipment_data.get(self.equipment[Equipment.WEAPON], {}).get("aircraft_speed", 0)
        if self.hull_type == "SS":
            return self.TORPEDO_SPEED + DataFiles.equipment_data.get(self.equipment[Equipment.WEAPON], {}).get("torpedo_speed", 0)
        return self.SHELL_SPEED + DataFiles.equipment_data.get(self.equipment[Equipment.WEAPON], {}).get("shell_speed", 0)

    def shell_type(self):
        if self.hull_type in ["SS", "CV"]:
            return "torpedo"
        weapon_config = DataFiles.equipment_data.get(self.equipment[Equipment.WEAPON], {})
        return weapon_config.get("shell_type", "normal")

    def reset(self):
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

    def ignite(self, damage, ticks):
        self.ignite_timer = 0
        self.ignite_ticks = ticks
        self.ignite_damage = damage

    def _update_ignite(self, dt, rect, vfx_manager):
        if self.ignite_ticks <= 0:
            return

        self.ignite_timer += dt
        agg_ignite_damage = 0
        while self.ignite_timer >= 1:
            self.ignite_timer -= 1
            self.ignite_ticks -= 1
            agg_ignite_damage += 1

            if self.ignite_ticks <= 0:
                self.ignite_timer = 0
        if agg_ignite_damage > 0:
            self.hp -= agg_ignite_damage
            vfx_manager.spawn_damage_counter(rect.midtop, agg_ignite_damage, "HE")
            self.shake()

    def _deal_damage(self, target, vfx_manager):
        if target.battle_component.evasion_gauge >= 1:
            target.battle_component.evasion_gauge -= 1
            vfx_manager.spawn_miss_counter(target.rect.midtop)
            return False
        else:
            target.battle_component.evasion_gauge += target.battle_component.stat("evasion") / 1000
            weapon_config = DataFiles.equipment_data.get(self.equipment[Equipment.WEAPON], {})
            shell_type = self.shell_type()
            damage = self.stat("firepower")
            crit = False
            if shell_type == "AP":
                crit_chance = weapon_config.get("crit_chance", 10)
                if random.randint(0, 99) < crit_chance:
                    crit = True
                    damage *= weapon_config.get("crit_mult", 2)
            target.battle_component.hp -= damage
            vfx_manager.spawn_damage_counter(target.rect.midtop, damage, shell_type, crit)
            if shell_type == "HE":
                ignite_chance = weapon_config.get("ignite_chance", 20)
                if random.randint(0, 99) < ignite_chance:
                    target.battle_component.ignite(
                        weapon_config.get("ignite_damage", 1),
                        weapon_config.get("ignite_ticks", 5),
                    )
            target.battle_component.shake()
            return True

    def _spawn_attacking_effects(self, rect, vfx_manager):
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
        shell_type = self.shell_type()
        relpos = target_pos - start_pos
        distance = relpos.length()
        scale = distance * SHELL_SCALE
        shell_angle = math.atan2(relpos.y, relpos.x)
        shell_incline = math.atan(-relpos.x / abs(relpos.x) * scale)
        shell_render_angle = shell_angle + shell_incline
        vfx_manager.spawn_muzzle_flash(start_pos, shell_render_angle, shell_type)

    def _spawn_impact_effects(self, hit, rect, target, vfx_manager):
        if self.hull_type in ["SS", "CV"]:
            if hit:
                vfx_manager.spawn_splash_impact(target.rect.center)
                return False, True
            return False, False
    
        shell_type = self.shell_type()
        start_pos = pygame.Vector2(rect.center)
        target_pos = pygame.Vector2(self.target.rect.center)
        relpos = target_pos - start_pos
        distance = relpos.length()
        scale = distance * SHELL_SCALE
        shell_angle = math.atan2(relpos.y, relpos.x)
        shell_incline = math.atan(relpos.x / abs(relpos.x) * scale)
        shell_render_angle = shell_angle + shell_incline
        if hit:
            vfx_manager.spawn_shell_impact(target.rect.center, shell_render_angle, shell_type)
            return True, False
        vfx_manager.spawn_splash_impact(target.rect.center)
        return False, True

    def _spawn_sfx(self):
        if self.hull_type == "CV":
            DataFiles.sfx["aircraft"].play()
            return
        if self.hull_type == "SS":
            return

        DataFiles.sfx["boom"].play()
        zip = DataFiles.sfx["zip"]
        zip.play(fade_ms=1000)
        zip.fadeout(1000)

    def attack(self, rect, vfx_manager):
        if not self.attack_animation:
            return
        self.cooldown_timer = 1
        self.attack_animation = False
        self.attack_timer = 1

        self._spawn_attacking_effects(rect, vfx_manager)
        self.shake()

        self._spawn_sfx()

    def update(self, dt, rect, fleet, vfx_manager):
        self.battlestation_effect_time += dt
        self.shake_time = max(0, self.shake_time - dt)

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
        
        if self.evasion_gauge >= 1:
            self.evasion_smoke.update(dt)

        if self.attack_animation:
            return

        if self.attack_timer > 0:
            start_pos = pygame.Vector2(rect.center)
            target_pos = pygame.Vector2(self.target.rect.center)
            relpos = target_pos - start_pos
            distance = relpos.length()
            old_distance = self.attack_timer * distance
            self.attack_timer = max(0, self.attack_timer - self.attack_speed()/distance*dt)
            new_distance = self.attack_timer * distance
            if self.hull_type in ["SS", "CV"] and old_distance > self.SONAR_DISTANCE >= new_distance:
                DataFiles.sfx["sonar"].play()
            if self.attack_timer <= 0:
                if self.target_pref == "all":
                    for shipgirl in fleet.shipgirls:
                        if shipgirl is None:
                            continue

                        hit = self._deal_damage(shipgirl, vfx_manager)
                        play_shell_impact, play_splash_impact = self._spawn_impact_effects(hit, rect, shipgirl, vfx_manager)
                else:
                    hit = self._deal_damage(self.target, vfx_manager)
                    play_shell_impact, play_splash_impact = self._spawn_impact_effects(hit, rect, self.target, vfx_manager)
                
                if play_shell_impact:
                    DataFiles.sfx["boom2"].play()
                if play_splash_impact:
                    DataFiles.sfx["boom3"].play()
            return

        if self.target_pref != "all" and self.target is not None and self.target.battle_component.hp <= 0:
            self.target = None
        
        self.cooldown_timer = max(0, self.cooldown_timer - self.stat("reload")/1000*dt)
        if self.target is not None and self.cooldown_timer <= 0:
            self.attack_animation = True

    def _draw_attack(self, surface, rect, vfx_manager):
        t = 1 - self.attack_timer

        if self.hull_type == "CV":
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
            aircraft_height = 128 / (1 + math.exp(-20 * (t-distance_ratio-0.1)))
            aircraft_rect.center = start_pos + aircraft_relpos * t - pygame.Vector2(0, aircraft_height)
            surface.blit(aircraft_sprite, aircraft_rect)


            if t < distance_ratio:
                return
            t = 0.5 * (t - distance_ratio) / (1 - distance_ratio) + 0.5
        
        if self.hull_type in ["SS", "CV"]:
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

        start_pos = pygame.Vector2(rect.center)
        target_pos = pygame.Vector2(self.target.rect.center)
        relpos = target_pos - start_pos
        distance = relpos.length()
        scale = distance * SHELL_SCALE
        shell_pos = shell_path(start_pos, target_pos, t)
        shell_incline = math.degrees(math.atan(relpos.x / abs(relpos.x) * scale * (2*t - 1)))
        shell_angle = math.degrees(math.atan2(relpos.y, relpos.x))
        render_angle = shell_angle + shell_incline

        shell_type = self.shell_type()
        shell_sprite = pygame.transform.flip(
            pygame.transform.rotate(DataFiles.sprites["encounter"][f"{shell_type}_shell"], render_angle),
            False, True
        )
        shell_rect = shell_sprite.get_rect()
        shell_rect.center = shell_pos
        surface.blit(shell_sprite, shell_rect)

    def draw_battlestation(self, surface, font_registry, rect):
        if self.hp <= 0:
            return

        if self.is_player:
            rigging_sprite = DataFiles.sprites["encounter"]["shipgirl_rigging"]
            rigging_rect = rigging_sprite.get_rect()
            rigging_rect.left = rect.left
            rigging_rect.centery = rect.centery + rigging_rect.height/3
            battlestation_glow = DataFiles.sprites["encounter"]["shipgirl_battlestation_glow"]
            battlestation_glow_rect = battlestation_glow.get_rect()
            battlestation_glow_rect.centerx = rigging_rect.centerx - Box.WIDTH/4
        else:
            rigging_sprite = DataFiles.sprites["encounter"]["siren_rigging"]
            rigging_rect = rigging_sprite.get_rect()
            rigging_rect.right = rect.right
            rigging_rect.centery = rect.centery + rigging_rect.height/3
            battlestation_glow = DataFiles.sprites["encounter"]["siren_battlestation_glow"]
            battlestation_glow_rect = battlestation_glow.get_rect()
            battlestation_glow_rect.centerx = rigging_rect.centerx + Box.WIDTH/4
        battlestation_glow_rect.bottom = rigging_rect.centery
        surface.blit(rigging_sprite, rigging_rect)
        pulse = (
            math.sin(
                self.battlestation_effect_time
                * math.tau
                / self.BATTLESTATION_PULSE_DURATION
            )
            + 1
        ) / 2
        battlestation_alpha = int(192 + 63*pulse)
        battlestation_glow = battlestation_glow.copy()
        battlestation_glow.set_alpha(battlestation_alpha)
        pulsing_glow = pygame.Surface(battlestation_glow.get_size())
        pulsing_glow.blit(battlestation_glow, (0, 0))
        surface.blit(
            pulsing_glow,
            battlestation_glow_rect,
            special_flags=pygame.BLEND_RGB_ADD,
        )
        vertical_spawn_range = (
            battlestation_glow_rect.height - 2*self.BATTLESTATION_GLINT_MARGIN
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
            glint_strength = (1 - glint_progress)**1.5
            spawn_y = (
                self.BATTLESTATION_GLINT_MARGIN
                + (cycle_index*19 + glint_index*31) % vertical_spawn_range
            )
            y_ratio = spawn_y / (battlestation_glow_rect.height - 1)
            cone_width = round(
                battlestation_glow_rect.width
                - (battlestation_glow_rect.width - 2)*y_ratio
            )
            half_spawn_width = cone_width/2 - self.BATTLESTATION_GLINT_MARGIN
            spawn_x = (
                (cycle_index*29 + glint_index*17) % (2*half_spawn_width)
                - half_spawn_width
            )
            spawn_center = pygame.Vector2(
                battlestation_glow_rect.centerx + spawn_x,
                battlestation_glow_rect.top + spawn_y,
            )
            glint_center = spawn_center - pygame.Vector2(
                0,
                self.BATTLESTATION_GLINT_DRIFT*glint_progress,
            )
            if glint_center.y < battlestation_glow_rect.top:
                continue
            self._draw_battlestation_glint(
                surface,
                glint_center,
                Color.HOLOGRAM_GLOW if self.is_player else Color.SIREN_HOLOGRAM_GLOW,
                glint_strength,
            )
        # TODO cleanup magic numbers
        if self.is_player:
            battlestation_back = pygame.Surface((battlestation_glow_rect.width, 48 + 2*Box.PADDING))
            battlestation_surf = pygame.Surface((battlestation_glow_rect.width, 48 + 2*Box.PADDING), flags=pygame.SRCALPHA)
        else:
            battlestation_back = pygame.Surface((battlestation_glow_rect.width, 40 + 3*Box.PADDING))
            battlestation_surf = pygame.Surface((battlestation_glow_rect.width, 40 + 3*Box.PADDING), flags=pygame.SRCALPHA)
        battlestation_rect = battlestation_back.get_rect()
        battlestation_rect.midbottom = battlestation_glow_rect.midtop
        battlestation_panel_color = (
            Color.HOLOGRAM_GLOW if self.is_player else Color.SIREN_HOLOGRAM_GLOW
        )
        battlestation_back.fill([c//3 for c in battlestation_panel_color])

        hull_sprite = pygame.transform.flip(
            DataFiles.sprites["encounter"]["hull"],
            flip_x=not self.is_player, flip_y=False
        )
        hull_rect = hull_sprite.get_rect()
        if self.is_player:
            hull_rect.right = battlestation_rect.width - Box.PADDING
            hull_rect.centery = Box.PADDING + hull_rect.height/2
        else:
            hull_rect.centerx = battlestation_rect.width/2
            hull_rect.bottom = battlestation_rect.height - Box.PADDING
        hull_panel_rect = hull_rect.inflate(Box.PADDING, Box.PADDING)
        pygame.draw.rect(battlestation_back, [c//2 for c in battlestation_panel_color], hull_panel_rect)
        pygame.draw.rect(battlestation_back, battlestation_panel_color, hull_panel_rect, width=Box.OUTLINE_WIDTH)

        if self.is_player:
            star_icon = DataFiles.sprites["encounter"]["star"]
            star_rect = star_icon.get_rect()
            bar_width = 56
            bar_height = 8
            bar_background = get_rect(
                width=bar_width, height=bar_height,
                right=battlestation_rect.width - Box.PADDING,
                centery=battlestation_rect.height - Box.PADDING - star_rect.height/2
            )
            star_rect.center = bar_background.midleft
            exp_panel_rect = bar_background.union(star_rect).inflate(
                Box.PADDING,
                Box.PADDING,
            )
            pygame.draw.rect(battlestation_back, [c//2 for c in battlestation_panel_color], exp_panel_rect)
            pygame.draw.rect(battlestation_back, battlestation_panel_color, exp_panel_rect, width=Box.OUTLINE_WIDTH)

            outer_radius = 24
            center = (
                pygame.Vector2(outer_radius, outer_radius)
                + pygame.Vector2(Box.PADDING, Box.PADDING)
            )
            reload_panel_rect = get_rect(
                width=2*outer_radius + Box.PADDING,
                height=2*outer_radius + Box.PADDING,
                centerx=center.x,
                centery=center.y,
            )
            pygame.draw.rect(battlestation_back, [c//2 for c in battlestation_panel_color], reload_panel_rect)
            pygame.draw.rect(battlestation_back, battlestation_panel_color, reload_panel_rect, width=Box.OUTLINE_WIDTH)
        else:
            siren_info_panel = get_rect(
                width=battlestation_rect.width - Box.PADDING,
                height=24,
                centerx=battlestation_rect.width/2,
                top=Box.PADDING/2,
            )
            pygame.draw.rect(battlestation_back, [c//2 for c in battlestation_panel_color], siren_info_panel)
            pygame.draw.rect(battlestation_back, battlestation_panel_color, siren_info_panel, width=Box.OUTLINE_WIDTH)

        hp_pct = self.hp / self.stat("max_hp")
        hull_back = pygame.Surface(hull_sprite.get_size())
        hull_back.fill(Color.EXP_BAR_BG)
        hull_back.blit(hull_sprite)
        hull_back.set_colorkey((255,0,0))
        battlestation_surf.blit(hull_back, hull_rect)
        
        hull_fill = pygame.Surface(hull_sprite.get_size())
        hull_fill.fill((0, 255, 205) if self.is_player else (255, 0, 50))
        hull_fill.blit(hull_sprite)
        missing_hp_rect = get_rect(width=hull_rect.width * (1 - hp_pct), height=hull_rect.height, left=0, top=0)
        if self.is_player:
            missing_hp_rect.right = hull_rect.width
        pygame.draw.rect(hull_fill, (255,0,0), missing_hp_rect)
        hull_fill.set_colorkey((255,0,0))
        battlestation_surf.blit(hull_fill, hull_rect)

        if not self.is_player:
            star_icon = DataFiles.sprites["encounter"]["star"]
            star_rect = star_icon.get_rect(
                topleft=(Box.PADDING, Box.PADDING)
            )
            battlestation_surf.blit(star_icon, star_rect)
            font_registry["big_pixel"].render(
                battlestation_surf,
                str(Stats.level(self.exp)),
                star_rect.center,
                Color.WHITE,
                1,
                style="center",
                outline_color=Color.BLACK,
            )
            font_registry["big_pixel"].render(
                battlestation_surf,
                f"{self.name} [{self.hull_type}]",
                (star_rect.right + Box.PADDING, star_rect.centery),
                Color.WHITE,
                1,
                style="centerleft",
                outline_color=Color.BLACK,
            )

            battlestation_back.set_alpha(battlestation_alpha)
            pulsing_battlestation_back = pygame.Surface(battlestation_back.get_size())
            pulsing_battlestation_back.blit(battlestation_back, (0, 0))
            surface.blit(
                pulsing_battlestation_back,
                battlestation_rect,
                special_flags=pygame.BLEND_RGB_ADD,
            )
            battlestation_surf.set_alpha(battlestation_alpha)
            pulsing_battlestation_surf = pygame.Surface(battlestation_surf.get_size(), flags=pygame.SRCALPHA)
            pulsing_battlestation_surf.blit(battlestation_surf, (0, 0))
            surface.blit(
                pulsing_battlestation_surf,
                battlestation_rect,
            )
            return

        exp_animation = self.last_exp + (self.exp - self.last_exp) * self.exp_timer
        bar_fill = get_rect(
            width=bar_width*Stats.level_progress(exp_animation), height=bar_background.height,
            left=bar_background.left, top=bar_background.top
        )
        pygame.draw.rect(battlestation_surf, Color.EXP_BAR_BG, bar_background)
        pygame.draw.rect(battlestation_surf, Color.EXP_BAR_FILL, bar_fill)
        battlestation_surf.blit(star_icon, star_rect)
        font_registry["big_pixel"].render(
            battlestation_surf,
            str(self.last_level),
            star_rect.center,
            Color.WHITE,
            1,
            style="center",
            outline_color=Color.BLACK
        )

        if self.level_timer > 0:
            t = 1 - self.level_timer
            y = rect.top - rect.height * t
            font_registry["big_pixel"].render(surface, "level up!", (rect.centerx, y), Color.WHITE, 1, style="center")
        
        # TODO clean up magic numbers
        inner_radius = 12
        outer_radius = 24
        start_angle = -90
        stop_angle = start_angle + (1 - self.cooldown_timer) * 360
        color = (50,200,50) if self.target is not None else (200,50,50)
        draw_annulus(battlestation_surf, Color.EXP_BAR_BG, center, inner_radius, outer_radius, 0, 360)
        draw_annulus(battlestation_surf, color, center, inner_radius, outer_radius, start_angle, stop_angle)
        if self.hull_type == "CV":
            attack_icon = DataFiles.sprites["user_interface"]["air_attack"]
        elif self.hull_type == "SS":
            attack_icon = DataFiles.sprites["user_interface"]["torp_attack"]
        else:
            attack_icon = DataFiles.sprites["user_interface"]["shell_attack"]
        attack_icon_rect = attack_icon.get_rect()
        attack_icon_rect.center = center
        battlestation_surf.blit(attack_icon, attack_icon_rect)

        battlestation_back.set_alpha(battlestation_alpha)
        pulsing_battlestation_back = pygame.Surface(battlestation_back.get_size())
        pulsing_battlestation_back.blit(battlestation_back, (0, 0))
        surface.blit(
            pulsing_battlestation_back,
            battlestation_rect,
            special_flags=pygame.BLEND_RGB_ADD,
        )
        battlestation_surf.set_alpha(battlestation_alpha)
        pulsing_battlestation_surf = pygame.Surface(battlestation_surf.get_size(), flags=pygame.SRCALPHA)
        pulsing_battlestation_surf.blit(battlestation_surf, (0, 0))
        surface.blit(
            pulsing_battlestation_surf,
            battlestation_rect,
        )

    def _draw_battlestation_glint(self, surface, center, color, strength):
        glint_length = 1 + round(
            (self.BATTLESTATION_GLINT_MAX_LENGTH - 1)*strength
        )
        glint_color = tuple(round(channel*strength) for channel in color)
        glint_surface = pygame.Surface(
            (
                2*self.BATTLESTATION_GLINT_MAX_LENGTH + 1,
                2*self.BATTLESTATION_GLINT_MAX_LENGTH + 1,
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

    def draw_effects(self, surface, rect, vfx_manager):
        if not self.active:
            return
        if self.attack_timer > 0:
            self._draw_attack(surface, rect, vfx_manager)
        if self.evasion_gauge >= 1:
            self.evasion_smoke.draw(surface, rect)
        if not self.is_player:
            return
        if self.target is not None:
            target_color = (
                Color.TARGET_INDICATOR if self.attack_animation or self.attack_timer > 0
                else Color.MUTED_TARGET_INDICATOR
            )
            dash_length = 8
            dash_width = 2
            if self.hull_type in ["DD", "CL", "CA", "BB"]:
                start_pos = pygame.Vector2(rect.center)
                curr_pos = start_pos
                end_pos = pygame.Vector2(self.target.rect.center)
            else:
                start_pos = pygame.Vector2(rect.centerx, rect.bottom - rect.height/5)
                curr_pos = start_pos
                target_rect = self.target.rect
                end_pos = pygame.Vector2(target_rect.centerx, target_rect.bottom - target_rect.height/5)
            distance = (end_pos - start_pos).length()
            for dash_start in range(0, round(distance), 2 * dash_length):
                start_t = dash_start / distance
                end_t = min((dash_start + dash_length) / distance, 1)
                if self.hull_type in ["DD", "CL", "CA", "BB"]:
                    curr_pos = shell_path(start_pos, end_pos, start_t)
                    dash_end_pos = shell_path(start_pos, end_pos, end_t)
                else:
                    curr_pos = start_pos.lerp(end_pos, start_t)
                    dash_end_pos = start_pos.lerp(end_pos, end_t)
                parallel = (dash_end_pos - curr_pos).normalize()
                perpendicular = pygame.Vector2(parallel.y, -parallel.x)
                polygon = [
                    curr_pos + dash_width/2 * perpendicular,
                    dash_end_pos + dash_width/2 * perpendicular,
                    dash_end_pos - dash_width/2 * perpendicular,
                    curr_pos - dash_width/2 * perpendicular,
                ]
                pygame.draw.polygon(
                    surface,
                    target_color,
                    polygon,
                )

            reticle_size = 24
            duplex_size = 16
            pygame.draw.circle(surface, target_color, end_pos, reticle_size, 2)
            for line in [
                [(end_pos.x - reticle_size, end_pos.y), (end_pos.x + reticle_size, end_pos.y)],
                [(end_pos.x, end_pos.y - reticle_size), (end_pos.x, end_pos.y + reticle_size)]
            ]:
                pygame.draw.line(surface, target_color, line[0], line[1], 1)
            for line in [
                [(end_pos.x - reticle_size, end_pos.y), (end_pos.x - reticle_size + duplex_size, end_pos.y)],
                [(end_pos.x + reticle_size, end_pos.y), (end_pos.x + reticle_size - duplex_size, end_pos.y)],
                [(end_pos.x, end_pos.y - reticle_size), (end_pos.x, end_pos.y - reticle_size + duplex_size)],
                [(end_pos.x, end_pos.y + reticle_size), (end_pos.x, end_pos.y + reticle_size - duplex_size)]
            ]:
                pygame.draw.line(surface, target_color, line[0], line[1], 3)

class Shipgirl:
    SPRITE_SIZE = 96 # TODO get this from the actual sprite?

    def __init__(self, name, is_player):
        if is_player:
            self.name = name
        else:
            self.name = name.split(":")[0]
    
        self.pos = self.get_random_floor_pos()
        self.wander_target = self.pos.copy()
        self.pause_time = 0
        if os.path.exists(f"live2d/{self.name}.json"):
            self.sprite = Live2D(f"live2d/{self.name}.json")
        elif os.path.exists("live2d/TB.json"):
            self.sprite = Live2D("live2d/TB.json")
        else:
            self.sprite = None
        self.facing_left = False
            
        self.rect = get_rect(width=self.SPRITE_SIZE, height=self.SPRITE_SIZE, centerx=self.pos.x, centery=self.pos.y)
        self.interacting_decoration = None
        self.battle_component = ShipgirlBattleComponent(name, is_player)

    def __repr__(self):
        return self.name

    @staticmethod
    def get_random_floor_pos():
        iso_x = random.uniform(0, Decorations.FLOOR_TILES_WIDE)
        iso_y = random.uniform(0, Decorations.FLOOR_TILES_TALL)
        target_x = (
            Decorations.floor_rect.left
            + Decorations.floor_rect.width / 2
            + (iso_x - iso_y) * Decorations.ISO_HALF_TILE_WIDTH
        )
        target_y = (
            Decorations.floor_rect.top
            + (iso_x + iso_y) * Decorations.ISO_HALF_TILE_HEIGHT
        )
        return pygame.Vector2(
            target_x,
            target_y
        )

    def pick_new_wander_target(self):
        self.wander_target = self.get_random_floor_pos()
        self.pause_time = random.uniform(1, 3) # TODO clean up magic numbers

    def update(self, dt):
        if self.sprite.animation == Live2D.BOUNCE_ANIMATION:
            return
        
        if self.interacting_decoration is not None:
            return
        
        if self.pause_time > 0:
            self.pause_time -= dt
            self.sprite.set_animation(Live2D.IDLE_ANIMATION)
        else:
            to_target = self.wander_target - self.pos
            if to_target.length() < 10: # TODO clean up
                self.pick_new_wander_target()
            else:
                direction = to_target.normalize()
                self.pos += direction * 50 * dt # TODO clean up magic numbers
                if direction.x >= 0:
                    self.facing_left = False
                else:
                    self.facing_left = True
            
            self.sprite.set_animation(Live2D.WALK_ANIMATION)
        self.rect.center = self.pos

    def animate(self, dt):
        self.sprite.update(dt)

    def draw(self, surface, font_registry, alpha=255):
        shake_amt = 4
        shake_offset = shake_amt * math.sin(4*math.radians(360)*self.battle_component.shake_time)
        self.sprite.draw(surface, self.rect.centerx + shake_offset, self.rect.centery, not self.facing_left, alpha=alpha)

class PlayerFleet:
    def __init__(self):
        self.shipgirls = [None, None, None]
        self.backups = [None, None, None]
    
    @property
    def afloat(self):
        return any(
            shipgirl is not None and shipgirl.battle_component.hp > 0
            for shipgirl in self.shipgirls + self.backups
        )

    @property
    def primary_fleet_size(self):
        return len([shipgirl for shipgirl in self.shipgirls if shipgirl is not None])

    @property
    def backup_fleet_size(self):
        return len([shipgirl for shipgirl in self.backups if shipgirl is not None])

    @property
    def fleet(self):
        return self.shipgirls + self.backups

    @property
    def front(self):
        for shipgirl in self.shipgirls:
            if shipgirl is not None and shipgirl.battle_component.hp > 0:
                return shipgirl
        return None

    @property
    def highest_hp(self):
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

    def in_fleet(self, shipgirl):
        return shipgirl in self.shipgirls or shipgirl in self.backups

    def clear_fleet(self):
        self.shipgirls = [None, None, None]
        self.backups = [None, None, None]

    def begin_sortie(self):
        for shipgirl in self.shipgirls + self.backups:
            if shipgirl is not None:
                shipgirl.battle_component.reset()

    def begin_encounter(self):
        for shipgirl in self.shipgirls:
            if shipgirl is not None:
                shipgirl.battle_component.active = True

    def end_encounter(self):
        for shipgirl in self.shipgirls:
            if shipgirl is not None:
                shipgirl.battle_component.target = None
                shipgirl.battle_component.attack_animation = False
                shipgirl.battle_component.attack_timer = 0
                shipgirl.battle_component.active = False

    def animate(self, dt):
        for shipgirl in self.fleet:
            if shipgirl is not None:
                if shipgirl.battle_component.hp <= 0:
                    shipgirl.sprite.set_animation(Live2D.SINK_ANIMATION)
                elif shipgirl.battle_component.attack_animation:
                    shipgirl.sprite.set_animation(Live2D.ATTACK_ANIMATION)
                shipgirl.animate(dt)

    def update(self, dt, vfx_manager):
        for shipgirl in self.fleet:
            if shipgirl is not None:
                if shipgirl.battle_component.hp <= 0:
                    shipgirl.battle_component.active = False
                elif shipgirl.battle_component.attack_animation:
                    if shipgirl.sprite.t > 2.5 * Live2D.KEYFRAME_DURATION:
                        shipgirl.battle_component.attack(shipgirl.rect, vfx_manager)
                shipgirl.battle_component.update(dt, shipgirl.rect, None, vfx_manager)

    def draw_shipgirl(self, surface, font_registry):
        for shipgirl in self.shipgirls:
            if shipgirl is not None:
                shipgirl.draw(surface, font_registry)
        for shipgirl in self.backups:
            if shipgirl is not None:
                shipgirl.draw(surface, font_registry)
    
    def draw_battle_effects(self, surface, vfx_manager):
        for shipgirl in self.shipgirls:
            if shipgirl is not None:
                shipgirl.battle_component.draw_effects(surface, shipgirl.rect, vfx_manager)
        for shipgirl in self.backups:
            if shipgirl is not None:
                shipgirl.battle_component.draw_effects(surface, shipgirl.rect, vfx_manager)

    def get_draw_indices(self):
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
    SLOT_SIZE = Shipgirl.SPRITE_SIZE

    def __init__(self):
        self._front = []
        self._back = []

        self.dummy_target = None
    
    @property
    def afloat(self):
        return any(siren.battle_component.hp > 0 for siren in self.fleet)

    @property
    def siren_names(self):
        return [siren.name for siren in self.fleet]

    @property
    def front(self):
        return (
            [siren for siren in self._front if siren.battle_component.hp > 0]
            or [siren for siren in self._back if siren.battle_component.hp > 0]
        )

    @property
    def fleet(self):
        return self._front + self._back

    def clear_fleet(self):
        self._front = []
        self._back = []

    def begin_encounter(self):
        for siren in self.fleet:
            siren.battle_component.active = True
        
        slot_size = siren.SPRITE_SIZE
        front_offset = (len(self._front)-1)/2
        for i, siren in enumerate(self._front):
            siren.rect.centerx = screen_x(0.75) - slot_size + (i-front_offset)*slot_size/2
            siren.rect.centery = screen_y(0.5) + (i-front_offset)*slot_size
        
        back_offset = (len(self._back)-1)/2
        for i, siren in enumerate(self._back): 
            siren.rect.centerx = screen_x(0.75) + slot_size + (i-back_offset)*slot_size/2
            siren.rect.centery = screen_y(0.5) + (i-back_offset)*slot_size
    
    def end_encounter(self):
        for siren in self.fleet:
            siren.battle_component.target = None
            siren.battle_component.attack_animation = False
            siren.battle_component.attack_timer = 0
            siren.battle_component.active = False

    def animate(self, dt):
        for siren in self.fleet:
            if siren.battle_component.hp <= 0:
                siren.sprite.set_animation(Live2D.SINK_ANIMATION)
            elif siren.battle_component.attack_animation:
                siren.sprite.set_animation(Live2D.ATTACK_ANIMATION)
            siren.animate(dt)

    def update(self, dt, menu_manager, vfx_manager):
        if self.dummy_target is None:
            self.dummy_target = DummyTarget(menu_manager)

        for siren in self.fleet:
            if siren.battle_component.target is None:
                if siren.battle_component.target_pref == "highest_hp":
                    siren.battle_component.target = menu_manager.player_fleet.highest_hp
                elif siren.battle_component.target_pref == "all":
                    siren.battle_component.target = self.dummy_target
                else:
                    siren.battle_component.target = menu_manager.player_fleet.front
            if siren.battle_component.hp <= 0:
                siren.battle_component.active = False
            elif siren.battle_component.attack_animation:
                if siren.sprite.t > 2.5 * Live2D.KEYFRAME_DURATION:
                    siren.battle_component.attack(siren.rect, vfx_manager)
            siren.battle_component.update(dt, siren.rect, menu_manager.player_fleet, vfx_manager)

    def get_draw_indices(self):
        draw_indices = []
        if len(self._front) == 1:
            draw_indices.append((3, self._front[0]))
        elif len(self._front) == 2:
            draw_indices.append((2, self._front[0]))
            draw_indices.append((4, self._front[1]))
        elif len(self._front) == 3:
            draw_indices.append((1, self._front[0]))
            draw_indices.append((3, self._front[1]))
            draw_indices.append((5, self._front[2]))
        
        if len(self._back) == 1:
            draw_indices.append((3, self._back[0]))
        elif len(self._back) == 2:
            draw_indices.append((2, self._back[0]))
            draw_indices.append((4, self._back[1]))
        elif len(self._back) == 3:
            draw_indices.append((1, self._back[0]))
            draw_indices.append((3, self._back[1]))
            draw_indices.append((5, self._back[2]))
        
        return draw_indices

    def draw_battle_effects(self, surface, vfx_manager):
        for siren in self.fleet:
            siren.battle_component.draw_effects(surface, siren.rect, vfx_manager)
