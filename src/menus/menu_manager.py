from src.constants import DataFiles
from src.shipgirls import Shipgirl, PlayerFleet, SirenFleet

from src.menus.port_menu import PortMenu
from src.menus.equipment_menu import EquipmentMenu
from src.menus.sortie_selection_menu import SortieSelectionMenu
from src.menus.fleet_selection_menu import FleetSelectionMenu
from src.menus.encounter_menu import EncounterMenu
from src.menus.quests import QuestManager
from src.menus.quests_data import quests

class MenuManager:
    PORT = 0
    EQUIPMENT = 1
    SORTIE_SELECTION = 2
    FLEET_SELECTION = 3
    ENCOUNTER = 4

    def __init__(self):
        self.player_fleet = PlayerFleet()
        self.siren_fleet = SirenFleet()

        self.available_shipgirls = [Shipgirl(shipgirl_name, True) for shipgirl_name in DataFiles.save_file["shipgirls"]]

        self.menu_register = {
            self.PORT: PortMenu(self),
            self.EQUIPMENT: EquipmentMenu(self),
            self.SORTIE_SELECTION: SortieSelectionMenu(self),
            self.FLEET_SELECTION: FleetSelectionMenu(self),
            self.ENCOUNTER: EncounterMenu(self),
        }
        self.current_menu = self.port_menu

        self.quest_manager = QuestManager()
        for quest in quests:
            quest_id = quest.quest_id
            if quest_id not in DataFiles.save_file["quests"]:
                continue

            quest_progress = DataFiles.save_file["quests"][quest_id]
            if quest_progress == self.quest_manager.STATUS_NEW:
                self.quest_manager.quests[quest_id] = quest
            elif quest_progress == self.quest_manager.STATUS_ACTIVE:
                # The quest being in progress means its briefing was already
                # accepted, even though individual dialogue pages are not
                # persisted. Resume at the objective page so a later
                # completion cannot be hidden behind stale briefing dialogue.
                quest.pre_quest_dialogue_index = len(quest.pre_quest_dialogue)
                quest.pre_quest_finished = True
                quest.started = True
                quest.on_start(self)
                self.quest_manager.quests[quest_id] = quest
            elif quest_progress == self.quest_manager.STATUS_COMPLETE:
                quest.started = True
                quest.on_start(self)
                quest.completed = True
                quest.on_complete(self, save_file_load=True)
                self.quest_manager.quests.pop(quest_id, None)

    @property
    def port_menu(self):
        return self.menu_register[self.PORT]

    @property
    def equipment_menu(self):
        return self.menu_register[self.EQUIPMENT]
    
    @property
    def sortie_selection_menu(self):
        return self.menu_register[self.SORTIE_SELECTION]
    
    @property
    def fleet_selection_menu(self):
        return self.menu_register[self.FLEET_SELECTION]
    
    @property
    def encounter_menu(self):
        return self.menu_register[self.ENCOUNTER]

    @property
    def current_menu(self):
        return self._current_menu

    @current_menu.setter
    def current_menu(self, menu):
        if menu is self.port_menu:
            self.port_menu.restore_shipgirl_decoration_interactions()
        if menu is self.fleet_selection_menu:
            if self.fleet_selection_menu.sortie_index < 0:
                return
            self.fleet_selection_menu.generate_path()
            self.fleet_selection_menu.header_ribbon.text = (
                f"sector {self.fleet_selection_menu.sortie_index + 1:02d}"
            )
        self._current_menu = menu
