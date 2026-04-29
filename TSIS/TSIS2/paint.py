"""
paint.py  –  Extended Paint Application  (TSIS 2)
Requires: Python 3.8+, Pygame 2.x   →   pip install pygame

Controls
────────
Mouse         : use active tool on the canvas
1 / 2 / 3    : brush size  small / medium / large
Ctrl+S        : save canvas as timestamped PNG
Escape        : cancel text input (when Text tool active)

Tools (click toolbar buttons)
─────────────────────────────
Pencil        freehand drawing
Line          straight line with live preview
Rectangle     outline rectangle
Square        constrained square
Circle        outline circle
Rt.Tri        right triangle
Eq.Tri        equilateral triangle
Rhombus       four-sided diamond
Eraser        erase to white
Fill          flood-fill closed region
Picker        eye-dropper / pick color from canvas
Text          click canvas → type → Enter to commit
"""

import sys
import pygame
from datetime import datetime

from tools import (
    PencilTool, LineTool, RectangleTool, SquareTool,
    CircleTool, RightTriangleTool, EquilateralTriangleTool,
    RhombusTool, EraserTool, FillTool, ColorPickerTool, TextTool,
)

# ── Constants ────────────────────────────────────────────────────────────────
WIN_W, WIN_H     = 1100, 720
TOOLBAR_W        = 160
CANVAS_W         = WIN_W - TOOLBAR_W
CANVAS_H         = WIN_H
CANVAS_OFFSET    = (TOOLBAR_W, 0)

BG_TOOLBAR       = (30,  30,  35)
BG_CANVAS        = (255, 255, 255)
ACCENT           = (90, 160, 255)
TEXT_COLOR       = (220, 220, 220)
SECTION_COLOR    = (55,  55,  65)
HOVER_COLOR      = (60,  60,  75)
ACTIVE_COLOR     = (70, 130, 220)

BRUSH_SIZES      = [2, 5, 10]
SIZE_LABELS      = ["S (1)", "M (2)", "L (3)"]

PALETTE = [
    (0,   0,   0),   (255, 255, 255), (200,  50,  50),
    (50,  160,  50), (50,  80,  220), (230, 180,  30),
    (200,  80, 200), (30,  200, 200), (255, 140,   0),
    (100,  50,  20), (150, 150, 150), (80,   80,  80),
]

# ── Helper ───────────────────────────────────────────────────────────────────
def draw_text(surf, text, pos, font, color=TEXT_COLOR, center=False):
    s = font.render(text, True, color)
    r = s.get_rect()
    if center:
        r.center = pos
    else:
        r.topleft = pos
    surf.blit(s, r)

def save_canvas(canvas):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = f"canvas_{ts}.png"
    pygame.image.save(canvas, fname)
    return fname

# ── Button ───────────────────────────────────────────────────────────────────
class Button:
    def __init__(self, rect, label, tag):
        self.rect  = pygame.Rect(rect)
        self.label = label
        self.tag   = tag
        self.hovered = False

    def draw(self, surf, font, active=False):
        color = ACTIVE_COLOR if active else (HOVER_COLOR if self.hovered else SECTION_COLOR)
        pygame.draw.rect(surf, color, self.rect, border_radius=6)
        pygame.draw.rect(surf, ACCENT if active else (80, 80, 100), self.rect, 1, border_radius=6)
        draw_text(surf, self.label, self.rect.center, font, center=True)

    def update(self, mouse_pos):
        self.hovered = self.rect.collidepoint(mouse_pos)

    def clicked(self, event):
        return (event.type == pygame.MOUSEBUTTONDOWN and
                event.button == 1 and
                self.rect.collidepoint(event.pos))

# ── Main application ─────────────────────────────────────────────────────────
class PaintApp:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Paint — TSIS 2")
        self.screen  = pygame.display.set_mode((WIN_W, WIN_H))
        self.canvas  = pygame.Surface((CANVAS_W, CANVAS_H))
        self.canvas.fill(BG_CANVAS)

        self.overlay = pygame.Surface((CANVAS_W, CANVAS_H), pygame.SRCALPHA)

        self.clock   = pygame.time.Clock()
        self.font_sm = pygame.font.SysFont("segoeui,dejavusans,sans-serif", 13)
        self.font_md = pygame.font.SysFont("segoeui,dejavusans,sans-serif", 15, bold=True)
        self.font_hd = pygame.font.SysFont("segoeui,dejavusans,sans-serif", 17, bold=True)

        # State
        self.active_color  = (0, 0, 0)
        self.brush_size_idx = 0           # index into BRUSH_SIZES
        self.active_tool   = "pencil"
        self.status_msg    = "Welcome! Choose a tool and draw."
        self.status_timer  = 0

        # Tool instances
        self.tools = {
            "pencil":  PencilTool(),
            "line":    LineTool(),
            "rect":    RectangleTool(),
            "square":  SquareTool(),
            "circle":  CircleTool(),
            "rtri":    RightTriangleTool(),
            "etri":    EquilateralTriangleTool(),
            "rhombus": RhombusTool(),
            "eraser":  EraserTool(),
            "fill":    FillTool(),
            "picker":  ColorPickerTool(),
            "text":    TextTool(),
        }

        self._build_ui()

    # ── UI layout ────────────────────────────────────────────────────────────
    def _build_ui(self):
        self.tool_buttons = []
        tool_defs = [
            ("pencil",  "✏ Pencil"),
            ("line",    "╱ Line"),
            ("rect",    "▭ Rect"),
            ("square",  "□ Square"),
            ("circle",  "○ Circle"),
            ("rtri",    "◺ Rt.Tri"),
            ("etri",    "△ Eq.Tri"),
            ("rhombus", "◇ Rhombus"),
            ("eraser",  "◻ Eraser"),
            ("fill",    "⬛ Fill"),
            ("picker",  "⊕ Picker"),
            ("text",    "T Text"),
        ]
        x, y = 8, 50
        bw, bh = TOOLBAR_W - 16, 34
        for tag, label in tool_defs:
            self.tool_buttons.append(Button((x, y, bw, bh), label, tag))
            y += bh + 4

        # Brush size buttons
        self.size_buttons = []
        y += 12
        bw3 = (TOOLBAR_W - 20) // 3
        for i, lbl in enumerate(SIZE_LABELS):
            bx = 8 + i * (bw3 + 2)
            self.size_buttons.append(Button((bx, y, bw3, 28), lbl, i))
        self.size_btn_y = y

        # Color palette buttons (grid 3 cols)
        self.palette_rects = []
        py = y + 50
        cols = 3
        pw = 28
        gap = 4
        for i, c in enumerate(PALETTE):
            col = i % cols
            row = i // cols
            px  = 10 + col * (pw + gap)
            pr  = pygame.Rect(px, py + row * (pw + gap), pw, pw)
            self.palette_rects.append((pr, c))

        # Custom color area (shows current color)
        self.custom_color_rect = pygame.Rect(10, py + (len(PALETTE)//cols) * (pw+gap) + 10, TOOLBAR_W-20, 32)

    # ── Event routing ─────────────────────────────────────────────────────────
    def run(self):
        while True:
            dt = self.clock.tick(60)
            mouse = pygame.mouse.get_pos()
            on_canvas = mouse[0] >= TOOLBAR_W

            for btn in self.tool_buttons + self.size_buttons:
                btn.update(mouse)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                self._handle_keyboard(event)
                self._handle_toolbar(event)

                # Route mouse events to active tool (canvas area only)
                if on_canvas or event.type in (pygame.KEYDOWN, pygame.KEYUP):
                    translated = self._translate_event(event)
                    if translated:
                        tool = self.tools[self.active_tool]
                        tool.handle_event(translated, self.canvas,
                                          self.active_color, self._brush())
                        # Color picker callback
                        if self.active_tool == "picker":
                            picked = self.tools["picker"].picked_color
                            if picked:
                                self.active_color = picked
                                self.tools["picker"].picked_color = None
                                self._status(f"Color picked: {picked}")

            self._draw(mouse)
            pygame.display.flip()

            if self.status_timer > 0:
                self.status_timer -= dt

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _brush(self):
        return BRUSH_SIZES[self.brush_size_idx]

    def _status(self, msg, ms=2500):
        self.status_msg   = msg
        self.status_timer = ms

    def _translate_event(self, event):
        """Shift mouse coordinates so (0,0) is canvas origin."""
        ox, oy = CANVAS_OFFSET
        if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            if event.pos[0] < TOOLBAR_W:
                return None
            new_pos = (event.pos[0] - ox, event.pos[1] - oy)
            return pygame.event.Event(event.type, {**event.__dict__, "pos": new_pos})
        elif event.type == pygame.MOUSEMOTION:
            new_pos  = (event.pos[0] - ox, event.pos[1] - oy)
            new_rel  = event.rel
            new_buttons = event.buttons
            return pygame.event.Event(event.type, pos=new_pos, rel=new_rel, buttons=new_buttons)
        elif event.type == pygame.KEYDOWN:
            return event
        return None

    def _handle_keyboard(self, event):
        if event.type != pygame.KEYDOWN:
            return
        mods = pygame.key.get_mods()

        # Ctrl+S  →  save
        if event.key == pygame.K_s and (mods & pygame.KMOD_CTRL):
            fname = save_canvas(self.canvas)
            self._status(f"Saved: {fname}", 3500)

        # Brush size  1/2/3
        elif event.key == pygame.K_1:
            self.brush_size_idx = 0
            self._status("Brush: Small (2 px)")
        elif event.key == pygame.K_2:
            self.brush_size_idx = 1
            self._status("Brush: Medium (5 px)")
        elif event.key == pygame.K_3:
            self.brush_size_idx = 2
            self._status("Brush: Large (10 px)")

    def _handle_toolbar(self, event):
        # Tool buttons
        for btn in self.tool_buttons:
            if btn.clicked(event):
                self.active_tool = btn.tag
                self._status(f"Tool: {btn.label.strip()}")
                return

        # Size buttons
        for i, btn in enumerate(self.size_buttons):
            if btn.clicked(event):
                self.brush_size_idx = i
                self._status(f"Brush: {['Small','Medium','Large'][i]} ({BRUSH_SIZES[i]} px)")
                return

        # Palette swatches
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for rect, c in self.palette_rects:
                if rect.collidepoint(event.pos):
                    self.active_color = c
                    self._status(f"Color: {c}")
                    return

    # ── Rendering ─────────────────────────────────────────────────────────────
    def _draw(self, mouse):
        self.screen.fill((20, 20, 25))

        # Canvas
        self.screen.blit(self.canvas, CANVAS_OFFSET)

        # Tool preview overlay (translucent)
        self.overlay.fill((0, 0, 0, 0))
        mouse_on_canvas = mouse[0] >= TOOLBAR_W
        if mouse_on_canvas:
            shifted_mouse = (mouse[0] - TOOLBAR_W, mouse[1])
            old_pos = pygame.mouse.get_pos()
            # draw preview into overlay
            tmp_surf = self.overlay
            tool = self.tools[self.active_tool]
            if hasattr(tool, "draw_preview"):
                # temporarily move logical cursor
                save = pygame.mouse.get_pos()
                # We pass overlay directly; tool reads pygame.mouse.get_pos()
                # so we need to offset consistently — draw on overlay using shifted
                _draw_preview_offset(tool, self.overlay, self.active_color,
                                     self._brush(), TOOLBAR_W)
        self.screen.blit(self.overlay, CANVAS_OFFSET)

        # Thin canvas border
        pygame.draw.rect(self.screen, (60, 60, 80),
                         (TOOLBAR_W-1, 0, CANVAS_W+1, CANVAS_H), 1)

        # ── Toolbar background ──
        pygame.draw.rect(self.screen, BG_TOOLBAR, (0, 0, TOOLBAR_W, WIN_H))

        # Header
        pygame.draw.rect(self.screen, (40, 40, 50), (0, 0, TOOLBAR_W, 40))
        draw_text(self.screen, "🎨 PAINT", (TOOLBAR_W//2, 20), self.font_hd, ACCENT, center=True)

        # Tool buttons
        draw_text(self.screen, "TOOLS", (8, 34), self.font_sm, (120, 120, 140))
        for btn in self.tool_buttons:
            btn.draw(self.screen, self.font_sm, active=(btn.tag == self.active_tool))

        # Brush size section
        y_s = self.size_btn_y
        draw_text(self.screen, "BRUSH SIZE", (8, y_s - 16), self.font_sm, (120, 120, 140))
        for i, btn in enumerate(self.size_buttons):
            btn.draw(self.screen, self.font_sm, active=(i == self.brush_size_idx))

        # Color palette
        pal_label_y = self.size_btn_y + 38
        draw_text(self.screen, "PALETTE", (8, pal_label_y), self.font_sm, (120, 120, 140))
        for rect, c in self.palette_rects:
            pygame.draw.rect(self.screen, c, rect, border_radius=4)
            if c == self.active_color:
                pygame.draw.rect(self.screen, (255, 255, 255), rect, 2, border_radius=4)
            else:
                pygame.draw.rect(self.screen, (80, 80, 90), rect, 1, border_radius=4)

        # Current color preview
        pygame.draw.rect(self.screen, self.active_color, self.custom_color_rect, border_radius=6)
        pygame.draw.rect(self.screen, (180, 180, 200), self.custom_color_rect, 1, border_radius=6)
        lum = 0.299*self.active_color[0] + 0.587*self.active_color[1] + 0.114*self.active_color[2]
        lbl_c = (0,0,0) if lum > 128 else (255,255,255)
        draw_text(self.screen, "Active Color", self.custom_color_rect.center,
                  self.font_sm, lbl_c, center=True)

        # Status bar at bottom of toolbar
        status_y = WIN_H - 44
        pygame.draw.line(self.screen, (60, 60, 80), (0, status_y), (TOOLBAR_W, status_y), 1)
        msg = self.status_msg if self.status_timer > 0 else f"{self.active_tool.title()}  |  {self._brush()}px"
        # Word-wrap for narrow toolbar
        words = msg.split()
        line, lines = "", []
        for w in words:
            test = (line + " " + w).strip()
            if self.font_sm.size(test)[0] < TOOLBAR_W - 10:
                line = test
            else:
                lines.append(line)
                line = w
        lines.append(line)
        for i, l in enumerate(lines[-2:]):
            draw_text(self.screen, l, (5, status_y + 6 + i*16), self.font_sm, (160, 200, 255))

        # Ctrl+S hint
        draw_text(self.screen, "Ctrl+S = Save PNG", (5, WIN_H - 16), self.font_sm, (80, 80, 100))


def _draw_preview_offset(tool, overlay, color, size, x_offset):
    """
    Call tool.draw_preview() but shift pygame.mouse.get_pos() by x_offset
    by drawing to the overlay surface.  The tool reads pygame.mouse.get_pos()
    which includes the toolbar; we subtract x_offset before drawing.
    """
    mx, my = pygame.mouse.get_pos()
    # Create a temporary surface that the tool draws on, faking a shifted mouse
    # by passing a monkey-patched approach — simplest: just offset the coords
    # manually via a thin wrapper.
    _orig_get_pos = pygame.mouse.get_pos
    try:
        pygame.mouse.get_pos = lambda: (mx - x_offset, my)
        tool.draw_preview(overlay, color, size)
    finally:
        pygame.mouse.get_pos = _orig_get_pos


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = PaintApp()
    app.run()
