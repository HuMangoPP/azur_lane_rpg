import pygame

from engine.util import get_rect, hex_to_pixel
from src.constants import DataFiles, Box, Color, Equipment, Decorations

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
        pygame.draw.rect(surface, Color.DIALOGUE_BOX, text_rect)
        pygame.draw.polygon(surface, Color.DIALOGUE_BOX, polygon)
        font.render(
            surface,
            text,
            pygame.Vector2(text_rect.topleft) + pygame.Vector2(Box.PADDING, Box.PADDING),
            Color.WHITE,
            text_scale,
            box_width=max_text_width
        )

choose_faction_pre_quest_dialogue = [
    "Hello, Commander. My name is TB. I am your virtual assistant.",
    "Before we begin, you will need to choose a faction.",
    "Your chosen faction will determine which shipgirls can join your fleet.",
    "Take your time and choose the faction you like best."
]
choose_faction_quest_line = "Choose a faction."
choose_faction_post_quest_dialogue = [
    "Faction registration successful. An excellent choice.",
    "Welcome to the Azur Lane port, Commander.",
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

        choose_faction_quest.rewards.pop("placeholder_DD")
        choose_faction_quest.rewards.pop("placeholder_BB")

    return completed

def choose_faction_tutorial_draw(menu_manager, surface, font):
    pass

def choose_faction_on_start(menu_manager):
    for choose_faction_button in menu_manager.port_menu.choose_faction_buttons:
        choose_faction_button.active = True

def choose_faction_on_complete(menu_manager, save_file_load=False):
    if not save_file_load:
        faction_shipgirls = DataFiles.get_faction_shipgirls()
        specialized_wisdom_cubes = DataFiles.save_file["specialized_wisdom_cubes"]
        for hull_type in ["DD", "BB"]:
            shipgirl = faction_shipgirls[hull_type]
            if DataFiles.save_file["inventory"].get("wisdom_cube", 0) > 0:
                DataFiles.save_file["inventory"]["wisdom_cube"] -= 1
                specialized_wisdom_cubes[shipgirl] = 0

    quest_name = construct_shipgirls_quest.quest_id
    menu_manager.quest_manager.quests[quest_name] = construct_shipgirls_quest
    if quest_name not in DataFiles.save_file["quests"]:
        DataFiles.save_file["quests"][quest_name] = "new"
    
    for choose_faction_button in menu_manager.port_menu.choose_faction_buttons:
        choose_faction_button.active = False

choose_faction_rewards = {
    "DD_blueprint": 1,
    "BB_blueprint": 1,
    "wisdom_cube": 2,
    "placeholder_DD": 1,
    "placeholder_BB": 1
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
    choose_faction_rewards
)

construct_shipgirls_pre_quest_dialogue = [
    "Your port is currently empty. You should starting building your fleet.",
    "High command has prepared enough materials for you to construct {DD_shipgirl} and {BB_shipgirl}.",
    "Navigate to the shipyard and construct both shipgirls."
]
construct_shipgirls_quest_line = "Construct {DD_shipgirl} and {BB_shipgirl} in the shipyard."
construct_shipgirls_post_quest_dialogue = [
    "Construction complete.",
    "{DD_shipgirl} and {BB_shipgirl} have joined your port.",
    "Your fleet is still small, but this is only the beginning."
]

def construct_shipgirls_completion_criteria(menu_manager):
    shipgirls = DataFiles.get_faction_shipgirls()
    return all(
        shipgirl in DataFiles.save_file["shipgirls"]
        for shipgirl in [shipgirls["DD"], shipgirls["BB"]]
    )

def shipyard_tutorial_draw_factory(highlighted_hull_types):
    def shipyard_tutorial_draw(menu_manager, surface, font):
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
            if menu_manager.port_menu.overlay_selected_filter is None:
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
                    and shipgirl_info["faction"] == menu_manager.port_menu.shipyard_filters[menu_manager.port_menu.overlay_selected_filter]
                }

            for i, (shipgirl, shipgirl_info) in enumerate(shipgirl_data.items()):
                if shipgirl in DataFiles.save_file["shipgirls"]:
                    continue
                if shipgirl_info["faction"] not in DataFiles.save_file["unlocked_factions"]:
                    continue
                faction_shipgirls = DataFiles.get_faction_shipgirls()
                shipgirls = [faction_shipgirls[hull_type] for hull_type in highlighted_hull_types]
                if shipgirl not in shipgirls:
                    continue

                rect = menu_manager.port_menu.dossier_icons[i]
                pygame.draw.rect(surface, Color.RED, rect, width=Box.OUTLINE_WIDTH)
                draw_tb(surface, font, None, rect.bottomleft, False, True)
            
            if menu_manager.port_menu.overlay_selected_entity in shipgirls:
                button_rect = menu_manager.port_menu.shipyard_sticky_note_button.rect
                rect = get_rect(
                    width=button_rect.width + 2*Box.PADDING,
                    height=button_rect.height + 2*Box.PADDING,
                    center=button_rect.center
                )
                pygame.draw.rect(surface, Color.RED, rect, width=Box.OUTLINE_WIDTH)
                draw_tb(surface, font, None, rect.bottomright, False, False)

    return shipyard_tutorial_draw

def construct_shipgirls_on_start(menu_manager):
    menu_manager.port_menu.open_shipyard_overlay_button.active = True

def construct_shipgirls_on_complete(menu_manager, save_file_load=False):
    quest_name = first_sortie_quest.quest_id
    menu_manager.quest_manager.quests[quest_name] = first_sortie_quest
    if quest_name not in DataFiles.save_file["quests"]:
        DataFiles.save_file["quests"][quest_name] = "new"

decoration_voucher_reward = {
    "decoration_coin": 1
}

construct_shipgirls_quest = Quest(
    "construct_shipgirls",
    construct_shipgirls_pre_quest_dialogue,
    construct_shipgirls_quest_line,
    construct_shipgirls_post_quest_dialogue,
    construct_shipgirls_completion_criteria,
    shipyard_tutorial_draw_factory(["DD", "BB"]),
    construct_shipgirls_on_start,
    construct_shipgirls_on_complete,
    decoration_voucher_reward
)

first_sortie_pre_quest_dialogue = [
    "Your fleet is ready for deployment. It's time to go on your first sortie.",
    "Sorties are combat operations where your fleet engages enemy sirens to secures zones and extract resources.",
    "Let us set sail.",
]
first_sortie_quest_line = "Sortie into zone 1."
first_sortie_post_quest_dialogue = [
    "Sortie complete.",
    "Your fleet performed well in combat thanks to your leadership.",
    "This is the first step towards protecting our seas from the siren invaders.",
    "More missions are becoming available. Continue preparing your fleet for future battles."
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

            shipgirls = DataFiles.get_faction_shipgirls()
            dd_shipgirl = shipgirls["DD"]
            bb_shipgirl = shipgirls["BB"]
            draw_tb(
                surface, font,
                f"drag {dd_shipgirl} and {bb_shipgirl} to your fleet",
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

def first_sortie_on_complete(menu_manager, save_file_load=False):
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
    first_sortie_tutorial_draw,
    first_sortie_on_start,
    first_sortie_on_complete,
    decoration_voucher_reward
)

inventory_pre_quest_dialogue = [
    "The resource you extracted from the sortie have been delivered to your depot.",
    "The depot stores all items you've collected from battles and missions.",
    "Let's go to the depot to review your inventory."
]
inventory_quest_line = "Visit the depot."
inventory_post_quest_dialogue = [
    "Depot access confirmed.",
    "Keeping track of your supplies is important for managing the port.",
    "As your fleet grows, the depot will continue to fill with new materials."
]

def inventory_completion_criteria(menu_manager):
    return menu_manager.port_menu.visited_depot

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
        rect = menu_manager.port_menu.warehouse_overlay
        draw_tb(
            surface, font,
            "You can see all of your items here!",
            (rect.left, rect.centery),
            False, True
        )

def inventory_on_start(menu_manager):
    menu_manager.port_menu.open_depot_overlay_button.active = True

def inventory_on_complete(menu_manager, save_file_load=False):
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
    inventory_on_complete,
    decoration_voucher_reward
)

intel_center_pre_quest_dialogue = [
    "All combat data from your sorties is recorded. You can review this information in the intel center.",
    "The intel center stores data on sirens your fleet has encountered.",
    "Different enemies have different strengths and weaknesses.",
    "Studying enemy data will help you strategize for future battles.",
    "Go to the intel center and review the available records."
]
intel_center_quest_line = "Visit the intel center."
intel_center_post_quest_dialogue = [
    "Intel center access confirmed.",
    "Enemy data will continue to update as your fleet encounters new threats.",
    "Use this information carefully, Commander. Good preparation can decide the outcome of battle."
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

def intel_center_on_complete(menu_manager, save_file_load=False):
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
    intel_center_on_complete,
    decoration_voucher_reward
)

research_shipgirl_pre_quest_dialogue = [
    "Growing your fleet will be important as you sortie into more dangerous territory",
    "Each shipgirl has a unique item that is required for construction.",
    "You can obtain these items by starting a research project and collecting combat exp during sorties.",
    "Once enough exp has been collected, the shipgirl's unique item can be synthesized.",
    "Provided that you have the required additional materials, the shipgirl can be constructed in the shipyard.",
    "Let us begin researching {CA_shipgirl}.",
    "Go to the shipyard and start the research project."
]
research_shipgirl_quest_line = "Begin researching {CA_shipgirl} in the shipyard."
research_shipgirl_post_quest_dialogue = [
    "Research project started.",
    "Your fleet can now collect combat exp for {CA_shipgirl} during sorties.",
    "Let us set sail and explore the new unlocked zone."
]

def research_shipgirl_completion_criteria(menu_manager):
    shipgirl = DataFiles.get_faction_shipgirls()["CA"]
    return DataFiles.save_file["research_target"] == shipgirl

def research_shipgirl_on_start(menu_manager):
    menu_manager.port_menu.open_shipyard_overlay_button.active = True

def research_shipgirl_on_complete(menu_manager, save_file_load=False):
    pass

research_shipgirl_quest = Quest(
    "research_shipgirl",
    research_shipgirl_pre_quest_dialogue,
    research_shipgirl_quest_line,
    research_shipgirl_post_quest_dialogue,
    research_shipgirl_completion_criteria,
    shipyard_tutorial_draw_factory(["CA"]),
    research_shipgirl_on_start,
    research_shipgirl_on_complete,
    decoration_voucher_reward
)

construct_shipgirl_pre_quest_dialogue = [
    "The research project is complete, Commander.",
    "{CA_shipgirl}'s unique item has been successfully synthesized.",
    "We are ready for another member to join your port.",
    "Go to the shipyard and construct {CA_shipgirl}."
]
construct_shipgirl_quest_line = "Construct {CA_shipgirl} in the shipyard."
construct_shipgirl_post_quest_dialogue = [
    "Construction complete.",
    "{CA_shipgirl} has joined your fleet, Commander.",
    "Continue expanding your fleet and preparing for stronger enemies ahead."
]

def construct_shipgirl_completion_criteria(menu_manager):
    return DataFiles.get_faction_shipgirls()["CA"] in DataFiles.save_file["shipgirls"]

def construct_shipgirl_on_start(menu_manager):
    pass

def construct_shipgirl_on_complete(menu_manager, save_file_load=False):
    pass

construct_shipgirl_quest = Quest(
    "construct_shipgirl",
    construct_shipgirl_pre_quest_dialogue,
    construct_shipgirl_quest_line,
    construct_shipgirl_post_quest_dialogue,
    construct_shipgirl_completion_criteria,
    shipyard_tutorial_draw_factory(["CA"]),
    construct_shipgirl_on_start,
    construct_shipgirl_on_complete,
    decoration_voucher_reward
)

craft_weapon_pre_quest_dialogue = [
    "Zone 3 has been cleared.",
    "We managed to extract materials for crafting new equipment.",
    "The gear lab has been unlocked. Let us craft a new gun for {DD_shipgirl}.",
    "Open the gear lab and begin crafting."
]
craft_weapon_quest_line = "Craft the twin 120mm gun in the gear lab."
craft_weapon_post_quest_dialogue = [
    "Crafting complete.",
    "The weapon is ready to be equipped.",
    "Crafting new equipment is an important part of strengthening your fleet.",
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
            button_rect = menu_manager.port_menu.gear_lab_sticky_note_button.rect
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

def craft_weapon_on_complete(menu_manager, save_file_load=False):
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
    craft_weapon_on_complete,
    decoration_voucher_reward
)

equip_weapon_pre_quest_dialogue = [
    "New equipment should be assigned to a shipgirl to be used in battle.",
    "Let us visit {DD_shipgirl} in the dock and equip her with the new weapon.",
]
equip_weapon_quest_line = "Equip {DD_shipgirl} with the twin 120mm gun."
equip_weapon_post_quest_dialogue = [
    "Weapon equipped successfully.",
    "{DD_shipgirl} has become stronger.",
    "Your fleet is now stronger and ready for the next operation."
]

def equip_weapon_completion_criteria(menu_manager):
    return DataFiles.save_file["shipgirls"][DataFiles.get_faction_shipgirls()["DD"]]["equipment"][Equipment.WEAPON] == "twin_120"

def equip_weapon_tutorial_draw(menu_manager, surface, font):
    if menu_manager.current_menu == menu_manager.port_menu:
        rect = menu_manager.available_shipgirls[0].rect
        pygame.draw.rect(surface, Color.RED, rect, width=Box.OUTLINE_WIDTH)

        draw_tb(surface, font, None, rect.bottomright, False, False)
    elif (
        menu_manager.current_menu == menu_manager.equipment_menu
        and menu_manager.equipment_menu.selected_shipgirl.name == DataFiles.get_faction_shipgirls()["DD"]
    ):
        if menu_manager.equipment_menu.selected_slot == Equipment.WEAPON:
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

def equip_weapon_on_complete(menu_manager, save_file_load=False):
    pass

equip_weapon_quest = Quest(
    "equip_weapon",
    equip_weapon_pre_quest_dialogue,
    equip_weapon_quest_line,
    equip_weapon_post_quest_dialogue,
    equip_weapon_completion_criteria,
    equip_weapon_tutorial_draw,
    equip_weapon_on_start,
    equip_weapon_on_complete,
    decoration_voucher_reward
)

buy_decoration_pre_quest_dialogue = [
    "By completing missions, you can earn decoration coins.",
    "These coin can be used in the store to purchase new decorations.",
    "Decorations let you customize the port menu in the style you like best.",
    "Open the decoration store and purchase one decoration."
]
buy_decoration_quest_line = "Purchase a decoration from the decoration store."
buy_decoration_post_quest_dialogue = [
    "Purchase complete.",
    "The new decoration has been added to your collection.",
    "You can use decorations to make the port feel more personal.",
    "Try placing it in the port when you are ready."
]

def buy_decoration_completion_criteria(menu_manager):
    return any(
        decoration_count > 0
        for decoration_count in DataFiles.save_file["decoration_depot"].values()
    )

def buy_decoration_tutorial_draw(menu_manager, surface, font):
    if menu_manager.current_menu != menu_manager.port_menu:
        return

    if menu_manager.port_menu.current_overlay == menu_manager.port_menu.NO_OVERLAY:
        button_rect = menu_manager.port_menu.open_decoration_store_overlay_button.rect
        rect = get_rect(
            width=button_rect.width + 2*Box.PADDING,
            height=button_rect.height + 2*Box.PADDING,
            center=button_rect.center
        )
        pygame.draw.rect(surface, Color.RED, rect, width=Box.OUTLINE_WIDTH)

        draw_tb(surface, font, None, rect.topright, True, False)
    elif menu_manager.port_menu.current_overlay == menu_manager.port_menu.DECORATION_STORE:
        if menu_manager.port_menu.overlay_selected_entity is None:
            rect = menu_manager.port_menu.warehouse_overlay
            draw_tb(
                surface, font,
                "Pick any decoration to buy.",
                rect.center,
                False, False
            )
        elif menu_manager.port_menu.decoration_stamp_button.active:
            button_rect = menu_manager.port_menu.decoration_stamp_button.rect
            rect = get_rect(
                width=button_rect.width + 2*Box.PADDING,
                height=button_rect.height + 2*Box.PADDING,
                center=button_rect.center
            )
            pygame.draw.rect(surface, Color.RED, rect, width=Box.OUTLINE_WIDTH)

            draw_tb(surface, font, None, rect.bottomright, False, False)

def buy_decoration_on_start(menu_manager):
    menu_manager.port_menu.open_decoration_store_overlay_button.active = True

def buy_decoration_on_complete(menu_manager, save_file_load=False):
    quest_name = decorate_port_quest.quest_id
    menu_manager.quest_manager.quests[quest_name] = decorate_port_quest
    if quest_name not in DataFiles.save_file["quests"]:
        DataFiles.save_file["quests"][quest_name] = "new"

buy_decoration_quest = Quest(
    "buy_decoration",
    buy_decoration_pre_quest_dialogue,
    buy_decoration_quest_line,
    buy_decoration_post_quest_dialogue,
    buy_decoration_completion_criteria,
    buy_decoration_tutorial_draw,
    buy_decoration_on_start,
    buy_decoration_on_complete,
    decoration_voucher_reward
)

decorate_port_pre_quest_dialogue = [
    "Your new decoration is ready to be placed, Commander.",
    "You can customize the port by placing decorations wherever you like.",
    "If you don't like how something looks, you can remove the decoration or rotate it to a different angle.",
    "Try arranging the new decoration until it looks good to you."
]
decorate_port_quest_line = "Place a decoration in the port."
decorate_port_post_quest_dialogue = [
    "Decoration setup complete.",
    "The port is starting to feel more lively, Commander.",
    "You can return to the edit menu at any time to change the layout.",
    "Collect more decorations to further customize the port."
]

def decorate_port_completion_criteria(menu_manager):
    port_menu = menu_manager.port_menu
    return (
        port_menu.moved_decoration_depot_overlay
        and port_menu.rotated_decoration
        and port_menu.placed_decoration
        and port_menu.removed_decoration
        and len(DataFiles.save_file["decorations"]) > 0
        and not port_menu.decorating_port_menu
    )

def _decorate_port_get_depot_decoration_rects(port_menu):
    rects = []
    decoration_index = 0
    for decoration, amt in DataFiles.save_file["decoration_depot"].items():
        if amt <= 0:
            continue
        rect = get_rect(
            width=Box.WIDTH, height=Box.HEIGHT,
            left=port_menu.decoration_depot_overlay.left + (decoration_index%3)*(Box.WIDTH+Box.PADDING) + Box.PADDING,
            top=port_menu.decoration_depot_overlay.top + (decoration_index//3)*(Box.HEIGHT+Box.PADDING) + Box.PADDING
        )
        rects.append(rect)
        decoration_index += 1
    return rects

def _decorate_port_get_delete_rect(port_menu):
    decoration_index = sum(
        1 for amt in DataFiles.save_file["decoration_depot"].values()
        if amt > 0
    )
    return get_rect(
        width=Box.WIDTH, height=Box.HEIGHT,
        left=port_menu.decoration_depot_overlay.left + (decoration_index%3)*(Box.WIDTH+Box.PADDING) + Box.PADDING,
        top=port_menu.decoration_depot_overlay.top + (decoration_index//3)*(Box.HEIGHT+Box.PADDING) + Box.PADDING
    )

def _decorate_port_get_placed_decoration_rect():
    if len(DataFiles.save_file["decorations"]) <= 0:
        return None

    decoration, tilepos_anchor, direction = DataFiles.save_file["decorations"][0]
    decoration_info = DataFiles.decoration_store[decoration][direction]
    return get_rect(
        width=decoration_info["width"] * Decorations.TILESIZE,
        height=decoration_info["height"] * Decorations.TILESIZE,
        left=Decorations.floor_rect.left + tilepos_anchor[0] * Decorations.TILESIZE,
        top=Decorations.floor_rect.top + tilepos_anchor[1] * Decorations.TILESIZE
    )

def _decorate_port_draw_depot_items(menu_manager, surface, font, text):
    for rect in _decorate_port_get_depot_decoration_rects(menu_manager.port_menu):
        pygame.draw.rect(surface, Color.RED, rect, width=Box.OUTLINE_WIDTH)

    draw_tb(
        surface, font,
        text,
        rect.bottomright,
        False, False
    )

def decorate_port_tutorial_draw(menu_manager, surface, font):
    if menu_manager.current_menu != menu_manager.port_menu:
        return

    port_menu = menu_manager.port_menu
    if not port_menu.decorating_port_menu:
        if port_menu.current_overlay != port_menu.NO_OVERLAY:
            return

        button_rect = port_menu.open_close_decoration_menu_button.rect
        rect = get_rect(
            width=button_rect.width + 2*Box.PADDING,
            height=button_rect.height + 2*Box.PADDING,
            center=button_rect.center
        )
        pygame.draw.rect(surface, Color.RED, rect, width=Box.OUTLINE_WIDTH)

        draw_tb(surface, font, None, rect.bottomleft, False, True)
        return

    if not port_menu.moved_decoration_depot_overlay:
        rect = port_menu.decoration_depot_overlay
        draw_tb(
            surface, font,
            "Drag the depot overlay if it is in the way.",
            (rect.right, rect.centery),
            False, False
        )
        return

    if not port_menu.placed_decoration:
        if port_menu.selected_decoration_in_depot is None:
            _decorate_port_draw_depot_items(
                menu_manager, surface, font,
                "Pick one decoration from your depot."
            )
        elif not port_menu.rotated_decoration:
            draw_tb(
                surface, font,
                "Right click to rotate the decoration.",
                pygame.mouse.get_pos(),
                False, False
            )
        else:
            draw_tb(
                surface, font,
                "Left click an open tile to place it.",
                pygame.mouse.get_pos(),
                False, False
            )
        return

    if not port_menu.removed_decoration:
        if not port_menu.deleting_decoration:
            rect = _decorate_port_get_delete_rect(port_menu)
            pygame.draw.rect(surface, Color.RED, rect, width=Box.OUTLINE_WIDTH)
            draw_tb(
                surface, font,
                "Use this to remove a placed decoration.",
                rect.bottomright,
                False, False
            )
        else:
            rect = _decorate_port_get_placed_decoration_rect()
            if rect is not None:
                pygame.draw.rect(surface, Color.RED, rect, width=Box.OUTLINE_WIDTH)
                draw_tb(
                    surface, font,
                    "Click the placed decoration to return it to the depot.",
                    rect.bottomright,
                    False, False
                )
        return

    if len(DataFiles.save_file["decorations"]) <= 0:
        draw_tb(
            surface, font,
            "Place the decoration again.",
            pygame.mouse.get_pos(),
            False, False
        )
        return

    button_rect = port_menu.open_close_decoration_menu_button.rect
    rect = get_rect(
        width=button_rect.width + 2*Box.PADDING,
        height=button_rect.height + 2*Box.PADDING,
        center=button_rect.center
    )
    pygame.draw.rect(surface, Color.RED, rect, width=Box.OUTLINE_WIDTH)

    draw_tb(surface, font, "Exit edit mode.", rect.bottomleft, False, True)

def decorate_port_on_start(menu_manager):
    port_menu = menu_manager.port_menu
    port_menu.open_close_decoration_menu_button.active = True
    port_menu.moved_decoration_depot_overlay = False
    port_menu.rotated_decoration = False
    port_menu.placed_decoration = False
    port_menu.removed_decoration = False

def decorate_port_on_complete(menu_manager, save_file_load=False):
    pass

decorate_port_quest = Quest(
    "decorate_port",
    decorate_port_pre_quest_dialogue,
    decorate_port_quest_line,
    decorate_port_post_quest_dialogue,
    decorate_port_completion_criteria,
    decorate_port_tutorial_draw,
    decorate_port_on_start,
    decorate_port_on_complete,
    decoration_voucher_reward
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
    equip_weapon_quest,
    buy_decoration_quest,
    decorate_port_quest,
]
