from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from engine.types import CoordinateType
    from engine.font import Font
    from src.menus.menu_manager import MenuManager
    from src.menus.port_menu import PortMenu
    from src.menus.quests import Quest
    from src.shipgirls import Shipgirl

import math
import pygame

from engine.util import get_rect, get_vec, hex_to_pixel
from src.constants import DataFiles, Box, Color, Equipment, Decorations

from src.menus.quests import Quest
from src.menus.sortie_selection_menu import SortieNode


def assign_quest(menu_manager: MenuManager, quest: Quest):
    """Assign this quest, if it has not already been assigned."""
    if quest.quest_id in DataFiles.save_file["quests"]:
        return

    menu_manager.quest_manager.quests[quest.quest_id] = quest
    DataFiles.save_file["quests"][quest.quest_id] = menu_manager.quest_manager.STATUS_NEW

def empty_tutorial_draw(menu_manager: MenuManager, surface: pygame.Surface, font_registry: dict[str, Font]):
    """Empty draw for tutorials that don't need tutorial rendering."""
    pass

def draw_tb(surface: pygame.Surface, font_registry: dict[str, Font], text: str | None, point_pos: CoordinateType, point_down: bool, point_right: bool):
    """Render the TB pointer sprite, pointing to the point pos, with a text bubble if provided."""
    # Make the TB pointer sprite point towards the point pos.
    # The TB pointer points diagonally.
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

    if text:
        # Render a text bubble, aligned so that it respects in which direction TB is pointing.
        text_scale = 1
        text_left_padding = 14
        text_right_padding = Box.PADDING
        max_chars_in_line = 25
        max_text_width = font_registry["big_pixel"].font_width * max_chars_in_line
        text_height = font_registry["big_pixel"].get_height(text, text_scale, max_text_width)
        text_box_width = font_registry["big_pixel"].get_width(text, text_scale, max_text_width)
        text_rect = get_rect(
            width=text_box_width + text_left_padding + text_right_padding,
            height=text_height + 2 * Box.PADDING,
            centerx=pointer_rect.centerx,
            bottom=pointer_rect.top
        )
        if point_right:
            text_rect.right = pointer_rect.left
            polygon = [
                (text_rect.width, text_rect.height - Box.PADDING),
                (text_rect.width + Box.PADDING, text_rect.height + Box.PADDING),
                (text_rect.width - Box.PADDING, text_rect.height)
            ]
        else:
            text_rect.left = pointer_rect.right
            polygon = [
                (0, text_rect.height - Box.PADDING),
                (-Box.PADDING, text_rect.height + Box.PADDING),
                (Box.PADDING, text_rect.height)
            ]
        accent = Color.QUEST_NOTIFICATION_NEW
        panel = pygame.Surface((text_rect.width + Box.PADDING, text_rect.height + Box.PADDING), pygame.SRCALPHA)
        panel_polygon = [
            (Quest.PANEL_CUT, text_rect.height),
            (0, text_rect.height - Quest.PANEL_CUT),
            (0, 0),
            (text_rect.width - Quest.PANEL_CUT, 0),
            (text_rect.width, Quest.PANEL_CUT),
            (text_rect.width, text_rect.height),
        ]
        pygame.draw.polygon(
            panel,
            (*Color.QUEST_NOTIFICATION_PANEL, 225),
            panel_polygon,
        )
        pygame.draw.lines(
            panel,
            (*accent, 230),
            False,
            panel_polygon[:-1],
            width=1,
        )
        pygame.draw.polygon(
            panel,
            (*Color.QUEST_NOTIFICATION_PANEL, 225),
            polygon,
        )
        surface.blit(panel, text_rect)

        rail_margins = 6
        rail_rect = get_rect(
            width=3,
            height=max(1, text_rect.height - 2 * rail_margins),
            left=text_rect.left + rail_margins,
            centery=text_rect.centery,
        )
        rail_glow = pygame.Surface(rail_rect.size, pygame.SRCALPHA)
        rail_glow.fill((*accent, 60))
        surface.blit(
            rail_glow,
            rail_rect,
            special_flags=pygame.BLEND_RGBA_ADD,
        )
        font_registry["big_pixel"].render(
            surface,
            text,
            pygame.Vector2(text_rect.topleft)
            + pygame.Vector2(text_left_padding, Box.PADDING),
            Color.QUEST_NOTIFICATION_TEXT,
            text_scale,
            box_width=max_text_width
        )

choose_faction_pre_quest_dialogue = [
    "Greetings, Commander.",
    "I am TB, your virtual assistant and navigator.",
    "To complete port registration, you must select a faction to support.",
    "This choice determines which faction's shipgirls can initially join your fleet.",
    "Review the available factions before making your selection.",
]
choose_faction_quest_line = "Choose a faction."
choose_faction_post_quest_dialogue = [
    "Faction registration successful.",
    "Your port authorization is now active, Commander.",
]

def choose_faction_completion_criteria(menu_manager: MenuManager) -> bool:
    completed = len(DataFiles.save_file["unlocked_factions"]) > 0
    if completed:
        chosen_faction = DataFiles.save_file["unlocked_factions"][0]

        # Update the rewards dynamically to provide the correct unique items to craft
        # the correct starter shipgirls based on chosen faction.
        for shipgirl_info in DataFiles.shipgirl_data.values():
            if shipgirl_info["faction"] != chosen_faction:
                continue
            if shipgirl_info["hull_type"] not in ["DD", "BB"]:
                continue
            choose_faction_quest.rewards[shipgirl_info["unique_item"]] = 1

        choose_faction_quest.rewards.pop("placeholder_DD")
        choose_faction_quest.rewards.pop("placeholder_BB")

    return completed

def choose_faction_tutorial_draw(menu_manager: MenuManager, surface: pygame.Surface, font_registry: dict[str, Font]):
    pass

def choose_faction_on_start(menu_manager: MenuManager):
    faction_selection_pending = not DataFiles.save_file["unlocked_factions"]
    for choose_faction_button in menu_manager.port_menu.choose_faction_buttons:
        choose_faction_button.active = faction_selection_pending

def choose_faction_on_complete(menu_manager: MenuManager):
    # On complete, the quest needs to convert the wisdom cubes awarded in the quest
    # into specialized wisdom cubes for the starter shipgirls.
    faction_shipgirls = DataFiles.get_faction_shipgirls()
    specialized_wisdom_cubes = DataFiles.save_file["specialized_wisdom_cubes"]
    for hull_type in ["DD", "BB"]:
        shipgirl = faction_shipgirls[hull_type]
        if shipgirl in DataFiles.save_file["shipgirls"]:
            continue
        if shipgirl in specialized_wisdom_cubes:
            continue
        if DataFiles.save_file["inventory"].get("wisdom_cube", 0) > 0:
            DataFiles.save_file["inventory"]["wisdom_cube"] -= 1
            specialized_wisdom_cubes[shipgirl] = 0

    assign_quest(menu_manager, construct_shipgirls_quest)
    
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
    "Currently, there are no shipgirls registered to your fleet.",
    "High Command has supplied the blueprints, Wisdom Cubes, and materials required for two constructions.",
    "The available candidates are {DD_shipgirl} and {BB_shipgirl}.",
    "Navigate to the shipyard and construct both shipgirls.",
]
construct_shipgirls_quest_line = (
    "Construct {DD_shipgirl} and {BB_shipgirl} in the shipyard."
)
construct_shipgirls_post_quest_dialogue = [
    "Construction complete.",
    "{DD_shipgirl} and {BB_shipgirl} are now registered to your fleet.",
    "The fleet has the minimum personnel required for deployment.",
]

def construct_shipgirls_completion_criteria(menu_manager: MenuManager) -> bool:
    shipgirls = DataFiles.get_faction_shipgirls()
    return all(
        shipgirl in DataFiles.save_file["shipgirls"]
        for shipgirl in [shipgirls["DD"], shipgirls["BB"]]
    )

def shipyard_tutorial_draw_factory(highlighted_hull_types: list[str]):
    """Factory to generate draw functions for the shipyard tutorials."""
    def shipyard_tutorial_draw(menu_manager: MenuManager, surface: pygame.Surface, font_registry: dict[str, Font]):
        if menu_manager.current_menu != menu_manager.port_menu:
            return
        
        if menu_manager.port_menu.current_overlay == menu_manager.port_menu.NO_OVERLAY:
            # Point towards overlay button.
            rect = menu_manager.port_menu.open_shipyard_overlay_button.rect
            rect = rect.inflate(-Box.WIDTH / 2, -Box.HEIGHT / 2)
            draw_tb(surface, font_registry, None, rect.topright, True, False)
        elif menu_manager.port_menu.current_overlay == menu_manager.port_menu.SHIPYARD:
            shipgirl_data = {
                shipgirl: shipgirl_info for shipgirl, shipgirl_info in DataFiles.shipgirl_data.items()
                if shipgirl not in DataFiles.save_file["shipgirls"]
                and shipgirl_info["faction"] in DataFiles.save_file["unlocked_factions"]
                and shipgirl_info["faction"] == menu_manager.port_menu.shipyard_filters[
                    menu_manager.port_menu.overlay_selected_filter
                ]
            }
            tutorial_done = True
            faction_shipgirls = DataFiles.get_faction_shipgirls()
            shipgirls = [faction_shipgirls[hull_type] for hull_type in highlighted_hull_types]
            for i, (shipgirl, shipgirl_info) in enumerate(shipgirl_data.items()):
                # Point towards the entities the player should select on the dossier page.
                # Do not point towards it if it is selected.
                if menu_manager.port_menu.overlay_selected_entity == shipgirl:
                    continue
                if shipgirl in DataFiles.save_file["shipgirls"]:
                    continue
                if shipgirl_info["faction"] not in DataFiles.save_file["unlocked_factions"]:
                    continue
                if shipgirl not in shipgirls:
                    continue

                rect = menu_manager.port_menu.dossier_icons[i]
                rect = rect.inflate(-Box.WIDTH / 2, -Box.HEIGHT / 2)
                draw_tb(surface, font_registry, None, rect.bottomleft, False, True)
                tutorial_done = False
            
            if (
                menu_manager.port_menu.overlay_selected_entity in shipgirls
                and menu_manager.port_menu.shipyard_sticky_note_button.text in ["construct?", "research?"]
            ):
                # Point towards the sticky note button if the correct shipgirl is selected.
                rect = menu_manager.port_menu.shipyard_sticky_note_button.rect
                rect = rect.inflate(-Box.WIDTH / 2, -Box.HEIGHT / 2)
                draw_tb(surface, font_registry, None, rect.bottomleft, False, True)
                tutorial_done = False

            # The tutorial has been completed i.e. TB is not pointing to anything,
            # so draw TB pointing outside of the overlay to tell the player to exit.
            if tutorial_done:
                point = menu_manager.port_menu.dossier_bg.bottomright + pygame.Vector2(-32, 32)
                draw_tb(surface, font_registry, "exit the shipyard", point, True, True)

    return shipyard_tutorial_draw

def construct_shipgirls_on_start(menu_manager: MenuManager):
    menu_manager.port_menu.open_shipyard_overlay_button.active = True

def construct_shipgirls_on_complete(menu_manager: MenuManager):
    assign_quest(menu_manager, first_sortie_quest)

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
    "Your fleet is ready for its first deployment.",
    "Sorties are combat operations used to engage Siren forces, secure ocean sectors, and recover resources.",
    "Select sector 1 and issue the sortie order.",
]
first_sortie_quest_line = "Complete a sortie in sector 1."
first_sortie_post_quest_dialogue = [
    "Sortie complete.",
    "Sector 1 is secure, and the recovered resources have been transferred to the port.",
    "Further sorties will expand our operational range and provide materials for fleet development.",
    "Additional port assignments are now available.",
]

def first_sortie_completion_criteria(menu_manager: MenuManager) -> bool:
    return DataFiles.save_file["sortie_progress"] == 1

def first_sortie_tutorial_draw(menu_manager: MenuManager, surface: pygame.Surface, font_registry: dict[str, Font]):
    if menu_manager.current_menu == menu_manager.port_menu:
        # Point towards the sortie button.
        rect = menu_manager.port_menu.open_select_sortie_menu_button.rect
        rect = rect.inflate(-Box.WIDTH / 2, -Box.HEIGHT / 2)
        draw_tb(surface, font_registry, None, rect.topleft, True, True)
    elif menu_manager.current_menu == menu_manager.sortie_selection_menu:
        if menu_manager.sortie_selection_menu.selected_sortie_node is not None:
            # Point towards the sortie button.
            rect = menu_manager.sortie_selection_menu.sortie_order_card.button.rect
            rect = rect.inflate(-Box.WIDTH / 2, -Box.HEIGHT / 2)
            draw_tb(surface, font_registry, None, rect.bottomleft, False, True)
        else:
            # Point towards the sortie node.
            q, r = menu_manager.sortie_selection_menu.sortie_nodes[0].hexes[0]
            xy = hex_to_pixel(q, r, SortieNode.SIZE)
            rect = get_rect(
                width=SortieNode.SIZE, height=SortieNode.SIZE,
                center=pygame.Vector2(xy) + SortieNode.center
            )
            rect = rect.inflate(-Box.WIDTH / 2, -Box.HEIGHT / 2)
            draw_tb(surface, font_registry, None, rect.bottomleft, False, True)
        # Point towards the exit button.
        rect = menu_manager.sortie_selection_menu.exit_sortie_selection_menu_button.rect
        rect = rect.inflate(-Box.WIDTH / 2, -Box.HEIGHT / 2)
        draw_tb(surface, font_registry, "click this to go back", rect.bottomleft, False, True)
    elif menu_manager.current_menu == menu_manager.fleet_selection_menu:
        if menu_manager.encounter_menu.transition_active:
            return
        if menu_manager.fleet_selection_menu.start_sortie_button.active:
            # Point towards the sortie button.
            rect = menu_manager.fleet_selection_menu.start_sortie_button.rect
            rect = rect.inflate(-Box.WIDTH / 2, -Box.HEIGHT / 2)
            draw_tb(surface, font_registry, None, rect.topright, True, False)

            # Tell the player they can shuffle around markers in the fleet.
            rect = (
                menu_manager.fleet_selection_menu.fleet_slots[0]
                .unionall(menu_manager.fleet_selection_menu.fleet_slots[1:])
            )
            rect = rect.inflate(-Box.WIDTH / 2, -Box.HEIGHT / 2)
            draw_tb(
                surface, font_registry,
                "you can shuffle around the markers to reorganize your fleet",
                rect.bottomright,
                False, False
            )

            # Tell the player they can return markers to the tray.
            point =  menu_manager.fleet_selection_menu.tray_overlay.center
            draw_tb(
                surface, font_registry,
                "you can drag and drop markers back here to unassign shipgirls from your fleet",
                point,
                True, True
            )
        else:
            # Point towards the fleet box and tell players to drag and drop markers here.
            rect = (
                menu_manager.fleet_selection_menu.fleet_slots[0]
                .unionall(menu_manager.fleet_selection_menu.fleet_slots[1:])
            )
            rect = rect.inflate(-Box.WIDTH / 2, -Box.HEIGHT / 2)
            shipgirls = DataFiles.get_faction_shipgirls()
            dd_shipgirl = shipgirls["DD"].replace("_", " ")
            bb_shipgirl = shipgirls["BB"].replace("_", " ")
            draw_tb(
                surface, font_registry,
                f"drag and drop {dd_shipgirl} and {bb_shipgirl}'s markers to assign them to your fleet",
                rect.bottomright,
                False, False
            )
        # Point towards the exit button.
        rect = menu_manager.fleet_selection_menu.exit_fleet_selection_menu_button.rect
        rect = rect.inflate(-Box.WIDTH / 2, -Box.HEIGHT / 2)
        draw_tb(surface, font_registry, "click this to go back", rect.bottomleft, False, True)
    elif menu_manager.current_menu == menu_manager.encounter_menu:
        if menu_manager.encounter_menu.transition_active:
            return
        if not menu_manager.encounter_menu.encounter_started:
            # Tell the player to drag all shipgirls to the entity siren.
            rect = menu_manager.siren_fleet.front[0].rect
            rect = rect.inflate(-Box.WIDTH / 2, -Box.HEIGHT / 2)
            draw_tb(
                surface, font_registry,
                "drag all of your shipgirls to target the enemy siren",
                rect.bottomright,
                False, False
            )
            # Point towards the retreat button.
            rect = menu_manager.encounter_menu.retreat_button.rect
            rect = rect.inflate(-Box.WIDTH / 2, -Box.HEIGHT / 2)
            draw_tb(
                surface, font_registry,
                "if you need to retreat, click this button",
                rect.bottomleft,
                False, True
            )
        elif menu_manager.encounter_menu.next_encounter_button.active:
            # Point towards the next encounter button.
            rect = menu_manager.encounter_menu.next_encounter_button.rect
            rect = rect.inflate(-Box.WIDTH / 2, -Box.HEIGHT / 2)
            draw_tb(surface, font_registry, None, rect.bottomleft, False, True)
        elif menu_manager.encounter_menu.return_to_port_button.active:
            # Point towards the return to port button.
            rect = menu_manager.encounter_menu.return_to_port_button.rect
            rect = rect.inflate(-Box.WIDTH / 2, -Box.HEIGHT / 2)
            draw_tb(surface, font_registry, None, rect.bottomleft, False, True)
        elif menu_manager.encounter_menu.open_reward_cache_button.active:
            # Point towards the siren cache.
            point = menu_manager.encounter_menu.open_reward_cache_button.rect.center
            draw_tb(surface, font_registry, "extract rewards from the siren cache", point, False, True)

def first_sortie_on_start(menu_manager: MenuManager):
    menu_manager.port_menu.open_select_sortie_menu_button.active = True

def first_sortie_on_complete(menu_manager: MenuManager):
    assign_quest(menu_manager, inventory_quest)

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
    "The resources you extracted from the sortie have been delivered to your depot.",
    "The depot stores items collected from battles, missions, and other port activities.",
    "Open the depot to review the available inventory.",
]
inventory_quest_line = "Visit the depot."
inventory_post_quest_dialogue = [
    "Depot access confirmed.",
    "Monitor stored supplies when planning construction, research, and equipment upgrades.",
    "Newly acquired materials will be recorded here automatically.",
]

def inventory_completion_criteria(menu_manager: MenuManager) -> bool:
    return menu_manager.port_menu.visited_depot

def inventory_tutorial_draw(menu_manager: MenuManager, surface: pygame.Surface, font_registry: dict[str, Font]):
    if menu_manager.current_menu != menu_manager.port_menu:
        return

    if menu_manager.port_menu.current_overlay == menu_manager.port_menu.NO_OVERLAY:
        # Point towards the overlay button.
        rect = menu_manager.port_menu.open_depot_overlay_button.rect
        rect = rect.inflate(-Box.WIDTH / 2, -Box.HEIGHT / 2)
        draw_tb(surface, font_registry, None, rect.topright, True, False)
    elif menu_manager.port_menu.current_overlay == menu_manager.port_menu.DEPOT:
        # Point towards the overlay.
        rect = menu_manager.port_menu.warehouse_overlay
        draw_tb(
            surface, font_registry,
            "You can see all of your items here",
            (rect.left + rect.width / 3, rect.bottom),
            False, True
        )
        if menu_manager.port_menu.overlay_selected_entity is None:
            # Point towards an item in the inventory.
            rect = menu_manager.port_menu.warehouse_icons[0]
            rect = rect.inflate(-Box.WIDTH / 2, -Box.HEIGHT / 2)
            draw_tb(surface, font_registry, None, rect.bottomright, False, False)
        else:
            # Point towards the clipboard overlay.
            point = menu_manager.port_menu.warehouse_overlay.bottomright + pygame.Vector2(-32, 64)
            draw_tb(surface, font_registry, "exit the depot", point, True, True)

def inventory_on_start(menu_manager: MenuManager):
    menu_manager.port_menu.open_depot_overlay_button.active = True

def inventory_on_complete(menu_manager: MenuManager):
    assign_quest(menu_manager, intel_center_quest)

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
    "Combat data from every sortie is recorded in the intel center.",
    "Its records contain information on Siren units your fleet has encountered.",
    "Different enemies have different strengths and weaknesses.",
    "Reviewing these records can help you prepare suitable fleets and equipment for future battles.",
    "Open the intel center and inspect the available records.",
]
intel_center_quest_line = "Visit the intel center."
intel_center_post_quest_dialogue = [
    "Intel center access confirmed.",
    "Enemy records will update as your fleet encounters new threats.",
    "Consult this information before entering unfamiliar sectors.",
]

def intel_center_completion_criteria(menu_manager: MenuManager) -> bool:
    return menu_manager.port_menu.visited_intel_center

def intel_center_tutorial_draw(menu_manager: MenuManager, surface: pygame.Surface, font_registry: dict[str, Font]):
    if menu_manager.current_menu != menu_manager.port_menu:
        return

    if menu_manager.port_menu.current_overlay == menu_manager.port_menu.NO_OVERLAY:
        # Point towards the overlay button.
        rect = menu_manager.port_menu.open_intel_center_overlay_button.rect
        rect = rect.inflate(-Box.WIDTH / 2, -Box.HEIGHT / 2)
        draw_tb(surface, font_registry, None, rect.topright, True, False)
    elif menu_manager.port_menu.current_overlay == menu_manager.port_menu.INTEL_CENTER:
        if menu_manager.port_menu.overlay_selected_entity is None:
            # Point towards a siren entry.
            rect = menu_manager.port_menu.dossier_icons[0]
            rect = rect.inflate(-Box.WIDTH / 2, -Box.HEIGHT / 2)
            draw_tb(surface, font_registry, None, rect.bottomright, False, False)
        else:
            # Point towards the blueprint overlay.
            rect = menu_manager.port_menu.blueprint_page
            rect = rect.inflate(-Box.WIDTH / 2, -Box.HEIGHT / 2)
            draw_tb(
                surface, font_registry,
                "the intel center has information on siren stats as well as the potential drops from defeating the siren",
                (rect.left, rect.centery),
                False, True
            )
            # Point outside of the overlay.
            point = menu_manager.port_menu.dossier_bg.bottomright + pygame.Vector2(-32, 32)
            draw_tb(surface, font_registry, "exit the intel center", point, True, True)

def intel_center_on_start(menu_manager: MenuManager):
    menu_manager.port_menu.open_intel_center_overlay_button.active = True

def intel_center_on_complete(menu_manager: MenuManager):
    assign_quest(menu_manager, research_shipgirl_quest)

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
    "A larger fleet will be required as operations extend into more dangerous territory.",
    "Each shipgirl has a unique item that is required for construction.",
    "To obtain one, begin a research project and collect combat data during sorties.",
    "Once sufficient data has been collected, the project will synthesize the unique item.",
    "The shipgirl can then be constructed if the remaining material requirements are met.",
    "Open the shipyard and begin research on {CA_shipgirl}.",
]
research_shipgirl_quest_line = "Begin researching {CA_shipgirl} in the shipyard."
research_shipgirl_post_quest_dialogue = [
    "Research project started.",
    "Future sorties will now contribute combat data to {CA_shipgirl}'s research project.",
    "Continue into the newly unlocked sector to gather the required data.",
]

def research_shipgirl_completion_criteria(menu_manager: MenuManager) -> bool:
    shipgirl = DataFiles.get_faction_shipgirls()["CA"]
    return DataFiles.save_file["research_target"] == shipgirl

def research_shipgirl_on_start(menu_manager: MenuManager):
    menu_manager.port_menu.open_shipyard_overlay_button.active = True

def research_shipgirl_on_complete(menu_manager: MenuManager):
    assign_quest(menu_manager, construct_shipgirl_quest)

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
    "Research on {CA_shipgirl} is now underway, Commander.",
    "Gather the required combat data during sorties to synthesize her unique item.",
    "Once the research and remaining material requirements are complete, construct {CA_shipgirl} in the shipyard.",
]
construct_shipgirl_quest_line = "Collect combat data to finish the research project, then construct {CA_shipgirl} in the shipyard."
construct_shipgirl_post_quest_dialogue = [
    "Construction complete.",
    "{CA_shipgirl} is now registered to your fleet.",
    "Additional fleet compositions are now available for future operations.",
]

def construct_shipgirl_completion_criteria(menu_manager: MenuManager) -> bool:
    return DataFiles.get_faction_shipgirls()["CA"] in DataFiles.save_file["shipgirls"]

def construct_shipgirl_on_start(menu_manager: MenuManager):
    pass

def construct_shipgirl_on_complete(menu_manager: MenuManager):
    assign_quest(menu_manager, craft_weapon_quest)

construct_shipgirl_quest = Quest(
    "construct_shipgirl",
    construct_shipgirl_pre_quest_dialogue,
    construct_shipgirl_quest_line,
    construct_shipgirl_post_quest_dialogue,
    construct_shipgirl_completion_criteria,
    empty_tutorial_draw,
    construct_shipgirl_on_start,
    construct_shipgirl_on_complete,
    decoration_voucher_reward
)

craft_weapon_pre_quest_dialogue = [
    "Sector 3 has been secured.",
    "The recovered materials are sufficient to craft new equipment.",
    "The gear lab is now available for equipment production.",
    "Open the gear lab and craft a twin 120mm gun for {DD_shipgirl}.",
]
craft_weapon_quest_line = "Craft the twin 120mm gun in the gear lab."
craft_weapon_post_quest_dialogue = [
    "Crafting complete.",
    "The twin 120mm gun has been added to the equipment inventory.",
    "Crafted equipment must be assigned to a shipgirl before it can be used in combat.",
]

def craft_weapon_completion_criteria(menu_manager: MenuManager) -> bool:
    return DataFiles.save_file["equipment"].get("twin_120", 0) == 1

def craft_weapon_tutorial_draw(menu_manager: MenuManager, surface: pygame.Surface, font_registry: dict[str, Font]):
    inventory = DataFiles.save_file["inventory"]
    craft_reqs = DataFiles.equipment_data["twin_120"]["craft_reqs"]
    has_craft_reqs = all(
        inventory.get(ingredient, 0) >= amount
        for ingredient, amount in craft_reqs.items()
    )
    if (
        "twin_120" not in DataFiles.save_file["equipment"]
        and not has_craft_reqs
    ):
        return

    if menu_manager.current_menu != menu_manager.port_menu:
        return

    if menu_manager.port_menu.current_overlay == menu_manager.port_menu.NO_OVERLAY:
        # Point towards the overlay button.
        rect = menu_manager.port_menu.open_gear_lab_overlay_button.rect
        rect = rect.inflate(-Box.WIDTH / 2, -Box.HEIGHT / 2)
        draw_tb(surface, font_registry, None, rect.topright, True, False)
    elif menu_manager.port_menu.current_overlay == menu_manager.port_menu.GEAR_LAB:
        if menu_manager.port_menu.overlay_selected_entity == "twin_120":
            if menu_manager.port_menu.gear_lab_sticky_note_button.active:
                # Point towards the sticky note button.
                rect = menu_manager.port_menu.gear_lab_sticky_note_button.rect
                rect = rect.inflate(-Box.WIDTH / 2, -Box.HEIGHT / 2)
                draw_tb(surface, font_registry, None, rect.bottomleft, False, True)
            else:
                # Point outside of the overlay.
                point = menu_manager.port_menu.dossier_bg.bottomright + pygame.Vector2(-32, 32)
                draw_tb(surface, font_registry, "exit the gear lab", point, True, True)
        elif menu_manager.port_menu.gear_lab_filters[menu_manager.port_menu.overlay_selected_filter] == "DD":
            # Point towards the twin 120mm gun.
            rect = menu_manager.port_menu.dossier_icons[0]
            rect = rect.inflate(-Box.WIDTH / 2, -Box.HEIGHT / 2)
            draw_tb(surface, font_registry, None, rect.bottomright, False, False)

def craft_weapon_on_start(menu_manager: MenuManager):
    menu_manager.port_menu.open_gear_lab_overlay_button.active = True

def craft_weapon_on_complete(menu_manager: MenuManager):
    assign_quest(menu_manager, equip_weapon_quest)

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
    "The new weapon must be assigned to a shipgirl before it can be used in battle.",
    "Open {DD_shipgirl}'s equipment screen from the dock and equip the twin 120mm gun.",
]
equip_weapon_quest_line = "Equip {DD_shipgirl} with the twin 120mm gun."
equip_weapon_post_quest_dialogue = [
    "Weapon equipped successfully.",
    "{DD_shipgirl}'s combat loadout has been updated.",
    "Review each shipgirl's equipment as stronger options become available.",
]

def equip_weapon_completion_criteria(menu_manager: MenuManager) -> bool:
    return DataFiles.save_file["shipgirls"][DataFiles.get_faction_shipgirls()["DD"]]["equipment"][Equipment.WEAPON] == "twin_120"

def equip_weapon_tutorial_draw(menu_manager: MenuManager, surface: pygame.Surface, font_registry: dict[str, Font]):
    if menu_manager.current_menu == menu_manager.port_menu:
        if menu_manager.port_menu.shipgirl_dialogue_options[0].active:
            # Point towards the equipment menu dialogue option.
            button = menu_manager.port_menu.shipgirl_dialogue_options[0]
            point = button.get_wedge_centroid()
            draw_tb(surface, font_registry, None, point, False, False)
        else:
            # Point towards the DD shipgirl.
            shipgirls = DataFiles.get_faction_shipgirls()
            dd_shipgirl_name = shipgirls["DD"].replace("_", " ")
            dd_shipgirl = next(shipgirl for shipgirl in menu_manager.available_shipgirls if shipgirl.name == dd_shipgirl_name)
            rect = dd_shipgirl.rect
            rect = rect = rect.inflate(-Box.WIDTH, -Box.HEIGHT)
            draw_tb(surface, font_registry, None, rect.bottomright, False, False)
    elif (
        menu_manager.current_menu == menu_manager.equipment_menu
        and menu_manager.equipment_menu.selected_shipgirl.name == DataFiles.get_faction_shipgirls()["DD"]
    ):
        if menu_manager.equipment_menu.selected_slot == Equipment.WEAPON:
            selected_shipgirl = menu_manager.equipment_menu.selected_shipgirl
            if selected_shipgirl.battle_component.equipment[Equipment.WEAPON] is None:
                tutorial_text = "hover over the weapon to preview its stats, then click to equip"
            else:
                tutorial_text = "click this to unequip the weapon"
                # Point towards the exit button.
                rect = menu_manager.equipment_menu.exit_equipment_menu_button.rect
                rect = rect.inflate(-Box.WIDTH / 2, -Box.HEIGHT / 2)
                draw_tb(surface, font_registry, "exit the equipment workshop", rect.bottomleft, False, True)
            # Point towards the equipment icon in the depot, which can either be the actual
            # equipment or the unequip button.
            rect = menu_manager.equipment_menu.equippable_rects[0]
            rect = rect.inflate(-Box.WIDTH / 2, -Box.HEIGHT / 2)
            draw_tb(surface, font_registry, tutorial_text, rect.bottomleft, False, True)
        else:
            # Point towards the weapon slot.
            rect = menu_manager.equipment_menu.equipped_rects[0]
            rect = rect.inflate(-Box.WIDTH / 2, -Box.HEIGHT / 2)
            draw_tb(surface, font_registry, None, rect.bottomleft, False, True)

def equip_weapon_on_start(menu_manager: MenuManager):
    pass

def equip_weapon_on_complete(menu_manager: MenuManager):
    assign_quest(menu_manager, clear_first_maritime_region_quest)

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

clear_first_maritime_region_pre_quest_dialogue = [
    "The fleet is now prepared for the operation's final engagement, Commander.",
    "Only one Siren stronghold remains in this maritime region.",
    "Complete the final sortie and secure the region.",
]
clear_first_maritime_region_quest_line = (
    "Complete the final sortie in the first maritime region."
)
clear_first_maritime_region_post_quest_dialogue = [
    "The first maritime region is secure.",
    "You have successfully prepared, deployed, and supplied the fleet through a complete operation.",
    "High Command has authorized continued operations in the next maritime region.",
]

def clear_first_maritime_region_completion_criteria(menu_manager: MenuManager) -> bool:
    return DataFiles.save_file["chapter_progress"] >= 1

def clear_first_maritime_region_on_start(menu_manager: MenuManager):
    menu_manager.port_menu.open_select_sortie_menu_button.active = True

def clear_first_maritime_region_on_complete(menu_manager: MenuManager):
    assign_quest(menu_manager, buy_decoration_quest)

clear_first_maritime_region_quest = Quest(
    "clear_first_maritime_region",
    clear_first_maritime_region_pre_quest_dialogue,
    clear_first_maritime_region_quest_line,
    clear_first_maritime_region_post_quest_dialogue,
    clear_first_maritime_region_completion_criteria,
    empty_tutorial_draw,
    clear_first_maritime_region_on_start,
    clear_first_maritime_region_on_complete,
    decoration_voucher_reward
)

buy_decoration_pre_quest_dialogue = [
    "Completed assignments may award decoration coins.",
    "These coins can be exchanged for port furnishings in the decoration store.",
    "Purchased decorations are stored in the decoration depot until placed.",
    "Open the decoration store and purchase a bed.",
]
buy_decoration_quest_line = "Purchase a bed from the decoration store."
buy_decoration_post_quest_dialogue = [
    "Purchase complete.",
    "The bed has been added to your decoration depot.",
    "It can now be placed by entering the port's edit mode.",
]

def buy_decoration_completion_criteria(menu_manager: MenuManager) -> bool:
    return DataFiles.save_file["decoration_depot"].get("bed", 0) > 0

def buy_decoration_tutorial_draw(menu_manager: MenuManager, surface: pygame.Surface, font_registry: dict[str, Font]):
    if menu_manager.current_menu != menu_manager.port_menu:
        return

    if menu_manager.port_menu.current_overlay == menu_manager.port_menu.NO_OVERLAY:
        # Point towards the overlay button.
        rect = menu_manager.port_menu.open_decoration_store_overlay_button.rect
        rect = rect.inflate(-Box.WIDTH / 2, -Box.HEIGHT / 2)
        draw_tb(surface, font_registry, None, rect.topright, True, False)
    elif menu_manager.port_menu.current_overlay == menu_manager.port_menu.DECORATION_STORE:
        if DataFiles.save_file["decoration_depot"].get("bed", 0) == 0:
            if menu_manager.port_menu.overlay_selected_entity != "bed":
                # Point towards the bed entry in the decoration sctore.
                rect = menu_manager.port_menu.warehouse_icons[0]
                rect = rect.inflate(-Box.WIDTH / 2, -Box.HEIGHT / 2)
                draw_tb(surface, font_registry, "buy a bed", rect.bottomright, False, False)
            elif menu_manager.port_menu.decoration_signature_button.active:
                # Point towards the signature action button.
                rect = menu_manager.port_menu.decoration_signature_button.rect
                rect = rect.inflate(-Box.WIDTH / 2, -Box.HEIGHT / 2)
                draw_tb(surface, font_registry, None, rect.bottomright, False, False)
        else:
            # Point outside of the overlay.
            point = menu_manager.port_menu.warehouse_overlay.bottomright + pygame.Vector2(-32, 64)
            draw_tb(surface, font_registry, "exit the decoration store", point, True, True)

def buy_decoration_on_start(menu_manager: MenuManager):
    menu_manager.port_menu.open_decoration_store_overlay_button.active = True

def buy_decoration_on_complete(menu_manager: MenuManager):
    assign_quest(menu_manager, decorate_port_quest)

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
    "The new bed is ready to be placed.",
    "In edit mode, decorations can be positioned, flipped horizontally, or returned to the depot.",
    "Some decorations also support interactions with shipgirls.",
    "Practice each editing function with the bed, then assign a shipgirl to rest on it.",
]
decorate_port_quest_line = "Arrange a bed in the port and assign a shipgirl to rest on it."
decorate_port_post_quest_dialogue = [
    "Decoration setup complete.",
    "The bed is placed and its interaction point is functioning correctly.",
    "You can return to edit mode at any time to revise the port layout.",
    "Additional furnishings are available from the decoration store.",
]

def decorate_port_completion_criteria(menu_manager: MenuManager) -> bool:
    port_menu = menu_manager.port_menu
    return (
        port_menu.moved_decoration_depot_overlay
        and port_menu.flipped_decoration
        and port_menu.placed_bed_decoration
        and port_menu.removed_bed_decoration
        and port_menu.shipgirl_interacted_with_bed
        and _decorate_port_get_placed_bed_data() is not None
        and _decorate_port_get_interacting_shipgirl_on_bed(menu_manager) is not None
        and not port_menu.is_decorating
    )

def _decorate_port_get_depot_decoration_rect(port_menu: PortMenu, target_decoration: str) -> pygame.Rect | None:
    """Get the decoration depot slot of the target decoration."""
    decoration_index = 0
    for decoration, amt in DataFiles.save_file["decoration_depot"].items():
        if amt <= 0:
            continue
        rect = get_rect(
            width=Box.WIDTH, height=Box.HEIGHT,
            left=port_menu.decoration_depot_overlay.left + (decoration_index % 3) * (Box.WIDTH + Box.PADDING) + Box.PADDING,
            top=port_menu.decoration_depot_overlay.top + (decoration_index // 3) * (Box.HEIGHT + Box.PADDING) + Box.PADDING
        )
        if decoration == target_decoration:
            return rect
        decoration_index += 1
    return None

def _decorate_port_get_delete_rect(port_menu: PortMenu) -> pygame.Rect:
    """Get the deletion action button."""
    decoration_index = sum(
        1 for amt in DataFiles.save_file["decoration_depot"].values()
        if amt > 0
    )
    return get_rect(
        width=Box.WIDTH, height=Box.HEIGHT,
        left=port_menu.decoration_depot_overlay.left + (decoration_index % 3) * (Box.WIDTH + Box.PADDING) + Box.PADDING,
        top=port_menu.decoration_depot_overlay.top + (decoration_index // 3) * (Box.HEIGHT + Box.PADDING) + Box.PADDING
    )

def _decorate_port_get_placed_bed_data() -> tuple[str, CoordinateType, bool] | None:
    """Get the decoration data of the first placed bed."""
    for decoration_data in DataFiles.save_file["decorations"]:
        decoration, _, _ = Decorations.unpack_decoration_data(decoration_data)
        if decoration == "bed":
            return decoration_data
    return None

def _decorate_port_get_placed_bed_rect() -> pygame.Rect:
    """Get the bounding box of the first placed bed."""
    decoration_data = _decorate_port_get_placed_bed_data()
    if decoration_data is None:
        return None

    decoration, tilepos_anchor, flipped = Decorations.unpack_decoration_data(decoration_data)
    return Decorations.get_decoration_sprite_rect(decoration, flipped, tilepos_anchor)

def _decorate_port_get_interacting_shipgirl_on_bed(menu_manager: MenuManager) -> Shipgirl | None:
    """Get the shipgirl that is interacting with the first placed bed."""
    decoration_data = _decorate_port_get_placed_bed_data()
    if decoration_data is None:
        return None

    _, tilepos_anchor, _ = Decorations.unpack_decoration_data(decoration_data)
    bed_anchor = tuple(tilepos_anchor)
    return next(
        (
            shipgirl for shipgirl in menu_manager.available_shipgirls
            if shipgirl.interacting_decoration == bed_anchor
        ),
        None
    )

def _decorate_port_draw_bed_depot_item(
    menu_manager: MenuManager, surface: pygame.Surface, font_registry: dict[str, Font], text: str
):
    """Draw a pointer towards the first placed bed bounding rect."""
    rect = _decorate_port_get_depot_decoration_rect(menu_manager.port_menu, "bed").inflate(-Box.WIDTH / 2, -Box.HEIGHT / 2)
    if rect is None:
        draw_tb(surface, font_registry, text, pygame.mouse.get_pos(), False, False)
        return
    draw_tb(
        surface, font_registry,
        text,
        rect.bottomright,
        False, False
    )

def decorate_port_tutorial_draw(menu_manager: MenuManager, surface: pygame.Surface, font_registry: dict[str, Font]):
    if menu_manager.current_menu != menu_manager.port_menu:
        return

    port_menu = menu_manager.port_menu
    if not port_menu.is_decorating:
        if port_menu.current_overlay != port_menu.NO_OVERLAY:
            return
        # Point towards the overlay button.
        rect = port_menu.toggle_decoration_mode_button.rect
        rect = rect.inflate(-Box.WIDTH / 2, -Box.HEIGHT / 2)
        draw_tb(surface, font_registry, None, rect.bottomleft, False, True)
        return

    if not port_menu.moved_decoration_depot_overlay:
        # Drag decoration depot tutorial.
        rect = port_menu.decoration_depot_overlay
        rect = rect.inflate(-Box.WIDTH / 2, 0)
        draw_tb(
            surface, font_registry,
            "drag the decoration inventory if it is in the way",
            rect.midright,
            False, False
        )
        return

    if not port_menu.placed_bed_decoration:
        if port_menu.selected_decoration_in_depot != "bed":
            # Tell player to select the bed from their depot.
            _decorate_port_draw_bed_depot_item(
                menu_manager, surface, font_registry,
                "pick the bed from your depot"
            )
        elif not port_menu.flipped_decoration:
            # Tell the player to flip the bed.
            draw_tb(
                surface, font_registry,
                "right click to flip the bed",
                pygame.mouse.get_pos(),
                False, False
            )
        else:
            # Tell the player to place down the bed.
            draw_tb(
                surface, font_registry,
                "left click an open tile to place the bed",
                pygame.mouse.get_pos(),
                False, False
            )
        return

    if not port_menu.removed_bed_decoration:
        if not port_menu.deleting_decoration:
            # Tell player to select the removal tool.
            rect = _decorate_port_get_delete_rect(port_menu)
            rect = rect.inflate(-Box.WIDTH / 2, -Box.HEIGHT / 2)
            draw_tb(
                surface, font_registry,
                "use this to remove the placed bed",
                rect.bottomright,
                False, False
            )
        else:
            # Tell player to remove the bed they placed down.
            rect = _decorate_port_get_placed_bed_rect()
            rect = rect.inflate(-Box.WIDTH, -Box.HEIGHT)
            if rect is not None:
                draw_tb(
                    surface, font_registry,
                    "click the bed to return it to the depot",
                    rect.bottomright,
                    False, False
                )
        return

    if _decorate_port_get_placed_bed_data() is None:
        # Tell the player to pick the bed and place it down again.
        if port_menu.selected_decoration_in_depot != "bed":
            _decorate_port_draw_bed_depot_item(
                menu_manager, surface, font_registry,
                "pick the bed again"
            )
        else:
            draw_tb(
                surface, font_registry,
                "place the bed again",
                pygame.mouse.get_pos(),
                False, False
            )
        return

    if port_menu.selected_decoration_in_depot is not None:
        # Tell the player to deselect the decoration they are currently selecting. 
        rect = _decorate_port_get_depot_decoration_rect(
            port_menu,
            port_menu.selected_decoration_in_depot
        )
        rect = rect.inflate(-Box.WIDTH / 2, -Box.HEIGHT / 2)
        if rect is not None:
            draw_tb(
                surface, font_registry,
                "deselect the decoration",
                rect.bottomright,
                False, False
            )
        else:
            draw_tb(
                surface, font_registry,
                "deselect the decoration",
                pygame.mouse.get_pos(),
                False, False
            )
        return

    if port_menu.deleting_decoration:
        # Tell the player to deselect the removal tool.
        rect = _decorate_port_get_delete_rect(port_menu)
        rect = rect.inflate(-Box.WIDTH / 2, -Box.HEIGHT / 2)
        draw_tb(
            surface, font_registry,
            "deselect the removal tool",
            rect.bottomright,
            False, False
        )

    if _decorate_port_get_interacting_shipgirl_on_bed(menu_manager) is None:
        # Tell the player to pickup a shipgirl and drop her on the bed.
        shipgirl = menu_manager.available_shipgirls[0]
        rect = shipgirl.rect
        rect = rect.inflate(-Box.WIDTH, -Box.HEIGHT)
        if port_menu.dragged_shipgirl is None:
            draw_tb(
                surface, font_registry,
                "pickup a shipgirl",
                rect.topright,
                True, False
            )
        else:
            draw_tb(
                surface, font_registry,
                "drop her onto the bed",
                pygame.mouse.get_pos(),
                False, False
            )
        return

    # Tell the player to exit decoration mode.
    rect = port_menu.toggle_decoration_mode_button.rect
    rect = rect.inflate(-Box.WIDTH / 2, -Box.HEIGHT / 2)
    draw_tb(surface, font_registry, "exit edit mode", rect.bottomleft, False, True)

def decorate_port_on_start(menu_manager: MenuManager):
    port_menu = menu_manager.port_menu
    # Reset tutorial state.
    port_menu.toggle_decoration_mode_button.active = True
    port_menu.moved_decoration_depot_overlay = False
    port_menu.flipped_decoration = False
    port_menu.placed_bed_decoration = False
    port_menu.removed_bed_decoration = False
    port_menu.shipgirl_interacted_with_bed = False

def decorate_port_on_complete(menu_manager: MenuManager):
    assign_quest(menu_manager, construct_additional_shipgirls_quest)
    assign_quest(menu_manager, construct_additional_weapons_quest)

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

def _owned_equipment(equipment: str) -> int:
    """Check the number of this equipment the player owns."""
    return (
        DataFiles.save_file["equipment"].get(equipment, 0)
        + sum(
            shipgirl_data["equipment"].count(equipment)
            for shipgirl_data in DataFiles.save_file["shipgirls"].values()
        )
    )

construct_additional_shipgirls_pre_quest_dialogue = [
    "Operations in the next maritime region will require a more versatile fleet.",
    "Upcoming sorties will provide the materials needed to initiate three additional research projects.",
    "Each project will also require combat data before its unique construction item can be synthesized.",
    "As resources become available, research and construct {CL_shipgirl}, {SS_shipgirl}, and {CV_shipgirl}.",
]
construct_additional_shipgirls_quest_line = (
    "Research and construct {CL_shipgirl}, {SS_shipgirl}, and {CV_shipgirl}."
)
construct_additional_shipgirls_post_quest_dialogue = [
    "Fleet expansion complete.",
    "{CL_shipgirl}, {SS_shipgirl}, and {CV_shipgirl} are now registered to your fleet.",
    "Your available hull types now support a broader range of fleet compositions.",
]

def construct_additional_shipgirls_completion_criteria(menu_manager: MenuManager) -> bool:
    faction_shipgirls = DataFiles.get_faction_shipgirls()
    return all(
        faction_shipgirls[hull_type] in DataFiles.save_file["shipgirls"]
        for hull_type in ["CL", "SS", "CV"]
    )

def construct_additional_shipgirls_on_start(menu_manager: MenuManager):
    menu_manager.port_menu.open_shipyard_overlay_button.active = True

def construct_additional_shipgirls_on_complete(menu_manager: MenuManager):
    pass

construct_additional_shipgirls_quest = Quest(
    "construct_additional_shipgirls",
    construct_additional_shipgirls_pre_quest_dialogue,
    construct_additional_shipgirls_quest_line,
    construct_additional_shipgirls_post_quest_dialogue,
    construct_additional_shipgirls_completion_criteria,
    empty_tutorial_draw,
    construct_additional_shipgirls_on_start,
    construct_additional_shipgirls_on_complete,
    decoration_voucher_reward
)

construct_additional_weapons_pre_quest_dialogue = [
    "Sorties in the next maritime region will provide blueprints and materials for additional weapon classes.",
    "The gear lab can produce new weapons for {BB_shipgirl}, {CA_shipgirl}, {CL_shipgirl}, {SS_shipgirl}, and {CV_shipgirl}.",
    "Construct one weapon for each of these five hull types as the required materials are recovered.",
]
construct_additional_weapons_quest_line = (
    "Construct weapons for {BB_shipgirl}, {CA_shipgirl}, {CL_shipgirl}, {SS_shipgirl}, and {CV_shipgirl}."
)
construct_additional_weapons_post_quest_dialogue = [
    "Weapon production objectives complete.",
    "The gear lab has produced a weapon for every currently supported hull type.",
    "Assign each weapon according to the hull type listed in its equipment record.",
]

def construct_additional_weapons_completion_criteria(menu_manager: MenuManager) -> bool:
    required_hull_types = {"DD", "BB", "CA", "CL", "SS", "CV"}
    required_weapons = [
        equipment for equipment, equipment_data in DataFiles.equipment_data.items()
        if equipment_data["type"] == Equipment.WEAPON_KEY
        and equipment_data["equippable_by"] in required_hull_types
    ]
    return all(_owned_equipment(equipment) >= 1 for equipment in required_weapons)

def construct_additional_weapons_on_start(menu_manager: MenuManager):
    menu_manager.port_menu.open_gear_lab_overlay_button.active = True

def construct_additional_weapons_on_complete(menu_manager: MenuManager):
    pass

construct_additional_weapons_quest = Quest(
    "construct_additional_weapons",
    construct_additional_weapons_pre_quest_dialogue,
    construct_additional_weapons_quest_line,
    construct_additional_weapons_post_quest_dialogue,
    construct_additional_weapons_completion_criteria,
    empty_tutorial_draw,
    construct_additional_weapons_on_start,
    construct_additional_weapons_on_complete,
    decoration_voucher_reward
)

construct_auxiliary_equipment_pre_quest_dialogue = [
    "Operations in the next maritime region are expected to place greater demands on every fleet role.",
    "Auxiliary equipment can improve attributes such as durability, evasion, firepower, and reload speed.",
    "Materials recovered throughout the operation will be sufficient to produce every auxiliary equipment design.",
    "Construct one of each auxiliary equipment item in the gear lab.",
]
construct_auxiliary_equipment_quest_line = (
    "Construct one of every auxiliary equipment item in the gear lab."
)
construct_auxiliary_equipment_post_quest_dialogue = [
    "Auxiliary equipment production complete.",
    "All current auxiliary designs are now available for fleet loadouts.",
    "Distribute them according to the attributes required by each shipgirl.",
]

def construct_auxiliary_equipment_completion_criteria(menu_manager: MenuManager) -> bool:
    auxiliary_equipment = [
        equipment for equipment, equipment_data in DataFiles.equipment_data.items()
        if equipment_data["type"] == Equipment.AUX_KEY
    ]
    return all(_owned_equipment(equipment) >= 2 for equipment in auxiliary_equipment)

def construct_auxiliary_equipment_on_start(menu_manager: MenuManager):
    menu_manager.port_menu.open_gear_lab_overlay_button.active = True

def construct_auxiliary_equipment_on_complete(menu_manager: MenuManager):
    pass

construct_auxiliary_equipment_quest = Quest(
    "construct_auxiliary_equipment",
    construct_auxiliary_equipment_pre_quest_dialogue,
    construct_auxiliary_equipment_quest_line,
    construct_auxiliary_equipment_post_quest_dialogue,
    construct_auxiliary_equipment_completion_criteria,
    empty_tutorial_draw,
    construct_auxiliary_equipment_on_start,
    construct_auxiliary_equipment_on_complete,
    decoration_voucher_reward
)

complete_final_sortie_pre_quest_dialogue = [
    "The final accessible sector has been unlocked.",
    "Siren resistance in this area exceeds all previously recorded encounters.",
    "Review fleet composition and equipment before deployment.",
    "Complete the final sortie and secure the remaining operational area.",
]
complete_final_sortie_quest_line = "Complete the final available sortie."
complete_final_sortie_post_quest_dialogue = [
    "Final sortie complete.",
    "All currently accessible ocean sectors have been secured.",
    "Continue developing the fleet in preparation for future operations.",
]

def complete_final_sortie_completion_criteria(menu_manager: MenuManager) -> bool:
    # The last sortie data entry is an inaccessible development dummy. The
    # accessible final sortie is complete when progress reaches its index.
    return DataFiles.save_file["sortie_progress"] >= len(DataFiles.sortie_data) - 1

def complete_final_sortie_on_start(menu_manager: MenuManager):
    menu_manager.port_menu.open_select_sortie_menu_button.active = True

def complete_final_sortie_on_complete(menu_manager: MenuManager):
    pass

complete_final_sortie_quest = Quest(
    "complete_final_sortie",
    complete_final_sortie_pre_quest_dialogue,
    complete_final_sortie_quest_line,
    complete_final_sortie_post_quest_dialogue,
    complete_final_sortie_completion_criteria,
    empty_tutorial_draw,
    complete_final_sortie_on_start,
    complete_final_sortie_on_complete,
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
    clear_first_maritime_region_quest,
    buy_decoration_quest,
    decorate_port_quest,
    construct_additional_shipgirls_quest,
    construct_additional_weapons_quest,
    construct_auxiliary_equipment_quest,
    complete_final_sortie_quest,
]
