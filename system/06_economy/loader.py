# -*- coding: utf-8 -*-
"""
system/06_economy/loader.py
=============================
Moedas do jogador (ganhas ao derrotar zumbis, gastas na hotbar pra
comprar defesa/ataque) e a barra de vida da base. O contador de
moedas fica embaixo, como você pediu.
"""
import pygame
import shared_helpers as sh

STARTING_COINS = 150


def setup(context):
    context.setdefault("coins", STARTING_COINS)


def update(context, dt):
    pass


def draw(context, surface):
    coins = context.get("coins", 0)
    font = sh.get_font(28, bold=True)
    text = font.render(f"Moedas: {coins}", True, sh.COL_GOLD)
    surface.blit(text, (30, context["height"] - 46))

    hp = context.get("base_hp", 100)
    hp_max = context.get("base_hp_max", 100)
    bar_rect = pygame.Rect(context["width"] // 2 - 160, context["height"] - 40, 320, 20)
    sh.draw_bar(surface, bar_rect, hp / hp_max if hp_max else 0, sh.COL_GREEN)

    label = sh.get_font(16, bold=True).render("BASE", True, sh.COL_TEXT)
    surface.blit(label, label.get_rect(midright=(bar_rect.x - 12, bar_rect.centery)))
