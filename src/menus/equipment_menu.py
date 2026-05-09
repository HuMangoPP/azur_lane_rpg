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

        self.blueprint_page = DataFiles.sprites["user_interface"]["equipment_menu_blueprint"].get_rect()
        self.blueprint_page.right = screen_x(0.75) - Box.PADDING
        self.blueprint_page.centery = screen_y(0.5)
        blueprint_page_center = pygame.Vector2(self.blueprint_page.center)
        rotated_angle = 5
        page_horizontal = get_vec(self.blueprint_page.width/2, math.radians(rotated_angle))
        page_vertical = get_vec(self.blueprint_page.height/2, math.radians(90+rotated_angle))
        self.misaligned_blueprint_page = [
            blueprint_page_center + page_horizontal + page_vertical,
            blueprint_page_center + page_horizontal - page_vertical,
            blueprint_page_center - page_horizontal - page_vertical,
            blueprint_page_center - page_horizontal + page_vertical,
        ]
        self.equipped_rects = [
            get_rect(
                width=Box.WIDTH, height=Box.HEIGHT,
                centerx=self.blueprint_page.centerx,
                bottom=screen_y(0.5) - Box.PADDING
            ),
            get_rect(
                width=Box.WIDTH, height=Box.HEIGHT,
                right=self.blueprint_page.centerx - Box.PADDING,
                top=screen_y(0.5) + Box.PADDING
            ),
            get_rect(
                width=Box.WIDTH, height=Box.HEIGHT,
                left=self.blueprint_page.centerx + Box.PADDING,
                top=screen_y(0.5) + Box.PADDING
            )
        ]
        self.selected_equipment = Equipment.WEAPON

        num_equipment_per_row = 3
        num_equipment_rows = 2
        self.equipment_depot = get_rect(
            width=num_equipment_per_row*(Box.WIDTH+Box.PADDING)+Box.PADDING,
            height=num_equipment_rows*(Box.HEIGHT+Box.PADDING)+Box.PADDING,
            left=self.blueprint_page.right + Box.PADDING,
            centery=screen_y(0.5)
        )
        self.equippable_rects = [
            get_rect(
                width=Box.WIDTH, height=Box.HEIGHT,
                left=self.equipment_depot.left+Box.PADDING + (i%num_equipment_per_row)*(Box.WIDTH+Box.PADDING),
                top=self.equipment_depot.top+Box.PADDING + (i//num_equipment_per_row)*(Box.HEIGHT+Box.PADDING) 
            )
            for i in range(num_equipment_per_row * num_equipment_rows)
        ]
        self.hovered_equipment = None

        self.dossier_page = get_rect(
            width=2.5*Box.WIDTH + 2*Box.PADDING,
            height=2*Box.PADDING + 9+16+2*Box.PADDING + 2*Box.HEIGHT+3*Box.PADDING,
            centerx=screen_x(0.25),
            centery=screen_y(0.5)
        )
        dossier_page_center = pygame.Vector2(self.dossier_page.center)
        rotated_angle = 5
        page_horizontal = get_vec(self.dossier_page.width/2, math.radians(rotated_angle))
        page_vertical = get_vec(self.dossier_page.height/2, math.radians(90 + rotated_angle))
        self.misaligned_dossier_page = [
            dossier_page_center + page_horizontal + page_vertical,
            dossier_page_center + page_horizontal - page_vertical,
            dossier_page_center - page_horizontal - page_vertical,
            dossier_page_center - page_horizontal + page_vertical,
        ]
        self.dossier_bg = get_rect(
            width=self.dossier_page.width + 2*Box.PADDING,
            height=self.dossier_page.height + 2*Box.PADDING,
            center=self.dossier_page.center
        )
        dossier_bg_topleft = pygame.Vector2(self.dossier_bg.topleft)
        self.dossier_tab = [
            dossier_bg_topleft,
            dossier_bg_topleft + pygame.Vector2(Box.WIDTH+Box.PADDING, 0),
            dossier_bg_topleft + pygame.Vector2(Box.WIDTH-Box.PADDING, -Box.HEIGHT/2),
            dossier_bg_topleft + pygame.Vector2(0, -Box.HEIGHT/2)
        ]

        stats = ["max_hp", "evasion", "firepower", "reload"]
        stat_rect_size = 32
        self.stat_rects = {
            stat: get_rect(
                width=stat_rect_size, height=stat_rect_size,
                left=self.dossier_page.left+3*Box.PADDING,
                bottom=self.dossier_page.bottom-Box.PADDING - (len(stats)-1-i)*(stat_rect_size+Box.PADDING)
            )
            for i, stat in enumerate(stats)
        }
        self.exp_bar_bg = get_rect(
            width=128, height=16,
            left=self.dossier_page.left+Box.PADDING,
            top=self.dossier_page.top+Box.PADDING+9+Box.PADDING
        )

        def exit_equipment_menu():
            self.menu_manager.current_menu = self.menu_manager.port_menu

            self.selected_shipgirl = None

        button_sprite = DataFiles.sprites["user_interface"]["prev"]
        button_rect = button_sprite.get_rect()
        button_rect.right = Box.RIGHT_OF_SCREEN
        button_rect.top = Box.TOP_OF_SCREEN
        self.exit_equipment_menu_button = Button(rect=button_rect,sprite=button_sprite,callback=exit_equipment_menu)

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
            self.selected_shipgirl.rect.right = screen_x(0.5)
            self.selected_shipgirl.rect.centery = screen_y(0.5)
            if self.selected_shipgirl.sprite is not None:
                self.selected_shipgirl.sprite.set_animation(Live2D.IDLE_ANIMATION)
            self.selected_shipgirl.animate(dt)

    def draw(self, surface, font):
        if self.selected_shipgirl is not None:
            self.selected_shipgirl.draw(surface, font)

            pygame.draw.rect(surface, Color.DOSSIER, self.dossier_bg)
            pygame.draw.polygon(surface, Color.DOSSIER, self.dossier_tab)
            pygame.draw.polygon(surface, Color.DOSSIER_PAGE, self.misaligned_dossier_page)
            pygame.draw.rect(surface, Color.DOSSIER_PAGE, self.dossier_page)

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
                (self.exp_bar_bg.left, self.dossier_page.top+Box.PADDING),
                Color.BLACK,
                1,
                style="topleft"
            )

            for stat, rect in self.stat_rects.items():
                stat_icon = DataFiles.recolor_sprite("user_interface", stat, Color.BLACK)
                surface.blit(stat_icon, rect)
                font.render(
                    surface,
                    str(self.get_stat(self.selected_shipgirl, stat)),
                    (rect.right + Box.PADDING, rect.centery),
                    Color.BLACK,
                    2,
                    style="centerleft"
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
            
            pygame.draw.polygon(surface, Color.BLUEPRINT_PAGE_BACK, self.misaligned_blueprint_page)
            surface.blit(DataFiles.sprites["user_interface"]["equipment_menu_blueprint"], self.blueprint_page)
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
            
            pygame.draw.rect(surface, Color.CARGO_BOX_BACK, self.equipment_depot)
            for equipment, rect in zip(equippable, self.equippable_rects):
                pygame.draw.rect(surface, Color.CARGO_BOX, rect)
                if equipment in DataFiles.sprites["entity"]:
                    surface.blit(DataFiles.sprites["entity"][equipment], rect)
                else:
                    font.render(surface, equipment, rect.center, Color.WHITE, 1, style="center", outline_color=Color.BLACK)
        
        self.exit_equipment_menu_button.draw(surface, font)
