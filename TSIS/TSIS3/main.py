"""
main.py — Entry point for the TSIS3 Racer game.

Screen state machine:
  menu  →  username  →  game  →  gameover
    ↑          ↓                     ↓
    ←←←←←←←←←←←←←←←←←←←←←←←←←←←←←
  leaderboard ← (from menu)
  settings    ← (from menu)

Run:
    python main.py
Requirements:
    pip install pygame
"""

import sys
import pygame

from persistence import (
    load_settings, save_settings,
    load_leaderboard, add_score,
)
from racer import RacerGame
from ui import (
    MainMenu, SettingsScreen, GameOverScreen,
    LeaderboardScreen, UsernameEntry,
)

# ── Window ────────────────────────────────────────────────────────────────────
SCREEN_W = 480
SCREEN_H = 700
FPS      = 60
TITLE    = "Racer — TSIS3"


def main():
    pygame.init()
    pygame.display.set_caption(TITLE)
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    clock  = pygame.time.Clock()

    # ── Load persistent data ──
    settings  = load_settings()

    # ── Build screens once ──
    menu_scr      = MainMenu(SCREEN_W, SCREEN_H)
    settings_scr  = SettingsScreen(SCREEN_W, SCREEN_H, settings)
    lb_scr        = LeaderboardScreen(SCREEN_W, SCREEN_H)
    username_scr  = UsernameEntry(SCREEN_W, SCREEN_H)

    # Mutable state
    state         = "menu"
    player_name   = "Player"
    game          = None        # RacerGame instance
    gameover_scr  = None

    # ── Main loop ─────────────────────────────────────────────────────────────
    while True:
        dt = clock.tick(FPS) / 1000.0

        events = pygame.event.get()
        for e in events:
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        # ── Menu ──────────────────────────────────────────────────────────────
        if state == "menu":
            action = menu_scr.handle(events)
            menu_scr.draw(screen)
            if action == "play":
                username_scr.reset()
                state = "username"
            elif action == "leaderboard":
                lb_scr.set_data(load_leaderboard())
                state = "leaderboard"
            elif action == "settings":
                settings_scr.set_settings(settings)
                state = "settings"
            elif action == "quit":
                pygame.quit()
                sys.exit()

        # ── Username entry ─────────────────────────────────────────────────
        elif state == "username":
            action, name = username_scr.handle(events)
            username_scr.draw(screen)
            if action == "start":
                player_name = name or "Player"
                game  = RacerGame(SCREEN_W, SCREEN_H, settings, player_name)
                state = "game"
            elif action == "back":
                state = "menu"

        # ── Active race ────────────────────────────────────────────────────
        elif state == "game":
            result = game.update(dt, events)
            game.draw(screen)
            if result == "gameover":
                updated_lb = add_score(
                    name     = player_name,
                    score    = game.score,
                    distance = int(game.distance),
                    coins    = game.coin_count,
                )
                gameover_scr = GameOverScreen(
                    SCREEN_W, SCREEN_H,
                    game.score, int(game.distance),
                    game.coin_count, player_name,
                )
                state = "gameover"

        # ── Game over ──────────────────────────────────────────────────────
        elif state == "gameover":
            action = gameover_scr.handle(events)
            gameover_scr.draw(screen)
            if action == "retry":
                game  = RacerGame(SCREEN_W, SCREEN_H, settings, player_name)
                state = "game"
            elif action == "menu":
                state = "menu"

        # ── Leaderboard ────────────────────────────────────────────────────
        elif state == "leaderboard":
            action = lb_scr.handle(events)
            lb_scr.draw(screen)
            if action == "back":
                state = "menu"

        # ── Settings ──────────────────────────────────────────────────────
        elif state == "settings":
            action, new_settings = settings_scr.handle(events)
            settings_scr.draw(screen)
            if action == "back":
                settings = new_settings
                save_settings(settings)
                state = "menu"

        pygame.display.flip()


if __name__ == "__main__":
    main()
