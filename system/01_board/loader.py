# -*- coding: utf-8 -*-
"""
system/01_board/loader.py
===========================
O tabuleiro do IF DEFENSE é representado como uma MATRIZ (lista de
listas) ROWS x COLS: context["board"]["grid"][row][col] guarda None
(célula vazia) ou um dict com a defesa/torre de ataque colocada ali
(esse dict é criado pelo 05_hotbar e lido/editado por 02_defenses,
03_attacks e 04_enemies).

Esse módulo roda primeiro (prefixo "01_") porque os outros módulos
dependem das funções auxiliares que ele registra em context:
    context["board_cell_rect"](row, col)   -> pygame.Rect da célula
    context["board_cell_center"](row, col) -> (x, y) do centro
    context["board_row_y"](row)             -> y central da linha
    context["board_point_to_cell"]((x, y))   -> (row, col) ou None
"""
import pygame
import shared_helpers as sh

ROWS = 5
COLS = 8

BOARD_X = 40
BOARD_Y = 130
BOARD_W = 1200
BOARD_H = 480

COL_CELL_A = (26, 46, 28)
COL_CELL_B = (20, 38, 22)
COL_GRID_LINE = (10, 18, 12)
COL_BASE_LINE = (150, 30, 30)


def setup(context):
    cell_w = BOARD_W / COLS
    cell_h = BOARD_H / ROWS

    # ---- A MATRIZ DO TABULEIRO ----
    grid = [[None for _ in range(COLS)] for _ in range(ROWS)]

    context["board"] = {
        "rows": ROWS, "cols": COLS,
        "x": BOARD_X, "y": BOARD_Y, "w": BOARD_W, "h": BOARD_H,
        "cell_w": cell_w, "cell_h": cell_h,
        "grid": grid,
    }

    def cell_rect(row, col):
        return pygame.Rect(
            int(BOARD_X + col * cell_w), int(BOARD_Y + row * cell_h),
            int(cell_w) + 1, int(cell_h) + 1,
        )

    def cell_center(row, col):
        return cell_rect(row, col).center

    def row_y(row):
        return int(BOARD_Y + row * cell_h + cell_h / 2)

    def point_to_cell(pos):
        x, y = pos
        if not (BOARD_X <= x < BOARD_X + BOARD_W and BOARD_Y <= y < BOARD_Y + BOARD_H):
            return None
        col = sh.clamp(int((x - BOARD_X) // cell_w), 0, COLS - 1)
        row = sh.clamp(int((y - BOARD_Y) // cell_h), 0, ROWS - 1)
        return row, col

    context["board_cell_rect"] = cell_rect
    context["board_cell_center"] = cell_center
    context["board_row_y"] = row_y
    context["board_point_to_cell"] = point_to_cell

    context.setdefault("base_hp", 100)
    context.setdefault("base_hp_max", 100)


def update(context, dt):
    pass


def draw(context, surface):
    board = context["board"]
    for row in range(board["rows"]):
        for col in range(board["cols"]):
            rect = context["board_cell_rect"](row, col)
            color = COL_CELL_A if (row + col) % 2 == 0 else COL_CELL_B
            pygame.draw.rect(surface, color, rect)
            pygame.draw.rect(surface, COL_GRID_LINE, rect, width=1)

    outer = pygame.Rect(board["x"], board["y"], board["w"], board["h"])
    pygame.draw.rect(surface, (60, 90, 60), outer, width=3)

    # linha vermelha marcando a base (lado esquerdo) - se um zumbi
    # chega aqui, tira vida da base
    pygame.draw.rect(surface, COL_BASE_LINE, (board["x"] - 10, board["y"], 8, board["h"]))
