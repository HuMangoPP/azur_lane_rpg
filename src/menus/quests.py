import pygame

from engine.util import get_rect

from src.constants import Box, Color, screen_x, screen_y

class QuestManager:
    def __init__(self):
        self.quests = {}
        self.selected_quest_id = None
    
    @property
    def started_quests(self):
        return {quest_id: quest for quest_id, quest in self.quests.items()}

    @property
    def selected_quest(self):
        return self.quests.get(self.selected_quest_id)

    def select_quest(self, mpos):
        for i, quest in enumerate(self.quests):
            rect = get_rect(
                width=Box.WIDTH, height=Box.HEIGHT,
                left=Box.PADDING,
                top=Box.PADDING + (Box.HEIGHT + Box.PADDING) * i
            )
            if rect.collidepoint(mpos):
                self.selected_quest_id = quest
                break
        else:
            self.selected_quest_id = None

    def draw(self, surface, font):
        for i, quest in enumerate(self.quests.values()):
            rect = get_rect(
                width=Box.WIDTH, height=Box.HEIGHT,
                left=Box.PADDING,
                top=Box.PADDING + (Box.HEIGHT + Box.PADDING) * i
            )
            pygame.draw.rect(surface, Color.WHITE, rect, Box.OUTLINE_WIDTH)

            if not quest.started:
                font.render(surface, "new", rect.center, Color.WHITE, 1, style="center", outline_color=Color.BLACK)
            elif quest.completed:
                font.render(surface, "completed", rect.center, Color.WHITE, 1, style="center", outline_color=Color.BLACK)
        
        if self.selected_quest_id is not None:
            self.selected_quest.draw(surface, font)

class Quest:
    DIALOGUE_OVERLAY = get_rect(width=200, height=200, centerx=screen_x(0.5), centery=screen_y(0.5))
    DIALOGUE_BOX = get_rect(
        width=DIALOGUE_OVERLAY.width - 2*Box.PADDING,
        height=DIALOGUE_OVERLAY.height - 2*Box.PADDING - Box.HEIGHT/2,
        top=DIALOGUE_OVERLAY.top + Box.PADDING,
        left=DIALOGUE_OVERLAY.left + Box.PADDING
    )
    def __init__(self, dialogue_texts, completion_criteria, tutorial_draw):
        self.started = False
        self.completed = False

        self.dialogue_index = 0
        self.dialogue_texts = dialogue_texts
        self.side_effects = [lambda : True] 

        self.next_button = get_rect(
            width=Box.WIDTH, height=Box.HEIGHT,
            centerx=self.DIALOGUE_OVERLAY.centerx,
            centery=self.DIALOGUE_OVERLAY.bottom
        )

        self.completion_criteria = completion_criteria
        self.tutorial_draw = tutorial_draw
    
    def go_next(self, mpos):
        if self.next_button.collidepoint(mpos):
            self.dialogue_index += 1
            if self.dialogue_index == len(self.dialogue_texts):
                self.dialogue_index = len(self.dialogue_texts) - 1
                self.started = True
    
    def draw(self, surface, font):
        pygame.draw.rect(surface, Color.BLUE_GREY, self.DIALOGUE_OVERLAY)
        pygame.draw.rect(surface, Color.DARK_BLUE, self.DIALOGUE_BOX)
        pygame.draw.rect(surface, Color.BLUE, self.next_button)

        text = self.dialogue_texts[self.dialogue_index]
        text_width = self.DIALOGUE_BOX.width - 2*Box.PADDING
        font.render(
            surface,
            text,
            pygame.Vector2(self.DIALOGUE_BOX.topleft) + pygame.Vector2(Box.PADDING, Box.PADDING),
            Color.WHITE,
            1, 
            box_width=text_width
        )