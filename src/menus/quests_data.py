import pygame

from engine.util import get_rect, hex_to_pixel
from src.constants import DataFiles, Box, Color, Equipment

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
    "sortie into zone 1",
    "we've successfully controlled zone 1!"
]
first_sortie_stop_index = 2

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
            center=pygame.Vector2(xy) + SortieNode.center
        )
        pygame.draw.rect(surface, Color.RED, rect, width=Box.OUTLINE_WIDTH)

        draw_tb(surface, font, None, rect.bottomleft, False, True)
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
                width=3*96 + 2*Box.PADDING, # TODO
                height=96 + 2*Box.PADDING,
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
        elif menu_manager.encounter_menu.open_reward_cache_button.active:
            button_rect = menu_manager.encounter_menu.open_reward_cache_button.rect
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
    quest_name = "research_shipgirl"
    menu_manager.quest_manager.quests[quest_name] = research_shipgirl_quest
    if quest_name not in DataFiles.save_file["quests"]:
        DataFiles.save_file["quests"][quest_name] = "new"

first_sortie_quest = Quest(
    first_sortie_dialogue_texts,
    first_sortie_stop_index,
    first_sortie_completion_criteria,
    first_sortie_tutorial_draw,
    first_sortie_on_start,
    first_sortie_on_complete
)

research_shipgirl_dialogue_texts = [
    "let's research a new shipgirl!",
    "go to the shipyard and start research on guam",
    "collect combat data during sorties to research new shipgirls",
    "let's sortie into zone 2 to collect combat data"
]
research_shipgirl_stop_index = 2

def research_shipgirl_completion_criteria(menu_manager):
    return DataFiles.save_file["research_target"] == "guam"

def research_shipgirl_tutorial_draw(menu_manager, surface, font):
    if menu_manager.current_menu != menu_manager.port_menu:
        return
    
    if menu_manager.port_menu.current_overlay == menu_manager.port_menu.NO_OVERLAY:
        button_rect = menu_manager.port_menu.open_shipyard_overlay_button.rect
        rect = get_rect(
            width=button_rect.width + 2*Box.PADDING,
            height=button_rect.height + 2*Box.PADDING,
            center=button_rect.center
        )
        pygame.draw.rect(surface, Color.RED, rect, width=Box.OUTLINE_WIDTH)

        draw_tb(surface, font, None, rect.topright, True, False)
    elif menu_manager.port_menu.current_overlay == menu_manager.port_menu.SHIPYARD:
        if menu_manager.port_menu.overlay_selected_entity == "guam":
            button_rect = menu_manager.port_menu.overlay_confirm_button.rect
            rect = get_rect(
                width=button_rect.width + 2*Box.PADDING,
                height=button_rect.height + 2*Box.PADDING,
                center=button_rect.center
            )
            pygame.draw.rect(surface, Color.RED, rect, width=Box.OUTLINE_WIDTH)

            draw_tb(surface, font, None, rect.bottomleft, False, True)
        else:
            button_rect = menu_manager.port_menu.overlay_left_icons[1]
            rect = get_rect(
                width=button_rect.width + 2*Box.PADDING,
                height=button_rect.height + 2*Box.PADDING,
                center=button_rect.center
            )
            pygame.draw.rect(surface, Color.RED, rect, width=Box.OUTLINE_WIDTH)

            draw_tb(surface, font, None, rect.bottomright, False, False)

def research_shipgirl_on_start(menu_manager):
    menu_manager.port_menu.open_shipyard_overlay_button.active = True

def research_shipgirl_on_complete(menu_manager):
    pass

research_shipgirl_quest = Quest(
    research_shipgirl_dialogue_texts,
    research_shipgirl_stop_index,
    research_shipgirl_completion_criteria,
    research_shipgirl_tutorial_draw,
    research_shipgirl_on_start,
    research_shipgirl_on_complete
)

construct_shipgirl_dialogue_texts = [
    "we've collected enough combat data to construct guam!",
    "go to the shipyard and construct guam",
    "guam has joined our port!",
    "let's add her to our fleet and sortie into zone 3"
]
construct_shipgirl_stop_index = 2

def construct_shipgirl_completion_criteria(menu_manager):
    return menu_manager.available_shipgirls[-1].name == "guam"

def construct_shipgirl_tutorial_draw(menu_manager, surface, font):
    if menu_manager.current_menu != menu_manager.port_menu:
        return

    if menu_manager.port_menu.current_overlay == menu_manager.port_menu.NO_OVERLAY:
        button_rect = menu_manager.port_menu.open_shipyard_overlay_button.rect
        rect = get_rect(
            width=button_rect.width + 2*Box.PADDING,
            height=button_rect.height + 2*Box.PADDING,
            center=button_rect.center
        )
        pygame.draw.rect(surface, Color.RED, rect, width=Box.OUTLINE_WIDTH)

        draw_tb(surface, font, None, rect.topright, True, False)
    elif menu_manager.port_menu.current_overlay == menu_manager.port_menu.SHIPYARD:
        if menu_manager.port_menu.overlay_selected_entity == "guam":
            button_rect = menu_manager.port_menu.overlay_confirm_button.rect
            rect = get_rect(
                width=button_rect.width + 2*Box.PADDING,
                height=button_rect.height + 2*Box.PADDING,
                center=button_rect.center
            )
            pygame.draw.rect(surface, Color.RED, rect, width=Box.OUTLINE_WIDTH)

            draw_tb(surface, font, None, rect.bottomleft, False, True)
        else:
            button_rect = menu_manager.port_menu.overlay_left_icons[1]
            rect = get_rect(
                width=button_rect.width + 2*Box.PADDING,
                height=button_rect.height + 2*Box.PADDING,
                center=button_rect.center
            )
            pygame.draw.rect(surface, Color.RED, rect, width=Box.OUTLINE_WIDTH)

            draw_tb(surface, font, None, rect.bottomright, False, False)
    
def construct_shipgirl_on_start(menu_manager):
    pass

def construct_shipgirl_on_complete(menu_manager):
    pass

construct_shipgirl_quest = Quest(
    construct_shipgirl_dialogue_texts,
    construct_shipgirl_stop_index,
    construct_shipgirl_completion_criteria,
    construct_shipgirl_tutorial_draw,
    construct_shipgirl_on_start,
    construct_shipgirl_on_complete
)

craft_weapon_dialogue_texts = [
    "we've collected enough materials to craft a new gun!",
    "go to the gear lab and craft a new DD gun",
    "we've crafted a new gun!"
]
craft_weapon_stop_index = 2

def craft_weapon_completion_criteria(menu_manager):
    return DataFiles.save_file["equipment"].get("twin_120", 0) == 1

def craft_weapon_tutorial_draw(menu_manager, surface, font):
    if menu_manager.current_menu != menu_manager.port_menu:
        return

    if menu_manager.port_menu.current_overlay == menu_manager.port_menu.NO_OVERLAY:
        button_rect = menu_manager.port_menu.open_gear_lab_overlay_button.rect
        rect = get_rect(
            width=button_rect.width + 2*Box.PADDING,
            height=button_rect.height + 2*Box.PADDING,
            center=button_rect.center
        )
        pygame.draw.rect(surface, Color.RED, rect, width=Box.OUTLINE_WIDTH)

        draw_tb(surface, font, None, rect.topright, True, False)
    elif menu_manager.port_menu.current_overlay == menu_manager.port_menu.GEAR_LAB:
        if menu_manager.port_menu.overlay_selected_entity == "twin_120":
            button_rect = menu_manager.port_menu.overlay_confirm_button.rect
            rect = get_rect(
                width=button_rect.width + 2*Box.PADDING,
                height=button_rect.height + 2*Box.PADDING,
                center=button_rect.center
            )
            pygame.draw.rect(surface, Color.RED, rect, width=Box.OUTLINE_WIDTH)

            draw_tb(surface, font, None, rect.bottomleft, False, True)
        else:
            button_rect = menu_manager.port_menu.overlay_left_icons[0]
            rect = get_rect(
                width=button_rect.width + 2*Box.PADDING,
                height=button_rect.height + 2*Box.PADDING,
                center=button_rect.center
            )
            pygame.draw.rect(surface, Color.RED, rect, width=Box.OUTLINE_WIDTH)

            draw_tb(surface, font, None, rect.bottomright, False, False)

def craft_weapon_on_start(menu_manager):
    menu_manager.port_menu.open_gear_lab_overlay_button.active = True

def craft_weapon_on_complete(menu_manager):
    quest_name = "equip_weapon"
    menu_manager.quest_manager.quests[quest_name] = equip_weapon_quest
    if quest_name not in DataFiles.save_file["quests"]:
        DataFiles.save_file["quests"][quest_name] = "new"

craft_weapon_quest = Quest(
    craft_weapon_dialogue_texts,
    craft_weapon_stop_index,
    craft_weapon_completion_criteria,
    craft_weapon_tutorial_draw,
    craft_weapon_on_start,
    craft_weapon_on_complete
)

equip_weapon_dialogue_texts = [
    "since we just crafted a new weapon, we should equip it",
    "equip laffey with the new gun",
    "laffey is now stronger!",
    "let's sortie into the new zone to test it out!"
]
equip_weapon_stop_index = 2

def equip_weapon_completion_criteria(menu_manager):
    return DataFiles.save_file["shipgirls"]["laffey"]["equipment"][Equipment.WEAPON] == "twin_120"

def equip_weapon_tutorial_draw(menu_manager, surface, font):
    if menu_manager.current_menu == menu_manager.port_menu:
        rect = menu_manager.available_shipgirls[0].rect
        pygame.draw.rect(surface, Color.RED, rect, width=Box.OUTLINE_WIDTH)

        draw_tb(surface, font, None, rect.bottomright, False, False)
    elif (
        menu_manager.current_menu == menu_manager.equipment_menu
        and menu_manager.equipment_menu.selected_shipgirl.name == "laffey"
    ):
        if menu_manager.equipment_menu.selected_equipment == Equipment.WEAPON:
            button_rect = menu_manager.equipment_menu.equippable_rects[0]
            rect = get_rect(
                width=button_rect.width + 2*Box.PADDING,
                height=button_rect.height + 2*Box.PADDING,
                center=button_rect.center
            )
            pygame.draw.rect(surface, Color.RED, rect, width=Box.OUTLINE_WIDTH)

            draw_tb(surface, font, None, rect.bottomleft, False, True)
        else:
            button_rect = menu_manager.equipment_menu.equipped_rects[0]
            rect = get_rect(
                width=button_rect.width + 2*Box.PADDING,
                height=button_rect.height + 2*Box.PADDING,
                center=button_rect.center
            )
            pygame.draw.rect(surface, Color.RED, rect, width=Box.OUTLINE_WIDTH)

            draw_tb(surface, font, None, rect.bottomleft, False, True)
        
def equip_weapon_on_start(menu_manager):
    pass

def equip_weapon_on_complete(menu_manager):
    pass

equip_weapon_quest = Quest(
    equip_weapon_dialogue_texts,
    equip_weapon_stop_index,
    equip_weapon_completion_criteria,
    equip_weapon_tutorial_draw,
    equip_weapon_on_start,
    equip_weapon_on_complete
)

quests = {
    "first_sortie": first_sortie_quest,
    "research_shipgirl": research_shipgirl_quest,
    "construct_shipgirl": construct_shipgirl_quest,
    "craft_weapon": craft_weapon_quest,
    "equip_weapon": equip_weapon_quest
}