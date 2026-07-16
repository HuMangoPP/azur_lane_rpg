import math
import random
import pygame

from engine.util import get_rect, get_vec
from engine.button import Button

from src.constants import DataFiles, Color, Equipment, Stats, Box, screen_x, screen_y

from live2d.live2d import Live2D

class EquipmentMenu:
    UNEQUIP_ITEM = "__unequip_item__"
    TABLETOP_COLOR = (171, 85, 33)
    TABLETOP_GRAIN_SEED = 0

    def __init__(self, menu_manager):
        self.menu_manager = menu_manager

        self.selected_shipgirl = None

        blueprint_surf = DataFiles.sprites["equipment_menu"]["blueprint"]
        self.blueprint_page = blueprint_surf.get_rect()
        self.blueprint_page.left = screen_x(0.5) - Box.WIDTH * 3/2
        self.blueprint_page.top = Box.TOP_OF_SCREEN - Box.PADDING
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
            right=self.blueprint_page.right,
            bottom=Box.BOTTOM_OF_SCREEN
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
            width=3*Box.WIDTH + 2*Box.PADDING,
            height=(
                2*Box.PADDING # padding
                + font_height+Box.PADDING # name
                + Box.HEIGHT/2 # exp
                + 2*Box.HEIGHT # stats
                + Box.HEIGHT
            ),
            centerx=screen_x(0.25),
            bottom=self.blueprint_page.bottom
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
            self.shipgirl_x = 0

        button_sprite = DataFiles.sprites["user_interface"]["prev"]
        button_rect = get_rect(width=48,height=48,right=Box.RIGHT_OF_SCREEN,top=Box.TOP_OF_SCREEN)
        self.exit_equipment_menu_button = Button(
            button_rect,
            exit_equipment_menu,
            background_styling={
                "background_color": Color.BLACK,
                "background_img": button_sprite,
                "opacity": 160
            },
            hover_styling={"opacity": 200}
        )

        self.shipgirl_x = None
        self.target_shipgirl_x = 0
        self.shipgirl_pause_time = 0

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

    def draw_tabletop(self, surface, tabletop_rect):
        grain_rng = random.Random(self.TABLETOP_GRAIN_SEED)
        y = tabletop_rect.top

        while y < tabletop_rect.bottom:
            band_height = min(grain_rng.randint(4, 24), tabletop_rect.bottom - y)
            color_offset = grain_rng.randint(-16, 16)
            color = (
                max(0, min(255, self.TABLETOP_COLOR[0] + color_offset)),
                max(0, min(255, self.TABLETOP_COLOR[1] + color_offset // 2)),
                max(0, min(255, self.TABLETOP_COLOR[2] + color_offset // 3)),
            )
            band_rect = get_rect(
                width=tabletop_rect.width,
                height=band_height,
                left=tabletop_rect.left,
                top=y
            )
            pygame.draw.rect(surface, color, band_rect)
            y += band_height

    def update(self, dt, events):
        if self.shipgirl_x is None:
            self.shipgirl_x = screen_x(0.5)
            self.target_shipgirl_x = self.shipgirl_x
            self.selected_shipgirl.rect.bottom = self.equipment_depot.bottom + Box.HEIGHT/4
        if self.shipgirl_pause_time > 0:
            self.shipgirl_pause_time -= dt
            self.selected_shipgirl.sprite.set_animation(Live2D.IDLE_ANIMATION)
        elif abs(self.target_shipgirl_x - self.selected_shipgirl.rect.centerx) < 10:
            self.shipgirl_pause_time = random.uniform(1, 3) # TODO clean up magic number
            self.target_shipgirl_x = random.uniform(Box.LEFT_OF_SCREEN, Box.RIGHT_OF_SCREEN)
        else:
            relx = self.target_shipgirl_x - self.selected_shipgirl.rect.centerx
            direction = relx / abs(relx)
            self.shipgirl_x += direction * 50 * dt # TODO clean up magic number
            self.selected_shipgirl.facing_left = direction < 0
            self.selected_shipgirl.sprite.set_animation(Live2D.WALK_ANIMATION)
        self.selected_shipgirl.rect.centerx = self.shipgirl_x
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
                self.exit_equipment_menu_button.hover(event.pos)
                
                for equipment, rect in zip(equippable, self.equippable_rects):
                    if rect.collidepoint(event.pos):
                        self.hovered_equipment = equipment
                        break
                else:
                    self.hovered_equipment = None

    def draw(self, surface, font_registry):
        # TODO clean up magic numbers
        floor_color = (71, 71, 71)
        wall_color = 105, 105, 105
        surface.fill(wall_color)

        workshop_floor = get_rect(
            width=screen_x(1), height=Box.HEIGHT,
            left=0, top=self.equipment_depot.bottom
        )
        pygame.draw.rect(surface, floor_color, workshop_floor)

        workshop_wall = get_rect(
            width=screen_x(1), height=2*Box.HEIGHT,
            left=0, bottom=workshop_floor.top
        )
        pygame.draw.rect(surface, wall_color, workshop_wall)

        workshop_ceiling = get_rect(
            width=screen_x(1), height=Box.HEIGHT/2,
            left=0, bottom=workshop_wall.top
        )
        pygame.draw.rect(surface, floor_color, workshop_ceiling)

        table_sprite = DataFiles.sprites["equipment_menu"]["table"]
        table_rect = table_sprite.get_rect()
        table_rect.bottom = workshop_floor.top + Box.PADDING
        table_rect.right = self.equipment_depot.left - 3/2 * Box.WIDTH
        surface.blit(table_sprite, table_rect)

        pegboard_sprite = DataFiles.sprites["equipment_menu"]["pegboard"]
        pegboard_rect = pegboard_sprite.get_rect()
        pegboard_rect.bottom = table_rect.top
        pegboard_rect.centerx = table_rect.centerx
        surface.blit(pegboard_sprite, pegboard_rect)

        paints_sprite = DataFiles.sprites["equipment_menu"]["paints"]
        paints_rect = paints_sprite.get_rect()
        paints_rect.centerx = table_rect.left
        paints_rect.bottom = table_rect.bottom
        surface.blit(paints_sprite, paints_rect)

        oil_drum_sprite = DataFiles.sprites["equipment_menu"]["oil_drum"]
        oil_drum_rect = oil_drum_sprite.get_rect()
        oil_drum_rect.right = table_rect.left - Box.WIDTH/2
        oil_drum_rect.bottom = table_rect.bottom
        surface.blit(oil_drum_sprite, oil_drum_rect)

        cabinet_sprite = DataFiles.sprites["equipment_menu"]["cabinet"]
        cabinet_rect = cabinet_sprite.get_rect()
        cabinet_rect.right = table_rect.left
        cabinet_rect.bottom = oil_drum_rect.top
        surface.blit(cabinet_sprite, cabinet_rect)

        lightbulb_sprite = DataFiles.sprites["equipment_menu"]["lightbulb"]
        lightbulb_rect = lightbulb_sprite.get_rect()
        lightbulb_rect.left = table_rect.centerx
        lightbulb_rect.top = workshop_wall.top - Box.PADDING
        surface.blit(lightbulb_sprite, lightbulb_rect)

        lightbulb_light_sprite = DataFiles.sprites["equipment_menu"]["lightbulb_light"]
        lightbulb_light_rect = lightbulb_light_sprite.get_rect()
        lightbulb_light_rect.centerx = lightbulb_rect.centerx
        lightbulb_light_rect.bottom = lightbulb_rect.bottom + Box.HEIGHT/4
        surface.blit(lightbulb_light_sprite, lightbulb_light_rect, special_flags=pygame.BLEND_RGB_ADD)

        equippable = self.get_equippable_options()
        pygame.draw.rect(surface, Color.CARGO_BOX_BACK, self.equipment_depot)
        for equipment, rect in zip(equippable, self.equippable_rects):
            pygame.draw.rect(surface, Color.CARGO_BOX, rect)
            if equipment == self.UNEQUIP_ITEM:
                surface.blit(DataFiles.sprites["user_interface"]["unequip_item"], rect)
            else:
                surface.blit(DataFiles.get_entity_sprite(equipment), rect)

        self.selected_shipgirl.draw(surface, font_registry)

        depot_decoration_top = self.equipment_depot.top - Box.WIDTH/8
        top_rope_sprite = DataFiles.sprites["props"]["top_rope"]
        top_rope_rect = top_rope_sprite.get_rect()
        top_rope_rect.left = self.equipment_depot.centerx + Box.WIDTH/2
        top_rope_rect.top = depot_decoration_top
        surface.blit(top_rope_sprite, top_rope_rect)

        big_top_rope_sprite = DataFiles.sprites["props"]["big_top_rope"]
        big_top_rope_rect = big_top_rope_sprite.get_rect()
        big_top_rope_rect.right = self.equipment_depot.centerx - Box.WIDTH/2
        big_top_rope_rect.top = depot_decoration_top
        surface.blit(big_top_rope_sprite, big_top_rope_rect)

        rope_hook_sprite = DataFiles.sprites["props"]["rope_hook"]
        rope_hook_rect = rope_hook_sprite.get_rect()
        rope_hook_rect.left = self.equipment_depot.left + Box.WIDTH/2
        rope_hook_rect.top = depot_decoration_top
        surface.blit(rope_hook_sprite, rope_hook_rect)

        corner_rope_sprite = DataFiles.sprites["props"]["corner_rope"]
        corner_rope_rect = corner_rope_sprite.get_rect()
        corner_rope_rect.right = self.equipment_depot.right + Box.WIDTH/8
        corner_rope_rect.top = depot_decoration_top
        surface.blit(corner_rope_sprite, corner_rope_rect)

        big_corner_rope_sprite = DataFiles.sprites["props"]["big_corner_rope"]
        big_corner_rope_rect = big_corner_rope_sprite.get_rect()
        big_corner_rope_rect.right = self.equipment_depot.right + Box.WIDTH/8
        big_corner_rope_rect.top = depot_decoration_top
        surface.blit(big_corner_rope_sprite, big_corner_rope_rect)

        lightbulb_sprite = DataFiles.sprites["props"]["lightbulb"]
        lightbulb_crop_rect = lightbulb_sprite.get_rect()
        lightbulb_crop_rect.top = lightbulb_crop_rect.height / 2
        lightbulb_crop_rect.height = lightbulb_crop_rect.height / 2
        lightbulb_rect = lightbulb_crop_rect.copy()
        lightbulb_rect.centerx = top_rope_rect.right
        lightbulb_rect.top = depot_decoration_top
        surface.blit(lightbulb_sprite, lightbulb_rect, lightbulb_crop_rect)

        lightbulb_light_sprite = DataFiles.sprites["props"]["lightbulb_light"]
        lightbulb_light_rect = lightbulb_light_sprite.get_rect()
        lightbulb_light_rect.centerx = lightbulb_rect.centerx
        lightbulb_light_rect.bottom = lightbulb_rect.bottom + Box.HEIGHT/4
        surface.blit(lightbulb_light_sprite, lightbulb_light_rect, special_flags=pygame.BLEND_RGB_ADD)

        cargo_box_sprite = DataFiles.sprites["props"]["cargo_box"]
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

        tabletop_rect = get_rect(
            width=screen_x(1) - 2*Box.WIDTH,
            height=workshop_ceiling.top,
            left=Box.WIDTH, top=0
        )
        self.draw_tabletop(surface, tabletop_rect)

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

        faction = DataFiles.shipgirl_data[self.selected_shipgirl.name]["faction"]
        font_registry["big_pixel"].render(surface,f"{faction} {self.selected_shipgirl.name}",(self.dossier_page.left+Box.PADDING, self.dossier_page.top+Box.PADDING),Color.BLACK,1)
        level = Stats.level(self.selected_shipgirl.battle_component.exp) + 1
        medal_icon = DataFiles.sprites["user_interface"]["medal"]
        medal_rect = medal_icon.get_rect()
        medal_rect.left = self.dossier_page.left + Box.PADDING
        medal_rect.centery = self.exp_bar_bg.centery
        surface.blit(medal_icon, medal_rect)
        font_registry["big_pixel"].render(
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
            font_registry["big_pixel"].render(
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
                font_registry["big_pixel"].render(
                    surface,
                    f"+{stat_delta}",
                    (rect.right + Box.PADDING + font_registry["big_pixel"].font_width*len(stat_text), rect.centery),
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
                font_registry["big_pixel"].render(
                    surface,
                    str(stat_delta),
                    (rect.right + Box.PADDING + font_registry["big_pixel"].font_width*len(stat_text), rect.centery),
                    (178, 34, 34),
                    1,
                    style="centerleft"
                )

        classified_sprite = DataFiles.sprites["props"]["classified"]
        classified_rect = classified_sprite.get_rect()
        classified_rect.topright = self.dossier_bg.topright
        surface.blit(classified_sprite, classified_rect)

        coffee_ring_sprite = DataFiles.sprites["props"]["coffee_ring"]
        coffee_ring_rect = coffee_ring_sprite.get_rect()
        coffee_ring_rect.bottomleft = self.dossier_bg.bottomleft
        surface.blit(coffee_ring_sprite, coffee_ring_rect)

        paperclip_sprite = pygame.transform.rotate(
            DataFiles.sprites["props"]["paperclip"],
            -90
        )
        paperclip_rect = paperclip_sprite.get_rect()
        paperclip_rect.right = self.dossier_page.right
        paperclip_rect.top = self.dossier_bg.top - 4 # TODO paper clip offset magic number
        surface.blit(paperclip_sprite, paperclip_rect)
        
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
        font_registry["big_pixel"].render(surface,f"{faction} {self.selected_shipgirl.name}",(faction_icon_rect.right, faction_icon_rect.centery-font_registry["big_pixel"].font_height-2),Color.WHITE,1)
        ship_class = DataFiles.shipgirl_data[self.selected_shipgirl.name]["class"]
        hull_type = DataFiles.shipgirl_data[self.selected_shipgirl.name]["hull_type"]
        font_registry["big_pixel"].render(surface,f"{ship_class}-class {hull_type}",(faction_icon_rect.right, faction_icon_rect.centery+2),Color.WHITE,1)
        for i, (equipment, rect) in enumerate(zip(self.selected_shipgirl.battle_component.equipment, self.equipped_rects)):
            pygame.draw.rect(
                surface,
                Color.BLUEPRINT_PAGE_GLOW if self.selected_slot == i else Color.BLUEPRINT_PAGE_BACK,
                rect
            )
            if equipment is not None:
                surface.blit(DataFiles.get_entity_sprite(equipment), rect)
            if self.selected_slot == i:
                pygame.draw.rect(surface, Color.BLUEPRINT_SLOT_BORDER_GLOW, rect, width=Box.OUTLINE_WIDTH)
                slot_glow = DataFiles.sprites["user_interface"]["blueprint_slot_glow"]
                slot_glow_rect = slot_glow.get_rect()
                slot_glow_rect.bottomleft = rect.topleft
                surface.blit(slot_glow, slot_glow_rect, special_flags=pygame.BLEND_RGB_ADD)

        pencil_sprite = DataFiles.sprites["props"]["pencil"]
        pencil_rect = pencil_sprite.get_rect()
        pencil_rect.right = self.blueprint_page.right + Box.WIDTH/4 # TODO alignment magic number
        pencil_rect.bottom = self.blueprint_page.bottom

        ruler_sprite = DataFiles.sprites["props"]["ruler"]
        ruler_rect = ruler_sprite.get_rect()
        ruler_rect.midbottom = pencil_rect.bottomleft
        surface.blit(ruler_sprite, ruler_rect)
        surface.blit(pencil_sprite, pencil_rect)

        compass_sprite = DataFiles.sprites["props"]["compass"]
        compass_rect = compass_sprite.get_rect()
        compass_rect.left = self.blueprint_page.left - Box.WIDTH/4 # TODO alignment magic number
        compass_rect.bottom = self.blueprint_page.bottom
        surface.blit(compass_sprite, compass_rect)
        
        # section divider
        pygame.draw.line(surface, Color.BLACK, workshop_ceiling.topleft, workshop_ceiling.topright, width=4)

        self.exit_equipment_menu_button.draw(surface, font_registry)
