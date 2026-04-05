import pygame

from engine.util import get_rect, pixel_to_hex, hex_to_pixel

from src.constants import DataFiles, Color, Box, screen_x, screen_y

from src.menus.sortie_selection_menu import SortieNode
from src.menus.port_menu import PortMenu

class TutorialTask:
    def __init__(self, tutorial_input, tutorial_draw):
        self.tutorial_input = tutorial_input
        self.tutorial_draw = tutorial_draw

    def check_completion(self, event):
        return self.tutorial_input(event)

class Tutorial:
    def __init__(self, tasks, on_complete):
        self.tasks = tasks
        self.task_index = 0
        self.completed = False
        self.on_complete = on_complete

    @property
    def current_task(self):
        if self.task_index < len(self.tasks):
            return self.tasks[self.task_index]
        return None

    def check_completion(self, event):
        if self.current_task.check_completion(event):
            self.task_index += 1
            if self.task_index == len(self.tasks):
                self.completed = True
            return True
        return False

    def draw(self, surface, font):
        current_task = self.current_task
        if current_task is not None:
            current_task.tutorial_draw(surface, font)

class Tutorials:
    def __init__(self, menu_manager):
        self.menu_manager = menu_manager
        
        def draw_tb(surface, font, text, point_pos, point_down, point_right):
            point_pos = pygame.Vector2(point_pos)

            if point_down:
                pointer = DataFiles.sprites["TB_point_down"]
            else:
                pointer = DataFiles.sprites["TB_point_up"]
            
            pointer = pygame.transform.flip(pointer, point_right, False)
            pointer_rect = pointer.get_rect()
            if point_down:
                pointer_rect.bottom = point_pos.y
            else:
                pointer_rect.top = point_pos.y
            if point_right:
                pointer_rect.right = point_pos.x
            else:
                pointer_rect.left = point_pos.x
            surface.blit(pointer, pointer_rect)

            text_scale = 1
            text_width = 4*Box.WIDTH - Box.PADDING
            text_height = font.get_height(text, text_scale, text_width)
            text_box_width = font.get_width(text, text_scale, text_width)
            text_rect = get_rect(
                width=text_box_width + Box.PADDING,
                height=text_height + Box.PADDING,
                centerx=pointer_rect.centerx,
                bottom=pointer_rect.top
            )
            if point_right:
                text_rect.right = pointer_rect.left
                polygon = [
                    (text_rect.right, text_rect.bottom-Box.PADDING),
                    (text_rect.right+Box.PADDING, text_rect.bottom+Box.PADDING),
                    (text_rect.right-Box.PADDING, text_rect.bottom)
                ]
            else:
                text_rect.left = pointer_rect.right
                polygon = [
                    (text_rect.left, text_rect.bottom-Box.PADDING),
                    (text_rect.left-Box.PADDING, text_rect.bottom+Box.PADDING),
                    (text_rect.left+Box.PADDING, text_rect.bottom)
                ]
            pygame.draw.rect(surface, Color.DARK_BLUE, text_rect)
            pygame.draw.polygon(surface, Color.DARK_BLUE, polygon)
            font.render(
                surface,
                text,
                pygame.Vector2(text_rect.topleft) + pygame.Vector2(0.5*Box.PADDING, 0.5*Box.PADDING),
                Color.WHITE,
                text_scale,
                outline_color=Color.BLACK,
                box_width=text_width
            )
            
        def start_sortie_on_complete():
            self.menu_manager.tutorial = self.assign_fleet

        def draw_start_a_sortie(surface, font):
            button_rect = self.menu_manager.port_menu.open_select_sortie_menu_button.rect
            rect = get_rect(
                width=button_rect.width + 2*Box.PADDING,
                height=button_rect.height + 2*Box.PADDING,
                center=button_rect.center
            )
            pygame.draw.rect(surface, Color.RED, rect, width=Box.OUTLINE_WIDTH)

            draw_tb(
                surface, font,
                "let's start a sortie!",
                rect.topright,
                True, False
            )

        def select_sortie_node(event):
            mouse_x, mouse_y = event.pos
            hx, hy = pixel_to_hex(mouse_x - SortieNode.CENTER.x, mouse_y - SortieNode.CENTER.y, SortieNode.SIZE)
            return (hx, hy) in self.menu_manager.sortie_selection_menu.sortie_nodes[0].hexes

        def draw_select_sortie_node(surface, font):
            q, r = self.menu_manager.sortie_selection_menu.sortie_nodes[0].hexes[0]
            xy = hex_to_pixel(q, r, SortieNode.SIZE)
            rect = get_rect(
                width=2*SortieNode.SIZE, height=2*SortieNode.SIZE,
                center=pygame.Vector2(xy) + SortieNode.CENTER
            )
            pygame.draw.rect(surface, Color.RED, rect, width=Box.OUTLINE_WIDTH)

            draw_tb(
                surface, font,
                "select the area to explore",
                rect.bottomright,
                False, False
            )

        self.start_sortie = Tutorial([
            TutorialTask(
                lambda event : self.menu_manager.port_menu.open_select_sortie_menu_button.rect.collidepoint(event.pos),
                draw_start_a_sortie
            ),
            TutorialTask(
                select_sortie_node,
                draw_select_sortie_node
            ),
        ], start_sortie_on_complete)

        def assign_fleet_on_complete():
            self.menu_manager.tutorial = self.combat_mechanics

        def assign_laffey_input(event):
            return (
                self.menu_manager.available_shipgirl_rects[0].collidepoint(self.menu_manager.mouse_start_drag)
                and any(fleet_slot.collidepoint(event.pos) for fleet_slot in self.menu_manager.fleet_selection_menu.fleet_slots)
            )

        def draw_assign_laffey(surface, font):
            shipgirl_rect = self.menu_manager.available_shipgirl_rects[0]
            rect = get_rect(
                width=shipgirl_rect.width + 2*Box.PADDING,
                height=shipgirl_rect.height + 2*Box.PADDING,
                center=shipgirl_rect.center
            )
            pygame.draw.rect(surface, Color.RED, rect, width=Box.OUTLINE_WIDTH)

            draw_tb(
                surface, font,
                "drag laffey...",
                rect.topleft,
                True, True
            )

            center_fleet_slot = self.menu_manager.fleet_selection_menu.fleet_slots[1]
            rect = get_rect(
                width=3*Box.WIDTH + 4*Box.PADDING,
                height=Box.HEIGHT + 2*Box.PADDING,
                center=center_fleet_slot.center
            )
            pygame.draw.rect(surface, Color.RED, rect, width=Box.OUTLINE_WIDTH)

            draw_tb(
                surface, font,
                "...and assign her to your fleet",
                rect.bottomright,
                False, False
            )

        def assign_new_jersey_input(event):
            return (
                self.menu_manager.available_shipgirl_rects[1].collidepoint(self.menu_manager.mouse_start_drag)
                and any(fleet_slot.collidepoint(event.pos) for fleet_slot in self.menu_manager.fleet_selection_menu.fleet_slots)
            )
    
        def draw_assign_new_jersey(surface, font):
            shipgirl_rect = self.menu_manager.available_shipgirl_rects[1]
            rect = get_rect(
                width=shipgirl_rect.width + 2*Box.PADDING,
                height=shipgirl_rect.height + 2*Box.PADDING,
                center=shipgirl_rect.center
            )
            pygame.draw.rect(surface, Color.RED, rect, width=Box.OUTLINE_WIDTH)

            draw_tb(
                surface, font,
                "drag new jersey...",
                rect.topleft,
                True, True
            )

            center_fleet_slot = self.menu_manager.fleet_selection_menu.fleet_slots[1]
            rect = get_rect(
                width=3*Box.WIDTH + 4*Box.PADDING,
                height=Box.HEIGHT + 2*Box.PADDING,
                center=center_fleet_slot.center
            )
            pygame.draw.rect(surface, Color.RED, rect, width=Box.OUTLINE_WIDTH)

            draw_tb(
                surface, font,
                "...and assign her to your fleet",
                rect.bottomright,
                False, False
            )

        def draw_start_sortie(surface, font):
            button_rect = self.menu_manager.fleet_selection_menu.start_sortie_button.rect
            rect = get_rect(
                width=button_rect.width + 2*Box.PADDING,
                height=button_rect.height + 2*Box.PADDING,
                center=button_rect.center
            )
            pygame.draw.rect(surface, Color.RED, rect, width=Box.OUTLINE_WIDTH)

            draw_tb(
                surface, font,
                "we're ready to start our sortie!",
                rect.topleft,
                True, True
            )

        self.assign_fleet = Tutorial([
            TutorialTask(
                assign_laffey_input,
                draw_assign_laffey
            ),
            TutorialTask(
                assign_new_jersey_input,
                draw_assign_new_jersey
            ),
            TutorialTask(
                lambda event : self.menu_manager.fleet_selection_menu.start_sortie_button.rect.collidepoint(event.pos),
                draw_start_sortie
            ),
        ], assign_fleet_on_complete)

        def combat_mechanics_on_complete():
            self.menu_manager.tutorial = None
        
        def combat_mechanics_input(event):
            return (
                self.menu_manager.player_fleet.front.rect.collidepoint(self.menu_manager.mouse_start_drag)
                and any(siren.rect.collidepoint(event.pos) for siren in self.menu_manager.siren_fleet.front)
            )

        def draw_combat_mechanics(surface, font):
            pygame.draw.rect(surface, Color.RED, self.menu_manager.player_fleet.front.rect, width=Box.OUTLINE_WIDTH)

            draw_tb(
                surface, font,
                "drag laffey...",
                self.menu_manager.player_fleet.front.rect.bottomright,
                False, False
            )

            for siren in self.menu_manager.siren_fleet.front:
                pygame.draw.rect(surface, Color.RED, siren.rect, width=Box.OUTLINE_WIDTH)
            
            draw_tb(
                surface, font,
                "...onto the enemy siren",
                self.menu_manager.siren_fleet.front[0].rect.topleft,
                True, True
            )

        self.combat_mechanics = Tutorial([
            TutorialTask(
                combat_mechanics_input,
                draw_combat_mechanics
            ),
        ], combat_mechanics_on_complete)

        def next_encounter_on_complete():
            self.menu_manager.tutorial = None
        
        def draw_next_encounter(surface, font):
            button_rect = self.menu_manager.encounter_menu.next_encounter_button.rect
            rect = get_rect(
                width=button_rect.width + 2*Box.PADDING,
                height=button_rect.height + 2*Box.PADDING,
                center=button_rect.center
            )
            pygame.draw.rect(surface, Color.RED, rect, width=Box.OUTLINE_WIDTH)

            draw_tb(
                surface, font,
                "go to the next encounter",
                rect.bottomleft,
                False, True
            )

        self.next_encounter = Tutorial([
            TutorialTask(
                lambda event : self.menu_manager.encounter_menu.next_encounter_button.rect.collidepoint(event.pos),
                draw_next_encounter
            ),
        ], next_encounter_on_complete)

        def draw_return_to_port(surface, font):
            button_rect = self.menu_manager.encounter_menu.return_to_port_button.rect
            rect = get_rect(
                width=button_rect.width + 2*Box.PADDING,
                height=button_rect.height + 2*Box.PADDING,
                center=button_rect.center
            )
            pygame.draw.rect(surface, Color.RED, rect, width=Box.OUTLINE_WIDTH)

            draw_tb(
                surface, font,
                "let's go home",
                rect.bottomleft,
                False, True
            )

        self.return_to_port = Tutorial([
            TutorialTask(
                lambda event : self.menu_manager.encounter_menu.return_to_port_button.rect.collidepoint(event.pos),
                draw_return_to_port
            ),
        ], lambda : True)

        def research_new_ship_on_complete():
            self.menu_manager.tutorial = None
        
        def draw_go_to_shipyard_new(surface, font):
            button_rect = self.menu_manager.port_menu.buildings[PortMenu.SHIPYARD].rect
            rect = get_rect(
                width=button_rect.width + 2*Box.PADDING,
                height=button_rect.height + 2*Box.PADDING,
                center=button_rect.center
            )
            pygame.draw.rect(surface, Color.RED, rect, width=Box.OUTLINE_WIDTH)

            draw_tb(
                surface, font,
                "let's research a new shipgirl! go to the shipyard",
                rect.bottomright,
                False, False
            )

        def draw_filter_by_shipgirl_faction(surface, font):
            button_rect = self.menu_manager.port_menu.overlay_filter_rects[0]
            rect = get_rect(
                width=button_rect.width + 2*Box.PADDING,
                height=button_rect.height + 2*Box.PADDING,
                center=button_rect.center
            )
            pygame.draw.rect(surface, Color.RED, rect, width=Box.OUTLINE_WIDTH)

            draw_tb(
                surface, font,
                "filter the shipgirls by faction",
                rect.bottomright,
                False, False
            )

        def draw_select_guam_research(surface, font):
            button_rect = self.menu_manager.port_menu.overlay_left_icons[1]
            rect = get_rect(
                width=button_rect.width + 2*Box.PADDING,
                height=button_rect.height + 2*Box.PADDING,
                center=button_rect.center
            )
            pygame.draw.rect(surface, Color.RED, rect, width=Box.OUTLINE_WIDTH)

            draw_tb(
                surface, font,
                "let's research guam",
                rect.bottomright,
                False, False
            )
        
        def draw_confirm_research(surface, font):
            button_rect = self.menu_manager.port_menu.overlay_confirm_button.rect
            rect = get_rect(
                width=button_rect.width + 2*Box.PADDING,
                height=button_rect.height + 2*Box.PADDING,
                center=button_rect.center
            )
            pygame.draw.rect(surface, Color.RED, rect, width=Box.OUTLINE_WIDTH)

            draw_tb(
                surface, font,
                "start researching!",
                rect.bottomleft,
                False, True
            )

        def draw_exit_overlay(surface, font):
            draw_tb(
                surface, font,
                "exit the menu by clicking outside of the overlay",
                (self.menu_manager.port_menu.overlay_bg.right + 2*Box.PADDING, screen_y(0.25)),
                False, True
            )

        def draw_research_info(surface, font):
            draw_tb(
                surface, font,
                "earning exp will contribute towards researching new shipgirls. let's sortie again to collect combat data",
                (screen_x(0.5) - Box.PADDING, screen_y(0.5) - Box.PADDING),
                False, False
            )

        self.research_new_ship = Tutorial([
            TutorialTask(
                lambda event : self.menu_manager.port_menu.buildings[PortMenu.SHIPYARD].rect.collidepoint(event.pos),
                draw_go_to_shipyard_new
            ),
            TutorialTask(
                lambda event : self.menu_manager.port_menu.overlay_filter_rects[0].collidepoint(event.pos),
                draw_filter_by_shipgirl_faction
            ),
            TutorialTask(
                lambda event : self.menu_manager.port_menu.overlay_left_icons[1].collidepoint(event.pos),
                draw_select_guam_research
            ),
            TutorialTask(
                lambda event : self.menu_manager.port_menu.overlay_confirm_button.rect.collidepoint(event.pos),
                draw_confirm_research
            ),
            TutorialTask(
                lambda event : not self.menu_manager.port_menu.overlay_bg.collidepoint(event.pos),
                draw_exit_overlay
            ),
            TutorialTask(
                lambda event : True,
                draw_research_info
            )
        ], research_new_ship_on_complete)

        def construct_new_ship_on_complete():
            self.menu_manager.tutorial = None

        def draw_go_to_shipyard_done(surface, font):
            button_rect = self.menu_manager.port_menu.buildings[PortMenu.SHIPYARD].rect
            rect = get_rect(
                width=button_rect.width + 2*Box.PADDING,
                height=button_rect.height + 2*Box.PADDING,
                center=button_rect.center
            )
            pygame.draw.rect(surface, Color.RED, rect, width=Box.OUTLINE_WIDTH)

            draw_tb(
                surface, font,
                "we've collected enough combat data to construct guam! go to the shipyard",
                rect.bottomright,
                False, False
            )

        def draw_construct_guam(surface, font):
            button_rect = self.menu_manager.port_menu.overlay_confirm_button.rect
            rect = get_rect(
                width=button_rect.width + 2*Box.PADDING,
                height=button_rect.height + 2*Box.PADDING,
                center=button_rect.center
            )
            pygame.draw.rect(surface, Color.RED, rect, width=Box.OUTLINE_WIDTH)

            draw_tb(
                surface, font,
                "construct the shipgirl!",
                rect.bottomleft,
                False, True
            )
        
        def draw_new_shipgirl_in_fleet(surface, font):
            draw_tb(
                surface, font,
                "congratulations! guam has joined our fleet!",
                (self.menu_manager.port_menu.overlay_bg.right + 2*Box.PADDING, screen_y(0.25)),
                False, True
            )

        self.construct_new_ship = Tutorial([
            TutorialTask(
                lambda event : self.menu_manager.port_menu.buildings[PortMenu.SHIPYARD].rect.collidepoint(event.pos),
                draw_go_to_shipyard_done
            ),
            TutorialTask(
                lambda event : self.menu_manager.port_menu.overlay_confirm_button.rect.collidepoint(event.pos),
                draw_construct_guam
            ),
            TutorialTask(
                lambda event : True,
                draw_new_shipgirl_in_fleet
            )
        ], construct_new_ship_on_complete)

        def craft_new_gear_on_complete():
            self.menu_manager.tutorial = None

        def draw_go_to_gear_lab(surface, font):
            button_rect = self.menu_manager.port_menu.buildings[PortMenu.GEAR_LAB].rect
            rect = get_rect(
                width=button_rect.width + 2*Box.PADDING,
                height=button_rect.height + 2*Box.PADDING,
                center=button_rect.center
            )
            pygame.draw.rect(surface, Color.RED, rect, width=Box.OUTLINE_WIDTH)

            draw_tb(
                surface, font,
                "we've collected enough materials to craft a new weapon! go to the gear lab", 
                rect.bottomright,
                False, False
            )
        
        def draw_filter_by_hull_type(surface, font):
            button_rect = self.menu_manager.port_menu.overlay_filter_rects[1]
            rect = get_rect(
                width=button_rect.width + 2*Box.PADDING,
                height=button_rect.height + 2*Box.PADDING,
                center=button_rect.center
            )
            pygame.draw.rect(surface, Color.RED, rect, width=Box.OUTLINE_WIDTH)

            draw_tb(
                surface, font,
                "filter the gear we can craft by hull type",
                rect.bottomright,
                False, False
            )

        def draw_select_gun_to_craft(surface, font):
            button_rect = self.menu_manager.port_menu.overlay_left_icons[0]
            rect = get_rect(
                width=button_rect.width + 2*Box.PADDING,
                height=button_rect.height + 2*Box.PADDING,
                center=button_rect.center
            )
            pygame.draw.rect(surface, Color.RED, rect, width=Box.OUTLINE_WIDTH)

            draw_tb(
                surface, font,
                "let's craft this new DD gun", 
                rect.bottomright,
                False, False
            )
        
        def draw_craft_gun(surface, font):
            button_rect = self.menu_manager.port_menu.overlay_confirm_button.rect
            rect = get_rect(
                width=button_rect.width + 2*Box.PADDING,
                height=button_rect.height + 2*Box.PADDING,
                center=button_rect.center
            )
            pygame.draw.rect(surface, Color.RED, rect, width=Box.OUTLINE_WIDTH)

            draw_tb(
                surface, font,
                "craft!",
                rect.bottomleft,
                False, True
            )

        def draw_exit_overlay_gear(surface, font):
            draw_tb(
                surface, font,
                "exit the menu",
                (self.menu_manager.port_menu.overlay_bg.right + 2*Box.PADDING, screen_y(0.25)),
                False, True
            )

        def draw_select_laffey(surface, font):
            button_rect = self.menu_manager.available_shipgirls[0].rect
            rect = get_rect(
                width=button_rect.width + 2*Box.PADDING,
                height=button_rect.height + 2*Box.PADDING,
                center=button_rect.center
            )
            pygame.draw.rect(surface, Color.RED, rect, width=Box.OUTLINE_WIDTH)

            draw_tb(
                surface, font,
                "let's equip this new gun to laffey. click on her to open the equipment screen",
                rect.bottomright,
                False, False
            )

        def draw_equip_gun(surface, font):
            button_rect = self.menu_manager.equipment_menu.equippable_rects[0]
            rect = get_rect(
                width=button_rect.width + 2*Box.PADDING,
                height=button_rect.height + 2*Box.PADDING,
                center=button_rect.center
            )
            pygame.draw.rect(surface, Color.RED, rect, width=Box.OUTLINE_WIDTH)

            draw_tb(
                surface, font,
                "equip the gun",
                rect.bottomleft,
                False, True
            )

        def draw_equipment_info(surface, font):
            button_rect = self.menu_manager.equipment_menu.exit_equipment_menu_button.rect
            rect = get_rect(
                width=button_rect.width + 2*Box.PADDING,
                height=button_rect.height + 2*Box.PADDING,
                center=button_rect.center
            )
            pygame.draw.rect(surface, Color.RED, rect, width=Box.OUTLINE_WIDTH)

            draw_tb(
                surface, font,
                "congratulations! you've equipped a new gun on laffey! exit this menu",
                rect.bottomleft,
                False, True
            )

        self.craft_new_gear = Tutorial([
            TutorialTask(
                lambda event : self.menu_manager.port_menu.buildings[PortMenu.GEAR_LAB].rect.collidepoint(event.pos),
                draw_go_to_gear_lab
            ),
            TutorialTask(
                lambda event : self.menu_manager.port_menu.overlay_filter_rects[1].collidepoint(event.pos),
                draw_filter_by_hull_type
            ),
            TutorialTask(
                lambda event : self.menu_manager.port_menu.overlay_left_icons[0].collidepoint(event.pos),
                draw_select_gun_to_craft
            ),
            TutorialTask(
                lambda event : self.menu_manager.port_menu.overlay_confirm_button.rect.collidepoint(event.pos),
                draw_craft_gun
            ),
            TutorialTask(
                lambda event : not self.menu_manager.port_menu.overlay_bg.collidepoint(event.pos),
                draw_exit_overlay_gear
            ),
            TutorialTask(
                lambda event : self.menu_manager.available_shipgirls[0].rect.collidepoint(event.pos),
                draw_select_laffey
            ),
            TutorialTask(
                lambda event : self.menu_manager.equipment_menu.equippable_rects[0].collidepoint(event.pos),
                draw_equip_gun
            ),
            TutorialTask(
                lambda event : self.menu_manager.equipment_menu.exit_equipment_menu_button.rect.collidepoint(event.pos),
                draw_equipment_info
            ),
        ], craft_new_gear_on_complete)

        self.sortie_end_tutorial_triggers = {
            1: self.research_new_ship,
            2: self.construct_new_ship,
            3: self.craft_new_gear
        }
