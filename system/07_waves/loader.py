# -*- coding: utf-8 -*-
"""
system/07_waves/loader.py
===========================
Controla o tempo e as ondas de zumbi:
    - toca TIMER1.mp3 (1:15) como música de fundo;
    - quando TIMER1 acaba, troca para TIMER2.mp3 em loop e o jogo
      entra na "fase 2" (mais difícil, chance do zumbi diretor
      aparecer sozinho, com barra de vida);
    - a dificuldade (intervalo entre spawns, mix de zumbis) aumenta
      com o tempo em ambas as fases;
    - desenha o cronômetro: normal no timer1, piscando vermelho e
      tremendo no timer2.
"""
import math
import random
import pygame
import shared_helpers as sh

TIMER1_DURATION = 75.0  # 1:15


def setup(context):
    context["wave_phase"] = "timer1"
    context["wave_elapsed"] = 0.0
    context["spawn_timer"] = 2.5
    context["difficulty"] = 1.0
    context["_boss_active"] = False

    context["_sfx_boss"] = sh.load_sound("sfx_boss.wav")

    sh.play_music("TIMER1.mp3", volume=0.55, loops=0)


def _start_timer2(context):
    context["wave_phase"] = "timer2"
    context["wave_elapsed"] = 0.0
    sh.play_music("TIMER2.mp3", volume=0.55, loops=-1)


def update(context, dt):
    if context.get("game_over") or context.get("paused"):
        return

    context["wave_elapsed"] += dt

    if context["wave_phase"] == "timer1":
        context["difficulty"] = 1.0 + context["wave_elapsed"] / TIMER1_DURATION
        if context["wave_elapsed"] >= TIMER1_DURATION:
            _start_timer2(context)
    else:
        context["difficulty"] = 2.0 + context["wave_elapsed"] / 40.0

    context["spawn_timer"] -= dt
    if context["spawn_timer"] <= 0:
        _spawn_wave(context)
        base_interval = 2.3
        context["spawn_timer"] = max(0.45, base_interval / context["difficulty"])


def _spawn_wave(context):
    rows = context["board"]["rows"]
    row = random.randrange(rows)
    phase = context["wave_phase"]
    roll = random.random()

    # zumbi diretor: só no timer2, sozinho (sem outro spawn junto), raro
    if phase == "timer2" and not context["_boss_active"] and roll < 0.05:
        context["_boss_active"] = True
        context["spawn_enemy"]("diretor", row)
        sh.play_sfx(context.get("_sfx_boss"), 0.8)
        return

    if phase == "timer1":
        kind = "professor" if roll < 0.25 else "estudante"
    else:
        kind = "professor" if roll < 0.45 else "estudante"
    context["spawn_enemy"](kind, row)


def draw(context, surface):
    phase = context["wave_phase"]

    if phase == "timer1":
        remaining = max(0.0, TIMER1_DURATION - context["wave_elapsed"])
        minutes, seconds = divmod(int(remaining) + 1, 60)
        label = f"{minutes}:{seconds:02d}"
        color = sh.COL_TEXT
        shake = (0, 0)
    else:
        elapsed = context["wave_elapsed"]
        minutes, seconds = divmod(int(elapsed), 60)
        label = f"+{minutes}:{seconds:02d}"
        blink = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.012)
        color = (
            int(sh.lerp(200, 255, blink)),
            int(sh.lerp(40, 90, blink)),
            int(sh.lerp(40, 60, blink)),
        )
        shake = (random.uniform(-3, 3), random.uniform(-3, 3))

    font = sh.get_font(34, bold=True)
    surf = font.render(label, True, color)
    rect = surf.get_rect(topright=(context["width"] - 30 + shake[0], 26 + shake[1]))
    surface.blit(surf, rect)
