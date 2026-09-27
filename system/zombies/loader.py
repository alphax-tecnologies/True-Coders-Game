# -*- coding: utf-8 -*-
"""
IF DEFENSE - system/zombies/loader.py
=======================================
Módulo plugável (contrato em system/general_loader.py) responsável por:

  1. Spawnar zumbis aleatoriamente numa das 4 linhas do campo, em
     intervalos de tempo também aleatórios.
  2. Mover cada zumbi da direita pra esquerda, em direção à casa.
  3. Desenhar cada zumbi com sua barra de vida acima da cabeça.
  4. Detectar quando um zumbi chega até a casa (x <= limite esquerdo):
     nesse caso o jogo é encerrado e a imagem de game over é mostrada.
  5. Quando um zumbi morre (vida <= 0), remove-lo da lista e dar
     recompensa em moedas ao jogador.

GRADE DO CAMPO
----------------
4 linhas x 6 colunas, como definido no jogo. As linhas são usadas
apenas para posicionar verticalmente os zumbis (cada zumbi anda em
linha reta, só no eixo x, dentro da sua linha).

CONTRATO COM OUTROS MÓDULOS (via context)
-------------------------------------------
Exposto por este módulo:
    context["zombies"]       -> lista de instâncias Zombie vivas (as
                                 mortas são removidas automaticamente).
                                 Lido por system/atacks/loader.py para
                                 escolher o alvo mais próximo.
    context["game_over"]     -> bool, True quando um zumbi chega na casa
    context["kills"]         -> int, contagem de zumbis derrotados

Lido de outros módulos:
    context["money"]         -> incrementado aqui quando um zumbi morre
                                 (recompensa). Criado com 200 se ainda
                                 não existir (mesmo default usado pelo
                                 módulo de ataques, caso a ordem de
                                 carregamento varie).
"""

import os
import random

import pygame


ASSETS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets"
)

# ---- geometria do campo de batalha ----------------------------------
FIELD_ROWS = 4
FIELD_COLS = 6

FIELD_LEFT = 400     # onde fica a "casa" - zumbi que passar disso, game over
FIELD_RIGHT = 1650   # zumbis aparecem a partir daqui (fora da tela, entram andando)
FIELD_TOP = 250
ROW_HEIGHT = 155

# ---- zumbi genérico (por enquanto só um tipo) ------------------------
ZOMBIE_MAX_HP = 100
ZOMBIE_SPEED = 35          # pixels por segundo
ZOMBIE_SIZE = (70, 100)    # largura, altura do sprite
ZOMBIE_KILL_REWARD = 25    # moedas ganhas ao matar um zumbi

# ---- spawn aleatório --------------------------------------------------
SPAWN_MIN_INTERVAL = 2.0   # segundos
SPAWN_MAX_INTERVAL = 4.5


# =========================================================================
#  SPRITE DO ZUMBI (com placeholder automático)
# =========================================================================


def _build_zombie_placeholder(size):
    """Placeholder simples pra zumbi enquanto não há spritesheet de
    verdade: um retângulo esverdeado com uma "cabeça" arredondada."""
    w, h = size
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    body_color = (70, 110, 60)
    outline = (20, 40, 20)

    body_rect = pygame.Rect(w * 0.15, h * 0.35, w * 0.7, h * 0.65)
    pygame.draw.rect(surf, body_color, body_rect, border_radius=8)
    pygame.draw.rect(surf, outline, body_rect, 2, border_radius=8)

    head_center = (w // 2, int(h * 0.22))
    head_radius = int(w * 0.28)
    pygame.draw.circle(surf, body_color, head_center, head_radius)
    pygame.draw.circle(surf, outline, head_center, head_radius, 2)

    eye_offset = head_radius // 2
    pygame.draw.circle(surf, (200, 30, 30), (head_center[0] - eye_offset, head_center[1]), 3)
    pygame.draw.circle(surf, (200, 30, 30), (head_center[0] + eye_offset, head_center[1]), 3)

    return surf


def _load_zombie_sprite(size):
    path = os.path.join(ASSETS_DIR, "zombie.png")
    if os.path.isfile(path):
        try:
            image = pygame.image.load(path).convert_alpha()
            return pygame.transform.smoothscale(image, size)
        except Exception:
            pass
    return _build_zombie_placeholder(size)


def _load_gameover_image(screen_size):
    path = os.path.join(ASSETS_DIR, "gameover.png")
    if os.path.isfile(path):
        try:
            image = pygame.image.load(path).convert_alpha()
            return pygame.transform.smoothscale(image, screen_size)
        except Exception:
            pass

    # placeholder de game over, caso a imagem ainda não exista
    w, h = screen_size
    surf = pygame.Surface((w, h))
    surf.fill((10, 10, 10))
    font = pygame.font.SysFont(None, 96)
    label = font.render("GAME OVER", True, (200, 30, 30))
    surf.blit(label, label.get_rect(center=(w // 2, h // 2)))
    return surf


# =========================================================================
#  ZUMBI
# =========================================================================


class Zombie:
    def __init__(self, row, sprite):
        self.row = row
        self.sprite = sprite
        self.x = float(FIELD_RIGHT)
        self.y = FIELD_TOP + row * ROW_HEIGHT + ROW_HEIGHT / 2
        self.hp = ZOMBIE_MAX_HP
        self.max_hp = ZOMBIE_MAX_HP
        self.alive = True

    def update(self, dt):
        if not self.alive:
            return
        self.x -= ZOMBIE_SPEED * dt

    def take_damage(self, amount):
        if not self.alive:
            return
        self.hp -= amount
        if self.hp <= 0:
            self.hp = 0
            self.alive = False

    def reached_house(self):
        return self.x <= FIELD_LEFT

    def draw(self, surface):
        sprite_rect = self.sprite.get_rect(center=(int(self.x), int(self.y)))
        surface.blit(self.sprite, sprite_rect)
        self._draw_health_bar(surface, sprite_rect)

    def _draw_health_bar(self, surface, sprite_rect):
        bar_width = sprite_rect.width
        bar_height = 8
        bar_x = sprite_rect.left
        bar_y = sprite_rect.top - bar_height - 6

        ratio = max(0.0, self.hp / self.max_hp)
        pygame.draw.rect(
            surface, (60, 0, 0), (bar_x, bar_y, bar_width, bar_height), border_radius=3
        )
        if ratio > 0:
            fill_color = (40, 200, 40) if ratio > 0.3 else (220, 160, 30)
            pygame.draw.rect(
                surface,
                fill_color,
                (bar_x, bar_y, int(bar_width * ratio), bar_height),
                border_radius=3,
            )
        pygame.draw.rect(
            surface, (10, 10, 10), (bar_x, bar_y, bar_width, bar_height), 1, border_radius=3
        )


# =========================================================================
#  HOOKS DO CONTRATO general_loader
# =========================================================================


def setup(context):
    context["zombies"] = []
    context["game_over"] = False
    context["kills"] = 0
    context.setdefault("money", 200)

    context["_zombie_sprite"] = _load_zombie_sprite(ZOMBIE_SIZE)
    context["_gameover_image"] = _load_gameover_image(
        (context.get("width", 1280), context.get("height", 720))
    )
    context["_next_spawn_in"] = random.uniform(SPAWN_MIN_INTERVAL, SPAWN_MAX_INTERVAL)


def _spawn_zombie(context):
    row = random.randint(0, FIELD_ROWS - 1)
    zombie = Zombie(row, context["_zombie_sprite"])
    context["zombies"].append(zombie)


def update(context, dt):
    if context.get("game_over"):
        return

    # ---- spawn aleatório de novos zumbis ----
    context["_next_spawn_in"] -= dt
    if context["_next_spawn_in"] <= 0:
        _spawn_zombie(context)
        context["_next_spawn_in"] = random.uniform(SPAWN_MIN_INTERVAL, SPAWN_MAX_INTERVAL)

    # ---- atualiza zumbis vivos ----
    zombies = context.get("zombies", [])
    for zombie in zombies:
        zombie.update(dt)

        if zombie.alive and zombie.reached_house():
            context["game_over"] = True
            return

    # ---- recompensa por zumbis mortos neste frame, depois remove ----
    still_alive = []
    for zombie in zombies:
        if zombie.alive:
            still_alive.append(zombie)
        else:
            context["money"] = context.get("money", 0) + ZOMBIE_KILL_REWARD
            context["kills"] = context.get("kills", 0) + 1

    context["zombies"] = still_alive


def draw(context, surface):
    for zombie in context.get("zombies", []):
        zombie.draw(surface)

    if context.get("game_over"):
        gameover_image = context.get("_gameover_image")
        if gameover_image is not None:
            surface.blit(gameover_image, (0, 0))
        context["running"] = False