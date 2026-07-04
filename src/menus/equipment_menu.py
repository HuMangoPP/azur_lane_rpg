import math
import random
import pygame

from engine.util import get_rect, get_vec
from engine.button import Button

from src.constants import DataFiles, Color, Equipment, Stats, Box, screen_x, screen_y

from live2d.live2d import Live2D

class EquipmentMenu:
    UNEQUIP_ITEM = "__unequip_item__"

    def __init__(self, menu_manager):
        self.menu_manager = menu_manager

        self.selected_shipgirl = None

        blueprint_surf = DataFiles.sprites["equipment_menu"]["blueprint"]
        self.blueprint_page = blueprint_surf.get_rect()
        self.blueprint_page.left = screen_x(0.5) - Box.WIDTH
        self.blueprint_page.bottom = screen_y(0.5) + 1.25*Box.HEIGHT
        self.equipped_rects = [
            get_rect(
                width=Box.WIDTH, height=Box.HEIGHT,
                centerx=self.blueprint_page.centerx,
                centery=self.blueprint_page.bottom - 3*Box.HEIGHT
            ),
            get_rect(
                width=Box.WIDTH, height=Box.HEIGHT,
                centerx=self.blueprint_page.centerx - Box.WIDTH,
                centery=self.blueprint_page.bottom - Box.HEIGHT
            ),
            get_rect(
                width=Box.WIDTH, height=Box.HEIGHT,
                centerx=self.blueprint_page.centerx + Box.WIDTH,
                centery=self.blueprint_page.bottom - Box.HEIGHT
            ),
        ]
        self.selected_slot = Equipment.WEAPON

        num_equipment_per_row = 7
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
        self.dossier_bg = get_rect(
            width=self.dossier_page.width + 2*Box.PADDING,
            height=self.dossier_page.height + 2*Box.PADDING,
            center=self.dossier_page.center
        )
        dossier_bg_topleft = pygame.Vector2(self.dossier_bg.topleft)
        self.dossier_tab = [
            dossier_bg_topleft,
            dossier_bg_topleft + pygame.Vector2(Box.WIDTH+Box.PADDING, 0),
            dossier_bg_topleft + pygame.Vector2(Box.WIDTH-Box.PADDING, -Box.HEIGHT/3),
            dossier_bg_topleft + pygame.Vector2(0, -Box.HEIGHT/3)
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

    def get_stat_delta(self, shipgirl, stat):
        if self.hovered_equipment is None:
            return 0
        currently_equipped = shipgirl.battle_component.equipment[self.selected_slot]
        return (
            DataFiles.equipment_data.get(self.hovered_equipment, {}).get(stat, 0)
            - DataFiles.equipment_data.get(currently_equipped, {}).get(stat, 0)
        )

    def get_equippable_inventory(self):
        if self.selected_slot == Equipment.WEAPON:
            return [
                weapon_name for weapon_name, weapon_info in DataFiles.equipment_data.items()
                if DataFiles.save_file["equipment"].get(weapon_name, 0) > 0
                and weapon_info["type"] == "weapon"
                and weapon_info["equippable_by"] == self.selected_shipgirl.battle_component.hull_type
            ]
        else:
            return [
                aux_name for aux_name, aux_info in DataFiles.equipment_data.items()
                if DataFiles.save_file["equipment"].get(aux_name, 0) > 0
                and aux_info["type"] == "aux"
            ]

    def get_equippable_options(self):
        options = self.get_equippable_inventory()
        current_equipment = self.selected_shipgirl.battle_component.equipment[self.selected_slot]
        if current_equipment is not None:
            options = [self.UNEQUIP_ITEM] + options
        return options

    def update(self, dt, events):
        self.selected_shipgirl.rect.centerx = screen_x(0.25)
        self.selected_shipgirl.rect.bottom = screen_y(0.5) - Box.HEIGHT
        if self.selected_shipgirl.sprite is not None:
            self.selected_shipgirl.sprite.set_animation(Live2D.IDLE_ANIMATION)
        self.selected_shipgirl.animate(dt)
        
        equip_slots = [Equipment.WEAPON, Equipment.AUX1, Equipment.AUX2]
        equippable = self.get_equippable_options()
        for event in events:
            if event.type == pygame.MOUSEBUTTONUP:
                for equip_slot, rect in zip(equip_slots, self.equipped_rects):
                    if rect.collidepoint(event.pos):
                        self.selected_slot = equip_slot
                        DataFiles.sfx["click"].play()

                for new_equipment, rect in zip(equippable, self.equippable_rects):
                    if rect.collidepoint(event.pos):
                        current_equipment = self.selected_shipgirl.battle_component.equipment[self.selected_slot]
                        if current_equipment is not None:
                            DataFiles.save_file["equipment"][current_equipment] = DataFiles.save_file["equipment"].get(current_equipment, 0) + 1
                        if new_equipment == self.UNEQUIP_ITEM:
                            self.selected_shipgirl.battle_component.equipment[self.selected_slot] = None
                        else:
                            self.selected_shipgirl.battle_component.equipment[self.selected_slot] = new_equipment
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
        surface.fill((59, 31, 18))
        pygame.draw.rect(surface, Color.DOSSIER, self.dossier_bg)
        pygame.draw.polygon(surface, Color.DOSSIER, self.dossier_tab)
        misaligned_dossier_pages = [
            (-4, pygame.Vector2(-6, 7), (224, 218, 201)),
            (5, pygame.Vector2(8, -5), (235, 229, 212)),
            (-3, pygame.Vector2(2, 6), (244, 239, 224)),
        ]
        for rotated_angle, offset, color in misaligned_dossier_pages:
            pygame.draw.polygon(
                surface,
                color,
                Box.get_rotated_rect_polygon(self.dossier_page, rotated_angle, offset)
            )
        pygame.draw.rect(surface, Color.DOSSIER_PAGE, self.dossier_page)

        # TODO instead of the live2d model, draw a little plushie of the character
        self.selected_shipgirl.draw(surface, font)

        faction = DataFiles.shipgirl_data[self.selected_shipgirl.name]["faction"]
        font.render(surface,f"{faction} {self.selected_shipgirl.name}",(self.dossier_page.left+Box.PADDING, self.dossier_page.top+Box.PADDING),Color.BLACK,1)
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
            stat_text = str(self.selected_shipgirl.battle_component.stat(stat))
            font.render(
                surface,
                stat_text,
                (rect.right + Box.PADDING, rect.centery),
                Color.BLACK,
                1,
                style="centerleft"
            )
            stat_delta = self.get_stat_delta(self.selected_shipgirl, stat)
            if stat_delta > 0:
                center = pygame.Vector2(rect.left-Box.PADDING,rect.centery)
                pygame.draw.polygon(surface, (34, 178, 34), [
                    center+get_vec(length=Box.PADDING, angle=math.radians(30)),
                    center+get_vec(length=Box.PADDING, angle=math.radians(150)),
                    center+get_vec(length=Box.PADDING, angle=math.radians(270))
                ])
                font.render(
                    surface,
                    f"+{stat_delta}",
                    (rect.right + Box.PADDING + font.font_width*len(stat_text), rect.centery),
                    (34, 178, 34),
                    1,
                    style="centerleft"
                )
            elif stat_delta < 0:
                center = pygame.Vector2(rect.left-Box.PADDING,rect.centery)
                pygame.draw.polygon(surface, (178, 34, 34),[
                    center+get_vec(length=Box.PADDING, angle=math.radians(90)),
                    center+get_vec(length=Box.PADDING, angle=math.radians(210)),
                    center+get_vec(length=Box.PADDING, angle=math.radians(330))
                ])
                font.render(
                    surface,
                    str(stat_delta),
                    (rect.right + Box.PADDING + font.font_width*len(stat_text), rect.centery),
                    (178, 34, 34),
                    1,
                    style="centerleft"
                )

        overlay_paperclip_sprite = pygame.transform.rotate(
            DataFiles.sprites["user_interface"]["overlay_paperclip"],
            -90
        )
        overlay_paperclip_rect = overlay_paperclip_sprite.get_rect()
        overlay_paperclip_rect.right = self.dossier_page.right
        overlay_paperclip_rect.top = self.dossier_bg.top - 4 # TODO paper clip offset
        surface.blit(overlay_paperclip_sprite, overlay_paperclip_rect)
        
        misaligned_blueprint_pages = [
            (-6, pygame.Vector2(-5, 7), Color.BLUEPRINT_PAGE_BACK),
            (3, pygame.Vector2(8, -5), (34, 62, 125)),
            (-1, pygame.Vector2(4, 6), (45, 76, 145)),
        ]
        for rotated_angle, offset, color in misaligned_blueprint_pages:
            pygame.draw.polygon(
                surface,
                color,
                Box.get_rotated_rect_polygon(self.blueprint_page, rotated_angle, offset)
            )
        surface.blit(DataFiles.sprites["equipment_menu"]["blueprint"], self.blueprint_page)
        faction_icon = DataFiles.sprites["user_interface"][f"{faction}_big"]
        faction_icon_rect = faction_icon.get_rect()
        faction_icon_rect.left = self.blueprint_page.left + Box.PADDING
        faction_icon_rect.top = self.blueprint_page.top + Box.PADDING
        surface.blit(faction_icon, faction_icon_rect)
        font.render(surface,f"{faction} {self.selected_shipgirl.name}",(faction_icon_rect.right, faction_icon_rect.centery-font.font_height-2),Color.WHITE,1)
        ship_class = DataFiles.shipgirl_data[self.selected_shipgirl.name]["class"]
        hull_type = DataFiles.shipgirl_data[self.selected_shipgirl.name]["hull_type"]
        font.render(surface,f"{ship_class}-class {hull_type}",(faction_icon_rect.right, faction_icon_rect.centery+2),Color.WHITE,1)
        for i, (equipment, rect) in enumerate(zip(self.selected_shipgirl.battle_component.equipment, self.equipped_rects)):
            outline_width = Box.OUTLINE_WIDTH + int(self.selected_slot == i)
            pygame.draw.rect(surface, Color.BLUEPRINT_PAGE_BACK, rect)
            pygame.draw.rect(surface, Color.WHITE, rect, width=outline_width)
            if equipment is not None:
                surface.blit(DataFiles.get_entity_sprite(equipment), rect)

        overlay_pencil_sprite = DataFiles.sprites["user_interface"]["overlay_pencil"]
        overlay_pencil_rect = overlay_pencil_sprite.get_rect()
        overlay_pencil_rect.right = self.blueprint_page.right + Box.WIDTH/4 # TODO alignment
        overlay_pencil_rect.bottom = self.blueprint_page.bottom
        surface.blit(overlay_pencil_sprite, overlay_pencil_rect)

        overlay_compass_sprite = DataFiles.sprites["user_interface"]["overlay_compass"]
        overlay_compass_rect = overlay_compass_sprite.get_rect()
        overlay_compass_rect.left = self.blueprint_page.left - Box.WIDTH/4 # TODO alignment
        overlay_compass_rect.bottom = self.blueprint_page.bottom
        surface.blit(overlay_compass_sprite, overlay_compass_rect)
        
        equippable = self.get_equippable_options()
        pygame.draw.rect(surface, Color.CARGO_BOX_BACK, self.equipment_depot)
        for equipment, rect in zip(equippable, self.equippable_rects):
            pygame.draw.rect(surface, Color.CARGO_BOX, rect)
            if equipment == self.UNEQUIP_ITEM:
                surface.blit(DataFiles.sprites["user_interface"]["unequip_item"], rect)
            else:
                surface.blit(DataFiles.get_entity_sprite(equipment), rect)

        depot_decoration_top = self.equipment_depot.top - Box.WIDTH/8
        top_rope_sprite = DataFiles.sprites["user_interface"]["top_rope"]
        top_rope_rect = top_rope_sprite.get_rect()
        top_rope_rect.centerx = self.equipment_depot.centerx + Box.WIDTH
        top_rope_rect.top = depot_decoration_top
        surface.blit(top_rope_sprite, top_rope_rect)

        rope_hook_sprite = DataFiles.sprites["user_interface"]["rope_hook"]
        rope_hook_rect = rope_hook_sprite.get_rect()
        rope_hook_rect.left = self.equipment_depot.left + Box.WIDTH/2
        rope_hook_rect.top = depot_decoration_top
        surface.blit(rope_hook_sprite, rope_hook_rect)

        corner_rope_sprite = DataFiles.sprites["user_interface"]["corner_rope"]
        corner_rope_rect = corner_rope_sprite.get_rect()
        corner_rope_rect.right = self.equipment_depot.right + Box.WIDTH/8
        corner_rope_rect.top = depot_decoration_top
        surface.blit(corner_rope_sprite, corner_rope_rect)

        big_corner_rope_sprite = DataFiles.sprites["user_interface"]["big_corner_rope"]
        big_corner_rope_rect = big_corner_rope_sprite.get_rect()
        big_corner_rope_rect.right = self.equipment_depot.right + Box.WIDTH/8
        big_corner_rope_rect.top = depot_decoration_top
        surface.blit(big_corner_rope_sprite, big_corner_rope_rect)

        lightbulb_sprite = DataFiles.sprites["user_interface"]["lightbulb"]
        lightbulb_crop_rect = lightbulb_sprite.get_rect()
        lightbulb_crop_rect.top = lightbulb_crop_rect.height // 2
        lightbulb_crop_rect.height -= lightbulb_crop_rect.top
        lightbulb_rect = lightbulb_crop_rect.copy()
        lightbulb_rect.centerx = top_rope_rect.right
        lightbulb_rect.top = depot_decoration_top
        surface.blit(lightbulb_sprite, lightbulb_rect, lightbulb_crop_rect)

        lightbulb_light_sprite = DataFiles.sprites["user_interface"]["lightbulb_light"]
        lightbulb_light_rect = lightbulb_light_sprite.get_rect()
        lightbulb_light_rect.centerx = lightbulb_rect.centerx
        lightbulb_light_rect.bottom = lightbulb_rect.bottom + Box.HEIGHT/4
        surface.blit(lightbulb_light_sprite, lightbulb_light_rect, special_flags=pygame.BLEND_RGB_ADD)

        cargo_box_sprite = DataFiles.sprites["user_interface"]["cargo_box"]
        cargo_box_rect = cargo_box_sprite.get_rect()
        left_crate_stack = pygame.Vector2(self.equipment_depot.bottomleft)
        right_crate_stack = pygame.Vector2(self.equipment_depot.bottomright)
        for cargo_box_pos in [
            left_crate_stack,
            left_crate_stack + pygame.Vector2(cargo_box_rect.width, 0),
            left_crate_stack + pygame.Vector2(0, -cargo_box_rect.height),
            left_crate_stack + pygame.Vector2(0, -2*cargo_box_rect.height),
            left_crate_stack + pygame.Vector2(-cargo_box_rect.width, 0),
            left_crate_stack + pygame.Vector2(-cargo_box_rect.width, -cargo_box_rect.height),
            
            right_crate_stack,
            right_crate_stack + pygame.Vector2(-cargo_box_rect.width, 0),
            right_crate_stack + pygame.Vector2(-2*cargo_box_rect.width, 0),
            right_crate_stack + pygame.Vector2(0, -cargo_box_rect.height),
            right_crate_stack + pygame.Vector2(cargo_box_rect.width, 0),
            right_crate_stack + pygame.Vector2(cargo_box_rect.width, -cargo_box_rect.height),
            right_crate_stack + pygame.Vector2(cargo_box_rect.width/2, -2*cargo_box_rect.height),
        ]:
            cargo_box_rect.center = cargo_box_pos
            surface.blit(cargo_box_sprite, cargo_box_rect)
        
        self.exit_equipment_menu_button.draw(surface, font)
