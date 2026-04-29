import math
import random
import pygame

from engine.util import get_rect, get_vec
from engine.button import Button

from src.constants import DataFiles, Color, Equipment, Stats, Box, screen_x, screen_y

from live2d.live2d import Live2D

class EquipmentMenu:
    def __init__(self, menu_manager):
        self.menu_manager = menu_manager

        self.selected_shipgirl = None
        self.equipped_rects = [
            get_rect(
                width=Box.WIDTH, height=Box.HEIGHT,
                centerx=(i-1)*(Box.WIDTH+Box.PADDING)+screen_x(0.75),
                centery=screen_y(0.5)
            ) for i in range(Equipment.NUM_EQUIPS)
        ]
        self.selected_equipment = Equipment.WEAPON

        num_rects_in_row = 3
        x_rect_offset = (num_rects_in_row-1)/2
        self.equippable_rects = [
            get_rect(
                width=Box.WIDTH, height=Box.HEIGHT,
                centerx=(i%num_rects_in_row-x_rect_offset)*(Box.WIDTH+Box.PADDING)+screen_x(0.75),
                top=(i//num_rects_in_row)*(Box.HEIGHT+Box.PADDING)+Box.HEIGHT/2+Box.PADDING+screen_y(0.5)
            )
            for i in range(6)
        ]
        self.hovered_equipment = None

        def exit_equipment_menu():
            self.menu_manager.current_menu = self.menu_manager.port_menu

            self.selected_shipgirl = None

        button_sprite = DataFiles.sprites["prev"]
        button_rect = button_sprite.get_rect()
        button_rect.right = Box.RIGHT_OF_SCREEN
        button_rect.top = Box.TOP_OF_SCREEN
        self.exit_equipment_menu_button = Button(rect=button_rect,sprite=button_sprite,callback=exit_equipment_menu)

        self.stat_text_xy = [
            pygame.Vector2(screen_x(0.25)-Box.WIDTH/2, Box.HEIGHT/2+Box.PADDING*(2+1.5*i)+screen_y(0.5))
            for i in range(Stats.NUM_STATS)
        ]

    def get_stat(self, shipgirl, stat):
        if stat == Stats.MAX_HP:
            if self.hovered_equipment is None:
                return shipgirl.battle_component.max_hp()
            else:
                return shipgirl.battle_component.max_hp((self.selected_equipment, self.hovered_equipment))
        elif stat == Stats.EVASION:
            if self.hovered_equipment is None:
                return shipgirl.battle_component.evasion()
            else:
                return shipgirl.battle_component.evasion((self.selected_equipment, self.hovered_equipment))
        elif stat == Stats.FIREPOWER:
            if self.hovered_equipment is None:
                return shipgirl.battle_component.firepower()
            else:
                return shipgirl.battle_component.firepower((self.selected_equipment, self.hovered_equipment))
        elif stat == Stats.RELOAD:
            if self.hovered_equipment is None:
                return shipgirl.battle_component.reload()
            else:
                return shipgirl.battle_component.reload((self.selected_equipment, self.hovered_equipment))

    def get_stat_delta(self, shipgirl, stat):
        if self.hovered_equipment is None:
            return 0
        if stat == Stats.MAX_HP:
            return (
                shipgirl.battle_component.max_hp((self.selected_equipment, self.hovered_equipment))
                - shipgirl.battle_component.max_hp()
            )
        elif stat == Stats.EVASION:
            return (
                shipgirl.battle_component.evasion((self.selected_equipment, self.hovered_equipment))
                - shipgirl.battle_component.evasion()
            )
        elif stat == Stats.FIREPOWER:
            return (
                shipgirl.battle_component.firepower((self.selected_equipment, self.hovered_equipment))
                - shipgirl.battle_component.firepower()
            )
        elif stat == Stats.RELOAD:
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
            self.selected_shipgirl.rect.centerx = screen_x(0.25)
            self.selected_shipgirl.rect.centery = screen_y(0.5)
            if self.selected_shipgirl.sprite is not None:
                self.selected_shipgirl.sprite.set_animation(Live2D.IDLE_ANIMATION)
            self.selected_shipgirl.animate(dt)

    def draw(self, surface, font):
        if self.selected_shipgirl is not None:
            # shipgirl chibi
            self.selected_shipgirl.draw(surface, font)
            # shipgirl stats
            for stat, xy in enumerate(self.stat_text_xy):
                font_rect = font.render(
                    surface,
                    f"{Stats.STAT_NAMES[stat]}: {self.get_stat(self.selected_shipgirl, stat)}",
                    xy,
                    Color.WHITE,
                    1,
                    style="topleft",
                    outline_color=Color.BLACK
                )
                stat_delta = self.get_stat_delta(self.selected_shipgirl, stat)
                if stat_delta > 0:
                    center = pygame.Vector2(font_rect.left-10,font_rect.centery) # TODO
                    pygame.draw.polygon(surface, (0,255,0),[
                        center+get_vec(length=5, angle=math.radians(30)),
                        center+get_vec(length=5, angle=math.radians(150)),
                        center+get_vec(length=5, angle=math.radians(270))
                    ])
                elif stat_delta < 0:
                    center = pygame.Vector2(font_rect.left-10,font_rect.centery)
                    pygame.draw.polygon(surface, (255,0,0),[
                        center+get_vec(length=5, angle=math.radians(90)),
                        center+get_vec(length=5, angle=math.radians(210)),
                        center+get_vec(length=5, angle=math.radians(330))
                    ])
            # shipgirl equipment
            for i, (equipment, rect) in enumerate(zip(self.selected_shipgirl.battle_component.equipment, self.equipped_rects)):
                if self.selected_equipment == i:
                    pygame.draw.rect(surface, Color.WHITE, rect, width=2*Box.OUTLINE_WIDTH)
                else:
                    pygame.draw.rect(surface, Color.WHITE, rect, width=Box.OUTLINE_WIDTH)
                if equipment is not None:
                    _ = font.render(surface, equipment, rect.center, Color.WHITE, 1, style="center", outline_color=Color.BLACK)
            # equippable equipment
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
            for equipment, rect in zip(equippable, self.equippable_rects):
                pygame.draw.rect(surface, Color.WHITE, rect, width=Box.OUTLINE_WIDTH)
                _ = font.render(surface, equipment, rect.center, Color.WHITE, 1, style="center", outline_color=Color.BLACK)
        # exit button
        self.exit_equipment_menu_button.draw(surface, font)
