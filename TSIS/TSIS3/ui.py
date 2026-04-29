"""
ui.py — All Pygame screens drawn without external UI libraries.

Screens:
  MainMenu       — Play / Leaderboard / Settings / Quit
  SettingsScreen — Sound toggle, car colour, difficulty
  GameOverScreen — Score / distance / coins + Retry / Main Menu
  LeaderboardScreen — Top 10 with rank / name / score / distance
  UsernameEntry  — Keyboard text input before race
"""

import pygame
import math

# ── Shared palette ────────────────────────────────────────────────────────────
WHITE      = (255, 255, 255)
BLACK      = (  0,   0,   0)
GRAY       = (100, 100, 100)
LIGHT_GRAY = (190, 190, 200)
RED        = (220,  50,  50)
GREEN      = ( 50, 200,  80)
BLUE       = ( 50, 130, 220)
YELLOW     = (240, 200,   0)
ORANGE     = (255, 140,   0)
CYAN       = (  0, 220, 220)

_BG_TOP = ( 18,  18,  38)
_BG_BOT = (  8,   8,  22)

CAR_COLOUR_MAP = {
    "red":    (220,  50,  50),
    "blue":   ( 50, 130, 220),
    "green":  ( 50, 200,  80),
    "yellow": (240, 200,   0),
    "purple": (160,  50, 220),
}
DIFFICULTIES = ["easy", "normal", "hard"]


# ─────────────────────────────────────────────────────────────────────────────
def _gradient_bg(surface: pygame.Surface, w: int, h: int):
    """Draw a dark top-to-bottom gradient background."""
    for y in range(h):
        t = y / h
        col = tuple(int(_BG_TOP[i] * (1 - t) + _BG_BOT[i] * t) for i in range(3))
        pygame.draw.line(surface, col, (0, y), (w, y))


def _panel(surface, rect, border=(80, 80, 120)):
    """Draw a semi-transparent rounded panel."""
    s = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    s.fill((28, 28, 55, 200))
    surface.blit(s, rect.topleft)
    pygame.draw.rect(surface, border, rect, 2, border_radius=12)


# ─────────────────────────────────────────────────────────────────────────────
class Button:
    """A simple rectangular button with hover highlight."""

    def __init__(self, x, y, w, h, text,
                 color=(55, 55, 82), hover=(82, 82, 128),
                 text_color=WHITE, font_size=30):
        self.rect       = pygame.Rect(x, y, w, h)
        self.text       = text
        self.color      = color
        self.hover      = hover
        self.text_color = text_color
        self._font      = pygame.font.SysFont(None, font_size)
        self._hovered   = False

    def handle(self, events) -> bool:
        mx, my = pygame.mouse.get_pos()
        self._hovered = self.rect.collidepoint(mx, my)
        for e in events:
            if (e.type == pygame.MOUSEBUTTONDOWN
                    and e.button == 1
                    and self._hovered):
                return True
        return False

    def draw(self, surface: pygame.Surface):
        col = self.hover if self._hovered else self.color
        pygame.draw.rect(surface, col,  self.rect, border_radius=9)
        pygame.draw.rect(surface, WHITE, self.rect, 2, border_radius=9)
        txt = self._font.render(self.text, True, self.text_color)
        surface.blit(txt, (self.rect.centerx - txt.get_width()  // 2,
                            self.rect.centery - txt.get_height() // 2))


# ─────────────────────────────────────────────────────────────────────────────
class MainMenu:
    def __init__(self, w: int, h: int):
        self.w, self.h = w, h
        self._title = pygame.font.SysFont(None, 80)
        self._sub   = pygame.font.SysFont(None, 28)
        bw, bh, cx = 210, 52, w // 2 - 105
        self._btns = {
            "play":        Button(cx, 240, bw, bh, "▶  PLAY",
                                  (40, 145, 70), (55, 175, 90)),
            "leaderboard": Button(cx, 308, bw, bh, "🏆  LEADERBOARD"),
            "settings":    Button(cx, 376, bw, bh, "⚙  SETTINGS"),
            "quit":        Button(cx, 444, bw, bh, "✕  QUIT",
                                  (145, 45, 45), (175, 65, 65)),
        }
        self._t = 0.0

    def handle(self, events) -> str | None:
        for name, btn in self._btns.items():
            if btn.handle(events):
                return name
        return None

    def draw(self, surface: pygame.Surface):
        _gradient_bg(surface, self.w, self.h)
        self._t += 0.016

        # Scrolling road decoration
        dash_period = 60
        for lane_x in [self.w // 2 - 2]:
            for i in range(12):
                y = int((i * dash_period + self._t * 180) % self.h)
                pygame.draw.rect(surface, (45, 45, 60), (lane_x, y, 4, 30))

        # Title with drop-shadow
        title_txt = self._title.render("RACER", True, (240, 200, 0))
        shadow_txt = self._title.render("RACER", True, (90, 70, 0))
        tx = self.w // 2 - title_txt.get_width() // 2
        surface.blit(shadow_txt, (tx + 4, 110))
        surface.blit(title_txt,  (tx,     107))

        sub = self._sub.render("Dodge traffic · Collect coins · Survive",
                               True, LIGHT_GRAY)
        surface.blit(sub, (self.w // 2 - sub.get_width() // 2, 185))

        for btn in self._btns.values():
            btn.draw(surface)

        ver = pygame.font.SysFont(None, 18).render(
            "Practice 12 — TSIS3", True, GRAY)
        surface.blit(ver, (self.w // 2 - ver.get_width() // 2, self.h - 22))


# ─────────────────────────────────────────────────────────────────────────────
class SettingsScreen:
    _DIFF_COLORS = {
        "easy":   ( 40, 180,  75),
        "normal": (230, 155,   0),
        "hard":   (210,  45,  45),
    }

    def __init__(self, w: int, h: int, settings: dict):
        self.w, self.h  = w, h
        self.settings   = dict(settings)
        self._title_f   = pygame.font.SysFont(None, 52)
        self._label_f   = pygame.font.SysFont(None, 28)
        self._sm_f      = pygame.font.SysFont(None, 20)

        self._back_btn  = Button(w // 2 - 90, h - 72, 180, 48, "◀  BACK")
        self._sound_btn = Button(w // 2 + 20, 148, 110, 40, "ON",
                                 (40, 175, 70), (55, 205, 90))

        # Car colour swatches  (5 colours × 56 px wide)
        self._colour_rects = {}
        swatch_start = (w - (len(CAR_COLOUR_MAP) * 56 - 6)) // 2
        for i, cn in enumerate(CAR_COLOUR_MAP):
            self._colour_rects[cn] = pygame.Rect(swatch_start + i * 56, 252, 50, 44)

        # Difficulty buttons
        self._diff_rects = {}
        d_start = (w - 3 * 118) // 2
        for i, d in enumerate(DIFFICULTIES):
            self._diff_rects[d] = pygame.Rect(d_start + i * 118, 358, 110, 44)

    def set_settings(self, settings: dict):
        self.settings = dict(settings)

    def handle(self, events):
        if self._back_btn.handle(events):
            return "back", self.settings

        for e in events:
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                mx, my = e.pos
                # Sound
                if self._sound_btn.rect.collidepoint(mx, my):
                    self.settings["sound"] = not self.settings.get("sound", True)
                # Colour
                for cn, r in self._colour_rects.items():
                    if r.collidepoint(mx, my):
                        self.settings["car_color"] = cn
                # Difficulty
                for d, r in self._diff_rects.items():
                    if r.collidepoint(mx, my):
                        self.settings["difficulty"] = d

        return None, self.settings

    def draw(self, surface: pygame.Surface):
        _gradient_bg(surface, self.w, self.h)

        title = self._title_f.render("SETTINGS", True, WHITE)
        surface.blit(title, (self.w // 2 - title.get_width() // 2, 34))

        # ── Sound ──
        lbl = self._label_f.render("Sound:", True, LIGHT_GRAY)
        surface.blit(lbl, (60, 157))
        sound_on = self.settings.get("sound", True)
        self._sound_btn.text  = "ON"  if sound_on else "OFF"
        self._sound_btn.color = (40, 175, 70)   if sound_on else (175, 45, 45)
        self._sound_btn.hover = (55, 205, 90)   if sound_on else (205, 65, 65)
        self._sound_btn.draw(surface)

        # ── Car colour ──
        lbl2 = self._label_f.render("Car colour:", True, LIGHT_GRAY)
        surface.blit(lbl2, (60, 222))
        for cn, r in self._colour_rects.items():
            pygame.draw.rect(surface, CAR_COLOUR_MAP[cn], r, border_radius=8)
            if self.settings.get("car_color") == cn:
                pygame.draw.rect(surface, WHITE, r, 3, border_radius=8)
            abbr = self._sm_f.render(cn[:3].upper(), True, WHITE)
            surface.blit(abbr, (r.centerx - abbr.get_width() // 2,
                                r.centery - abbr.get_height() // 2))

        # ── Difficulty ──
        lbl3 = self._label_f.render("Difficulty:", True, LIGHT_GRAY)
        surface.blit(lbl3, (60, 326))
        for d, r in self._diff_rects.items():
            sel = self.settings.get("difficulty") == d
            col = self._DIFF_COLORS[d] if sel else (52, 52, 78)
            pygame.draw.rect(surface, col, r, border_radius=8)
            pygame.draw.rect(surface, WHITE if sel else GRAY, r, 2, border_radius=8)
            dlbl = self._label_f.render(d.capitalize(), True, WHITE)
            surface.blit(dlbl, (r.centerx - dlbl.get_width() // 2,
                                r.centery - dlbl.get_height() // 2))

        # Hint
        hint = self._sm_f.render(
            "Settings saved automatically when you leave.", True, GRAY)
        surface.blit(hint, (self.w // 2 - hint.get_width() // 2, self.h - 108))

        self._back_btn.draw(surface)


# ─────────────────────────────────────────────────────────────────────────────
class GameOverScreen:
    def __init__(self, w: int, h: int, score: int, distance: int,
                 coins: int, player_name: str = ""):
        self.w, self.h     = w, h
        self.score         = score
        self.distance      = distance
        self.coins         = coins
        self.player_name   = player_name
        self._title_f      = pygame.font.SysFont(None, 70)
        self._stat_f       = pygame.font.SysFont(None, 32)
        self._name_f       = pygame.font.SysFont(None, 28)
        bw = 180
        mid = w // 2
        self._retry_btn = Button(mid - bw - 8, h - 106, bw, 52,
                                 "↺  RETRY", (40, 145, 70), (55, 175, 90))
        self._menu_btn  = Button(mid + 8,      h - 106, bw, 52, "⌂  MENU")

    def handle(self, events) -> str | None:
        if self._retry_btn.handle(events):
            return "retry"
        if self._menu_btn.handle(events):
            return "menu"
        return None

    def draw(self, surface: pygame.Surface):
        _gradient_bg(surface, self.w, self.h)

        title = self._title_f.render("GAME OVER", True, RED)
        surface.blit(title, (self.w // 2 - title.get_width() // 2, 82))

        if self.player_name:
            nm = self._name_f.render(f"Driver: {self.player_name}", True, LIGHT_GRAY)
            surface.blit(nm, (self.w // 2 - nm.get_width() // 2, 158))

        # Stats panel
        panel_r = pygame.Rect(self.w // 2 - 165, 192, 330, 210)
        _panel(surface, panel_r)

        stats = [
            ("Score",    str(self.score),    YELLOW),
            ("Distance", f"{self.distance} m", (180, 255, 180)),
            ("Coins",    str(self.coins),    (240, 200, 0)),
        ]
        for i, (label, val, col) in enumerate(stats):
            y = 212 + i * 62
            lbl = self._stat_f.render(label + ":", True, LIGHT_GRAY)
            vtxt = self._stat_f.render(val, True, col)
            surface.blit(lbl,  (panel_r.x + 24,  y))
            surface.blit(vtxt, (panel_r.right - vtxt.get_width() - 24, y))

        self._retry_btn.draw(surface)
        self._menu_btn.draw(surface)


# ─────────────────────────────────────────────────────────────────────────────
class LeaderboardScreen:
    _RANK_COLORS = [(240, 200, 0), (200, 200, 210), (200, 140, 60)]

    def __init__(self, w: int, h: int):
        self.w, self.h = w, h
        self.data      = []
        self._title_f  = pygame.font.SysFont(None, 52)
        self._hdr_f    = pygame.font.SysFont(None, 22)
        self._row_f    = pygame.font.SysFont(None, 24)
        self._back_btn = Button(w // 2 - 90, h - 66, 180, 46, "◀  BACK")

    def set_data(self, data: list):
        self.data = data

    def handle(self, events) -> str | None:
        if self._back_btn.handle(events):
            return "back"
        return None

    def draw(self, surface: pygame.Surface):
        _gradient_bg(surface, self.w, self.h)

        title = self._title_f.render("LEADERBOARD", True, YELLOW)
        surface.blit(title, (self.w // 2 - title.get_width() // 2, 22))

        # Column headers
        cols = [28, 60, 200, 305, 390]
        hdrs = ["#", "Name", "Score", "Dist", "Coins"]
        for hdr, cx in zip(hdrs, cols):
            ht = self._hdr_f.render(hdr, True, LIGHT_GRAY)
            surface.blit(ht, (cx, 82))
        pygame.draw.line(surface, GRAY, (18, 104), (self.w - 18, 104), 1)

        # Rows
        for i, entry in enumerate(self.data[:10]):
            ry = 110 + i * 46
            # Alternating row tint
            if i % 2 == 0:
                row_s = pygame.Surface((self.w - 36, 40), pygame.SRCALPHA)
                row_s.fill((40, 40, 72, 160))
                surface.blit(row_s, (18, ry - 2))

            rank_col = (self._RANK_COLORS[i] if i < 3 else WHITE)
            items = [
                (str(i + 1),                cols[0], rank_col),
                (entry.get("name", "---")[:12], cols[1], WHITE),
                (str(entry.get("score", 0)),    cols[2], YELLOW),
                (f"{entry.get('distance', 0)}m", cols[3], (180, 255, 180)),
                (str(entry.get("coins", 0)),    cols[4], (240, 200, 0)),
            ]
            for text, cx, col in items:
                txt = self._row_f.render(text, True, col)
                surface.blit(txt, (cx, ry + 8))

        if not self.data:
            empty = self._row_f.render(
                "No scores yet. Play to enter the board!", True, GRAY)
            surface.blit(empty, (self.w // 2 - empty.get_width() // 2, 240))

        self._back_btn.draw(surface)


# ─────────────────────────────────────────────────────────────────────────────
class UsernameEntry:
    MAX_LEN = 15

    def __init__(self, w: int, h: int):
        self.w, self.h  = w, h
        self.name       = ""
        self._title_f   = pygame.font.SysFont(None, 52)
        self._input_f   = pygame.font.SysFont(None, 38)
        self._hint_f    = pygame.font.SysFont(None, 24)
        bw = 190
        cx = w // 2 - bw // 2
        self._start_btn = Button(cx, h - 116, bw, 52, "▶  START",
                                 (40, 145, 70), (55, 175, 90))
        self._back_btn  = Button(cx, h - 56,  bw, 42, "◀  BACK")
        self._cursor    = True
        self._cursor_t  = 0.0

    def reset(self):
        self.name    = ""
        self._cursor = True

    def handle(self, events):
        self._cursor_t += 0.016
        if self._cursor_t >= 0.5:
            self._cursor   = not self._cursor
            self._cursor_t = 0.0

        for e in events:
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_BACKSPACE:
                    self.name = self.name[:-1]
                elif e.key == pygame.K_RETURN:
                    if self.name.strip():
                        return "start", self.name.strip()
                elif (len(self.name) < self.MAX_LEN
                      and e.unicode.isprintable()
                      and e.unicode != ""):
                    self.name += e.unicode

        if self._start_btn.handle(events) and self.name.strip():
            return "start", self.name.strip()
        if self._back_btn.handle(events):
            return "back", ""
        return None, self.name

    def draw(self, surface: pygame.Surface):
        _gradient_bg(surface, self.w, self.h)

        title = self._title_f.render("ENTER YOUR NAME", True, WHITE)
        surface.blit(title, (self.w // 2 - title.get_width() // 2, 110))

        # Input box
        box = pygame.Rect(self.w // 2 - 170, 220, 340, 60)
        _panel(surface, box, border=(100, 100, 200))
        display = self.name + ("|" if self._cursor else " ")
        inp = self._input_f.render(display, True, WHITE)
        surface.blit(inp, (box.x + 14, box.y + 14))

        # Char counter
        cnt = self._hint_f.render(
            f"{len(self.name)}/{self.MAX_LEN}", True, GRAY)
        surface.blit(cnt, (box.right - cnt.get_width() - 8, box.bottom + 6))

        hint = self._hint_f.render(
            "Type your name · Enter or click START", True, GRAY)
        surface.blit(hint, (self.w // 2 - hint.get_width() // 2, 302))

        self._start_btn.draw(surface)
        self._back_btn.draw(surface)
