import math
import pygame

from engine.util import get_rect

from src.constants import DataFiles, Box, Color, screen_x, screen_y

class QuestManager:
    NOTIFICATION_LEFT = Box.PADDING
    NOTIFICATION_TOP = Box.PADDING
    NOTIFICATION_WIDTH = 320
    NOTIFICATION_HEADER_HEIGHT = 72
    NOTIFICATION_ROW_HEIGHT = 40
    NOTIFICATION_GAP = 4
    NOTIFICATION_CUT = 7
    NOTIFICATION_PANEL_ALPHA = 210
    NOTIFICATION_PANEL_HOVER_ALPHA = 230

    STATUS_NEW = "new"
    STATUS_ACTIVE = "active"
    STATUS_COMPLETE = "complete"

    STATUS_STYLES = {
        STATUS_NEW: (
            "new briefing // review to start",
            Color.QUEST_NOTIFICATION_NEW,
            3,
            1.0,
        ),
        STATUS_ACTIVE: (
            "task in progress",
            Color.QUEST_NOTIFICATION_ACTIVE,
            1,
            0.55,
        ),
        STATUS_COMPLETE: (
            "task complete // rewards ready",
            Color.QUEST_NOTIFICATION_COMPLETE,
            4,
            1.25,
        ),
    }

    def __init__(self):
        self.quests = {}
        self.selected_quest = None
        self.notification_effect_time = 0

    @property
    def started_quests(self):
        return {quest_id: quest for quest_id, quest in self.quests.items()}

    def update(self, dt):
        self.notification_effect_time += dt

    @classmethod
    def _quest_status(cls, quest):
        if quest.completed:
            return cls.STATUS_COMPLETE
        if not quest.started:
            return cls.STATUS_NEW
        return cls.STATUS_ACTIVE

    def _ordered_quests(self):
        priorities = {
            self.STATUS_COMPLETE: 0,
            self.STATUS_NEW: 1,
            self.STATUS_ACTIVE: 2,
        }
        return sorted(
            self.quests.values(),
            key=lambda quest: priorities[self._quest_status(quest)],
        )

    def get_notification_entries(self):
        rows_top = (
            self.NOTIFICATION_TOP
            + self.NOTIFICATION_HEADER_HEIGHT
            + self.NOTIFICATION_GAP
        )
        return [
            (
                quest,
                get_rect(
                    width=self.NOTIFICATION_WIDTH,
                    height=self.NOTIFICATION_ROW_HEIGHT,
                    left=self.NOTIFICATION_LEFT,
                    top=rows_top
                    + i*(self.NOTIFICATION_ROW_HEIGHT + self.NOTIFICATION_GAP),
                ),
            )
            for i, quest in enumerate(self._ordered_quests())
        ]

    def notifications_collidepoint(self, point):
        return any(
            rect.collidepoint(point)
            for _, rect in self.get_notification_entries()
        )

    def select_quest(self, mpos):
        for quest, rect in self.get_notification_entries():
            if rect.collidepoint(mpos):
                self.selected_quest = quest
                return True
        self.selected_quest = None
        return False

    @classmethod
    def _panel_polygon(cls, size):
        width, height = size
        cut = cls.NOTIFICATION_CUT
        return [
            (0, 0),
            (width-cut, 0),
            (width, cut),
            (width, height),
            (cut, height),
            (0, height-cut),
        ]

    def _draw_panel(
        self,
        surface,
        rect,
        fill_color,
        edge_color,
        pulse,
        opacity=NOTIFICATION_PANEL_ALPHA,
    ):
        panel = pygame.Surface(rect.size, pygame.SRCALPHA)
        polygon = self._panel_polygon(rect.size)
        pygame.draw.polygon(panel, (*fill_color, opacity), polygon)
        pygame.draw.polygon(
            panel,
            (*edge_color, round(135 + 85*pulse)),
            polygon,
            width=1,
        )

        surface.blit(panel, rect)

    def _draw_glints(self, surface, rect, color, count, intensity, seed):
        glint_cycle = 1.15
        glint_lifetime = 0.72
        glint_max_length = 4
        glint_drift = 9
        previous_clip = surface.get_clip()
        surface.set_clip(rect)

        for glint_index in range(count):
            glint_time = (
                self.notification_effect_time
                + glint_index*glint_cycle/count
                + seed*0.071
            )
            glint_age = glint_time % glint_cycle
            if glint_age >= glint_lifetime:
                continue

            cycle_index = math.floor(glint_time/glint_cycle)
            progress = glint_age/glint_lifetime
            strength = (1-progress)**1.5*intensity
            spawn_center = pygame.Vector2(
                rect.left + 10
                + (cycle_index*29 + glint_index*17 + seed*7)
                % (rect.width-20),
                rect.top + 7
                + (cycle_index*19 + glint_index*31 + seed*11)
                % (rect.height-14),
            )
            center = spawn_center - pygame.Vector2(0, glint_drift*progress)
            if center.y < rect.top + 2:
                continue

            length = 1 + round((glint_max_length-1)*min(1, strength))
            glint_color = tuple(
                min(255, round(channel*strength))
                for channel in color
            )
            glint = pygame.Surface(
                (2*glint_max_length+1, 2*glint_max_length+1),
                pygame.SRCALPHA,
            )
            glint_center = pygame.Vector2(glint_max_length, glint_max_length)
            pygame.draw.line(
                glint,
                (*glint_color, 255),
                glint_center-pygame.Vector2(length, 0),
                glint_center+pygame.Vector2(length, 0),
            )
            pygame.draw.line(
                glint,
                (*glint_color, 255),
                glint_center-pygame.Vector2(0, length),
                glint_center+pygame.Vector2(0, length),
            )
            surface.blit(
                glint,
                glint.get_rect(center=center),
                special_flags=pygame.BLEND_RGBA_ADD,
            )
        surface.set_clip(previous_clip)

    @staticmethod
    def _format_objective(quest):
        shipgirls = DataFiles.get_faction_shipgirls()
        return quest.quest_line.format(**{
            f"{hull_type}_shipgirl": " ".join(shipgirl.split("_"))
            for hull_type, shipgirl in shipgirls.items()
        })

    @staticmethod
    def _ellipsize(text, font, max_width):
        if font.get_width(text, 1, 0) <= max_width:
            return text
        suffix = "..."
        max_chars = max(0, int(max_width//font.font_width)-len(suffix))
        return text[:max_chars].rstrip() + suffix

    def _draw_header(self, surface, font_registry, quest_count):
        rect = get_rect(
            width=self.NOTIFICATION_WIDTH,
            height=self.NOTIFICATION_HEADER_HEIGHT,
            left=self.NOTIFICATION_LEFT,
            top=self.NOTIFICATION_TOP,
        )
        pulse = (
            math.sin(self.notification_effect_time*math.tau/2.4)+1
        )/2
        self._draw_panel(
            surface,
            rect,
            Color.QUEST_NOTIFICATION_HEADER,
            Color.QUEST_NOTIFICATION_NEW,
            pulse,
        )

        tb = DataFiles.sprites["user_interface"]["TB"]
        surface.blit(tb, tb.get_rect(midleft=(rect.left+3, rect.centery)))
        pygame.draw.line(
            surface,
            Color.QUEST_NOTIFICATION_NEW,
            (rect.left+72, rect.top+6),
            (rect.left+72, rect.bottom-6),
            width=3
        )
        font_registry["big_pixel"].render(
            surface,
            "mission relay",
            (rect.left+80, rect.top+8),
            Color.QUEST_NOTIFICATION_TEXT,
            1,
        )
        signal_label = f"{quest_count} active signal"
        if quest_count != 1:
            signal_label += "s"
        font_registry["pixel"].render(
            surface,
            signal_label,
            (rect.left+80, rect.top+24),
            Color.QUEST_NOTIFICATION_MUTED,
            1,
        )
        self._draw_glints(
            surface,
            rect,
            Color.QUEST_NOTIFICATION_NEW,
            3,
            0.75,
            0,
        )

    def _draw_notification_row(
        self,
        surface,
        font_registry,
        quest,
        rect,
        index,
        hovered,
    ):
        status = self._quest_status(quest)
        status_text, accent, glint_count, intensity = self.STATUS_STYLES[status]
        pulse = (
            math.sin(
                self.notification_effect_time*math.tau/2.4 + index*0.65
            )+1
        )/2
        self._draw_panel(
            surface,
            rect,
            Color.QUEST_NOTIFICATION_PANEL,
            accent,
            pulse,
            opacity=(
                self.NOTIFICATION_PANEL_HOVER_ALPHA
                if hovered
                else self.NOTIFICATION_PANEL_ALPHA
            ),
        )

        rail_glow = get_rect(
            width=3,
            height=rect.height-12,
            left=rect.left+6,
            centery=rect.centery,
        )
        glow = pygame.Surface(rail_glow.size, pygame.SRCALPHA)
        glow.fill((*accent, round(28 + 35*pulse)))
        surface.blit(glow, rail_glow, special_flags=pygame.BLEND_RGBA_ADD)

        font_registry["big_pixel"].render(
            surface,
            status_text,
            (rect.left+14, rect.top+8),
            accent,
            1,
        )
        objective = self._ellipsize(
            self._format_objective(quest),
            font_registry["pixel"],
            rect.width-42,
        )
        font_registry["pixel"].render(
            surface,
            objective,
            (rect.left+14, rect.top+23),
            Color.QUEST_NOTIFICATION_TEXT,
            1,
        )

        chevron_x = rect.right-13
        pygame.draw.lines(
            surface,
            accent,
            False,
            [
                (chevron_x-3, rect.centery-4),
                (chevron_x+1, rect.centery),
                (chevron_x-3, rect.centery+4),
            ],
            width=1,
        )
        self._draw_glints(
            surface,
            rect,
            accent,
            glint_count,
            intensity,
            index+1,
        )

    def draw(self, surface, font_registry):
        entries = self.get_notification_entries()
        if entries:
            self._draw_header(surface, font_registry, len(entries))
            mouse_pos = pygame.mouse.get_pos()
            for index, (quest, rect) in enumerate(entries):
                self._draw_notification_row(
                    surface,
                    font_registry,
                    quest,
                    rect,
                    index,
                    rect.collidepoint(mouse_pos),
                )

        if self.selected_quest is not None:
            self.selected_quest.draw(
                surface,
                font_registry,
                self.notification_effect_time,
            )

class Quest:
    DIALOGUE_OVERLAY = get_rect(
        width=512,
        height=104,
        centerx=screen_x(0.5), centery=screen_y(0.5)
    )
    DIALOGUE_BOX = get_rect(
        width=408,
        height=64,
        left=DIALOGUE_OVERLAY.left + 92,
        top=DIALOGUE_OVERLAY.top + 32
    )

    QUEST_LINE_OVERLAY = get_rect(
        width=512,
        height=104,
        centerx=screen_x(0.5), top=142
    )
    QUEST_LINE_BOX = get_rect(
        width=408,
        height=64,
        left=QUEST_LINE_OVERLAY.left + 92,
        top=QUEST_LINE_OVERLAY.top + 32
    )
    REWARD_PANEL = get_rect(
        width=512,
        height=112,
        centerx=screen_x(0.5),
        top=QUEST_LINE_OVERLAY.bottom + Box.PADDING,
    )

    NEXT_BUTTON = get_rect(
        width=144, height=32,
        centerx=DIALOGUE_OVERLAY.centerx,
        centery=DIALOGUE_OVERLAY.bottom
    )
    QUEST_BUTTON = get_rect(
        width=144, height=32,
        centerx=REWARD_PANEL.centerx,
        centery=REWARD_PANEL.bottom
    )

    PANEL_CUT = 7
    CONTENT_SEPARATOR_X = 80
    REWARD_GAP = Box.PADDING

    def __init__(
        self,
        quest_id,
        pre_quest_dialogue,
        quest_line,
        post_quest_dialogue,
        completion_criteria,
        tutorial_draw,
        on_start,
        on_complete,
        rewards
    ):
        self.quest_id = quest_id

        self.pre_quest_finished = False
        self.started = False
        self.completed = False
        self.rewards_collected = False

        self.pre_quest_dialogue_index = 0
        self.pre_quest_dialogue = pre_quest_dialogue
        self.quest_line = quest_line
        self.post_quest_dialogue_index = 0
        self.post_quest_dialogue = post_quest_dialogue

        self.completion_criteria = completion_criteria
        self.tutorial_draw = tutorial_draw
        self.on_start = on_start
        self.on_complete = on_complete

        self.rewards = rewards
        reward_count = len(self.rewards)
        rewards_width = (
            reward_count*Box.WIDTH
            + max(0, reward_count-1)*self.REWARD_GAP
        )
        rewards_left = self.REWARD_PANEL.centerx - rewards_width/2
        self.reward_rects = [
            get_rect(
                width=Box.WIDTH,
                height=Box.HEIGHT,
                left=rewards_left + i*(Box.WIDTH + self.REWARD_GAP),
                top=self.REWARD_PANEL.top + 24,
            )
            for i in range(reward_count)
        ]

    def go_next(self, menu_manager, mpos):
        if self.rewards_collected:
            if self.NEXT_BUTTON.collidepoint(mpos):
                DataFiles.sfx["click"].play()
                self.post_quest_dialogue_index += 1
            if self.post_quest_dialogue_index == len(self.post_quest_dialogue):
                self.on_complete(menu_manager)
                DataFiles.save_file["quests"][self.quest_id] = "completed"
                menu_manager.quest_manager.quests.pop(self.quest_id)
                return True
            return False
        elif self.completed:
            if not self.rewards_collected and self.QUEST_BUTTON.collidepoint(mpos):
                DataFiles.sfx["scale"].play()
                self.rewards_collected = True
                for reward, amt in self.rewards.items():
                    DataFiles.save_file["inventory"][reward] = DataFiles.save_file["inventory"].get(reward, 0) + amt
            return False
        elif self.pre_quest_finished:
            if self.QUEST_BUTTON.collidepoint(mpos):
                DataFiles.sfx["click"].play()
                if not self.started:
                    self.started = True
                    self.on_start(menu_manager)
                    DataFiles.save_file["quests"][self.quest_id] = "in_progress"
                return True
            return False
        else:
            if self.NEXT_BUTTON.collidepoint(mpos):
                DataFiles.sfx["click"].play()
                self.pre_quest_dialogue_index += 1
            if self.pre_quest_dialogue_index == len(self.pre_quest_dialogue):
                self.pre_quest_finished = True
        return False

    @classmethod
    def _panel_polygon(cls, size):
        width, height = size
        return [
            (0, 0),
            (width-cls.PANEL_CUT, 0),
            (width, cls.PANEL_CUT),
            (width, height),
            (cls.PANEL_CUT, height),
            (0, height-cls.PANEL_CUT),
        ]

    @staticmethod
    def _format_text(text):
        shipgirls = DataFiles.get_faction_shipgirls()
        return text.format(**{
            f"{hull_type}_shipgirl": " ".join(shipgirl.split("_"))
            for hull_type, shipgirl in shipgirls.items()
        })

    def _draw_panel(self, surface, rect, accent, effect_time, intensity=1):
        pulse = (math.sin(effect_time*math.tau/2.4)+1)/2
        panel = pygame.Surface(rect.size, pygame.SRCALPHA)
        polygon = self._panel_polygon(rect.size)
        pygame.draw.polygon(
            panel,
            (*Color.QUEST_NOTIFICATION_PANEL, 225),
            polygon,
        )
        pygame.draw.polygon(
            panel,
            (*accent, round(145 + 85*pulse)),
            polygon,
            width=1,
        )
        surface.blit(panel, rect)
        self._draw_panel_glints(
            surface,
            rect,
            accent,
            effect_time,
            max(2, round(3*intensity)),
            intensity,
        )

    @staticmethod
    def _draw_panel_glints(
        surface,
        rect,
        color,
        effect_time,
        count,
        intensity,
    ):
        cycle = 1.35
        lifetime = 0.7
        max_length = 4
        previous_clip = surface.get_clip()
        surface.set_clip(rect)

        for glint_index in range(count):
            glint_time = effect_time + glint_index*cycle/count
            age = glint_time % cycle
            if age >= lifetime:
                continue

            cycle_index = math.floor(glint_time/cycle)
            progress = age/lifetime
            strength = min(1, (1-progress)**1.5*intensity)
            if glint_index % 2 == 0:
                center = pygame.Vector2(
                    rect.left + 12
                    + (cycle_index*31 + glint_index*43) % (rect.width-24),
                    rect.top + 3 + 3*progress,
                )
            else:
                center = pygame.Vector2(
                    rect.left + 3 + 3*progress,
                    rect.top + 12
                    + (cycle_index*23 + glint_index*37) % (rect.height-24),
                )

            length = 1 + round((max_length-1)*strength)
            glint_color = tuple(round(channel*strength) for channel in color)
            glint = pygame.Surface(
                (2*max_length+1, 2*max_length+1),
                pygame.SRCALPHA,
            )
            glint_center = pygame.Vector2(max_length, max_length)
            pygame.draw.line(
                glint,
                (*glint_color, 255),
                glint_center-pygame.Vector2(length, 0),
                glint_center+pygame.Vector2(length, 0),
            )
            pygame.draw.line(
                glint,
                (*glint_color, 255),
                glint_center-pygame.Vector2(0, length),
                glint_center+pygame.Vector2(0, length),
            )
            surface.blit(
                glint,
                glint.get_rect(center=center),
                special_flags=pygame.BLEND_RGBA_ADD,
            )
        surface.set_clip(previous_clip)

    def _draw_content_panel(
        self,
        surface,
        font_registry,
        overlay,
        text_box,
        context_label,
        text,
        accent,
        effect_time,
        intensity=1,
    ):
        self._draw_panel(surface, overlay, accent, effect_time, intensity)

        tb_sprite = DataFiles.sprites["user_interface"]["TB"]
        tb_rect = tb_sprite.get_rect(
            left=overlay.left + Box.PADDING,
            centery=overlay.centery,
        )
        surface.blit(tb_sprite, tb_rect)

        separator_x = overlay.left + self.CONTENT_SEPARATOR_X
        pygame.draw.line(
            surface,
            accent,
            (separator_x, overlay.top+8),
            (separator_x, overlay.bottom-8),
            width=3,
        )
        font_registry["big_pixel"].render(
            surface,
            context_label,
            (text_box.left, overlay.top+12),
            accent,
            1,
        )
        font_registry["big_pixel"].render(
            surface,
            self._format_text(text),
            text_box.topleft,
            Color.QUEST_NOTIFICATION_TEXT,
            1,
            box_width=text_box.width,
        )

    def _draw_reward_panel(
        self,
        surface,
        font_registry,
        accent,
        effect_time,
        intensity,
    ):
        self._draw_panel(
            surface,
            self.REWARD_PANEL,
            accent,
            effect_time,
            intensity,
        )
        font_registry["big_pixel"].render(
            surface,
            "reward allocation",
            (self.REWARD_PANEL.left+14, self.REWARD_PANEL.top+8),
            accent,
            1,
        )

        for rect, (reward, amount) in zip(
            self.reward_rects,
            self.rewards.items(),
        ):
            sprite_key = (
                "placeholder"
                if reward.startswith("placeholder")
                else reward
            )
            tile = pygame.Surface(rect.size, pygame.SRCALPHA)
            tile.fill((*Color.QUEST_NOTIFICATION_HEADER, 225))
            surface.blit(tile, rect)
            reward_sprite = DataFiles.get_entity_sprite(sprite_key)
            surface.blit(
                reward_sprite,
                reward_sprite.get_rect(center=rect.center),
            )
            pygame.draw.rect(surface, accent, rect, width=1)

            quantity_rect = get_rect(
                width=24,
                height=14,
                right=rect.right-2,
                bottom=rect.bottom-2,
            )
            quantity_panel = pygame.Surface(quantity_rect.size, pygame.SRCALPHA)
            quantity_panel.fill((*Color.QUEST_NOTIFICATION_PANEL, 235))
            surface.blit(quantity_panel, quantity_rect)
            pygame.draw.rect(surface, accent, quantity_rect, width=1)
            font_registry["pixel"].render(
                surface,
                f"x{amount}",
                quantity_rect.center,
                Color.QUEST_NOTIFICATION_TEXT,
                1,
                style="center",
            )

    def _draw_action_button(
        self,
        surface,
        font_registry,
        rect,
        label,
        accent,
    ):
        hovered = rect.collidepoint(pygame.mouse.get_pos())
        button = pygame.Surface(rect.size, pygame.SRCALPHA)
        polygon = self._panel_polygon(rect.size)
        pygame.draw.polygon(
            button,
            (*Color.QUEST_NOTIFICATION_PANEL, 240 if hovered else 215),
            polygon,
        )
        pygame.draw.polygon(button, (*accent, 235), polygon, width=1)
        surface.blit(button, rect)

        if label == "next":
            next_sprite = DataFiles.sprites["user_interface"]["next"]
            surface.blit(next_sprite, next_sprite.get_rect(center=rect.center))
        else:
            font_registry["big_pixel"].render(
                surface,
                label,
                rect.center,
                Color.QUEST_NOTIFICATION_TEXT,
                1,
                style="center",
            )

    def draw(self, surface, font_registry, effect_time=0):
        if self.rewards_collected:
            final_page = (
                self.post_quest_dialogue_index
                == len(self.post_quest_dialogue)-1
            )
            self._draw_content_panel(
                surface,
                font_registry,
                self.DIALOGUE_OVERLAY,
                self.DIALOGUE_BOX,
                "tb // mission debrief",
                self.post_quest_dialogue[self.post_quest_dialogue_index],
                Color.QUEST_NOTIFICATION_NEW,
                effect_time,
            )
            self._draw_action_button(
                surface,
                font_registry,
                self.NEXT_BUTTON,
                "close" if final_page else "next",
                Color.QUEST_NOTIFICATION_NEW,
            )
            return

        if not self.pre_quest_finished:
            final_page = (
                self.pre_quest_dialogue_index
                == len(self.pre_quest_dialogue)-1
            )
            self._draw_content_panel(
                surface,
                font_registry,
                self.DIALOGUE_OVERLAY,
                self.DIALOGUE_BOX,
                "tb // mission briefing",
                self.pre_quest_dialogue[self.pre_quest_dialogue_index],
                Color.QUEST_NOTIFICATION_NEW,
                effect_time,
            )
            self._draw_action_button(
                surface,
                font_registry,
                self.NEXT_BUTTON,
                "view briefing" if final_page else "next",
                Color.QUEST_NOTIFICATION_NEW,
            )
            return

        if self.completed:
            context_label = "task complete // final report"
            accent = Color.QUEST_NOTIFICATION_COMPLETE
            button_label = "collect rewards"
            intensity = 1.3
        elif self.started:
            context_label = "task in progress // objective"
            accent = Color.QUEST_NOTIFICATION_ACTIVE
            button_label = "close"
            intensity = 0.65
        else:
            context_label = "new briefing // objective"
            accent = Color.QUEST_NOTIFICATION_NEW
            button_label = "accept task"
            intensity = 1

        self._draw_content_panel(
            surface,
            font_registry,
            self.QUEST_LINE_OVERLAY,
            self.QUEST_LINE_BOX,
            context_label,
            self.quest_line,
            accent,
            effect_time,
            intensity,
        )
        self._draw_reward_panel(
            surface,
            font_registry,
            accent,
            effect_time,
            intensity,
        )
        self._draw_action_button(
            surface,
            font_registry,
            self.QUEST_BUTTON,
            button_label,
            accent,
        )
