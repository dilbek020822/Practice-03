"""
tools.py  –  Drawing tool implementations for the Paint application.
Each tool class exposes:
    handle_event(event, canvas, color, size) -> None
    draw_preview(surface, color, size)       -> None  (optional live overlay)
"""

import pygame
import math
from collections import deque


# ──────────────────────────────────────────────────────────────────────────────
# PENCIL  (freehand)
# ──────────────────────────────────────────────────────────────────────────────
class PencilTool:
    def __init__(self):
        self._last = None

    def handle_event(self, event, canvas, color, size):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._last = event.pos
            pygame.draw.circle(canvas, color, event.pos, max(1, size // 2))

        elif event.type == pygame.MOUSEMOTION and event.buttons[0]:
            if self._last:
                pygame.draw.line(canvas, color, self._last, event.pos, size)
            self._last = event.pos

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._last = None

    def draw_preview(self, surface, color, size):
        pos = pygame.mouse.get_pos()
        r = max(1, size // 2)
        pygame.draw.circle(surface, color, pos, r, 1)


# ──────────────────────────────────────────────────────────────────────────────
# STRAIGHT LINE
# ──────────────────────────────────────────────────────────────────────────────
class LineTool:
    def __init__(self):
        self._start = None

    def handle_event(self, event, canvas, color, size):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._start = event.pos

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self._start:
                pygame.draw.line(canvas, color, self._start, event.pos, size)
                self._start = None

    def draw_preview(self, surface, color, size):
        if self._start:
            end = pygame.mouse.get_pos()
            pygame.draw.line(surface, color, self._start, end, size)


# ──────────────────────────────────────────────────────────────────────────────
# RECTANGLE
# ──────────────────────────────────────────────────────────────────────────────
class RectangleTool:
    def __init__(self):
        self._start = None

    def _make_rect(self, a, b):
        x = min(a[0], b[0])
        y = min(a[1], b[1])
        w = abs(a[0] - b[0])
        h = abs(a[1] - b[1])
        return pygame.Rect(x, y, w, h)

    def handle_event(self, event, canvas, color, size):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._start = event.pos
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self._start:
                pygame.draw.rect(canvas, color, self._make_rect(self._start, event.pos), size)
                self._start = None

    def draw_preview(self, surface, color, size):
        if self._start:
            rect = self._make_rect(self._start, pygame.mouse.get_pos())
            pygame.draw.rect(surface, color, rect, size)


# ──────────────────────────────────────────────────────────────────────────────
# SQUARE  (constrained rectangle)
# ──────────────────────────────────────────────────────────────────────────────
class SquareTool:
    def __init__(self):
        self._start = None

    def _make_rect(self, a, b):
        dx = b[0] - a[0]
        dy = b[1] - a[1]
        side = min(abs(dx), abs(dy))
        sx = a[0] + (side if dx >= 0 else -side)
        sy = a[1] + (side if dy >= 0 else -side)
        x = min(a[0], sx)
        y = min(a[1], sy)
        return pygame.Rect(x, y, side, side)

    def handle_event(self, event, canvas, color, size):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._start = event.pos
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self._start:
                pygame.draw.rect(canvas, color, self._make_rect(self._start, event.pos), size)
                self._start = None

    def draw_preview(self, surface, color, size):
        if self._start:
            rect = self._make_rect(self._start, pygame.mouse.get_pos())
            pygame.draw.rect(surface, color, rect, size)


# ──────────────────────────────────────────────────────────────────────────────
# CIRCLE
# ──────────────────────────────────────────────────────────────────────────────
class CircleTool:
    def __init__(self):
        self._start = None

    def _params(self, a, b):
        cx = (a[0] + b[0]) // 2
        cy = (a[1] + b[1]) // 2
        r = int(math.hypot(b[0] - a[0], b[1] - a[1]) / 2)
        return (cx, cy), r

    def handle_event(self, event, canvas, color, size):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._start = event.pos
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self._start:
                center, r = self._params(self._start, event.pos)
                if r > 0:
                    pygame.draw.circle(canvas, color, center, r, size)
                self._start = None

    def draw_preview(self, surface, color, size):
        if self._start:
            center, r = self._params(self._start, pygame.mouse.get_pos())
            if r > 0:
                pygame.draw.circle(surface, color, center, r, size)


# ──────────────────────────────────────────────────────────────────────────────
# RIGHT TRIANGLE
# ──────────────────────────────────────────────────────────────────────────────
class RightTriangleTool:
    def __init__(self):
        self._start = None

    def _points(self, a, b):
        return [a, (a[0], b[1]), b]

    def handle_event(self, event, canvas, color, size):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._start = event.pos
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self._start:
                pygame.draw.polygon(canvas, color, self._points(self._start, event.pos), size)
                self._start = None

    def draw_preview(self, surface, color, size):
        if self._start:
            pts = self._points(self._start, pygame.mouse.get_pos())
            pygame.draw.polygon(surface, color, pts, size)


# ──────────────────────────────────────────────────────────────────────────────
# EQUILATERAL TRIANGLE
# ──────────────────────────────────────────────────────────────────────────────
class EquilateralTriangleTool:
    def __init__(self):
        self._start = None

    def _points(self, a, b):
        dx = b[0] - a[0]
        dy = b[1] - a[1]
        side = math.hypot(dx, dy)
        h = side * math.sqrt(3) / 2
        mx = (a[0] + b[0]) / 2
        my = (a[1] + b[1]) / 2
        angle = math.atan2(dy, dx)
        px = mx - h * math.sin(angle)
        py = my + h * math.cos(angle)
        return [a, b, (int(px), int(py))]

    def handle_event(self, event, canvas, color, size):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._start = event.pos
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self._start:
                pygame.draw.polygon(canvas, color, self._points(self._start, event.pos), size)
                self._start = None

    def draw_preview(self, surface, color, size):
        if self._start:
            pts = self._points(self._start, pygame.mouse.get_pos())
            pygame.draw.polygon(surface, color, pts, size)


# ──────────────────────────────────────────────────────────────────────────────
# RHOMBUS
# ──────────────────────────────────────────────────────────────────────────────
class RhombusTool:
    def __init__(self):
        self._start = None

    def _points(self, a, b):
        cx = (a[0] + b[0]) // 2
        cy = (a[1] + b[1]) // 2
        hw = abs(b[0] - a[0]) // 2
        hh = abs(b[1] - a[1]) // 2
        return [(cx, cy - hh), (cx + hw, cy), (cx, cy + hh), (cx - hw, cy)]

    def handle_event(self, event, canvas, color, size):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._start = event.pos
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self._start:
                pygame.draw.polygon(canvas, color, self._points(self._start, event.pos), size)
                self._start = None

    def draw_preview(self, surface, color, size):
        if self._start:
            pts = self._points(self._start, pygame.mouse.get_pos())
            pygame.draw.polygon(surface, color, pts, size)


# ──────────────────────────────────────────────────────────────────────────────
# ERASER
# ──────────────────────────────────────────────────────────────────────────────
class EraserTool:
    def __init__(self):
        self._last = None
        self.bg_color = (255, 255, 255)

    def handle_event(self, event, canvas, color, size):
        erase_size = size * 3
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._last = event.pos
            pygame.draw.circle(canvas, self.bg_color, event.pos, erase_size)
        elif event.type == pygame.MOUSEMOTION and event.buttons[0]:
            if self._last:
                pygame.draw.line(canvas, self.bg_color, self._last, event.pos, erase_size * 2)
            pygame.draw.circle(canvas, self.bg_color, event.pos, erase_size)
            self._last = event.pos
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._last = None

    def draw_preview(self, surface, color, size):
        pos = pygame.mouse.get_pos()
        pygame.draw.circle(surface, (180, 180, 180), pos, size * 3, 1)


# ──────────────────────────────────────────────────────────────────────────────
# FLOOD FILL
# ──────────────────────────────────────────────────────────────────────────────
class FillTool:
    def handle_event(self, event, canvas, color, size):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._flood_fill(canvas, event.pos, color)

    def _flood_fill(self, canvas, pos, new_color):
        x, y = pos
        w, h = canvas.get_size()
        if not (0 <= x < w and 0 <= y < h):
            return
        target = canvas.get_at((x, y))[:3]
        nc = new_color[:3] if len(new_color) > 3 else new_color
        if target == nc:
            return

        # BFS iterative flood fill
        canvas.lock()
        queue = deque()
        queue.append((x, y))
        visited = set()
        visited.add((x, y))

        while queue:
            cx, cy = queue.popleft()
            if not (0 <= cx < w and 0 <= cy < h):
                continue
            if canvas.get_at((cx, cy))[:3] != target:
                continue
            canvas.set_at((cx, cy), nc)
            for nx, ny in ((cx+1, cy), (cx-1, cy), (cx, cy+1), (cx, cy-1)):
                if (nx, ny) not in visited and 0 <= nx < w and 0 <= ny < h:
                    visited.add((nx, ny))
                    queue.append((nx, ny))
        canvas.unlock()

    def draw_preview(self, surface, color, size):
        pos = pygame.mouse.get_pos()
        # paint-bucket cursor hint
        r = 12
        pygame.draw.circle(surface, color, pos, r, 2)
        pygame.draw.line(surface, color, (pos[0], pos[1]-r-4), (pos[0], pos[1]-r+4), 2)
        pygame.draw.line(surface, color, (pos[0]-r-4, pos[1]), (pos[0]-r+4, pos[1]), 2)


# ──────────────────────────────────────────────────────────────────────────────
# COLOR PICKER  (eye-dropper)
# ──────────────────────────────────────────────────────────────────────────────
class ColorPickerTool:
    """Returns picked color via .picked_color attribute after a click."""
    def __init__(self):
        self.picked_color = None

    def handle_event(self, event, canvas, color, size):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            x, y = event.pos
            w, h = canvas.get_size()
            if 0 <= x < w and 0 <= y < h:
                self.picked_color = canvas.get_at((x, y))[:3]

    def draw_preview(self, surface, color, size):
        pos = pygame.mouse.get_pos()
        pygame.draw.circle(surface, (0, 0, 0), pos, 8, 2)
        pygame.draw.circle(surface, color,    pos, 6)


# ──────────────────────────────────────────────────────────────────────────────
# TEXT TOOL
# ──────────────────────────────────────────────────────────────────────────────
class TextTool:
    def __init__(self):
        self._active = False
        self._pos = (0, 0)
        self._text = ""
        self._font = None
        self._blink = 0
        self._show_cursor = True

    def _get_font(self, size):
        font_size = {2: 16, 5: 22, 10: 32}.get(size, 22)
        if self._font is None or self._font.size("A")[1] != font_size:
            try:
                self._font = pygame.font.SysFont("consolas,dejavusansmono,monospace", font_size)
            except Exception:
                self._font = pygame.font.Font(None, font_size)
        return self._font

    def handle_event(self, event, canvas, color, size):
        font = self._get_font(size)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._active and self._text:
                self._commit(canvas, color, font)
            self._active = True
            self._pos = event.pos
            self._text = ""

        elif event.type == pygame.KEYDOWN and self._active:
            if event.key == pygame.K_RETURN:
                if self._text:
                    self._commit(canvas, color, font)
                self._active = False
                self._text = ""
            elif event.key == pygame.K_ESCAPE:
                self._active = False
                self._text = ""
            elif event.key == pygame.K_BACKSPACE:
                self._text = self._text[:-1]
            else:
                ch = event.unicode
                if ch and ch.isprintable():
                    self._text += ch

    def _commit(self, canvas, color, font):
        surf = font.render(self._text, True, color)
        canvas.blit(surf, self._pos)

    def draw_preview(self, surface, color, size):
        if not self._active:
            return
        font = self._get_font(size)
        # live text
        surf = font.render(self._text, True, color)
        surface.blit(surf, self._pos)
        # blinking cursor
        self._blink = (self._blink + 1) % 60
        if self._blink < 30:
            tw = surf.get_width()
            th = surf.get_height()
            cx = self._pos[0] + tw + 1
            cy = self._pos[1]
            pygame.draw.line(surface, color, (cx, cy), (cx, cy + th), 2)
