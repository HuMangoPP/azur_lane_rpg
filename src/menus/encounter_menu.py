import math
import random
import pygame

from engine.util import get_rect, get_vec
from engine.button import Button

from src.constants import DataFiles, Color, Box, Stats, screen_x, screen_y
from src.shipgirls import Shipgirl
from src.menus.quests_data import first_sortie_quest, research_shipgirl_quest, construct_shipgirl_quest, craft_weapon_quest
from src.menus.background import Background

class Drop:
    def __init__(self, item, pos):
        self.item = item
        self.pos = pos
        self.bottom = pos.y + 50
        self.vel = get_vec(100, math.radians(random.uniform(-15,15)-90))

    def update(self, dt):
        if self.pos.y < self.bottom:
            self.pos = self.pos + self.vel * dt
            self.pos.y = min(self.pos.y, self.bottom)
            self.vel = self.vel + pygame.Vector2(0, 200) * dt
    
    def draw(self, surface, font):
        if self.item in DataFiles.sprites["entity"]:
            image = DataFiles.sprites["entity"][self.item]
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

        self.mouse_start_drag = None

        self.current_sortie = 0
        self.current_encounter = 0
        self.selected_shipgirl = None
        self.selected_shipgirl_index = None
        self.encounter_started = False

        def next_encounter():
            for drop in self.drops:
                DataFiles.save_file["inventory"][drop.item] = DataFiles.save_file["inventory"].get(drop.item, 0) + 1

            self.current_encounter += 1
            self.begin_encounter()

        button_sprite = DataFiles.sprites["user_interface"]["next"]
        button_rect = button_sprite.get_rect()
        button_rect.right = Box.RIGHT_OF_SCREEN
        button_rect.centery = screen_y(0.5)
        self.next_encounter_button = Button(rect=button_rect,sprite=button_sprite,callback=next_encounter,active=False)

        def open_reward_cache():
            if self.current_sortie == DataFiles.save_file["sortie_progress"]:
                rewards = DataFiles.sortie_data[self.current_sortie]["rewards"]
                for reward in rewards:
                    self.drops.append(Drop(reward, pygame.Vector2(screen_x(0.75), screen_y(0.5))))

            self.open_reward_cache_button.active = False
            self.return_to_port_button.active = True
        
        button_sprite = DataFiles.sprites["user_interface"]["cache"]
        button_rect = button_sprite.get_rect()
        button_rect.center = (screen_x(0.75), screen_y(0.5))
        self.open_reward_cache_button = Button(rect=button_rect,sprite=button_sprite,callback=open_reward_cache,active=False)

        def return_to_port():
            new_sortie_progress = self.current_sortie + 1
            if DataFiles.save_file["sortie_progress"] < new_sortie_progress:
                DataFiles.save_file["sortie_progress"] = new_sortie_progress
                if new_sortie_progress == 3:
                    self.menu_manager.quest_manager.quests[craft_weapon_quest.quest_id] = craft_weapon_quest
            
            self.menu_manager.sortie_selection_menu.sortie_nodes[new_sortie_progress].unlocked = True
            self.menu_manager.sortie_selection_menu.sortie_nodes[self.current_sortie].cleared = True
            self.menu_manager.port_menu.update_encountered_sirens()
            
            for drop in self.drops:
                DataFiles.save_file["inventory"][drop.item] = DataFiles.save_file["inventory"].get(drop.item, 0) + 1

            self.menu_manager.current_menu = self.menu_manager.port_menu

            self.menu_manager.encounter_menu.return_to_port_button.active = False

        button_sprite = DataFiles.sprites["user_interface"]["port"]
        button_rect = button_sprite.get_rect()
        button_rect.center = (screen_x(0.5), screen_y(0.75))
        self.return_to_port_button = Button(rect=button_rect,sprite=button_sprite,callback=return_to_port,active=False)

        def retreat():
            self.menu_manager.current_menu = self.menu_manager.port_menu

            self.menu_manager.player_fleet.end_encounter()        
        
        button_sprite = DataFiles.sprites["user_interface"]["port"]
        button_rect = button_sprite.get_rect()
        button_rect.right = Box.RIGHT_OF_SCREEN
        button_rect.top = Box.TOP_OF_SCREEN
        self.retreat_button = Button(rect=button_rect,sprite=button_sprite,callback=retreat)

        self.end_sortie_text_pos = pygame.Vector2(screen_x(0.5), screen_y(0.25))
        self.encounter_end_flag = True

        self.drops = []
        self.research_exp = 0
        self.exp_timer = 0

        self.background = Background()

    def begin_sortie(self):
        self.open_reward_cache_button.active = False
        self.return_to_port_button.active = False

        self.begin_encounter()

    def begin_encounter(self):
        self.drops = []
        self.next_encounter_button.active = False

        sortie_data = DataFiles.sortie_data[self.current_sortie]
        num_encounters = len(sortie_data["encounters"])
        if self.current_encounter == num_encounters:
            if self.current_sortie < DataFiles.save_file["sortie_progress"]:
                self.return_to_port_button.active = True
            else:
                self.open_reward_cache_button.active = True

            self.menu_manager.siren_fleet._front = []
            self.menu_manager.siren_fleet._back = []
            return
        
        self.encounter_end_flag = True
        self.retreat_button.active = True

        encounter_data = sortie_data["encounters"][self.current_encounter]
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
            and first_sortie_quest.quest_id in self.menu_manager.quest_manager.started_quests
        ):
            self.encounter_started = False
        else:
            self.encounter_started = True

    def update(self, dt, events):
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN:
                for i, shipgirl in enumerate(self.menu_manager.player_fleet.shipgirls):
                    if (
                        shipgirl is not None
                        and shipgirl.battle_component.active
                        and shipgirl.battle_component.attack_timer <= 0
                        and shipgirl.rect.collidepoint(event.pos)
                    ):
                        self.mouse_start_drag = event.pos
                        self.selected_shipgirl = shipgirl
                        self.selected_shipgirl_index = i
                        self.selected_shipgirl.battle_component.target = None
            if event.type == pygame.MOUSEBUTTONUP:
                mouse_end_drag = event.pos
                if self.selected_shipgirl is not None:
                    for siren in self.menu_manager.siren_fleet.fleet:
                        if not siren.rect.collidepoint(mouse_end_drag):
                            continue
                        if self.selected_shipgirl.battle_component.hull_type in ["DD", "CL"]:
                            if siren in self.menu_manager.siren_fleet.front:
                                self.selected_shipgirl.battle_component.target = siren
                        else:
                            self.selected_shipgirl.battle_component.target = siren
                        self.selected_shipgirl = None
                        self.selected_shipgirl_index = None
                if self.selected_shipgirl is not None:
                    for i, backup_shipgirl in enumerate(self.menu_manager.player_fleet.backups):
                        if backup_shipgirl is None:
                            continue
                        if not backup_shipgirl.rect.collidepoint(mouse_end_drag):
                            continue

                        (
                            self.selected_shipgirl.rect.center,
                            backup_shipgirl.rect.center
                        ) = (
                            backup_shipgirl.rect.center,
                            self.selected_shipgirl.rect.center,
                        )
                        self.selected_shipgirl.battle_component.active = False
                        self.menu_manager.player_fleet.backups[i] = self.selected_shipgirl
                        backup_shipgirl.battle_component.active = True
                        self.menu_manager.player_fleet.shipgirls[self.selected_shipgirl_index] = backup_shipgirl

                        for siren in self.menu_manager.siren_fleet.fleet:
                            if (
                                siren.battle_component.attack_timer <= 0
                                and siren.battle_component.target == self.selected_shipgirl
                            ):
                                siren.battle_component.target = backup_shipgirl

                        self.selected_shipgirl = None
                        self.selected_shipgirl_index = None
                self.mouse_start_drag = None

                self.next_encounter_button.click(event.pos)
                self.open_reward_cache_button.click(event.pos)
                self.return_to_port_button.click(event.pos)
                self.retreat_button.click(event.pos)
        
        if self.encounter_started:
            afloat_sirens_before = [siren for siren in self.menu_manager.siren_fleet.fleet if siren.battle_component.hp > 0]
            self.menu_manager.player_fleet.update(dt)
            afloat_sirens_after = [siren for siren in self.menu_manager.siren_fleet.fleet if siren.battle_component.hp > 0]
            if self.current_sortie < DataFiles.save_file["sortie_progress"]:
                defeated_sirens = [siren for siren in afloat_sirens_before if siren not in afloat_sirens_after]
                for siren in defeated_sirens:
                    siren_data = DataFiles.siren_data[siren.name]
                    for drop, drop_rate in siren_data["drops"].items():
                        drop_roll = random.random() * 100
                        if drop_roll < drop_rate:
                            self.drops.append(Drop(drop, pygame.Vector2(siren.rect.center)))
            self.menu_manager.siren_fleet.update(dt, self.menu_manager)

            for drop in self.drops:
                drop.update(dt)
        else:
            self.encounter_started = all(
                shipgirl.battle_component.target is not None
                for shipgirl in self.menu_manager.player_fleet.shipgirls
                if shipgirl is not None
            )
        
        if self.research_exp > 0:
            self.exp_timer += dt
            if self.exp_timer > 1:
                self.exp_timer = 1
                DataFiles.save_file["research_progress"] += self.research_exp
                num_shipgirls_in_port = len(DataFiles.save_file["shipgirls"])
                exp_req = Stats.RESEARCH_EXP_REQUIREMENTS[num_shipgirls_in_port]
                if DataFiles.save_file["research_progress"] >= exp_req:
                    unique_item = DataFiles.shipgirl_data[DataFiles.save_file["research_target"]]["unique_item"]
                    DataFiles.save_file["research_progress"] = 0
                    self.drops.append(Drop(unique_item, pygame.Vector2(screen_x(0.5), screen_y(0.5))))

                    if (
                        construct_shipgirl_quest.quest_id not in DataFiles.save_file["quests"]
                        and research_shipgirl_quest.completion_criteria(self.menu_manager)
                    ):
                        self.menu_manager.quest_manager.quests[construct_shipgirl_quest.quest_id] = construct_shipgirl_quest
                    DataFiles.save_file["research_target"] = None
                self.research_exp = 0
        elif self.exp_timer > 0:
            self.exp_timer -= dt
            if self.exp_timer < 0:
                self.exp_timer = 0

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
                        self.research_exp += siren.battle_component.exp

                self.menu_manager.player_fleet.end_encounter()
                self.menu_manager.siren_fleet.end_encounter()
                self.next_encounter_button.active = True
                self.retreat_button.active = False

        self.background.update(dt)

    def draw(self, surface, font):
        self.background.draw(surface, font, player_fleet=self.menu_manager.player_fleet, siren_fleet=self.menu_manager.siren_fleet)

        self.next_encounter_button.draw(surface, font)
        self.open_reward_cache_button.draw(surface, font)
        self.return_to_port_button.draw(surface, font)
        self.retreat_button.draw(surface, font)
        self.menu_manager.player_fleet.draw_battle_component(surface, font)
        self.menu_manager.siren_fleet.draw_battle_component(surface, font)

        for drop in self.drops:
            drop.draw(surface, font)
        
        if self.exp_timer > 0:
            bar_width = 256
            bar_height = 16
            bar_background = get_rect(
                width=bar_width, height=bar_height,
                centerx=screen_x(0.5), bottom=Box.BOTTOM_OF_SCREEN
            )
            num_shipgirls_in_port = len(DataFiles.save_file["shipgirls"])
            exp_req = Stats.RESEARCH_EXP_REQUIREMENTS[num_shipgirls_in_port]
            research_progress = DataFiles.save_file["research_progress"] + self.research_exp * self.exp_timer
            bar_fill = get_rect(
                width=bar_width * min(1, research_progress/exp_req),
                height=bar_height, left=bar_background.left, top=bar_background.top 
            )
            pygame.draw.rect(surface, Color.GREY, bar_background)
            pygame.draw.rect(surface, Color.BLUE_GREY, bar_fill)
            font.render(
                surface,
                "shipgirl research progress",
                (bar_background.centerx, bar_background.top - bar_height),
                Color.WHITE,
                1,
                style="center",
                outline_color=Color.BLACK
            )
        
        if self.next_encounter_button.active:
            if not self.menu_manager.player_fleet.afloat:
                font.render(surface, "you lose", self.end_sortie_text_pos, Color.WHITE, 1, style="center", outline_color=Color.BLACK)
            elif not self.menu_manager.siren_fleet.afloat:
                font.render(surface, "you win", self.end_sortie_text_pos, Color.WHITE, 1, style="center", outline_color=Color.BLACK)

        mpos = pygame.mouse.get_pos()
        if self.mouse_start_drag is not None:
            pygame.draw.line(surface, Color.WHITE, self.mouse_start_drag, mpos, width=Box.OUTLINE_WIDTH)
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
