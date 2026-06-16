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

        blueprint_surf = DataFiles.sprites["equipment_menu"]["blueprint"]
        self.blueprint_page = blueprint_surf.get_rect()
        self.blueprint_page.left = screen_x(0.5) - Box.WIDTH
        self.blueprint_page.bottom = screen_y(0.5) + 1.25*Box.HEIGHT
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
                centery=self.blueprint_page.centery - Box.HEIGHT
            ),
            get_rect(
                width=Box.WIDTH, height=Box.HEIGHT,
                centerx=self.blueprint_page.centerx - Box.WIDTH,
                centery=self.blueprint_page.centery + Box.HEIGHT
            ),
            get_rect(
                width=Box.WIDTH, height=Box.HEIGHT,
                centerx=self.blueprint_page.centerx + Box.WIDTH,
                centery=self.blueprint_page.centery + Box.HEIGHT
            ),
        ]
        self.selected_equipment = Equipment.WEAPON

        num_equipment_per_row = 5
        num_equipment_rows = 2
        self.equipment_depot = get_rect(
            width=num_equipment_per_row*(Box.WIDTH+Box.PADDING)+Box.PADDING,
            height=num_equipment_rows*(Box.HEIGHT+Box.PADDING)+Box.PADDING,
            centerx=self.blueprint_page.centerx,
            top=self.blueprint_page.bottom + Box.PADDING,
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

        font_height = 12
        self.dossier_page = get_rect(
            width=2.5*Box.WIDTH + 2*Box.PADDING,
            height=(
                2*Box.PADDING # padding
                + font_height+Box.PADDING # name
                + Box.HEIGHT/2 # exp
                + 2*Box.HEIGHT # stats
            ),
            centerx=screen_x(0.25),
            top=screen_y(0.5)
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

        self.exp_bar_bg = get_rect(
            width=2*Box.WIDTH, height=Box.HEIGHT/4,
            left=self.dossier_page.left+Box.PADDING+Box.WIDTH/2,
            centery=self.dossier_page.top+2*Box.PADDING+font_height+Box.HEIGHT/4
        )

        stats = ["max_hp", "evasion", "firepower", "reload"]
        stat_rect_size = 32
        self.stat_rects = {
            stat: get_rect(
                width=stat_rect_size, height=stat_rect_size,
                left=self.dossier_page.left+3*Box.PADDING,
                top=self.exp_bar_bg.centery + Box.HEIGHT/4 + i*stat_rect_size
            )
            for i, stat in enumerate(stats)
        }

        def exit_equipment_menu():
            self.menu_manager.current_menu = self.menu_manager.port_menu
            self.selected_shipgirl = None

        button_sprite = DataFiles.sprites["user_interface"]["prev"]
        button_rect = get_rect(width=48,height=48,right=Box.RIGHT_OF_SCREEN,top=Box.TOP_OF_SCREEN)
        self.exit_equipment_menu_button = Button(
            button_rect,
            exit_equipment_menu,
            background_styling={
                "background_color": Color.BLACK,
                "background_img": button_sprite,
                "opacity": 160
            }
        )

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
        self.selected_shipgirl.rect.centerx = screen_x(0.25)
        self.selected_shipgirl.rect.bottom = screen_y(0.5) - Box.HEIGHT
        if self.selected_shipgirl.sprite is not None:
            self.selected_shipgirl.sprite.set_animation(Live2D.IDLE_ANIMATION)
        self.selected_shipgirl.animate(dt)
        
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
                        DataFiles.sfx["click"].play()

                for new_equipment, rect in zip(equippable, self.equippable_rects):
                    if rect.collidepoint(event.pos):
                        current_equipment = self.selected_shipgirl.battle_component.equipment[self.selected_equipment]
                        if current_equipment is not None:
                            DataFiles.save_file["equipment"][current_equipment] = DataFiles.save_file["equipment"].get(current_equipment, 0) + 1
                        self.selected_shipgirl.battle_component.equipment[self.selected_equipment] = new_equipment
                        DataFiles.save_file["equipment"][new_equipment] -= 1
                        DataFiles.sfx["click"].play()
            
                if self.exit_equipment_menu_button.click(event.pos):
                    DataFiles.sfx["click"].play()
            if event.type == pygame.MOUSEMOTION:
                for equipment, rect in zip(equippable, self.equippable_rects):
                    if rect.collidepoint(event.pos):
                        self.hovered_equipment = equipment
                        break
                else:
                    self.hovered_equipment = None

    def draw(self, surface, font):
        self.selected_shipgirl.draw(surface, font)

        pygame.draw.rect(surface, Color.DOSSIER, self.dossier_bg)
        pygame.draw.polygon(surface, Color.DOSSIER, self.dossier_tab)
        pygame.draw.polygon(surface, Color.DOSSIER_PAGE, self.misaligned_dossier_page)
        pygame.draw.rect(surface, Color.DOSSIER_PAGE, self.dossier_page)

        faction = DataFiles.shipgirl_data[self.selected_shipgirl.name]["faction"]
        font.render(
            surface,
            f"{faction} {self.selected_shipgirl.name}",
            (self.dossier_page.left+Box.PADDING, self.dossier_page.top+Box.PADDING),
            Color.BLACK,
            1,
            style="topleft"
        )
        level = Stats.level(self.selected_shipgirl.battle_component.exp) + 1
        medal_icon = DataFiles.sprites["user_interface"]["medal"]
        medal_rect = medal_icon.get_rect()
        medal_rect.left = self.dossier_page.left + Box.PADDING
        medal_rect.centery = self.exp_bar_bg.centery
        surface.blit(medal_icon, medal_rect)
        font.render(
            surface,
            str(level),
            medal_rect.center,
            Color.WHITE,
            1,
            style="center",
            outline_color=Color.BLACK
        )
        level_progress = Stats.level_progress(self.selected_shipgirl.battle_component.exp)
        exp_bar = get_rect(
            width=level_progress*self.exp_bar_bg.width,
            height=self.exp_bar_bg.height,
            left=self.exp_bar_bg.left,
            top=self.exp_bar_bg.top
        )
        pygame.draw.rect(surface, Color.EXP_BAR_BG, self.exp_bar_bg)
        pygame.draw.rect(surface, Color.EXP_BAR_FILL, exp_bar)

        for stat, rect in self.stat_rects.items():
            stat_icon = DataFiles.recolor_sprite("user_interface", stat, Color.BLACK)
            surface.blit(stat_icon, rect)
            font.render(
                surface,
                str(self.get_stat(self.selected_shipgirl, stat)),
                (rect.right + Box.PADDING, rect.centery),
                Color.BLACK,
                1,
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
        surface.blit(DataFiles.sprites["equipment_menu"]["blueprint"], self.blueprint_page)
        faction_icon = DataFiles.sprites["user_interface"][f"{faction}_big"]
        faction_icon_rect = faction_icon.get_rect()
        faction_icon_rect.left = self.blueprint_page.left + Box.PADDING
        faction_icon_rect.top = self.blueprint_page.top + Box.PADDING
        surface.blit(DataFiles.sprites["user_interface"][f"{faction}_big"], faction_icon_rect)
        for i, (equipment, rect) in enumerate(zip(self.selected_shipgirl.battle_component.equipment, self.equipped_rects)):
            outline_width = Box.OUTLINE_WIDTH + int(self.selected_equipment == i)
            pygame.draw.rect(surface, Color.BLUEPRINT_PAGE_BACK, rect)
            pygame.draw.rect(surface, Color.WHITE, rect, width=outline_width)
            if equipment is not None:
                surface.blit(DataFiles.get_entity_sprite(equipment), rect)
        
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
            surface.blit(DataFiles.get_entity_sprite(equipment), rect)
        
        self.exit_equipment_menu_button.draw(surface, font)
