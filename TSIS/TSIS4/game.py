# game.py — Snake Game: full game logic + all screens

from __future__ import annotations

import json
import os
import random
import sys
from enum import Enum, auto
from typing import Optional

import pygame

import db as database
from config import (
    BG_COLOR, BLACK, BLUE, CYAN, DARK_GRAY, DARK_GREEN, DARK_RED,
    FPS, FPS_BASE, FOOD_DISAPPEAR_MS, FOOD_PER_LEVEL,
    GRAY, GREEN, GRID_HEIGHT, GRID_SIZE, GRID_WIDTH,
    HUD_BG, HUD_HEIGHT, LIGHT_GRAY, OBSTACLE_BASE_COUNT,
    OBSTACLE_COLOR, OBSTACLE_MAX, OBSTACLE_PER_LEVEL,
    ORANGE, PURPLE, RED, SPEED_INCREMENT, WALL_COLOR,
    WHITE, WINDOW_HEIGHT, WINDOW_WIDTH, YELLOW,
    POWERUP_EFFECT_MS, POWERUP_FIELD_MS,
)

# ─────────────────────────────────────────────────────────────────────────────
# Enumerations
# ─────────────────────────────────────────────────────────────────────────────

class GameState(Enum):
    MENU        = auto()
    PLAYING     = auto()
    GAME_OVER   = auto()
    LEADERBOARD = auto()
    SETTINGS    = auto()


class Direction(Enum):
    UP    = ( 0, -1)
    DOWN  = ( 0,  1)
    LEFT  = (-1,  0)
    RIGHT = ( 1,  0)

    def opposite(self) -> Direction:
        opp = {
            Direction.UP:    Direction.DOWN,
            Direction.DOWN:  Direction.UP,
            Direction.LEFT:  Direction.RIGHT,
            Direction.RIGHT: Direction.LEFT,
        }
        return opp[self]


class FoodType(Enum):
    NORMAL  = "normal"   # 1 pt, no timer
    SILVER  = "silver"   # 2 pts, timed
    BONUS   = "bonus"    # 3 pts, timed
    POISON  = "poison"   # shortens snake by 2


class PowerUpKind(Enum):
    SPEED_BOOST = "speed_boost"
    SLOW_MOTION = "slow_motion"
    SHIELD      = "shield"


# ─────────────────────────────────────────────────────────────────────────────
# Data classes
# ─────────────────────────────────────────────────────────────────────────────

class Food:
    _CONFIG = {
        FoodType.NORMAL: (GREEN,       1, False),
        FoodType.SILVER: (LIGHT_GRAY,  2, True),
        FoodType.BONUS:  (YELLOW,      3, True),
        FoodType.POISON: (DARK_RED,    0, False),
    }

    def __init__(self, pos: tuple, ftype: FoodType, now: int) -> None:
        self.pos       = pos
        self.ftype     = ftype
        self.spawn_ms  = now
        self.color, self.points, self.timed = self._CONFIG[ftype]

    def is_expired(self, now: int) -> bool:
        return self.timed and (now - self.spawn_ms) > FOOD_DISAPPEAR_MS

    def remaining_frac(self, now: int) -> float:
        """0.0 → 1.0 fraction of lifetime left (for timed foods)."""
        if not self.timed:
            return 1.0
        elapsed = now - self.spawn_ms
        return max(0.0, 1.0 - elapsed / FOOD_DISAPPEAR_MS)


class PowerUp:
    _COLORS = {
        PowerUpKind.SPEED_BOOST: ORANGE,
        PowerUpKind.SLOW_MOTION: CYAN,
        PowerUpKind.SHIELD:      PURPLE,
    }
    _LABELS = {
        PowerUpKind.SPEED_BOOST: "+",
        PowerUpKind.SLOW_MOTION: "~",
        PowerUpKind.SHIELD:      "S",
    }

    def __init__(self, pos: tuple, kind: PowerUpKind, now: int) -> None:
        self.pos      = pos
        self.kind     = kind
        self.spawn_ms = now
        self.color    = self._COLORS[kind]
        self.label    = self._LABELS[kind]

    def is_expired(self, now: int) -> bool:
        return (now - self.spawn_ms) > POWERUP_FIELD_MS


# ─────────────────────────────────────────────────────────────────────────────
# Snake game simulation
# ─────────────────────────────────────────────────────────────────────────────

class SnakeGame:
    """Holds all mutable game state and update logic."""

    def __init__(self, settings: dict, personal_best: int) -> None:
        self.settings      = settings
        self.personal_best = personal_best
        self._reset()

    def _reset(self) -> None:
        cx, cy = GRID_WIDTH // 2, GRID_HEIGHT // 2
        self.body: list[tuple] = [(cx, cy), (cx - 1, cy), (cx - 2, cy)]
        self.direction      = Direction.RIGHT
        self.queued_dir     = Direction.RIGHT
        self.score          = 0
        self.level          = 1
        self.food_count     = 0   # total food items eaten this game
        self.level_food     = 0   # food eaten this level
        self.foods: list[Food]      = []
        self.power_up: Optional[PowerUp] = None
        self.active_effect: Optional[tuple] = None  # (PowerUpKind, end_ms)
        self.shield_ready   = False
        self.obstacles: list[tuple] = []
        self.speed          = FPS_BASE   # moves/second
        self.alive          = True
        self.move_accum     = 0.0        # fractional move accumulator (seconds)
        self._spawn_food()

    # ── helpers ──────────────────────────────────────────────────────────────

    def _occupied(self) -> set:
        occ = set(self.body) | set(self.obstacles)
        for f in self.foods:
            occ.add(f.pos)
        if self.power_up:
            occ.add(self.power_up.pos)
        return occ

    def _random_free(self) -> Optional[tuple]:
        occ  = self._occupied()
        free = [
            (x, y)
            for x in range(1, GRID_WIDTH  - 1)
            for y in range(1, GRID_HEIGHT - 1)
            if (x, y) not in occ
        ]
        return random.choice(free) if free else None

    # ── spawning ─────────────────────────────────────────────────────────────

    def _spawn_food(self) -> None:
        now = pygame.time.get_ticks()
        # Always keep at least one normal food alive
        has_normal = any(f.ftype == FoodType.NORMAL for f in self.foods)
        if not has_normal:
            pos = self._random_free()
            if pos:
                self.foods.append(Food(pos, FoodType.NORMAL, now))

        # Optionally add a special food (max 3 total)
        if len(self.foods) < 3:
            r = random.random()
            if r < 0.18:
                ftype = FoodType.BONUS
            elif r < 0.38:
                ftype = FoodType.SILVER
            elif r < 0.52:
                ftype = FoodType.POISON
            else:
                return
            pos = self._random_free()
            if pos:
                self.foods.append(Food(pos, ftype, now))

    def _maybe_spawn_power_up(self) -> None:
        if self.power_up:
            return
        if random.random() < 0.35:
            pos = self._random_free()
            if pos:
                kind = random.choice(list(PowerUpKind))
                self.power_up = PowerUp(pos, kind, pygame.time.get_ticks())

    def _place_obstacles(self) -> None:
        """Randomly place obstacle blocks for the current level (level ≥ 3)."""
        count = OBSTACLE_BASE_COUNT + (self.level - 3) * OBSTACLE_PER_LEVEL
        count = min(count, OBSTACLE_MAX)

        # Safe zone: 4-cell radius around snake head
        head = self.body[0]
        safe: set = set(self.body)
        for dx in range(-4, 5):
            for dy in range(-4, 5):
                safe.add((head[0] + dx, head[1] + dy))

        new_obs: list[tuple] = []
        for _ in range(count * 10):           # try hard to place them all
            if len(new_obs) >= count:
                break
            x = random.randint(1, GRID_WIDTH  - 2)
            y = random.randint(1, GRID_HEIGHT - 2)
            p = (x, y)
            if p not in safe and p not in new_obs and p not in self._occupied():
                new_obs.append(p)
        self.obstacles = new_obs

    # ── input ────────────────────────────────────────────────────────────────

    def handle_key(self, key: int) -> None:
        mapping = {
            pygame.K_UP:    Direction.UP,
            pygame.K_w:     Direction.UP,
            pygame.K_DOWN:  Direction.DOWN,
            pygame.K_s:     Direction.DOWN,
            pygame.K_LEFT:  Direction.LEFT,
            pygame.K_a:     Direction.LEFT,
            pygame.K_RIGHT: Direction.RIGHT,
            pygame.K_d:     Direction.RIGHT,
        }
        if key in mapping:
            wanted = mapping[key]
            if wanted != self.direction.opposite():
                self.queued_dir = wanted

    # ── update ───────────────────────────────────────────────────────────────

    def update(self, dt: float) -> None:
        """Called every display frame; dt is seconds since last frame."""
        if not self.alive:
            return

        now = pygame.time.get_ticks()

        # ── expire power-up on field ──────────────────────────────────────
        if self.power_up and self.power_up.is_expired(now):
            self.power_up = None

        # ── expire active effect ──────────────────────────────────────────
        if self.active_effect and now >= self.active_effect[1]:
            self._clear_effect()

        # ── remove expired timed foods ────────────────────────────────────
        self.foods = [f for f in self.foods if not f.is_expired(now)]

        # ── accumulate and check if it's time to move ─────────────────────
        self.move_accum += dt
        if self.move_accum < 1.0 / self.speed:
            return
        self.move_accum -= 1.0 / self.speed

        # ── move snake ────────────────────────────────────────────────────
        self.direction = self.queued_dir
        dx, dy = self.direction.value
        hx, hy = self.body[0]
        new_head = (hx + dx, hy + dy)

        # Collision checks ────────────────────────────────────────────────
        wall_hit     = (new_head[0] <= 0 or new_head[0] >= GRID_WIDTH  - 1 or
                        new_head[1] <= 0 or new_head[1] >= GRID_HEIGHT - 1)
        obstacle_hit = new_head in self.obstacles
        self_hit     = new_head in self.body[1:]

        if wall_hit or obstacle_hit or self_hit:
            if self.shield_ready:
                self.shield_ready = False
                self.active_effect = None
                return          # collision absorbed — don't move this tick
            self.alive = False
            return

        # Advance head
        self.body.insert(0, new_head)
        grow = False

        # ── check food ────────────────────────────────────────────────────
        eaten: Optional[Food] = next(
            (f for f in self.foods if f.pos == new_head), None
        )
        if eaten:
            self.foods.remove(eaten)
            if eaten.ftype == FoodType.POISON:
                # Shrink by 2 extra segments (already inserted head, so pop 3)
                for _ in range(3):
                    if len(self.body) > 1:
                        self.body.pop()
                if len(self.body) <= 1:
                    self.alive = False
                    return
                # don't grow
            else:
                self.score      += eaten.points
                self.food_count += 1
                self.level_food += 1
                grow = True
                # Level up?
                if self.level_food >= FOOD_PER_LEVEL:
                    self.level_food = 0
                    self.level     += 1
                    self._update_base_speed()
                    if self.level >= 3:
                        self._place_obstacles()
                self._maybe_spawn_power_up()
        
        if not grow:
            self.body.pop()   # remove tail (no growth)

        # ── check power-up pickup ─────────────────────────────────────────
        if self.power_up and new_head == self.power_up.pos:
            self._collect_power_up(self.power_up)
            self.power_up = None

        # ── ensure food exists ────────────────────────────────────────────
        self._spawn_food()

    def _update_base_speed(self) -> None:
        base = FPS_BASE + (self.level - 1) * SPEED_INCREMENT
        # Only override speed if no time-based effect is overriding it
        if self.active_effect is None:
            self.speed = base

    def _collect_power_up(self, pu: PowerUp) -> None:
        now  = pygame.time.get_ticks()
        base = FPS_BASE + (self.level - 1) * SPEED_INCREMENT
        end  = now + POWERUP_EFFECT_MS

        if pu.kind == PowerUpKind.SPEED_BOOST:
            self.speed  = base + 5
            self.shield_ready  = False
            self.active_effect = (PowerUpKind.SPEED_BOOST, end)
        elif pu.kind == PowerUpKind.SLOW_MOTION:
            self.speed  = max(2, base - 3)
            self.shield_ready  = False
            self.active_effect = (PowerUpKind.SLOW_MOTION, end)
        elif pu.kind == PowerUpKind.SHIELD:
            self.shield_ready  = True
            self.active_effect = (PowerUpKind.SHIELD, end)

    def _clear_effect(self) -> None:
        self.active_effect = None
        self.shield_ready  = False
        self._update_base_speed()

    # ── convenience properties ────────────────────────────────────────────────

    @property
    def head(self) -> tuple:
        return self.body[0]

    def effect_remaining_frac(self) -> float:
        if not self.active_effect:
            return 0.0
        _, end = self.active_effect
        elapsed = POWERUP_EFFECT_MS - (end - pygame.time.get_ticks())
        return max(0.0, 1.0 - elapsed / POWERUP_EFFECT_MS)


# ─────────────────────────────────────────────────────────────────────────────
# Button helper
# ─────────────────────────────────────────────────────────────────────────────

class Button:
    def __init__(self, rect: pygame.Rect, text: str,
                 color=(60, 60, 100), hover=(90, 90, 150),
                 font: Optional[pygame.font.Font] = None) -> None:
        self.rect  = rect
        self.text  = text
        self.color = color
        self.hover = hover
        self.font  = font

    def draw(self, surface: pygame.Surface) -> None:
        mouse   = pygame.mouse.get_pos()
        is_over = self.rect.collidepoint(mouse)
        color   = self.hover if is_over else self.color
        pygame.draw.rect(surface, color,     self.rect, border_radius=8)
        pygame.draw.rect(surface, LIGHT_GRAY, self.rect, 2, border_radius=8)
        if self.font:
            label = self.font.render(self.text, True, WHITE)
            lx    = self.rect.centerx - label.get_width()  // 2
            ly    = self.rect.centery - label.get_height() // 2
            surface.blit(label, (lx, ly))

    def is_clicked(self, event: pygame.event.Event) -> bool:
        return (event.type == pygame.MOUSEBUTTONDOWN and
                event.button == 1 and
                self.rect.collidepoint(event.pos))


# ─────────────────────────────────────────────────────────────────────────────
# Main application / screen manager
# ─────────────────────────────────────────────────────────────────────────────

COLOR_PRESETS = [
    ("Green",  (  0, 200,   0)),
    ("Blue",   (  0, 120, 255)),
    ("Yellow", (255, 220,   0)),
    ("Red",    (220,  50,  50)),
    ("Cyan",   (  0, 210, 210)),
    ("Purple", (180,   0, 220)),
    ("White",  (220, 220, 220)),
    ("Orange", (255, 140,   0)),
]


class GameApp:
    def __init__(self) -> None:
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("🐍  Snake Game")
        self.clock = pygame.time.Clock()

        # Fonts
        self.f_huge   = pygame.font.SysFont("Arial", 56, bold=True)
        self.f_large  = pygame.font.SysFont("Arial", 38, bold=True)
        self.f_medium = pygame.font.SysFont("Arial", 28)
        self.f_small  = pygame.font.SysFont("Arial", 20)
        self.f_tiny   = pygame.font.SysFont("Arial", 15)

        # Settings
        self.settings     = self._load_settings()
        self.state        = GameState.MENU

        # DB
        self.db_ok        = False
        try:
            database.init_db()
            self.db_ok = True
        except Exception as e:
            print(f"[DB] Not available: {e}")

        # Persistent player info
        self.username     = ""
        self.player_id: Optional[int]  = None
        self.personal_best= 0

        # Menu input
        self.username_input = ""
        self.input_active   = True
        self.input_error    = ""

        # Game object
        self.game: Optional[SnakeGame] = None

        # Leaderboard cache
        self.leaderboard: list = []

        # Settings temp copy
        self.settings_tmp    = {}
        self.color_idx       = self._find_color_idx()

        # Pre-build buttons (will be rebuilt each frame but cached here)
        self._build_menu_buttons()
        self._build_gameover_buttons()
        self._build_leaderboard_buttons()
        self._build_settings_buttons()

    # ── settings persistence ─────────────────────────────────────────────────

    def _load_settings(self) -> dict:
        defaults = {"snake_color": [0, 200, 0], "grid_overlay": False, "sound": True}
        try:
            with open("settings.json") as f:
                defaults.update(json.load(f))
        except Exception:
            pass
        return defaults

    def _save_settings(self) -> None:
        with open("settings.json", "w") as f:
            json.dump(self.settings, f, indent=2)

    def _find_color_idx(self) -> int:
        sc = tuple(self.settings.get("snake_color", [0, 200, 0]))
        for i, (_, c) in enumerate(COLOR_PRESETS):
            if c == sc:
                return i
        return 0

    # ── button builders ───────────────────────────────────────────────────────

    def _btn(self, cx: int, cy: int, w: int, h: int, text: str,
             color=(55, 55, 100), hover=(85, 85, 150)) -> Button:
        r = pygame.Rect(cx - w // 2, cy - h // 2, w, h)
        return Button(r, text, color, hover, self.f_medium)

    def _build_menu_buttons(self) -> None:
        cx = WINDOW_WIDTH // 2
        self.btn_play  = self._btn(cx, 370, 220, 50, "▶  Play")
        self.btn_lb    = self._btn(cx, 435, 220, 50, "🏆  Leaderboard")
        self.btn_set   = self._btn(cx, 500, 220, 50, "⚙  Settings")
        self.btn_quit  = self._btn(cx, 565, 220, 50, "✕  Quit", (90, 30, 30), (130, 50, 50))

    def _build_gameover_buttons(self) -> None:
        cx = WINDOW_WIDTH // 2
        self.btn_retry = self._btn(cx - 120, 480, 200, 50, "↺  Retry")
        self.btn_menu  = self._btn(cx + 120, 480, 200, 50, "⌂  Main Menu")

    def _build_leaderboard_buttons(self) -> None:
        self.btn_back_lb = self._btn(WINDOW_WIDTH // 2, 580, 200, 46, "← Back")

    def _build_settings_buttons(self) -> None:
        cx = WINDOW_WIDTH // 2
        self.btn_save_back = self._btn(cx, 555, 240, 50, "💾  Save & Back")

    # ── main loop ─────────────────────────────────────────────────────────────

    def run(self) -> None:
        while True:
            dt = self.clock.tick(FPS) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._quit()
                self._dispatch_event(event)

            self._update(dt)
            self._draw()
            pygame.display.flip()

    def _quit(self) -> None:
        pygame.quit()
        sys.exit()

    # ── event dispatch ────────────────────────────────────────────────────────

    def _dispatch_event(self, event: pygame.event.Event) -> None:
        if self.state == GameState.MENU:
            self._menu_event(event)
        elif self.state == GameState.PLAYING:
            self._play_event(event)
        elif self.state == GameState.GAME_OVER:
            self._gameover_event(event)
        elif self.state == GameState.LEADERBOARD:
            self._lb_event(event)
        elif self.state == GameState.SETTINGS:
            self._settings_event(event)

    # ── update dispatch ───────────────────────────────────────────────────────

    def _update(self, dt: float) -> None:
        if self.state == GameState.PLAYING and self.game:
            self.game.update(dt)
            if not self.game.alive:
                self._on_game_over()

    # ── draw dispatch ─────────────────────────────────────────────────────────

    def _draw(self) -> None:
        self.screen.fill(BG_COLOR)
        if self.state == GameState.MENU:
            self._draw_menu()
        elif self.state == GameState.PLAYING:
            self._draw_game()
        elif self.state == GameState.GAME_OVER:
            self._draw_gameover()
        elif self.state == GameState.LEADERBOARD:
            self._draw_leaderboard()
        elif self.state == GameState.SETTINGS:
            self._draw_settings()

    # =========================================================================
    # MENU screen
    # =========================================================================

    def _menu_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                self.username_input = self.username_input[:-1]
            elif event.key == pygame.K_RETURN:
                self._try_start_game()
            elif len(self.username_input) < 20 and event.unicode.isprintable():
                self.username_input += event.unicode
                self.input_error = ""

        if self.btn_play.is_clicked(event):
            self._try_start_game()
        if self.btn_lb.is_clicked(event):
            self._open_leaderboard()
        if self.btn_set.is_clicked(event):
            self._open_settings()
        if self.btn_quit.is_clicked(event):
            self._quit()

    def _try_start_game(self) -> None:
        name = self.username_input.strip()
        if not name:
            self.input_error = "Please enter a username."
            return
        self.username = name

        if self.db_ok:
            try:
                self.player_id    = database.get_or_create_player(name)
                self.personal_best = database.get_personal_best(self.player_id)
            except Exception as e:
                print(f"[DB] {e}")
                self.player_id    = None
                self.personal_best = 0
        else:
            self.player_id    = None
            self.personal_best = 0

        self.game  = SnakeGame(self.settings, self.personal_best)
        self.state = GameState.PLAYING

    def _open_leaderboard(self) -> None:
        if self.db_ok:
            try:
                self.leaderboard = database.get_leaderboard()
            except Exception as e:
                print(f"[DB] {e}")
                self.leaderboard = []
        self.state = GameState.LEADERBOARD

    def _open_settings(self) -> None:
        self.settings_tmp = dict(self.settings)
        self.color_idx    = self._find_color_idx()
        self.state        = GameState.SETTINGS

    def _draw_menu(self) -> None:
        # Title
        self._draw_text("🐍  SNAKE",  self.f_huge,  WINDOW_WIDTH // 2, 110, GREEN, center=True)
        self._draw_text("GAME",       self.f_huge,  WINDOW_WIDTH // 2, 175, YELLOW, center=True)

        # Username input
        self._draw_text("Enter Username:", self.f_small, WINDOW_WIDTH // 2, 255, LIGHT_GRAY, center=True)
        inp_rect = pygame.Rect(WINDOW_WIDTH // 2 - 130, 270, 260, 42)
        pygame.draw.rect(self.screen, (30, 30, 55), inp_rect, border_radius=6)
        pygame.draw.rect(self.screen, YELLOW if self.input_active else GRAY, inp_rect, 2, border_radius=6)
        display_text = self.username_input + ("|" if pygame.time.get_ticks() % 1000 < 500 else "")
        self._draw_text(display_text, self.f_medium, inp_rect.centerx, inp_rect.centery,
                        WHITE, center=True)

        if self.input_error:
            self._draw_text(self.input_error, self.f_small, WINDOW_WIDTH // 2, 320, RED, center=True)

        if not self.db_ok:
            self._draw_text("⚠ DB offline — scores won't be saved",
                            self.f_tiny, WINDOW_WIDTH // 2, 335, ORANGE, center=True)

        self.btn_play.draw(self.screen)
        self.btn_lb.draw(self.screen)
        self.btn_set.draw(self.screen)
        self.btn_quit.draw(self.screen)

    # =========================================================================
    # PLAYING screen
    # =========================================================================

    def _play_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and self.game:
            self.game.handle_key(event.key)
            if event.key == pygame.K_ESCAPE:
                self.state = GameState.MENU

    def _on_game_over(self) -> None:
        if self.game and self.db_ok and self.player_id is not None:
            try:
                database.save_session(self.player_id, self.game.score, self.game.level)
                self.personal_best = database.get_personal_best(self.player_id)
            except Exception as e:
                print(f"[DB] {e}")
        self.state = GameState.GAME_OVER

    def _draw_game(self) -> None:
        if not self.game:
            return
        g    = self.game
        now  = pygame.time.get_ticks()
        sc   = tuple(self.settings.get("snake_color", [0, 200, 0]))

        # ── HUD background ──────────────────────────────────────────────────
        pygame.draw.rect(self.screen, HUD_BG, (0, 0, WINDOW_WIDTH, HUD_HEIGHT))

        hud_items = [
            (f"Score: {g.score}",         10,   YELLOW),
            (f"Level: {g.level}",         210,  CYAN),
            (f"Best: {self.personal_best}", 400, LIGHT_GRAY),
            (f"Length: {len(g.body)}",    600,  GREEN),
        ]
        for text, x, color in hud_items:
            self._draw_text(text, self.f_small, x + 5, HUD_HEIGHT // 2, color, center=False)

        # Active effect bar
        if g.active_effect:
            kind, end_ms = g.active_effect
            remaining = max(0, end_ms - now)
            frac = remaining / POWERUP_EFFECT_MS
            bar_w = int(150 * frac)
            effect_color = {
                PowerUpKind.SPEED_BOOST: ORANGE,
                PowerUpKind.SLOW_MOTION: CYAN,
                PowerUpKind.SHIELD:      PURPLE,
            }[kind]
            label_map = {
                PowerUpKind.SPEED_BOOST: "FAST",
                PowerUpKind.SLOW_MOTION: "SLOW",
                PowerUpKind.SHIELD:      "SHIELD",
            }
            pygame.draw.rect(self.screen, (50, 50, 80), (WINDOW_WIDTH - 165, 8, 155, 14), border_radius=4)
            pygame.draw.rect(self.screen, effect_color, (WINDOW_WIDTH - 165, 8, bar_w, 14), border_radius=4)
            self._draw_text(label_map[kind], self.f_tiny, WINDOW_WIDTH - 90, 38, effect_color, center=True)

        # ── Game area ────────────────────────────────────────────────────────
        game_top = HUD_HEIGHT
        game_rect = pygame.Rect(0, game_top, WINDOW_WIDTH, WINDOW_HEIGHT - game_top)
        pygame.draw.rect(self.screen, DARK_GRAY, game_rect)

        def cell(x: int, y: int) -> pygame.Rect:
            return pygame.Rect(x * GRID_SIZE, game_top + y * GRID_SIZE, GRID_SIZE, GRID_SIZE)

        # Grid overlay
        if self.settings.get("grid_overlay", False):
            for gx in range(GRID_WIDTH):
                for gy in range(GRID_HEIGHT):
                    pygame.draw.rect(self.screen, (20, 20, 38), cell(gx, gy), 1)

        # Border walls
        for gx in range(GRID_WIDTH):
            pygame.draw.rect(self.screen, WALL_COLOR, cell(gx, 0))
            pygame.draw.rect(self.screen, WALL_COLOR, cell(gx, GRID_HEIGHT - 1))
        for gy in range(GRID_HEIGHT):
            pygame.draw.rect(self.screen, WALL_COLOR, cell(0, gy))
            pygame.draw.rect(self.screen, WALL_COLOR, cell(GRID_WIDTH - 1, gy))

        # Obstacles
        for ox, oy in g.obstacles:
            r = cell(ox, oy)
            pygame.draw.rect(self.screen, OBSTACLE_COLOR, r)
            pygame.draw.rect(self.screen, (140, 90, 40), r, 2)

        # Foods
        for food in g.foods:
            r = cell(*food.pos)
            pygame.draw.rect(self.screen, food.color, r.inflate(-4, -4), border_radius=3)
            if food.timed:
                frac = food.remaining_frac(now)
                bar_h = int((GRID_SIZE - 4) * frac)
                bar_r = pygame.Rect(r.right - 4, r.bottom - bar_h - 2, 3, bar_h)
                pygame.draw.rect(self.screen, WHITE, bar_r)
            # Poison skull indicator
            if food.ftype == FoodType.POISON:
                mid = r.inflate(-6, -6)
                pygame.draw.line(self.screen, WHITE, mid.topleft, mid.bottomright, 2)
                pygame.draw.line(self.screen, WHITE, mid.topright, mid.bottomleft, 2)

        # Power-up
        if g.power_up:
            pu  = g.power_up
            r   = cell(*pu.pos)
            pygame.draw.rect(self.screen, pu.color, r.inflate(-2, -2), border_radius=4)
            pygame.draw.rect(self.screen, WHITE, r.inflate(-2, -2), 2, border_radius=4)
            lbl = self.f_small.render(pu.label, True, WHITE)
            self.screen.blit(lbl, lbl.get_rect(center=r.center))

        # Snake body
        for i, (bx, by) in enumerate(g.body):
            r = cell(bx, by)
            shade = max(30, 200 - i * 4)
            body_color = tuple(min(255, int(c * shade / 200)) for c in sc)
            pygame.draw.rect(self.screen, body_color, r.inflate(-2, -2), border_radius=3)

        # Snake head (brighter)
        hx, hy = g.body[0]
        hr = cell(hx, hy)
        head_color = tuple(min(255, c + 55) for c in sc)
        pygame.draw.rect(self.screen, head_color, hr.inflate(-1, -1), border_radius=4)
        # Eyes
        if g.direction in (Direction.RIGHT, Direction.LEFT):
            eye1 = (hr.centerx + (3 if g.direction == Direction.RIGHT else -3), hr.top + 4)
            eye2 = (hr.centerx + (3 if g.direction == Direction.RIGHT else -3), hr.bottom - 6)
        else:
            eye1 = (hr.left  + 4,  hr.centery + (3 if g.direction == Direction.DOWN else -3))
            eye2 = (hr.right - 6,  hr.centery + (3 if g.direction == Direction.DOWN else -3))
        pygame.draw.circle(self.screen, BLACK, eye1, 2)
        pygame.draw.circle(self.screen, BLACK, eye2, 2)

        # Shield aura
        if g.shield_ready:
            aura = hr.inflate(6, 6)
            pygame.draw.rect(self.screen, PURPLE, aura, 2, border_radius=6)

        # Level banner (brief flash after level-up — not implemented separately,
        # level is shown in HUD)

    # =========================================================================
    # GAME OVER screen
    # =========================================================================

    def _gameover_event(self, event: pygame.event.Event) -> None:
        if self.btn_retry.is_clicked(event):
            self.game = SnakeGame(self.settings, self.personal_best)
            self.state = GameState.PLAYING
        if self.btn_menu.is_clicked(event):
            self.state = GameState.MENU

    def _draw_gameover(self) -> None:
        g = self.game
        self._draw_overlay(160)
        self._draw_text("GAME OVER", self.f_huge, WINDOW_WIDTH // 2, 160, RED, center=True)

        if g:
            self._draw_text(f"Score:  {g.score}",        self.f_large,  WINDOW_WIDTH // 2, 255, YELLOW, center=True)
            self._draw_text(f"Level reached:  {g.level}", self.f_medium, WINDOW_WIDTH // 2, 305, CYAN,   center=True)
            self._draw_text(f"Personal Best:  {self.personal_best}", self.f_medium,
                            WINDOW_WIDTH // 2, 348, LIGHT_GRAY, center=True)
            if g.score > 0 and g.score == self.personal_best:
                self._draw_text("🎉 New personal best!", self.f_medium, WINDOW_WIDTH // 2, 390, YELLOW, center=True)

        if not self.db_ok:
            self._draw_text("(DB offline — result not saved)", self.f_small,
                            WINDOW_WIDTH // 2, 430, ORANGE, center=True)

        self.btn_retry.draw(self.screen)
        self.btn_menu.draw(self.screen)

    # =========================================================================
    # LEADERBOARD screen
    # =========================================================================

    def _lb_event(self, event: pygame.event.Event) -> None:
        if self.btn_back_lb.is_clicked(event):
            self.state = GameState.MENU
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.state = GameState.MENU

    def _draw_leaderboard(self) -> None:
        self._draw_text("🏆  Leaderboard", self.f_large, WINDOW_WIDTH // 2, 50, YELLOW, center=True)

        if not self.db_ok:
            self._draw_text("Database not available.", self.f_medium,
                            WINDOW_WIDTH // 2, 200, RED, center=True)
            self.btn_back_lb.draw(self.screen)
            return

        if not self.leaderboard:
            self._draw_text("No scores yet — be the first!", self.f_medium,
                            WINDOW_WIDTH // 2, 250, LIGHT_GRAY, center=True)
        else:
            # Header
            cols = [(50, "#"), (150, "Username"), (370, "Score"), (530, "Level"), (680, "Date")]
            for cx, header in cols:
                self._draw_text(header, self.f_small, cx, 105, CYAN, center=False)
            pygame.draw.line(self.screen, GRAY, (30, 122), (WINDOW_WIDTH - 30, 122), 1)

            for row in self.leaderboard:
                rank, uname, score, level, played_at = row
                y = 130 + (rank - 1) * 44
                bg_color = (25, 30, 50) if rank % 2 == 0 else (30, 35, 60)
                pygame.draw.rect(self.screen, bg_color, (30, y - 2, WINDOW_WIDTH - 60, 40), border_radius=4)

                medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, str(rank))
                row_color = {1: YELLOW, 2: LIGHT_GRAY, 3: ORANGE}.get(rank, WHITE)

                date_str = played_at.strftime("%m/%d %H:%M") if played_at else "-"
                data = [(50, medal), (150, uname[:14]), (370, str(score)),
                        (530, str(level)), (680, date_str)]
                for cx, val in data:
                    self._draw_text(val, self.f_small, cx, y + 18, row_color, center=False)

        self.btn_back_lb.draw(self.screen)

    # =========================================================================
    # SETTINGS screen
    # =========================================================================

    def _settings_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.state = GameState.MENU

        if self.btn_save_back.is_clicked(event):
            self.settings["snake_color"] = list(COLOR_PRESETS[self.color_idx][1])
            self._save_settings()
            self.state = GameState.MENU

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos

            # Grid toggle
            grid_r = pygame.Rect(WINDOW_WIDTH // 2 - 25, 195, 50, 30)
            if grid_r.collidepoint(mx, my):
                self.settings["grid_overlay"] = not self.settings.get("grid_overlay", False)

            # Sound toggle
            sound_r = pygame.Rect(WINDOW_WIDTH // 2 - 25, 265, 50, 30)
            if sound_r.collidepoint(mx, my):
                self.settings["sound"] = not self.settings.get("sound", True)

            # Color swatches
            for i, (_, col) in enumerate(COLOR_PRESETS):
                sw_x = 120 + i * 65
                sw_r = pygame.Rect(sw_x - 18, 360, 36, 36)
                if sw_r.collidepoint(mx, my):
                    self.color_idx = i

    def _draw_settings(self) -> None:
        self._draw_text("⚙  Settings", self.f_large, WINDOW_WIDTH // 2, 55, CYAN, center=True)

        # Grid overlay
        self._draw_text("Grid Overlay:", self.f_medium, 160, 210, LIGHT_GRAY, center=True)
        self._draw_toggle(WINDOW_WIDTH // 2, 210, self.settings.get("grid_overlay", False))

        # Sound
        self._draw_text("Sound:", self.f_medium, 160, 280, LIGHT_GRAY, center=True)
        self._draw_toggle(WINDOW_WIDTH // 2, 280, self.settings.get("sound", True))

        # Snake color
        self._draw_text("Snake Color:", self.f_medium, WINDOW_WIDTH // 2, 330, LIGHT_GRAY, center=True)
        for i, (name, col) in enumerate(COLOR_PRESETS):
            sw_x = 120 + i * 65
            sw_r = pygame.Rect(sw_x - 18, 360, 36, 36)
            pygame.draw.rect(self.screen, col, sw_r, border_radius=5)
            if i == self.color_idx:
                pygame.draw.rect(self.screen, WHITE, sw_r, 3, border_radius=5)
                self._draw_text(name, self.f_tiny, sw_x, 405, WHITE, center=True)

        self._draw_text("(changes take effect next game)", self.f_tiny,
                        WINDOW_WIDTH // 2, 445, GRAY, center=True)

        self.btn_save_back.draw(self.screen)

    def _draw_toggle(self, cx: int, cy: int, on: bool) -> None:
        r = pygame.Rect(cx - 25, cy - 15, 50, 30)
        bg = (0, 180, 80) if on else (80, 80, 80)
        pygame.draw.rect(self.screen, bg, r, border_radius=15)
        knob_x = r.right - 17 if on else r.left + 17
        pygame.draw.circle(self.screen, WHITE, (knob_x, cy), 11)
        label = "ON" if on else "OFF"
        lbl = self.f_tiny.render(label, True, WHITE)
        self.screen.blit(lbl, lbl.get_rect(center=(cx + (15 if on else -15), cy)))

    # =========================================================================
    # Shared drawing utilities
    # =========================================================================

    def _draw_text(self, text: str, font: pygame.font.Font,
                   x: int, y: int, color: tuple, center: bool = True) -> None:
        surf = font.render(text, True, color)
        if center:
            self.screen.blit(surf, surf.get_rect(center=(x, y)))
        else:
            self.screen.blit(surf, (x, y - surf.get_height() // 2))

    def _draw_overlay(self, alpha: int = 160) -> None:
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, alpha))
        self.screen.blit(overlay, (0, 0))
