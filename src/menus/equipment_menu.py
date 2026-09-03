from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from engine.font import Font
    from src.menus.menu_manager import MenuManager
    from src.shipgirls import Shipgirl

import math
import random
import pygame

from engine.util import get_rect, get_vec, draw_dashed_rect
from engine.button import RectangularButton

from src.constants import DataFiles, Color, Equipment, Stats, Box, screen_x, screen_y
from src.menus.base_menu import Menu
from live2d.live2d import Live2D


class EquipmentMenu(Menu):
    UNEQUIP_ITEM = "__unequip_item__"
    TABLETOP_COLOR = (171, 85, 33)
    TABLETOP_GRAIN_SEED = 0
    SELECTION_ACTIVATION_DURATION = 0.22
    SLOT_LABELS = {
        Equipment.WEAPON: "main",
        Equipment.AUX1: "aux 1",
        Equipment.AUX2: "aux 2",
    }
    DOSSIER_STAT_LABELS = {
        "max_hp": "structural integrity",
        "evasion": "maneuverability",
        "firepower": "firepower",
        "reload": "reload cycle",
    }

    def __init__(self, menu_manager: MenuManager):
        self.menu_manager = menu_manager

        self.selected_shipgirl: Shipgirl | None = None

        # Blueprint page-themed component.
        self.blueprint_page = get_rect(
            width=7 * Box.WIDTH + 2 * Box.PADDING,
            height=4.5 * Box.WIDTH + 2 * Box.PADDING,
            left=screen_x(0.5) - 1.5 * Box.WIDTH,
            top=2 * Box.PADDING,
        )
        self.equipped_rects = [
            get_rect(
                width=Box.WIDTH, height=Box.HEIGHT,
                centerx=self.blueprint_page.centerx,
                centery=self.blueprint_page.bottom - 3 * Box.HEIGHT - Box.PADDING
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

        # Lazily populated blueprint layers. The selection glow remains live so
        # its pulse and activation animation are not frozen into the cache.
        self._blueprint_static_surface: pygame.Surface | None = None
        self._blueprint_composite_surface: pygame.Surface | None = None
        self._blueprint_foreground_surface: pygame.Surface | None = None
        self._blueprint_static_bounds: pygame.Rect | None = None
        self._blueprint_cache_bounds: pygame.Rect | None = None
        self._blueprint_foreground_bounds: pygame.Rect | None = None
        self._blueprint_static_key: tuple | None = None
        self._blueprint_render_key: tuple | None = None

        # Warehouse-themed equipment depot component.
        num_equipment_per_row = 7
        num_equipment_rows = 2
        equipment_depot_content_height = num_equipment_rows * (Box.HEIGHT + Box.PADDING) + Box.PADDING
        self.equipment_depot = get_rect(
            width=num_equipment_per_row * (Box.WIDTH + Box.PADDING) + Box.PADDING,
            height=equipment_depot_content_height,
            right=self.blueprint_page.right + Box.WIDTH / 2,
            top=Box.BOTTOM_OF_SCREEN - equipment_depot_content_height
        )
        self.equippable_rects = [
            get_rect(
                width=Box.WIDTH, height=Box.HEIGHT,
                left=self.equipment_depot.left + Box.PADDING + (i % num_equipment_per_row) * (Box.WIDTH + Box.PADDING),
                top=self.equipment_depot.top + Box.PADDING + (i // num_equipment_per_row) * (Box.HEIGHT + Box.PADDING) 
            )
            for i in range(num_equipment_per_row * num_equipment_rows)
        ]
        self.hovered_equipment = None
        self.equipment_pages = {}

        # Equipment depot pagination controls.
        pagination_button_size = 48
        self.equipment_page_prev_button = RectangularButton(
            get_rect(width=pagination_button_size, height=pagination_button_size, left=0, top=0),
            lambda: self._change_equipment_page(-1),
            active=False,
            background_styling={
                "background_color": Color.WHITE,
                "background_img": DataFiles.sprites["user_interface"]["prev"],
                "opacity": 0,
            },
            hover_styling={"opacity": 32}
        )
        self.equipment_page_next_button = RectangularButton(
            get_rect(width=pagination_button_size, height=pagination_button_size, left=0, top=0),
            lambda: self._change_equipment_page(1),
            active=False,
            background_styling={
                "background_color": Color.WHITE,
                "background_img": DataFiles.sprites["user_interface"]["next"],
                "opacity": 0,
            },
            hover_styling={"opacity": 32}
        )

        # Dossier-themed UI component.
        self.dossier_page = get_rect(
            width=3 * Box.WIDTH + 2 * Box.PADDING,
            height=4.5 * Box.HEIGHT,
            centerx=screen_x(0.25),
            bottom=self.blueprint_page.bottom + Box.PADDING
        )
        self.dossier_bg = get_rect(
            width=self.dossier_page.width + 2 * Box.PADDING,
            height=self.dossier_page.height + 2 * Box.PADDING,
            center=self.dossier_page.center
        )
        dossier_bg_topleft = pygame.Vector2(self.dossier_bg.topleft)
        self.dossier_tab = [
            dossier_bg_topleft,
            dossier_bg_topleft + pygame.Vector2(Box.WIDTH + Box.PADDING, 0),
            dossier_bg_topleft + pygame.Vector2(Box.WIDTH - Box.PADDING, -Box.HEIGHT / 3),
            dossier_bg_topleft + pygame.Vector2(0, -Box.HEIGHT / 3)
        ]

        dossier_content_left = self.dossier_page.left + Box.PADDING
        dossier_content_width = self.dossier_page.width - 2 * Box.PADDING
        self.dossier_header = get_rect(
            width=dossier_content_width,
            height=68,
            left=dossier_content_left,
            top=self.dossier_page.top + Box.PADDING,
        )
        self.dossier_progress = get_rect(
            width=dossier_content_width,
            height=50,
            left=dossier_content_left,
            top=self.dossier_header.bottom + 4,
        )
        self.dossier_capabilities = get_rect(
            width=dossier_content_width,
            height=150,
            left=dossier_content_left,
            top=self.dossier_progress.bottom + 6,
        )
        self.exp_bar_bg = get_rect(
            width=116,
            height=10,
            right=self.dossier_progress.right,
            top=self.dossier_progress.top + 32,
        )

        stat_row_height = 32
        stat_rows_top = self.dossier_capabilities.top + 14
        self.stat_row_rects = {
            stat: get_rect(
                width=dossier_content_width,
                height=stat_row_height,
                left=dossier_content_left,
                top=stat_rows_top + i * stat_row_height,
            )
            for i, stat in enumerate(self.DOSSIER_STAT_LABELS)
        }
        self.stat_rects = {
            stat: get_rect(
                width=Box.WIDTH / 2,
                height=Box.HEIGHT / 2,
                left=self.dossier_page.left + 3 * Box.PADDING,
                centery=self.stat_row_rects[stat].centery,
            )
            for stat in self.DOSSIER_STAT_LABELS
        }

        # Lazily populated once the draw surface and font registry are available.
        # The static surface contains the dossier paper and fixed document content;
        # the composed surface contains the final dossier for the current UI state.
        self._dossier_static_surface: pygame.Surface | None = None
        self._dossier_composite_surface: pygame.Surface | None = None
        self._dossier_static_bounds: pygame.Rect | None = None
        self._dossier_cache_bounds: pygame.Rect | None = None
        self._dossier_static_key: tuple | None = None
        self._dossier_render_key: tuple | None = None
        self._dossier_prop_sprites: dict[str, pygame.Surface] = {}

        # Exit menu button.
        def exit_equipment_menu():
            self.menu_manager.current_menu = self.menu_manager.port_menu

        button_sprite = DataFiles.sprites["user_interface"]["prev"]
        button_size = 48
        button_rect = get_rect(
            width=button_size, height=button_size,
            right=Box.RIGHT_OF_SCREEN, top=Box.TOP_OF_SCREEN
        )
        self.exit_equipment_menu_button = RectangularButton(
            button_rect,
            exit_equipment_menu,
            background_styling={
                "background_color": Color.BLACK,
                "background_img": button_sprite,
                "opacity": 160
            },
            hover_styling={"opacity": 200}
        )

        # Shipgirl wander logic.
        self.shipgirl_x = None
        self.target_shipgirl_x = 0
        self.shipgirl_pause_time = 0

        # Blueprint slot glow logic.
        self.blueprint_effect_time = 0
        self.selection_activation_time = 0

    def _get_stat_delta(self, shipgirl: Shipgirl, stat: str) -> float:
        """Compute the change in the stat.
        
        The comparison is between the hovered equipment and the currently equipped equipment.
        """
        if self.hovered_equipment is None:
            return 0
        currently_equipped = shipgirl.battle_component.equipment[self.selected_slot]
        return (
            DataFiles.equipment_data.get(self.hovered_equipment, {}).get(stat, 0)
            - DataFiles.equipment_data.get(currently_equipped, {}).get(stat, 0)
        )

    def _get_equippable_options(self) -> list[str]:
        """Get the list of clickable options in the equipment depot.
        
        Filter the equipment depot by the equippable items based on the selected shipgirl
        and selected slot. Add the unequip slot if the shipgirl currently has something
        equipped in this slot.
        """
        if self.selected_slot == Equipment.WEAPON:
            options = [
                weapon_name for weapon_name, weapon_info in DataFiles.equipment_data.items()
                if DataFiles.save_file["equipment"].get(weapon_name, 0) > 0
                and weapon_info["type"] == Equipment.WEAPON_KEY
                and weapon_info["equippable_by"] == self.selected_shipgirl.battle_component.hull_type
            ]
        else:
            options = [
                aux_name for aux_name, aux_info in DataFiles.equipment_data.items()
                if DataFiles.save_file["equipment"].get(aux_name, 0) > 0
                and aux_info["type"] == Equipment.AUX_KEY
            ]
        current_equipment = self.selected_shipgirl.battle_component.equipment[self.selected_slot]
        if current_equipment is not None:
            options = options + [self.UNEQUIP_ITEM]
        return options

    def _get_equipment_page_count(self, equippable: list[str] = None) -> int:
        """Get the number of pages in the equipment depot."""
        if equippable is None:
            equippable = self._get_equippable_options()

        return max(1, math.ceil(len(equippable) / len(self.equippable_rects)))

    def _get_equipment_page(self, equippable: list[str] = None) -> int:
        """Get the current page in the equipment depot."""
        page_count = self._get_equipment_page_count(equippable)
        page = min(self.equipment_pages.get(self.selected_slot, 0), page_count - 1)
        page = max(0, page)
        self.equipment_pages[self.selected_slot] = page
        return page

    def _get_visible_equippable_options(self, equippable: list[str] = None) -> list[str]:
        """Clamp all valid equippable options to those viewable on the current depot page."""
        if equippable is None:
            equippable = self._get_equippable_options()

        page = self._get_equipment_page(equippable)
        page_size = len(self.equippable_rects)
        start = page * page_size
        return equippable[start:start + page_size]

    def _refresh_equipment_page_buttons(self):
        """Refresh the equipment pagination controls."""
        equippable = self._get_equippable_options()
        page_count = self._get_equipment_page_count(equippable)
        page = self._get_equipment_page(equippable)
        self.equipment_page_prev_button.rect.center = self.equipment_depot.bottomleft
        self.equipment_page_next_button.rect.center = self.equipment_depot.bottomright
        self.equipment_page_prev_button.active = page_count > 1 and page > 0
        self.equipment_page_next_button.active = page_count > 1 and page < page_count - 1

    def _change_equipment_page(self, delta: int):
        """Increment or decrement the equipment page index."""
        equippable = self._get_equippable_options()
        page_count = self._get_equipment_page_count(equippable)
        page = self._get_equipment_page(equippable)
        self.equipment_pages[self.selected_slot] = min(page_count - 1, max(0, page + delta))
        self._refresh_equipment_page_buttons()

    def update(self, dt: float, events: list[pygame.Event]):
        """Update the equipment menu."""
        # Animate the blueprint selected slow glow effect and activation.
        self.blueprint_effect_time += dt
        self.selection_activation_time = min(
            self.SELECTION_ACTIVATION_DURATION,
            self.selection_activation_time + dt,
        )

        # Animate the shipgirl wandering in the workshop.
        shipgirl_to_target_x_tolerance = 10
        if self.shipgirl_x is None:
            self.shipgirl_x = screen_x(0.5)
            self.target_shipgirl_x = self.shipgirl_x
            self.selected_shipgirl.rect.bottom = self.equipment_depot.bottom + Box.HEIGHT / 2.5
        if self.shipgirl_pause_time > 0:
            self.shipgirl_pause_time -= dt
            self.selected_shipgirl.sprite.set_animation(Live2D.IDLE_ANIMATION)
        elif abs(self.target_shipgirl_x - self.selected_shipgirl.rect.centerx) < shipgirl_to_target_x_tolerance:
            self.shipgirl_pause_time = random.uniform(1, 3)
            self.target_shipgirl_x = random.uniform(Box.LEFT_OF_SCREEN, Box.RIGHT_OF_SCREEN)
        else:
            relx = self.target_shipgirl_x - self.selected_shipgirl.rect.centerx
            direction = relx / abs(relx)
            shipgirl_wander_speed = 50
            self.shipgirl_x += direction * shipgirl_wander_speed * dt
            self.selected_shipgirl.facing_left = direction < 0
            self.selected_shipgirl.sprite.set_animation(Live2D.WALK_ANIMATION)
        self.selected_shipgirl.rect.centerx = self.shipgirl_x
        self.selected_shipgirl.animate(dt)

        for event in events:
            if event.type == pygame.MOUSEBUTTONUP:
                self._refresh_equipment_page_buttons()
                if (
                    self.equipment_page_prev_button.click(event.pos)
                    or self.equipment_page_next_button.click(event.pos)
                ):
                    DataFiles.sfx["click"].play()

                equip_slots = [Equipment.WEAPON, Equipment.AUX1, Equipment.AUX2]
                for equip_slot, rect in zip(equip_slots, self.equipped_rects):
                    if rect.collidepoint(event.pos):
                        if equip_slot != self.selected_slot:
                            # Play the activation animation when switching to a new slot.
                            self.selection_activation_time = 0
                        self.selected_slot = equip_slot
                        self._refresh_equipment_page_buttons()
                        DataFiles.sfx["click"].play()

                for new_equipment, rect in zip(self._get_visible_equippable_options(), self.equippable_rects):
                    if rect.collidepoint(event.pos):
                        current_equipment = self.selected_shipgirl.battle_component.equipment[self.selected_slot]
                        if current_equipment is not None:
                            DataFiles.save_file["equipment"][current_equipment] = (
                                DataFiles.save_file["equipment"].get(current_equipment, 0) + 1
                            )
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
                self._refresh_equipment_page_buttons()
                self.equipment_page_prev_button.hover(event.pos)
                self.equipment_page_next_button.hover(event.pos)

                # Set the hovered equipment.
                for equipment, rect in zip(self._get_visible_equippable_options(), self.equippable_rects):
                    if rect.collidepoint(event.pos):
                        self.hovered_equipment = equipment
                        break
                else:
                    self.hovered_equipment = None

    def _draw_blueprint_page(self, surface: pygame.Surface):
        """Helper to draw the blueprint page background."""
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

        # Blueprint grid.
        grid_step = 2 * Box.PADDING
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
        # Blueprint inset border.
        inset_rect = self.blueprint_page.inflate(-2 * Box.PADDING, -2 * Box.PADDING)
        pygame.draw.rect(
            surface,
            Color.BLUEPRINT_GRID_MAJOR,
            inset_rect,
            width=Box.OUTLINE_WIDTH,
        )

    def _draw_blueprint_identity(self, surface: pygame.Surface, font_registry: dict[str, Font]):
        """Helper to draw the blueprint header and icons."""
        shipgirl_data = DataFiles.shipgirl_data[self.selected_shipgirl.name]
        faction = shipgirl_data["faction"]
        ship_class = shipgirl_data["class"].replace("_", " ")
        hull_type = shipgirl_data["hull_type"]
        hull_name = Equipment.HULL_TYPE_MAPPING[hull_type]

        # Faction icon.
        faction_icon = DataFiles.sprites["user_interface"][f"{faction}_big"]
        faction_icon_rect = faction_icon.get_rect(
            left=self.blueprint_page.left + Box.PADDING,
            top=self.blueprint_page.top + Box.PADDING,
        )
        surface.blit(faction_icon, faction_icon_rect)
        # Draw corner brackets
        corners = [
            (faction_icon_rect.topleft, (1, 1)),
            (faction_icon_rect.topright, (-1, 1)),
            (faction_icon_rect.bottomleft, (1, -1)),
            (faction_icon_rect.bottomright, (-1, -1)),
        ]
        for corner, direction in corners:
            corner = pygame.Vector2(corner)
            dx, dy = direction
            pygame.draw.line(surface, Color.BLUEPRINT_GRID_MAJOR, corner, corner + pygame.Vector2(dx * Box.PADDING, 0))
            pygame.draw.line(surface, Color.BLUEPRINT_GRID_MAJOR, corner, corner + pygame.Vector2(0, dy * Box.PADDING))
        # Blueprint header: title, shipgirl name, hull classification.
        pixel_font = font_registry["pixel"]
        big_pixel_font = font_registry["big_pixel"]
        text_left = faction_icon_rect.right + 4
        heading_top = self.blueprint_page.top + 2 * Box.PADDING
        display_name = self.selected_shipgirl.name.replace("_", " ")
        name_scale = 1
        blueprint_name_padding = 3
        name_top = heading_top + pixel_font.font_height + blueprint_name_padding
        classification_top = name_top + name_scale * big_pixel_font.font_height + blueprint_name_padding
        pixel_font.render(
            surface,
            f"refit schematic // {faction}",
            (text_left, heading_top),
            Color.BLUEPRINT_INK_MUTED,
            scale=1,
        )
        big_pixel_font.render(
            surface,
            display_name,
            (text_left, name_top),
            Color.BLUEPRINT_SLOT_BORDER_GLOW,
            name_scale,
        )
        pixel_font.render(
            surface,
            f"{ship_class}-class // {hull_name} [{hull_type}]",
            (text_left, classification_top),
            Color.BLUEPRINT_INK_MUTED,
            scale=1,
        )

    def _draw_blueprint_slot_selection(self, surface: pygame.Surface, rect: pygame.Rect):
        """Draw the blueprint selected slot glow animation and glint particle effects."""
        # Selected slot glow animation.
        pulse = (math.sin(self.blueprint_effect_time * math.tau / 2.4) + 1) / 2
        activation_progress = min(1, self.selection_activation_time / self.SELECTION_ACTIVATION_DURATION)
        activation_ease = 1 - (1 - activation_progress) ** 3

        beacon_base = DataFiles.sprites["user_interface"]["blueprint_slot_glow"].copy()
        beacon_base.set_alpha(int(128 + 127 * pulse))
        beacon = pygame.Surface(beacon_base.get_size())
        beacon.blit(beacon_base)
        beacon_rect = beacon.get_rect()
        beacon_rect.bottomleft = rect.topleft

        visible_beacon_height = max(1, math.ceil(beacon_rect.height * activation_ease))
        beacon_source_rect = pygame.Rect(
            0,
            beacon_rect.height - visible_beacon_height,
            beacon_rect.width,
            visible_beacon_height,
        )
        visible_beacon_rect = beacon_source_rect.copy()
        visible_beacon_rect.bottomleft = rect.topleft
        surface.blit(
            beacon,
            visible_beacon_rect,
            beacon_source_rect,
            special_flags=pygame.BLEND_RGB_ADD,
        )

        # Slot border.
        activation_flash = (1 - activation_progress) ** 2
        border_color = tuple(
            round(channel + (white - channel) * 0.65 * activation_flash)
            for channel, white in zip(Color.BLUEPRINT_SLOT_BORDER_GLOW, Color.WHITE)
        )
        pygame.draw.rect(
            surface,
            border_color,
            rect,
            width=Box.OUTLINE_WIDTH,
        )

        seam_strength = min(1, 0.25 + 0.25 * pulse + 0.65 * activation_flash)
        seam_color = tuple(
            round(glow + (bright - glow)*seam_strength)
            for glow, bright in zip(
                Color.BLUEPRINT_PAGE_GLOW,
                Color.BLUEPRINT_SLOT_BORDER_GLOW,
            )
        )
        pygame.draw.line(
            surface,
            seam_color,
            (rect.left + 4, rect.top),
            (rect.right - 5, rect.top),
            width=Box.OUTLINE_WIDTH,
        )

        # Glint particle effects.
        glint_cycle = 0.9
        glint_lifetime = 0.7
        glint_max_length = 5
        glint_drift = 12
        for glint_index in range(4):
            glint_time = self.blueprint_effect_time + glint_index * glint_cycle / 4
            glint_age = glint_time % glint_cycle
            if glint_age >= glint_lifetime:
                continue

            cycle_index = math.floor(glint_time / glint_cycle)
            glint_progress = glint_age / glint_lifetime
            glint_strength = (1 - glint_progress) ** 1.5
            spawn_center = pygame.Vector2(
                beacon_rect.left + 6 + (cycle_index * 29 + glint_index * 17) % (beacon_rect.width - 12),
                beacon_rect.top+ beacon_rect.height / 2 + 4
                + (cycle_index * 19 + glint_index * 31) % (1.5 * beacon_rect.height - 8),
            )
            center = spawn_center - pygame.Vector2(0, glint_drift * glint_progress)
            if center.y < visible_beacon_rect.top:
                continue
            glint_length = 1 + round((glint_max_length - 1) * glint_strength)
            glint_color = tuple(
                round(channel * glint_strength * activation_ease)
                for channel in Color.BLUEPRINT_SLOT_BORDER_GLOW
            )
            glint_surface = pygame.Surface(
                (2 * glint_max_length + 1, 2 * glint_max_length + 1)
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

    def _draw_blueprint_slots(self, surface: pygame.Surface, font_registry: dict[str, Font]):
        """Draw the cacheable blueprint slot content and inactive borders."""
        equipment_slots = self.selected_shipgirl.battle_component.equipment
        for slot, (equipment, rect) in enumerate(zip(equipment_slots, self.equipped_rects)):
            slot_color = (
                Color.BLUEPRINT_PAGE_GLOW
                if self.selected_slot == slot
                else Color.BLUEPRINT_TITLE_BLOCK
            )
            pygame.draw.rect(surface, slot_color, rect)
            if equipment is None:
                # No equipment, render a default empty text.
                slot_label_y_up_shift = 2
                big_pixel_font = font_registry["big_pixel"]
                big_pixel_font.render(
                    surface,
                    self.SLOT_LABELS[slot],
                    (rect.centerx, rect.centery - big_pixel_font.font_height / 2 - slot_label_y_up_shift),
                    Color.BLUEPRINT_SLOT_BORDER_GLOW,
                    scale=1,
                    style="center",
                )
                pixel_font = font_registry["pixel"]
                pixel_font.render(
                    surface,
                    "vacant",
                    (rect.centerx, rect.centery + pixel_font.font_height),
                    Color.BLUEPRINT_INK_MUTED,
                    scale=1,
                    style="center",
                )
            else:
                equipment_sprite = DataFiles.get_entity_sprite(equipment)
                surface.blit(equipment_sprite, equipment_sprite.get_rect(center=rect.center))

            # Slot border.
            if self.selected_slot != slot:
                draw_dashed_rect(
                    surface,
                    Color.BLUEPRINT_INK_MUTED,
                    rect,
                    dash_length=8,
                    gap_length=4,
                    width=Box.OUTLINE_WIDTH,
                )

    def _draw_blueprint_static_backdrop(self, surface: pygame.Surface):
        """Draw blueprint content which is invariant across menu frames."""
        self._draw_blueprint_page(surface)

        # Draw the warship side and top schematic sprites.
        side_schematic = DataFiles.sprites["equipment_menu"]["side_schematic"]
        side_schematic_rect = side_schematic.get_rect()
        side_schematic_rect.left = self.blueprint_page.left
        side_schematic_rect.centery = self.equipped_rects[Equipment.WEAPON].centery
        surface.blit(side_schematic, side_schematic_rect)

        top_schematic = DataFiles.sprites["equipment_menu"]["top_schematic"]
        top_schematic_rect = top_schematic.get_rect()
        top_schematic_rect.left = self.blueprint_page.left
        top_schematic_rect.centery = self.equipped_rects[Equipment.AUX1].centery
        surface.blit(top_schematic, top_schematic_rect)

    def _draw_blueprint_foreground(self, surface: pygame.Surface):
        """Draw the fixed props which appear above the animated selection."""
        page_bottom = self.blueprint_page.bottom + Box.HEIGHT / 2

        pencil_sprite = DataFiles.sprites["props"]["pencil"]
        pencil_rect = pencil_sprite.get_rect()
        pencil_rect.right = self.blueprint_page.right + Box.WIDTH / 4
        pencil_rect.bottom = page_bottom

        ruler_sprite = DataFiles.sprites["props"]["ruler"]
        ruler_rect = ruler_sprite.get_rect()
        ruler_rect.midbottom = pencil_rect.bottomleft
        surface.blit(ruler_sprite, ruler_rect)
        surface.blit(pencil_sprite, pencil_rect)

        compass_sprite = DataFiles.sprites["props"]["compass"]
        compass_rect = compass_sprite.get_rect()
        compass_rect.left = self.blueprint_page.left - Box.WIDTH / 4
        compass_rect.bottom = page_bottom
        surface.blit(compass_sprite, compass_rect)

    def _get_blueprint_static_key(self, surface: pygame.Surface) -> tuple:
        """Return inputs which determine the blueprint's fixed render layers."""
        return (surface.get_size(),)

    def _get_blueprint_render_key(self, font_registry: dict[str, Font]) -> tuple:
        """Return the inexpensive inputs which determine cached blueprint state."""
        return (
            self.selected_shipgirl.name,
            tuple(self.selected_shipgirl.battle_component.equipment),
            self.selected_slot,
            id(font_registry["pixel"]),
            id(font_registry["big_pixel"]),
        )

    def _ensure_blueprint_static_cache(self, surface: pygame.Surface):
        """Build or refresh the blueprint's frame-invariant layers."""
        static_key = self._get_blueprint_static_key(surface)
        if static_key == self._blueprint_static_key:
            return

        self._blueprint_static_surface = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        self._blueprint_composite_surface = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        self._blueprint_foreground_surface = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        self._draw_blueprint_static_backdrop(self._blueprint_static_surface)
        self._draw_blueprint_foreground(self._blueprint_foreground_surface)

        self._blueprint_static_bounds = self._blueprint_static_surface.get_bounding_rect(min_alpha=1)
        self._blueprint_foreground_bounds = self._blueprint_foreground_surface.get_bounding_rect(min_alpha=1)
        self._blueprint_cache_bounds = None
        self._blueprint_static_key = static_key
        self._blueprint_render_key = None

    def _rebuild_blueprint_cache(self, font_registry: dict[str, Font], render_key: tuple):
        """Compose shipgirl and equipment state over the static blueprint."""
        if self._blueprint_cache_bounds is not None:
            self._blueprint_composite_surface.fill((0, 0, 0, 0), self._blueprint_cache_bounds)
        self._blueprint_composite_surface.blit(
            self._blueprint_static_surface,
            self._blueprint_static_bounds,
            self._blueprint_static_bounds,
        )
        self._draw_blueprint_identity(self._blueprint_composite_surface, font_registry)
        self._draw_blueprint_slots(self._blueprint_composite_surface, font_registry)

        self._blueprint_cache_bounds = self._blueprint_composite_surface.get_bounding_rect(min_alpha=1)
        self._blueprint_render_key = render_key

    def _draw_blueprint(self, surface: pygame.Surface, font_registry: dict[str, Font]):
        """Draw the cached blueprint with its live selection animation."""
        self._ensure_blueprint_static_cache(surface)
        render_key = self._get_blueprint_render_key(font_registry)
        if render_key != self._blueprint_render_key:
            self._rebuild_blueprint_cache(font_registry, render_key)

        surface.blit(
            self._blueprint_composite_surface,
            self._blueprint_cache_bounds,
            self._blueprint_cache_bounds,
        )
        self._draw_blueprint_slot_selection(
            surface,
            self.equipped_rects[self.selected_slot],
        )
        surface.blit(
            self._blueprint_foreground_surface,
            self._blueprint_foreground_bounds,
            self._blueprint_foreground_bounds,
        )

    def _draw_dossier_header_static(self, surface: pygame.Surface, font_registry: dict[str, Font]):
        """Draw the parts of the dossier header shared by every shipgirl."""
        pixel_font = font_registry["pixel"]
        pixel_font.render(
            surface,
            "azur lane naval command",
            self.dossier_header.topleft,
            Color.DOSSIER_RULE,
            scale=1,
        )
        form_text = "form er-01"
        form_left = self.dossier_header.right - pixel_font.get_width(form_text, scale=1, box_width=0)
        pixel_font.render(
            surface,
            form_text,
            (form_left, self.dossier_header.top),
            Color.DOSSIER_INK,
            scale=1,
        )

    def _draw_dossier_header(self, surface: pygame.Surface, font_registry: dict[str, Font]):
        """Draw the shipgirl-specific dossier header content."""
        pixel_font = font_registry["pixel"]
        title_font = font_registry["big_pixel"]
        shipgirl_data = DataFiles.shipgirl_data[self.selected_shipgirl.name]
        faction = shipgirl_data["faction"]
        hull_type = shipgirl_data["hull_type"]
        display_name = self.selected_shipgirl.name.replace("_", " ")
        file_name = self.selected_shipgirl.name.replace("_", "-")

        text_y_padding = 3
        name_scale = 2
        title_y = self.dossier_header.top + 11
        title_font.render(
            surface,
            display_name,
            (self.dossier_header.left, title_y),
            Color.DOSSIER_INK,
            name_scale,
        )
        subtitle1_y = title_y + name_scale * title_font.font_height + 2 * text_y_padding
        pixel_font.render(
            surface,
            f"file: {faction}-{file_name}",
            (self.dossier_header.left, subtitle1_y),
            Color.DOSSIER_RULE,
            scale=1,
        )
        subtitle2_y = subtitle1_y + pixel_font.font_height + text_y_padding
        pixel_font.render(
            surface,
            f"class: {shipgirl_data['class'].replace('_', ' ')}",
            (self.dossier_header.left, subtitle2_y),
            Color.DOSSIER_RULE,
            scale=1,
        )
        subtitle3_y = subtitle2_y + pixel_font.font_height + text_y_padding
        pixel_font.render(
            surface,
            f"hull: {Equipment.HULL_TYPE_MAPPING[hull_type]} [{hull_type}]",
            (self.dossier_header.left, subtitle3_y),
            Color.DOSSIER_RULE,
            1,
        )

    @staticmethod
    def _draw_dossier_section_header(
        surface: pygame.Surface, font_registry: dict[str, Font], text: str, rect: pygame.Rect
    ):
        """Draw the dossier page section headers."""
        horizontal_rule_up_shift = 4
        pygame.draw.line(
            surface,
            Color.DOSSIER_RULE,
            (rect.left, rect.top - horizontal_rule_up_shift),
            (rect.right, rect.top - horizontal_rule_up_shift),
        )
        font_registry["pixel"].render(
            surface,
            text,
            rect.topleft,
            Color.DOSSIER_RULE,
            scale=1,
        )
        horizontal_rule_down_shift = 10
        pygame.draw.line(
            surface,
            Color.DOSSIER_RULE,
            (rect.left, rect.top + horizontal_rule_down_shift),
            (rect.right, rect.top + horizontal_rule_down_shift),
        )

    def _draw_dossier_progress_static(self, surface: pygame.Surface, font_registry: dict[str, Font]):
        """Draw the fixed labels and geometry in the dossier progress section."""
        self._draw_dossier_section_header(
            surface,
            font_registry,
            "01 service progression",
            self.dossier_progress,
        )

        medal_icon = DataFiles.sprites["user_interface"]["medal"]
        medal_rect = medal_icon.get_rect(
            left=self.dossier_progress.left,
            top=self.dossier_progress.top + 14,
        )
        surface.blit(medal_icon, medal_rect)

        font_registry["pixel"].render(
            surface,
            "service level",
            (medal_rect.right + Box.PADDING, medal_rect.top),
            Color.DOSSIER_RULE,
            scale=1,
        )
        pygame.draw.rect(surface, Color.DOSSIER_RULE, self.exp_bar_bg)

    def _draw_dossier_progress(self, surface: pygame.Surface, font_registry: dict[str, Font]):
        """Draw the state-dependent level and EXP progress."""
        exp = self.selected_shipgirl.battle_component.exp
        level_index = Stats.level(exp)
        level = level_index + 1
        level_exp = exp - Stats.exp_to_level(level_index)
        required_exp = Stats.exp_amount_at_level(level_index)
        level_progress = level_exp / required_exp

        medal_icon = DataFiles.sprites["user_interface"]["medal"]
        medal_rect = medal_icon.get_rect(
            left=self.dossier_progress.left,
            top=self.dossier_progress.top + 14,
        )

        pixel_font = font_registry["pixel"]
        font_registry["big_pixel"].render(
            surface,
            f"{level:02d}",
            (medal_rect.right + Box.PADDING, medal_rect.top + pixel_font.font_height + 3),
            Color.DOSSIER_INK,
            scale=2,
        )
        pixel_font.render(
            surface,
            f"{level_exp}/{required_exp}",
            (self.exp_bar_bg.centerx, self.exp_bar_bg.top - pixel_font.font_height),
            Color.DOSSIER_RULE,
            scale=1,
            style="center"
        )

        exp_bar = get_rect(
            width=round(level_progress * self.exp_bar_bg.width),
            height=self.exp_bar_bg.height,
            left=self.exp_bar_bg.left,
            top=self.exp_bar_bg.top,
        )
        pygame.draw.rect(surface, Color.DOSSIER_INK, exp_bar)

    def _draw_dossier_progress_foreground(self, surface: pygame.Surface):
        """Draw EXP bar marks which must appear above the progress fill."""
        for tick in (0.25, 0.5, 0.75):
            tick_x = self.exp_bar_bg.left + round(self.exp_bar_bg.width * tick)
            pygame.draw.line(
                surface,
                Color.DOSSIER_PAGE,
                (tick_x, self.exp_bar_bg.top + 1),
                (tick_x, self.exp_bar_bg.bottom - 2),
            )
        pygame.draw.rect(surface, Color.DOSSIER_INK, self.exp_bar_bg, width=1)

    def _draw_dossier_capabilities_static(self, surface: pygame.Surface, font_registry: dict[str, Font]):
        """Draw fixed labels and icons in the dossier capabilities section."""
        self._draw_dossier_section_header(
            surface,
            font_registry,
            "02 combat capability",
            self.dossier_capabilities,
        )

        pixel_font = font_registry["pixel"]
        for stat, row_rect in self.stat_row_rects.items():
            icon_rect = self.stat_rects[stat]
            stat_icon = DataFiles.recolor_sprite("user_interface", stat, Color.DOSSIER_INK)
            surface.blit(stat_icon, icon_rect)
            pixel_font.render(
                surface,
                self.DOSSIER_STAT_LABELS[stat],
                (icon_rect.right + Box.PADDING, row_rect.top + 6),
                Color.DOSSIER_RULE,
                scale=1,
            )

        horizontal_rule_up_shift = 1
        pygame.draw.line(
            surface,
            Color.DOSSIER_RULE,
            (row_rect.left, row_rect.bottom - horizontal_rule_up_shift),
            (row_rect.right, row_rect.bottom - horizontal_rule_up_shift),
        )

    def _draw_dossier_capabilities(self, surface: pygame.Surface, font_registry: dict[str, Font]):
        """Draw the state-dependent stat values and equipment deltas."""
        for stat, row_rect in self.stat_row_rects.items():
            icon_rect = self.stat_rects[stat]
            pixel_font = font_registry["pixel"]
            big_pixel_font = font_registry["big_pixel"]
            value = str(self.selected_shipgirl.battle_component.stat(stat))
            value_left = icon_rect.right + Box.PADDING
            stat_label_y = row_rect.top + 6
            text_y_padding = 3
            value_font_scale = 1
            value_text_y = stat_label_y + pixel_font.font_height + text_y_padding
            big_pixel_font.render(
                surface,
                value,
                (value_left, stat_label_y + pixel_font.font_height + text_y_padding),
                Color.DOSSIER_INK,
                value_font_scale,
            )
            # Draw the stat deltas.
            stat_delta = self._get_stat_delta(self.selected_shipgirl, stat)
            if stat_delta != 0:
                color = (34, 178, 34) if stat_delta > 0 else (178, 34, 34)
                center = pygame.Vector2(icon_rect.left - Box.PADDING, icon_rect.centery)
                angles = (30, 150, 270) if stat_delta > 0 else (90, 210, 330)
                pygame.draw.polygon(
                    surface,
                    color,
                    [center + get_vec(length=Box.PADDING, angle=math.radians(angle)) for angle in angles],
                )

                value_width = font_registry["big_pixel"].get_width(value, value_font_scale, box_width=0)
                delta_text = f"+{stat_delta}" if stat_delta > 0 else str(stat_delta)
                delta_text_y = value_text_y + value_font_scale * big_pixel_font.font_height / 2
                big_pixel_font.render(
                    surface,
                    delta_text,
                    (value_left + value_width + value_font_scale * big_pixel_font.font_width, delta_text_y),
                    color,
                    scale=1,
                    style="centerleft",
                )

    def _draw_dossier_static_backdrop(self, surface: pygame.Surface, font_registry: dict[str, Font]):
        """Draw dossier content which is invariant across menu frames."""
        pygame.draw.rect(surface, Color.DOSSIER, self.dossier_bg)
        pygame.draw.polygon(surface, Color.DOSSIER, self.dossier_tab)

        misaligned_pages = [
            (-4, pygame.Vector2(-6, 7), (224, 218, 201)),
            (5, pygame.Vector2(8, -5), (235, 229, 212)),
            (-3, pygame.Vector2(2, 6), (244, 239, 224)),
        ]
        for rotated_angle, offset, color in misaligned_pages:
            pygame.draw.polygon(
                surface,
                color,
                Box.get_rotated_rect_polygon(self.dossier_page, rotated_angle, offset),
            )
        pygame.draw.rect(surface, Color.DOSSIER_PAGE, self.dossier_page)

        self._draw_dossier_header_static(surface, font_registry)
        self._draw_dossier_progress_static(surface, font_registry)
        self._draw_dossier_capabilities_static(surface, font_registry)

    def _prepare_dossier_props(self):
        """Prepare transformed and translucent dossier props once per static cache."""
        classified_sprite = DataFiles.sprites["props"]["classified"].copy()
        classified_sprite.set_alpha(80)
        coffee_ring_sprite = DataFiles.sprites["props"]["coffee_ring"].copy()
        coffee_ring_sprite.set_alpha(144)
        paperclip_sprite = pygame.transform.rotate(
            DataFiles.sprites["props"]["paperclip"],
            angle=-90,
        )
        self._dossier_prop_sprites = {
            "classified": classified_sprite,
            "coffee_ring": coffee_ring_sprite,
            "paperclip": paperclip_sprite,
        }

    def _get_dossier_prop_rects(self) -> dict[str, pygame.Rect]:
        """Return the fixed destination rectangles for the prepared props."""
        classified_rect = self._dossier_prop_sprites["classified"].get_rect(
            topright=self.dossier_bg.topright,
        )
        coffee_ring_rect = self._dossier_prop_sprites["coffee_ring"].get_rect(
            bottomleft=self.dossier_bg.bottomleft,
        )
        paperclip_rect = self._dossier_prop_sprites["paperclip"].get_rect(
            right=self.dossier_bg.right,
            top=self.dossier_bg.top - 4,
        )
        return {
            "classified": classified_rect,
            "coffee_ring": coffee_ring_rect,
            "paperclip": paperclip_rect,
        }

    def _draw_dossier_foreground(self, surface: pygame.Surface):
        """Draw fixed details which must remain above state-dependent content."""
        self._draw_dossier_progress_foreground(surface)
        for prop_name, prop_rect in self._get_dossier_prop_rects().items():
            surface.blit(self._dossier_prop_sprites[prop_name], prop_rect)

    def _get_dossier_static_key(
        self,
        surface: pygame.Surface,
        font_registry: dict[str, Font],
    ) -> tuple:
        """Return inputs which determine the static cache's rendering environment."""
        return (
            surface.get_size(),
            id(font_registry["pixel"]),
            id(font_registry["big_pixel"]),
        )

    def _get_dossier_render_key(self) -> tuple:
        """Return the inexpensive inputs which determine visible dossier state."""
        battle_component = self.selected_shipgirl.battle_component
        return (
            self.selected_shipgirl.name,
            battle_component.exp,
            tuple(battle_component.equipment),
            self.selected_slot,
            self.hovered_equipment,
        )

    def _ensure_dossier_static_cache(
        self,
        surface: pygame.Surface,
        font_registry: dict[str, Font],
    ):
        """Build or refresh static dossier resources for the render environment."""
        static_key = self._get_dossier_static_key(surface, font_registry)
        if static_key == self._dossier_static_key:
            return

        self._dossier_static_surface = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        self._dossier_composite_surface = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        self._prepare_dossier_props()
        self._draw_dossier_static_backdrop(self._dossier_static_surface, font_registry)

        static_bounds = self._dossier_static_surface.get_bounding_rect(min_alpha=1)
        for prop_rect in self._get_dossier_prop_rects().values():
            static_bounds.union_ip(prop_rect)
        self._dossier_static_bounds = static_bounds.clip(self._dossier_static_surface.get_rect())
        self._dossier_cache_bounds = None
        self._dossier_static_key = static_key
        self._dossier_render_key = None

    def _rebuild_dossier_cache(self, font_registry: dict[str, Font], render_key: tuple):
        """Compose the dossier for the current state onto the persistent cache."""
        if self._dossier_cache_bounds is not None:
            self._dossier_composite_surface.fill((0, 0, 0, 0), self._dossier_cache_bounds)
        self._dossier_composite_surface.blit(
            self._dossier_static_surface,
            self._dossier_static_bounds,
            self._dossier_static_bounds,
        )
        self._draw_dossier_header(self._dossier_composite_surface, font_registry)
        self._draw_dossier_progress(self._dossier_composite_surface, font_registry)
        self._draw_dossier_capabilities(self._dossier_composite_surface, font_registry)
        self._draw_dossier_foreground(self._dossier_composite_surface)

        self._dossier_cache_bounds = self._dossier_composite_surface.get_bounding_rect(min_alpha=1)
        self._dossier_render_key = render_key

    def _draw_dossier(self, surface: pygame.Surface, font_registry: dict[str, Font]):
        """Draw the cached dossier, rebuilding it only when visible state changes."""
        self._ensure_dossier_static_cache(surface, font_registry)
        render_key = self._get_dossier_render_key()
        if render_key != self._dossier_render_key:
            self._rebuild_dossier_cache(font_registry, render_key)

        surface.blit(
            self._dossier_composite_surface,
            self._dossier_cache_bounds,
            self._dossier_cache_bounds,
        )

    def draw(self, surface: pygame.Surface, font_registry: dict[str, Font]):
        floor_color = (71, 71, 71)
        wall_color = (105, 105, 105)
        surface.fill(wall_color)

        workshop_floor = get_rect(
            width=screen_x(1), height=Box.HEIGHT,
            left=0, top=self.equipment_depot.bottom
        )
        workshop_wall = get_rect(
            width=screen_x(1), height=2 * Box.HEIGHT,
            left=0, bottom=workshop_floor.top
        )
        workshop_ceiling = get_rect(
            width=screen_x(1), height=Box.HEIGHT / 2,
            left=0, bottom=workshop_wall.top
        )

        # Draw the tabletop pattern.
        tabletop_rect = get_rect(
            width=screen_x(1) - 2 * Box.WIDTH,
            height=workshop_ceiling.top,
            left=Box.WIDTH, top=0
        )
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

        self._draw_dossier(surface, font_registry)
        self._draw_blueprint(surface, font_registry)

        # Draw the bottom half of the screen, which is a workshop.
        pygame.draw.rect(surface, floor_color, workshop_floor)
        pygame.draw.rect(surface, wall_color, workshop_wall)
        pygame.draw.rect(surface, floor_color, workshop_ceiling)

        # Workshop props.
        table_sprite = DataFiles.sprites["equipment_menu"]["table"]
        table_rect = table_sprite.get_rect()
        table_rect.bottom = workshop_floor.top + Box.PADDING
        table_rect.right = self.equipment_depot.left - 1.5 * Box.WIDTH
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
        oil_drum_rect.right = table_rect.left - Box.WIDTH / 2
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
        lightbulb_light_rect.bottom = lightbulb_rect.bottom + Box.HEIGHT / 4
        surface.blit(lightbulb_light_sprite, lightbulb_light_rect, special_flags=pygame.BLEND_RGB_ADD)

        # Equipment depot.
        equippable = self._get_visible_equippable_options()
        self._refresh_equipment_page_buttons()
        pygame.draw.rect(surface, Color.CARGO_BOX_BACK, self.equipment_depot)
        for equipment, rect in zip(equippable, self.equippable_rects):
            pygame.draw.rect(surface, Color.CARGO_BOX, rect)
            if equipment == self.UNEQUIP_ITEM:
                surface.blit(DataFiles.sprites["user_interface"]["unequip_item"], rect)
            else:
                surface.blit(DataFiles.get_entity_sprite(equipment), rect)
        # Equipment depot props.
        depot_decoration_top = self.equipment_depot.top - Box.WIDTH / 8
        top_rope_sprite = DataFiles.sprites["props"]["top_rope"]
        top_rope_rect = top_rope_sprite.get_rect()
        top_rope_rect.left = self.equipment_depot.centerx + Box.WIDTH / 2
        top_rope_rect.top = depot_decoration_top
        surface.blit(top_rope_sprite, top_rope_rect)

        big_top_rope_sprite = DataFiles.sprites["props"]["big_top_rope"]
        big_top_rope_rect = big_top_rope_sprite.get_rect()
        big_top_rope_rect.right = self.equipment_depot.centerx - Box.WIDTH / 2
        big_top_rope_rect.top = depot_decoration_top
        surface.blit(big_top_rope_sprite, big_top_rope_rect)

        rope_hook_sprite = DataFiles.sprites["props"]["short_rope_hook"]
        rope_hook_rect = rope_hook_sprite.get_rect()
        rope_hook_rect.left = self.equipment_depot.left + Box.WIDTH / 2
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
            (sign_rect.centerx, sign_rect.centery - 1.25 * font.font_height),
            Color.BLACK,
            scale=1,
            style="center"
        )
        font.render(
            surface,
            str(self._get_equipment_page() + 1),
            (sign_rect.centerx, sign_rect.centery + font.font_height / 2),
            Color.BLACK,
            scale=2,
            style="center"
        )

        corner_rope_sprite = DataFiles.sprites["props"]["corner_rope"]
        corner_rope_rect = corner_rope_sprite.get_rect()
        corner_rope_rect.right = self.equipment_depot.right + Box.WIDTH / 8
        corner_rope_rect.top = depot_decoration_top
        surface.blit(corner_rope_sprite, corner_rope_rect)

        big_corner_rope_sprite = DataFiles.sprites["props"]["big_corner_rope"]
        big_corner_rope_rect = big_corner_rope_sprite.get_rect()
        big_corner_rope_rect.right = self.equipment_depot.right + Box.WIDTH / 8
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

        self.selected_shipgirl.draw(surface, font_registry)

        lightbulb_light_sprite = DataFiles.sprites["props"]["lightbulb_light"]
        lightbulb_light_rect = lightbulb_light_sprite.get_rect()
        lightbulb_light_rect.centerx = lightbulb_rect.centerx
        lightbulb_light_rect.bottom = lightbulb_rect.bottom + Box.HEIGHT / 4
        surface.blit(lightbulb_light_sprite, lightbulb_light_rect, special_flags=pygame.BLEND_RGB_ADD)

        cargo_box_sprite = DataFiles.sprites["props"]["cargo_box"]
        cargo_box_rect = cargo_box_sprite.get_rect()
        left_crate_stack = pygame.Vector2(self.equipment_depot.bottomleft)
        right_crate_stack = pygame.Vector2(self.equipment_depot.bottomright)
        for cargo_box_pos in [
            left_crate_stack,
            left_crate_stack + pygame.Vector2(cargo_box_rect.width, 0),
            left_crate_stack + pygame.Vector2(0, -cargo_box_rect.height),
            left_crate_stack + pygame.Vector2(0, -2 * cargo_box_rect.height),
            left_crate_stack + pygame.Vector2(-cargo_box_rect.width, 0),
            left_crate_stack + pygame.Vector2(-cargo_box_rect.width, -cargo_box_rect.height),
            
            right_crate_stack,
            right_crate_stack + pygame.Vector2(-cargo_box_rect.width, 0),
            right_crate_stack + pygame.Vector2(-2 * cargo_box_rect.width, 0),
            right_crate_stack + pygame.Vector2(0, -cargo_box_rect.height),
            right_crate_stack + pygame.Vector2(cargo_box_rect.width, 0),
            right_crate_stack + pygame.Vector2(cargo_box_rect.width, -cargo_box_rect.height),
            right_crate_stack + pygame.Vector2(cargo_box_rect.width / 2, -2 * cargo_box_rect.height),
        ]:
            cargo_box_rect.center = cargo_box_pos
            surface.blit(cargo_box_sprite, cargo_box_rect)

        # Draw the depot pagination controls.
        self._refresh_equipment_page_buttons()
        if self._get_equipment_page_count() > 1:
            self.equipment_page_prev_button.draw(surface, font_registry)
            self.equipment_page_next_button.draw(surface, font_registry)
        
        # section divider
        pygame.draw.line(surface, Color.BLACK, workshop_ceiling.topleft, workshop_ceiling.topright, width=4)

        self.exit_equipment_menu_button.draw(surface, font_registry)
