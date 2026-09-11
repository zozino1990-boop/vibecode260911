import random
from pathlib import Path

import pygame


COLS = 10
ROWS = 20
CELL = 30
BOARD_WIDTH = COLS * CELL
BOARD_HEIGHT = ROWS * CELL
WINDOW_WIDTH = 760
WINDOW_HEIGHT = 700
FPS = 60

BG = (11, 16, 32)
BOARD_BG = (13, 20, 38)
PANEL = (19, 26, 45)
PANEL_LIGHT = (27, 37, 61)
INK = (246, 247, 251)
MUTED = (140, 149, 173)
CYAN = (77, 225, 225)
PINK = (255, 79, 154)
YELLOW = (248, 211, 79)
COLORS = {
    "I": (77, 225, 225),
    "J": (86, 132, 255),
    "L": (255, 159, 67),
    "O": (248, 211, 79),
    "S": (116, 227, 106),
    "T": (189, 112, 255),
    "Z": (255, 79, 154),
}
SHAPES = {
    "I": [[1, 1, 1, 1]],
    "J": [[1, 0, 0], [1, 1, 1]],
    "L": [[0, 0, 1], [1, 1, 1]],
    "O": [[1, 1], [1, 1]],
    "S": [[0, 1, 1], [1, 1, 0]],
    "T": [[0, 1, 0], [1, 1, 1]],
    "Z": [[1, 1, 0], [0, 1, 1]],
}


class Piece:
    def __init__(self, piece_type):
        self.type = piece_type
        self.matrix = [row[:] for row in SHAPES[piece_type]]
        self.x = 0
        self.y = 0

    def reset_position(self):
        self.x = (COLS - len(self.matrix[0])) // 2
        self.y = 0


class TetrisGame:
    def __init__(self):
        self.high_score = self.load_high_score()
        self.start_game()

    @staticmethod
    def load_high_score():
        score_file = Path(__file__).with_name("neon-tetris-high-score.txt")
        try:
            return int(score_file.read_text(encoding="utf-8"))
        except (FileNotFoundError, ValueError):
            return 0

    def save_high_score(self):
        score_file = Path(__file__).with_name("neon-tetris-high-score.txt")
        score_file.write_text(str(self.high_score), encoding="utf-8")

    def start_game(self):
        self.board = [[None for _ in range(COLS)] for _ in range(ROWS)]
        self.score = 0
        self.lines = 0
        self.level = 1
        self.drop_interval = 900
        self.drop_timer = 0
        self.current = self.random_piece()
        self.next_piece = self.random_piece()
        self.current.reset_position()
        self.started = True
        self.paused = False
        self.game_over = False
        self.line_effect_ms = 0
        self.line_effect_count = 0
        self.line_effect_score = 0

    @staticmethod
    def random_piece():
        return Piece(random.choice(list(SHAPES)))

    def collides(self, piece=None):
        piece = piece or self.current
        for row_index, row in enumerate(piece.matrix):
            for column_index, value in enumerate(row):
                if not value:
                    continue
                board_x = piece.x + column_index
                board_y = piece.y + row_index
                if board_x < 0 or board_x >= COLS or board_y >= ROWS:
                    return True
                if board_y >= 0 and self.board[board_y][board_x] is not None:
                    return True
        return False

    def move(self, direction):
        if not self.started or self.paused:
            return
        self.current.x += direction
        if self.collides():
            self.current.x -= direction

    def rotate(self):
        if not self.started or self.paused:
            return
        original_matrix = [row[:] for row in self.current.matrix]
        original_x = self.current.x
        self.current.matrix = [
            list(row) for row in zip(*self.current.matrix[::-1])
        ]
        offset = 0
        while self.collides():
            offset = -offset + 1 if offset <= 0 else -offset
            self.current.x += offset
            if abs(offset) > len(self.current.matrix[0]):
                self.current.matrix = original_matrix
                self.current.x = original_x
                return

    def soft_drop(self):
        if not self.started or self.paused:
            return
        self.current.y += 1
        if self.collides():
            self.current.y -= 1
            self.lock_piece()
        else:
            self.score += 1
        self.drop_timer = 0

    def hard_drop(self):
        if not self.started or self.paused:
            return
        distance = 0
        while not self.collides():
            self.current.y += 1
            distance += 1
        self.current.y -= 1
        self.score += max(0, distance - 1) * 2
        self.lock_piece()
        self.drop_timer = 0

    def lock_piece(self):
        for row_index, row in enumerate(self.current.matrix):
            for column_index, value in enumerate(row):
                if value and self.current.y + row_index >= 0:
                    self.board[self.current.y + row_index][self.current.x + column_index] = self.current.type
        self.clear_lines()
        self.current = self.next_piece
        self.next_piece = self.random_piece()
        self.current.reset_position()
        if self.collides():
            self.end_game()

    def clear_lines(self):
        complete_rows = [row for row in self.board if all(row)]
        if not complete_rows:
            return
        self.board = [row for row in self.board if not all(row)]
        self.board = [[None for _ in range(COLS)] for _ in complete_rows] + self.board
        cleared = len(complete_rows)
        self.score += [0, 100, 300, 500, 800][cleared] * self.level
        self.lines += cleared
        self.level = self.lines // 10 + 1
        self.drop_interval = max(100, 900 - (self.level - 1) * 70)
        self.line_effect_ms = 420
        self.line_effect_count = cleared
        self.line_effect_score = [0, 100, 300, 500, 800][cleared] * self.level

    def update(self, elapsed_ms):
        self.line_effect_ms = max(0, self.line_effect_ms - elapsed_ms)
        if not self.started or self.paused:
            return
        self.drop_timer += elapsed_ms
        if self.drop_timer > self.drop_interval:
            self.soft_drop_without_bonus()

    def soft_drop_without_bonus(self):
        self.current.y += 1
        if self.collides():
            self.current.y -= 1
            self.lock_piece()
        self.drop_timer = 0

    def toggle_pause(self):
        if self.started:
            self.paused = not self.paused

    def end_game(self):
        self.started = False
        self.game_over = True
        if self.score > self.high_score:
            self.high_score = self.score
            self.save_high_score()


def draw_cell(screen, x, y, color, size=CELL, origin=(0, 0)):
    gap = max(2, int(size * 0.08))
    rect = pygame.Rect(origin[0] + x * size + gap, origin[1] + y * size + gap, size - gap * 2, size - gap * 2)
    pygame.draw.rect(screen, color, rect)
    highlight = tuple(min(255, channel + 50) for channel in color)
    pygame.draw.rect(screen, highlight, (rect.x, rect.y, rect.width, max(2, size // 10)))
    shadow = tuple(max(0, channel - 40) for channel in color)
    pygame.draw.rect(screen, shadow, (rect.x, rect.bottom - max(2, size // 10), rect.width, max(2, size // 10)))


def draw_matrix(screen, matrix, offset_x, offset_y, piece_type, size=CELL, origin=(0, 0)):
    for row_index, row in enumerate(matrix):
        for column_index, value in enumerate(row):
            if value:
                draw_cell(screen, column_index + offset_x, row_index + offset_y, COLORS[piece_type], size, origin)


def font(size, bold=False):
    return pygame.font.SysFont("consolas", size, bold=bold)


def draw_text(screen, text, position, size, color=INK, bold=False):
    screen.blit(font(size, bold).render(text, True, color), position)


def draw_panel(screen, rect):
    pygame.draw.rect(screen, PANEL, rect)
    pygame.draw.rect(screen, (48, 60, 88), rect, 1)


def draw_line_effect(screen, game):
    if game.line_effect_ms <= 0:
        return
    progress = game.line_effect_ms / 420
    flash_alpha = int(105 * progress)
    flash = pygame.Surface((BOARD_WIDTH, BOARD_HEIGHT), pygame.SRCALPHA)
    flash.fill((77, 225, 225, flash_alpha))
    screen.blit(flash, (30, 50))

    scan_y = int((1 - progress) * (BOARD_HEIGHT - 8))
    scan = pygame.Surface((BOARD_WIDTH, 8), pygame.SRCALPHA)
    scan.fill((255, 255, 255, int(220 * progress)))
    screen.blit(scan, (30, 50 + scan_y))

    popup = font(24, bold=True).render(f"+{game.line_effect_score:,}", True, YELLOW)
    popup.set_alpha(int(255 * progress))
    popup_y = 240 - int((1 - progress) * 38)
    screen.blit(popup, (120, popup_y))


def draw_game(screen, game):
    screen.fill(BG)
    pygame.draw.rect(screen, BOARD_BG, (30, 50, BOARD_WIDTH, BOARD_HEIGHT))
    for row_index, row in enumerate(game.board):
        for column_index, piece_type in enumerate(row):
            if piece_type:
                draw_cell(screen, column_index, row_index, COLORS[piece_type], origin=(30, 50))
    if game.started or game.game_over:
            draw_matrix(screen, game.current.matrix, game.current.x, game.current.y, game.current.type, origin=(30, 50))
    draw_line_effect(screen, game)

    draw_text(screen, "NEON TETRIS", (30, 14), 28, INK, True)
    draw_text(screen, "ARCADE / 01", (390, 22), 14, CYAN, True)
    panel_x = 370
    stats = [("SCORE", game.score), ("HIGH SCORE", game.high_score), ("LEVEL", game.level), ("LINES", game.lines)]
    for index, (label, value) in enumerate(stats):
        y = 70 + index * 78
        draw_panel(screen, pygame.Rect(panel_x, y, 280, 62))
        draw_text(screen, label, (panel_x + 14, y + 9), 12, MUTED)
        draw_text(screen, f"{value:,}", (panel_x + 14, y + 28), 21, YELLOW, True)

    next_rect = pygame.Rect(panel_x, 390, 280, 180)
    draw_panel(screen, next_rect)
    draw_text(screen, "NEXT BLOCK", (panel_x + 14, 405), 12, INK, True)
    preview_x = (11 - len(game.next_piece.matrix[0])) // 2
    preview_y = (5 - len(game.next_piece.matrix)) // 2
    draw_matrix(screen, game.next_piece.matrix, preview_x, preview_y, game.next_piece.type, 24, origin=(panel_x + 4, 426))

    draw_text(screen, "ARROWS  MOVE / ROTATE", (370, 600), 12, MUTED)
    draw_text(screen, "SPACE  HARD DROP     P  PAUSE", (370, 622), 12, MUTED)
    draw_text(screen, "BLOCKS FALL. YOU RISE.", (30, 665), 12, (88, 99, 122), True)

    if not game.started:
        overlay = pygame.Surface((BOARD_WIDTH, BOARD_HEIGHT), pygame.SRCALPHA)
        overlay.fill((11, 16, 32, 220))
        screen.blit(overlay, (30, 50))
        message = "GAME OVER" if game.game_over else "NEON TETRIS"
        subtitle = f"{game.score:,} POINTS" if game.game_over else "PRESS ENTER TO START"
        draw_text(screen, message, (65, 285), 32, INK, True)
        draw_text(screen, subtitle, (72, 330), 15, PINK if game.game_over else CYAN, True)

    if game.paused:
        overlay = pygame.Surface((BOARD_WIDTH, BOARD_HEIGHT), pygame.SRCALPHA)
        overlay.fill((11, 16, 32, 220))
        screen.blit(overlay, (30, 50))
        draw_text(screen, "PAUSED", (108, 285), 32, INK, True)
        draw_text(screen, "PRESS P TO CONTINUE", (72, 330), 14, CYAN, True)


def main():
    pygame.init()
    pygame.display.set_caption("NEON TETRIS - DemoSnake.py")
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    clock = pygame.time.Clock()
    game = TetrisGame()
    game.started = False
    running = True

    while running:
        elapsed = clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN and not game.started:
                    game.start_game()
                elif event.key == pygame.K_LEFT:
                    game.move(-1)
                elif event.key == pygame.K_RIGHT:
                    game.move(1)
                elif event.key == pygame.K_UP:
                    game.rotate()
                elif event.key == pygame.K_DOWN:
                    game.soft_drop()
                elif event.key == pygame.K_SPACE:
                    game.hard_drop()
                elif event.key == pygame.K_p:
                    game.toggle_pause()
        game.update(elapsed)
        draw_game(screen, game)
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
