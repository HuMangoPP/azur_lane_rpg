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
            self.selected_quest.draw(surface, font_registry)

class Quest:
    DIALOGUE_OVERLAY = get_rect(
        width=7*30 + 2*Box.PADDING + 2*Box.PADDING,
        height=9*4 + 4*3 + 2*Box.PADDING + 2*Box.PADDING + Box.HEIGHT/2,
        centerx=screen_x(0.5), centery=screen_y(0.5)
    )
    DIALOGUE_BOX = get_rect(
        width=DIALOGUE_OVERLAY.width - 2*Box.PADDING,
        height=DIALOGUE_OVERLAY.height - 2*Box.PADDING - Box.HEIGHT/2,
        left=DIALOGUE_OVERLAY.left + Box.PADDING,
        top=DIALOGUE_OVERLAY.top + Box.PADDING
    )

    QUEST_LINE_OVERLAY = get_rect(
        width=7*30 + 2*Box.PADDING + 2*Box.PADDING,
        height=9*2 + 4*1 + 2*Box.PADDING + 4*Box.PADDING + Box.HEIGHT/2 + 2*Box.HEIGHT,
        centerx=screen_x(0.5), centery=screen_y(0.5)
    )
    QUEST_LINE_BOX = get_rect(
        width=QUEST_LINE_OVERLAY.width - 2*Box.PADDING,
        height=QUEST_LINE_OVERLAY.height - 4*Box.PADDING - Box.HEIGHT/2 - 2*Box.HEIGHT,
        left=QUEST_LINE_OVERLAY.left + Box.PADDING,
        top=QUEST_LINE_OVERLAY.top + Box.PADDING
    )

    NEXT_BUTTON = get_rect(
        width=96, height=32,
        centerx=DIALOGUE_OVERLAY.centerx,
        centery=DIALOGUE_OVERLAY.bottom
    )
    QUEST_BUTTON = get_rect(
        width=96, height=32,
        centerx=QUEST_LINE_OVERLAY.centerx,
        centery=QUEST_LINE_OVERLAY.bottom
    )

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
        num_reward_rects_in_row = (self.QUEST_LINE_OVERLAY.width - 2*Box.PADDING) // Box.WIDTH
        reward_rect_padding = ((self.QUEST_LINE_OVERLAY.width - 2*Box.PADDING) - Box.WIDTH*num_reward_rects_in_row) / (num_reward_rects_in_row-1)
        self.reward_rects = [
            get_rect(
                width=Box.WIDTH, height=Box.HEIGHT,
                left=self.QUEST_LINE_OVERLAY.left + Box.PADDING + (i%num_reward_rects_in_row)*(Box.WIDTH+reward_rect_padding),
                top=self.QUEST_LINE_BOX.bottom + Box.PADDING + (i//num_reward_rects_in_row)*(Box.HEIGHT+Box.PADDING)
            )
            for i in range(2*num_reward_rects_in_row)
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

    def draw(self, surface, font_registry):
        shipgirls = DataFiles.get_faction_shipgirls()

        if self.rewards_collected:
            overlay = self.DIALOGUE_OVERLAY
            box = self.DIALOGUE_BOX
            button = self.NEXT_BUTTON
            button_text = "next"
            if self.post_quest_dialogue_index == len(self.post_quest_dialogue) - 1:
                button_text = "ok"
            text = self.post_quest_dialogue[self.post_quest_dialogue_index]
            show_reward = False
        elif self.completed:
            overlay = self.QUEST_LINE_OVERLAY
            box = self.QUEST_LINE_BOX
            button = self.QUEST_BUTTON
            button_text = "get reward"
            text = self.quest_line
            show_reward = True
        elif self.pre_quest_finished:
            overlay = self.QUEST_LINE_OVERLAY
            box = self.QUEST_LINE_BOX
            button = self.QUEST_BUTTON
            button_text = "ok"
            text = self.quest_line
            show_reward = True
        else:
            overlay = self.DIALOGUE_OVERLAY
            box = self.DIALOGUE_BOX
            button = self.NEXT_BUTTON
            button_text = "next"
            if self.pre_quest_dialogue_index == len(self.pre_quest_dialogue) - 1:
                button_text = "ok"
            text = self.pre_quest_dialogue[self.pre_quest_dialogue_index]
            show_reward = False
        
        pygame.draw.rect(surface, Color.DIALOGUE_OVERLAY, overlay)
        pygame.draw.rect(surface, Color.DIALOGUE_BOX, box)
        middleleft = pygame.Vector2(box.left, box.centery)
        polygon = [
            middleleft + pygame.Vector2(0, Box.PADDING),
            middleleft + pygame.Vector2(0, -Box.PADDING),
            middleleft + pygame.Vector2(-Box.WIDTH/2, 0)
        ]
        pygame.draw.polygon(surface, Color.DIALOGUE_BOX, polygon)
        tb_sprite = DataFiles.sprites["user_interface"]["TB"]
        rect = tb_sprite.get_rect()
        rect.right = polygon[-1].x
        rect.centery = polygon[-1].y
        surface.blit(tb_sprite, rect)

        text_width = box.width - 2*Box.PADDING
        font_registry["big_pixel"].render(
            surface,
            text.format(**{
                f"{hull_type}_shipgirl": " ".join(shipgirl.split("_"))
                for hull_type, shipgirl in shipgirls.items()
            }),
            pygame.Vector2(box.topleft) + pygame.Vector2(Box.PADDING, Box.PADDING),
            Color.WHITE,
            1, 
            box_width=text_width
        )

        pygame.draw.rect(surface, Color.DIALOGUE_BUTTON, button)
        if button_text == "next":
            next_sprite = DataFiles.sprites["user_interface"]["next"]
            next_sprite_rect = next_sprite.get_rect()
            next_sprite_rect.center = button.center
            surface.blit(next_sprite, next_sprite_rect)
        else:
            font_registry["big_pixel"].render(surface, button_text, button.center, Color.WHITE, 1, style="center")

        if show_reward:
            for rect, (reward, amt) in zip(self.reward_rects, self.rewards.items()):
                if reward.startswith("placeholder"):
                    reward = "placeholder"
                pygame.draw.rect(surface, Color.WHITE, rect, width=Box.OUTLINE_WIDTH)
                surface.blit(DataFiles.get_entity_sprite(reward), rect)
                font_registry["big_pixel"].render(surface, str(amt), rect.center, Color.WHITE, 1, style="center")
