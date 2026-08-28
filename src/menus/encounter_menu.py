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

    def __init__(self, index, x, y, speed, cloud_sprites):
        self.index = index
        self.sprite = cloud_sprites[index]
        self.shadow = DataFiles.sprites["background"][f"cloud_shadow{index}"]
        self.x = x
        self.y = y
        self.speed = speed

    def set_cloud_sprites(self, cloud_sprites):
        self.sprite = cloud_sprites[self.index]

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


class SeaFoam:
    FADE_IN_DURATION = 0.5
    FADE_OUT_DURATION = 1.0
    HOLD_DURATION = 0.3
    CREST_X_RATIO = 1 / 4

    def __init__(self, sprite, wave_index, wave_rep_index, moving_left):
        self.sprite = pygame.transform.flip(sprite, True, False) if moving_left else sprite.copy()
        self.moving_left = moving_left
        self.wave_index = wave_index
        self.wave_rep_index = wave_rep_index
        self.duration = self.FADE_IN_DURATION + self.HOLD_DURATION + self.FADE_OUT_DURATION
        self.lifetime = 0

    @property
    def expired(self):
        return self.lifetime >= self.duration

    @property
    def alpha(self):
        if self.lifetime < self.FADE_IN_DURATION:
            return int(255 * self.lifetime / self.FADE_IN_DURATION)

        fade_out_start = self.FADE_IN_DURATION + self.HOLD_DURATION
        if self.lifetime > fade_out_start:
            fade_out_lifetime = self.lifetime - fade_out_start
            return int(255 * (1 - fade_out_lifetime / self.FADE_OUT_DURATION))

        return 255

    def update(self, dt):
        self.lifetime += dt

    def align_rect(self, wave_rect):
        rect = self.sprite.get_rect()
        rect.top = wave_rect.top
        rect.left = wave_rect.left
        if self.moving_left:
            rect.left += int(2 * self.sprite.get_width() * self.CREST_X_RATIO - self.sprite.get_width())
        return rect

    def draw(self, surface, wave_rect):
        rect = self.align_rect(wave_rect)
        self.sprite.set_alpha(self.alpha)
        surface.blit(self.sprite, rect)


class RainDrop:
    def __init__(self, pos, color, bottom):
        self.pos = pygame.Vector2(pos)
        self.color = color
        self.bottom = bottom
        self.length = random.uniform(18, 34)
        self.speed = random.uniform(520, 720)
        self.angle = math.radians(135 + random.uniform(-6, 6))

    @property
    def offscreen(self):
        return self.pos.x < -self.length or self.pos.y > self.bottom + self.length

    def update(self, dt):
        self.pos += get_vec(self.speed * dt, self.angle)

    def draw(self, surface):
        end_pos = self.pos + get_vec(self.length, self.angle)
        pygame.draw.line(surface, self.color, self.pos, end_pos, width=1)


class Background:
    Y_GAP = 48
    NUM_WAVE_REPS = 5
    WAVE_HORIZONTAL_AMPLITUDE = 48
    WAVE_VERTICAL_AMPLITUDE = 8
    RAIN_SPAWN_RATE = 90
    NUM_STARS = 65
    STAR_COLORS = [
        (245, 245, 255),
        (221, 226, 255),
        (205, 214, 248),
    ]
    MOON_COLOR = (232, 229, 210)
    MOON_SHADOW_COLOR = (18, 16, 45)

    def __init__(self, sky_colors, wave_sprites, cloud_sprites, rain_colors):
        self.set_sky_colors(sky_colors)
        self.wave_sprites = wave_sprites
        self.cloud_sprites = cloud_sprites
        self.rain_colors = rain_colors
        self.raining = False
        self.rain_drops = []
        self.rain_spawn_progress = 0
        self.night_sky_visible = False
        self.stars = []
        self.moon_pos = pygame.Vector2(screen_x(0.36), screen_y(0.12))
        self.sea_foam_sprite = DataFiles.sprites["background"]["sea_foam"]
        self.sea_foams = []
        num_waves = DataFiles.sprites["background"]["num_waves"]
        self.wave_speeds = [
            (wave_index + 1) / num_waves
            for wave_index in range(num_waves)
        ]
        self.sea_foam_spawned_this_rise = [False] * num_waves
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

    @staticmethod
    def wave_vertical_offset(wave_timer):
        return -math.cos(2 * wave_timer)

    @staticmethod
    def wave_is_rising(wave_timer):
        return math.sin(2 * wave_timer) < 0

    @classmethod
    def sea_foam_is_ready(cls, wave_timer, wave_speed):
        if not cls.wave_is_rising(wave_timer):
            return False

        upcoming_crest = math.pi if wave_timer < math.pi else math.tau
        time_until_crest = (upcoming_crest - wave_timer) / wave_speed
        return time_until_crest <= SeaFoam.FADE_IN_DURATION

    def set_cloud_sprites(self, weather):
        self.cloud_sprites = DataFiles.sprites["background"]["cloud_sets"][weather]
        for cloud in self.clouds:
            cloud.set_cloud_sprites(self.cloud_sprites)

    def set_rain(self, raining, rain_colors):
        self.raining = raining
        self.rain_colors = rain_colors
        if not self.raining:
            self.rain_drops = []
            self.rain_spawn_progress = 0

    def set_night_sky(self, visible):
        self.night_sky_visible = visible
        if self.night_sky_visible:
            self.generate_stars()
        else:
            self.stars = []

    def generate_stars(self):
        self.stars = []
        star_bottom = self.wave_ys[0] + 32
        for _ in range(self.NUM_STARS):
            self.stars.append((
                pygame.Vector2(
                    random.uniform(screen_x(0.03), screen_x(0.97)),
                    random.uniform(screen_y(0.04), star_bottom),
                ),
                random.choice([1, 1, 1, 2]),
                random.choice(self.STAR_COLORS),
            ))

    def draw_night_sky(self, surface):
        if not self.night_sky_visible:
            return

        moon_radius = 20
        pygame.draw.circle(surface, self.MOON_COLOR, self.moon_pos, moon_radius)
        pygame.draw.circle(
            surface,
            self.MOON_SHADOW_COLOR,
            self.moon_pos + pygame.Vector2(moon_radius * 0.36, -moon_radius * 0.36),
            moon_radius,
        )
        for star_pos, star_radius, star_color in self.stars:
            pygame.draw.circle(surface, star_color, star_pos, star_radius)

    def update(self, dt):
        self.wave_timers = [
            (wave_timer + wave_speed * dt) % math.tau
            for wave_timer, wave_speed in zip(self.wave_timers, self.wave_speeds)
        ]

        if self.raining:
            self.rain_spawn_progress += self.RAIN_SPAWN_RATE * dt
            num_rain_drops = int(self.rain_spawn_progress)
            self.rain_spawn_progress -= num_rain_drops
            for _ in range(num_rain_drops):
                self.rain_drops.append(RainDrop(
                    (
                        random.uniform(0, screen_x(1) + screen_y(0.45)),
                        random.uniform(-screen_y(0.2), 0),
                    ),
                    random.choice(self.rain_colors),
                    random.uniform(screen_y(0.45), self.wave_ys[-1]),
                ))
        for rain_drop in self.rain_drops:
            rain_drop.update(dt)
        self.rain_drops = [
            rain_drop for rain_drop in self.rain_drops
            if not rain_drop.offscreen
        ]

        for cloud in self.clouds:
            cloud.update(dt)
        self.clouds = [
            cloud for cloud in self.clouds
            if cloud.x >= -128
            and cloud.x <= screen_x(1) + 128
        ]

        for sea_foam in self.sea_foams:
            sea_foam.update(dt)
        self.sea_foams = [
            sea_foam for sea_foam in self.sea_foams
            if not sea_foam.expired
        ]

        for wave_index, (wave_timer, wave_speed) in enumerate(zip(
            self.wave_timers,
            self.wave_speeds,
        )):
            if not self.wave_is_rising(wave_timer):
                self.sea_foam_spawned_this_rise[wave_index] = False
                continue

            if (
                not self.sea_foam_spawned_this_rise[wave_index]
                and self.sea_foam_is_ready(wave_timer, wave_speed)
            ):
                self.sea_foams.append(SeaFoam(
                    self.sea_foam_sprite,
                    wave_index,
                    random.randrange(self.NUM_WAVE_REPS),
                    math.cos(wave_timer) < 0,
                ))
                self.sea_foam_spawned_this_rise[wave_index] = True

        self.cloud_timer += dt
        if self.cloud_timer > self.cloud_spawn_time:
            move_right = bool(random.randint(0, 1))
            self.clouds.append(Cloud(
                random.randint(1, DataFiles.sprites["background"]["num_clouds"])-1,
                0 if move_right else screen_x(1),
                random.uniform(-64, 64),
                random.uniform(32, 64) * (1 if move_right else -1),
                self.cloud_sprites,
            ))
            self.cloud_timer = 0
            self.cloud_spawn_time = random.uniform(5, 10)

    def draw(
        self,
        surface,
        font_registry,
        player_fleet=None,
        siren_fleet=None,
        player_shipgirl_filter=None,
    ):
        sky_surf = self.sky_surf
        sky_surf_rect = sky_surf.get_rect()
        sky_surf_rect.top = 0
        num_sky_reps = 9
        sky_rep_offset = (num_sky_reps-1)/2
        for i in range(num_sky_reps):
            sky_surf_rect.centerx = screen_x(0.5) + sky_surf_rect.width * (i-sky_rep_offset)
            surface.blit(sky_surf, sky_surf_rect)

        self.draw_night_sky(surface)

        for cloud in self.clouds:
            cloud.draw(surface)

        if siren_fleet is not None:
            siren_draw_indices = siren_fleet.get_draw_indices()
        else:
            siren_draw_indices = None

        if player_fleet is not None:
            shipgirl_draw_indices = player_fleet.get_draw_indices()
            if player_shipgirl_filter is not None:
                shipgirl_draw_indices = [
                    (draw_index, shipgirl)
                    for draw_index, shipgirl in shipgirl_draw_indices
                    if player_shipgirl_filter(shipgirl)
                ]
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
        num_wave_reps = self.NUM_WAVE_REPS
        wave_rep_offset = (num_wave_reps-1)/2
        for i, (wave_y, wave_timer) in enumerate(zip(self.wave_ys, self.wave_timers)):
            if shipgirl_draw_indices is not None:
                for draw_index, shipgirl in shipgirl_draw_indices:
                    if i == draw_index:
                        shipgirl.draw(surface, font_registry)
                        # shipgirl.battle_component.draw_battlestation(surface, font_registry, shipgirl.rect)

            if siren_draw_indices is not None:
                for draw_index, siren in siren_draw_indices:
                    if i == draw_index:
                        siren.draw(surface, font_registry)
                        # siren.battle_component.draw_battlestation(surface, font_registry, siren.rect)

            move_amt = i / num_waves
            wave = self.wave_sprites[i]
            wave_rect = wave.get_rect()
            wave_rect.top = (
                wave_y
                + self.WAVE_VERTICAL_AMPLITUDE
                * (move_amt + 1)
                * self.wave_vertical_offset(wave_timer)
            )
            centerx = (
                self.WAVE_HORIZONTAL_AMPLITUDE
                * (move_amt + 1)
                * math.sin(wave_timer)
                + screen_x(0.5)
            )
            for j in range(num_wave_reps):
                wave_rect.centerx = centerx + wave_rect.width * (j-wave_rep_offset)
                surface.blit(wave, wave_rect)
                for sea_foam in self.sea_foams:
                    if sea_foam.wave_index == i and sea_foam.wave_rep_index == j:
                        sea_foam.draw(surface, wave_rect)

        for rain_drop in self.rain_drops:
            rain_drop.draw(surface)

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
    TRANSITION_IDLE = "idle"
    TRANSITION_EXITING = "exiting"
    TRANSITION_FADE_TO_BLACK = "fade_to_black"
    TRANSITION_BLACK_INTERLUDE = "black_interlude"
    TRANSITION_FADE_FROM_BLACK = "fade_from_black"
    TRANSITION_ENTERING = "entering"

    TRANSITION_MOVE_SPEED = 600
    TRANSITION_FADE_DURATION = 0.35
    TRANSITION_INTERLUDE_DURATION = 0.25
    OPENED_REWARD_REPORT_DELAY = 0.5

    MELEE_SHIPS = ["DD", "CL", "SS"]
    REPORT_PAGE_COUNT = 2
    REWARDS_SECTION_TOP = 56
    SIREN_CARDS_PER_ROW = 3
    SIREN_CARD_WIDTH = 152
    SHIPGIRL_WAKE_CONFIG = {
        "upward_bias": -0.4,
        "spark_chance": 1.0,
        "spark_duration_range": (0.22, 0.34),
        "spark_distance_range": (12, 24),
        "spark_length_range": (12, 24),
        "spark_width_range": (4, 6),
        "smoke_chance": 0.25,
        "smoke_duration_range": (0.28, 0.45),
        "smoke_distance_range": (8, 16),
        "smoke_size_range": (16, 24),
    }
    SHIPGIRL_WAKE_COLORS = {
        "daytime": [
            (231, 237, 249),
            (209, 220, 242),
            (185, 202, 234),
            (162, 184, 224),
        ],
        "nighttime": [
            (174, 174, 199),
            (149, 150, 183),
            (124, 128, 165),
            (101, 106, 146),
        ],
        "stormy": [
            (215, 226, 226),
            (193, 211, 213),
            (170, 195, 201),
            (148, 179, 190),
        ],
    }
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
        self.sortie_completed = False
        self.selected_shipgirl = None
        self.selected_shipgirl_index = None
        self.encounter_started = False
        self.vfx_manager = VFXManager()

        self._transition_state = self.TRANSITION_IDLE
        self._transition_timer = 0
        self._transition_shipgirls = []
        self._transition_slot_positions = {}
        self._opened_reward_report_timer = None

        def next_encounter():
            self.start_encounter_transition()

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
            rewards = DataFiles.sortie_data[self.current_sortie]["rewards"]
            for reward, amount in rewards.items():
                self.add_sortie_drop(
                    reward,
                    pygame.Vector2(self.open_reward_cache_button.rect.center),
                    amount,
                )

            self.return_to_port_button.active = True

            DataFiles.sfx["open"].play()

        button_sprite = DataFiles.sprites["user_interface"]["closed_reward_cache"]
        button_rect = button_sprite.get_rect()
        self.open_reward_cache_button = Button(
            button_rect,
            open_reward_cache,
            active=False,
            background_styling={"background_img": button_sprite}
        )

        def return_to_port():
            if self.sortie_completed:
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
                
                self.claim_drops()

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

        # Size the end-of-sortie report for the largest Siren record set in the
        # sortie data, arranged in three columns.
        max_siren_records = max(
            len({
                siren
                for encounter in sortie["encounters"]
                for siren in encounter["front"] + encounter["back"]
            })
            for sortie in DataFiles.sortie_data
        )
        max_siren_rows = math.ceil(
            max_siren_records / self.SIREN_CARDS_PER_ROW
        )
        report_page_width = (
            2*Box.PADDING
            + self.SIREN_CARDS_PER_ROW*self.SIREN_CARD_WIDTH
            + (self.SIREN_CARDS_PER_ROW - 1)*Box.PADDING
        )
        report_page_height = (
            self.REWARDS_SECTION_TOP
            + 2*Box.PADDING
            + max_siren_rows*Box.HEIGHT
            + (max_siren_rows - 1)*Box.PADDING
            + 3*Box.PADDING
        )
        self.dossier_overlay = get_rect(
            width=report_page_width + 2*Box.PADDING,
            height=report_page_height + 2*Box.PADDING + Box.HEIGHT/2,
            center=(screen_x(0.5), screen_y(0.5)),
        )
        self.dossier_bg = self.dossier_overlay.inflate(
            0,
            -Box.HEIGHT/2,
        )
        self.dossier_bg.bottom = self.dossier_overlay.bottom
        self.dossier_page = self.dossier_bg.inflate(
            -2*Box.PADDING,
            -2*Box.PADDING,
        )
        self.return_to_port_button.rect.center = (
            self.dossier_overlay.right + Box.WIDTH/2,
            self.dossier_overlay.bottom - Box.HEIGHT/2,
        )
        self.report_page = 0
        self.report_page_prev_button = Button(
            get_rect(
                width=48,
                height=48,
                left=self.dossier_page.left,
                top=self.dossier_page.top,
            ),
            lambda: self.change_report_page(-1),
            active=False,
        )
        self.report_page_next_button = Button(
            get_rect(
                width=48,
                height=48,
                right=self.dossier_page.right,
                bottom=self.dossier_page.bottom,
            ),
            lambda: self.change_report_page(1),
            active=False,
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
        self.defeat_pending = False

        self.drops = []
        self.sortie_rewards = {}
        self.defeated_sirens = {}
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
                centerx=screen_x(0.275) + slot_size - (slot_index-fleet_slot_offset)*slot_size/2,
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
            DataFiles.sprites["background"]["cloud_sets"][self.time_weather],
            self.SHIPGIRL_WAKE_COLORS["stormy"],
        )
        self.apply_time_weather_style()

    @property
    def transition_active(self):
        return self._transition_state != self.TRANSITION_IDLE

    def _set_transition_state(self, state):
        self._transition_state = state
        self._transition_timer = 0

    def _get_fleet_slot_positions(self):
        slot_positions = {}
        for shipgirl, slot in zip(
            self.menu_manager.player_fleet.shipgirls,
            self.fleet_slots,
        ):
            if shipgirl is not None:
                slot_positions[shipgirl] = pygame.Vector2(slot.center)
        for shipgirl, slot in zip(
            self.menu_manager.player_fleet.backups,
            self.backup_fleet_slots,
        ):
            if shipgirl is not None:
                slot_positions[shipgirl] = pygame.Vector2(slot.center)
        return slot_positions

    def start_encounter_transition(self):
        if self.transition_active:
            return

        self.claim_drops()
        self.next_encounter_button.active = False
        self.open_reward_cache_button.active = False
        self.return_to_port_button.active = False
        self.retreat_button.active = False
        self.report_page_prev_button.active = False
        self.report_page_next_button.active = False

        self.mouse_start_drag = None
        self.selected_shipgirl = None
        self.selected_shipgirl_index = None

        self._transition_slot_positions = self._get_fleet_slot_positions()
        self._transition_shipgirls = [
            shipgirl
            for shipgirl in self._transition_slot_positions
            if shipgirl.battle_component.hp > 0
        ]
        for shipgirl in self._transition_shipgirls:
            shipgirl.facing_left = False
            shipgirl.sprite.set_animation(shipgirl.sprite.WALK_ANIMATION)

        self._set_transition_state(self.TRANSITION_EXITING)

    def _load_transition_destination(self):
        self.current_encounter += 1
        self.begin_encounter()

        for shipgirl, target in self._transition_slot_positions.items():
            shipgirl.rect.center = target

        if self._transition_shipgirls:
            rightmost_edge = max(
                self._transition_slot_positions[shipgirl].x
                + shipgirl.rect.width / 2
                for shipgirl in self._transition_shipgirls
            )
            entry_offset = -rightmost_edge
            for shipgirl in self._transition_shipgirls:
                target = self._transition_slot_positions[shipgirl]
                shipgirl.rect.center = target + pygame.Vector2(entry_offset, 0)
                shipgirl.facing_left = False
                shipgirl.sprite.set_animation(shipgirl.sprite.WALK_ANIMATION)

    def _finish_encounter_transition(self):
        for shipgirl in self._transition_shipgirls:
            shipgirl.rect.center = self._transition_slot_positions[shipgirl]
            shipgirl.facing_left = False
            shipgirl.sprite.set_animation(shipgirl.sprite.IDLE_ANIMATION)

        self._transition_shipgirls = []
        self._transition_slot_positions = {}
        self._set_transition_state(self.TRANSITION_IDLE)

    def _update_transition_shipgirl_animation(self, dt):
        for shipgirl in self._transition_shipgirls:
            shipgirl.sprite.set_animation(shipgirl.sprite.WALK_ANIMATION)
            shipgirl.animate(dt)

    def _update_encounter_transition(self, dt):
        state = self._transition_state

        if state == self.TRANSITION_EXITING:
            distance = self.TRANSITION_MOVE_SPEED * dt
            for shipgirl in self._transition_shipgirls:
                shipgirl.rect.centerx += distance
            self._update_transition_shipgirl_animation(dt)
            if not self._transition_shipgirls or all(
                shipgirl.rect.left >= screen_x(1)
                for shipgirl in self._transition_shipgirls
            ):
                self._set_transition_state(self.TRANSITION_FADE_TO_BLACK)

        elif state == self.TRANSITION_FADE_TO_BLACK:
            self._transition_timer += dt
            if self._transition_timer >= self.TRANSITION_FADE_DURATION:
                self._load_transition_destination()
                self._set_transition_state(self.TRANSITION_BLACK_INTERLUDE)

        elif state == self.TRANSITION_BLACK_INTERLUDE:
            self._transition_timer += dt
            if self._transition_timer >= self.TRANSITION_INTERLUDE_DURATION:
                self._set_transition_state(self.TRANSITION_FADE_FROM_BLACK)

        elif state == self.TRANSITION_FADE_FROM_BLACK:
            self._transition_timer += dt
            if self._transition_timer >= self.TRANSITION_FADE_DURATION:
                self._set_transition_state(self.TRANSITION_ENTERING)

        elif state == self.TRANSITION_ENTERING:
            distance = self.TRANSITION_MOVE_SPEED * dt
            for shipgirl in self._transition_shipgirls:
                target_x = self._transition_slot_positions[shipgirl].x
                shipgirl.rect.centerx = min(
                    target_x,
                    shipgirl.rect.centerx + distance,
                )
            self._update_transition_shipgirl_animation(dt)
            if not self._transition_shipgirls or all(
                shipgirl.rect.centerx >= self._transition_slot_positions[shipgirl].x
                for shipgirl in self._transition_shipgirls
            ):
                self._finish_encounter_transition()

        if self._transition_state in (
            self.TRANSITION_EXITING,
            self.TRANSITION_ENTERING,
        ):
            self.spawn_shipgirl_wakes(self.menu_manager.player_fleet)

        self.vfx_manager.update(dt)
        self.background.update(dt)

    def _transition_overlay_alpha(self):
        if self._transition_state == self.TRANSITION_FADE_TO_BLACK:
            progress = min(
                1,
                self._transition_timer / self.TRANSITION_FADE_DURATION,
            )
            return int(255 * progress)
        if self._transition_state == self.TRANSITION_BLACK_INTERLUDE:
            return 255
        if self._transition_state == self.TRANSITION_FADE_FROM_BLACK:
            progress = min(
                1,
                self._transition_timer / self.TRANSITION_FADE_DURATION,
            )
            return int(255 * (1 - progress))
        return 0

    def _transition_interlude_progress(self):
        if self._transition_state == self.TRANSITION_BLACK_INTERLUDE:
            return min(
                1,
                self._transition_timer / self.TRANSITION_INTERLUDE_DURATION,
            )
        if self._transition_state == self.TRANSITION_FADE_FROM_BLACK:
            return 1
        return 0

    def draw_transition_interlude(self, surface, font_registry, progress):
        """Draw the obscured portion of an encounter transition.

        Extend this method with future interstitial animation. ``progress`` runs
        from zero to one during the fully obscured interlude.
        """
        surface.fill(Color.BLACK)

    def _draw_transition_overlay(self, surface, font_registry):
        alpha = self._transition_overlay_alpha()
        if alpha <= 0:
            return

        interlude_surface = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        self.draw_transition_interlude(
            interlude_surface,
            font_registry,
            self._transition_interlude_progress(),
        )
        interlude_surface.set_alpha(alpha)
        surface.blit(interlude_surface, (0, 0))

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
        self.background.set_cloud_sprites(self.time_weather)
        self.background.set_rain(
            self.time_weather == "stormy",
            self.SHIPGIRL_WAKE_COLORS["stormy"],
        )
        self.background.set_night_sky(self.time_weather == "nighttime")

    def begin_sortie(self):
        self._transition_state = self.TRANSITION_IDLE
        self._transition_timer = 0
        self._transition_shipgirls = []
        self._transition_slot_positions = {}
        self._opened_reward_report_timer = None
        self.roll_time_weather()
        self.open_reward_cache_button.active = False
        self.return_to_port_button.active = False
        self.sortie_completed = False
        self.sortie_rewards = {}
        self.defeated_sirens = {}
        self.report_page = 0
        self.refresh_report_page_buttons()

        self.begin_encounter()

    def add_sortie_drop(self, item, pos, amount=1):
        for _ in range(amount):
            self.drops.append(Drop(
                item,
                pygame.Vector2(pos),
            ))

    def claim_drops(self):
        for drop in self.drops:
            DataFiles.save_file["inventory"][drop.item] = (
                DataFiles.save_file["inventory"].get(drop.item, 0) + 1
            )
            self.sortie_rewards[drop.item] = (
                self.sortie_rewards.get(drop.item, 0) + 1
            )

    def begin_encounter(self):
        self.drops = []
        self.next_encounter_button.active = False
        self.vfx_manager.clear()
        self.defeat_pending = False
        self._opened_reward_report_timer = None

        sortie_data = DataFiles.sortie_data[self.current_sortie]
        num_encounters = len(sortie_data["encounters"])
        self.end_encounter_banner.text = ""
        if self.current_encounter == num_encounters:
            self.sortie_completed = True
            self.open_reward_cache_button.active = True
            if self.current_sortie < DataFiles.save_file["sortie_progress"]:
                self.return_to_port_button.active = False
                self._opened_reward_report_timer = (
                    self.OPENED_REWARD_REPORT_DELAY
                )
                self.open_reward_cache_button.background_img = DataFiles.sprites["user_interface"]["open_reward_cache"]
            else:
                self.open_reward_cache_button.background_img = DataFiles.sprites["user_interface"]["closed_reward_cache"]

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

    def _update_opened_reward_report(self, dt):
        if self._opened_reward_report_timer is None:
            return

        self._opened_reward_report_timer = max(
            0,
            self._opened_reward_report_timer - dt,
        )
        if self._opened_reward_report_timer == 0:
            self._opened_reward_report_timer = None
            self.return_to_port_button.active = True

    def spawn_shipgirl_wakes(self, fleet):
        for shipgirl in fleet.fleet:
            if shipgirl is None or shipgirl.battle_component.hp <= 0:
                continue

            wake_pos = pygame.Vector2(
                (
                    shipgirl.rect.centerx
                    + (-1 if shipgirl.rect.x < screen_x(0.5) else 1)
                    * random.uniform(-shipgirl.rect.width * 0.1, shipgirl.rect.width * 0.3)
                ),
                shipgirl.rect.bottom - random.uniform(11, 16),
            )
            torpedo_angle = 0 if shipgirl.rect.x < screen_x(0.5) else math.pi
            self.vfx_manager.spawn_wake(
                wake_pos,
                torpedo_angle,
                wake_colors=self.SHIPGIRL_WAKE_COLORS[self.time_weather],
                **self.SHIPGIRL_WAKE_CONFIG,
            )

    def update(self, dt, events):
        if self.transition_active:
            self._update_encounter_transition(dt)
            return

        self._update_opened_reward_report(dt)
        self.refresh_report_page_buttons()
        for event in events:
            if self.transition_active:
                break
            if event.type == pygame.MOUSEMOTION:
                self.next_encounter_button.hover(event.pos)
                self.retreat_button.hover(event.pos)
                self.return_to_port_button.hover(event.pos)
                self.report_page_prev_button.hover(event.pos)
                self.report_page_next_button.hover(event.pos)
            if event.type == pygame.MOUSEBUTTONDOWN:
                for i, shipgirl in enumerate(self.menu_manager.player_fleet.shipgirls):
                    if shipgirl is None:
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
                        if backup_shipgirl.battle_component.hp <= 0:
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
                    or self.report_page_prev_button.click(event.pos)
                    or self.report_page_next_button.click(event.pos)
                    or self.return_to_port_button.click(event.pos)
                    or self.retreat_button.click(event.pos)
                )

                if click:
                    DataFiles.sfx["click"].play()
                elif (
                    self.current_sortie == DataFiles.save_file["sortie_progress"]
                    and self.open_reward_cache_button.click(event.pos)
                ):
                    self.open_reward_cache_button.background_img = DataFiles.sprites["user_interface"]["open_reward_cache"]

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_f:
                    self.fast_forward = not self.fast_forward
                if event.key == pygame.K_d:
                    self.slow_down = not self.slow_down

        if self.transition_active:
            self._update_encounter_transition(dt)
            return
        
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
                            self.add_sortie_drop(drop, siren.rect.center)
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
                        self.add_sortie_drop(
                            unique_item,
                            (screen_x(0.5), screen_y(0.5)),
                        )
                self.research_exp = 0
        elif self.exp_timer > 0:
            self.exp_timer -= dt
            if self.exp_timer < 0:
                self.exp_timer = 0

        if self.encounter_end_flag:
            if not self.menu_manager.player_fleet.afloat:
                self.encounter_end_flag = False
                self.end_encounter_banner.text = ""
                self.menu_manager.player_fleet.end_encounter()
                self.menu_manager.siren_fleet.end_encounter()
                self.retreat_button.active = False
                self.defeat_pending = True

            if not self.menu_manager.siren_fleet.afloat:
                self.encounter_end_flag = False
                self.end_encounter_banner.text = "victory"
                for siren in self.menu_manager.siren_fleet.fleet:
                    siren_level = Stats.level(siren.battle_component.exp)
                    siren_key = (siren.name, siren_level)
                    self.defeated_sirens[siren_key] = (
                        self.defeated_sirens.get(siren_key, 0) + 1
                    )
                    siren_reward_exp = Stats.stat(
                        *DataFiles.siren_data[siren.name]["reward_exp"],
                        exp=siren.battle_component.exp,
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

        if self.defeat_pending:
            sunk_shipgirls = [
                shipgirl
                for shipgirl in self.menu_manager.player_fleet.fleet
                if shipgirl is not None and shipgirl.battle_component.hp <= 0
            ]
            if sunk_shipgirls and all(
                shipgirl.sprite.animation_finished(shipgirl.sprite.SINK_ANIMATION)
                for shipgirl in sunk_shipgirls
            ):
                self.defeat_pending = False
                self.return_to_port_button.active = True

        self.spawn_shipgirl_wakes(self.menu_manager.player_fleet)
        self.spawn_shipgirl_wakes(self.menu_manager.siren_fleet)
        self.vfx_manager.update(dt)
        self.background.update(dt)

        self.open_reward_cache_button.rect.center = (
            pygame.Vector2(screen_x(0.75), screen_y(0.575))
            + pygame.Vector2(
                72 * math.sin(self.background.wave_timers[3]),
                12 * self.background.wave_vertical_offset(self.background.wave_timers[3]),
            )
        )

    def draw_encounter_progress(self, surface):
        encounters = DataFiles.sortie_data[self.current_sortie]["encounters"]
        icon_spacing = 128
        first_icon_x = screen_x(0.5) - icon_spacing * (len(encounters) - 1) / 2
        icon_center_y = Box.BOTTOM_OF_SCREEN - 16

        prev_icon_rect = None
        dash_length = 8
        dash_gap = 8
        for encounter_index, encounter in enumerate(encounters):
            current_encounter_cleared = (
                encounter_index == self.current_encounter
                and not self.encounter_end_flag
                and self.end_encounter_banner.text == "victory"
            )
            if encounter_index < self.current_encounter or current_encounter_cleared:
                icon_name = "cleared"
            else:
                enemies = encounter["front"] + encounter["back"]
                is_boss = any(
                    enemy_encoding.split(":", 1)[0] == "tester"
                    for enemy_encoding in enemies
                )
                icon_name = "boss" if is_boss else "uncleared"

            icon = DataFiles.sprites["user_interface"][icon_name]
            icon_rect = icon.get_rect(
                centerx=first_icon_x + encounter_index * icon_spacing,
                bottom=Box.BOTTOM_OF_SCREEN,
            )
            surface.blit(icon, icon_rect)

            if prev_icon_rect is None:
                prev_icon_rect = icon_rect
                continue
            dash_x = prev_icon_rect.right + Box.PADDING
            path_end_x = icon_rect.left - Box.PADDING
            while dash_x < path_end_x:
                pygame.draw.line(
                    surface,
                    Color.BLUEPRINT_INK_MUTED,
                    (dash_x, icon_center_y),
                    (min(dash_x + dash_length, path_end_x), icon_center_y),
                    width=Box.OUTLINE_WIDTH,
                )
                dash_x += dash_length + dash_gap
            prev_icon_rect = icon_rect

        if self.current_encounter < len(encounters):
            current_icon_x = first_icon_x + self.current_encounter * icon_spacing
            current_icon = DataFiles.sprites["user_interface"]["uncleared"]
            current_icon_top = Box.BOTTOM_OF_SCREEN - current_icon.get_height()
            pointer_tip_y = current_icon_top - 4
            pointer = [
                (current_icon_x - 8, pointer_tip_y - 10),
                (current_icon_x + 8, pointer_tip_y - 10),
                (current_icon_x, pointer_tip_y),
            ]
            pygame.draw.polygon(surface, Color.WHITE, pointer)

    def refresh_report_page_buttons(self):
        report_visible = self.return_to_port_button.active
        self.report_page_prev_button.active = (
            report_visible and self.report_page > 0
        )
        self.report_page_next_button.active = (
            report_visible and self.report_page < self.REPORT_PAGE_COUNT - 1
        )
        if not self.report_page_prev_button.active:
            self.report_page_prev_button.hovered = False
        if not self.report_page_next_button.active:
            self.report_page_next_button.hovered = False

    def change_report_page(self, delta):
        self.report_page = min(
            self.REPORT_PAGE_COUNT - 1,
            max(0, self.report_page + delta),
        )
        self.refresh_report_page_buttons()

    def draw_dossier_page(self, surface):
        page_turn_size = self.report_page_next_button.rect.width
        prev_fold_hovered = self.report_page_prev_button.hovered
        prev_fold_size = (
            page_turn_size if prev_fold_hovered
            else page_turn_size - Box.PADDING
        )
        next_fold_hovered = self.report_page_next_button.hovered
        next_fold_size = (
            page_turn_size if next_fold_hovered
            else page_turn_size - Box.PADDING
        )

        page_polygon = []
        if self.report_page_prev_button.active:
            page_polygon.append((
                self.dossier_page.left + prev_fold_size,
                self.dossier_page.top,
            ))
        else:
            page_polygon.append(self.dossier_page.topleft)
        page_polygon.append(self.dossier_page.topright)

        if self.report_page_next_button.active:
            fold_top = (
                self.dossier_page.right,
                self.dossier_page.bottom - next_fold_size,
            )
            fold_left = (
                self.dossier_page.right - next_fold_size,
                self.dossier_page.bottom,
            )
            fold_tip = (
                self.dossier_page.right - next_fold_size,
                self.dossier_page.bottom - next_fold_size,
            )
            page_polygon.extend([fold_top, fold_left])
        else:
            page_polygon.append(self.dossier_page.bottomright)

        page_polygon.append(self.dossier_page.bottomleft)
        if self.report_page_prev_button.active:
            page_polygon.append((
                self.dossier_page.left,
                self.dossier_page.top + prev_fold_size,
            ))
        pygame.draw.polygon(surface, Color.DOSSIER_PAGE, page_polygon)

        if self.report_page_next_button.active:
            fold_shadow = (
                Color.DOSSIER_FOLD_SHADOW_HOVER
                if next_fold_hovered
                else Color.DOSSIER_FOLD_SHADOW
            )
            pygame.draw.polygon(
                surface,
                Color.DOSSIER_PAPER_UNDERSIDE,
                [fold_top, fold_left, fold_tip],
            )
            pygame.draw.line(
                surface,
                fold_shadow,
                fold_top,
                fold_left,
                width=Box.OUTLINE_WIDTH + int(next_fold_hovered),
            )
            pygame.draw.line(
                surface,
                Color.DOSSIER_RULE,
                fold_left,
                fold_tip,
            )

    def draw_dossier_prev_page_fold(self, surface):
        if not self.report_page_prev_button.active:
            return

        page_turn_size = self.report_page_prev_button.rect.width
        fold_hovered = self.report_page_prev_button.hovered
        fold_size = (
            page_turn_size if fold_hovered
            else page_turn_size - Box.PADDING
        )
        fold_top = pygame.Vector2(
            self.dossier_page.left + fold_size,
            self.dossier_page.top,
        )
        fold_left = pygame.Vector2(
            self.dossier_page.left,
            self.dossier_page.top + fold_size,
        )
        page_topleft = pygame.Vector2(self.dossier_page.topleft)
        fold_height = 2*Box.PADDING
        fold_polygon = [
            fold_top - pygame.Vector2(0, fold_height),
            fold_top,
            fold_left,
            fold_left - pygame.Vector2(fold_height, 0),
            page_topleft - pygame.Vector2(fold_height, fold_height),
        ]
        pygame.draw.polygon(surface, Color.DOSSIER_CARD, fold_polygon)
        pygame.draw.line(
            surface,
            (
                Color.DOSSIER_FOLD_SHADOW_HOVER
                if fold_hovered
                else Color.DOSSIER_FOLD_SHADOW
            ),
            fold_polygon[1],
            fold_polygon[2],
            width=Box.OUTLINE_WIDTH + int(fold_hovered),
        )

    def draw_dossier_overlay(self, surface, font_registry):
        """Draw the empty dossier and report page used after a sortie."""
        pygame.draw.rect(surface, Color.DOSSIER, self.dossier_bg)

        tab = [
            pygame.Vector2(self.dossier_overlay.topleft),
            pygame.Vector2(self.dossier_overlay.topleft)
            + pygame.Vector2(2*Box.WIDTH - Box.PADDING, 0),
            pygame.Vector2(self.dossier_overlay.topleft)
            + pygame.Vector2(2*Box.WIDTH + Box.PADDING, Box.HEIGHT/2),
            pygame.Vector2(self.dossier_overlay.topleft)
            + pygame.Vector2(0, Box.HEIGHT/2),
        ]
        pygame.draw.polygon(surface, Color.DOSSIER, tab)

        undersheets = [
            (-2, pygame.Vector2(-3, 4), Color.DOSSIER_PAPER_UNDERSIDE),
            (2, pygame.Vector2(4, 2), Color.DOSSIER_CARD),
        ]
        for angle, offset, color in undersheets:
            pygame.draw.polygon(
                surface,
                color,
                Box.get_rotated_rect_polygon(
                    self.dossier_page,
                    angle,
                    offset,
                ),
            )
        self.refresh_report_page_buttons()
        self.draw_dossier_page(surface)

        header_text = (
            "operation completed"
            if self.sortie_completed
            else "operation failed"
        )
        header_y = self.dossier_page.top + Box.PADDING
        font_registry["big_pixel"].render(
            surface,
            header_text,
            (
                self.dossier_page.centerx,
                header_y + font_registry["big_pixel"].font_height,
            ),
            Color.DOSSIER_INK,
            2,
            style="center",
        )
        pygame.draw.line(
            surface,
            Color.DOSSIER_RULE,
            (self.dossier_page.left + Box.PADDING, header_y + 32),
            (self.dossier_page.right - Box.PADDING, header_y + 32),
        )

        if self.report_page == 0:
            self.draw_sortie_rewards(surface, font_registry)
        else:
            self.draw_defeated_sirens(
                surface,
                font_registry,
                self.dossier_page.top + self.REWARDS_SECTION_TOP,
            )

        font_registry["big_pixel"].render(
            surface,
            f"sheet {self.report_page + 1:02d} of {self.REPORT_PAGE_COUNT:02d}",
            (self.dossier_page.centerx, self.dossier_page.bottom - Box.PADDING),
            Color.DOSSIER_RULE,
            1,
            style="center",
        )
        paperclip_sprite = DataFiles.sprites["props"]["diagonal_paperclip"]
        paperclip_rect = paperclip_sprite.get_rect()
        paperclip_rect.left = self.dossier_page.left - 20
        paperclip_rect.top = self.dossier_page.top - 20
        surface.blit(paperclip_sprite, paperclip_rect)
        self.draw_dossier_prev_page_fold(surface)

    def draw_sortie_rewards(self, surface, font_registry):
        font = font_registry["big_pixel"]
        section_left = self.dossier_page.left + Box.PADDING
        section_top = self.dossier_page.top + self.REWARDS_SECTION_TOP
        font.render(
            surface,
            "recovered materials",
            (section_left, section_top),
            Color.DOSSIER_RULE,
            1,
        )

        cards_top = section_top + font.font_height + Box.PADDING
        if not self.sortie_rewards:
            font.render(
                surface,
                "no materials recovered",
                (self.dossier_page.centerx, cards_top + Box.HEIGHT/2),
                Color.DOSSIER_RULE,
                2,
                style="center",
            )
            return cards_top + Box.HEIGHT

        cards_per_row = max(
            1,
            (self.dossier_page.width - Box.PADDING)
            // (Box.WIDTH + Box.PADDING),
        )
        for index, (reward, amount) in enumerate(self.sortie_rewards.items()):
            reward_rect = get_rect(
                width=Box.WIDTH,
                height=Box.HEIGHT,
                left=(
                    section_left
                    + (index % cards_per_row)*(Box.WIDTH + Box.PADDING)
                ),
                top=(
                    cards_top
                    + (index // cards_per_row)*(Box.HEIGHT + Box.PADDING)
                ),
            )
            pygame.draw.rect(
                surface,
                Color.DOSSIER_CARD_SHADOW,
                reward_rect.move(2, 2),
            )
            pygame.draw.rect(surface, Color.DOSSIER_CARD, reward_rect)
            reward_sprite = DataFiles.get_entity_sprite(reward)
            surface.blit(
                reward_sprite,
                reward_sprite.get_rect(center=reward_rect.center),
            )

            quantity_rect = pygame.Rect(
                reward_rect.left,
                reward_rect.bottom - 14,
                reward_rect.width,
                14,
            )
            pygame.draw.rect(surface, Color.DOSSIER_CARD, quantity_rect)
            pygame.draw.line(
                surface,
                Color.DOSSIER_RULE,
                quantity_rect.topleft,
                quantity_rect.topright,
            )
            font.render(
                surface,
                f"qty {amount:02d}",
                quantity_rect.center,
                Color.DOSSIER_INK,
                1,
                style="center",
            )
            pygame.draw.rect(
                surface,
                Color.DOSSIER_INK,
                reward_rect,
                width=1,
            )

        reward_rows = (
            len(self.sortie_rewards) + cards_per_row - 1
        ) // cards_per_row
        return (
            cards_top
            + reward_rows*Box.HEIGHT
            + (reward_rows - 1)*Box.PADDING
        )

    def draw_defeated_sirens(self, surface, font_registry, section_top):
        font = font_registry["big_pixel"]
        section_left = self.dossier_page.left + Box.PADDING
        font.render(
            surface,
            "enemy sirens sunk",
            (section_left, section_top),
            Color.DOSSIER_RULE,
            1,
        )

        cards_top = section_top + font.font_height + Box.PADDING
        if not self.defeated_sirens:
            font.render(
                surface,
                "no confirmed siren vessels sunk",
                (self.dossier_page.centerx, cards_top + Box.HEIGHT/2),
                Color.DOSSIER_RULE,
                2,
                style="center",
            )
            return

        card_width = self.SIREN_CARD_WIDTH
        cards_per_row = self.SIREN_CARDS_PER_ROW
        for index, ((siren_name, siren_level), amount) in enumerate(
            self.defeated_sirens.items()
        ):
            card_rect = get_rect(
                width=card_width,
                height=Box.HEIGHT,
                left=(
                    section_left
                    + (index % cards_per_row)*(card_width + Box.PADDING)
                ),
                top=(
                    cards_top
                    + (index // cards_per_row)*(Box.HEIGHT + Box.PADDING)
                ),
            )
            pygame.draw.rect(
                surface,
                Color.DOSSIER_CARD_SHADOW,
                card_rect.move(2, 2),
            )
            pygame.draw.rect(surface, Color.DOSSIER_CARD, card_rect)

            portrait_rect = get_rect(
                width=Box.WIDTH,
                height=Box.HEIGHT,
                left=card_rect.left,
                top=card_rect.top,
            )
            siren_sprite = DataFiles.get_entity_sprite(siren_name)
            surface.blit(
                siren_sprite,
                siren_sprite.get_rect(center=portrait_rect.center),
            )
            pygame.draw.line(
                surface,
                Color.DOSSIER_RULE,
                portrait_rect.topright,
                portrait_rect.bottomright,
            )

            text_left = portrait_rect.right + Box.PADDING
            font.render(
                surface,
                siren_name.replace("_", " "),
                (text_left, card_rect.top + Box.PADDING),
                Color.DOSSIER_INK,
                1,
            )
            font.render(
                surface,
                f"level {siren_level:02d}",
                (text_left, card_rect.top + Box.PADDING + 16),
                Color.DOSSIER_RULE,
                1,
            )
            font.render(
                surface,
                f"qty {amount:02d}",
                (text_left, card_rect.top + Box.PADDING + 32),
                Color.DOSSIER_INK,
                1,
            )
            pygame.draw.rect(
                surface,
                Color.DOSSIER_INK,
                card_rect,
                width=1,
            )

    def draw(self, surface, font_registry):
        self.background.draw(
            surface,
            font_registry,
            player_fleet=self.menu_manager.player_fleet,
            siren_fleet=self.menu_manager.siren_fleet,
            player_shipgirl_filter=(
                (lambda shipgirl: shipgirl.battle_component.hp > 0)
                if self.transition_active
                else None
            ),
        )
        self.vfx_manager.draw(surface, font_registry)

        if self.transition_active:
            self._draw_transition_overlay(surface, font_registry)
            return

        for shipgirl in self.menu_manager.player_fleet.fleet:
            if shipgirl is None:
                continue
            shipgirl.battle_component.draw_battlestation(surface, font_registry, shipgirl.rect)
        for siren in self.menu_manager.siren_fleet.fleet:
            siren.battle_component.draw_battlestation(surface, font_registry, siren.rect)

        self.menu_manager.player_fleet.draw_battle_effects(surface, self.vfx_manager)
        self.menu_manager.siren_fleet.draw_battle_effects(surface, self.vfx_manager)

        self.next_encounter_button.draw(surface, font_registry)
        self.open_reward_cache_button.draw(surface, font_registry)
        self.retreat_button.draw(surface, font_registry)
        self.draw_encounter_progress(surface)

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

        if self.return_to_port_button.active:
            self.draw_dossier_overlay(surface, font_registry)

        self.return_to_port_button.draw(surface, font_registry)
        
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
