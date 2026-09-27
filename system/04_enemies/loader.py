# -*- coding: utf-8 -*-
"""
system/04_enemies/loader.py
=============================
Zumbis: estudante (comum, pouca vida), professor (vida/dano médios)
e o zumbi diretor (boss - vida alta, aparece sozinho, sempre com
barra de vida visível, só surge no timer2).

Este é o módulo que faz os zumbis "conversarem" com a matriz do
tabuleiro (context["board"]["grid"]):
    - barreira / ônibus: bloqueiam o zumbi, que passa a bater na
      defesa em vez de andar, até ela morrer;
    - fosso: desacelera o zumbi enquanto ele estiver na célula;
    - espinhos: causa dano contínuo (por segundo) no zumbi;
    - mina: explode no primeiro contato (dano alto + some do
      tabuleiro).

context["spawn_enemy"](kind, row) é a função que o módulo 07_waves
chama pra colocar um zumbi novo vindo do lado direito da tela.
"""
import pygame
import shared_helpers as sh

DAMAGE_TO_BASE = 15
FX_DURATION = 0.4

_IMAGES = {}


def setup(context):
    context["enemies"] = []
    context.setdefault("fx", [])
    context["spawn_enemy"] = lambda kind, row: _spawn_enemy(context, kind, row)

    for kind, stats in sh.ZOMBIE_STATS.items():
        _IMAGES[kind] = sh.load_image(stats["image"], (100, 100))

    context["_sfx_explosion"] = sh.load_sound("sfx_explosion.wav")
    context["_sfx_base_hit"] = sh.load_sound("sfx_base_hit.wav")
    context["_sfx_coin"] = sh.load_sound("sfx_coin.wav")


def _spawn_enemy(context, kind, row):
    stats = sh.ZOMBIE_STATS[kind]
    board = context["board"]
    y = context["board_row_y"](row)
    x = board["x"] + board["w"] + 50
    enemy = {
        "kind": kind, "row": row, "x": float(x), "y": float(y),
        "hp": float(stats["hp"]), "max_hp": float(stats["hp"]),
        "speed": stats["speed"], "damage": stats["damage"], "coins": stats["coins"],
        "color": stats["color"], "attack_timer": 0.0,
    }
    context["enemies"].append(enemy)
    return enemy


def update(context, dt):
    if context.get("game_over") or context.get("paused"):
        return

    board = context["board"]
    grid = board["grid"]
    frozen = context.get("ultimate_freeze", 0) > 0

    if not frozen:
        for z in context["enemies"]:
            if z["hp"] <= 0:
                continue

            slow_mult = 1.0
            cell = context["board_point_to_cell"]((z["x"], z["y"]))
            if cell is not None:
                row, col = cell
                entry = grid[row][col]
                if entry is not None:
                    if entry["kind"] == "fosso":
                        slow_mult = 0.45
                    elif entry["kind"] == "espinhos":
                        z["hp"] -= 6 * dt
                    elif entry["kind"] == "mina":
                        z["hp"] -= 9999
                        entry["hp"] = 0
                        context["fx"].append({"x": z["x"], "y": z["y"], "t": 0.0})
                        sh.play_sfx(context.get("_sfx_explosion"), 0.7)
                    elif entry["kind"] in ("barreira", "onibus"):
                        z["attack_timer"] -= dt
                        if z["attack_timer"] <= 0:
                            entry["hp"] -= z["damage"]
                            z["attack_timer"] = 0.8
                        slow_mult = 0.0

            z["x"] -= z["speed"] * slow_mult * dt

            if z["x"] <= board["x"]:
                context["base_hp"] = max(0, context.get("base_hp", 100) - DAMAGE_TO_BASE)
                sh.play_sfx(context.get("_sfx_base_hit"), 0.7)
                z["hp"] = 0
                if context["base_hp"] <= 0:
                    context["game_over"] = True

    # ---- remover mortos, dar moedas / carga do botão roxo ----
    survivors = []
    for z in context["enemies"]:
        if z["hp"] <= 0:
            if z["x"] > board["x"]:  # morreu de dano (não por chegar na base)
                context["coins"] = context.get("coins", 0) + z["coins"]
                context["ultimate_charge"] = sh.clamp(
                    context.get("ultimate_charge", 0) + 6, 0, 100
                )
                sh.play_sfx(context.get("_sfx_coin"), 0.35)
            if z["kind"] == "diretor":
                context["_boss_active"] = False
        else:
            survivors.append(z)
    context["enemies"] = survivors

    alive_fx = []
    for fx in context["fx"]:
        fx["t"] += dt
        if fx["t"] < FX_DURATION:
            alive_fx.append(fx)
    context["fx"] = alive_fx


def draw(context, surface):
    for z in context["enemies"]:
        radius = 40 if z["kind"] == "diretor" else 26
        rect = pygame.Rect(int(z["x"]) - radius, int(z["y"]) - radius, radius * 2, radius * 2)
        img = _IMAGES.get(z["kind"])

        if sh.has_image(img):
            sh.blit_scaled(surface, img, rect)
        else:
            pygame.draw.circle(surface, z["color"], rect.center, radius)
            pygame.draw.circle(surface, (10, 10, 10), rect.center, radius, width=2)
            letter = {"estudante": "E", "professor": "P", "diretor": "D"}[z["kind"]]
            label = sh.get_font(18, bold=True).render(letter, True, (255, 255, 255))
            surface.blit(label, label.get_rect(center=rect.center))

        if z["kind"] == "diretor" or z["hp"] < z["max_hp"]:
            bar_rect = pygame.Rect(rect.x, rect.y - 14, rect.width, 7)
            sh.draw_bar(surface, bar_rect, z["hp"] / z["max_hp"], sh.COL_RED)

    for fx in context["fx"]:
        t = fx["t"] / FX_DURATION
        radius = int(sh.lerp(10, 60, t))
        alpha = int(sh.lerp(220, 0, t))
        fx_surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(fx_surf, (255, 160, 40, max(0, alpha)), (radius, radius), radius)
        surface.blit(fx_surf, (int(fx["x"]) - radius, int(fx["y"]) - radius))
