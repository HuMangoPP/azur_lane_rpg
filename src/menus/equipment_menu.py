import math
import random
import pygame

from engine.util import get_rect, get_vec
from engine.button import Button

from src.constants import DataFiles, Color, Equipment, Stats, Box, screen_x, screen_y

from live2d.live2d import Live2D

class Cloud:
    def __init__(self, index, x, y, speed):
        self.sprite = DataFiles.sprites["sortie_selection"][f"cloud{index}"]
        self.x = x
        self.y = y
        self.speed = speed
    
    def update(self, dt):
        self.x = self.x + self.speed * dt
    
    def draw(self, surface):
        rect = self.sprite.get_rect()
        rect.centerx = self.x
        rect.top = self.y
        surface.blit(self.sprite, rect)

class EquipmentMenu:
    def __init__(self, menu_manager):
        self.menu_manager = menu_manager

        self.equipment_section = get_rect(
            width=3*Box.WIDTH+2*Box.PADDING+2*Box.PADDING + 2*Box.PADDING,
            height=Box.HEIGHT+2*Box.PADDING + 2*Box.PADDING + 2*Box.HEIGHT+Box.PADDING+2*Box.PADDING + 2*Box.PADDING,
            centerx=screen_x(0.75),
            centery=screen_y(0.5)
        )

        self.selected_shipgirl = None
        self.equipment_panel = get_rect(
            width=self.equipment_section.width - 2*Box.PADDING,
            height=Box.HEIGHT + 2*Box.PADDING,
            centerx=self.equipment_section.centerx,
            top=self.equipment_section.top+Box.PADDING
        )
        self.equipped_rects = [
            get_rect(
                width=Box.WIDTH, height=Box.HEIGHT,
                left=self.equipment_panel.left+Box.PADDING + i*(Box.WIDTH+Box.PADDING),
                centery=self.equipment_panel.centery
            ) for i in range(Equipment.NUM_EQUIPS)
        ]
        self.selected_equipment = Equipment.WEAPON

        self.equippable_panel = get_rect(
            width=self.equipment_section.width - 2*Box.PADDING,
            height=2*Box.HEIGHT+Box.PADDING + 2*Box.PADDING,
            centerx=self.equipment_section.centerx,
            bottom=self.equipment_section.bottom-Box.PADDING
        )

        self.equippable_rects = [
            get_rect(
                width=Box.WIDTH, height=Box.HEIGHT,
                left=self.equippable_panel.left+Box.PADDING + (i%3)*(Box.WIDTH+Box.PADDING),
                top=self.equippable_panel.top+Box.PADDING + (i//3)*(Box.HEIGHT+Box.PADDING)
            )
            for i in range(6)
        ]
        self.hovered_equipment = None

        def exit_equipment_menu():
            self.menu_manager.current_menu = self.menu_manager.port_menu

            self.selected_shipgirl = None

        button_sprite = DataFiles.sprites["user_interface"]["prev"]
        button_rect = button_sprite.get_rect()
        button_rect.right = Box.RIGHT_OF_SCREEN
        button_rect.top = Box.TOP_OF_SCREEN
        self.exit_equipment_menu_button = Button(rect=button_rect,sprite=button_sprite,callback=exit_equipment_menu)

        self.stats_panel = get_rect(
            width=2.5*Box.WIDTH + 2*Box.PADDING,
            height=2*Box.PADDING + 9+16+2*Box.PADDING + 2*Box.HEIGHT+3*Box.PADDING,
            centerx=screen_x(0.25),
            centery=screen_y(0.5)
        )

        stats = ["max_hp", "evasion", "firepower", "reload"]
        stat_rect_size = 32
        self.stat_rects = {
            stat: get_rect(
                width=stat_rect_size, height=stat_rect_size,
                left=self.stats_panel.left+3*Box.PADDING,
                bottom=self.stats_panel.bottom-Box.PADDING - (len(stats)-1-i)*(stat_rect_size+Box.PADDING)
            )
            for i, stat in enumerate(stats)
        }
        self.exp_bar_bg = get_rect(
            width=128, height=16,
            left=self.stats_panel.left+Box.PADDING,
            top=self.stats_panel.top+Box.PADDING+9+Box.PADDING
        )

        num_waves = DataFiles.sprites["sortie_selection"]["num_waves"]
        self.wave_ys = [
            screen_y(0.5) + 48*(i-(num_waves-1)/2)
            for i in range(num_waves)
        ]
        self.wave_timers = [
            math.radians(360)*random.random()
            for _ in range(num_waves)
        ]

        self.cloud_timer = 0
        self.cloud_spawn_time = 0
        self.clouds = []


    def get_stat(self, shipgirl, stat):
        if stat == "max_hp":
            if self.hovered_equipment is None:
                return shipgirl.battle_component.max_hp()
            else:
                return shipgirl.battle_component.max_hp((self.selected_equipment, self.hovered_equipment))
        elif stat == "evasion":
            if self.hovered_equipment is None:
                return shipgirl.battle_component.evasion()
            else:
                return shipgirl.battle_component.evasion((self.selected_equipment, self.hovered_equipment))
        elif stat == "firepower":
            if self.hovered_equipment is None:
                return shipgirl.battle_component.firepower()
            else:
                return shipgirl.battle_component.firepower((self.selected_equipment, self.hovered_equipment))
        elif stat == "reload":
            if self.hovered_equipment is None:
                return shipgirl.battle_component.reload()
            else:
                return shipgirl.battle_component.reload((self.selected_equipment, self.hovered_equipment))

    def get_stat_delta(self, shipgirl, stat):
        if self.hovered_equipment is None:
            return 0
        if stat == "max_hp":
            return (
                shipgirl.battle_component.max_hp((self.selected_equipment, self.hovered_equipment))
                - shipgirl.battle_component.max_hp()
            )
        elif stat == "evasion":
            return (
                shipgirl.battle_component.evasion((self.selected_equipment, self.hovered_equipment))
                - shipgirl.battle_component.evasion()
            )
        elif stat == "firepower":
            return (
                shipgirl.battle_component.firepower((self.selected_equipment, self.hovered_equipment))
                - shipgirl.battle_component.firepower()
            )
        elif stat == "reload":
            return (
                shipgirl.battle_component.reload((self.selected_equipment, self.hovered_equipment))
                - shipgirl.battle_component.reload()
            )

    def update(self, dt, events):
        if self.selected_equipment == Equipment.WEAPON:
            equippable = [
                weapon_name for weapon_name, weapon_info in DataFiles.equipment_data.items()
                if DataFiles.save_file["equipment"].get(weapon_name, 0) > 0
                and weapon_info["type"] == "weapon"
                and weapon_info["equippable_by"] == self.selected_shipgirl.battle_component.hull_type
            ]
        else:
            equippable = [
                aux_name for aux_name, aux_info in DataFiles.equipment_data.items()
                if DataFiles.save_file["equipment"].get(aux_name, 0) > 0
                and aux_info["type"] == "aux"
            ]
        for event in events:
            if event.type == pygame.MOUSEBUTTONUP:
                for i, rect in enumerate(self.equipped_rects):
                    if rect.collidepoint(event.pos):
                        self.selected_equipment = i

                for new_equipment, rect in zip(equippable, self.equippable_rects):
                    if rect.collidepoint(event.pos):
                        current_equipment = self.selected_shipgirl.battle_component.equipment[self.selected_equipment]
                        if current_equipment is not None:
                            DataFiles.save_file["equipment"][current_equipment] = DataFiles.save_file["equipment"].get(current_equipment, 0) + 1
                        self.selected_shipgirl.battle_component.equipment[self.selected_equipment] = new_equipment
                        DataFiles.save_file["equipment"][new_equipment] -= 1
            
                self.exit_equipment_menu_button.click(event.pos)
            if event.type == pygame.MOUSEMOTION:
                for equipment, rect in zip(equippable, self.equippable_rects):
                    if rect.collidepoint(event.pos):
                        self.hovered_equipment = equipment
                        break
                else:
                    self.hovered_equipment = None
        
        if self.selected_shipgirl is not None:
            self.selected_shipgirl.rect.centerx = screen_x(0.5)
            self.selected_shipgirl.rect.centery = screen_y(0.5)
            if self.selected_shipgirl.sprite is not None:
                self.selected_shipgirl.sprite.set_animation(Live2D.IDLE_ANIMATION)
            self.selected_shipgirl.animate(dt)

        num_waves = DataFiles.sprites["sortie_selection"]["num_waves"]
        self.wave_timers = [
            (wave_timer + (i+1)/num_waves*dt)%math.radians(360)
            for i, wave_timer in enumerate(self.wave_timers)
        ]

        for cloud in self.clouds:
            cloud.update(dt)
        self.clouds = [
            cloud for cloud in self.clouds
            if cloud.x >= -128
            and cloud.x <= screen_x(1) + 128
        ]

        self.cloud_timer += dt
        if self.cloud_timer > self.cloud_spawn_time:
            move_right = random.random() > 0.5
            self.clouds.append(Cloud(
                random.randint(1, DataFiles.sprites["sortie_selection"]["num_clouds"])-1,
                0 if move_right else screen_x(1),
                random.uniform(0, 128),
                random.uniform(32, 64) * (1 if move_right else -1)
            ))
            self.cloud_timer = 0
            self.cloud_spawn_time = random.uniform(5, 10)

    def draw(self, surface, font):
        sky_surf = DataFiles.sprites["sortie_selection"]["sky"]
        sky_surf_rect = sky_surf.get_rect()
        sky_surf_rect.top = 0
        num_sky_reps = 9
        sky_rep_offset = (num_sky_reps-1)/2
        for i in range(num_sky_reps):
            sky_surf_rect.centerx = screen_x(0.5) + sky_surf_rect.width * (i-sky_rep_offset)
            surface.blit(sky_surf, sky_surf_rect)

        for cloud in self.clouds:
            cloud.draw(surface)
            
        num_waves = DataFiles.sprites["sortie_selection"]["num_waves"]
        num_wave_reps = 5
        wave_rep_offset = (num_wave_reps-1)/2
        for i, (wave_y, wave_timer) in enumerate(zip(self.wave_ys, self.wave_timers)):
            if i == (num_waves-1)//2 and self.selected_shipgirl is not None:
                self.selected_shipgirl.draw(surface, font)
            wave = DataFiles.sprites["sortie_selection"][f"wave{i}"]
            wave_rect = wave.get_rect()
            wave_rect.top = wave_y
            centerx = 64 * math.sin(wave_timer) + screen_x(0.5)
            for j in range(num_wave_reps):
                wave_rect.centerx = centerx + wave_rect.width * (j-wave_rep_offset)
                surface.blit(wave, wave_rect)

        if self.selected_shipgirl is not None:
            
            pygame.draw.rect(surface, Color.BLUE, self.stats_panel)

            level_progress = Stats.level_progress(self.selected_shipgirl.battle_component.exp)
            exp_bar = get_rect(
                width=level_progress*self.exp_bar_bg.width,
                height=self.exp_bar_bg.height,
                left=self.exp_bar_bg.left,
                top=self.exp_bar_bg.top
            )
            pygame.draw.rect(surface, Color.GREY, self.exp_bar_bg)
            pygame.draw.rect(surface, Color.BLUE_GREY, exp_bar)

            level = Stats.level(self.selected_shipgirl.battle_component.exp) + 1
            font.render(
                surface,
                f"level {level}",
                (self.exp_bar_bg.left, self.stats_panel.top+Box.PADDING),
                Color.WHITE,
                1,
                style="topleft",
                outline_color=Color.BLACK
            )

            for stat, rect in self.stat_rects.items():
                surface.blit(DataFiles.sprites["user_interface"][stat], rect)
                font.render(
                    surface,
                    str(self.get_stat(self.selected_shipgirl, stat)),
                    (rect.right + Box.PADDING, rect.centery),
                    Color.WHITE,
                    1,
                    style="centerleft",
                    outline_color=Color.BLACK
                )
                stat_delta = self.get_stat_delta(self.selected_shipgirl, stat)
                if stat_delta > 0:
                    center = pygame.Vector2(rect.left-Box.PADDING,rect.centery)
                    pygame.draw.polygon(surface, (0,255,0),[
                        center+get_vec(length=Box.PADDING, angle=math.radians(30)),
                        center+get_vec(length=Box.PADDING, angle=math.radians(150)),
                        center+get_vec(length=Box.PADDING, angle=math.radians(270))
                    ])
                elif stat_delta < 0:
                    center = pygame.Vector2(rect.left-Box.PADDING,rect.centery)
                    pygame.draw.polygon(surface, (255,0,0),[
                        center+get_vec(length=Box.PADDING, angle=math.radians(90)),
                        center+get_vec(length=Box.PADDING, angle=math.radians(210)),
                        center+get_vec(length=Box.PADDING, angle=math.radians(330))
                    ])
            
            pygame.draw.rect(surface, Color.BLUE_GREY, self.equipment_section)
            pygame.draw.rect(surface, Color.BLUE, self.equipment_panel)
            for i, (equipment, rect) in enumerate(zip(self.selected_shipgirl.battle_component.equipment, self.equipped_rects)):
                if self.selected_equipment == i:
                    pygame.draw.rect(surface, Color.WHITE, rect, width=2*Box.OUTLINE_WIDTH)
                else:
                    pygame.draw.rect(surface, Color.WHITE, rect, width=Box.OUTLINE_WIDTH)
                if equipment is not None:
                    if equipment in DataFiles.sprites["entity"]:
                        surface.blit(DataFiles.sprites["entity"][equipment], rect)
                    else:
                        font.render(surface, equipment, rect.center, Color.WHITE, 1, style="center", outline_color=Color.BLACK)
            
            if self.selected_equipment == Equipment.WEAPON:
                equippable = [
                    weapon_name for weapon_name, weapon_info in DataFiles.equipment_data.items()
                    if DataFiles.save_file["equipment"].get(weapon_name, 0) > 0
                    and weapon_info["type"] == "weapon"
                    and weapon_info["equippable_by"] == self.selected_shipgirl.battle_component.hull_type
                ]
            else:
                equippable = [
                    aux_name for aux_name, aux_info in DataFiles.equipment_data.items()
                    if DataFiles.save_file["equipment"].get(aux_name, 0) > 0
                    and aux_info["type"] == "aux"
                ]
            
            pygame.draw.rect(surface, Color.BLUE, self.equippable_panel)
            point_at = self.equipped_rects[self.selected_equipment]
            pointer = [
                (point_at.centerx, point_at.bottom+Box.PADDING),
                (point_at.centerx-Box.PADDING, self.equippable_panel.top),
                (point_at.centerx+Box.PADDING, self.equippable_panel.top)
            ]
            pygame.draw.polygon(surface, Color.BLUE, pointer)
            for equipment, rect in zip(equippable, self.equippable_rects):
                pygame.draw.rect(surface, Color.WHITE, rect, width=Box.OUTLINE_WIDTH)
                if equipment in DataFiles.sprites["entity"]:
                    surface.blit(DataFiles.sprites["entity"][equipment], rect)
                else:
                    font.render(surface, equipment, rect.center, Color.WHITE, 1, style="center", outline_color=Color.BLACK)
        
        self.exit_equipment_menu_button.draw(surface, font)
