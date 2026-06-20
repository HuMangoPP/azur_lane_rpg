import math
import random
import pygame

from engine.util import get_rect, get_vec
from engine.button import Button

from src.constants import DataFiles, Color, Box, Stats, screen_x, screen_y
from src.shipgirls import Shipgirl
from src.vfx import VFXManager
from src.menus.quests_data import (
    first_sortie_quest,
    construct_shipgirl_quest,
    craft_weapon_quest,
    buy_decoration_quest
)

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
        image = DataFiles.get_entity_sprite(self.item)
        rect = image.get_rect()
        rect.center = self.pos
        surface.blit(image, rect)

class EncounterMenu:
    MELEE_SHIPS = ["DD", "CL", "SS"]

    def __init__(self, menu_manager):
        self.menu_manager = menu_manager

        self.mouse_start_drag = None

        self.current_sortie = 0
        self.current_encounter = 0
        self.selected_shipgirl = None
        self.selected_shipgirl_index = None
        self.encounter_started = False
        self.vfx_manager = VFXManager()

        def next_encounter():
            for drop in self.drops:
                DataFiles.save_file["inventory"][drop.item] = DataFiles.save_file["inventory"].get(drop.item, 0) + 1

            self.current_encounter += 1
            self.begin_encounter()

        button_sprite = DataFiles.sprites["user_interface"]["next"]
        button_rect = get_rect(width=48,height=48,right=Box.RIGHT_OF_SCREEN,centery=screen_y(0.5))
        self.next_encounter_button = Button(
            button_rect,
            next_encounter,
            active=False,
            background_styling={
                "background_color": Color.BLACK,
                "background_img": button_sprite,
                "opacity": 160
            }
        )

        def open_reward_cache():
            if self.current_sortie == DataFiles.save_file["sortie_progress"]:
                rewards = DataFiles.sortie_data[self.current_sortie]["rewards"]
                for reward in rewards:
                    self.drops.append(Drop(reward, pygame.Vector2(screen_x(0.75), screen_y(0.5))))

            self.open_reward_cache_button.active = False
            self.return_to_port_button.active = True

            DataFiles.sfx["open"].play()
        
        button_sprite = DataFiles.sprites["user_interface"]["cache"]
        button_rect = button_sprite.get_rect()
        button_rect.center = (screen_x(0.75), screen_y(0.5))
        self.open_reward_cache_button = Button(
            button_rect,
            open_reward_cache,
            active=False,
            background_styling={"background_img": button_sprite}
        )

        def return_to_port():
            new_sortie_progress = self.current_sortie + 1
            if DataFiles.save_file["sortie_progress"] < new_sortie_progress:
                DataFiles.save_file["sortie_progress"] = new_sortie_progress
                if new_sortie_progress == 3:
                    self.menu_manager.quest_manager.quests[craft_weapon_quest.quest_id] = craft_weapon_quest
                    DataFiles.save_file["quests"][craft_weapon_quest.quest_id] = "new"
                if new_sortie_progress == 4:
                    self.menu_manager.quest_manager.quests[buy_decoration_quest.quest_id] = buy_decoration_quest
                    DataFiles.save_file["quests"][buy_decoration_quest.quest_id] = "new"

            new_chapter_progress = DataFiles.sortie_data[new_sortie_progress]["chapter"]
            if DataFiles.save_file["chapter_progress"] < new_chapter_progress:
                DataFiles.save_file["chapter_progress"] = new_chapter_progress
                self.menu_manager.sortie_selection_menu.fogs[new_chapter_progress].disperse = True
            
            self.menu_manager.sortie_selection_menu.sortie_nodes[new_sortie_progress].unlocked = True
            self.menu_manager.sortie_selection_menu.sortie_nodes[self.current_sortie].cleared = True
            self.menu_manager.port_menu.update_encountered_sirens()
            
            for drop in self.drops:
                DataFiles.save_file["inventory"][drop.item] = DataFiles.save_file["inventory"].get(drop.item, 0) + 1

            self.menu_manager.current_menu = self.menu_manager.port_menu
            DataFiles.sfx["waves"].fadeout(3000)
            self.vfx_manager.clear()
            self.fast_forward = False
            self.slow_down = False

            self.menu_manager.encounter_menu.return_to_port_button.active = False

        button_sprite = DataFiles.sprites["user_interface"]["port"]
        button_rect = get_rect(width=48,height=48,centerx=screen_x(0.5),centery=screen_y(0.75))
        self.return_to_port_button = Button(
            button_rect,
            return_to_port,
            active=False,
            background_styling={
                "background_color": Color.BLACK,
                "background_img": button_sprite,
                "opacity": 160
            }
        )

        def retreat():
            self.menu_manager.current_menu = self.menu_manager.port_menu
            DataFiles.sfx["waves"].fadeout(3000)

            self.menu_manager.player_fleet.end_encounter()        
            self.menu_manager.siren_fleet.end_encounter()
            self.vfx_manager.clear()
            self.fast_forward = False
            self.slow_down = False

        
        button_sprite = DataFiles.sprites["user_interface"]["port"]
        button_rect = get_rect(width=48,height=48,right=Box.RIGHT_OF_SCREEN,top=Box.TOP_OF_SCREEN)
        self.retreat_button = Button(
            button_rect,
            retreat,
            background_styling={
                "background_color": Color.BLACK,
                "background_img": button_sprite,
                "opacity": 160
            }
        )

        self.end_sortie_text_pos = pygame.Vector2(screen_x(0.5), screen_y(0.25))
        self.encounter_end_flag = True

        self.drops = []
        self.research_exp = 0
        self.exp_timer = 0

        self.fast_forward = False
        self.slow_down = False

    def begin_sortie(self):
        self.open_reward_cache_button.active = False
        self.return_to_port_button.active = False

        self.begin_encounter()

    def begin_encounter(self):
        self.drops = []
        self.next_encounter_button.active = False
        self.vfx_manager.clear()

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
            siren.facing_left = True
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
                click = False
                # drag shipgirl onto siren target
                if self.selected_shipgirl is not None:
                    for siren in self.menu_manager.siren_fleet.fleet:
                        if not siren.rect.collidepoint(mouse_end_drag):
                            continue
                        click = True
                        if self.selected_shipgirl.battle_component.hull_type in self.MELEE_SHIPS:
                            if siren in self.menu_manager.siren_fleet.front:
                                self.selected_shipgirl.battle_component.target = siren
                        else:
                            self.selected_shipgirl.battle_component.target = siren
                        self.selected_shipgirl = None
                        self.selected_shipgirl_index = None
                # drag shipgirl onto backup shipgirl
                if self.selected_shipgirl is not None:
                    for i, backup_shipgirl in enumerate(self.menu_manager.player_fleet.backups):
                        if backup_shipgirl is None:
                            continue
                        if not backup_shipgirl.rect.collidepoint(mouse_end_drag):
                            continue
                        click = True
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
                        if siren.battle_component.target == self.selected_shipgirl:
                            siren.battle_component.target = None

                    self.selected_shipgirl = None
                    self.selected_shipgirl_index = None
                self.mouse_start_drag = None

                click = (
                    click
                    or self.next_encounter_button.click(event.pos)
                    or self.open_reward_cache_button.click(event.pos)
                    or self.return_to_port_button.click(event.pos)
                    or self.retreat_button.click(event.pos)
                )

                if click:
                    DataFiles.sfx["click"].play()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_f:
                    self.fast_forward = not self.fast_forward
                if event.key == pygame.K_d:
                    self.slow_down = not self.slow_down
        
        if self.fast_forward:
            dt = dt * 2
        if self.slow_down:
            dt = dt / 5
        if self.encounter_started:
            afloat_sirens_before = [siren for siren in self.menu_manager.siren_fleet.fleet if siren.battle_component.hp > 0]
            self.menu_manager.player_fleet.update(dt, self.vfx_manager)
            afloat_sirens_after = [siren for siren in self.menu_manager.siren_fleet.fleet if siren.battle_component.hp > 0]
            if self.current_sortie < DataFiles.save_file["sortie_progress"]:
                defeated_sirens = [siren for siren in afloat_sirens_before if siren not in afloat_sirens_after]
                for siren in defeated_sirens:
                    siren_data = DataFiles.siren_data[siren.name]
                    for drop, drop_rate in siren_data["drops"].items():
                        drop_roll = random.random() * 100
                        if drop_roll < drop_rate:
                            self.drops.append(Drop(drop, pygame.Vector2(siren.rect.center)))
            self.menu_manager.siren_fleet.update(dt, self.menu_manager, self.vfx_manager)

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
                    if DataFiles.save_file["research_target"] == DataFiles.get_faction_shipgirls()["CA"]:
                        self.menu_manager.quest_manager.quests[construct_shipgirl_quest.quest_id] = construct_shipgirl_quest
                        DataFiles.save_file["quests"][construct_shipgirl_quest.quest_id] = "new"

                    unique_item = DataFiles.shipgirl_data[DataFiles.save_file["research_target"]]["unique_item"]
                    DataFiles.save_file["research_progress"] = 0
                    self.drops.append(Drop(unique_item, pygame.Vector2(screen_x(0.5), screen_y(0.5))))
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
                            shipgirl.battle_component.exp += Stats.stat(
                                siren.battle_component.exp,
                                *DataFiles.siren_data[siren.name]["reward_exp"]
                            )
                    if DataFiles.save_file["research_target"] is not None:
                        self.research_exp += siren.battle_component.exp

                self.menu_manager.player_fleet.end_encounter()
                self.menu_manager.siren_fleet.end_encounter()
                self.next_encounter_button.active = True
                self.retreat_button.active = False

        self.vfx_manager.update(dt)
        self.menu_manager.background.update(dt)

    def draw(self, surface, font):
        self.menu_manager.background.draw(surface, font, player_fleet=self.menu_manager.player_fleet, siren_fleet=self.menu_manager.siren_fleet)

        self.menu_manager.player_fleet.draw_battle_component(surface, font)
        self.menu_manager.siren_fleet.draw_battle_component(surface, font)
        self.vfx_manager.draw(surface)

        self.next_encounter_button.draw(surface, font)
        self.open_reward_cache_button.draw(surface, font)
        self.return_to_port_button.draw(surface, font)
        self.retreat_button.draw(surface, font)

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
            pygame.draw.rect(surface, Color.EXP_BAR_BG, bar_background)
            pygame.draw.rect(surface, Color.EXP_BAR_FILL, bar_fill)
            banner_text = "shipgirl research progress"
            banner_surf = pygame.Surface((
                len(banner_text)*font.font_width + 2*Box.PADDING,
                font.font_height + 2*Box.PADDING
            ))
            banner_surf.fill(Color.BLACK)
            banner_surf.set_alpha(160)
            banner_rect = banner_surf.get_rect()
            banner_rect.centerx = bar_background.centerx
            banner_rect.bottom = bar_background.top - Box.PADDING
            surface.blit(banner_surf, banner_rect)
            font.render(
                surface,
                banner_text,
                banner_rect.center,
                Color.WHITE,
                1,
                style="center"
            )
        
        if self.next_encounter_button.active:
            font_size = 2
            if not self.menu_manager.player_fleet.afloat:
                end_text = "you lose"
            elif not self.menu_manager.siren_fleet.afloat:
                end_text = "you win"
            banner_surf = pygame.Surface((
                len(end_text)*font_size*font.font_width + 2*Box.PADDING, 
                font_size*font.font_height + 2*Box.PADDING
            ))
            banner_surf.fill(Color.BLACK)
            banner_surf.set_alpha(160)
            banner_rect = banner_surf.get_rect()
            banner_rect.center = self.end_sortie_text_pos
            surface.blit(banner_surf, banner_rect)
            font.render(surface, end_text, self.end_sortie_text_pos, Color.WHITE, font_size, style="center")

        mpos = pygame.mouse.get_pos()
        if self.mouse_start_drag is not None:
            pygame.draw.line(surface, Color.WHITE, self.mouse_start_drag, mpos, width=Box.OUTLINE_WIDTH)
            for siren in self.menu_manager.siren_fleet.fleet:
                if siren.battle_component.hp <= 0:
                    continue
                if siren.rect.collidepoint(mpos):
                    if self.selected_shipgirl.battle_component.hull_type in self.MELEE_SHIPS:
                        if siren in self.menu_manager.siren_fleet.front: # TODO
                            color = (50,200,50)
                        else:
                            color = (200,50,50)
                    else:
                        color = (50,200,50)
                    
                    inner_radius = 16
                    outer_radius = 32
                    annulus = pygame.Surface((2*outer_radius, 2*outer_radius))
                    annulus.fill((0,0,0))
                    pygame.draw.circle(annulus, color, (outer_radius, outer_radius), outer_radius)
                    pygame.draw.circle(annulus, (0,0,0), (outer_radius, outer_radius), inner_radius)
                    annulus.set_colorkey((0,0,0))
                    annulus_rect = annulus.get_rect()

                    drawpos = pygame.Vector2(mpos) + pygame.Vector2(48)
                    annulus_rect.center = drawpos
                    surface.blit(annulus, annulus_rect)

                    attack_icon = DataFiles.sprites["user_interface"]["attack"]
                    attack_icon_rect = attack_icon.get_rect()
                    attack_icon_rect.center = drawpos
                    surface.blit(attack_icon, attack_icon_rect)
