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
        text_width = 8*Box.WIDTH - Box.PADDING
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

choose_faction_pre_quest_dialogue = [
    "Hello commander, welcome to the Azur Lane port.",
    "I am your virtual assistant. You may call me TB.",
    "First things first, we will need to choose our faction.",
]
choose_faction_quest_line = "Choose a faction."
choose_faction_post_quest_dialogue = [
    "You've successfully chosen a faction!"
]

def choose_faction_completion_criteria(menu_manager):
    return len(DataFiles.save_file["unlocked_factions"]) > 0

def choose_faction_tutorial_draw(menu_manager, surface, font):
    pass

def choose_faction_on_start(menu_manager):
    for choose_faction_button in menu_manager.port_menu.choose_faction_buttons:
        choose_faction_button.active = True

def choose_faction_on_complete(menu_manager):
    quest_name = "construct_shipgirls"
    menu_manager.quest_manager.quests[quest_name] = quests[quest_name]
    if quest_name not in DataFiles.save_file["quests"]:
        DataFiles.save_file["quests"][quest_name] = "new"
    
    for choose_faction_button in menu_manager.port_menu.choose_faction_buttons:
        choose_faction_button.active = False

choose_faction_rewards = {
    "DD_blueprint": 1,
    "BB_blueprint": 1,
    "wisdom_cube": 2,
    "huggy_pillow": 1,
    "dragon_cannon": 1,
}

choose_faction_quest = Quest(
    "choose_faction",
    choose_faction_pre_quest_dialogue,
    choose_faction_quest_line,
    choose_faction_post_quest_dialogue,
    choose_faction_completion_criteria,
    choose_faction_tutorial_draw,
    choose_faction_on_start,
    choose_faction_on_complete,
    rewards=choose_faction_rewards
)

construct_shipgirls_pre_quest_dialogue = [
    "We should construct some shipgirls to join our fleet."
]
construct_shipgirls_quest_line = "Construct Laffey and New Jersey.",
construct_shipgirls_post_quest_dialogue = [
    "Laffey and New Jersey have joined our fleet!"
]

def construct_shipgirls_completion_criteria(menu_manager):
    return (
        "laffey" in DataFiles.save_file["shipgirls"]
        and "new_jersey" in DataFiles.save_file["shipgirls"]
    )

def construct_shipgirls_tutorial_draw(menu_manager, surface, font):
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
        if menu_manager.port_menu.selected_overlay_filter is None:
            shipgirl_data = {
                shipgirl: shipgirl_info for shipgirl, shipgirl_info in DataFiles.shipgirl_data.items()
                if shipgirl not in DataFiles.save_file["shipgirls"]
                and shipgirl_info["faction"] in DataFiles.save_file["unlocked_factions"]
            }
        else:
            shipgirl_data = {
                shipgirl: shipgirl_info for shipgirl, shipgirl_info in DataFiles.shipgirl_data.items()
                if shipgirl not in DataFiles.save_file["shipgirls"]
                and shipgirl_info["faction"] in DataFiles.save_file["unlocked_factions"]
                and shipgirl_info["faction"] == menu_manager.port_menu.shipgirl_filters[menu_manager.port_menu.selected_overlay_filter]
            }

        for i, (shipgirl, shipgirl_info) in enumerate(shipgirl_data.items()):
            if shipgirl in DataFiles.save_file["shipgirls"]:
                continue
            if shipgirl_info["faction"] not in DataFiles.save_file["unlocked_factions"]:
                continue
            if shipgirl_info["hull_type"] not in ["DD", "BB"]:
                continue

            rect = menu_manager.port_menu.overlay_left_icons[i]
            pygame.draw.rect(surface, Color.RED, rect, width=Box.OUTLINE_WIDTH)
            draw_tb(surface, font, None, rect.bottomleft, False, True)
        
        if menu_manager.port_menu.overlay_selected_entity in ["laffey", "new_jersey"]:
            button_rect = menu_manager.port_menu.overlay_confirm_button.rect
            rect = get_rect(
                width=button_rect.width + 2*Box.PADDING,
                height=button_rect.height + 2*Box.PADDING,
                center=button_rect.center
            )
            pygame.draw.rect(surface, Color.RED, rect, width=Box.OUTLINE_WIDTH)
            draw_tb(surface, font, None, rect.bottomright, False, False)

def construct_shipgirls_on_start(menu_manager):
    menu_manager.port_menu.open_shipyard_overlay_button.active = True

def construct_shipgirls_on_complete(menu_manager):
    quest_name = "first_sortie"
    menu_manager.quest_manager.quests[quest_name] = quests[quest_name]
    if quest_name not in DataFiles.save_file["quests"]:
        DataFiles.save_file["quests"][quest_name] = "new"

construct_shipgirls_quest = Quest(
    "construct_shipgirls",
    construct_shipgirls_pre_quest_dialogue,
    construct_shipgirls_quest_line,
    construct_shipgirls_post_quest_dialogue,
    construct_shipgirls_completion_criteria,
    construct_shipgirls_tutorial_draw,
    construct_shipgirls_on_start,
    construct_shipgirls_on_complete
)

first_sortie_pre_quest_dialogue = [
    "Now it's time to go on a sortie."
]
first_sortie_quest_line = "Sortie into zone 1."
first_sortie_post_quest_dialogue = [
    "We've successfully controlled zone 1!"
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
    menu_manager.quest_manager.quests[quest_name] = quests[quest_name]
    if quest_name not in DataFiles.save_file["quests"]:
        DataFiles.save_file["quests"][quest_name] = "new"

first_sortie_quest = Quest(
    "first_sortie",
    first_sortie_pre_quest_dialogue,
    first_sortie_quest_line,
    first_sortie_post_quest_dialogue,
    first_sortie_completion_criteria,
    first_sortie_tutorial_draw,
    first_sortie_on_start,
    first_sortie_on_complete
)

research_shipgirl_pre_quest_dialogue = [
    "We can research a new shipgirl."
]
research_shipgirl_quest_line = "Go to the research and start researching Guam."
research_shipgirl_post_quest_dialogue = [
    "Let's sortie into zone 2 to collect combat data.",
    "Collecting combat data contributes towards obtaining the shipgirl's unique item."
]

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
            if menu_manager.port_menu.selected_overlay_filter is None:
                shipgirl_data = {
                    shipgirl: shipgirl_info for shipgirl, shipgirl_info in DataFiles.shipgirl_data.items()
                    if shipgirl not in DataFiles.save_file["shipgirls"]
                    and shipgirl_info["faction"] in DataFiles.save_file["unlocked_factions"]
                }
            else:
                shipgirl_data = {
                    shipgirl: shipgirl_info for shipgirl, shipgirl_info in DataFiles.shipgirl_data.items()
                    if shipgirl not in DataFiles.save_file["shipgirls"]
                    and shipgirl_info["faction"] in DataFiles.save_file["unlocked_factions"]
                    and shipgirl_info["faction"] == menu_manager.port_menu.shipgirl_filters[menu_manager.port_menu.selected_overlay_filter]
                }

            for i, (shipgirl, shipgirl_info) in enumerate(shipgirl_data.items()):
                if shipgirl in DataFiles.save_file["shipgirls"]:
                    continue
                if shipgirl_info["faction"] not in DataFiles.save_file["unlocked_factions"]:
                    continue
                if shipgirl_info["hull_type"] not in ["CA"]:
                    continue

                rect = menu_manager.port_menu.overlay_left_icons[i]
                pygame.draw.rect(surface, Color.RED, rect, width=Box.OUTLINE_WIDTH)
                draw_tb(surface, font, None, rect.bottomleft, False, True)

def research_shipgirl_on_start(menu_manager):
    menu_manager.port_menu.open_shipyard_overlay_button.active = True

def research_shipgirl_on_complete(menu_manager):
    pass

research_shipgirl_quest = Quest(
    "research_shipgirl",
    research_shipgirl_pre_quest_dialogue,
    research_shipgirl_quest_line,
    research_shipgirl_post_quest_dialogue,
    research_shipgirl_completion_criteria,
    research_shipgirl_tutorial_draw,
    research_shipgirl_on_start,
    research_shipgirl_on_complete
)

construct_shipgirl_pre_quest_dialogue = [
    "We've collected enough combat data and obtained Guam's unique item!"
]
construct_shipgirl_quest_line = "Go to the shipyard and construct Guam."
construct_shipgirl_post_quest_dialogue = [
    "Guam has joined our port!",
    "Let's add her to our fleet and sortie into zone 3."
]

def construct_shipgirl_completion_criteria(menu_manager):
    return "guam" in DataFiles.save_file["shipgirls"]

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
    "construct_shipgirl",
    construct_shipgirl_pre_quest_dialogue,
    construct_shipgirl_quest_line,
    construct_shipgirl_post_quest_dialogue,
    construct_shipgirl_completion_criteria,
    construct_shipgirl_tutorial_draw,
    construct_shipgirl_on_start,
    construct_shipgirl_on_complete
)

craft_weapon_pre_quest_dialogue = [
    "We've collected enough materials to craft a new gun!"
]
craft_weapon_quest_line = "Go to the gear lab and craft a new DD gun."
craft_weapon_post_quest_dialogue = [
    "We've crafted a new gun!"
]

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
    menu_manager.quest_manager.quests[quest_name] = quests[quest_name]
    if quest_name not in DataFiles.save_file["quests"]:
        DataFiles.save_file["quests"][quest_name] = "new"

craft_weapon_quest = Quest(
    "craft_weapon",
    craft_weapon_pre_quest_dialogue,
    craft_weapon_quest_line,
    craft_weapon_post_quest_dialogue,
    craft_weapon_completion_criteria,
    craft_weapon_tutorial_draw,
    craft_weapon_on_start,
    craft_weapon_on_complete
)

equip_weapon_pre_quest_dialogue = [
    "Since we just crafted a new gun, we should equip it."
]
equip_weapon_quest_line = "Equip the new gun onto Laffey."
equip_weapon_post_quest_dialogue = [
    "Now Laffey is stronger!",
    "Let's sortie into the new zone!"
]

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
    "equip_weapon",
    equip_weapon_pre_quest_dialogue,
    equip_weapon_quest_line,
    equip_weapon_post_quest_dialogue,
    equip_weapon_completion_criteria,
    equip_weapon_tutorial_draw,
    equip_weapon_on_start,
    equip_weapon_on_complete
)

quests = {
    choose_faction_quest.quest_id: choose_faction_quest,
    construct_shipgirls_quest.quest_id: construct_shipgirls_quest,
    first_sortie_quest.quest_id: first_sortie_quest,
    research_shipgirl_quest.quest_id: research_shipgirl_quest,
    construct_shipgirl_quest.quest_id: construct_shipgirl_quest,
    craft_weapon_quest.quest_id: craft_weapon_quest,
    equip_weapon_quest.quest_id: equip_weapon_quest
}