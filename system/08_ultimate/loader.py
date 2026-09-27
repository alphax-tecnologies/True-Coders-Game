# -*- coding: utf-8 -*-
"""
system/08_ultimate/loader.py
==============================
O botão roxo ao lado da hotbar. Carrega 6% a cada zumbi derrotado
(isso é somado direto em context["ultimate_charge"] pelo módulo
04_enemies). Quando chega em 100% e o jogador clica, a tela fica
momentaneamente roxa (context["ultimate_active_fx"]) e os zumbis
ficam congelados por 5 segundos (context["ultimate_freeze"] - lido
pelo 04_enemies pra travar o movimento/ataque deles).
"""
import math
import pygame
import shared_helpers as sh

BUTTON_SIZE = 90
FREEZE_DURATION = 5.0
FX_DURATION = 0.6


def setup(context):
    context.setdefault("ultimate_charge", 0)
    context["ultimate_freeze"] = 0.0
    context["ultimate_active_fx"] = 0.0

    x = context.get("hotbar_end_x", context["width"] - 140) + 16
    context["ultimate_button_rect"] = pygame.Rect(x, 16, BUTTON_SIZE, BUTTON_SIZE)

    context["_sfx_ultimate"] = sh.load_sound("sfx_ultimate.wav")


def handle_event(context, event):
    if context.get("game_over") or context.get("paused"):
        return
    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        rect = context["ultimate_button_rect"]
        if rect.collidepoint(event.pos) and context.get("ultimate_charge", 0) >= 100:
            context["ultimate_charge"] = 0
            context["ultimate_freeze"] = FREEZE_DURATION
            context["ultimate_active_fx"] = FX_DURATION
            sh.play_sfx(context.get("_sfx_ultimate"), 0.8)


def update(context, dt):
    if context.get("ultimate_freeze", 0) > 0:
        context["ultimate_freeze"] = max(0.0, context["ultimate_freeze"] - dt)
    if context.get("ultimate_active_fx", 0) > 0:
        context["ultimate_active_fx"] = max(0.0, context["ultimate_active_fx"] - dt)


def draw(context, surface):
    rect = context["ultimate_button_rect"]
    charge = context.get("ultimate_charge", 0)
    ready = charge >= 100

    if ready:
        pulse = 0.6 + 0.4 * math.sin(pygame.time.get_ticks() * 0.01)
        glow = pygame.Surface((rect.width + 34, rect.height + 34), pygame.SRCALPHA)
        pygame.draw.ellipse(glow, (*sh.COL_PURPLE, int(140 * pulse)), glow.get_rect())
        surface.blit(glow, glow.get_rect(center=rect.center).topleft)

    fill_color = (
        int(sh.lerp(70, 170, charge / 100)),
        int(sh.lerp(30, 60, charge / 100)),
        int(sh.lerp(90, 230, charge / 100)),
    )
    pygame.draw.rect(surface, (24, 20, 30), rect, border_radius=14)
    inner = rect.inflate(-10, -10)
    pygame.draw.rect(surface, fill_color, inner, border_radius=10)
    pygame.draw.rect(
        surface, (255, 255, 255) if ready else (100, 70, 120), rect, width=3, border_radius=14
    )

    label = sh.get_font(16, bold=True).render(f"{int(charge)}%", True, sh.COL_TEXT)
    surface.blit(label, label.get_rect(center=rect.center))

    # tela roxa momentânea ao ativar (o congelamento em si é lido pelo
    # 04_enemies através de context["ultimate_freeze"])
    fx = context.get("ultimate_active_fx", 0)
    if fx > 0:
        alpha = int(150 * (fx / FX_DURATION))
        overlay = pygame.Surface((context["width"], context["height"]), pygame.SRCALPHA)
        overlay.fill((130, 40, 200, alpha))
        surface.blit(overlay, (0, 0))
    elif context.get("ultimate_freeze", 0) > 0:
        overlay = pygame.Surface((context["width"], context["height"]), pygame.SRCALPHA)
        overlay.fill((130, 40, 200, 55))
        surface.blit(overlay, (0, 0))
