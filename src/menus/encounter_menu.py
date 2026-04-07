import math
import random
import pygame

from engine.util import get_rect, get_vec
from engine.button import Button

from src.constants import DataFiles, Color, Box, RIGHT_OF_SCREEN, TOP_OF_SCREEN, screen_x, screen_y
from src.shipgirls import Shipgirl

class Drop:
    def __init__(self, item, pos, vel):
        self.item = item
        self.pos = pos
        self.vel = vel

    def update(self, dt):
        bottom = screen_y(0.6)
        if self.pos.y < bottom:
            self.pos = self.pos + self.vel * dt
            self.pos.y = min(self.pos.y, bottom)
            self.vel = self.vel + pygame.Vector2(0, 200) * dt
    
    def draw(self, surface, font):
        if self.item in DataFiles.sprites:
            image = DataFiles.sprites[self.item]
            rect = image.get_rect()
            rect.center = self.pos
            surface.blit(image, rect)
        else:
            rect = get_rect(width=Box.WIDTH, height=Box.HEIGHT, centerx=self.pos.x, centery=self.pos.y)
            pygame.draw.rect(surface, Color.WHITE, rect, width=Box.OUTLINE_WIDTH)
            font.render(surface, self.item, rect.center, Color.WHITE, 1, style="center", outline_color=Color.BLACK)

class EncounterMenu:
    def __init__(self, menu_manager):
        self.menu_manager = menu_manager

        self.current_sortie = 0
        self.current_encounter = 0
        self.selected_shipgirl = None
        self.encounter_started = False

        def next_encounter():
            self.current_encounter += 1
            self.begin_encounter()

            self.next_encounter_button.active = False

        self.next_encounter_button = Button(
            rect=get_rect(width=Box.WIDTH, height=Box.HEIGHT, right=RIGHT_OF_SCREEN, centery=screen_y(0.5)),
            color=Color.BLUE_GREY,
            text="next",
            text_color=Color.WHITE,
            callback=next_encounter,
            active=False
        )

        def return_to_port():
            new_sortie_progress = self.current_sortie + 1
            if DataFiles.save_file["sortie_progress"] < new_sortie_progress:
                DataFiles.save_file["sortie_progress"] = new_sortie_progress
            
            for sortie_node in self.menu_manager.sortie_selection_menu.sortie_nodes:
                if sortie_node.index <= DataFiles.save_file["sortie_progress"]:
                    sortie_node.unlocked = True
            self.menu_manager.port_menu.update_encountered_sirens()
            
            for drop in self.drops:
                DataFiles.save_file["inventory"][drop.item] = DataFiles.save_file["inventory"].get(drop.item, 0) + 1

            self.menu_manager.current_menu = self.menu_manager.port_menu

            self.menu_manager.encounter_menu.return_to_port_button.active = False

        self.return_to_port_button = Button(
            rect=get_rect(width=Box.WIDTH, height=Box.HEIGHT, right=RIGHT_OF_SCREEN, centery=screen_y(0.5)),
            color=Color.BLUE_GREY,
            text="back to port",
            text_color=Color.WHITE,
            callback=return_to_port,
            active=False
        )

        def retreat():
            self.menu_manager.current_menu = self.menu_manager.port_menu

            self.menu_manager.player_fleet.end_encounter()        
        
        self.retreat_button = Button(
            rect=get_rect(width=2*Box.WIDTH, height=Box.HEIGHT, right=RIGHT_OF_SCREEN, top=TOP_OF_SCREEN),
            color=Color.BLUE_GREY,
            text="retreat",
            text_color=Color.WHITE,
            callback=retreat
        )

        self.end_sortie_text_pos = pygame.Vector2(screen_x(0.5), screen_y(0.25))
        self.encounter_end_flag = True

        self.drops = []

    def begin_sortie(self):
        self.drops = []
        self.begin_encounter()

    def begin_encounter(self):
        encounter_data = DataFiles.sortie_data[self.current_sortie]["encounters"][self.current_encounter]
        self.menu_manager.siren_fleet._front = [Shipgirl(siren_name, False) for siren_name in encounter_data["front"]] # TODO
        self.menu_manager.siren_fleet._back = [Shipgirl(siren_name, False) for siren_name in encounter_data["back"]]
        for siren in self.menu_manager.siren_fleet.fleet:
            if DataFiles.siren_data[siren.name]["target_pref"] == "front":
                siren.facing_left = True
                siren.battle_component.target = self.menu_manager.player_fleet.front
        self.menu_manager.player_fleet.begin_encounter()
        self.menu_manager.siren_fleet.begin_encounter()

        if (
            self.current_encounter == 0
            and "first_sortie" in self.menu_manager.quest_manager.started_quests
        ):
            self.encounter_started = False
        else:
            self.encounter_started = True
        self.next_encounter_button.active = False
        self.return_to_port_button.active = False
        self.retreat_button.active = True
        self.encounter_end_flag = True

    def update(self, dt, events):
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN:
                for shipgirl in self.menu_manager.player_fleet.shipgirls:
                    if (
                        shipgirl is not None
                        and shipgirl.battle_component.active
                        and shipgirl.battle_component.attack_timer <= 0
                        and shipgirl.rect.collidepoint(event.pos)
                    ):
                        self.menu_manager.mouse_start_drag = event.pos
                        self.selected_shipgirl = shipgirl
                        self.selected_shipgirl.battle_component.target = None
            if event.type == pygame.MOUSEBUTTONUP:
                mouse_end_drag = event.pos
                if self.menu_manager.mouse_start_drag is not None and self.selected_shipgirl is not None:
                    for siren in self.menu_manager.siren_fleet.fleet:
                        if siren.rect.collidepoint(mouse_end_drag):
                            if self.selected_shipgirl.battle_component.hull_type in ["DD", "CL"]:
                                if siren in self.menu_manager.siren_fleet.front:
                                    self.selected_shipgirl.battle_component.target = siren
                            else:
                                self.selected_shipgirl.battle_component.target = siren
                            self.selected_shipgirl = None
                self.menu_manager.mouse_start_drag = None
                self.next_encounter_button.click(event.pos)
                self.return_to_port_button.click(event.pos)
                self.retreat_button.click(event.pos)
        
        if self.encounter_started:
            self.menu_manager.player_fleet.update(dt)
            self.menu_manager.siren_fleet.update(dt, self.menu_manager)
            for drop in self.drops:
                drop.update(dt)
        else:
            self.encounter_started = all(
                shipgirl.battle_component.target is not None
                for shipgirl in self.menu_manager.player_fleet.shipgirls
                if shipgirl is not None
            )

        if self.encounter_end_flag:
            if not self.menu_manager.player_fleet.afloat:
                self.encounter_end_flag = False
                self.menu_manager.player_fleet.end_encounter()
                self.menu_manager.siren_fleet.end_encounter()
                self.return_to_port_button.active = True
                self.retreat_button.active = False
            if not self.menu_manager.siren_fleet.afloat:
                self.encounter_end_flag = False
                for siren in self.menu_manager.siren_fleet.fleet:
                    for shipgirl in self.menu_manager.player_fleet.shipgirls:
                        if shipgirl is not None:
                            shipgirl.battle_component.exp += siren.battle_component.exp
                    if DataFiles.save_file["research_target"] is not None:
                        DataFiles.save_file["research_progress"] += siren.battle_component.exp
                
                exp_req = 5 # TODO
                if DataFiles.save_file["research_progress"] >= exp_req:
                    if DataFiles.save_file["research_target"] is not None:
                        unique_item = DataFiles.shipgirl_data[DataFiles.save_file["research_target"]]["unique_item"]
                        DataFiles.save_file["inventory"][unique_item] = 1
                        DataFiles.save_file["research_progress"] -= exp_req

                self.menu_manager.player_fleet.end_encounter()
                self.menu_manager.siren_fleet.end_encounter()
                num_encounters = len(DataFiles.sortie_data[self.current_sortie]["encounters"])
                if self.current_encounter+1 < num_encounters:
                    self.next_encounter_button.active = True
                else:
                    self.return_to_port_button.active = True

                    if self.current_sortie == DataFiles.save_file["sortie_progress"]:
                        rewards = DataFiles.sortie_data[self.current_sortie]["rewards"]
                        for reward in rewards:
                            self.drops.append(Drop(
                                reward,
                                pygame.Vector2(screen_x(0.75), screen_y(0.5)),
                                get_vec(100, math.radians(random.uniform(-15,15)-90))
                            ))
                    # else:
                    #     for siren in self.menu_manager.siren_fleet.fleet:
                    #         drops = DataFiles.siren_data[siren.name]["drops"]
                    #         for drop, drop_probability in drops.items():
                    #             roll = random.random()*100
                    #             if roll > drop_probability:
                    #                 continue
                    #             self.drops.append(Drop(
                    #                 drop,
                    #                 pygame.Vector2(screen_x(0.75), screen_y(0.5)),
                    #                 get_vec(100, math.radians(random.uniform(-15,15)-90))
                    #             ))
                self.retreat_button.active = False

    def draw(self, surface, font):
        self.menu_manager.player_fleet.draw(surface, font)
        self.menu_manager.siren_fleet.draw(surface, font)
        self.next_encounter_button.draw(surface, font)
        self.return_to_port_button.draw(surface, font)
        self.retreat_button.draw(surface, font)

        for drop in self.drops:
            drop.draw(surface, font)
        
        if self.return_to_port_button.active:
            if not self.menu_manager.player_fleet.afloat:
                font.render(surface, "you lose", self.end_sortie_text_pos, Color.WHITE, 1, style="center", outline_color=Color.BLACK)
            elif not self.menu_manager.siren_fleet.afloat:
                font.render(surface, "you win", self.end_sortie_text_pos, Color.WHITE, 1, style="center", outline_color=Color.BLACK)

        mpos = pygame.mouse.get_pos()
        if self.menu_manager.mouse_start_drag is not None:
            pygame.draw.line(surface, Color.WHITE, self.menu_manager.mouse_start_drag, mpos, width=Box.OUTLINE_WIDTH)
            for siren in self.menu_manager.siren_fleet.fleet:
                if siren.rect.collidepoint(mpos):
                    if self.selected_shipgirl.battle_component.hull_type in ["DD", "CL"]:
                        # TODO 
                        if siren in self.menu_manager.siren_fleet.front:
                            pygame.draw.circle(surface, (50,200,50), pygame.Vector2(mpos) + pygame.Vector2(30, 30), 25)
                        else:
                            pygame.draw.circle(surface, (200,50,50), pygame.Vector2(mpos) + pygame.Vector2(30, 30), 25)
                    else:
                        pygame.draw.circle(surface, (50,200,50), pygame.Vector2(mpos) + pygame.Vector2(30, 30), 25)
