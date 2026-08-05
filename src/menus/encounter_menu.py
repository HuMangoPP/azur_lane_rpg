import math
import random
import pygame

from engine.util import get_rect, get_vec
from engine.button import Button

from src.constants import DataFiles, Color, Box, Stats, screen_x, screen_y
from src.shipgirls import Shipgirl
from src.vfx import VFXManager
from src.menus.fleet_selection_menu import FleetNameRibbon
from src.menus.quests_data import (
    first_sortie_quest,
    construct_shipgirl_quest,
    craft_weapon_quest,
    buy_decoration_quest
)


class Cloud:
    SHADOW_OFFSET = pygame.Vector2(4, 8)

    def __init__(self, index, x, y, speed):
        self.sprite = DataFiles.sprites["background"][f"cloud{index}"]
        self.shadow = DataFiles.sprites["background"][f"cloud_shadow{index}"]
        self.x = x
        self.y = y
        self.speed = speed

    def update(self, dt):
        self.x = self.x + self.speed * dt

    def draw(self, surface):
        shadow_rect = self.shadow.get_rect()
        shadow_rect.centerx = self.x + self.SHADOW_OFFSET.x
        shadow_rect.top = self.y + self.SHADOW_OFFSET.y
        surface.blit(self.shadow, shadow_rect, special_flags=pygame.BLEND_RGB_SUB)

        rect = self.sprite.get_rect()
        rect.centerx = self.x
        rect.top = self.y
        surface.blit(self.sprite, rect)


class BackgroundProp:
    def __init__(self, sprite_name, x, top, draw_index):
        self.sprite = DataFiles.sprites["background"][sprite_name]
        self.x = x
        self.top = top
        self.draw_index = draw_index

    def draw(self, surface):
        rect = self.sprite.get_rect()
        rect.centerx = self.x
        rect.top = self.top
        surface.blit(self.sprite, rect)


class Background:
    Y_GAP = 48

    def __init__(self, sky_colors, wave_sprites):
        self.set_sky_colors(sky_colors)
        self.wave_sprites = wave_sprites
        num_waves = DataFiles.sprites["background"]["num_waves"]
        self.wave_ys = [
            screen_y(0.5) + self.Y_GAP*(i-num_waves/2) + 8
            for i in range(num_waves)
        ]
        self.wave_timers = [
            math.radians(random.randint(0, 359))
            for _ in range(num_waves)
        ]

        self.cloud_timer = 0
        self.cloud_spawn_time = 0
        self.clouds = []

    def set_sky_colors(self, sky_colors):
        sky_surf = pygame.Surface((1, len(sky_colors)))
        for y, color in enumerate(sky_colors):
            sky_surf.set_at((0, y), color)
        self.sky_surf = pygame.transform.smoothscale(sky_surf, (128, 256))

    def set_wave_sprites(self, weather):
        self.wave_sprites = DataFiles.sprites["background"]["wave_sets"][weather]

    def update(self, dt):
        num_waves = DataFiles.sprites["background"]["num_waves"]
        self.wave_timers = [
            (wave_timer + (i+1)/num_waves*dt)%math.radians(360)
            for i, wave_timer in enumerate(self.wave_timers)
        ]

        for cloud in self.clouds:
            cloud.update(dt)
        self.clouds = [
            cloud for cloud in self.clouds
            if cloud.x >= -128
            and cloud.x <= screen_x(1) + 128
        ]

        self.cloud_timer += dt
        if self.cloud_timer > self.cloud_spawn_time:
            move_right = bool(random.randint(0, 1))
            self.clouds.append(Cloud(
                random.randint(1, DataFiles.sprites["background"]["num_clouds"])-1,
                0 if move_right else screen_x(1),
                random.uniform(-64, 64),
                random.uniform(32, 64) * (1 if move_right else -1)
            ))
            self.cloud_timer = 0
            self.cloud_spawn_time = random.uniform(5, 10)

    def draw(self, surface, font_registry, player_fleet=None, siren_fleet=None):
        sky_surf = self.sky_surf
        sky_surf_rect = sky_surf.get_rect()
        sky_surf_rect.top = 0
        num_sky_reps = 9
        sky_rep_offset = (num_sky_reps-1)/2
        for i in range(num_sky_reps):
            sky_surf_rect.centerx = screen_x(0.5) + sky_surf_rect.width * (i-sky_rep_offset)
            surface.blit(sky_surf, sky_surf_rect)

        for cloud in self.clouds:
            cloud.draw(surface)

        if siren_fleet is not None:
            siren_draw_indices = siren_fleet.get_draw_indices()
        else:
            siren_draw_indices = None

        if player_fleet is not None:
            shipgirl_draw_indices = player_fleet.get_draw_indices()
        else:
            shipgirl_draw_indices = None

        landmark_y = self.wave_ys[0] - 4

        left_landmarks = DataFiles.sprites["background"]["left_landmarks"]
        left_landmarks_rect = left_landmarks.get_rect()
        left_landmarks_rect.left = screen_x(0)
        left_landmarks_rect.centery = landmark_y
        surface.blit(left_landmarks, left_landmarks_rect)

        middle_landmarks = DataFiles.sprites["background"]["middle_landmarks"]
        middle_landmarks_rect = middle_landmarks.get_rect()
        middle_landmarks_rect.centerx = screen_x(0.5)
        middle_landmarks_rect.centery = landmark_y
        surface.blit(middle_landmarks, middle_landmarks_rect)
        
        right_landmarks = DataFiles.sprites["background"]["right_landmarks"]
        right_landmarks_rect = right_landmarks.get_rect()
        right_landmarks_rect.right = screen_x(1)
        right_landmarks_rect.centery = landmark_y
        surface.blit(right_landmarks, right_landmarks_rect)

        num_waves = DataFiles.sprites["background"]["num_waves"]
        num_wave_reps = 5
        wave_rep_offset = (num_wave_reps-1)/2
        for i, (wave_y, wave_timer) in enumerate(zip(self.wave_ys, self.wave_timers)):
            if shipgirl_draw_indices is not None:
                for draw_index, shipgirl in shipgirl_draw_indices:
                    if i == draw_index:
                        shipgirl.draw(surface, font_registry)
                        shipgirl.battle_component.draw_battlestation(surface, font_registry, shipgirl.rect)

            if siren_draw_indices is not None:
                for draw_index, siren in siren_draw_indices:
                    if i == draw_index:
                        siren.draw(surface, font_registry)
                        siren.battle_component.draw_battlestation(surface, font_registry, siren.rect)

            move_amt = i / num_waves
            wave = self.wave_sprites[i]
            wave_rect = wave.get_rect()
            wave_rect.top = wave_y + 4 * (move_amt + 1) * math.sin(2*wave_timer)
            centerx = 64 * (move_amt + 1) * math.sin(wave_timer) + screen_x(0.5)
            for j in range(num_wave_reps):
                wave_rect.centerx = centerx + wave_rect.width * (j-wave_rep_offset)
                surface.blit(wave, wave_rect)

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
    
    def draw(self, surface, font_registry):
        image = DataFiles.get_entity_sprite(self.item)
        rect = image.get_rect()
        rect.center = self.pos
        surface.blit(image, rect)

class EncounterMenu:
    MELEE_SHIPS = ["DD", "CL", "SS"]
    TIME_WEATHER_STYLES = {
        "daytime": {
            "weight": 1,
            "sky_colors": ((89, 150, 227), (150, 197, 255)),
        },
        "nighttime": {
            "weight": 1,
            "sky_colors": ((7, 10, 34), (45, 28, 82)),
        },
        "stormy": {
            "weight": 1,
            "sky_colors": ((40, 57, 83), (82, 95, 111)),
        },
    }

    def __init__(self, menu_manager):
        self.menu_manager = menu_manager

        self.mouse_start_drag = None

        self.time_weather = "daytime"
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
            },
            hover_styling={"opacity": 200}
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
            if self.end_encounter_banner.text == "victory":
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
            },
            hover_styling={"opacity": 200}
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
            },
            hover_styling={"opacity": 200}
        )

        self.end_encounter_banner = FleetNameRibbon(pygame.Vector2(screen_x(0.5), screen_y(0.1)), "")
        self.encounter_end_flag = True

        self.drops = []
        self.research_exp = 0
        self.exp_timer = 0

        self.fast_forward = False
        self.slow_down = False

        slot_size = 96
        num_fleet_slots = 3
        fleet_slot_offset = (num_fleet_slots-1)/2
        self.fleet_slots = [
            get_rect(
                width=slot_size, height=slot_size,
                centerx=screen_x(0.25) + slot_size - (slot_index-fleet_slot_offset)*slot_size/2,
                centery=screen_y(0.5) + (slot_index-fleet_slot_offset)*slot_size
            ) for slot_index in range(num_fleet_slots)
        ]

        self.backup_fleet_slots = [
            get_rect(
                width=slot_size, height=slot_size,
                centerx=slot.centerx - 2*slot_size,
                centery=slot.centery,
            ) for slot in self.fleet_slots
        ]

        self.background = Background(
            self.TIME_WEATHER_STYLES[self.time_weather]["sky_colors"],
            DataFiles.sprites["background"]["wave_sets"][self.time_weather],
        )

    def roll_time_weather(self):
        weather_names = list(self.TIME_WEATHER_STYLES.keys())
        weather_weights = [
            self.TIME_WEATHER_STYLES[weather_name]["weight"]
            for weather_name in weather_names
        ]
        self.time_weather = random.choices(weather_names, weights=weather_weights, k=1)[0]
        self.apply_time_weather_style()

    def apply_time_weather_style(self):
        weather_style = self.TIME_WEATHER_STYLES[self.time_weather]
        self.background.set_sky_colors(weather_style["sky_colors"])
        self.background.set_wave_sprites(self.time_weather)

    def begin_sortie(self):
        self.roll_time_weather()
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
        # TODO update the naming convention
        self.menu_manager.siren_fleet._front = [Shipgirl(siren_name, False) for siren_name in encounter_data["front"]]
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
            if event.type == pygame.MOUSEMOTION:
                self.next_encounter_button.hover(event.pos)
                self.retreat_button.hover(event.pos)
                self.return_to_port_button.hover(event.pos)
            if event.type == pygame.MOUSEBUTTONDOWN:
                for i, shipgirl in enumerate(self.menu_manager.player_fleet.shipgirls):
                    if shipgirl is None:
                        continue
                    if not shipgirl.battle_component.active:
                        continue
                    if shipgirl.battle_component.attack_animation:
                        continue
                    if shipgirl.battle_component.attack_timer > 0:
                        continue
                    if not shipgirl.rect.collidepoint(event.pos):
                        continue
                    self.mouse_start_drag = shipgirl.rect.center
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
            dt = dt / 2
        if self.encounter_started:
            afloat_sirens_before = [siren for siren in self.menu_manager.siren_fleet.fleet if siren.battle_component.hp > 0]
            self.menu_manager.player_fleet.update(dt, self.vfx_manager)
            afloat_sirens_after = [siren for siren in self.menu_manager.siren_fleet.fleet if siren.battle_component.hp > 0]
            if self.current_sortie < DataFiles.save_file["sortie_progress"]:
                defeated_sirens = [siren for siren in afloat_sirens_before if siren not in afloat_sirens_after]
                for siren in defeated_sirens:
                    siren_data = DataFiles.siren_data[siren.name]
                    for drop, drop_rate in siren_data["drops"].items():
                        if random.randint(0, 99) < drop_rate:
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
                research_target = DataFiles.save_file["research_target"]
                specialized_wisdom_cubes = DataFiles.save_file["specialized_wisdom_cubes"]
                specialized_wisdom_cubes[research_target] += self.research_exp
                avg_shipgirl_level = int(
                    sum(
                        Stats.level(shipgirl.battle_component.exp)
                        for shipgirl in self.menu_manager.available_shipgirls
                    )
                    / len(self.menu_manager.available_shipgirls)
                )
                exp_req = Stats.exp_to_level(avg_shipgirl_level)
                if specialized_wisdom_cubes[research_target] >= exp_req:
                    if research_target == DataFiles.get_faction_shipgirls()["CA"]:
                        self.menu_manager.quest_manager.quests[construct_shipgirl_quest.quest_id] = construct_shipgirl_quest
                        DataFiles.save_file["quests"][construct_shipgirl_quest.quest_id] = "new"

                    unique_item = DataFiles.shipgirl_data[research_target]["unique_item"]
                    if DataFiles.save_file["inventory"].get(unique_item, 0) == 0:
                        self.drops.append(Drop(unique_item, pygame.Vector2(screen_x(0.5), screen_y(0.5))))
                self.research_exp = 0
        elif self.exp_timer > 0:
            self.exp_timer -= dt
            if self.exp_timer < 0:
                self.exp_timer = 0

        if self.encounter_end_flag:
            if not self.menu_manager.player_fleet.afloat:
                self.encounter_end_flag = False
                self.end_encounter_banner.text = "defeat"
                self.menu_manager.player_fleet.end_encounter()
                self.menu_manager.siren_fleet.end_encounter()
                self.return_to_port_button.active = True
                self.retreat_button.active = False

            if not self.menu_manager.siren_fleet.afloat:
                self.encounter_end_flag = False
                self.end_encounter_banner.text = "victory"
                for siren in self.menu_manager.siren_fleet.fleet:
                    siren_reward_exp = Stats.stat(
                        siren.battle_component.exp,
                        *DataFiles.siren_data[siren.name]["reward_exp"]
                    )
                    for shipgirl in self.menu_manager.player_fleet.fleet:
                        if shipgirl is not None:
                            shipgirl.battle_component.exp += siren_reward_exp
                    if DataFiles.save_file["research_target"] is not None:
                        self.research_exp += siren_reward_exp

                self.menu_manager.player_fleet.end_encounter()
                self.menu_manager.siren_fleet.end_encounter()
                self.next_encounter_button.active = True
                self.retreat_button.active = False

        self.vfx_manager.update(dt)
        self.background.update(dt)

    def draw(self, surface, font_registry):
        self.background.draw(surface, font_registry, player_fleet=self.menu_manager.player_fleet, siren_fleet=self.menu_manager.siren_fleet)

        self.menu_manager.player_fleet.draw_battle_effects(surface, self.vfx_manager)
        self.menu_manager.siren_fleet.draw_battle_effects(surface, self.vfx_manager)
        self.vfx_manager.draw(surface, font_registry)

        self.next_encounter_button.draw(surface, font_registry)
        self.open_reward_cache_button.draw(surface, font_registry)
        self.return_to_port_button.draw(surface, font_registry)
        self.retreat_button.draw(surface, font_registry)

        for drop in self.drops:
            drop.draw(surface, font_registry)
        
        if self.exp_timer > 0:
            bar_width = 256
            bar_height = 16
            bar_background = get_rect(
                width=bar_width, height=bar_height,
                centerx=screen_x(0.5), bottom=Box.BOTTOM_OF_SCREEN
            )
            avg_shipgirl_level = int(
                sum(
                    Stats.level(shipgirl.battle_component.exp)
                    for shipgirl in self.menu_manager.available_shipgirls
                )
                / len(self.menu_manager.available_shipgirls)
            )
            exp_req = Stats.exp_to_level(avg_shipgirl_level)
            research_target = DataFiles.save_file["research_target"]
            research_progress = (
                DataFiles.save_file["specialized_wisdom_cubes"][research_target]
                + self.research_exp * self.exp_timer
            )
            bar_fill = get_rect(
                width=bar_width * min(1, research_progress/exp_req),
                height=bar_height, left=bar_background.left, top=bar_background.top 
            )
            pygame.draw.rect(surface, Color.EXP_BAR_BG, bar_background)
            pygame.draw.rect(surface, Color.EXP_BAR_FILL, bar_fill)
            banner_text = "shipgirl research progress"
            banner_surf = pygame.Surface((
                len(banner_text)*font_registry["big_pixel"].font_width + 2*Box.PADDING,
                font_registry["big_pixel"].font_height + 2*Box.PADDING
            ))
            banner_surf.fill(Color.BLACK)
            banner_surf.set_alpha(160)
            banner_rect = banner_surf.get_rect()
            banner_rect.centerx = bar_background.centerx
            banner_rect.bottom = bar_background.top - Box.PADDING
            surface.blit(banner_surf, banner_rect)
            font_registry["big_pixel"].render(
                surface,
                banner_text,
                banner_rect.center,
                Color.WHITE,
                1,
                style="center"
            )
        
        if self.end_encounter_banner.text:
            self.end_encounter_banner.draw(surface, font_registry)

        mpos = pygame.mouse.get_pos()
        if self.mouse_start_drag is not None:
            pygame.draw.line(surface, Color.WHITE, self.mouse_start_drag, mpos, width=Box.OUTLINE_WIDTH)
            for siren in self.menu_manager.siren_fleet.fleet:
                if siren.battle_component.hp <= 0:
                    continue
                if siren.rect.collidepoint(mpos):
                    if self.selected_shipgirl.battle_component.hull_type in self.MELEE_SHIPS:
                        # TODO clean up magic numbers
                        if siren in self.menu_manager.siren_fleet.front:
                            color = (50,200,50)
                        else:
                            color = (200,50,50)
                    else:
                        color = (50,200,50)
                    
                    inner_radius = 12
                    outer_radius = 24
                    annulus = pygame.Surface((2*outer_radius, 2*outer_radius))
                    annulus.fill((0,0,0))
                    pygame.draw.circle(annulus, color, (outer_radius, outer_radius), outer_radius)
                    pygame.draw.circle(annulus, (0,0,0), (outer_radius, outer_radius), inner_radius)
                    annulus.set_colorkey((0,0,0))
                    annulus_rect = annulus.get_rect()

                    drawpos = pygame.Vector2(mpos) + pygame.Vector2(48)
                    annulus_rect.center = drawpos
                    surface.blit(annulus, annulus_rect)

                    if self.selected_shipgirl.battle_component.hull_type == "CV":
                        attack_icon = DataFiles.sprites["user_interface"]["air_attack"]
                    elif self.selected_shipgirl.battle_component.hull_type == "SS":
                        attack_icon = DataFiles.sprites["user_interface"]["torp_attack"]
                    else:
                        attack_icon = DataFiles.sprites["user_interface"]["shell_attack"]
                    attack_icon_rect = attack_icon.get_rect()
                    attack_icon_rect.center = drawpos
                    surface.blit(attack_icon, attack_icon_rect)
