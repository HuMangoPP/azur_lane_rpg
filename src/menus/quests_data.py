import pygame

from engine.util import get_rect, hex_to_pixel
from src.constants import DataFiles, Box, Color, Equipment

from src.menus.quests import Quest
from src.menus.sortie_selection_menu import SortieNode

def draw_tb(surface, font, text, point_pos, point_down, point_right):
    point_pos = pygame.Vector2(point_pos)

    if point_down:
        pointer = DataFiles.sprites["user_interface"]["TB_point_down"]
    else:
        pointer = DataFiles.sprites["user_interface"]["TB_point_up"]
    
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
        max_text_width = font.font_width*25
        text_height = font.get_height(text, text_scale, max_text_width)
        text_box_width = font.get_width(text, text_scale, max_text_width)
        text_rect = get_rect(
            width=text_box_width + 2*Box.PADDING,
            height=text_height + 2*Box.PADDING,
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
        pygame.draw.rect(surface, Color.WHITE, text_rect)
        pygame.draw.polygon(surface, Color.WHITE, polygon)
        font.render(
            surface,
            text,
            pygame.Vector2(text_rect.topleft) + pygame.Vector2(Box.PADDING, Box.PADDING),
            Color.BLACK,
            text_scale,
            box_width=max_text_width
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
    completed = len(DataFiles.save_file["unlocked_factions"]) > 0
    if completed:
        chosen_faction = DataFiles.save_file["unlocked_factions"][0]
        for shipgirl_info in DataFiles.shipgirl_data.values():
            if shipgirl_info["faction"] != chosen_faction:
                continue
            if shipgirl_info["hull_type"] not in ["DD", "BB"]:
                continue
            choose_faction_quest.rewards[shipgirl_info["unique_item"]] = 1

    return completed

def choose_faction_tutorial_draw(menu_manager, surface, font):
    pass

def choose_faction_on_start(menu_manager):
    for choose_faction_button in menu_manager.port_menu.choose_faction_buttons:
        choose_faction_button.active = True

def choose_faction_on_complete(menu_manager):
    quest_name = construct_shipgirls_quest.quest_id
    menu_manager.quest_manager.quests[quest_name] = construct_shipgirls_quest
    if quest_name not in DataFiles.save_file["quests"]:
        DataFiles.save_file["quests"][quest_name] = "new"
    
    for choose_faction_button in menu_manager.port_menu.choose_faction_buttons:
        choose_faction_button.active = False

    shipgirls = {}
    chosen_faction = DataFiles.save_file["unlocked_factions"][0]
    for shipgirl, shipgirl_info in DataFiles.shipgirl_data.items():
        if shipgirl_info["faction"] != chosen_faction:
            continue
        shipgirls[shipgirl_info["hull_type"]] = shipgirl

    construct_shipgirls_quest.completion_criteria = construct_shipgirls_completion_criteria_factory([shipgirls["DD"], shipgirls["BB"]])
    construct_shipgirls_quest.tutorial_draw = construct_shipgirls_tutorial_draw_factory([shipgirls["DD"], shipgirls["BB"]])

    first_sortie_quest.tutorial_draw = first_sortie_tutorial_draw_factory([shipgirls["DD"], shipgirls["BB"]])

    equip_weapon_quest.completion_criteria = equip_weapon_completion_criteria_factory(shipgirls["DD"])
    equip_weapon_quest.tutorial_draw = equip_weapon_tutorial_draw_factory(shipgirls["DD"])

    construct_shipgirls_quest.quest_line = construct_shipgirls_quest.quest_line.replace(
        "DD_shipgirl",
        shipgirls["DD"]
    ).replace("BB_shipgirl", shipgirls["BB"])
    construct_shipgirls_quest.post_quest_dialogue = [
        dialogue.replace("DD_shipgirl", shipgirls["DD"]).replace("BB_shipgirl", shipgirls["BB"])
        for dialogue in construct_shipgirls_quest.post_quest_dialogue
    ]

    research_shipgirl_quest.quest_line = research_shipgirl_quest.quest_line.replace(
        "CA_shipgirl",
        shipgirls["CA"]
    )
    research_shipgirl_quest.completion_criteria = research_shipgirl_completion_criteria_factory(shipgirls["CA"])
    research_shipgirl_quest.tutorial_draw = construct_shipgirls_tutorial_draw_factory([shipgirls["CA"]])

    construct_shipgirl_quest.pre_quest_dialogue = [
        dialogue.replace("CA_shipgirl", shipgirls["CA"])
        for dialogue in construct_shipgirl_quest.pre_quest_dialogue
    ]
    construct_shipgirl_quest.quest_line = construct_shipgirl_quest.quest_line.replace(
        "CA_shipgirl",
        shipgirls["CA"]
    )
    construct_shipgirl_quest.post_quest_dialogue = [
        dialogue.replace("CA_shipgirl", shipgirls["CA"])
        for dialogue in construct_shipgirl_quest.post_quest_dialogue
    ]
    construct_shipgirl_quest.completion_criteria = construct_shipgirls_completion_criteria_factory([shipgirls["CA"]])
    construct_shipgirl_quest.tutorial_draw = construct_shipgirls_tutorial_draw_factory([shipgirls["CA"]])

    equip_weapon_quest.quest_line = equip_weapon_quest.quest_line.replace(
        "DD_shipgirl",
        shipgirls["DD"]
    ).replace("BB_shipgirl", shipgirls["BB"])
    equip_weapon_quest.post_quest_dialogue = [
        dialogue.replace("DD_shipgirl", shipgirls["DD"]).replace("BB_shipgirl", shipgirls["BB"])
        for dialogue in equip_weapon_quest.post_quest_dialogue
    ]

choose_faction_rewards = {
    "DD_blueprint": 1,
    "BB_blueprint": 1,
    "wisdom_cube": 2,
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
construct_shipgirls_quest_line = "Construct DD_shipgirl and BB_shipgirl."
construct_shipgirls_post_quest_dialogue = [
    "DD_shipgirl and BB_shipgirl have joined our fleet!"
]

def construct_shipgirls_completion_criteria_factory(shipgirls):
    def construct_shipgirls_completion_criteria(menu_manager):
        return all(
            shipgirl in DataFiles.save_file["shipgirls"]
            for shipgirl in shipgirls
        )
    return construct_shipgirls_completion_criteria

def construct_shipgirls_tutorial_draw_factory(shipgirls):
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
                if shipgirl not in shipgirls:
                    continue

                rect = menu_manager.port_menu.dossier_icons[i]
                pygame.draw.rect(surface, Color.RED, rect, width=Box.OUTLINE_WIDTH)
                draw_tb(surface, font, None, rect.bottomleft, False, True)
            
            if menu_manager.port_menu.overlay_selected_entity in shipgirls:
                button_rect = menu_manager.port_menu.overlay_confirm_button.rect
                rect = get_rect(
                    width=button_rect.width + 2*Box.PADDING,
                    height=button_rect.height + 2*Box.PADDING,
                    center=button_rect.center
                )
                pygame.draw.rect(surface, Color.RED, rect, width=Box.OUTLINE_WIDTH)
                draw_tb(surface, font, None, rect.bottomright, False, False)

    return construct_shipgirls_tutorial_draw

def construct_shipgirls_on_start(menu_manager):
    menu_manager.port_menu.open_shipyard_overlay_button.active = True

def construct_shipgirls_on_complete(menu_manager):
    quest_name = first_sortie_quest.quest_id
    menu_manager.quest_manager.quests[quest_name] = first_sortie_quest
    if quest_name not in DataFiles.save_file["quests"]:
        DataFiles.save_file["quests"][quest_name] = "new"

construct_shipgirls_quest = Quest(
    "construct_shipgirls",
    construct_shipgirls_pre_quest_dialogue,
    construct_shipgirls_quest_line,
    construct_shipgirls_post_quest_dialogue,
    None,
    None,
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

def first_sortie_tutorial_draw_factory(shipgirls):
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
                    f"drag {shipgirls[0]} and {shipgirls[1]} to your fleet",
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

    return first_sortie_tutorial_draw

def first_sortie_on_start(menu_manager):
    menu_manager.port_menu.open_select_sortie_menu_button.active = True

def first_sortie_on_complete(menu_manager):
    quest_name = inventory_quest.quest_id
    menu_manager.quest_manager.quests[quest_name] = inventory_quest
    if quest_name not in DataFiles.save_file["quests"]:
        DataFiles.save_file["quests"][quest_name] = "new"

first_sortie_quest = Quest(
    "first_sortie",
    first_sortie_pre_quest_dialogue,
    first_sortie_quest_line,
    first_sortie_post_quest_dialogue,
    first_sortie_completion_criteria,
    None,
    first_sortie_on_start,
    first_sortie_on_complete
)

inventory_pre_quest_dialogue = [
    "We found some rewards in a hidden siren cache from our sortie.",
    "Let me show you were our items are stored."
]
inventory_quest_line = "Visit the depot."
inventory_post_quest_dialogue = [
    "Now you know how to access the depot!"
]

def inventory_completion_criteria(menu_manager):
    return menu_manager.port_menu.visited_inventory

def inventory_tutorial_draw(menu_manager, surface, font):
    if menu_manager.current_menu != menu_manager.port_menu:
        return

    if menu_manager.port_menu.current_overlay == menu_manager.port_menu.NO_OVERLAY:
        button_rect = menu_manager.port_menu.open_depot_overlay_button.rect
        rect = get_rect(
            width=button_rect.width + 2*Box.PADDING,
            height=button_rect.height + 2*Box.PADDING,
            center=button_rect.center
        )
        pygame.draw.rect(surface, Color.RED, rect, width=Box.OUTLINE_WIDTH)

        draw_tb(surface, font, None, rect.topright, True, False)
    elif menu_manager.port_menu.current_overlay == menu_manager.port_menu.DEPOT:
        rect = menu_manager.port_menu.depot_overlay
        draw_tb(
            surface, font,
            "You can see all of your items here!",
            (rect.left, rect.centery),
            False, True
        )

def inventory_on_start(menu_manager):
    menu_manager.port_menu.open_depot_overlay_button.active = True

def inventory_on_complete(menu_manager):
    quest_name = intel_center_quest.quest_id
    menu_manager.quest_manager.quests[quest_name] = intel_center_quest
    if quest_name not in DataFiles.save_file["quests"]:
        DataFiles.save_file["quests"][quest_name] = "new"

inventory_quest = Quest(
    "inventory",
    inventory_pre_quest_dialogue,
    inventory_quest_line,
    inventory_post_quest_dialogue,
    inventory_completion_criteria,
    inventory_tutorial_draw,
    inventory_on_start,
    inventory_on_complete
)

intel_center_pre_quest_dialogue = [
    "During our sortie, we encounter some enemy sirens.",
    "By successfully completing sorties, we can collect data about the enemies.",
    "Let me show you were you can read more about our enemies."
]
intel_center_quest_line = "Visit the intel center."
intel_center_post_quest_dialogue = [
    "Now you know how to access the intel center!",
    "This information can help you get an advantage when fighting sirens."
]

def intel_center_completion_criteria(menu_manager):
    return menu_manager.port_menu.visited_intel_center

def intel_center_tutorial_draw(menu_manager, surface, font):
    if menu_manager.current_menu != menu_manager.port_menu:
        return

    if menu_manager.port_menu.current_overlay == menu_manager.port_menu.NO_OVERLAY:
        button_rect = menu_manager.port_menu.open_intel_center_overlay_button.rect
        rect = get_rect(
            width=button_rect.width + 2*Box.PADDING,
            height=button_rect.height + 2*Box.PADDING,
            center=button_rect.center
        )
        pygame.draw.rect(surface, Color.RED, rect, width=Box.OUTLINE_WIDTH)

        draw_tb(surface, font, None, rect.topright, True, False)
    elif menu_manager.port_menu.current_overlay == menu_manager.port_menu.INTEL_CENTER:
        if menu_manager.port_menu.overlay_selected_entity is None:
            siren_rect = menu_manager.port_menu.dossier_icons[0]
            rect = get_rect(
                width=siren_rect.width + 2*Box.PADDING,
                height=siren_rect.height + 2*Box.PADDING,
                center=siren_rect.center
            )
            pygame.draw.rect(surface, Color.RED, rect, width=Box.OUTLINE_WIDTH)
            draw_tb(surface, font, None, rect.bottomright, False, False)
        else:
            rect = menu_manager.port_menu.blueprint_page
            draw_tb(
                surface, font,
                "The intel center has information on siren stats as well as the potential drops from defeating the siren.",
                (rect.right, rect.centery),
                False, False
            )

def intel_center_on_start(menu_manager):
    menu_manager.port_menu.open_intel_center_overlay_button.active = True

def intel_center_on_complete(menu_manager):
    quest_name = research_shipgirl_quest.quest_id
    menu_manager.quest_manager.quests[quest_name] = research_shipgirl_quest
    if quest_name not in DataFiles.save_file["quests"]:
        DataFiles.save_file["quests"][quest_name] = "new"

intel_center_quest = Quest(
    "intel_center",
    intel_center_pre_quest_dialogue,
    intel_center_quest_line,
    intel_center_post_quest_dialogue,
    intel_center_completion_criteria,
    intel_center_tutorial_draw,
    intel_center_on_start,
    intel_center_on_complete
)

research_shipgirl_pre_quest_dialogue = [
    "We can research a new shipgirl."
]
research_shipgirl_quest_line = "Go to the research and start researching CA_shipgirl."
research_shipgirl_post_quest_dialogue = [
    "Let's sortie into zone 2 to collect combat data.",
    "Collecting combat data contributes towards obtaining the shipgirl's unique item."
]

def research_shipgirl_completion_criteria_factory(shipgirl):
    def research_shipgirl_completion_criteria(menu_manager):
        return DataFiles.save_file["research_target"] == shipgirl
    return research_shipgirl_completion_criteria

def research_shipgirl_on_start(menu_manager):
    menu_manager.port_menu.open_shipyard_overlay_button.active = True

def research_shipgirl_on_complete(menu_manager):
    pass

research_shipgirl_quest = Quest(
    "research_shipgirl",
    research_shipgirl_pre_quest_dialogue,
    research_shipgirl_quest_line,
    research_shipgirl_post_quest_dialogue,
    None,
    None,
    research_shipgirl_on_start,
    research_shipgirl_on_complete
)

construct_shipgirl_pre_quest_dialogue = [
    "We've collected enough combat data and obtained CA_shipgirl's unique item!"
]
construct_shipgirl_quest_line = "Go to the shipyard and construct CA_shipgirl."
construct_shipgirl_post_quest_dialogue = [
    "CA_shipgirl has joined our port!",
    "Let's add her to our fleet and sortie into zone 3."
]

def construct_shipgirl_on_start(menu_manager):
    pass

def construct_shipgirl_on_complete(menu_manager):
    pass

construct_shipgirl_quest = Quest(
    "construct_shipgirl",
    construct_shipgirl_pre_quest_dialogue,
    construct_shipgirl_quest_line,
    construct_shipgirl_post_quest_dialogue,
    None,
    None,
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
            button_rect = menu_manager.port_menu.dossier_icons[0]
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
    quest_name = equip_weapon_quest.quest_id
    menu_manager.quest_manager.quests[quest_name] = equip_weapon_quest
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
equip_weapon_quest_line = "Equip the new gun onto DD_shipgirl."
equip_weapon_post_quest_dialogue = [
    "Now DD_shipgirl is stronger!",
    "Let's sortie into the new zone!"
]

def equip_weapon_completion_criteria_factory(shipgirl):
    def equip_weapon_completion_criteria(menu_manager):
        return DataFiles.save_file["shipgirls"][shipgirl]["equipment"][Equipment.WEAPON] == "twin_120"
    
    return equip_weapon_completion_criteria

def equip_weapon_tutorial_draw_factory(shipgirl):
    def equip_weapon_tutorial_draw(menu_manager, surface, font):
        if menu_manager.current_menu == menu_manager.port_menu:
            rect = menu_manager.available_shipgirls[0].rect
            pygame.draw.rect(surface, Color.RED, rect, width=Box.OUTLINE_WIDTH)

            draw_tb(surface, font, None, rect.bottomright, False, False)
        elif (
            menu_manager.current_menu == menu_manager.equipment_menu
            and menu_manager.equipment_menu.selected_shipgirl.name == shipgirl
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
    return equip_weapon_tutorial_draw
        
def equip_weapon_on_start(menu_manager):
    pass

def equip_weapon_on_complete(menu_manager):
    pass

equip_weapon_quest = Quest(
    "equip_weapon",
    equip_weapon_pre_quest_dialogue,
    equip_weapon_quest_line,
    equip_weapon_post_quest_dialogue,
    None,
    None,
    equip_weapon_on_start,
    equip_weapon_on_complete
)

quests = [
    choose_faction_quest,
    construct_shipgirls_quest,
    first_sortie_quest,
    inventory_quest,
    intel_center_quest,
    research_shipgirl_quest,
    construct_shipgirl_quest,
    craft_weapon_quest,
    equip_weapon_quest
]