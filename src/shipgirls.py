import os
import math
import random
import pygame

from engine.util import get_rect, draw_annulus

from src.constants import DataFiles, Color, Equipment, Box, Stats, screen_x, screen_y
from src.vfx import shell_position, SHELL_SCALE
from live2d.live2d import Live2D

class DummyTarget:
    def __init__(self, menu_manager):
        self.rect = menu_manager.fleet_selection_menu.fleet_slots[1]

class ShipgirlBattleComponent:
    LIGHT_ARMOR = 0
    MEDIUM_ARMOR = 1
    HEAVY_ARMOR = 2

    HULL_TO_ARMOR_MAP = {
        "DD": LIGHT_ARMOR,
        "CL": MEDIUM_ARMOR,
        "CA": MEDIUM_ARMOR,
        "BB": HEAVY_ARMOR
    }

    DAMAGE_MULTIPLIER = {
        "normal": {LIGHT_ARMOR: 1.0, MEDIUM_ARMOR: 1.0, HEAVY_ARMOR: 1.0},
        "HE": {LIGHT_ARMOR: 1.5, MEDIUM_ARMOR: 1.25, HEAVY_ARMOR: 1.0},
        "AP": {LIGHT_ARMOR: 1.0, MEDIUM_ARMOR: 1.25, HEAVY_ARMOR: 1.5},
    }

    SHELL_SPEED = 800

    def __init__(self, name, is_player):
        self.name = name
        self.active = False
        self.is_player = is_player

        if self.is_player:
            info = DataFiles.shipgirl_data[name]
            save = DataFiles.save_file["shipgirls"][name]
            stats = DataFiles.stats_data[info["hull_type"]]
        else:
            info = DataFiles.siren_data[name]
            stats = info
            save = info

        self.base_max_hp = stats["max_hp"]
        self.base_evasion = stats["evasion"]
        self.base_firepower = stats["firepower"]
        self.base_reload = stats["reload"]
        self.hull_type = info["hull_type"]
        self.equipment = save["equipment"]
        self.exp = save["exp"]
        if self.is_player:
            self.target_pref = None
        else:
            self.target_pref = info["target_pref"]

        self.hp = self.max_hp()
        self.cooldown_timer = 1
        self.attack_timer = 0
        self.target = None
        self.evasion_gauge = 0

        self.last_exp = save["exp"]
        self.exp_timer = 0
        self.last_level = Stats.level(self.last_exp)
        self.level_timer = 0

    def max_hp(self, equipment_override=None):
        equipment = self.equipment.copy()
        if equipment_override is not None:
            equipment[equipment_override[0]] = equipment_override[1]
        return (
            Stats.stat(self.exp, *self.base_max_hp)
            + DataFiles.equipment_data.get(equipment[Equipment.WEAPON], {}).get("max_hp", 0)
            + DataFiles.equipment_data.get(equipment[Equipment.AUX1], {}).get("max_hp", 0)
            + DataFiles.equipment_data.get(equipment[Equipment.AUX2], {}).get("max_hp", 0)
        )

    def evasion(self, equipment_override=None):
        equipment = self.equipment.copy()
        if equipment_override is not None:
            equipment[equipment_override[0]] = equipment_override[1]
        return (
            Stats.stat(self.exp, *self.base_evasion)
            + DataFiles.equipment_data.get(equipment[Equipment.WEAPON], {}).get("evasion", 0)
            + DataFiles.equipment_data.get(equipment[Equipment.AUX1], {}).get("evasion", 0)
            + DataFiles.equipment_data.get(equipment[Equipment.AUX2], {}).get("evasion", 0)
        )

    def firepower(self, equipment_override=None):
        equipment = self.equipment.copy()
        if equipment_override is not None:
            equipment[equipment_override[0]] = equipment_override[1]
        return (
            Stats.stat(self.exp, *self.base_firepower)
            + DataFiles.equipment_data.get(equipment[Equipment.WEAPON], {}).get("firepower", 0)
            + DataFiles.equipment_data.get(equipment[Equipment.AUX1], {}).get("firepower", 0)
            + DataFiles.equipment_data.get(equipment[Equipment.AUX2], {}).get("firepower", 0)
        )

    def reload(self, equipment_override=None):
        equipment = self.equipment.copy()
        if equipment_override is not None:
            equipment[equipment_override[0]] = equipment_override[1]
        return (
            Stats.stat(self.exp, *self.base_reload)
            + DataFiles.equipment_data.get(equipment[Equipment.WEAPON], {}).get("reload", 0)
            + DataFiles.equipment_data.get(equipment[Equipment.AUX1], {}).get("reload", 0)
            + DataFiles.equipment_data.get(equipment[Equipment.AUX2], {}).get("reload", 0)
        )

    def shell_speed(self):
        return self.SHELL_SPEED + DataFiles.equipment_data.get(self.equipment[Equipment.WEAPON], {}).get("shell_speed", 0)

    def shell_type(self):
        return DataFiles.equipment_data.get(self.equipment[Equipment.WEAPON], {}).get("shell_type", "normal")

    def reset(self):
        self.hp = self.max_hp()
        self.cooldown_timer = 1
        self.target = None
        self.evasion_gauge = 0

    def _deal_damage(self, target):
        target.battle_component.evasion_gauge += target.battle_component.evasion() / 1000
        if target.battle_component.evasion_gauge >= 1:
            target.battle_component.evasion_gauge -= 1
            return False
        else:
            shell_type = self.shell_type()
            armor_type = self.HULL_TO_ARMOR_MAP[target.battle_component.hull_type]
            target.battle_component.hp -= self.firepower() * self.DAMAGE_MULTIPLIER[shell_type][armor_type]
            return True

    def update(self, dt, rect, fleet, vfx_manager):
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
        
        if self.attack_timer > 0:
            start_pos = pygame.Vector2(rect.center)
            target_pos = pygame.Vector2(self.target.rect.center)
            relpos = target_pos - start_pos
            distance = relpos.length()
            self.attack_timer = max(0, self.attack_timer - self.shell_speed()/distance*dt)
            if self.attack_timer <= 0:
                hit = False
                shell_type = self.shell_type()
                if self.target_pref == "all":
                    for shipgirl in fleet.shipgirls:
                        if shipgirl is None:
                            continue

                        target_hit = self._deal_damage(shipgirl)
                        hit = target_hit or hit
                        vfx_manager.spawn_impact(shipgirl.rect.center, shell_type, target_hit)
                else:
                    hit = self._deal_damage(self.target)
                    vfx_manager.spawn_impact(self.target.rect.center, shell_type, hit)
                
                if hit:
                    DataFiles.sfx["boom2"].play()
            return

        if self.target_pref != "all" and self.target is not None and self.target.battle_component.hp <= 0:
            self.target = None
        
        self.cooldown_timer = max(0, self.cooldown_timer - self.reload()/1000*dt)
        if self.target is not None and self.cooldown_timer <= 0:
            start_pos = pygame.Vector2(rect.center)
            target_pos = pygame.Vector2(self.target.rect.center)
            shell_type = self.shell_type()
            vfx_manager.spawn_muzzle_flash(start_pos, shell_type, self.hull_type)
            vfx_manager.spawn_tracer(start_pos, target_pos, shell_type, self.shell_speed())

            self.attack_timer = 1
            self.cooldown_timer = 1
            DataFiles.sfx["boom"].play()

            zip = DataFiles.sfx["zip"]
            zip.play(fade_ms=1000)
            zip.fadeout(1000)


    def draw(self, surface, font, rect):
        bar_width = 64
        bar_height = 8
        if self.exp_timer > 0:
            exp_animation = self.last_exp + (self.exp - self.last_exp) * self.exp_timer
            bar_background = get_rect(width=bar_width, height=bar_height, centerx=rect.centerx, bottom=rect.top-Box.PADDING)
            bar_fill = get_rect(
                width=bar_width*Stats.level_progress(exp_animation), height=bar_background.height,
                left=bar_background.left, top=bar_background.top
            )
            pygame.draw.rect(surface, Color.EXP_BAR_BG, bar_background)
            pygame.draw.rect(surface, Color.EXP_BAR_FILL, bar_fill)

        if self.level_timer > 0:
            t = 1 - self.level_timer
            y = rect.top - rect.height * t
            font.render(surface, "level up!", (rect.centerx, y), Color.WHITE, 1, style="center")

        if not self.active:
            return
        
        if self.attack_timer > 0:
            start_pos = pygame.Vector2(rect.center)
            target_pos = pygame.Vector2(self.target.rect.center)
            relpos = target_pos - start_pos
            direction = relpos.normalize()
            distance = relpos.length()
            t = 1 - self.attack_timer
            scale = distance * SHELL_SCALE
            shell_pos = shell_position(start_pos, target_pos, t)
            shell_incline = math.degrees(math.atan(direction.x / abs(direction.x) * scale * (2*t - 1)))
            shell_angle = math.degrees(math.atan2(direction.y, direction.x))
            render_angle = shell_angle + shell_incline

            shell_type = self.shell_type()
            shell_sprite = pygame.transform.flip(
                pygame.transform.rotate(DataFiles.sprites["encounter"][f"{shell_type}_shell"], render_angle),
                False, True
            )
            shell_rect = shell_sprite.get_rect()
            shell_rect.center = shell_pos
            surface.blit(shell_sprite, shell_rect)
        
        bar_background = get_rect(width=bar_width, height=bar_height, centerx=rect.centerx, top=rect.bottom+Box.PADDING)
        bar_fill = get_rect(
            width=bar_width*self.hp/self.max_hp(), height=bar_background.height,
            left=bar_background.left, top=bar_background.top
        )
        pygame.draw.rect(surface, Color.EXP_BAR_BG, bar_background)
        pygame.draw.rect(surface, Color.WHITE, bar_fill)

        if not self.is_player:
            return

        center = pygame.Vector2(rect.centerx, rect.top-50) # TODO
        inner_radius = 16
        outer_radius = 32
        start_angle = -90
        stop_angle = start_angle + (1 - self.cooldown_timer) * 360
        color = (50,200,50) if self.target is not None else (200,50,50)
        draw_annulus(surface, color, center, inner_radius, outer_radius, start_angle, stop_angle)
        attack_icon = DataFiles.sprites["user_interface"]["attack"]
        attack_icon_rect = attack_icon.get_rect()
        attack_icon_rect.center = center
        surface.blit(attack_icon, attack_icon_rect)

class Shipgirl:
    SPRITE_SIZE = 96 # TODO

    def __init__(self, name, is_player):
        self.name = name.split(":")[0]
    
        self.pos = pygame.Vector2(
            screen_x(random.random()),
            screen_y(random.random())
        )
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

        self.battle_component = ShipgirlBattleComponent(self.name, is_player)

    def __repr__(self):
        return self.name

    def update(self, dt):
        if self.pause_time > 0:
            self.pause_time -= dt
            if self.sprite is not None:
                self.sprite.set_animation(Live2D.IDLE_ANIMATION)
        else:
            to_target = self.wander_target - self.pos
            if to_target.length() < 10: # TODO
                self.wander_target = pygame.Vector2(
                    screen_x(random.random()),
                    screen_y(random.random())
                )
                self.pause_time = random.uniform(1, 3) # TODO
            else:
                direction = to_target.normalize()
                self.pos += direction * 50 * dt # TODO
                if direction.x >= 0:
                    self.facing_left = False
                else:
                    self.facing_left = True
            
            if self.sprite is not None:
                self.sprite.set_animation(Live2D.WALK_ANIMATION)
        self.rect.center = self.pos

        self.animate(dt)

    def animate(self, dt):
        if self.sprite is not None:
            self.sprite.update(dt)

    def draw(self, surface, font):
        if self.sprite is not None:
            self.sprite.draw(surface, self.rect.centerx, self.rect.centery, not self.facing_left)
        else:
            pygame.draw.rect(surface, Color.WHITE, self.rect, width=Box.OUTLINE_WIDTH)
            font.render(surface, self.name, self.rect.center, Color.WHITE, 1, style="center")

class PlayerFleet:
    def __init__(self):
        self.shipgirls = [None, None, None]
        self.backups = [None, None, None]
    
    @property
    def afloat(self):
        return any(shipgirl is not None and shipgirl.battle_component.hp > 0 for shipgirl in self.shipgirls)

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
            elif shipgirl.battle_component.max_hp() > shipgirl_with_highest_hp.battle_component.max_hp():
                shipgirl_with_highest_hp = shipgirl
        return shipgirl_with_highest_hp

    def in_fleet(self, shipgirl):
        return shipgirl in self.shipgirls or shipgirl in self.backups

    def clear_fleet(self):
        self.shipgirls = [None, None, None]
        self.backups = [None, None, None]

    def begin_sortie(self):
        for shipgirl in self.shipgirls:
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
                shipgirl.battle_component.attack_timer = 0
                shipgirl.battle_component.active = False

    def update(self, dt, vfx_manager):
        for shipgirl in self.fleet:
            if shipgirl is not None:
                if shipgirl.battle_component.hp <= 0:
                    shipgirl.battle_component.active = False
                shipgirl.battle_component.update(dt, shipgirl.rect, None, vfx_manager)

                shipgirl.animate(dt)

    def draw_shipgirl(self, surface, font):
        for shipgirl in self.shipgirls:
            if shipgirl is not None:
                shipgirl.draw(surface, font)
        for shipgirl in self.backups:
            if shipgirl is not None:
                shipgirl.draw(surface, font)
    
    def draw_battle_component(self, surface, font):
        for shipgirl in self.shipgirls:
            if shipgirl is not None:
                shipgirl.battle_component.draw(surface, font, shipgirl.rect)
        for shipgirl in self.backups:
            if shipgirl is not None:
                shipgirl.battle_component.draw(surface, font, shipgirl.rect)

class SirenFleet:
    SLOT_SIZE = 96 # TODO

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
        
        front_offset = (len(self._front)-1)/2
        for i, siren in enumerate(self._front):
            siren.rect.centerx = screen_x(0.8) - self.SLOT_SIZE + (i-front_offset)*self.SLOT_SIZE/2
            siren.rect.centery = screen_y(0.5) + (i-front_offset)*self.SLOT_SIZE
        
        back_offset = (len(self._back)-1)/2
        for i, siren in enumerate(self._back): 
            siren.rect.centerx = screen_x(0.8) + self.SLOT_SIZE + (i-back_offset)*self.SLOT_SIZE/2
            siren.rect.centery = screen_y(0.5) + (i-back_offset)*self.SLOT_SIZE
    
    def end_encounter(self):
        for siren in self.fleet:
            siren.battle_component.target = None
            siren.battle_component.active = False

    def update(self, dt, menu_manager, vfx_manager):
        if self.dummy_target is None:
            self.dummy_target = DummyTarget(menu_manager)

        for siren in self.fleet:
            if siren.battle_component.hp <= 0:
                siren.battle_component.active = False
            elif siren.battle_component.target is None:
                if siren.battle_component.target_pref == "highest_hp":
                    siren.battle_component.target = menu_manager.player_fleet.highest_hp
                elif siren.battle_component.target_pref == "all":
                    siren.battle_component.target = self.dummy_target
                else:
                    siren.battle_component.target = menu_manager.player_fleet.front
            siren.battle_component.update(dt, siren.rect, menu_manager.player_fleet, vfx_manager)

            siren.animate(dt)

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

    def draw_battle_component(self, surface, font):
        for siren in self.fleet:
            siren.battle_component.draw(surface, font, siren.rect)
