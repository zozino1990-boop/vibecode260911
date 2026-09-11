import random
from pathlib import Path

import pygame


CELL_SIZE = 24
GRID_COLUMNS = 25
GRID_ROWS = 25
BOARD_WIDTH = CELL_SIZE * GRID_COLUMNS
BOARD_HEIGHT = CELL_SIZE * GRID_ROWS
SIDE_WIDTH = 220
WINDOW_WIDTH = BOARD_WIDTH + SIDE_WIDTH
WINDOW_HEIGHT = BOARD_HEIGHT
FPS = 60
MOVE_INTERVAL = 105

BACKGROUND = (8, 18, 28)
BOARD_BACKGROUND = (11, 27, 38)
PANEL = (17, 39, 50)
PANEL_LINE = (38, 78, 86)
TEXT = (231, 255, 248)
MUTED = (132, 173, 170)
MINT = (91, 232, 181)
MINT_DARK = (28, 142, 104)
ORANGE = (255, 156, 79)
RED = (255, 91, 105)

DIRECTIONS = {
    pygame.K_UP: (0, -1),
    pygame.K_w: (0, -1),
    pygame.K_DOWN: (0, 1),
    pygame.K_s: (0, 1),
    pygame.K_LEFT: (-1, 0),
    pygame.K_a: (-1, 0),
    pygame.K_RIGHT: (1, 0),
    pygame.K_d: (1, 0),
}


class SnakeGame:
    def __init__(self):
        self.high_score = self.load_high_score()
        self.reset()

    @staticmethod
    def score_path():
        return Path(__file__).with_name("mysnake-high-score.txt")

    @classmethod
    def load_high_score(cls):
        try:
            return int(cls.score_path().read_text(encoding="utf-8"))
        except (FileNotFoundError, ValueError):
            return 0

    def save_high_score(self):
        self.score_path().write_text(str(self.high_score), encoding="utf-8")

    def reset(self):
        center = (GRID_COLUMNS // 2, GRID_ROWS // 2)
        self.player_snake = [center, (center[0] - 1, center[1]), (center[0] - 2, center[1])]
        self.ai_snake = [(GRID_COLUMNS - 4, GRID_ROWS // 2), (GRID_COLUMNS - 3, GRID_ROWS // 2), (GRID_COLUMNS - 2, GRID_ROWS // 2)]
        self.player_direction = (1, 0)
        self.player_next_direction = self.player_direction
        self.ai_direction = (-1, 0)
        self.food = self.create_food()
        self.player_score = 0
        self.ai_score = 0
        self.move_timer = 0
        self.game_over = False
        self.paused = False
        self.winner = ""

    def create_food(self):
        available = [
            (x, y)
            for y in range(GRID_ROWS)
            for x in range(GRID_COLUMNS)
            if (x, y) not in self.player_snake + self.ai_snake
        ]
        return random.choice(available)

    def change_direction(self, direction):
        if direction == (-self.player_direction[0], -self.player_direction[1]):
            return
        self.player_next_direction = direction

    def choose_ai_direction(self):
        head_x, head_y = self.ai_snake[0]
        options = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        safe_options = []
        for direction in options:
            if direction == (-self.ai_direction[0], -self.ai_direction[1]):
                continue
            next_cell = (head_x + direction[0], head_y + direction[1])
            if self.is_safe(next_cell, self.ai_snake[:-1]):
                safe_options.append(direction)
        if not safe_options:
            return self.ai_direction
        return min(safe_options, key=lambda direction: abs(head_x + direction[0] - self.food[0]) + abs(head_y + direction[1] - self.food[1]))

    @staticmethod
    def is_safe(cell, body):
        return 0 <= cell[0] < GRID_COLUMNS and 0 <= cell[1] < GRID_ROWS and cell not in body

    def move_snake(self, snake, direction):
        head_x, head_y = snake[0]
        new_head = (head_x + direction[0], head_y + direction[1])
        grows = new_head == self.food
        body_to_check = snake if grows else snake[:-1]
        hits_other = new_head in (self.ai_snake if snake is self.player_snake else self.player_snake)
        crashed = not self.is_safe(new_head, body_to_check) or hits_other
        snake.insert(0, new_head)
        if not grows:
            snake.pop()
        return crashed, grows

    def update(self, elapsed_ms):
        if self.game_over or self.paused:
            return
        self.move_timer += elapsed_ms
        if self.move_timer < MOVE_INTERVAL:
            return
        self.move_timer = 0
        self.player_direction = self.player_next_direction
        self.ai_direction = self.choose_ai_direction()
        player_crashed, player_ate = self.move_snake(self.player_snake, self.player_direction)
        ai_crashed, ai_ate = self.move_snake(self.ai_snake, self.ai_direction)
        if player_ate and ai_ate:
            self.player_score += 10
            self.ai_score += 10
            self.food = self.create_food()
        elif player_ate:
            self.player_score += 10
            self.food = self.create_food()
        elif ai_ate:
            self.ai_score += 10
            self.food = self.create_food()
        if player_crashed or ai_crashed or self.player_snake[0] == self.ai_snake[0]:
            self.finish_game(player_crashed, ai_crashed)

    def finish_game(self, player_crashed, ai_crashed):
        self.game_over = True
        if player_crashed and not ai_crashed:
            self.winner = "MACHINE WINS"
        elif ai_crashed and not player_crashed:
            self.winner = "YOU WIN"
        elif self.player_score > self.ai_score:
            self.winner = "YOU WIN"
        elif self.ai_score > self.player_score:
            self.winner = "MACHINE WINS"
        else:
            self.winner = "DRAW"
        if self.player_score > self.high_score:
            self.high_score = self.player_score
            self.save_high_score()


def make_font(size, bold=False):
    return pygame.font.SysFont("consolas", size, bold=bold)


def draw_text(screen, text, position, size, color=TEXT, bold=False):
    screen.blit(make_font(size, bold).render(text, True, color), position)


def draw_cell(screen, cell, color, inset=2):
    x, y = cell
    rect = pygame.Rect(
        x * CELL_SIZE + inset,
        y * CELL_SIZE + inset,
        CELL_SIZE - inset * 2,
        CELL_SIZE - inset * 2,
    )
    pygame.draw.rect(screen, color, rect)
    return rect


def draw_board(screen, game):
    board_rect = pygame.Rect(0, 0, BOARD_WIDTH, BOARD_HEIGHT)
    pygame.draw.rect(screen, BOARD_BACKGROUND, board_rect)
    for x in range(0, BOARD_WIDTH + 1, CELL_SIZE):
        pygame.draw.line(screen, (15, 42, 51), (x, 0), (x, BOARD_HEIGHT))
    for y in range(0, BOARD_HEIGHT + 1, CELL_SIZE):
        pygame.draw.line(screen, (15, 42, 51), (0, y), (BOARD_WIDTH, y))

    food_rect = draw_cell(screen, game.food, ORANGE, 4)
    pygame.draw.circle(screen, (255, 224, 137), food_rect.center, 4)

    for index, segment in enumerate(reversed(game.player_snake)):
        color = MINT_DARK if index else MINT
        draw_cell(screen, segment, color, 2)
    for index, segment in enumerate(reversed(game.ai_snake)):
        color = (39, 104, 190) if index else (91, 157, 255)
        draw_cell(screen, segment, color, 2)
    for snake in (game.player_snake, game.ai_snake):
        head_rect = draw_cell(screen, snake[0], (MINT if snake is game.player_snake else (91, 157, 255)), 2)
        pygame.draw.circle(screen, BACKGROUND, (head_rect.centerx - 4, head_rect.centery - 3), 2)
        pygame.draw.circle(screen, BACKGROUND, (head_rect.centerx + 4, head_rect.centery - 3), 2)


def draw_sidebar(screen, game):
    panel_rect = pygame.Rect(BOARD_WIDTH, 0, SIDE_WIDTH, WINDOW_HEIGHT)
    pygame.draw.rect(screen, PANEL, panel_rect)
    pygame.draw.line(screen, PANEL_LINE, (BOARD_WIDTH, 0), (BOARD_WIDTH, WINDOW_HEIGHT), 2)
    draw_text(screen, "SNAKE DUEL", (BOARD_WIDTH + 22, 28), 27, MINT, True)
    draw_text(screen, "HUMAN VS MACHINE", (BOARD_WIDTH + 24, 64), 10, MUTED)

    pygame.draw.line(screen, PANEL_LINE, (BOARD_WIDTH + 22, 92), (WINDOW_WIDTH - 22, 92))
    draw_text(screen, "YOU", (BOARD_WIDTH + 22, 120), 11, MINT)
    draw_text(screen, f"{game.player_score:05d}", (BOARD_WIDTH + 22, 143), 25, MINT, True)
    draw_text(screen, "MACHINE", (BOARD_WIDTH + 115, 120), 11, (91, 157, 255))
    draw_text(screen, f"{game.ai_score:05d}", (BOARD_WIDTH + 115, 143), 25, (91, 157, 255), True)
    draw_text(screen, "BEST HUMAN", (BOARD_WIDTH + 22, 201), 11, MUTED)
    draw_text(screen, f"{game.high_score:05d}", (BOARD_WIDTH + 22, 224), 24, TEXT, True)

    pygame.draw.line(screen, PANEL_LINE, (BOARD_WIDTH + 22, 275), (WINDOW_WIDTH - 22, 275))
    draw_text(screen, "CONTROLS", (BOARD_WIDTH + 22, 302), 11, MUTED)
    controls = [("WASD", "MOVE"), ("ARROWS", "MOVE"), ("P", "PAUSE"), ("R", "RESTART")]
    for index, (key, label) in enumerate(controls):
        y = 335 + index * 31
        draw_text(screen, key, (BOARD_WIDTH + 22, y), 12, MINT, True)
        draw_text(screen, label, (BOARD_WIDTH + 92, y), 11, TEXT)

    draw_text(screen, "SHARE THE APPLE", (BOARD_WIDTH + 22, WINDOW_HEIGHT - 78), 11, ORANGE, True)
    draw_text(screen, "OUTSMART THE MACHINE", (BOARD_WIDTH + 22, WINDOW_HEIGHT - 54), 10, MUTED)


def draw_overlay(screen, game):
    if not game.game_over and not game.paused:
        return
    overlay = pygame.Surface((BOARD_WIDTH, BOARD_HEIGHT), pygame.SRCALPHA)
    overlay.fill((5, 13, 21, 215))
    screen.blit(overlay, (0, 0))
    if game.game_over:
        title = game.winner
        subtitle = f"YOU {game.player_score:05d}  /  CPU {game.ai_score:05d}"
        prompt = "PRESS R TO RESTART"
        accent = RED
    else:
        title = "PAUSED"
        subtitle = "TAKE A BREATH"
        prompt = "PRESS P TO CONTINUE"
        accent = MINT
    title_surface = make_font(38, True).render(title, True, TEXT)
    screen.blit(title_surface, title_surface.get_rect(center=(BOARD_WIDTH // 2, BOARD_HEIGHT // 2 - 42)))
    subtitle_surface = make_font(17, True).render(subtitle, True, accent)
    screen.blit(subtitle_surface, subtitle_surface.get_rect(center=(BOARD_WIDTH // 2, BOARD_HEIGHT // 2 + 8)))
    prompt_surface = make_font(12).render(prompt, True, MUTED)
    screen.blit(prompt_surface, prompt_surface.get_rect(center=(BOARD_WIDTH // 2, BOARD_HEIGHT // 2 + 48)))


def main():
    pygame.init()
    pygame.display.set_caption("MY SNAKE - pygame")
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    clock = pygame.time.Clock()
    game = SnakeGame()
    running = True

    while running:
        elapsed_ms = clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in DIRECTIONS and not game.game_over:
                    game.change_direction(DIRECTIONS[event.key])
                elif event.key == pygame.K_p and not game.game_over:
                    game.paused = not game.paused
                elif event.key == pygame.K_r:
                    game.reset()
        game.update(elapsed_ms)
        screen.fill(BACKGROUND)
        draw_board(screen, game)
        draw_sidebar(screen, game)
        draw_overlay(screen, game)
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
