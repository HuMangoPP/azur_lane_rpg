import os
import math
import random
import pygame

from engine.util import get_rect, get_vec, draw_slice

from src.constants import DataFiles, Color, Equipment, Box, screen_x, screen_y

from live2d.live2d import Live2D

class ShipgirlBattleComponent:
    LEVEL_EXPS = [3, 5, 7, 9, 11]
    
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

    SHELL_SPEED = {
        "DD": 1500,
        "CL": 1500,
        "CA": 1000,
        "BB": 1000
    }

    def __init__(self, name, is_player):
        self.name = name
        self.active = False
        self.is_player = is_player

        if name in DataFiles.shipgirl_data:
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

        self.hp = self.max_hp()
        self.cooldown_timer = 1
        self.attack_timer = 0
        self.target = None
        self.evasion_gauge = 0

    @property
    def level(self):
        level_index = 0
        exp = self.exp
        while exp >= self.LEVEL_EXPS[level_index]:
            exp -= self.LEVEL_EXPS[level_index]
            level_index += 1
        return level_index

    def max_hp(self, equipment_override=None):
        equipment = self.equipment.copy()
        if equipment_override is not None:
            equipment[equipment_override[0]] = equipment_override[1]
        return (
            self.base_max_hp[0] + self.base_max_hp[1] * self.level
            + DataFiles.equipment_data.get(equipment[Equipment.WEAPON], {}).get("max_hp", 0)
            + DataFiles.equipment_data.get(equipment[Equipment.AUX1], {}).get("max_hp", 0)
            + DataFiles.equipment_data.get(equipment[Equipment.AUX2], {}).get("max_hp", 0)
        )

    def evasion(self, equipment_override=None):
        equipment = self.equipment.copy()
        if equipment_override is not None:
            equipment[equipment_override[0]] = equipment_override[1]
        return (
            self.base_evasion[0] + self.base_evasion[1] * self.level
            + DataFiles.equipment_data.get(equipment[Equipment.WEAPON], {}).get("evasion", 0)
            + DataFiles.equipment_data.get(equipment[Equipment.AUX1], {}).get("evasion", 0)
            + DataFiles.equipment_data.get(equipment[Equipment.AUX2], {}).get("evasion", 0)
        )

    def firepower(self, equipment_override=None):
        equipment = self.equipment.copy()
        if equipment_override is not None:
            equipment[equipment_override[0]] = equipment_override[1]
        return (
            self.base_firepower[0] + self.base_firepower[1] * self.level
            + DataFiles.equipment_data.get(equipment[Equipment.WEAPON], {}).get("firepower", 0)
            + DataFiles.equipment_data.get(equipment[Equipment.AUX1], {}).get("firepower", 0)
            + DataFiles.equipment_data.get(equipment[Equipment.AUX2], {}).get("firepower", 0)
        )

    def reload(self, equipment_override=None):
        equipment = self.equipment.copy()
        if equipment_override is not None:
            equipment[equipment_override[0]] = equipment_override[1]
        return (
            self.base_reload[0] + self.base_reload[1] * self.level
            + DataFiles.equipment_data.get(equipment[Equipment.WEAPON], {}).get("reload", 0)
            + DataFiles.equipment_data.get(equipment[Equipment.AUX1], {}).get("reload", 0)
            + DataFiles.equipment_data.get(equipment[Equipment.AUX2], {}).get("reload", 0)
        )

    def shell_speed(self):
        return self.SHELL_SPEED[self.hull_type] + DataFiles.equipment_data.get(self.equipment[Equipment.WEAPON], {}).get("shell_speed", 0)

    def reset(self):
        self.hp = self.max_hp()
        self.cooldown_timer = 1
        self.target = None
        self.evasion_gauge = 0

    def update(self, dt):
        if not self.active:
            return
        
        if self.attack_timer > 0:
            self.attack_timer = max(0, self.attack_timer - self.shell_speed()/1000*dt)
            if self.attack_timer <= 0:
                self.target.battle_component.evasion_gauge += self.target.battle_component.evasion() / 1000
                if self.target.battle_component.evasion_gauge >= 1:
                    self.target.battle_component.evasion_gauge -= 1
                else:
                    weapon_info = DataFiles.equipment_data.get(self.equipment[0], {}) if self.equipment[0] is not None else {}
                    shell_type = weapon_info.get("shell_type", "normal")
                    armor_type = self.HULL_TO_ARMOR_MAP[self.target.battle_component.hull_type]
                    self.target.battle_component.hp -= self.firepower() * self.DAMAGE_MULTIPLIER[shell_type][armor_type]
            return

        if self.target is not None and self.target.battle_component.hp <= 0:
            self.target = None
        
        self.cooldown_timer = max(0, self.cooldown_timer - self.reload()/1000*dt)
        if self.target is not None and self.cooldown_timer <= 0:
            self.attack_timer = 1
            self.cooldown_timer = 1

    def draw(self, screen, rect):
        if not self.active:
            return
        
        if self.attack_timer > 0:
            start_pos = pygame.Vector2(rect.center)
            target_pos = pygame.Vector2(self.target.rect.center)
            t = 1 - self.attack_timer
            if self.hull_type in ["DD", "CL"]:
                apex_pos = 0.5 * (start_pos + target_pos) + pygame.Vector2(0,-50)
            else:
                apex_pos = 0.5 * (start_pos + target_pos) + pygame.Vector2(0,-100)
            shell_x = (target_pos.x - start_pos.x) * t + start_pos.x
            shell_y = (
                start_pos.y * (shell_x - apex_pos.x) * (shell_x - target_pos.x) / (start_pos.x - apex_pos.x) / (start_pos.x - target_pos.x)
                + apex_pos.y * (shell_x - start_pos.x) * (shell_x - target_pos.x) / (apex_pos.x - start_pos.x) / (apex_pos.x - target_pos.x)
                + target_pos.y * (shell_x - start_pos.x) * (shell_x - apex_pos.x) / (target_pos.x - start_pos.x) / (target_pos.x - apex_pos.x)
            )
            shell_pos = pygame.Vector2(shell_x, shell_y)
            shell_yvel = (
                start_pos.y * (2*shell_x - apex_pos.x - target_pos.x) / (start_pos.x - apex_pos.x) / (start_pos.x - target_pos.x)
                + apex_pos.y * (2*shell_x - start_pos.x - target_pos.x) / (apex_pos.x - start_pos.x) / (apex_pos.x - target_pos.x)
                + target_pos.y * (2*shell_x - start_pos.x - apex_pos.x) / (target_pos.x - start_pos.x) / (target_pos.x - apex_pos.x)
            )
            sign = (target_pos.x - start_pos.x) / abs(target_pos.x - start_pos.x)
            shell_angle = math.atan2(sign* shell_yvel, sign)
            shell_polygon = [
                shell_pos + get_vec(20, shell_angle),
                shell_pos + get_vec(10, shell_angle + math.radians(150)),
                shell_pos + get_vec(10, shell_angle - math.radians(150))
            ]
            pygame.draw.polygon(screen, Color.WHITE, shell_polygon)
        
        bar_width = 50
        bar_background = get_rect(width=bar_width, height=10, centerx=rect.centerx, top=rect.bottom+20) # TODO
        bar_fill = get_rect(width=bar_width*self.hp/self.max_hp(), height=bar_background.height, left=bar_background.left, top=bar_background.top)
        pygame.draw.rect(screen, (50,50,50), bar_background)
        pygame.draw.rect(screen, Color.WHITE, bar_fill)

        if not self.is_player:
            return

        center = pygame.Vector2(rect.centerx, rect.top-50) # TODO
        radius = 30
        start_angle = -90
        end_angle = start_angle + 360 * (1 - self.cooldown_timer)
        color = (50,200,50) if self.target is not None else (200,50,50)
        draw_slice(screen, color, center, radius, start_angle, end_angle)
        pygame.draw.circle(screen, Color.WHITE, center, radius, width=Box.OUTLINE_WIDTH)

class Shipgirl:
    SPRITE_SIZE = 96 # TODO

    def __init__(self, name, is_player):
        self.name = name
    
        self.pos = pygame.Vector2(
            screen_x(random.random()),
            screen_y(random.random())
        )
        self.wander_target = self.pos.copy()
        self.pause_time = 0
        if os.path.exists(f"live2d/{self.name}.json"):
            self.sprite = Live2D(f"live2d/{self.name}.json")
        elif os.path.exists("live2d/laffey.json"):
            self.sprite = Live2D("live2d/laffey.json")
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

    def draw(self, screen, font):
        if self.sprite is not None:
            self.sprite.draw(screen, self.rect.centerx, self.rect.centery, not self.facing_left)
        else:
            pygame.draw.rect(screen, Color.WHITE, self.rect, width=Box.OUTLINE_WIDTH)
            _ = font.render(screen, self.name, self.rect.center, Color.WHITE, 1, style="center", outline_color=Color.BLACK)

        self.battle_component.draw(screen, self.rect)

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

    def update(self, dt):
        for shipgirl in self.fleet:
            if shipgirl is not None:
                if shipgirl.battle_component.hp <= 0:
                    shipgirl.battle_component.active = False
                shipgirl.battle_component.update(dt)

                shipgirl.animate(dt)

    def draw(self, screen, font):
        for shipgirl in self.shipgirls:
            if shipgirl is not None:
                shipgirl.draw(screen, font)
        for shipgirl in self.backups:
            if shipgirl is not None:
                shipgirl.draw(screen, font)

class SirenFleet:
    SLOT_SIZE = 96 # TODO

    def __init__(self):
        self._front = []
        self._back = []
    
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

    def update(self, dt, menu_manager):
        for i, siren in enumerate(self._front):
            if siren.battle_component.hp <= 0:
                siren.battle_component.active = False
            if siren.battle_component.active:
                if siren.battle_component.target is None:
                    siren.battle_component.target = menu_manager.player_fleet.front
            siren.battle_component.update(dt)

            siren.animate(dt)
        
        back_offset = (len(self._back)-1)/2
        for i, siren in enumerate(self._back):
            if siren.battle_component.hp <= 0:
                siren.battle_component.active = False
            siren.battle_component.update(dt)

            siren.animate(dt)

    def draw(self, screen, font):
        for siren in self.fleet:
            siren.draw(screen, font)