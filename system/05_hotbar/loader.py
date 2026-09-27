# -*- coding: utf-8 -*-
"""
system/05_hotbar/loader.py
============================
Hotbar estilo PvZ: um slot por defesa/ataque disponível (mina,
barreira, ônibus, fosso, espinhos, LAISER, computador, canhão).

Igual ao mockup que você mandou: a borda do slot embaixo do mouse
fica BRANCA (hover). Clicar num slot seleciona o item (a borda
continua branca mesmo sem o mouse em cima, pra indicar "selecionado");
clicar de novo no mesmo slot, clicar com o botão direito, ou apertar
ESC cancela a seleção. Com um item selecionado, clicar numa célula
vazia do tabuleiro compra e coloca (se tiver moedas suficiente).
"""
import pygame
import shared_helpers as sh

SLOT_SIZE = 84
SLOT_GAP = 10
START_X = 30
START_Y = 16


def _stats(kind):
    return sh.DEFENSE_STATS.get(kind) or sh.ATTACK_STATS.get(kind)


def setup(context):
    slots = []
    x = START_X
    for kind in sh.HOTBAR_ITEMS:
        slots.append({"kind": kind, "rect": pygame.Rect(x, START_Y, SLOT_SIZE, SLOT_SIZE)})
        x += SLOT_SIZE + SLOT_GAP

    context["hotbar_slots"] = slots
    context["hotbar_end_x"] = x  # onde o 08_ultimate deve começar a desenhar o botão roxo
    context["selected_item"] = None

    context["_sfx_select"] = sh.load_sound("sfx_select.wav")
    context["_sfx_place"] = sh.load_sound("sfx_place.wav")


def handle_event(context, event):
    if context.get("game_over") or context.get("paused"):
        return

    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
        context["selected_item"] = None
        return

    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
        context["selected_item"] = None
        return

    if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
        return

    for slot in context["hotbar_slots"]:
        if slot["rect"].collidepoint(event.pos):
            if context.get("selected_item") == slot["kind"]:
                context["selected_item"] = None
            else:
                context["selected_item"] = slot["kind"]
                sh.play_sfx(context.get("_sfx_select"), 0.5)
            return

    selected = context.get("selected_item")
    if selected is not None:
        cell = context["board_point_to_cell"](event.pos)
        if cell is not None:
            _try_place(context, cell[0], cell[1], selected)


def _try_place(context, row, col, kind):
    grid = context["board"]["grid"]
    if grid[row][col] is not None:
        return False
    stats = _stats(kind)
    if stats is None or context.get("coins", 0) < stats["cost"]:
        return False

    context["coins"] -= stats["cost"]
    entry = {
        "row": row, "col": col, "kind": kind, "category": stats["category"],
        "hp": stats.get("hp", 0), "max_hp": stats.get("hp", 0), "cooldown": 0.0,
    }
    grid[row][col] = entry
    if stats["category"] == "defense":
        context["placed_defenses"].append(entry)
    else:
        context["placed_attacks"].append(entry)

    sh.play_sfx(context.get("_sfx_place"), 0.6)
    return True


def update(context, dt):
    pass


def draw(context, surface):
    mouse = pygame.mouse.get_pos()
    selected = context.get("selected_item")

    for slot in context["hotbar_slots"]:
        rect = slot["rect"]
        stats = _stats(slot["kind"])
        hovered = rect.collidepoint(mouse)
        is_selected = selected == slot["kind"]

        pygame.draw.rect(surface, (24, 30, 22), rect, border_radius=8)
        inner = rect.inflate(-10, -10)
        pygame.draw.rect(surface, stats["color"], inner, border_radius=6)

        # destaque BRANCO no hover/selecionado, igual ao mockup
        border_color = (255, 255, 255) if (hovered or is_selected) else (70, 78, 68)
        border_w = 4 if (hovered or is_selected) else 2
        pygame.draw.rect(surface, border_color, rect, width=border_w, border_radius=8)

        cost_col = sh.COL_GOLD if context.get("coins", 0) >= stats["cost"] else sh.COL_RED
        cost = sh.get_font(14, bold=True).render(str(stats["cost"]), True, cost_col)
        surface.blit(cost, cost.get_rect(bottomright=(rect.right - 4, rect.bottom - 4)))

        if context.get("coins", 0) < stats["cost"]:
            dim = pygame.Surface(rect.size, pygame.SRCALPHA)
            dim.fill((0, 0, 0, 110))
            surface.blit(dim, rect.topleft)

        label = sh.get_font(12, bold=True).render(stats["label"][:9], True, sh.COL_TEXT)
        surface.blit(label, label.get_rect(midtop=(rect.centerx, rect.bottom + 2)))

    # "fantasma" mostrando onde o item selecionado vai cair no tabuleiro
    if selected is not None:
        cell = context["board_point_to_cell"](mouse)
        if cell is not None:
            row, col = cell
            rect = context["board_cell_rect"](row, col)
            ok = context["board"]["grid"][row][col] is None
            ghost = pygame.Surface(rect.size, pygame.SRCALPHA)
            ghost.fill((255, 255, 255, 90) if ok else (200, 40, 40, 110))
            surface.blit(ghost, rect.topleft)
