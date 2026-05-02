import pygame

from engine.util import get_rect
from engine.button import Button

from src.constants import DataFiles, Color, Box, Stats, screen_x, screen_y
from src.shipgirls import Shipgirl

class PortMenu:
    NO_OVERLAY = -1
    DEPOT = 0
    SHIPYARD = 1
    GEAR_LAB = 2
    INTEL_CENTER = 3

    def __init__(self, menu_manager):
        self.menu_manager = menu_manager

        factions = ["USS", "HMS", "IJN", "KMS"]
        def choose_faction_factory(faction):
            def choose_faction():
                DataFiles.save_file["unlocked_factions"].append(faction)
                for choose_faction_button in self.choose_faction_buttons:
                    choose_faction_button.active = False
            return choose_faction
        
        self.choose_faction_buttons = [
            Button(
                rect=get_rect(
                    width=Box.WIDTH, height=Box.HEIGHT,
                    centerx=screen_x(0.5) + (i-2)*Box.WIDTH+(i-1.5)*Box.PADDING,
                    centery=screen_y(0.5)
                ),
                color=Color.BLUE_GREY,
                sprite=DataFiles.sprites[faction],
                callback=choose_faction_factory(faction),
                active=False
            )
            for i, faction in enumerate(factions)
        ]

        self.current_overlay = self.NO_OVERLAY

        def open_overlay_factory(overlay_enum):
            def open_overlay():
                self.current_overlay = overlay_enum

                if overlay_enum == self.SHIPYARD and DataFiles.save_file["research_target"] is not None:
                    self.overlay_selected_entity = DataFiles.save_file["research_target"]
                    self.overlay_confirm_button.active = True
                    unique_item = DataFiles.shipgirl_data[self.overlay_selected_entity]["unique_item"]
                    if unique_item in DataFiles.save_file["inventory"]:
                        self.overlay_confirm_button.sprite = DataFiles.sprites["gear_lab"]
                        self.overlay_confirm_button.text = "construct"
                    else:
                        self.overlay_confirm_button.sprite = DataFiles.sprites["research"]
                        self.overlay_confirm_button.text = "research"

            return open_overlay

        self.open_depot_overlay_button = Button(
            rect=get_rect(
                width=Box.WIDTH, height=Box.HEIGHT,
                centerx=screen_x(1/6),
                bottom=Box.BOTTOM_OF_SCREEN
            ),
            color=Color.BLUE_GREY,
            sprite=DataFiles.sprites["depot"],
            callback=open_overlay_factory(self.DEPOT),
            # active=False
        )
        self.open_intel_center_overlay_button = Button(
            rect=get_rect(
                width=Box.WIDTH, height=Box.HEIGHT,
                centerx=screen_x(2/6),
                bottom=Box.BOTTOM_OF_SCREEN
            ),
            color=Color.BLUE_GREY,
            sprite=DataFiles.sprites["intel_center"],
            callback=open_overlay_factory(self.INTEL_CENTER),
            # active=False
        )
        self.open_shipyard_overlay_button = Button(
            rect=get_rect(
                width=Box.WIDTH, height=Box.HEIGHT,
                centerx=screen_x(3/6),
                bottom=Box.BOTTOM_OF_SCREEN
            ),
            color=Color.BLUE_GREY,
            sprite=DataFiles.sprites["shipyard"],
            callback=open_overlay_factory(self.SHIPYARD),
            # active=False
        )

        self.open_gear_lab_overlay_button = Button(
            rect=get_rect(
                width=Box.WIDTH, height=Box.HEIGHT,
                centerx=screen_x(4/6),
                bottom=Box.BOTTOM_OF_SCREEN
            ),
            color=Color.BLUE_GREY,
            sprite=DataFiles.sprites["gear_lab"],
            callback=open_overlay_factory(self.GEAR_LAB),
            # active=False
        )

        overlay_left_panel_width = 5*(Box.WIDTH + Box.PADDING) + Box.PADDING
        overlay_right_panel_width = 3*(Box.WIDTH + Box.PADDING) + Box.PADDING
        overlay_bg_width = (
            3*Box.PADDING # padding
            + overlay_left_panel_width
            + overlay_right_panel_width
        )
        overlay_left_panel_height = 4*(Box.WIDTH + Box.PADDING) + Box.PADDING
        overlay_bg_height = (
            2*Box.PADDING # padding
            + Box.HEIGHT # filters
            + overlay_left_panel_height
        )
        self.overlay_bg = get_rect(
            width=overlay_bg_width, height=overlay_bg_height,
            centerx=screen_x(0.5), centery=screen_y(0.5)
        )
        self.overlay_right_panel = get_rect(
            width=overlay_right_panel_width,
            height=self.overlay_bg.height-2*Box.PADDING,
            right=self.overlay_bg.right-Box.PADDING,
            top=self.overlay_bg.top+Box.PADDING
        )
        self.overlay_left_panel = get_rect(
            width=overlay_left_panel_width,
            height=overlay_left_panel_height,
            left=self.overlay_bg.left+Box.PADDING,
            bottom=self.overlay_bg.bottom-Box.PADDING
        )

        num_filter_rects = 5
        filter_rect_padding = (self.overlay_left_panel.width - num_filter_rects*Box.WIDTH) / (num_filter_rects-1)
        self.overlay_filter_rects = [
            get_rect(
                width=Box.WIDTH, height=Box.HEIGHT,
                left=self.overlay_left_panel.left+i*(Box.WIDTH+filter_rect_padding),
                bottom=self.overlay_left_panel.top
            ) for i in range(5)
        ]
        self.selected_overlay_filter = None
        self.shipgirl_filters = ["USS", "HMS", "IJN", "KMS"]
        self.equipment_filters = ["DD", "CL", "CA", "BB", "AUX"]
        self.siren_filters = ["DD", "CA", "BB"]

        num_icons_per_row = (self.overlay_left_panel.width-Box.PADDING) // (Box.WIDTH+Box.PADDING)
        icon_padding = (self.overlay_left_panel.width - 2*Box.PADDING - num_icons_per_row*Box.WIDTH) / (num_icons_per_row-1)
        self.overlay_left_icons = [
            get_rect(
                width=Box.WIDTH, height=Box.HEIGHT,
                left=self.overlay_left_panel.left+Box.PADDING+(i%num_icons_per_row)*(Box.WIDTH+icon_padding),
                top=self.overlay_left_panel.top+Box.PADDING+(i//num_icons_per_row)*(Box.HEIGHT+icon_padding)
            ) for i in range(16)
        ]

        self.overlay_right_name = pygame.Vector2(
            self.overlay_right_panel.centerx,
            self.overlay_right_panel.top+Box.PADDING
        )
        self.overlay_right_icon = get_rect(
            width=Box.WIDTH, height=Box.HEIGHT,
            centerx=self.overlay_right_panel.centerx,
            top=self.overlay_right_name.y+Box.PADDING
        )
        num_icons_per_row = 3
        self.overlay_right_icons = [
            get_rect(
                width=Box.WIDTH, height=Box.HEIGHT,
                left=self.overlay_right_panel.left+Box.PADDING+(i%num_icons_per_row)*(Box.WIDTH+Box.PADDING),
                bottom=self.overlay_right_panel.bottom-2*Box.PADDING-Box.HEIGHT+(i//num_icons_per_row)*(Box.HEIGHT+Box.PADDING)
            ) for i in range(6)
        ]

        def overlay_confirm():
            if self.current_overlay == self.SHIPYARD:
                selected_entity_info = DataFiles.shipgirl_data[self.overlay_selected_entity]
                hull_type = selected_entity_info["hull_type"]
                unique_item = selected_entity_info["unique_item"]
                selected_entity_reqs = {
                    f"{hull_type}_blueprint": 1,
                    "wisdom_cube": 1,
                    unique_item: 1
                }
                if all(DataFiles.save_file["inventory"].get(ingredient, 0) >= req for ingredient, req in selected_entity_reqs.items()):
                    num_shipgirls_in_port = len(DataFiles.save_file["shipgirls"])
                    DataFiles.save_file["shipgirls"][self.overlay_selected_entity] = {
                        "equipment": [None, None, None],
                        "exp": Stats.RESEARCH_EXP_REQUIREMENTS[num_shipgirls_in_port]
                    }
                    shipgirl = Shipgirl(self.overlay_selected_entity, True)
                    self.menu_manager.available_shipgirls.append(shipgirl)
                    for ingredient, req in selected_entity_reqs.items():
                        DataFiles.save_file["inventory"][ingredient] -= req
                    DataFiles.save_file["research_target"] = None
                    self.overlay_selected_entity = None
                else:
                    DataFiles.save_file["research_target"] = self.overlay_selected_entity
            elif self.current_overlay == self.GEAR_LAB:
                selected_entity_reqs = DataFiles.equipment_data[self.overlay_selected_entity]["craft_reqs"]
                if all(DataFiles.save_file["inventory"].get(ingredient, 0) >= req for ingredient, req in selected_entity_reqs.items()):
                    DataFiles.save_file["equipment"][self.overlay_selected_entity] = DataFiles.save_file["equipment"].get(self.overlay_selected_entity, 0) + 1
                    for ingredient, req in selected_entity_reqs.items():
                        DataFiles.save_file["inventory"][ingredient] -= req

        self.overlay_confirm_button = Button(
            rect=get_rect(
                width=2*Box.WIDTH, height=Box.HEIGHT,
                centerx=self.overlay_right_panel.centerx,
                bottom=self.overlay_right_panel.bottom-Box.PADDING
            ),
            color=Color.BLUE_GREY,
            text=None,
            text_pos=(0.66,0.5),
            text_color=Color.WHITE,
            callback=overlay_confirm,
            active=False
        )
        self.overlay_selected_entity = None

        def open_select_sortie_menu():
            self.menu_manager.current_menu = self.menu_manager.sortie_selection_menu

        self.open_select_sortie_menu_button = Button(
            rect=get_rect(
                width=Box.WIDTH, height=Box.HEIGHT,
                centerx=screen_x(5/6),
                bottom=Box.BOTTOM_OF_SCREEN
            ),
            color=Color.BLUE_GREY,
            sprite=DataFiles.sprites["sortie"],
            callback=open_select_sortie_menu,
            active=False
        )

        self.update_encountered_sirens()

    def update_encountered_sirens(self):
        self.encountered_sirens = set()
        for i in range(DataFiles.save_file["sortie_progress"]):
            encounters = DataFiles.sortie_data[i]["encounters"]
            for encounter in encounters:
                self.encountered_sirens = self.encountered_sirens.union(encounter["front"] + encounter["back"])
        self.encountered_sirens = list(self.encountered_sirens)

    def update_no_overlay(self, events):
        for event in events:
            if event.type == pygame.MOUSEBUTTONUP:
                selected_quest_id = self.menu_manager.quest_manager.selected_quest_id
                if selected_quest_id is not None:
                    selected_quest = self.menu_manager.quest_manager.selected_quest
                    finished_dialogue = selected_quest.go_next(self.menu_manager, event.pos)
                    if finished_dialogue:
                        if selected_quest.start(self.menu_manager):
                            DataFiles.save_file["quests"][selected_quest_id] = "in_progress"
                        
                        if selected_quest.completed:
                            selected_quest.on_complete(self.menu_manager)
                            self.menu_manager.quest_manager.quests.pop(selected_quest_id, None)
                            DataFiles.save_file["quests"][selected_quest_id] = "completed"
                        if selected_quest.started:
                            self.menu_manager.quest_manager.selected_quest_id = None
                    break

                for shipgirl in self.menu_manager.available_shipgirls:
                    if shipgirl.rect.collidepoint(event.pos):
                        self.menu_manager.equipment_menu.selected_shipgirl = shipgirl
                        self.menu_manager.current_menu = self.menu_manager.equipment_menu
                
                self.menu_manager.quest_manager.select_quest(event.pos)
                self.open_select_sortie_menu_button.click(event.pos)
                self.open_depot_overlay_button.click(event.pos)
                self.open_shipyard_overlay_button.click(event.pos)
                self.open_gear_lab_overlay_button.click(event.pos)
                self.open_intel_center_overlay_button.click(event.pos)

                for choose_faction_button in self.choose_faction_buttons:
                    choose_faction_button.click(event.pos)

    def draw_inventory_overlay(self, surface, font):
        pygame.draw.rect(surface, Color.DARK_BLUE, self.overlay_bg)

        num_items_in_row = (self.overlay_bg.width - 2*Box.PADDING) // Box.WIDTH - 1
        padding = (self.overlay_bg.width - 2*Box.PADDING - num_items_in_row*Box.WIDTH) / (num_items_in_row-1)
        item_index = 0
        for item, count in DataFiles.save_file["inventory"].items():
            if count <= 0:
                continue
            left = self.overlay_bg.left + Box.PADDING + (item_index%num_items_in_row)*(Box.WIDTH + padding)
            top = self.overlay_bg.top + Box.PADDING + (item_index//num_items_in_row)*(Box.HEIGHT+padding)
            rect = get_rect(width=Box.WIDTH, height=Box.HEIGHT, left=left, top=top)
            pygame.draw.rect(surface, Color.WHITE, rect, width=Box.OUTLINE_WIDTH)
            if item in DataFiles.sprites:
                surface.blit(DataFiles.sprites[item], rect)
                font.render(surface, str(count), rect.center, Color.WHITE, 1, style="center", outline_color=Color.BLACK)
            else:
                font.render(surface, f"{item} ({count})", rect.center, Color.WHITE, 1, style="center", outline_color=Color.BLACK)
            item_index += 1

    def exit_overlay(self, mouseup_event):
        if not self.overlay_bg.collidepoint(mouseup_event.pos):
            self.current_overlay = self.NO_OVERLAY
            self.overlay_confirm_button.active = False
            self.selected_overlay_filter = None
            self.overlay_selected_entity = None

    def overlay_mouseup_logic(self, mouseup_event, entities, entity_filters, activate_confirm_button):
        for entity, rect in zip(entities, self.overlay_left_icons):
            if rect.collidepoint(mouseup_event.pos):
                self.overlay_selected_entity = entity
                self.overlay_confirm_button.active = activate_confirm_button

                if self.current_overlay == self.SHIPYARD:
                    unique_item = DataFiles.shipgirl_data[self.overlay_selected_entity]["unique_item"]
                    if unique_item in DataFiles.save_file["inventory"]:
                        self.overlay_confirm_button.sprite = DataFiles.sprites["gear_lab"]
                        self.overlay_confirm_button.text = "construct"
                    else:
                        self.overlay_confirm_button.sprite = DataFiles.sprites["research"]
                        self.overlay_confirm_button.text = "research"
                else:
                    self.overlay_confirm_button.sprite = DataFiles.sprites["gear_lab"]
                    self.overlay_confirm_button.text = "construct"
        
        for i, (cat, rect) in enumerate(zip(entity_filters, self.overlay_filter_rects)):
            if rect.collidepoint(mouseup_event.pos):
                if self.selected_overlay_filter == i:
                    self.selected_overlay_filter = None
                else:
                    self.selected_overlay_filter = i

    def draw_dual_panel_overlay(self, surface, font, entities, entity_filters, info, icons):
        pygame.draw.rect(surface, Color.BLUE_GREY, self.overlay_bg)
        pygame.draw.rect(surface, Color.DARK_BLUE, self.overlay_left_panel)
        pygame.draw.rect(surface, Color.DARK_BLUE, self.overlay_right_panel)

        for i, (cat, rect) in enumerate(zip(entity_filters, self.overlay_filter_rects)):
            if self.selected_overlay_filter == i:
                pygame.draw.rect(surface, Color.DARK_BLUE, rect)
            else:
                pygame.draw.rect(surface, Color.BLUE, rect)
            if cat in DataFiles.sprites:
                icon = DataFiles.sprites[cat]
                icon_rect = icon.get_rect()
                icon_rect.center = rect.center
                surface.blit(icon, icon_rect)
            else:
                font.render(surface, cat, rect.center, Color.WHITE, 1, style="center", outline_color=Color.BLACK)

        for entity, rect in zip(entities, self.overlay_left_icons):
            pygame.draw.rect(surface, Color.WHITE, rect, width=Box.OUTLINE_WIDTH)
            if entity in DataFiles.sprites:
                image = DataFiles.sprites[entity]
                image_rect = image.get_rect()
                image_rect.center = rect.center
                surface.blit(image, image_rect)
            else:
                font.render(surface, entity, rect.center, Color.WHITE, 1, style="center", outline_color=Color.BLACK)
        
        if self.overlay_selected_entity:
            font.render(surface, self.overlay_selected_entity, self.overlay_right_name, Color.WHITE, 1, style="center", outline_color=Color.BLACK)
            if self.overlay_selected_entity in DataFiles.sprites:
                surface.blit(DataFiles.sprites[self.overlay_selected_entity], self.overlay_right_icon)
            pygame.draw.rect(surface, Color.WHITE, self.overlay_right_icon, width=Box.OUTLINE_WIDTH)

            icon_size = 32 # TODO
            left_align = [
                self.overlay_right_panel.left + Box.PADDING,
                self.overlay_right_panel.centerx + Box.PADDING
            ]
            y = self.overlay_right_icon.bottom + Box.PADDING
            info_index = 0
            for info_key, info_value in info.items():
                if info_value is None:
                    continue

                x = left_align[info_index%2]
                if info_key in DataFiles.sprites:
                    info_icon = DataFiles.sprites[info_key]
                    info_rect = info_icon.get_rect()
                    info_rect.left = x
                    info_rect.top = y
                    surface.blit(info_icon, info_rect)
                else:
                    info_rect = get_rect(width=icon_size, height=icon_size, left=x, top=y)
                    font.render(
                        surface,
                        str(info_key),
                        info_rect.center,
                        Color.WHITE,
                        1,
                        style="center",
                        outline_color=Color.BLACK
                    )
                font.render(
                    surface,
                    str(info_value),
                    (info_rect.right + Box.PADDING, info_rect.centery),
                    Color.WHITE,
                    1,
                    style="centerleft",
                    outline_color=Color.BLACK
                )
                
                info_index += 1
                if info_index % 2 == 0:
                    y += icon_size

            for (icon_name, icon_text), rect in zip(icons, self.overlay_right_icons):
                if icon_name in DataFiles.sprites:
                    surface.blit(DataFiles.sprites[icon_name], rect)
                    pygame.draw.rect(surface, Color.WHITE, rect, width=Box.OUTLINE_WIDTH)
                else:
                    pygame.draw.rect(surface, Color.WHITE, rect, width=Box.OUTLINE_WIDTH)
                    xy = (rect.centerx, rect.top+0.33*rect.height) # TODO
                    font.render(surface, icon_name, xy, Color.WHITE, 1, style="center", outline_color=Color.BLACK)
                xy = (rect.centerx, rect.top+0.67*rect.height)
                font.render(surface, icon_text, xy, Color.WHITE, 1, style="center", outline_color=Color.BLACK)

    def update_shipyard_overlay(self, events):
        for event in events:
            if event.type == pygame.MOUSEBUTTONUP:
                self.exit_overlay(event)

                if self.selected_overlay_filter is None:
                    shipgirls = [
                        shipgirl for shipgirl, shipgirl_info in DataFiles.shipgirl_data.items()
                        if shipgirl not in DataFiles.save_file["shipgirls"]
                        and shipgirl_info["faction"] in DataFiles.save_file["unlocked_factions"]
                    ]
                else:
                    shipgirls = [
                        shipgirl for shipgirl, shipgirl_info in DataFiles.shipgirl_data.items()
                        if shipgirl not in DataFiles.save_file["shipgirls"]
                        and shipgirl_info["faction"] in DataFiles.save_file["unlocked_factions"]
                        and shipgirl_info["faction"] == self.shipgirl_filters[self.selected_overlay_filter]
                    ]
                self.overlay_mouseup_logic(event, shipgirls, self.shipgirl_filters, True)
                self.overlay_confirm_button.click(event.pos)

    def draw_shipyard_overlay(self, surface, font):
        if self.selected_overlay_filter is None:
            shipgirls = [
                shipgirl for shipgirl, shipgirl_info in DataFiles.shipgirl_data.items()
                if shipgirl not in DataFiles.save_file["shipgirls"]
                and shipgirl_info["faction"] in DataFiles.save_file["unlocked_factions"]
            ]
        else:
            shipgirls = [
                shipgirl for shipgirl, shipgirl_info in DataFiles.shipgirl_data.items()
                if shipgirl not in DataFiles.save_file["shipgirls"]
                and shipgirl_info["faction"] in DataFiles.save_file["unlocked_factions"]
                and shipgirl_info["faction"] == self.shipgirl_filters[self.selected_overlay_filter]
            ]
        if self.overlay_selected_entity:
            selected_entity_info = DataFiles.shipgirl_data.get(self.overlay_selected_entity, {})
            hull_type = selected_entity_info["hull_type"]
            unique_item = selected_entity_info["unique_item"]
            inventory = DataFiles.save_file["inventory"]
            research_reqs = [f"{hull_type}_blueprint", "wisdom_cube", unique_item]
            research_icons = [
                (research_req, f"{inventory.get(research_req,0)}/1")
                for research_req in research_reqs
            ]
            hull_type = selected_entity_info.get("hull_type")
            selected_entity_stats = DataFiles.stats_data[hull_type]
            num_shipgirls_in_port = len(DataFiles.save_file["shipgirls"])
            research_shipgirl_exp = Stats.RESEARCH_EXP_REQUIREMENTS[num_shipgirls_in_port]
            shipgirl_stats = {
                "hull_type": hull_type,
                "max_hp": Stats.stat(research_shipgirl_exp, *selected_entity_stats["max_hp"]),
                "evasion": Stats.stat(research_shipgirl_exp, *selected_entity_stats["evasion"]),
                "firepower": Stats.stat(research_shipgirl_exp, *selected_entity_stats["firepower"]),
                "reload": Stats.stat(research_shipgirl_exp, *selected_entity_stats["reload"]),
                "EXP": research_shipgirl_exp
            }
        else:
            research_icons = []
            shipgirl_stats = {}
        self.draw_dual_panel_overlay(
            surface, font,
            shipgirls,
            self.shipgirl_filters,
            shipgirl_stats,
            research_icons
        )

    def update_gear_lab_overlay(self, events):
        for event in events:
            if event.type == pygame.MOUSEBUTTONUP:
                self.exit_overlay(event)

                if self.selected_overlay_filter is None:
                    equipment = [equip for equip in DataFiles.equipment_data]
                elif self.selected_overlay_filter == 4: # TODO
                    equipment = [
                        equip for equip, equip_data in DataFiles.equipment_data.items()
                        if equip_data["type"] == "aux"
                    ]
                else:
                    equipment = [
                        equip for equip, equip_data in DataFiles.equipment_data.items()
                        if equip_data["type"] == "weapon"
                        and equip_data["equippable_by"] == self.equipment_filters[self.selected_overlay_filter]
                    ]
                self.overlay_mouseup_logic(event, equipment, self.equipment_filters, True)
                self.overlay_confirm_button.click(event.pos)

    def draw_gear_lab_overlay(self, surface, font):
        if self.selected_overlay_filter is None:
            equipment = [equip for equip in DataFiles.equipment_data]
        elif self.selected_overlay_filter == 4: # TODO
            equipment = [
                equip for equip, equip_data in DataFiles.equipment_data.items()
                if equip_data["type"] == "aux"
            ]
        else:
            equipment = [
                equip for equip, equip_data in DataFiles.equipment_data.items()
                if equip_data["type"] == "weapon"
                and equip_data["equippable_by"] == self.equipment_filters[self.selected_overlay_filter]
            ]
        if self.overlay_selected_entity:
            selected_entity_info = DataFiles.equipment_data.get(self.overlay_selected_entity)
            crafting_reqs = selected_entity_info.get("craft_reqs")
            inventory = DataFiles.save_file["inventory"]
            crafting_icons = [
                (material, f"{inventory.get(material,0)}/{req}")
                for material, req in crafting_reqs.items()
            ]
            equip_stats = {
                "hull_type": selected_entity_info.get("equippable_by"),
                "max_hp": selected_entity_info.get("max_hp"),
                "evasion": selected_entity_info.get("evasion"),
                "firepower": selected_entity_info.get("firepower"),
                "reload": selected_entity_info.get("reload"),
                "shell_type": selected_entity_info.get("shell_type"),
            }
        else:
            crafting_icons = []
            equip_stats = {}
        self.draw_dual_panel_overlay(
            surface, font,
            equipment,
            self.equipment_filters,
            equip_stats,
            crafting_icons
        )

    def update_intel_center_overlay(self, events):
        for event in events:
            if event.type == pygame.MOUSEBUTTONUP:
                self.exit_overlay(event)

                if self.selected_overlay_filter is None:
                    encountered_sirens = self.encountered_sirens
                else:
                    encountered_sirens = [
                        siren for siren in self.encountered_sirens
                        if self.siren_filters[self.selected_overlay_filter] == siren # TODO
                    ]
                self.overlay_mouseup_logic(event, encountered_sirens, self.siren_filters, False)

    def draw_intel_center_overlay(self, surface, font):
        if self.selected_overlay_filter is None:
            encountered_sirens = self.encountered_sirens
        else:
            encountered_sirens = [
                siren for siren in self.encountered_sirens
                if self.siren_filters[self.selected_overlay_filter] == siren # TODO
            ]
        if self.overlay_selected_entity:
            selected_entity_info = DataFiles.siren_data.get(self.overlay_selected_entity)
            drop_rates = selected_entity_info["drops"]
            drop_icons = [
                (drop, str(drop_rate))
                for drop, drop_rate in drop_rates.items()
            ]
            siren_stats = {
                "hull_type": selected_entity_info.get("hull_type"),
                "max_hp": selected_entity_info["max_hp"][0],
                "evasion": selected_entity_info["evasion"][0],
                "firepower": selected_entity_info["firepower"][0],
                "reload": selected_entity_info["reload"][0],
                "target_pref": selected_entity_info["target_pref"],
                "EXP": selected_entity_info["exp"],
            }
        else:
            drop_icons = []
            siren_stats = {}
        self.draw_dual_panel_overlay(
            surface, font,
            encountered_sirens,
            self.siren_filters,
            siren_stats,
            drop_icons
        )

    def update(self, dt, events):
        if self.current_overlay == self.NO_OVERLAY:
            self.update_no_overlay(events)
        elif self.current_overlay == self.DEPOT:
            for event in events:
                if event.type == pygame.MOUSEBUTTONUP:
                    self.exit_overlay(event)
        elif self.current_overlay == self.SHIPYARD:
            self.update_shipyard_overlay(events)
        elif self.current_overlay == self.GEAR_LAB:
            self.update_gear_lab_overlay(events)
        elif self.current_overlay == self.INTEL_CENTER:
            self.update_intel_center_overlay(events)
        
        for shipgirl in self.menu_manager.available_shipgirls:
            shipgirl.update(dt)

    def draw(self, surface, font):
        for shipgirl in self.menu_manager.available_shipgirls:
            shipgirl.draw(surface, font)
        self.open_select_sortie_menu_button.draw(surface, font)

        self.open_depot_overlay_button.draw(surface, font)
        self.open_shipyard_overlay_button.draw(surface, font)
        self.open_gear_lab_overlay_button.draw(surface, font)
        self.open_intel_center_overlay_button.draw(surface, font)

        if self.current_overlay != self.NO_OVERLAY:
            if self.current_overlay == self.DEPOT:
                self.draw_inventory_overlay(surface, font)
            if self.current_overlay == self.SHIPYARD: 
                self.draw_shipyard_overlay(surface, font)
            elif self.current_overlay == self.GEAR_LAB:
                self.draw_gear_lab_overlay(surface, font)
            elif self.current_overlay == self.INTEL_CENTER:
                self.draw_intel_center_overlay(surface, font)

            self.overlay_confirm_button.draw(surface, font)
    
        self.menu_manager.quest_manager.draw(surface, font)
        for choose_faction_button in self.choose_faction_buttons:
            choose_faction_button.draw(surface, font)
