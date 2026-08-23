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
    HULL_TYPE_MAPPING = {
        "DD": "destroyer",
        "CL": "light cruiser",
        "CA": "heavy cruiser",
        "BB": "battleship",
        "SS": "submarine",
        "CV": "aircraft carrier",
    }
    SLOT_LABELS = {
        Equipment.WEAPON: "main",
        Equipment.AUX1: "aux 1",
        Equipment.AUX2: "aux 2",
    }

    def __init__(self, menu_manager):
        self.menu_manager = menu_manager

        self.selected_shipgirl = None


        self.blueprint_page = get_rect(
            width=7*Box.WIDTH + 2*Box.PADDING,
            height=4.5*Box.WIDTH + 2*Box.PADDING,
            left=screen_x(0.5) - Box.WIDTH * 3/2,
            top=2*Box.PADDING,
        )
        self.equipped_rects = [
            get_rect(
                width=Box.WIDTH, height=Box.HEIGHT,
                centerx=self.blueprint_page.centerx,
                centery=self.blueprint_page.bottom - 3*Box.HEIGHT - Box.PADDING
            ),
            get_rect(
                width=Box.WIDTH, height=Box.HEIGHT,
                centerx=self.blueprint_page.centerx - Box.WIDTH,
                centery=self.blueprint_page.bottom - Box.HEIGHT - Box.PADDING
            ),
            get_rect(
                width=Box.WIDTH, height=Box.HEIGHT,
                centerx=self.blueprint_page.centerx + Box.WIDTH,
                centery=self.blueprint_page.bottom - Box.HEIGHT - Box.PADDING
            ),
        ]
        self.selected_slot = Equipment.WEAPON

        num_equipment_per_row = 7
        num_equipment_rows = 2
        equipment_depot_content_height = num_equipment_rows*(Box.HEIGHT+Box.PADDING)+Box.PADDING
        self.equipment_depot = get_rect(
            width=num_equipment_per_row*(Box.WIDTH+Box.PADDING)+Box.PADDING,
            height=equipment_depot_content_height,
            right=self.blueprint_page.right + Box.WIDTH/2,
            top=Box.BOTTOM_OF_SCREEN-equipment_depot_content_height
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
        self.equipment_pages = {}

        self.equipment_page_prev_button = Button(
            get_rect(width=48, height=48, left=0, top=0),
            lambda: self.change_equipment_page(-1),
            active=False,
            background_styling={
                "background_color": Color.WHITE,
                "background_img": DataFiles.sprites["user_interface"]["prev"],
                "opacity": 0,
            },
            hover_styling={"opacity": 32}
        )
        self.equipment_page_next_button = Button(
            get_rect(width=48, height=48, left=0, top=0),
            lambda: self.change_equipment_page(1),
            active=False,
            background_styling={
                "background_color": Color.WHITE,
                "background_img": DataFiles.sprites["user_interface"]["next"],
                "opacity": 0,
            },
            hover_styling={"opacity": 32}
        )

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
            self.shipgirl_x = None

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
        self.blueprint_effect_time = 0

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
            options = options + [self.UNEQUIP_ITEM]
        return options

    def get_equipment_page_count(self, equippable=None):
        if equippable is None:
            equippable = self.get_equippable_options()

        return max(1, math.ceil(len(equippable) / len(self.equippable_rects)))

    def get_equipment_page(self, equippable=None):
        page_count = self.get_equipment_page_count(equippable)
        page = min(self.equipment_pages.get(self.selected_slot, 0), page_count - 1)
        page = max(0, page)
        self.equipment_pages[self.selected_slot] = page
        return page

    def get_visible_equippable_options(self, equippable=None):
        if equippable is None:
            equippable = self.get_equippable_options()

        page = self.get_equipment_page(equippable)
        page_size = len(self.equippable_rects)
        start = page * page_size
        return equippable[start:start + page_size]

    def position_equipment_page_buttons(self):
        self.equipment_page_prev_button.rect.center = self.equipment_depot.bottomleft
        self.equipment_page_next_button.rect.center = self.equipment_depot.bottomright

    def refresh_equipment_page_buttons(self):
        equippable = self.get_equippable_options()
        page_count = self.get_equipment_page_count(equippable)
        page = self.get_equipment_page(equippable)
        self.position_equipment_page_buttons()
        self.equipment_page_prev_button.active = page_count > 1 and page > 0
        self.equipment_page_next_button.active = page_count > 1 and page < page_count - 1

    def change_equipment_page(self, delta):
        equippable = self.get_equippable_options()
        page_count = self.get_equipment_page_count(equippable)
        page = self.get_equipment_page(equippable)
        self.equipment_pages[self.selected_slot] = min(page_count - 1, max(0, page + delta))
        self.refresh_equipment_page_buttons()

    def draw_equipment_page_buttons(self, surface, font_registry):
        self.refresh_equipment_page_buttons()
        if self.get_equipment_page_count() <= 1:
            return

        self.equipment_page_prev_button.draw(surface, font_registry)
        self.equipment_page_next_button.draw(surface, font_registry)

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
        self.blueprint_effect_time = (self.blueprint_effect_time + dt) % 12
        if self.shipgirl_x is None:
            self.shipgirl_x = screen_x(0.5)
            self.target_shipgirl_x = self.shipgirl_x
            self.selected_shipgirl.rect.bottom = self.equipment_depot.bottom + Box.HEIGHT/2.5
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
        for event in events:
            if event.type == pygame.MOUSEBUTTONUP:
                self.refresh_equipment_page_buttons()
                if (
                    self.equipment_page_prev_button.click(event.pos)
                    or self.equipment_page_next_button.click(event.pos)
                ):
                    DataFiles.sfx["click"].play()
                    continue

                for equip_slot, rect in zip(equip_slots, self.equipped_rects):
                    if rect.collidepoint(event.pos):
                        self.selected_slot = equip_slot
                        self.refresh_equipment_page_buttons()
                        DataFiles.sfx["click"].play()

                for new_equipment, rect in zip(self.get_visible_equippable_options(), self.equippable_rects):
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
                self.refresh_equipment_page_buttons()
                self.equipment_page_prev_button.hover(event.pos)
                self.equipment_page_next_button.hover(event.pos)
                
                for equipment, rect in zip(self.get_visible_equippable_options(), self.equippable_rects):
                    if rect.collidepoint(event.pos):
                        self.hovered_equipment = equipment
                        break
                else:
                    self.hovered_equipment = None

    @staticmethod
    def draw_blueprint_corner_brackets(surface, rect, color, length=8):
        corners = [
            (rect.topleft, (1, 1)),
            (rect.topright, (-1, 1)),
            (rect.bottomleft, (1, -1)),
            (rect.bottomright, (-1, -1)),
        ]
        for corner, direction in corners:
            corner = pygame.Vector2(corner)
            dx, dy = direction
            pygame.draw.line(surface, color, corner, corner + pygame.Vector2(dx*length, 0))
            pygame.draw.line(surface, color, corner, corner + pygame.Vector2(0, dy*length))

    @staticmethod
    def draw_dashed_rect(surface, color, rect, dash_length=8, gap_length=4, width=2):
        dash_step = dash_length + gap_length
        right = rect.right - 1
        bottom = rect.bottom - 1
        for x in range(rect.left, rect.right, dash_step):
            dash_right = min(x + dash_length, right)
            pygame.draw.line(surface, color, (x, rect.top), (dash_right, rect.top), width)
            pygame.draw.line(surface, color, (x, bottom), (dash_right, bottom), width)
        for y in range(rect.top, rect.bottom, dash_step):
            dash_bottom = min(y + dash_length, bottom)
            pygame.draw.line(surface, color, (rect.left, y), (rect.left, dash_bottom), width)
            pygame.draw.line(surface, color, (right, y), (right, dash_bottom), width)

    def draw_blueprint_page(self, surface):
        misaligned_pages = [
            (-6, pygame.Vector2(-5, 7), Color.BLUEPRINT_PAGE_BACK),
            (3, pygame.Vector2(8, -5), (34, 62, 125)),
            (-1, pygame.Vector2(4, 6), (45, 76, 145)),
        ]
        for rotated_angle, offset, color in misaligned_pages:
            pygame.draw.polygon(
                surface,
                color,
                Box.get_rotated_rect_polygon(self.blueprint_page, rotated_angle, offset),
            )
        pygame.draw.rect(surface, Color.BLUEPRINT_PAGE, self.blueprint_page)

        grid_step = 2*Box.PADDING
        for index, x in enumerate(range(
            self.blueprint_page.left + grid_step + Box.PADDING,
            self.blueprint_page.right - Box.PADDING,
            grid_step,
        ), 1):
            color = Color.BLUEPRINT_GRID_MAJOR if index % 4 == 0 else Color.BLUEPRINT_GRID_MINOR
            pygame.draw.line(
                surface,
                color,
                (x, self.blueprint_page.top),
                (x, self.blueprint_page.bottom),
            )
        for index, y in enumerate(range(
            self.blueprint_page.top + grid_step + Box.PADDING,
            self.blueprint_page.bottom - Box.PADDING,
            grid_step,
        ), 1):
            color = Color.BLUEPRINT_GRID_MAJOR if index % 4 == 0 else Color.BLUEPRINT_GRID_MINOR
            pygame.draw.line(
                surface,
                color,
                (self.blueprint_page.left, y),
                (self.blueprint_page.right, y),
            )

        inset_rect = self.blueprint_page.inflate(-2*Box.PADDING, -2*Box.PADDING)
        pygame.draw.rect(
            surface,
            Color.BLUEPRINT_GRID_MAJOR,
            inset_rect,
            width=Box.OUTLINE_WIDTH,
        )

    def draw_blueprint_schematics(self, surface):
        side_schematic = DataFiles.sprites["equipment_menu"]["side_schematic"]
        side_schematic_rect = side_schematic.get_rect()
        side_schematic_rect.left = self.blueprint_page.left
        side_schematic_rect.centery = self.equipped_rects[0].centery
        surface.blit(side_schematic, side_schematic_rect)

        top_schematic = DataFiles.sprites["equipment_menu"]["top_schematic"]
        top_schematic_rect = top_schematic.get_rect()
        top_schematic_rect.left = self.blueprint_page.left
        top_schematic_rect.centery = self.equipped_rects[-1].centery
        surface.blit(top_schematic, top_schematic_rect)

    def draw_blueprint_identity(self, surface, font_registry):
        shipgirl_data = DataFiles.shipgirl_data[self.selected_shipgirl.name]
        faction = shipgirl_data["faction"]
        ship_class = shipgirl_data["class"].replace("_", " ")
        hull_type = shipgirl_data["hull_type"]
        hull_name = self.HULL_TYPE_MAPPING.get(hull_type, hull_type)

        faction_icon = DataFiles.sprites["user_interface"][f"{faction}_big"]
        faction_icon_rect = faction_icon.get_rect(
            left=self.blueprint_page.left + Box.PADDING,
            top=self.blueprint_page.top + Box.PADDING,
        )
        font = font_registry["big_pixel"]
        text_left = faction_icon_rect.right + Box.PADDING
        text_right = self.blueprint_page.right - 2*Box.PADDING
        text_width = text_right - text_left
        heading_top = self.blueprint_page.top + 2*Box.PADDING
        display_name = self.selected_shipgirl.name.replace("_", " ")
        name_scale = 2 if font.get_width(display_name, 2, 0) <= text_width else 1
        name_top = heading_top + font.font_height + 2
        classification_top = name_top + name_scale*font.font_height + 2

        surface.blit(faction_icon, faction_icon_rect)
        self.draw_blueprint_corner_brackets(
            surface,
            faction_icon_rect,
            Color.BLUEPRINT_GRID_MAJOR,
            length=Box.PADDING,
        )
        font.render(
            surface,
            f"refit schematic // {faction}",
            (text_left, heading_top),
            Color.BLUEPRINT_INK_MUTED,
            1,
        )
        font.render(
            surface,
            display_name,
            (text_left, name_top),
            Color.BLUEPRINT_SLOT_BORDER_GLOW,
            name_scale,
        )
        font.render(
            surface,
            f"{ship_class}-class // {hull_name} [{hull_type}]",
            (text_left, classification_top),
            Color.BLUEPRINT_INK_MUTED,
            1,
        )

    def draw_blueprint_slot_selection(self, surface, rect):
        pulse = (math.sin(self.blueprint_effect_time * math.tau / 2.4) + 1) / 2
        beacon_base = DataFiles.sprites["user_interface"]["blueprint_slot_glow"].copy()
        beacon_base.set_alpha(int(128 + 127*pulse))
        beacon = pygame.Surface(beacon_base.get_size())
        beacon.blit(beacon_base)
        beacon_rect = beacon.get_rect()
        beacon_rect.bottomleft = rect.topleft
        surface.blit(beacon, beacon_rect, special_flags=pygame.BLEND_RGB_ADD)

        pygame.draw.rect(
            surface,
            Color.BLUEPRINT_SLOT_BORDER_GLOW,
            rect,
            width=Box.OUTLINE_WIDTH,
        )

        glint_cycle = 0.9
        glint_lifetime = 0.7
        glint_max_length = 5
        glint_drift = 12
        for glint_index in range(4):
            glint_time = self.blueprint_effect_time + glint_index*glint_cycle/4
            glint_age = glint_time % glint_cycle
            if glint_age >= glint_lifetime:
                continue

            cycle_index = math.floor(glint_time / glint_cycle)
            glint_progress = glint_age / glint_lifetime
            glint_strength = (1 - glint_progress)**1.5
            spawn_center = pygame.Vector2(
                beacon_rect.left + 6 + (cycle_index*29 + glint_index*17) % (beacon_rect.width - 12),
                beacon_rect.top + beacon_rect.height/2 + 4 + (cycle_index*19 + glint_index*31) % (1.5*beacon_rect.height - 8),
            )
            center = spawn_center - pygame.Vector2(0, glint_drift*glint_progress)
            glint_length = 1 + round((glint_max_length - 1)*glint_strength)
            glint_color = tuple(
                round(channel*glint_strength)
                for channel in Color.BLUEPRINT_SLOT_BORDER_GLOW
            )
            glint_surface = pygame.Surface(
                (2*glint_max_length + 1, 2*glint_max_length + 1)
            )
            glint_surface_center = pygame.Vector2(glint_max_length, glint_max_length)
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

    def draw_blueprint_slots(self, surface, font_registry):
        equipment_slots = self.selected_shipgirl.battle_component.equipment
        for slot, (equipment, rect) in enumerate(zip(equipment_slots, self.equipped_rects)):
            slot_color = (
                Color.BLUEPRINT_PAGE_GLOW
                if self.selected_slot == slot
                else Color.BLUEPRINT_TITLE_BLOCK
            )
            pygame.draw.rect(surface, slot_color, rect)
            if equipment is None:
                label_y = rect.centery - font_registry["big_pixel"].font_height/2 - 2
                font_registry["big_pixel"].render(
                    surface,
                    self.SLOT_LABELS[slot],
                    (rect.centerx, label_y),
                    Color.BLUEPRINT_SLOT_BORDER_GLOW,
                    1,
                    style="center",
                )
                font_registry["pixel"].render(
                    surface,
                    "vacant",
                    (rect.centerx, rect.centery + font_registry["pixel"].font_height),
                    Color.BLUEPRINT_INK_MUTED,
                    1,
                    style="center",
                )
            else:
                equipment_sprite = DataFiles.get_entity_sprite(equipment)
                surface.blit(equipment_sprite, equipment_sprite.get_rect(center=rect.center))

            if self.selected_slot == slot:
                self.draw_blueprint_slot_selection(surface, rect)
            else:
                self.draw_dashed_rect(
                    surface,
                    Color.BLUEPRINT_INK_MUTED,
                    rect,
                    width=Box.OUTLINE_WIDTH,
                )

    def draw_blueprint_tools(self, surface):
        page_bottom = self.blueprint_page.bottom + Box.HEIGHT/2

        pencil_sprite = DataFiles.sprites["props"]["pencil"]
        pencil_rect = pencil_sprite.get_rect()
        pencil_rect.right = self.blueprint_page.right + Box.WIDTH/4
        pencil_rect.bottom = page_bottom

        ruler_sprite = DataFiles.sprites["props"]["ruler"]
        ruler_rect = ruler_sprite.get_rect()
        ruler_rect.midbottom = pencil_rect.bottomleft
        surface.blit(ruler_sprite, ruler_rect)
        surface.blit(pencil_sprite, pencil_rect)

        compass_sprite = DataFiles.sprites["props"]["compass"]
        compass_rect = compass_sprite.get_rect()
        compass_rect.left = self.blueprint_page.left - Box.WIDTH/4
        compass_rect.bottom = page_bottom
        surface.blit(compass_sprite, compass_rect)

    def draw_blueprint(self, surface, font_registry):
        self.draw_blueprint_page(surface)
        self.draw_blueprint_schematics(surface)
        self.draw_blueprint_identity(surface, font_registry)
        self.draw_blueprint_slots(surface, font_registry)
        self.draw_blueprint_tools(surface)

    def draw(self, surface, font_registry):
        # TODO clean up magic numbers
        floor_color = (71, 71, 71)
        wall_color = (105, 105, 105)
        surface.fill(wall_color)

        workshop_floor = get_rect(
            width=screen_x(1), height=Box.HEIGHT,
            left=0, top=self.equipment_depot.bottom
        )
        workshop_wall = get_rect(
            width=screen_x(1), height=2*Box.HEIGHT,
            left=0, bottom=workshop_floor.top
        )
        workshop_ceiling = get_rect(
            width=screen_x(1), height=Box.HEIGHT/2,
            left=0, bottom=workshop_wall.top
        )

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

        self.draw_blueprint(surface, font_registry)

        pygame.draw.rect(surface, floor_color, workshop_floor)
        pygame.draw.rect(surface, wall_color, workshop_wall)
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

        equippable = self.get_visible_equippable_options()
        self.refresh_equipment_page_buttons()
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

        rope_hook_sprite = DataFiles.sprites["props"]["short_rope_hook"]
        rope_hook_rect = rope_hook_sprite.get_rect()
        rope_hook_rect.left = self.equipment_depot.left + Box.WIDTH/2
        rope_hook_rect.top = depot_decoration_top
        surface.blit(rope_hook_sprite, rope_hook_rect)

        sign_rect = get_rect(
            width=Box.WIDTH,
            height=Box.HEIGHT,
            centerx=rope_hook_rect.centerx,
            bottom=rope_hook_rect.bottom
        )
        font = font_registry["big_pixel"]
        font.render(
            surface,
            "depot",
            (sign_rect.centerx, sign_rect.centery - 1.25*font.font_height),
            Color.BLACK,
            1,
            style="center"
        )
        font.render(
            surface,
            str(self.get_equipment_page() + 1),
            (sign_rect.centerx, sign_rect.centery + font.font_height/2),
            Color.BLACK,
            2,
            style="center"
        )

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
        self.draw_equipment_page_buttons(surface, font_registry)
        
        # section divider
        pygame.draw.line(surface, Color.BLACK, workshop_ceiling.topleft, workshop_ceiling.topright, width=4)

        self.exit_equipment_menu_button.draw(surface, font_registry)
