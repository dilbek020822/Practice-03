import pygame

pygame.init()
screen = pygame.display.set_mode((800, 600))
clock = pygame.time.Clock()

# Цвета и настройки
RED = (255, 0, 0)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)

current_color = RED
mode = 'brush'  # Режимы: 'brush', 'rect', 'circle', 'eraser'
start_pos = None # Для запоминания, где начали рисовать фигуру
drawing = False

screen.fill(WHITE) # Белый холст

while True:
    pos = pygame.mouse.get_pos() # Текущая позиция мыши

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            exit()

        # Нажали клавишу — сменили цвет или инструмент
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r: current_color = RED
            if event.key == pygame.K_g: current_color = GREEN
            if event.key == pygame.K_b: current_color = BLUE
            if event.key == pygame.K_e: mode = 'eraser'
            if event.key == pygame.K_1: mode = 'brush'
            if event.key == pygame.key.K_2: mode = 'rect'
            if event.key == pygame.key.K_3: mode = 'circle'

        # Нажали мышку
        if event.type == pygame.MOUSEBUTTONDOWN:
            drawing = True
            start_pos = event.pos # Запоминаем точку старта для фигур

        # Отпустили мышку
        if event.type == pygame.MOUSEBUTTONUP:
            if drawing:
                # Рисуем фигуру один раз при отпускании
                if mode == 'rect':
                    width = pos[0] - start_pos[0]
                    height = pos[1] - start_pos[1]
                    pygame.draw.rect(screen, current_color, (start_pos[0], start_pos[1], width, height), 2)
                elif mode == 'circle':
                    radius = abs(pos[0] - start_pos[0]) # Радиус как расстояние по X
                    pygame.draw.circle(screen, current_color, start_pos, radius, 2)
            drawing = False

    # Логика рисования кистью и ластиком (пока кнопка зажата)
    if drawing:
        if mode == 'brush':
            pygame.draw.circle(screen, current_color, pos, 5)
        elif mode == 'eraser':
            pygame.draw.circle(screen, WHITE, pos, 20) # Ластик — это просто белый круг

    pygame.display.flip()
    clock.tick(60)