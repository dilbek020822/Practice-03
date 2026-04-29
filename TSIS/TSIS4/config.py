# config.py — Snake Game Configuration

# Window & Grid
WINDOW_WIDTH  = 800
WINDOW_HEIGHT = 620
HUD_HEIGHT    = 60
GRID_SIZE     = 20
GRID_WIDTH    = WINDOW_WIDTH // GRID_SIZE               # 40
GRID_HEIGHT   = (WINDOW_HEIGHT - HUD_HEIGHT) // GRID_SIZE  # 28

# Speed
FPS             = 60           # display FPS (constant)
FPS_BASE        = 8            # snake moves per second at level 1
SPEED_INCREMENT = 1            # extra moves/s per level

# Gameplay
FOOD_PER_LEVEL         = 5
FOOD_DISAPPEAR_MS      = 7_000  # timed foods vanish after 7 s
POWERUP_FIELD_MS       = 8_000  # power-up on field expires after 8 s
POWERUP_EFFECT_MS      = 5_000  # active effect lasts 5 s
OBSTACLE_BASE_COUNT    = 4      # blocks placed at level 3
OBSTACLE_PER_LEVEL     = 2      # extra blocks each level above 3
OBSTACLE_MAX           = 18

# Colour palette
BLACK       = (  0,   0,   0)
WHITE       = (255, 255, 255)
GREEN       = (  0, 200,   0)
DARK_GREEN  = (  0, 120,   0)
RED         = (220,  40,  40)
DARK_RED    = (140,   0,   0)
BLUE        = (  0, 100, 255)
YELLOW      = (255, 220,   0)
ORANGE      = (255, 140,   0)
PURPLE      = (170,   0, 220)
CYAN        = (  0, 210, 210)
GRAY        = (110, 110, 110)
DARK_GRAY   = ( 45,  45,  60)
LIGHT_GRAY  = (180, 180, 190)
BG_COLOR    = ( 12,  12,  25)
WALL_COLOR  = ( 60,  60, 100)
OBSTACLE_COLOR = ( 90,  55,  25)
HUD_BG      = ( 18,  18,  35)

# Default DB config (user edits as needed)
DB_CONFIG = {
    "dbname"  : "snake_game",
    "user"    : "postgres",
    "password": "abdisabirov",
    "host"    : "localhost",
    "port"    : 5432,
}
