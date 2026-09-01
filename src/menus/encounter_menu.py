from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from collections.abc import Callable
    from engine.types import CoordinateType, ColorType
    from engine.font import Font
    from src.menus.menu_manager import MenuManager
    from src.shipgirls import PlayerFleet, SirenFleet

import math
import random
import pygame

from engine.util import get_rect, get_vec
from engine.button import RectangularButton

from src.constants import DataFiles, Color, Box, Stats, screen_x, screen_y
from src.menus.base_menu import Menu
from src.menus.fleet_selection_menu import FleetNameRibbon
from src.menus.quests_data import (
    assign_quest,
    first_sortie_quest,
    construct_auxiliary_equipment_quest,
    complete_final_sortie_quest,
)
from src.shipgirls import Shipgirl, LAYER_SIZE
from src.vfx import VFXManager


class Cloud:
    SHADOW_OFFSET = pygame.Vector2(4, 8)

    def __init__(self, index: int, x: float, y: float, speed: float, cloud_sprites: list[pygame.Surface]):
        self.index = index
        self.sprite = cloud_sprites[index]
        self.shadow = DataFiles.sprites["background"][f"cloud_shadow{index}"]
        self.x = x
        self.y = y
        self.speed = speed

    def set_cloud_sprites(self, cloud_sprites: list[pygame.Surface]):
        """Set a new set of cloud sprites."""
        self.sprite = cloud_sprites[self.index]

    def update(self, dt: float):
        """Progress the x position of the cloud."""
        self.x = self.x + self.speed * dt

    def draw(self, surface: pygame.Surface):
        """Draw this cloud, along with its shadow subtractively beneath it."""
        shadow_rect = self.shadow.get_rect()
        shadow_rect.centerx = self.x + self.SHADOW_OFFSET.x
        shadow_rect.top = self.y + self.SHADOW_OFFSET.y
        surface.blit(self.shadow, shadow_rect, special_flags=pygame.BLEND_RGB_SUB)

        rect = self.sprite.get_rect()
        rect.centerx = self.x
        rect.top = self.y
        surface.blit(self.sprite, rect)


class SeaFoam:
    FADE_IN_DURATION = 0.5
    FADE_OUT_DURATION = 1.0
    HOLD_DURATION = 0.3
    CREST_X_RATIO = 1 / 4

    def __init__(self, sprite: pygame.Surface, wave_index: int, wave_rep_index: int, moving_left: bool):
        self.sprite = pygame.transform.flip(sprite, True, False) if moving_left else sprite.copy()
        self.moving_left = moving_left
        self.wave_index = wave_index
        self.wave_rep_index = wave_rep_index
        self.duration = self.FADE_IN_DURATION + self.HOLD_DURATION + self.FADE_OUT_DURATION
        self.lifetime = 0

    @property
    def expired(self):
        """Check if this sea foam's animation has expired."""
        return self.lifetime >= self.duration

    @property
    def alpha(self):
        """Get the opacity of the sea foam sprite."""
        if self.lifetime < self.FADE_IN_DURATION:
            return int(255 * self.lifetime / self.FADE_IN_DURATION)

        fade_out_start = self.FADE_IN_DURATION + self.HOLD_DURATION
        if self.lifetime > fade_out_start:
            fade_out_lifetime = self.lifetime - fade_out_start
            return int(255 * (1 - fade_out_lifetime / self.FADE_OUT_DURATION))

        return 255

    def update(self, dt):
        """Update the sea foam animation."""
        self.lifetime += dt

    def _align_rect(self, wave_rect: pygame.Rect):
        """Align the sea foam with the corresponding wave rect."""
        rect = self.sprite.get_rect()
        rect.top = wave_rect.top
        rect.left = wave_rect.left
        if self.moving_left:
            rect.left += int(2 * self.sprite.get_width() * self.CREST_X_RATIO - self.sprite.get_width())
        return rect

    def draw(self, surface: pygame.Surface, wave_rect: pygame.Rect):
        """Draw the sea foam."""
        rect = self._align_rect(wave_rect)
        self.sprite.set_alpha(self.alpha)
        surface.blit(self.sprite, rect)


class RainDrop:
    def __init__(self, pos: CoordinateType, color: ColorType, bottom: float):
        self.pos = pygame.Vector2(pos)
        self.color = color
        self.bottom = bottom
        self.length = random.uniform(18, 34)
        self.speed = random.uniform(520, 720)
        self.angle = math.radians(135 + random.uniform(-6, 6))

    @property
    def offscreen(self):
        """Check if this rain drop has fallen off-screen."""
        return self.pos.x < -self.length or self.pos.y > self.bottom + self.length

    def update(self, dt: float):
        """Update the animation of this rain drop."""
        self.pos += get_vec(self.speed * dt, self.angle)

    def draw(self, surface):
        """Draw this rain drop."""
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

    def __init__(
        self,
        sky_colors: list[ColorType],
        wave_sprites: list[pygame.Surface],
        cloud_sprites: list[pygame.Surface],
        rain_colors: list[ColorType]
    ):
        self.set_sky_colors(sky_colors)

        self.rain_colors = rain_colors
        self.raining = False
        self.rain_drops: list[RainDrop] = []
        self.rain_spawn_progress = 0

        self.night_sky_visible = False
        self.stars: list[tuple[pygame.Vector2, int, ColorType]] = []
        self.moon_pos = pygame.Vector2(screen_x(0.36), screen_y(0.12))

        self.wave_sprites = wave_sprites
        self.sea_foam_sprite = DataFiles.sprites["background"]["sea_foam"]
        self.sea_foams: list[SeaFoam] = []
        num_waves = DataFiles.sprites["background"]["num_waves"]
        self.wave_speeds: list[float] = [
            (wave_index + 1) / num_waves
            for wave_index in range(num_waves)
        ]
        self.sea_foam_spawned_this_rise: list[bool] = [False] * num_waves
        self.wave_ys: list[float] = [
            screen_y(0.5) + self.Y_GAP * (i - num_waves / 2) + 8
            for i in range(num_waves)
        ]
        self.wave_timers: list[float] = [
            math.radians(random.randint(0, 359))
            for _ in range(num_waves)
        ]

        self.cloud_sprites = cloud_sprites
        self.cloud_timer = 0
        self.cloud_spawn_time = 0
        self.clouds: list[Cloud] = []

    def set_sky_colors(self, sky_colors: list[ColorType]):
        """Set the sky color based on the weather conditions."""
        sky_surf = pygame.Surface((1, len(sky_colors)))
        for y, color in enumerate(sky_colors):
            sky_surf.set_at((0, y), color)
        self.sky_surf = pygame.transform.smoothscale(sky_surf, (128, 256))

    def set_wave_sprites(self, weather: str):
        """Set the wave sprites based on the weather conditions."""
        self.wave_sprites = DataFiles.sprites["background"]["wave_sets"][weather]

    @staticmethod
    def wave_vertical_offset(wave_timer: float):
        """Get the vertical offset of the wave."""
        return -math.cos(2 * wave_timer)

    @staticmethod
    def _wave_is_rising(wave_timer: float):
        """Determine if the wave is rising."""
        return math.sin(2 * wave_timer) < 0

    @classmethod
    def _sea_foam_is_ready(cls, wave_timer: float, wave_speed: float):
        """Determine if the sea foam is ready to be spawned.
        
        The sea foam should be spawned as the wave is rising, and with such a timing
        so that it reaches maximum opacity when the wave is at its peak.
        """
        if not cls._wave_is_rising(wave_timer):
            return False

        upcoming_crest = math.pi if wave_timer < math.pi else math.tau
        time_until_crest = (upcoming_crest - wave_timer) / wave_speed
        return time_until_crest <= SeaFoam.FADE_IN_DURATION

    def set_cloud_sprites(self, weather: str):
        """Set the cloud sprites based on weather conditions."""
        self.cloud_sprites = DataFiles.sprites["background"]["cloud_sets"][weather]
        for cloud in self.clouds:
            cloud.set_cloud_sprites(self.cloud_sprites)

    def set_rain(self, raining: bool, rain_colors: list[ColorType]):
        """Set the raining animation state based on weather conditions."""
        self.raining = raining
        self.rain_colors = rain_colors
        if not self.raining:
            self.rain_drops = []
            self.rain_spawn_progress = 0

    def set_night_sky(self, visible: bool):
        """Set the night sky background based on weather conditions."""
        self.night_sky_visible = visible
        if self.night_sky_visible:
            self._generate_stars()
        else:
            self.stars = []

    def _generate_stars(self):
        """Generate stars randomly in the night sky."""
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

    def update(self, dt: float):
        """Update the background animations."""
        # Waves move in a sinusoidal shape.
        self.wave_timers = [
            (wave_timer + wave_speed * dt) % math.tau
            for wave_timer, wave_speed in zip(self.wave_timers, self.wave_speeds)
        ]

        # Spawn, update, and despawn rain drops.
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

        # Spawn, update, and despawn clouds.
        # Clouds scroll horizontally through the sky.
        self.cloud_timer += dt
        if self.cloud_timer > self.cloud_spawn_time:
            move_right = bool(random.randint(0, 1))
            self.clouds.append(Cloud(
                index=random.randint(1, DataFiles.sprites["background"]["num_clouds"])-1,
                x=0 if move_right else screen_x(1),
                y=random.uniform(-64, 64),
                speed=random.uniform(32, 64) * (1 if move_right else -1),
                cloud_sprites=self.cloud_sprites,
            ))
            self.cloud_timer = 0
            self.cloud_spawn_time = random.uniform(5, 10)
        for cloud in self.clouds:
            cloud.update(dt)
        cloud_width = 128
        self.clouds = [
            cloud for cloud in self.clouds
            if cloud.x >= -cloud_width
            and cloud.x <= screen_x(1) + cloud_width
        ]

        # Update, despawn, and spawn sea foams.
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
            # Sea foam spawns from a rising wave.
            if not self._wave_is_rising(wave_timer):
                self.sea_foam_spawned_this_rise[wave_index] = False
                continue
            # Sea foam spawns exactly when the wave is at a distance away
            # where the sea foam will reach full opacity at the wave peak.
            # A sea foam should be spawned once per wave strip..
            if (
                not self.sea_foam_spawned_this_rise[wave_index]
                and self._sea_foam_is_ready(wave_timer, wave_speed)
            ):
                self.sea_foams.append(SeaFoam(
                    self.sea_foam_sprite,
                    wave_index,
                    wave_rep_index=random.randrange(self.NUM_WAVE_REPS),
                    moving_left=math.cos(wave_timer) < 0,
                ))
                self.sea_foam_spawned_this_rise[wave_index] = True

    def draw(
        self,
        surface: pygame.Surface,
        font_registry: dict[str, Font],
        player_fleet: PlayerFleet | None = None,
        siren_fleet: SirenFleet | None = None,
        player_shipgirl_filter: Callable[[Shipgirl], bool] | None = None,
    ):
        """Draw the background.
        
        If the PlayerFleet or SirenFleet are provided, then render the shipgirls or sirens among
        the wave strips, so that they feel embedded into the theme.
        If player_shipgirl_filter is provided, render only the shipgirls passing this filter.
        """
        # The sky surf is not wider enough to fill the whole screen, so it is repeated
        # horizontally to completely fill the background.
        sky_surf = self.sky_surf
        sky_surf_rect = sky_surf.get_rect()
        sky_surf_rect.top = 0
        num_sky_reps = 9
        sky_rep_offset = (num_sky_reps - 1) / 2
        for i in range(num_sky_reps):
            sky_surf_rect.centerx = screen_x(0.5) + sky_surf_rect.width * (i - sky_rep_offset)
            surface.blit(sky_surf, sky_surf_rect)

        # Draw stars and moon.
        if self.night_sky_visible:
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

        for cloud in self.clouds:
            cloud.draw(surface)

        # Draw the background landmarks.
        landmark_y = self.wave_ys[0] + 4

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

        # Compute the draw indices of the siren and player fleets.
        # The draw indices tell the renderer at which wave index the
        # shipgirl or siren should be drawn before.
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

        num_waves = DataFiles.sprites["background"]["num_waves"]
        num_wave_reps = self.NUM_WAVE_REPS
        wave_rep_offset = (num_wave_reps - 1) / 2
        for i, (wave_y, wave_timer) in enumerate(zip(self.wave_ys, self.wave_timers)):
            # Draw the shipgirl and sirens at this wave index before the wave itself.
            if shipgirl_draw_indices is not None:
                for draw_index, shipgirl in shipgirl_draw_indices:
                    if i == draw_index:
                        shipgirl.draw(surface, font_registry)

            if siren_draw_indices is not None:
                for draw_index, siren in siren_draw_indices:
                    if i == draw_index:
                        siren.draw(surface, font_registry)
            # The horizontal motion of the wave is a sine wave.
            # The wave motion is in such a way that it reaches its crest in
            # the middle of its horizontal motion in both directions.
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
            # The wave strips are not wide enough for the whole screen, so we repeat
            # their rendering to fill the whole horizontal space.
            # The sea foam is also rendered onto the correct wave rep index.
            for j in range(num_wave_reps):
                wave_rect.centerx = centerx + wave_rect.width * (j - wave_rep_offset)
                surface.blit(wave, wave_rect)
                for sea_foam in self.sea_foams:
                    if sea_foam.wave_index == i and sea_foam.wave_rep_index == j:
                        sea_foam.draw(surface, wave_rect)

        for rain_drop in self.rain_drops:
            rain_drop.draw(surface)


class Drop:
    def __init__(self, item: str, pos: pygame.Vector2):
        self.item = item
        self.pos = pos
        self.bottom = pos.y + 50
        self.vel = get_vec(100, math.radians(random.uniform(-15, 15) - 90))

    def update(self, dt: float):
        """Update the drop item.
        
        The item moves in a parabolic arc, initially going upwards then eventually
        falling down to a maximum bottom position and coming to rest.
        """
        if self.pos.y < self.bottom:
            self.pos = self.pos + self.vel * dt
            self.pos.y = min(self.pos.y, self.bottom)
            self.vel = self.vel + pygame.Vector2(0, 200) * dt
    
    def draw(self, surface: pygame.Surface, font_registry: dict[str, Font]):
        """Draw the drop item."""
        image = DataFiles.get_entity_sprite(self.item)
        rect = image.get_rect()
        rect.center = self.pos
        surface.blit(image, rect)


class EncounterMenu(Menu):
    TRANSITION_IDLE = "idle"
    TRANSITION_EXITING = "exiting"
    TRANSITION_WAVE_COVER = "wave_cover"
    TRANSITION_WAVE_REVEAL = "wave_reveal"
    TRANSITION_ENTERING = "entering"

    TRANSITION_MOVE_SPEED = 200
    TRANSITION_WAVE_DURATION = 1.5
    TRANSITION_WAVE_INDICES = (3, 2, 0)
    TRANSITION_WAVE_STAGGERS = (0.0, 0.12, 0.24)
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

    def __init__(self, menu_manager: MenuManager):
        self.menu_manager = menu_manager

        self.weather_condition = "daytime"

        # Player controls.
        self.mouse_start_drag: CoordinateType | None = None
        self.selected_shipgirl: Shipgirl | None = None
        self.selected_shipgirl_index: int | None = None

        # Sortie and encounter metadata.
        self.current_sortie = 0
        self.current_encounter = 0

        # Sortie and encounter end state.
        self.encounter_started = False
        self.sortie_completed = False
        self.sortie_suspended = False
        self.end_encounter_banner = FleetNameRibbon(pygame.Vector2(screen_x(0.5), screen_y(0.1)), "")
        self.encounter_has_not_ended = True
        self.defeat_pending = False

        self.vfx_manager = VFXManager()

        # Transition state.
        self.transition_state = self.TRANSITION_IDLE
        self.transition_timer = 0
        self.transition_shipgirls: list[Shipgirl] = []
        self.transition_slot_positions: dict[Shipgirl, pygame.Rect] = {}
        self.transition_starts_sortie = False
        self.transition_to_port = False
        self.transition_port_callback: Callable = None
        self.opened_reward_report_timer: float = None

        def next_encounter():
            self._start_encounter_transition()

        button_size = 48
        button_sprite = DataFiles.sprites["user_interface"]["next"]
        button_rect = get_rect(
            width=button_size, height=button_size,
            right=Box.RIGHT_OF_SCREEN, centery=screen_y(0.5)
        )
        self.next_encounter_button = RectangularButton(
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
                self._add_sortie_drop(
                    reward,
                    pygame.Vector2(self.open_reward_cache_button.rect.center),
                    amount,
                )
            self._claim_drops()

            self.return_to_port_button.active = True

            DataFiles.sfx["open"].play()

        button_sprite = DataFiles.sprites["user_interface"]["closed_reward_cache"]
        button_rect = button_sprite.get_rect()
        self.open_reward_cache_button = RectangularButton(
            button_rect,
            open_reward_cache,
            active=False,
            background_styling={"background_img": button_sprite}
        )

        # End of sortie report card.
        # The size of the report is based on the maximum number of sirens
        # in any encounter, so that the sizing of the card is the same for all sorties
        # and is capable of housing the results of any sortie.
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
        # Dossier-themed page.
        report_page_width = (
            2 * Box.PADDING
            + self.SIREN_CARDS_PER_ROW * self.SIREN_CARD_WIDTH
            + (self.SIREN_CARDS_PER_ROW - 1) * Box.PADDING
        )
        report_page_height = (
            self.REWARDS_SECTION_TOP
            + 2 * Box.PADDING
            + max_siren_rows * Box.HEIGHT
            + (max_siren_rows - 1) * Box.PADDING
            + 3 * Box.PADDING
        )
        self.dossier_overlay = get_rect(
            width=report_page_width + 2 * Box.PADDING,
            height=report_page_height + 2 * Box.PADDING + Box.HEIGHT / 2,
            center=(screen_x(0.5), screen_y(0.5)),
        )
        self.dossier_bg = self.dossier_overlay.inflate(0, -Box.HEIGHT / 2)
        self.dossier_bg.bottom = self.dossier_overlay.bottom
        self.dossier_page = self.dossier_bg.inflate(-2 * Box.PADDING, -2 * Box.PADDING)

        def finish_return_to_port():
            if self.sortie_completed:
                new_sortie_progress = self.current_sortie + 1
                if DataFiles.save_file["sortie_progress"] < new_sortie_progress:
                    DataFiles.save_file["sortie_progress"] = new_sortie_progress
                    # Assign quests whose triggers are based on completing certain sorties.
                    if new_sortie_progress == 11:
                        assign_quest(self.menu_manager, construct_auxiliary_equipment_quest)
                    if new_sortie_progress == len(DataFiles.sortie_data) - 2:
                        assign_quest(self.menu_manager, complete_final_sortie_quest)

                # Update chapter progress and disperse the fog on the new chapter if
                # the player has unlocked that new chapter.
                new_chapter_progress = DataFiles.sortie_data[new_sortie_progress]["chapter"]
                if DataFiles.save_file["chapter_progress"] < new_chapter_progress:
                    DataFiles.save_file["chapter_progress"] = new_chapter_progress
                    self.menu_manager.sortie_selection_menu.fogs[new_chapter_progress].disperse = True
                
                self.menu_manager.sortie_selection_menu.sortie_nodes[new_sortie_progress].unlocked = True
                self.menu_manager.sortie_selection_menu.sortie_nodes[self.current_sortie].cleared = True
                self.menu_manager.port_menu.update_encountered_sirens()

            self.menu_manager.current_menu = self.menu_manager.port_menu
            DataFiles.sfx["waves"].fadeout(3000)
            self.vfx_manager.clear()
            self.fast_forward = False
            self.slow_down = False

            self.menu_manager.encounter_menu.return_to_port_button.active = False

        button_rect = get_rect(
            width=2 * Box.WIDTH + 2 * Box.PADDING,
            height=2 * Box.HEIGHT + 2 * Box.PADDING,
            right=self.dossier_page.right + Box.WIDTH + Box.PADDING,
            centery=self.dossier_page.top,
        )
        self.return_to_port_button = RectangularButton(
            button_rect,
            lambda : self._start_port_transition(finish_return_to_port),
            active=False,
        )

        # Report pagination controls.
        self.report_page = 0
        self.report_page_prev_button = RectangularButton(
            get_rect(
                width=button_size,
                height=button_size,
                left=self.dossier_page.left,
                top=self.dossier_page.top,
            ),
            lambda: self._change_report_page(-1),
            active=False,
        )
        self.report_page_next_button = RectangularButton(
            get_rect(
                width=button_size,
                height=button_size,
                right=self.dossier_page.right,
                bottom=self.dossier_page.bottom,
            ),
            lambda: self._change_report_page(1),
            active=False,
        )

        def retreat():
            self.menu_manager.player_fleet.end_encounter()
            self.menu_manager.siren_fleet.end_encounter()
            self.vfx_manager.clear()
            self.fast_forward = False
            self.slow_down = False

            self.encounter_has_not_ended = False
            self.defeat_pending = False
            self.encounter_started = False
            self.end_encounter_banner.text = ""
            self.next_encounter_button.active = False
            self.open_reward_cache_button.active = False
            self.retreat_button.active = False
            self.sortie_suspended = True
            self.report_page = 0
            self.return_to_port_button.active = True
            self._refresh_report_page_buttons()

        button_sprite = DataFiles.sprites["user_interface"]["port"]
        button_rect = get_rect(
            width=button_size, height=button_size,
            right=Box.RIGHT_OF_SCREEN, top=Box.TOP_OF_SCREEN
        )
        self.retreat_button = RectangularButton(
            button_rect,
            retreat,
            background_styling={
                "background_color": Color.BLACK,
                "background_img": button_sprite,
                "opacity": 160
            },
            hover_styling={"opacity": 200}
        )

        # Data for the report.
        self.drops: list[Drop] = []
        self.sortie_rewards: dict[str, int] = {}
        self.defeated_sirens: dict[tuple[str, int], int] = {}
        self.research_exp = 0
        self.exp_timer = 0

        # Dev controls.
        self.fast_forward = False
        self.slow_down = False

        # Primary and backup fleet slots for shipgirl sprites.
        num_fleet_slots = 3
        fleet_slot_offset = (num_fleet_slots - 1) / 2
        self.fleet_slots = [
            get_rect(
                width=LAYER_SIZE, height=LAYER_SIZE,
                centerx=screen_x(0.275) + LAYER_SIZE - (slot_index - fleet_slot_offset) * LAYER_SIZE / 2,
                centery=screen_y(0.5) + (slot_index - fleet_slot_offset) * LAYER_SIZE
            ) for slot_index in range(num_fleet_slots)
        ]
        self.backup_fleet_slots = [
            get_rect(
                width=LAYER_SIZE, height=LAYER_SIZE,
                centerx=slot.centerx - 2 * LAYER_SIZE,
                centery=slot.centery,
            ) for slot in self.fleet_slots
        ]

        self.background = Background(
            self.TIME_WEATHER_STYLES[self.weather_condition]["sky_colors"],
            DataFiles.sprites["background"]["wave_sets"][self.weather_condition],
            DataFiles.sprites["background"]["cloud_sets"][self.weather_condition],
            self.SHIPGIRL_WAKE_COLORS["stormy"],
        )
        self._apply_time_weather_style()

    @property
    def transition_active(self):
        """Check if the transition is active."""
        return self.transition_state != self.TRANSITION_IDLE

    def _set_transition_state(self, state: str):
        """Set the transition state."""
        self.transition_state = state
        self.transition_timer = 0

    def _prepare_transition_shipgirls(self):
        # Get the slot positions corresponding to each shipgirl.
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
        self.transition_slot_positions = slot_positions

        # Get the shipgirls that are still afloat.
        self.transition_shipgirls = [
            shipgirl
            for shipgirl in self.transition_slot_positions
            if shipgirl.battle_component.hp > 0
        ]
        for shipgirl in self.transition_shipgirls:
            shipgirl.facing_left = False
            shipgirl.sprite.set_animation(shipgirl.sprite.SAIL_ANIMATION)

    def _position_transition_shipgirls_for_entry(self):
        """Position the shipgirl on the left side of the screen.
        
        This is for the entrance phase of the transition.
        """
        # Set the shipgirls to their target as a fallback.
        # This will be overriden if the transition is active.
        for shipgirl, target in self.transition_slot_positions.items():
            shipgirl.rect.center = target

        if not self.transition_shipgirls:
            return

        rightmost_edge = max(
            self.transition_slot_positions[shipgirl].x
            + shipgirl.rect.width / 2
            for shipgirl in self.transition_shipgirls
        )
        entry_offset = -rightmost_edge
        for shipgirl in self.transition_shipgirls:
            target = self.transition_slot_positions[shipgirl]
            shipgirl.rect.center = target + pygame.Vector2(entry_offset, 0)
            shipgirl.facing_left = False
            shipgirl.sprite.set_animation(shipgirl.sprite.SAIL_ANIMATION)

    def start_sortie_transition(self):
        """Begin the transition from the fleet selection menu to the encounter menu."""
        if self.transition_active:
            return

        # Choose the encounter weather before the wipe starts so the same
        # palette is used on both sides of the menu handoff.
        self._roll_time_weather()
        self.transition_starts_sortie = True
        self.transition_to_port = False
        self.transition_port_callback = None
        self.transition_shipgirls = []
        self.transition_slot_positions = {}
        self._set_transition_state(self.TRANSITION_WAVE_COVER)

    def _start_port_transition(self, destination_callback: Callable):
        """Begin the transition from the encounter menu to the port menu."""
        if self.transition_active:
            return

        self.mouse_start_drag = None
        self.selected_shipgirl = None
        self.selected_shipgirl_index = None
        self.transition_starts_sortie = False
        self.transition_to_port = True
        self.transition_port_callback = destination_callback
        self.transition_shipgirls = []
        self.transition_slot_positions = {}
        self._set_transition_state(self.TRANSITION_WAVE_COVER)

    def _start_encounter_transition(self):
        """Begin the transition between encounters."""
        if self.transition_active:
            return

        self._claim_drops()

        # Hide buttons during the transition.
        # The player is not able to interact with the game during the
        # transition and must wait for it to finish.
        self.next_encounter_button.active = False
        self.open_reward_cache_button.active = False
        self.return_to_port_button.active = False
        self.retreat_button.active = False
        self.report_page_prev_button.active = False
        self.report_page_next_button.active = False

        self.mouse_start_drag = None
        self.selected_shipgirl = None
        self.selected_shipgirl_index = None

        self.transition_starts_sortie = False
        self.transition_to_port = False
        self.transition_port_callback = None
        self._prepare_transition_shipgirls()
        self._set_transition_state(self.TRANSITION_EXITING)

    def _load_transition_destination(self):
        """Load the transition destination.
        
        There are three possible destinations: the port menu, the first encounter,
        or the next encounter, each with different handling logic.
        """
        if self.transition_to_port:
            destination_callback = self.transition_port_callback
            self.transition_port_callback = None
            destination_callback()
            return

        if self.transition_starts_sortie:
            self.menu_manager.player_fleet.begin_sortie()
            self._begin_sortie()
            self._prepare_transition_shipgirls()
            self._position_transition_shipgirls_for_entry()
            self.menu_manager.current_menu = self
            return

        self.current_encounter += 1
        self._begin_encounter()
        self._position_transition_shipgirls_for_entry()

    def _finish_encounter_transition(self):
        """Complete the encounter transition."""
        for shipgirl in self.transition_shipgirls:
            shipgirl.rect.center = self.transition_slot_positions[shipgirl]
            shipgirl.facing_left = False
            shipgirl.sprite.set_animation(shipgirl.sprite.IDLE_ANIMATION)

        self.transition_shipgirls = []
        self.transition_slot_positions = {}
        self.transition_starts_sortie = False
        self.transition_to_port = False
        self.transition_port_callback = None
        self._set_transition_state(self.TRANSITION_IDLE)

    def _update_transition_shipgirl_animation(self, dt: float):
        """Animate shipgirls during transitions."""
        for shipgirl in self.transition_shipgirls:
            shipgirl.sprite.set_animation(shipgirl.sprite.SAIL_ANIMATION)
            shipgirl.animate(dt)

    def _update_encounter_transition(self, dt: float):
        """Update the encounter transition, based on the current transition state."""
        state = self.transition_state

        # In this state, the shipgirls will move right until they are off-screen.
        # This transition state is only met between encounters, meaning no sirens
        # are alive and hence do not need to be animated.
        if state == self.TRANSITION_EXITING:
            distance = self.TRANSITION_MOVE_SPEED * dt
            for shipgirl in self.transition_shipgirls:
                shipgirl.rect.centerx += distance
            self._update_transition_shipgirl_animation(dt)
            if not self.transition_shipgirls or all(
                shipgirl.rect.left >= screen_x(1)
                for shipgirl in self.transition_shipgirls
            ):
                self._set_transition_state(self.TRANSITION_WAVE_COVER)

        # In this state, a wave animation rises to cover the screen.
        # The state is the entrypoint for the fleet selection -> encounter menu
        # transition, and also occurs after shipgirls have exited from the right side.
        # No animations are needed.
        # Once the wave fully covers the screen, the destination can be loaded.
        elif state == self.TRANSITION_WAVE_COVER:
            self.transition_timer += dt
            if self.transition_timer >= self.TRANSITION_WAVE_DURATION:
                self._load_transition_destination()
                self._set_transition_state(self.TRANSITION_WAVE_REVEAL)

        # In this state, the same wave animation crashes down to reveal the screen.
        # If the player is returning to the port menu, this is the terminal transition state.
        # Otherwise, the new destination is revealed and the next phase of the transition
        # is started.
        elif state == self.TRANSITION_WAVE_REVEAL:
            self.transition_timer += dt
            if self.transition_timer >= self.TRANSITION_WAVE_DURATION:
                if self.transition_to_port:
                    self._finish_encounter_transition()
                else:
                    self._set_transition_state(self.TRANSITION_ENTERING)

        # In this state, the shipgirls enter from the left side of the screen
        # and move until they are in position.
        # The shipgirls need to be animated, as do the sirens of the new encounter
        # that have been spawned in already.
        elif state == self.TRANSITION_ENTERING:
            distance = self.TRANSITION_MOVE_SPEED * dt
            for shipgirl in self.transition_shipgirls:
                target_x = self.transition_slot_positions[shipgirl].x
                shipgirl.rect.centerx = min(
                    target_x,
                    shipgirl.rect.centerx + distance,
                )
            self._update_transition_shipgirl_animation(dt)
            self.menu_manager.siren_fleet.animate(dt)
            if not self.transition_shipgirls or all(
                shipgirl.rect.centerx >= self.transition_slot_positions[shipgirl].x
                for shipgirl in self.transition_shipgirls
            ):
                self._finish_encounter_transition()

        # The shipgirls are on-screen and have a rightward sailing animation, so wakes
        # need to be spawned.
        if self.transition_state in (
            self.TRANSITION_EXITING,
            self.TRANSITION_ENTERING,
        ):
            self._spawn_shipgirl_wakes(self.menu_manager.player_fleet, True)

        self.vfx_manager.update(dt)

    def _roll_time_weather(self):
        """Generate a random weather condition and apply the weather style."""
        weather_names = list(self.TIME_WEATHER_STYLES.keys())
        weather_weights = [
            self.TIME_WEATHER_STYLES[weather_name]["weight"]
            for weather_name in weather_names
        ]
        self.weather_condition = random.choices(weather_names, weights=weather_weights, k=1)[0]
        self._apply_time_weather_style()

    def _apply_time_weather_style(self):
        """Apply the style of the weather condition to the background."""
        weather_style = self.TIME_WEATHER_STYLES[self.weather_condition]
        self.vfx_manager.wave_colors = self.SHIPGIRL_WAKE_COLORS[self.weather_condition]
        self.background.set_sky_colors(weather_style["sky_colors"])
        self.background.set_wave_sprites(self.weather_condition)
        self.background.set_cloud_sprites(self.weather_condition)
        self.background.set_rain(
            self.weather_condition == "stormy",
            self.SHIPGIRL_WAKE_COLORS["stormy"],
        )
        self.background.set_night_sky(self.weather_condition == "nighttime")

    def _begin_sortie(self):
        """Begin a new sortie."""
        self.transition_state = self.TRANSITION_IDLE
        self.transition_timer = 0
        self.transition_shipgirls = []
        self.transition_slot_positions = {}
        self.transition_starts_sortie = False
        self.transition_to_port = False
        self.transition_port_callback = None
        self.opened_reward_report_timer = None

        self.open_reward_cache_button.active = False
        self.return_to_port_button.active = False
        self.sortie_completed = False
        self.sortie_suspended = False
        self.sortie_rewards = {}
        self.defeated_sirens = {}
        self.report_page = 0
        self._refresh_report_page_buttons()

        self._begin_encounter()

    def _add_sortie_drop(self, item: str, pos: CoordinateType, amount: int = 1):
        """Create amount number of drops of this item."""
        for _ in range(amount):
            self.drops.append(Drop(
                item,
                pygame.Vector2(pos),
            ))

    def _claim_drops(self):
        """Add the drop items to the player inventory."""
        for drop in self.drops:
            DataFiles.save_file["inventory"][drop.item] = (
                DataFiles.save_file["inventory"].get(drop.item, 0) + 1
            )
            self.sortie_rewards[drop.item] = (
                self.sortie_rewards.get(drop.item, 0) + 1
            )

    def _begin_encounter(self):
        """Begin a new encounter."""
        self.drops = []
        self.next_encounter_button.active = False
        self.vfx_manager.clear()
        self.defeat_pending = False
        self.opened_reward_report_timer = None

        sortie_data = DataFiles.sortie_data[self.current_sortie]
        num_encounters = len(sortie_data["encounters"])
        self.end_encounter_banner.text = ""
        # The current encounter is the number of encounters, meaning that
        # this is not actually an encounter but is instead the reward room.
        if self.current_encounter == num_encounters:
            self.sortie_completed = True
            self.open_reward_cache_button.active = True
            if self.current_sortie < DataFiles.save_file["sortie_progress"]:
                # If this sortie has already been cleared, then the rewards have already
                # been cleared.
                # After a brief delay, open the end of sortie report.
                # Do not allow the player to claim rewards again.
                self.return_to_port_button.active = False
                self.opened_reward_report_timer = (
                    self.OPENED_REWARD_REPORT_DELAY
                )
                self.open_reward_cache_button.background_img = DataFiles.sprites["user_interface"]["open_reward_cache"]
            else:
                self.open_reward_cache_button.background_img = DataFiles.sprites["user_interface"]["closed_reward_cache"]

            self.menu_manager.siren_fleet.front = []
            self.menu_manager.siren_fleet.back = []
            return
        
        self.encounter_has_not_ended = True
        self.retreat_button.active = True

        encounter_data = sortie_data["encounters"][self.current_encounter]
        self.menu_manager.siren_fleet.front = [Shipgirl(siren_name, False) for siren_name in encounter_data["front"]]
        self.menu_manager.siren_fleet.back = [Shipgirl(siren_name, False) for siren_name in encounter_data["back"]]
        for siren in self.menu_manager.siren_fleet.fleet:
            siren.facing_left = True
        self.menu_manager.player_fleet.begin_encounter()
        self.menu_manager.siren_fleet.begin_encounter()

        self.encounter_started = False

    def _spawn_shipgirl_wakes(self, fleet: PlayerFleet | SirenFleet, is_player: bool):
        """Spawn wake vfx for the shipgirls/sirens in the fleet.
        
        The is_player flag controls which direction the wakes spawn in.
        """
        for shipgirl in fleet.fleet:
            if shipgirl.battle_component.hp <= 0:
                continue

            wake_pos = pygame.Vector2(
                (
                    shipgirl.rect.centerx
                    + (-1 if is_player else 1)
                    * random.uniform(-shipgirl.rect.width * 0.1, shipgirl.rect.width * 0.3)
                ),
                shipgirl.rect.bottom - random.uniform(11, 16),
            )
            wake_angle = 0 if is_player else math.radians(180)
            self.vfx_manager.spawn_wake(
                wake_pos,
                wake_angle,
                wake_colors=self.SHIPGIRL_WAKE_COLORS[self.weather_condition],
                **self.SHIPGIRL_WAKE_CONFIG,
            )

    def update(self, dt: float, events: list[pygame.Event]):
        """Update the encounter menu."""
        # Update the background.
        # The reward cache moves with the wave, which makes it look as if it is drifting
        # in the ocean.
        self.background.update(dt)

        middle_wave_timer = self.background.wave_timers[3]
        horizontal_movement = 72
        vertical_movement = 12
        self.open_reward_cache_button.rect.center = (
            pygame.Vector2(screen_x(0.75), screen_y(0.575))
            + pygame.Vector2(
                horizontal_movement * math.sin(middle_wave_timer),
                vertical_movement * self.background.wave_vertical_offset(middle_wave_timer),
            )
        )

        if self.transition_active:
            self._update_encounter_transition(dt)
            return

        # If the reward has already been opened, after a delay, show the report.
        if self.opened_reward_report_timer is not None:
            self.opened_reward_report_timer = max(
                0,
                self.opened_reward_report_timer - dt,
            )
            if self.opened_reward_report_timer == 0:
                self.opened_reward_report_timer = None
                self.return_to_port_button.active = True

        self._refresh_report_page_buttons()
        for event in events:
            if event.type == pygame.MOUSEMOTION:
                buttons: list[RectangularButton] = [
                    self.next_encounter_button,
                    self.retreat_button,
                    self.return_to_port_button,
                    self.report_page_prev_button,
                    self.report_page_next_button
                ]
                for button in buttons:
                    button.hover(event.pos)
            if event.type == pygame.MOUSEBUTTONDOWN:
                for i, shipgirl in enumerate(self.menu_manager.player_fleet.shipgirls):
                    # The player controls which target the shipgirl is attacking by clicking and
                    # dragging from that shipgirl onto the desired target.
                    # Prevent the player from changing the shipgirl target if the shipgirl
                    # is locked in the attack animation / is attacking.
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
                # If the player drags the shipgirl onto a siren target, then the shipgirl
                # will target that siren.
                if self.selected_shipgirl is not None:
                    for siren in self.menu_manager.siren_fleet.fleet:
                        if not siren.rect.collidepoint(mouse_end_drag):
                            continue
                        click = True
                        # Melee ships (DD, CL, SS) cannot attack sirens in the back row
                        # unless the front row is completely sunk.
                        if self.selected_shipgirl.battle_component.hull_type in self.MELEE_SHIPS:
                            if siren in self.menu_manager.siren_fleet.afloat_front:
                                self.selected_shipgirl.battle_component.target = siren
                        else:
                            self.selected_shipgirl.battle_component.target = siren
                        self.selected_shipgirl = None
                        self.selected_shipgirl_index = None
                # If the player drags the shipgirl onto a shipgirl in the backup fleet,
                # then the shipgirls swap positions.
                if self.selected_shipgirl is not None:
                    for i, backup_shipgirl in enumerate(self.menu_manager.player_fleet.backups):
                        # Do not allow the swap if the backup shipgirl is already sunk.
                        # Note that the player is able to swap OUT a sunk shipgirl.
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

                    # The sirens should not be able to target the shipgirl that was just swapped out.
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
                elif self.open_reward_cache_button.click(event.pos):
                    self.open_reward_cache_button.background_img = DataFiles.sprites["user_interface"]["open_reward_cache"]

            # Dev controls.
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_f:
                    self.fast_forward = not self.fast_forward
                if event.key == pygame.K_d:
                    self.slow_down = not self.slow_down
        if self.fast_forward:
            dt = dt * 2
        if self.slow_down:
            dt = dt / 2

        self.menu_manager.player_fleet.animate(dt)
        self.menu_manager.siren_fleet.animate(dt)

        if self.encounter_started:
            # Check which sirens were defeated this frame.
            # If this is not the first clear of this sortie, then sirens are capable of dropping
            # loot randomly.
            afloat_sirens_before = [siren for siren in self.menu_manager.siren_fleet.fleet if siren.battle_component.hp > 0]
            self.menu_manager.player_fleet.update(dt, self.vfx_manager)
            afloat_sirens_after = [siren for siren in self.menu_manager.siren_fleet.fleet if siren.battle_component.hp > 0]
            if self.current_sortie < DataFiles.save_file["sortie_progress"]:
                defeated_sirens = [siren for siren in afloat_sirens_before if siren not in afloat_sirens_after]
                for siren in defeated_sirens:
                    siren_data = DataFiles.siren_data[siren.name]
                    for drop, drop_rate in siren_data["drops"].items():
                        if random.randint(0, 99) < drop_rate:
                            self._add_sortie_drop(drop, siren.rect.center)
            self.menu_manager.siren_fleet.update(dt, self.menu_manager, self.vfx_manager)

            for drop in self.drops:
                drop.update(dt)
        else:
            # Gating for the first sortie quest.
            # The player is shown a tutorial of the game mechanics, so the encounter
            # does not start until the player learns the game mechanics first.
            if (
                self.current_encounter == 0
                and first_sortie_quest.quest_id in self.menu_manager.quest_manager.started_quests
            ):
                # All of the players shipgirls must be targetting a siren for the encounter to start.
                self.encounter_started = all(
                    shipgirl.battle_component.target is not None
                    for shipgirl in self.menu_manager.player_fleet.shipgirls
                    if shipgirl is not None
                )
            else:
                # Only one shipgirl needs to have a target for the encounter to start.
                # This will allow the player some leeway, so the game remains paused if they have
                # not chosen at least one target, which might mean the player is AFK.
                self.encounter_started = any(
                    shipgirl.battle_component.target is not None
                    for shipgirl in self.menu_manager.player_fleet.shipgirls
                    if shipgirl is not None
                )

        # Logic for animating the research exp widget.
        if self.research_exp > 0:
            self.exp_timer += dt
            if self.exp_timer > 1:
                self.exp_timer = 1
                # Check the research exp obtained and drop the unique item if the required exp
                # threshold was reached.
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
                    unique_item = DataFiles.shipgirl_data[research_target]["unique_item"]
                    if DataFiles.save_file["inventory"].get(unique_item, 0) == 0:
                        self._add_sortie_drop(
                            unique_item,
                            (screen_x(0.5), screen_y(0.5)),
                        )
                self.research_exp = 0
        elif self.exp_timer > 0:
            self.exp_timer -= dt
            if self.exp_timer < 0:
                self.exp_timer = 0

        # The encounter can only end once, to prevent duplication.
        if self.encounter_has_not_ended:
            # Defeat condition.
            if not self.menu_manager.player_fleet.afloat:
                self.encounter_has_not_ended = False
                self.end_encounter_banner.text = ""
                self.menu_manager.player_fleet.end_encounter()
                self.menu_manager.siren_fleet.end_encounter()
                self.retreat_button.active = False
                self.defeat_pending = True
            # Victory condition.
            if not self.menu_manager.siren_fleet.afloat:
                self.encounter_has_not_ended = False
                self.end_encounter_banner.text = "victory"
                for siren in self.menu_manager.siren_fleet.fleet:
                    # Track defeated sirens.
                    siren_level = Stats.level(siren.battle_component.exp)
                    siren_key = (siren.name, siren_level)
                    self.defeated_sirens[siren_key] = (
                        self.defeated_sirens.get(siren_key, 0) + 1
                    )
                    # Award exp to research and shipgirls in fleet.
                    siren_reward_exp = Stats.stat(
                        *DataFiles.siren_data[siren.name]["reward_exp"],
                        exp=siren.battle_component.exp,
                    )
                    for shipgirl in self.menu_manager.player_fleet.fleet:
                        shipgirl.battle_component.gain_exp(siren_reward_exp)
                    if DataFiles.save_file["research_target"] is not None:
                        self.research_exp += siren_reward_exp

                self.menu_manager.player_fleet.end_encounter()
                self.menu_manager.siren_fleet.end_encounter()
                self.next_encounter_button.active = True
                self.retreat_button.active = False

        if self.defeat_pending:
            # Allow the sinking animation of the shipgirl to finish on defeat before showing
            # the end of sortie report.
            sunk_shipgirls = [
                shipgirl
                for shipgirl in self.menu_manager.player_fleet.fleet
                if shipgirl.battle_component.hp <= 0
            ]
            if sunk_shipgirls and all(
                shipgirl.sprite.animation_finished(shipgirl.sprite.SINK_ANIMATION)
                for shipgirl in sunk_shipgirls
            ):
                self.defeat_pending = False
                self.return_to_port_button.active = True

        self._spawn_shipgirl_wakes(self.menu_manager.player_fleet, True)
        self._spawn_shipgirl_wakes(self.menu_manager.siren_fleet, False)
        self.vfx_manager.update(dt)

    def draw_transition_wave_wipe(self, surface: pygame.Surface):
        """Draw the wave cover and reveal wipe.
        
        This wipe consists of three waves with different colors based on the current wave palette
        due to the weather conditions, with some staggering in terms of their vertical movement and
        horizontal offset.
        """
        if self.transition_state not in (
            self.TRANSITION_WAVE_COVER,
            self.TRANSITION_WAVE_REVEAL,
        ):
            return

        progress = min(
            1.0,
            self.transition_timer / self.TRANSITION_WAVE_DURATION,
        )
        covering = self.transition_state == self.TRANSITION_WAVE_COVER
        staggers = (
            self.TRANSITION_WAVE_STAGGERS
            if covering
            else reversed(self.TRANSITION_WAVE_STAGGERS)
        )

        wave_sets = DataFiles.sprites["background"]["wave_sets"]
        wave_set = wave_sets[self.weather_condition]
        wave_sprites = [
            wave_set[index]
            for index in self.TRANSITION_WAVE_INDICES
        ]

        for idx, (wave, stagger) in enumerate(zip(wave_sprites, staggers)):
            layer_progress = max(0.0, min(1.0, (progress - stagger) / (1 - stagger)))
            layer_progress = layer_progress * layer_progress * (3 - 2 * layer_progress)
            if not covering:
                layer_progress = 1 - layer_progress

            wave_width, wave_height = wave.get_size()
            wave_top = round(
                surface.get_height()
                + (-wave_height - surface.get_height()) * layer_progress
            )
            first_wave_left = -wave_width + idx / len(wave_sprites) * wave_width
            wave_left = first_wave_left
            # Draw the wave strip.
            while wave_left < surface.get_width():
                surface.blit(wave, (wave_left, wave_top))
                wave_left += wave_width
            # Fill in the space below the wave strip with the solid wave color.
            solid_top = wave_top + wave_height
            if solid_top < surface.get_height():
                wave_color = wave.get_at((0, wave_height - 1))[:3]
                solid_top = max(0, solid_top)
                pygame.draw.rect(
                    surface,
                    wave_color,
                    (
                        0,
                        solid_top,
                        surface.get_width(),
                        surface.get_height() - solid_top,
                    ),
                )

    def _draw_encounter_progress(self, surface: pygame.Surface):
        """Draw the encounter progress widget."""
        encounters = DataFiles.sortie_data[self.current_sortie]["encounters"]
        icon_spacing = 128
        first_icon_x = screen_x(0.5) - icon_spacing * (len(encounters) - 1) / 2
        icon_center_y = Box.BOTTOM_OF_SCREEN - 16

        prev_icon_rect = None
        dash_length = 8
        dash_gap = 8
        for encounter_index, encounter in enumerate(encounters):
            # Draw icons for each encounter using the existing encounter
            # icon language: flag=cleared, monster=uncleared, skull=boss.
            current_encounter_cleared = (
                encounter_index == self.current_encounter
                and not self.encounter_has_not_ended
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
            # Draw a dashed line between two encounter icons.
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
        # Draw a pointer at the current encounter icon.
        if self.current_encounter < len(encounters):
            current_icon_x = first_icon_x + self.current_encounter * icon_spacing
            current_icon = DataFiles.sprites["user_interface"]["uncleared"]
            current_icon_top = Box.BOTTOM_OF_SCREEN - current_icon.get_height()
            pointer_padding = 4
            pointer_tip_y = current_icon_top - pointer_padding
            pointer_height = 10
            pointer_width = 8
            pointer = [
                (current_icon_x - pointer_width, pointer_tip_y - pointer_height),
                (current_icon_x + pointer_width, pointer_tip_y - pointer_height),
                (current_icon_x, pointer_tip_y),
            ]
            pygame.draw.polygon(surface, Color.WHITE, pointer)

    def _refresh_report_page_buttons(self):
        """Refresh the report pagination controls."""
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

    def _change_report_page(self, delta: int):
        """Increment or decrement the report page index."""
        self.report_page = min(
            self.REPORT_PAGE_COUNT - 1,
            max(0, self.report_page + delta),
        )
        self._refresh_report_page_buttons()

    def _draw_dossier_page(self, surface: pygame.Surface):
        """Helper to draw the dossier-themed end of sortie report page."""
        # Page shape is based on available pagination controls, as the pagination
        # control is styled as a flipped page corner.
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

        # Draw the styled pagination controls.
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

    def _draw_dossier_prev_page_fold(self, surface: pygame.Surface):
        """Helper to draw the dossier prev page pagination control."""
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
        fold_height = 2 * Box.PADDING
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

    def _draw_dossier_overlay(self, surface: pygame.Surface, font_registry: dict[str, Font]):
        """Draw the dossier and report page used after a sortie."""
        pygame.draw.rect(surface, Color.DOSSIER, self.dossier_bg)

        # Dossier tab.
        tab = [
            pygame.Vector2(self.dossier_overlay.topleft),
            pygame.Vector2(self.dossier_overlay.topleft)
            + pygame.Vector2(2 * Box.WIDTH - Box.PADDING, 0),
            pygame.Vector2(self.dossier_overlay.topleft)
            + pygame.Vector2(2 * Box.WIDTH + Box.PADDING, Box.HEIGHT / 2),
            pygame.Vector2(self.dossier_overlay.topleft)
            + pygame.Vector2(0, Box.HEIGHT / 2),
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

        self._refresh_report_page_buttons()
        self._draw_dossier_page(surface)

        # Render different header text based on completion status.
        if self.sortie_completed:
            header_text = "operation completed"
        elif self.sortie_suspended:
            header_text = "operation suspended"
        else:
            header_text = "operation failed"
        header_y = self.dossier_page.top + Box.PADDING
        font_registry["big_pixel"].render(
            surface,
            header_text,
            (
                self.dossier_page.centerx,
                header_y + font_registry["big_pixel"].font_height,
            ),
            Color.DOSSIER_INK,
            scale=2,
            style="center",
        )
        horizontal_rule_down_shift = 32
        pygame.draw.line(
            surface,
            Color.DOSSIER_RULE,
            (self.dossier_page.left + Box.PADDING, header_y + horizontal_rule_down_shift),
            (self.dossier_page.right - Box.PADDING, header_y + horizontal_rule_down_shift),
        )

        # Based on the current page, render either the rewards collected report
        # or the defeated sirens report
        if self.report_page == 0:
            self._draw_sortie_rewards(surface, font_registry)
        else:
            self._draw_defeated_sirens(
                surface,
                font_registry,
            )

        # Draw page counter.
        font_registry["big_pixel"].render(
            surface,
            f"sheet {self.report_page + 1:02d} of {self.REPORT_PAGE_COUNT:02d}",
            (self.dossier_page.centerx, self.dossier_page.bottom - Box.PADDING),
            Color.DOSSIER_RULE,
            scale=1,
            style="center",
        )

        # Drop props.
        paperclip_sprite = DataFiles.sprites["props"]["diagonal_paperclip"]
        paperclip_rect = paperclip_sprite.get_rect()
        paperclip_alignment = 20
        paperclip_rect.left = self.dossier_page.left - paperclip_alignment
        paperclip_rect.top = self.dossier_page.top - paperclip_alignment
        surface.blit(paperclip_sprite, paperclip_rect)
        self._draw_dossier_prev_page_fold(surface)

    def _draw_return_to_port_sticky_note(self, surface: pygame.Surface, font_registry: dict[str, Font]):
        """Helper to draw the sticky note button styling for the return to port button."""
        note_rect = self.return_to_port_button.rect
        misaligned_pages = [
            (4, pygame.Vector2(-5, 4), Color.STICKY_NOTE_BACK),
            (-5, pygame.Vector2(5, -3), (239, 207, 87)),
            (2, pygame.Vector2(2, 4), (247, 220, 105)),
        ]
        for angle, offset, color in misaligned_pages:
            pygame.draw.polygon(
                surface,
                color,
                Box.get_rotated_rect_polygon(
                    note_rect,
                    angle,
                    offset,
                ),
            )
        pygame.draw.rect(
            surface,
            Color.STICKY_NOTE,
            note_rect,
        )

        # Draw the home icon and return to port text to signify what this sticky note does.
        home_icon = DataFiles.recolor_sprite("user_interface", "port", Color.STICKY_NOTE_HANDWRITING)
        home_icon_rect = home_icon.get_rect(
            center=(
                note_rect.centerx,
                note_rect.top + 0.75 * note_rect.height,
            ),
        )
        surface.blit(home_icon, home_icon_rect)
        font_registry["handwritten"].render(
            surface,
            "return to port?",
            (
                note_rect.centerx,
                note_rect.top + 0.35 * note_rect.height,
            ),
            Color.STICKY_NOTE_HANDWRITING,
            scale=1,
            style="center",
            box_width=note_rect.width,
        )

    def _draw_sortie_rewards(self, surface: pygame.Surface, font_registry: dict[str, Font]):
        """Helper to draw the sortie rewards page of the report."""
        # Page header.
        font = font_registry["big_pixel"]
        section_left = self.dossier_page.left + Box.PADDING
        section_top = self.dossier_page.top + self.REWARDS_SECTION_TOP
        font.render(
            surface,
            "recovered materials",
            (section_left, section_top),
            Color.DOSSIER_RULE,
            scale=1,
        )

        cards_top = section_top + font.font_height + Box.PADDING
        if not self.sortie_rewards:
            # Render a default no materials recovered text when empty.
            font.render(
                surface,
                "no materials recovered",
                (self.dossier_page.centerx, cards_top + Box.HEIGHT / 2),
                Color.DOSSIER_RULE,
                scale=2,
                style="center",
            )
            return cards_top + Box.HEIGHT

        # Draw the reward cards.
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
                    + (index % cards_per_row) * (Box.WIDTH + Box.PADDING)
                ),
                top=(
                    cards_top
                    + (index // cards_per_row) * (Box.HEIGHT + Box.PADDING)
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
            quantity_height = 14
            quantity_rect = get_rect(
                width=reward_rect.width, height=quantity_height,
                left=reward_rect.left, bottom=reward_rect.bottom
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
                scale=1,
                style="center",
            )
            pygame.draw.rect(
                surface,
                Color.DOSSIER_INK,
                reward_rect,
                width=1,
            )

    def _draw_defeated_sirens(self, surface: pygame.Surface, font_registry: dict[str, Font]):
        """Helper to draw the defeated sirens page in the report."""
        # TODO Consider writing a generic which can render this and the above.
        # Page header.
        section_top = self.dossier_page.top + self.REWARDS_SECTION_TOP
        font = font_registry["big_pixel"]
        section_left = self.dossier_page.left + Box.PADDING
        font.render(
            surface,
            "enemy sirens sunk",
            (section_left, section_top),
            Color.DOSSIER_RULE,
            scale=1,
        )

        cards_top = section_top + font.font_height + Box.PADDING
        if not self.defeated_sirens:
            # No sirens were defeated, so render a default empty message.
            font.render(
                surface,
                "no confirmed siren vessels sunk",
                (self.dossier_page.centerx, cards_top + Box.HEIGHT / 2),
                Color.DOSSIER_RULE,
                scale=2,
                style="center",
            )
            return

        # Draw the siren cards.
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
                    + (index % cards_per_row) * (card_width + Box.PADDING)
                ),
                top=(
                    cards_top
                    + (index // cards_per_row) * (Box.HEIGHT + Box.PADDING)
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
            siren_record_text_height = 16
            siren_name_text_y = card_rect.top + Box.PADDING
            font.render(
                surface,
                siren_name.replace("_", " "),
                (text_left, siren_name_text_y),
                Color.DOSSIER_INK,
                scale=1,
            )
            font.render(
                surface,
                f"level {siren_level:02d}",
                (text_left, siren_name_text_y + siren_record_text_height),
                Color.DOSSIER_RULE,
                scale=1,
            )
            font.render(
                surface,
                f"qty {amount:02d}",
                (text_left, siren_name_text_y + 2 * siren_record_text_height),
                Color.DOSSIER_INK,
                scale=1,
            )
            pygame.draw.rect(
                surface,
                Color.DOSSIER_INK,
                card_rect,
                width=1,
            )

    def draw(self, surface: pygame.Surface, font_registry: dict[str, Font]):
        """Draw the encounter menu."""
        self.background.draw(
            surface,
            font_registry,
            player_fleet=self.menu_manager.player_fleet,
            siren_fleet=self.menu_manager.siren_fleet,
            player_shipgirl_filter=(
                (lambda shipgirl: shipgirl.battle_component.hp > 0)
                if self.transition_active and not self.transition_to_port
                else None
            ),
        )
        self.vfx_manager.draw(surface, font_registry)

        self.open_reward_cache_button.draw(surface, font_registry)

        if self.transition_active and not self.transition_to_port:
            self.draw_transition_wave_wipe(surface)
            return

        for shipgirl in self.menu_manager.player_fleet.fleet:
            shipgirl.battle_component.draw_battlestation(surface, font_registry, shipgirl.rect)
        for siren in self.menu_manager.siren_fleet.fleet:
            siren.battle_component.draw_battlestation(surface, font_registry, siren.rect)
        for shipgirl in self.menu_manager.player_fleet.fleet:
            shipgirl.battle_component.draw_effects(surface, shipgirl.rect, self.vfx_manager)
        for siren in self.menu_manager.siren_fleet.fleet:
            siren.battle_component.draw_effects(surface, siren.rect, self.vfx_manager)

        self.next_encounter_button.draw(surface, font_registry)
        self.retreat_button.draw(surface, font_registry)
        self._draw_encounter_progress(surface)

        for drop in self.drops:
            drop.draw(surface, font_registry)

        # Draw the research exp widget.
        if self.exp_timer > 0:
            research_target = DataFiles.save_file["research_target"]
            unique_item = DataFiles.shipgirl_data[research_target]["unique_item"]
            avg_shipgirl_level = int(
                sum(
                    Stats.level(shipgirl.battle_component.exp)
                    for shipgirl in self.menu_manager.available_shipgirls
                )
                / len(self.menu_manager.available_shipgirls)
            )
            exp_req = Stats.exp_to_level(avg_shipgirl_level)
            research_progress = (
                DataFiles.save_file["specialized_wisdom_cubes"][research_target]
                + self.research_exp * self.exp_timer
            )

            panel_rect = get_rect(
                width=320,
                height=88,
                centerx=screen_x(0.5),
                centery=screen_y(0.5),
            )
            panel_margin = 8
            icon_padding = 4
            icon = DataFiles.get_entity_sprite(unique_item)
            icon_frame = get_rect(
                width=icon.get_width() + 2 * icon_padding,
                height=icon.get_height() + 2 * icon_padding,
                left=panel_rect.left + panel_margin,
                centery=panel_rect.centery,
            )
            rail_rect = get_rect(
                width=3,
                height=panel_rect.height - 2 * panel_margin,
                left=icon_frame.right + panel_margin,
                centery=panel_rect.centery,
            )
            big_pixel_font = font_registry["big_pixel"]
            content_left = rail_rect.right + panel_margin

            accent = Color.QUEST_NOTIFICATION_COMPLETE
            pulse = (math.sin(pygame.time.get_ticks() / 1000 * math.tau / 2.4) + 1) / 2
            panel = pygame.Surface(panel_rect.size, pygame.SRCALPHA)
            panel_cut_size = 7
            panel_polygon = [
                (panel_cut_size, panel_rect.height),
                (0, panel_rect.height-panel_cut_size),
                (0, 0),
                (panel_rect.width-panel_cut_size, 0),
                (panel_rect.width, panel_cut_size),
                (panel_rect.width, panel_rect.height),
            ]
            pygame.draw.polygon(
                panel,
                (*Color.QUEST_NOTIFICATION_PANEL, 225),
                panel_polygon,
            )
            pygame.draw.lines(
                panel,
                (*accent, round(145 + 85 * pulse)),
                False,
                panel_polygon[:-1],
                width=1,
            )
            surface.blit(panel, panel_rect)

            shipgirl_name_y = panel_rect.top + 1.5 * panel_margin
            shipgirl_name_scale = 2
            big_pixel_font.render(
                surface,
                unique_item.replace("_", " "),
                (content_left, shipgirl_name_y),
                accent,
                scale=shipgirl_name_scale
            )
            banner_text_y = shipgirl_name_y + shipgirl_name_scale * big_pixel_font.font_height + panel_margin
            big_pixel_font.render(
                surface,
                "shipgirl research progress",
                (content_left, banner_text_y),
                accent,
                scale=1,
            )
            bar_width = panel_rect.right - 2 * panel_margin - content_left
            bar_height = 16
            bar_background = get_rect(
                width=bar_width, height=bar_height,
                left=content_left,
                top=banner_text_y + big_pixel_font.font_height + panel_margin,
            )

            bar_fill = get_rect(
                width=bar_width * min(1, research_progress / exp_req),
                height=bar_height, left=bar_background.left, top=bar_background.top
            )
            bar_backplate = bar_background.inflate(4, 4)
            pygame.draw.rect(surface, Color.QUEST_NOTIFICATION_HEADER, bar_backplate)
            pygame.draw.rect(surface, Color.QUEST_NOTIFICATION_MUTED, bar_backplate, width=1)
            pygame.draw.rect(surface, Color.EXP_BAR_BG, bar_background)
            pygame.draw.rect(surface, accent, bar_fill)

            rail_glow = pygame.Surface(rail_rect.size, pygame.SRCALPHA)
            rail_glow.fill((*accent, round(35 + 35 * pulse)))
            surface.blit(
                rail_glow,
                rail_rect,
                special_flags=pygame.BLEND_RGBA_ADD,
            )

            pygame.draw.rect(surface, Color.QUEST_NOTIFICATION_HEADER, icon_frame)
            pygame.draw.rect(surface, accent, icon_frame, width=Box.OUTLINE_WIDTH)
            surface.blit(icon, icon.get_rect(center=icon_frame.center))

        if self.return_to_port_button.active:
            self._draw_dossier_overlay(surface, font_registry)
            self._draw_return_to_port_sticky_note(surface, font_registry)
        
        if self.end_encounter_banner.text:
            self.end_encounter_banner.draw(surface, font_registry)

        # Draw a line based on mouse drag.
        # If the player has dragged from a shipgirl to an enemy siren, show an indicator
        # of whether the player can or cannot drop to target this siren.
        mpos = pygame.mouse.get_pos()
        if self.mouse_start_drag is not None:
            pygame.draw.line(surface, Color.WHITE, self.mouse_start_drag, mpos, width=Box.OUTLINE_WIDTH)
            for siren in self.menu_manager.siren_fleet.fleet:
                if siren.battle_component.hp <= 0:
                    continue
                if siren.rect.collidepoint(mpos):
                    # Based on whether this siren is a valid target, pick the color
                    # for the indicator.
                    if self.selected_shipgirl.battle_component.hull_type in self.MELEE_SHIPS:
                        if siren in self.menu_manager.siren_fleet.afloat_front:
                            color = (50,200,50)
                        else:
                            color = (200,50,50)
                    else:
                        color = (50,200,50)
                    
                    inner_radius = 12
                    outer_radius = 24
                    annulus = pygame.Surface((2 * outer_radius, 2 * outer_radius))
                    annulus.fill((0, 0, 0))
                    pygame.draw.circle(annulus, color, (outer_radius, outer_radius), outer_radius)
                    pygame.draw.circle(annulus, (0, 0, 0), (outer_radius, outer_radius), inner_radius)
                    annulus.set_colorkey((0, 0, 0))
                    annulus_rect = annulus.get_rect()

                    drawpos = pygame.Vector2(mpos) + pygame.Vector2(48)
                    annulus_rect.center = drawpos
                    surface.blit(annulus, annulus_rect)

                    # Different hull tpyes have different attack icons.
                    if self.selected_shipgirl.battle_component.hull_type == "CV":
                        attack_icon = DataFiles.sprites["user_interface"]["air_attack"]
                    elif self.selected_shipgirl.battle_component.hull_type == "SS":
                        attack_icon = DataFiles.sprites["user_interface"]["torp_attack"]
                    else:
                        attack_icon = DataFiles.sprites["user_interface"]["shell_attack"]
                    attack_icon_rect = attack_icon.get_rect()
                    attack_icon_rect.center = drawpos
                    surface.blit(attack_icon, attack_icon_rect)

        if self.transition_to_port:
            self.draw_transition_wave_wipe(surface)
