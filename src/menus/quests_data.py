import pygame

from engine.util import get_rect, hex_to_pixel
from src.constants import DataFiles, Box, Color

from src.menus.quests import Quest
from src.menus.sortie_selection_menu import SortieNode

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

    if text is not None:
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

first_sortie_dialogue_texts = [
    "it's time to set sail!",
    "sortie into zone 1"
]

def first_sortie_completion_criteria(menu_manager):
    return DataFiles.save_file["sortie_progress"] == 1

def first_sortie_tutorial_draw(menu_manager, surface, font):
    if menu_manager.current_menu == menu_manager.port_menu:
        button_rect = menu_manager.port_menu.open_select_sortie_menu_button.rect
        rect = get_rect(
            width=button_rect.width + 2*Box.PADDING,
            height=button_rect.height + 2*Box.PADDING,
            center=button_rect.center
        )
        pygame.draw.rect(surface, Color.RED, rect, width=Box.OUTLINE_WIDTH)

        draw_tb(surface, font, None, rect.topright, True, False)
    elif menu_manager.current_menu == menu_manager.sortie_selection_menu:
        q, r = menu_manager.sortie_selection_menu.sortie_nodes[0].hexes[0]
        xy = hex_to_pixel(q, r, SortieNode.SIZE)
        rect = get_rect(
            width=2*SortieNode.SIZE, height=2*SortieNode.SIZE,
            center=pygame.Vector2(xy) + SortieNode.CENTER
        )
        pygame.draw.rect(surface, Color.RED, rect, width=Box.OUTLINE_WIDTH)

        draw_tb(surface, font, None, rect.bottomright, False, False)
    elif menu_manager.current_menu == menu_manager.fleet_selection_menu:
        if menu_manager.fleet_selection_menu.start_sortie_button.active:
            button_rect = menu_manager.fleet_selection_menu.start_sortie_button.rect
            rect = get_rect(
                width=button_rect.width + 2*Box.PADDING,
                height=button_rect.height + 2*Box.PADDING,
                center=button_rect.center
            )
            pygame.draw.rect(surface, Color.RED, rect, width=Box.OUTLINE_WIDTH)

            draw_tb(surface, font, None, rect.topleft, True, True)
        else:
            center_fleet_slot = menu_manager.fleet_selection_menu.fleet_slots[1]
            rect = get_rect(
                width=3*Box.WIDTH + 4*Box.PADDING,
                height=Box.HEIGHT + 2*Box.PADDING,
                center=center_fleet_slot.center
            )
            pygame.draw.rect(surface, Color.RED, rect, width=Box.OUTLINE_WIDTH)

            draw_tb(
                surface, font,
                "drag laffey and new jersey to your fleet",
                rect.bottomright,
                False, False
            )
    elif menu_manager.current_menu == menu_manager.encounter_menu:
        if not menu_manager.encounter_menu.encounter_started:
            for siren in menu_manager.siren_fleet.front:
                pygame.draw.rect(surface, Color.RED, siren.rect, width=Box.OUTLINE_WIDTH)
            
            draw_tb(
                surface, font,
                "drag all of your shipgirls onto the enemy siren",
                menu_manager.siren_fleet.front[0].rect.topleft,
                True, True
            )
        elif menu_manager.encounter_menu.next_encounter_button.active:
            button_rect = menu_manager.encounter_menu.next_encounter_button.rect
            rect = get_rect(
                width=button_rect.width + 2*Box.PADDING,
                height=button_rect.height + 2*Box.PADDING,
                center=button_rect.center
            )
            pygame.draw.rect(surface, Color.RED, rect, width=Box.OUTLINE_WIDTH)

            draw_tb(surface, font, None, rect.bottomleft, False, True)
        elif menu_manager.encounter_menu.return_to_port_button.active:
            button_rect = menu_manager.encounter_menu.return_to_port_button.rect
            rect = get_rect(
                width=button_rect.width + 2*Box.PADDING,
                height=button_rect.height + 2*Box.PADDING,
                center=button_rect.center
            )
            pygame.draw.rect(surface, Color.RED, rect, width=Box.OUTLINE_WIDTH)

            draw_tb(surface, font, None, rect.bottomleft, False, True)

def first_sortie_on_start(menu_manager):
    menu_manager.port_menu.open_select_sortie_menu_button.active = True

def first_sortie_on_complete(menu_manager):
    menu_manager.port_menu.shipyard_building.unlocked = True

first_sortie_quest = Quest(
    first_sortie_dialogue_texts,
    first_sortie_completion_criteria,
    first_sortie_tutorial_draw,
    first_sortie_on_start,
    first_sortie_on_complete
)