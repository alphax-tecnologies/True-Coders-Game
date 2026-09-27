# -*- coding: utf-8 -*-
"""
system/02_defenses/loader.py
==============================
Defesas colocáveis no tabuleiro: Mina, Barreira, Ônibus, Fosso e
Espinhos. Este módulo cuida de GUARDAR (context["placed_defenses"]) e
DESENHAR cada defesa, e de remover as que "morreram" (hp <= 0).

A interação de verdade com os zumbis (barreira/ônibus bloqueando e
recebendo dano, fosso desacelerando, espinhos causando dano contínuo,
mina explodindo) é feita pelo módulo 04_enemies, que lê e edita
diretamente os dicts guardados aqui através da matriz
context["board"]["grid"] — assim toda a "física" de colisão fica
concentrada num lugar só.
"""
import pygame
import shared_helpers as sh

_IMAGES = {}


def setup(context):
    context["placed_defenses"] = []
    for kind, stats in sh.DEFENSE_STATS.items():
        _IMAGES[kind] = sh.load_image(stats["image"], (100, 100))


def update(context, dt):
    grid = context["board"]["grid"]
    alive = []
    for d in context["placed_defenses"]:
        # "fosso" não tem vida de verdade (hp é só um valor gigante
        # pra nunca "morrer" de dano) - só sai do tabuleiro se alguém
        # remover manualmente no futuro.
        if d["kind"] != "fosso" and d["hp"] <= 0:
            grid[d["row"]][d["col"]] = None
            continue
        alive.append(d)
    context["placed_defenses"] = alive


def draw(context, surface):
    for d in context["placed_defenses"]:
        rect = context["board_cell_rect"](d["row"], d["col"])
        stats = sh.DEFENSE_STATS[d["kind"]]
        img = _IMAGES.get(d["kind"])

        if sh.has_image(img):
            sh.blit_scaled(surface, img, rect.inflate(-8, -8))
        else:
            inset = rect.inflate(-16, -16)
            pygame.draw.rect(surface, stats["color"], inset, border_radius=6)
            pygame.draw.rect(surface, (10, 10, 10), inset, width=2, border_radius=6)
            label = sh.get_font(13, bold=True).render(stats["label"][:3].upper(), True, sh.COL_TEXT)
            surface.blit(label, label.get_rect(center=inset.center))

        if d["kind"] in ("barreira", "onibus", "espinhos") and d["max_hp"] > 0:
            bar_rect = pygame.Rect(rect.x + 6, rect.y + 4, rect.width - 12, 6)
            sh.draw_bar(surface, bar_rect, d["hp"] / d["max_hp"], sh.COL_GREEN)
