import math
import pygame

from engine.util import get_rect, get_vec

from src.constants import DataFiles, Box, Color, screen_x, screen_y

class QuestManager:
    def __init__(self):
        self.quests = {}
        self.selected_quest = None
    
    @property
    def started_quests(self):
        return {quest_id: quest for quest_id, quest in self.quests.items()}

    def select_quest(self, mpos):
        for i, quest in enumerate(self.quests.values()):
            rect = get_rect(
                width=Box.WIDTH, height=Box.HEIGHT,
                left=Box.PADDING,
                top=Box.PADDING + (Box.HEIGHT + Box.PADDING) * i
            )
            if rect.collidepoint(mpos):
                self.selected_quest = quest
                break
        else:
            self.selected_quest = None

    def draw(self, surface, font):
        for i, quest in enumerate(self.quests.values()):
            rect = get_rect(
                width=Box.WIDTH, height=Box.HEIGHT,
                left=Box.PADDING,
                top=Box.PADDING + (Box.HEIGHT + Box.PADDING) * i
            )
            pygame.draw.rect(surface, Color.WHITE, rect, Box.OUTLINE_WIDTH)
            surface.blit(DataFiles.sprites["user_interface"]["TB"], rect)

            textpos = (rect.right + Box.PADDING, rect.centery)
            if not quest.started:
                font.render(surface, "new", textpos, Color.WHITE, 1, style="centerleft", outline_color=Color.BLACK)
            elif quest.completed:
                font.render(surface, "completed", textpos, Color.WHITE, 1, style="centerleft", outline_color=Color.BLACK)
        
        if self.selected_quest is not None:
            self.selected_quest.draw(surface, font)

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
        width=Box.WIDTH, height=Box.HEIGHT,
        centerx=DIALOGUE_OVERLAY.centerx,
        centery=DIALOGUE_OVERLAY.bottom
    )
    QUEST_BUTTON = get_rect(
        width=Box.WIDTH, height=Box.HEIGHT,
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
        rewards={}
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
                self.post_quest_dialogue_index += 1
            if self.post_quest_dialogue_index == len(self.post_quest_dialogue):
                self.on_complete(menu_manager)
                DataFiles.save_file["quests"][self.quest_id] = "completed"
                menu_manager.quest_manager.quests.pop(self.quest_id)
                return True
            return False
        elif self.completed:
            if not self.rewards_collected and self.QUEST_BUTTON.collidepoint(mpos):
                self.rewards_collected = True
                for reward, amt in self.rewards.items():
                    DataFiles.save_file["inventory"][reward] = DataFiles.save_file["inventory"].get(reward, 0) + amt
            return False
        elif self.pre_quest_finished:
            if not self.started and self.QUEST_BUTTON.collidepoint(mpos):
                self.started = True
                self.on_start(menu_manager)
                DataFiles.save_file["quests"][self.quest_id] = "in_progress"
                return True
            return False
        else:
            if self.NEXT_BUTTON.collidepoint(mpos):
                self.pre_quest_dialogue_index += 1
            if self.pre_quest_dialogue_index == len(self.pre_quest_dialogue):
                self.pre_quest_finished = True
        return False
    
    def draw(self, surface, font):
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
        
        pygame.draw.rect(surface, Color.BLUE_GREY, overlay)
        pygame.draw.rect(surface, Color.DARK_BLUE, box)
        middleleft = pygame.Vector2(box.left, box.centery)
        polygon = [
            middleleft + pygame.Vector2(0, 2*Box.PADDING),
            middleleft + pygame.Vector2(0, -2*Box.PADDING),
            middleleft + pygame.Vector2(-5*Box.PADDING, 0)
        ]
        pygame.draw.polygon(surface, Color.DARK_BLUE, polygon)
        tb_sprite = DataFiles.sprites["user_interface"]["TB"]
        rect = tb_sprite.get_rect()
        rect.right = polygon[-1].x
        rect.centery = polygon[-1].y
        surface.blit(tb_sprite, rect)

        if button_text == "next":
            center = pygame.Vector2(button.center)
            polygon = [
                center + get_vec(button.width/2, 0),
                center + get_vec(button.width/2, math.radians(135)),
                center + get_vec(button.width/2, math.radians(225))
            ]
            pygame.draw.polygon(surface, Color.BLUE, polygon)
            font.render(surface, button_text, button.center, Color.WHITE, 1, style="center", outline_color=Color.BLACK)
        else:
            rect = get_rect(width=96, height=32, center=button.center) # TODO
            pygame.draw.rect(surface, Color.BLUE, rect)
            font.render(surface, button_text, button.center, Color.WHITE, 1, style="center", outline_color=Color.BLACK)

        text_width = box.width - 2*Box.PADDING
        font.render(
            surface,
            text,
            pygame.Vector2(box.topleft) + pygame.Vector2(Box.PADDING, Box.PADDING),
            Color.WHITE,
            1, 
            box_width=text_width
        )

        if show_reward:
            for rect, (reward, amt) in zip(self.reward_rects, self.rewards.items()):
                if reward in DataFiles.sprites["entity"]:
                    pygame.draw.rect(surface, Color.WHITE, rect, width=Box.OUTLINE_WIDTH)
                    surface.blit(DataFiles.sprites["entity"][reward], rect)
                    font.render(surface, str(amt), rect.center, Color.WHITE, 1, style="center", outline_color=Color.BLACK)
                else:
                    pygame.draw.rect(surface, Color.WHITE, rect, width=Box.OUTLINE_WIDTH)
                    font.render(surface, f"{reward} ({amt})", rect.center, Color.WHITE, 1, style="center", outline_color=Color.BLACK)
