# -*- coding: utf-8 -*-
"""
system/09_gamestate/loader.py
===============================
Detecta o fim de jogo (base_hp chega a 0, marcado pelo 04_enemies em
context["game_over"]). Quando isso acontece: pausa TUDO (os outros
módulos checam context["paused"]/context["game_over"] e param de
atualizar), para a música do timer e toca GAMEOVER.mp3, e mostra a
tela de Game Over com os botões REINICIAR / MENU.

REINICIAR reseta a run inteira (general_loader.py chama run_game()
de novo do zero quando vê context["restart_requested"]).
MENU sinaliza context["return_to_menu_requested"] e encerra o loop -
quem decide o que fazer com isso é quem chamou run_game() (main.py /
title_screen.py).
"""
import os
import pygame
import shared_helpers as sh


def setup(context):
    context.setdefault("game_over", False)
    context["paused"] = False
    context["_gameover_music_played"] = False
    context["restart_requested"] = False
    context["return_to_menu_requested"] = False

    context["_sfx_click"] = sh.load_sound("sfx_click.wav")

    btn_w, btn_h = 260, 60
    cx, cy = context["width"] // 2, context["height"] // 2
    context["_go_restart_rect"] = pygame.Rect(cx - btn_w - 15, cy + 50, btn_w, btn_h)
    context["_go_menu_rect"] = pygame.Rect(cx + 15, cy + 50, btn_w, btn_h)


def handle_event(context, event):
    if not context.get("game_over"):
        return
    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        if context["_go_restart_rect"].collidepoint(event.pos):
            sh.play_sfx(context.get("_sfx_click"), 0.6)
            context["restart_requested"] = True
            context["running"] = False
        elif context["_go_menu_rect"].collidepoint(event.pos):
            sh.play_sfx(context.get("_sfx_click"), 0.6)
            context["return_to_menu_requested"] = True
            context["running"] = False


def update(context, dt):
    if context.get("game_over") and not context.get("_gameover_music_played"):
        context["paused"] = True
        if sh.MIXER_OK:
            pygame.mixer.music.stop()
        sh.play_music("GAMEOVER.mp3", volume=0.7, loops=0)
        context["_gameover_music_played"] = True


def draw(context, surface):
    if not context.get("game_over"):
        return

    overlay = pygame.Surface((context["width"], context["height"]), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 190))
    surface.blit(overlay, (0, 0))

    title = sh.get_font(64, bold=True).render("GAME OVER", True, sh.COL_RED)
    surface.blit(title, title.get_rect(center=(context["width"] // 2, context["height"] // 2 - 70)))

    mouse = pygame.mouse.get_pos()
    for rect, text in (
        (context["_go_restart_rect"], "REINICIAR"),
        (context["_go_menu_rect"], "MENU"),
    ):
        hovered = rect.collidepoint(mouse)
        pygame.draw.rect(surface, (60, 90, 60) if hovered else (40, 50, 40), rect, border_radius=10)
        pygame.draw.rect(surface, sh.COL_GOLD if hovered else sh.COL_TEXT_DIM, rect, width=2, border_radius=10)
        label = sh.get_font(24, bold=True).render(text, True, sh.COL_TEXT)
        surface.blit(label, label.get_rect(center=rect.center))
