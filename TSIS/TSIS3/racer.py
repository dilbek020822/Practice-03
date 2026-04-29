"""
racer.py — Core game objects and RacerGame controller.

Built on top of Practice 10/11 foundations:
  • Lane-based road scrolling            (P10)
  • Random weighted coins + counter      (P10/P11)
  • Enemy speed scaling with coins       (P11)

New in this file (Practice 12):
  • Lane hazards: oil spills, barriers, potholes, speed bumps, nitro strips
  • Dynamic traffic cars with collision logic
  • Power-ups: Nitro, Shield, Repair (one active at a time)
  • Safe-spawn logic (no spawns directly on player)
  • Difficulty scaling by distance (level up every 500 m)
  • Particle effects for collisions / pickups
"""

import pygame
import random
import math

# ── Palette ───────────────────────────────────────────────────────────────────
WHITE       = (255, 255, 255)
BLACK       = (0,   0,   0)
GRAY        = (100, 100, 100)
LIGHT_GRAY  = (190, 190, 200)
YELLOW      = (240, 200,   0)
ORANGE      = (255, 140,   0)
RED         = (220,  50,  50)
GREEN       = ( 50, 200,  80)
BLUE        = ( 50, 130, 220)
CYAN        = (  0, 220, 220)
ROAD_COLOR  = ( 48,  50,  58)
GRASS_COLOR = ( 35, 110,  35)
LANE_DASH   = (240, 220,  50)

CAR_COLORS = {
    "red":    (220,  50,  50),
    "blue":   ( 50, 130, 220),
    "green":  ( 50, 200,  80),
    "yellow": (240, 200,   0),
    "purple": (160,  50, 220),
}

LANE_COUNT = 3
ROAD_W     = 294         # divisible by LANE_COUNT
ROAD_PAD   = 10          # coloured kerb on each side


# ─────────────────────────────────────────────────────────────────────────────
class Road:
    """Scrolling three-lane road with animated dashes and kerb stripes."""

    DASH_H   = 32
    DASH_GAP = 28

    def __init__(self, sw: int, sh: int):
        self.sw, self.sh = sw, sh
        self.left  = (sw - ROAD_W) // 2
        self.right = self.left + ROAD_W
        self.lane_w = ROAD_W // LANE_COUNT
        self.offset  = 0.0
        self.period  = self.DASH_H + self.DASH_GAP
        self.kerb_timer = 0.0          # for animated kerb stripes

    def get_lane_cx(self, lane: int) -> int:
        return self.left + self.lane_w * lane + self.lane_w // 2

    def update(self, dt: float, speed: float) -> None:
        self.offset    = (self.offset + speed * dt) % self.period
        self.kerb_timer = (self.kerb_timer + speed * dt * 0.003) % 1.0

    def draw(self, surface: pygame.Surface) -> None:
        # Grass
        pygame.draw.rect(surface, GRASS_COLOR, (0, 0, self.left, self.sh))
        pygame.draw.rect(surface, GRASS_COLOR,
                         (self.right, 0, self.sw - self.right, self.sh))

        # Road body
        pygame.draw.rect(surface, ROAD_COLOR, (self.left, 0, ROAD_W, self.sh))

        # Animated red-white kerb stripes (left)
        stripe_w = 10
        stripe_h = 24
        n_stripes = self.sh // stripe_h + 2
        shift = int(self.kerb_timer * stripe_h * 2) % (stripe_h * 2)
        for i in range(n_stripes):
            y = i * stripe_h - shift
            col = RED if i % 2 == 0 else WHITE
            pygame.draw.rect(surface, col, (self.left - stripe_w, y, stripe_w, stripe_h))
            pygame.draw.rect(surface, col, (self.right, y, stripe_w, stripe_h))

        # Lane dashes
        for lane_idx in range(1, LANE_COUNT):
            x = self.left + self.lane_w * lane_idx - 2
            y = -self.period + self.offset
            while y < self.sh:
                pygame.draw.rect(surface, LANE_DASH, (x, int(y), 4, self.DASH_H))
                y += self.period


# ─────────────────────────────────────────────────────────────────────────────
def _draw_car(surface, x, y, w, h, body_col, windshield_top=True):
    """Generic car shape: body + windshield + four wheels."""
    # Body
    pygame.draw.rect(surface, body_col,
                     pygame.Rect(x, y, w, h), border_radius=7)
    # Windshield
    ws_y = y + 6 if windshield_top else y + h - 24
    pygame.draw.rect(surface, (170, 215, 255),
                     pygame.Rect(x + 7, ws_y, w - 14, 18), border_radius=4)
    # Rear window
    rw_y = y + h - 22 if windshield_top else y + 6
    pygame.draw.rect(surface, (130, 180, 220),
                     pygame.Rect(x + 7, rw_y, w - 14, 14), border_radius=3)
    # Wheels
    wc = (25, 25, 25)
    ww, wh = 9, 15
    for wx, wy in [(x - 6, y + 8),  (x + w - 3, y + 8),
                   (x - 6, y + h - 23), (x + w - 3, y + h - 23)]:
        pygame.draw.rect(surface, wc, (wx, wy, ww, wh), border_radius=3)
        pygame.draw.rect(surface, (60, 60, 60), (wx + 2, wy + 2, ww - 4, wh - 4),
                         border_radius=2)


# ─────────────────────────────────────────────────────────────────────────────
class Player:
    W, H = 36, 62

    def __init__(self, road: Road, color=(220, 50, 50)):
        self.road   = road
        self.lane   = 1
        self._tgt   = 1        # target lane
        self.x      = float(road.get_lane_cx(1) - self.W // 2)
        self.y      = 0
        self.color  = color
        self._moving = False
        self.SWITCH_SPD = 420  # px / s

        self.shields  = 0
        self.debuffs  = {}     # name -> remaining seconds

    def set_y(self, y: int):
        self.y = y

    def _can_switch(self) -> bool:
        return not self._moving and "oil" not in self.debuffs

    def move_left(self):
        if self._can_switch() and self._tgt > 0:
            self._tgt -= 1
            self._moving = True

    def move_right(self):
        if self._can_switch() and self._tgt < LANE_COUNT - 1:
            self._tgt += 1
            self._moving = True

    def update(self, dt: float):
        # Slide toward target lane
        target_x = float(self.road.get_lane_cx(self._tgt) - self.W // 2)
        if self._moving:
            diff = target_x - self.x
            step = self.SWITCH_SPD * dt
            if abs(diff) <= step:
                self.x = target_x
                self.lane = self._tgt
                self._moving = False
            else:
                self.x += math.copysign(step, diff)

        # Tick debuffs
        expired = [k for k, v in self.debuffs.items() if v - dt <= 0]
        for k in expired:
            del self.debuffs[k]
        for k in list(self.debuffs):
            self.debuffs[k] -= dt

    def get_rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x) + 5, self.y + 5, self.W - 10, self.H - 10)

    def draw(self, surface: pygame.Surface):
        _draw_car(surface, int(self.x), self.y, self.W, self.H, self.color)
        if self.shields:
            pygame.draw.rect(surface, CYAN,
                             pygame.Rect(int(self.x) - 3, self.y - 3,
                                         self.W + 6, self.H + 6), 3, border_radius=9)


# ─────────────────────────────────────────────────────────────────────────────
_ENEMY_PALETTES = [
    (180, 60,  60), (60,  60, 180), (60, 160,  60),
    (170,120,  50), (140, 60, 170), (200,120,  40),
]

class EnemyCar:
    W, H = 36, 62

    def __init__(self, road: Road, lane: int, speed: float):
        self.road   = road
        self.lane   = lane
        self.speed  = speed
        self.x      = road.get_lane_cx(lane) - self.W // 2
        self.y      = float(-self.H - 20)
        self.color  = random.choice(_ENEMY_PALETTES)
        self.active = True

    def update(self, dt: float):
        self.y += self.speed * dt

    def get_rect(self) -> pygame.Rect:
        return pygame.Rect(self.x + 5, int(self.y) + 5, self.W - 10, self.H - 10)

    def draw(self, surface: pygame.Surface):
        _draw_car(surface, self.x, int(self.y), self.W, self.H,
                  self.color, windshield_top=False)


# ─────────────────────────────────────────────────────────────────────────────
_COIN_TYPES = [
    {"value": 1, "color": (190, 100,  40), "r": 10, "name": "bronze"},
    {"value": 3, "color": (190, 190, 200), "r": 12, "name": "silver"},
    {"value": 5, "color": (240, 200,   0), "r": 14, "name": "gold"},
]
_COIN_WEIGHTS = [0.60, 0.30, 0.10]


class Coin:
    def __init__(self, road: Road, lane: int, scroll_speed: float):
        self.road   = road
        self.lane   = lane
        t = random.choices(_COIN_TYPES, weights=_COIN_WEIGHTS)[0]
        self.value  = t["value"]
        self.color  = t["color"]
        self.r      = t["r"]
        self.cx     = float(road.get_lane_cx(lane))
        self.y      = float(-self.r * 2 - 10)
        self.speed  = scroll_speed
        self.active = True
        self._anim  = random.uniform(0, math.tau)

    def update(self, dt: float):
        self.y     += self.speed * dt
        self._anim += dt * 5.0

    def get_rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.cx) - self.r, int(self.y) - self.r,
                           self.r * 2, self.r * 2)

    def draw(self, surface: pygame.Surface):
        r = self.r + int(math.sin(self._anim) * 2)
        pygame.draw.circle(surface, self.color, (int(self.cx), int(self.y)), r)
        pygame.draw.circle(surface, WHITE,      (int(self.cx), int(self.y)), r, 2)
        fnt = pygame.font.SysFont(None, 16)
        lbl = fnt.render(str(self.value), True, BLACK)
        surface.blit(lbl, (int(self.cx) - lbl.get_width() // 2,
                            int(self.y)  - lbl.get_height() // 2))


# ─────────────────────────────────────────────────────────────────────────────
_OBS_DEFS = {
    # name -> (w, h, border_r, base_color, effect, eff_dur, label)
    "oil":        (68, 32, 22, ( 15,  15,  40), "oil",    3.0, "OIL"),
    "barrier":    (86, 20,  4, (220,  60,  60), "damage", 0.0, "!!"),
    "pothole":    (36, 28, 14, ( 28,  22,  16), "slow",   1.8, "HOLE"),
    "speedbump":  (88, 14,  3, (240, 195,  40), "slow",   1.6, "BUMP"),
    "nitrostrip": (88, 14,  3, (  0, 210, 115), "nitro",  3.0, "NITRO"),
}


class Obstacle:
    def __init__(self, road: Road, lane: int, kind: str, scroll_speed: float):
        self.road   = road
        self.lane   = lane
        self.kind   = kind
        w, h, br, col, eff, dur, lbl = _OBS_DEFS[kind]
        self.w, self.h    = w, h
        self.br           = br
        self.base_color   = col
        self.effect       = eff
        self.eff_dur      = dur
        self.label        = lbl
        cx = road.get_lane_cx(lane)
        self.x      = cx - w // 2
        self.y      = float(-h - 20)
        self.speed  = scroll_speed
        self.active = True

    def update(self, dt: float):
        self.y += self.speed * dt

    def get_rect(self) -> pygame.Rect:
        return pygame.Rect(self.x, int(self.y), self.w, self.h)

    def draw(self, surface: pygame.Surface):
        r = pygame.Rect(self.x, int(self.y), self.w, self.h)
        pygame.draw.rect(surface, self.base_color, r, border_radius=self.br)

        if self.kind == "barrier":
            # Red-white hazard stripes
            stripe_w = 14
            n = self.w // stripe_w + 1
            clip = surface.get_clip()
            surface.set_clip(r)
            for i in range(n):
                sc = (230, 230, 230) if i % 2 == 0 else (210, 40, 40)
                pygame.draw.rect(surface, sc,
                                 (self.x + i * stripe_w, int(self.y),
                                  stripe_w, self.h))
            surface.set_clip(clip)
            pygame.draw.rect(surface, (200, 40, 40), r, 2, border_radius=self.br)

        elif self.kind == "oil":
            pygame.draw.ellipse(surface, (40, 40, 90),
                                (self.x + 6, int(self.y) + 4,
                                 self.w - 12, self.h - 8))
            # Rainbow sheen dots
            for ix, iy, ic in [(10, 6, (180, 60, 180)),
                                (30, 10, (60, 180, 180)),
                                (50, 6, (180, 180, 60))]:
                pygame.draw.circle(surface, ic,
                                   (self.x + ix, int(self.y) + iy), 3)

        elif self.kind == "nitrostrip":
            # Arrow chevrons
            for i in range(3):
                ax = self.x + 12 + i * 26
                ay = int(self.y)
                pygame.draw.polygon(surface, WHITE, [
                    (ax,      ay + 3),
                    (ax + 10, ay + 7),
                    (ax,      ay + 11),
                ])

        # Label
        fnt = pygame.font.SysFont(None, 16)
        lbl = fnt.render(self.label, True, WHITE)
        cx  = self.x + self.w // 2 - lbl.get_width() // 2
        cy  = int(self.y) + self.h // 2 - lbl.get_height() // 2
        surface.blit(lbl, (cx, cy))


# ─────────────────────────────────────────────────────────────────────────────
_PU_DEFS = {
    "nitro":  {"color": (  0, 180, 255), "sym": "N", "label": "NITRO",  "dur": 4.0},
    "shield": {"color": (255, 200,   0), "sym": "S", "label": "SHIELD", "dur": 0.0},
    "repair": {"color": (  0, 200,  80), "sym": "R", "label": "REPAIR", "dur": 0.0},
}
_PU_TIMEOUT = 9.0
_PU_SIZE    = 28


class PowerUp:
    def __init__(self, road: Road, lane: int, kind: str, scroll_speed: float):
        self.road   = road
        self.lane   = lane
        self.kind   = kind
        d = _PU_DEFS[kind]
        self.color  = d["color"]
        self.sym    = d["sym"]
        self.label  = d["label"]
        self.pu_dur = d["dur"]
        self.cx     = float(road.get_lane_cx(lane))
        self.y      = float(-_PU_SIZE - 10)
        self.speed  = scroll_speed
        self.active = True
        self._life  = _PU_TIMEOUT
        self._anim  = 0.0

    def update(self, dt: float):
        self.y     += self.speed * dt
        self._life -= dt
        self._anim += dt * 3.5
        if self._life <= 0:
            self.active = False

    def get_rect(self) -> pygame.Rect:
        s = _PU_SIZE
        return pygame.Rect(int(self.cx) - s // 2, int(self.y) - s // 2, s, s)

    def draw(self, surface: pygame.Surface):
        if not self.active:
            return
        r   = _PU_SIZE // 2 + int(math.sin(self._anim) * 3)
        cx, cy = int(self.cx), int(self.y)
        # Glow ring
        pygame.draw.circle(surface, self.color, (cx, cy), r + 4)
        pygame.draw.circle(surface, WHITE,      (cx, cy), r + 4, 2)
        # Inner
        dark = tuple(max(0, c - 80) for c in self.color)
        pygame.draw.circle(surface, dark, (cx, cy), r)
        # Symbol
        fnt = pygame.font.SysFont(None, 22)
        sym = fnt.render(self.sym, True, WHITE)
        surface.blit(sym, (cx - sym.get_width() // 2,
                            cy - sym.get_height() // 2))
        # Countdown bar when nearly expiring
        if self._life < 4.0:
            bar_w = int(_PU_SIZE * max(0, self._life / 4.0))
            pygame.draw.rect(surface, ORANGE,
                             (cx - _PU_SIZE // 2, cy + r + 4, bar_w, 3))


# ─────────────────────────────────────────────────────────────────────────────
class RacerGame:
    BASE_ROAD_SPD  = 230.0
    BASE_ENEMY_SPD = 190.0
    LVL_DIST       = 500          # metres per difficulty level

    def __init__(self, sw: int, sh: int, settings: dict, player_name: str):
        self.sw, self.sh    = sw, sh
        self.settings       = settings
        self.player_name    = player_name

        self.road = Road(sw, sh)

        col_name = settings.get("car_color", "red")
        self.player = Player(self.road, CAR_COLORS.get(col_name, RED))
        self.player.set_y(int(sh * 0.76))

        diff = settings.get("difficulty", "normal")
        self._dmult = {"easy": 0.70, "normal": 1.00, "hard": 1.50}.get(diff, 1.0)

        self.road_spd  = self.BASE_ROAD_SPD  * self._dmult
        self.enemy_spd = self.BASE_ENEMY_SPD * self._dmult

        # Game state
        self.score        = 0
        self.distance     = 0.0
        self.coin_count   = 0
        self._coin_value  = 0       # weighted total

        self.enemies   : list[EnemyCar] = []
        self.coins     : list[Coin]     = []
        self.obstacles : list[Obstacle] = []
        self.powerups  : list[PowerUp]  = []
        self.particles : list[dict]     = []

        # Active power-up HUD state
        self.active_pu       = None    # "nitro" | "shield" | "repair" | None
        self.active_pu_timer = 0.0
        self.nitro_on        = False
        self.nitro_timer     = 0.0

        # Spawn timers
        self._t_enemy  = 0.0
        self._t_coin   = 0.0
        self._t_obs    = 0.0
        self._t_pu     = 0.0

        # Difficulty
        self.level      = 1
        self._next_lvl  = float(self.LVL_DIST)

        self.game_over  = False

        # Fonts
        self._f_big = pygame.font.SysFont(None, 40)
        self._f_med = pygame.font.SysFont(None, 28)
        self._f_sm  = pygame.font.SysFont(None, 20)

    # ── Spawn helpers ──────────────────────────────────────────────────────

    def _safe_lane(self, excluded: set = None) -> int:
        """Random lane that is not directly on the player."""
        pool = set(range(LANE_COUNT))
        if excluded:
            pool -= excluded
        # Prefer not to pick the player's current lane
        no_player = pool - {self.player.lane}
        if no_player:
            return random.choice(list(no_player))
        return random.choice(list(pool)) if pool else self.player.lane

    def _spawn_enemy(self):
        lane  = random.randint(0, LANE_COUNT - 1)
        speed = self.enemy_spd + random.uniform(-25, 50)
        self.enemies.append(EnemyCar(self.road, lane, speed))

    def _spawn_coins(self):
        lane  = random.randint(0, LANE_COUNT - 1)
        count = random.choices([1, 3, 5], weights=[0.60, 0.30, 0.10])[0]
        base_spd = self.road_spd * 0.80
        for i in range(count):
            c   = Coin(self.road, lane, base_spd)
            c.y -= i * 44
            self.coins.append(c)

    def _spawn_obstacle(self):
        if self.level < 3:
            kinds   = ["oil", "speedbump", "pothole", "nitrostrip"]
            weights = [0.25, 0.25, 0.20, 0.30]
        else:
            kinds   = ["oil", "barrier", "speedbump", "pothole", "nitrostrip"]
            weights = [0.25, 0.22, 0.20, 0.13, 0.20]
        kind = random.choices(kinds, weights=weights)[0]
        # Barriers never spawn on player's lane
        excluded = {self.player.lane} if kind == "barrier" else set()
        lane = self._safe_lane(excluded)
        spd  = self.road_spd * 0.65
        self.obstacles.append(Obstacle(self.road, lane, kind, spd))

    def _spawn_powerup(self):
        if len(self.powerups) >= 1:
            return
        lane = random.randint(0, LANE_COUNT - 1)
        kind = random.choice(["nitro", "shield", "repair"])
        self.powerups.append(PowerUp(self.road, lane, kind, self.road_spd * 0.75))

    def _burst(self, x, y, color, n=7):
        for _ in range(n):
            self.particles.append({
                "x": float(x), "y": float(y),
                "vx": random.uniform(-90, 90),
                "vy": random.uniform(-130, -20),
                "life": random.uniform(0.25, 0.70),
                "color": color,
                "size": random.randint(3, 7),
            })

    # ── Spawn intervals (scale with level & difficulty) ────────────────────

    def _intervals(self):
        lvl, d = self.level, self._dmult
        ei  = max(0.70, (2.6  - lvl * 0.14) / d)
        ci  = max(0.45, (1.4  - lvl * 0.04) / d)
        oi  = max(0.90, (3.2  - lvl * 0.18) / d)
        pi  = max(5.0,   9.0  / d)
        return ei, ci, oi, pi

    # ── Main update ────────────────────────────────────────────────────────

    def update(self, dt: float, events) -> str | None:
        if self.game_over:
            return "gameover"

        # ── Input ──
        for e in events:
            if e.type == pygame.KEYDOWN:
                if e.key in (pygame.K_LEFT,  pygame.K_a):
                    self.player.move_left()
                if e.key in (pygame.K_RIGHT, pygame.K_d):
                    self.player.move_right()

        # ── Effective speed ──
        eff_spd = self.road_spd
        if "slow"  in self.player.debuffs:
            eff_spd *= 0.48
        if self.nitro_on:
            eff_spd += 130

        # ── Road & player ──
        self.road.update(dt, eff_spd)
        self.player.update(dt)
        self.distance += eff_spd * dt / 10.0

        # ── Nitro timer ──
        if self.nitro_on:
            self.nitro_timer -= dt
            if self.nitro_timer <= 0:
                self.nitro_on = False
                if self.active_pu == "nitro":
                    self.active_pu = None

        if self.active_pu_timer > 0:
            self.active_pu_timer -= dt
            if self.active_pu_timer <= 0 and self.active_pu == "repair":
                self.active_pu = None

        # ── Difficulty level-up ──
        if self.distance >= self._next_lvl:
            self.level     += 1
            self._next_lvl += self.LVL_DIST + self.level * 80
            self.enemy_spd  = min(400, self.enemy_spd + 22 * self._dmult)
            self.road_spd   = min(480, self.road_spd  + 16 * self._dmult)

        # ── Spawn timers ──
        ei, ci, oi, pi = self._intervals()
        self._t_enemy += dt
        self._t_coin  += dt
        self._t_obs   += dt
        self._t_pu    += dt

        if self._t_enemy >= ei:
            self._t_enemy = 0.0
            self._spawn_enemy()
            if self.level >= 4 and random.random() < 0.30:
                self._spawn_enemy()

        if self._t_coin >= ci:
            self._t_coin = 0.0
            self._spawn_coins()

        if self._t_obs >= oi:
            self._t_obs = 0.0
            self._spawn_obstacle()

        if self._t_pu >= pi:
            self._t_pu = 0.0
            self._spawn_powerup()

        p_rect = self.player.get_rect()

        # ── Enemies ──
        for en in self.enemies:
            en.update(dt)
            if en.active and en.get_rect().colliderect(p_rect):
                if self.player.shields:
                    self.player.shields -= 1
                    self.active_pu = None
                    en.active = False
                    self._burst(int(self.player.x) + 18, self.player.y, CYAN, 10)
                else:
                    self.game_over = True
                    return "gameover"
        self.enemies = [e for e in self.enemies
                        if e.active and e.y < self.sh + 80]

        # ── Coins ──
        for c in self.coins:
            c.update(dt)
            if c.active and c.get_rect().colliderect(p_rect):
                self.coin_count  += 1
                self._coin_value += c.value
                self._burst(int(c.cx), int(c.y), c.color, 5)
                c.active = False
                # P11: increase enemy speed with every 5 coins collected
                if self.coin_count % 5 == 0:
                    self.enemy_spd = min(450, self.enemy_spd + 8 * self._dmult)
        self.coins = [c for c in self.coins
                      if c.active and c.y < self.sh + 30]

        # ── Obstacles ──
        for ob in self.obstacles:
            ob.update(dt)
            if ob.active and ob.get_rect().colliderect(p_rect):
                ob.active = False
                eff = ob.effect
                if eff == "damage":
                    if self.player.shields:
                        self.player.shields -= 1
                        self.active_pu = None
                        self._burst(int(self.player.x) + 18, self.player.y, CYAN, 10)
                    else:
                        self.game_over = True
                        return "gameover"
                elif eff == "oil":
                    self.player.debuffs["oil"]  = ob.eff_dur
                    self.player.debuffs["slow"] = ob.eff_dur
                    self._burst(int(self.player.x) + 18, self.player.y + 30, (40, 40, 90), 9)
                elif eff == "slow":
                    self.player.debuffs["slow"] = ob.eff_dur
                elif eff == "nitro":
                    self.nitro_on    = True
                    self.nitro_timer = ob.eff_dur
                    self.active_pu   = "nitro"
                    self.active_pu_timer = ob.eff_dur
                    self._burst(int(self.player.x) + 18, self.player.y, (0, 220, 130), 9)
        self.obstacles = [o for o in self.obstacles
                          if o.active and o.y < self.sh + 30]

        # ── Power-ups ──
        for pu in self.powerups:
            pu.update(dt)
            if pu.active and pu.get_rect().colliderect(p_rect):
                self._apply_pu(pu)
                self._burst(int(pu.cx), int(pu.y), pu.color, 10)
                pu.active = False
        self.powerups = [p for p in self.powerups
                         if p.active and p.y < self.sh + 30]

        # ── Particles ──
        self.particles = [
            {**p, "x": p["x"] + p["vx"]*dt, "y": p["y"] + p["vy"]*dt,
             "life": p["life"] - dt}
            for p in self.particles if p["life"] > 0
        ]

        # ── Score ──
        bonus = self.level * 40
        self.score = int(self._coin_value * 12 + self.distance + bonus)

        return None

    def _apply_pu(self, pu: PowerUp):
        # Only one active power-up at a time
        self.active_pu = pu.kind
        if pu.kind == "nitro":
            self.nitro_on        = True
            self.nitro_timer     = pu.pu_dur
            self.active_pu_timer = pu.pu_dur
        elif pu.kind == "shield":
            self.player.shields  = 1
            self.active_pu_timer = 0.0   # shield has no timer (lasts until hit)
        elif pu.kind == "repair":
            self.player.debuffs.clear()
            self.active_pu_timer = 0.8   # brief flash, then clear

    # ── Draw ──────────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface):
        surface.fill(GRASS_COLOR)
        self.road.draw(surface)

        # Particles (below objects)
        for p in self.particles:
            alpha_frac = max(0.0, p["life"] / 0.60)
            col = tuple(min(255, int(c * 0.6 + 100 * alpha_frac)) for c in p["color"])
            pygame.draw.circle(surface, col,
                               (int(p["x"]), int(p["y"])), p["size"])

        for ob in self.obstacles:
            ob.draw(surface)
        for c in self.coins:
            c.draw(surface)
        for pu in self.powerups:
            pu.draw(surface)
        for en in self.enemies:
            en.draw(surface)
        self.player.draw(surface)

        self._draw_hud(surface)

    def _draw_hud(self, surface: pygame.Surface):
        # Top bar
        hbar = pygame.Surface((self.sw, 64), pygame.SRCALPHA)
        hbar.fill((0, 0, 0, 170))
        surface.blit(hbar, (0, 0))

        # Score / distance / coins / level
        self._blit(surface, self._f_med,
                   f"Score: {self.score}", WHITE, (10, 8))
        self._blit(surface, self._f_med,
                   f"Dist: {int(self.distance)} m",
                   (180, 255, 180), (10, 36))
        self._blit(surface, self._f_med,
                   f"Coins: {self.coin_count}", YELLOW,
                   (self.sw // 2 - 60, 8))
        self._blit(surface, self._f_med,
                   f"Lv {self.level}", ORANGE,
                   (self.sw - 68, 8))
        self._blit(surface, self._f_sm,
                   f"Next lv: {int(self._next_lvl - self.distance)} m",
                   GRAY, (self.sw - 100, 34))

        # Status badges
        sy = 72
        for name, timer in self.player.debuffs.items():
            if name == "oil":
                self._badge(surface, f"OIL  {timer:.1f}s", ( 80,  80, 200), sy)
                sy += 26
            elif name == "slow" and "oil" not in self.player.debuffs:
                self._badge(surface, f"SLOW {timer:.1f}s", (220, 210,  60), sy)
                sy += 26

        if self.nitro_on:
            self._badge(surface, f"NITRO {self.nitro_timer:.1f}s", (0, 220, 130), sy)
            sy += 26

        if self.player.shields:
            self._badge(surface, "SHIELD", CYAN, sy)
            sy += 26

        if self.active_pu == "repair" and self.active_pu_timer > 0:
            self._badge(surface, "REPAIRED!", GREEN, sy)

        # Bottom hint
        hint = self._f_sm.render("← → / A D  to change lanes", True, (130, 130, 130))
        surface.blit(hint, (self.sw // 2 - hint.get_width() // 2, self.sh - 18))

    def _blit(self, surface, font, text, color, pos):
        surface.blit(font.render(text, True, color), pos)

    def _badge(self, surface, text, color, y):
        txt = self._f_sm.render(text, True, color)
        bg  = pygame.Rect(7, y - 2, txt.get_width() + 12, txt.get_height() + 4)
        pygame.draw.rect(surface, (0, 0, 0), bg, border_radius=5)
        pygame.draw.rect(surface, color, bg, 1, border_radius=5)
        surface.blit(txt, (13, y))
