from engine.util import get_rect

from src.constants import DataFiles, Box, screen_x, screen_y
from src.shipgirls import Shipgirl, PlayerFleet, SirenFleet

from src.menus.port_menu import PortMenu
from src.menus.equipment_menu import EquipmentMenu
from src.menus.sortie_selection_menu import SortieSelectionMenu
from src.menus.fleet_selection_menu import FleetSelectionMenu
from src.menus.encounter_menu import EncounterMenu
from src.menus.tutorials import Tutorials


class MenuManager:
    PORT = 0
    EQUIPMENT = 1
    SORTIE_SELECTION = 2
    FLEET_SELECTION = 3
    ENCOUNTER = 4

    def __init__(self):
        self.mouse_start_drag = None

        self.player_fleet = PlayerFleet()
        self.siren_fleet = SirenFleet()

        self.available_shipgirls = [Shipgirl(shipgirl_name, True) for shipgirl_name in DataFiles.save_file["shipgirls"]]
        self.available_shipgirl_rects = [
            get_rect( # TODO
                width=Box.WIDTH, height=Box.HEIGHT,
                centerx=(Box.WIDTH+Box.PADDING)*(i%4-1.5) + screen_x(0.75),
                centery=(Box.HEIGHT+Box.PADDING)*(i//4-1.5) + screen_y(0.5)
            ) for i in range(4)
        ]

        self.menu_register = {
            self.PORT: PortMenu(self),
            self.EQUIPMENT: EquipmentMenu(self),
            self.SORTIE_SELECTION: SortieSelectionMenu(self),
            self.FLEET_SELECTION: FleetSelectionMenu(self),
            self.ENCOUNTER: EncounterMenu(self),
        }
        self.current_menu = self.menu_register[self.PORT]
        
        self.tutorials = Tutorials(self)
        self.tutorial = self.tutorials.start_sortie

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