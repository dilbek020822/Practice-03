# main.py — Snake Game entry point

import sys
import pygame
from game import GameApp


def main() -> None:
    pygame.init()
    pygame.font.init()

    app = GameApp()
    app.run()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
