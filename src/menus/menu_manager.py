from engine.util import get_rect

from src.constants import DataFiles, Box, screen_x, screen_y
from src.shipgirls import Shipgirl, PlayerFleet, SirenFleet

from src.menus.port_menu import PortMenu
from src.menus.equipment_menu import EquipmentMenu
from src.menus.sortie_selection_menu import SortieSelectionMenu
from src.menus.fleet_selection_menu import FleetSelectionMenu
from src.menus.encounter_menu import EncounterMenu
from src.menus.background import Background
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

        self.background = Background()

        self.quest_manager = QuestManager()
        for quest in quests:
            quest_id = quest.quest_id
            if quest_id not in DataFiles.save_file["quests"]:
                continue

            quest_progress = DataFiles.save_file["quests"][quest_id]
            if quest_progress == "new":
                self.quest_manager.quests[quest_id] = quest
            elif quest_progress == "in_progress":
                quest.started = True
                quest.on_start(self)
                self.quest_manager.quests[quest_id] = quest
            elif quest_progress == "completed":
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