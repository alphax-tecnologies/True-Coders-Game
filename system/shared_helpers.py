# -*- coding: utf-8 -*-
"""
system/shared_helpers.py
==========================
Funções e constantes compartilhadas entre os módulos loader.py do IF
DEFENSE (carregamento seguro de imagem/som, easing, cores, barra de
vida, e as "estatísticas" de cada defesa/ataque/zumbi).

IMPORTANTE: este arquivo NÃO é um loader.py — ele fica direto dentro
de system/ (não dentro de uma subpasta), então o general_loader.py
NUNCA o enxerga como módulo do jogo (ele só varre subpastas que
contêm um loader.py). É só uma biblioteca comum que cada loader.py
importa com `import shared_helpers as sh`.
"""

import os
import math
import pygame

SYSTEM_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SYSTEM_DIR)
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

try:
    MIXER_OK = pygame.mixer.get_init() is not None
except pygame.error:
    MIXER_OK = False


# =========================================================================
#  CARREGAMENTO SEGURO DE ASSETS
# =========================================================================


def load_image(filename, fallback_size=None):
    """Carrega uma imagem de assets/. Se não existir, devolve uma
    superfície pequena e transparente — quem desenha checa
    has_image() e usa um desenho de fallback (retângulo/círculo
    colorido) em vez de travar o jogo."""
    path = os.path.join(ASSETS_DIR, filename)
    if os.path.isfile(path):
        try:
            return pygame.image.load(path).convert_alpha()
        except pygame.error:
            pass
    return pygame.Surface(fallback_size or (10, 10), pygame.SRCALPHA)


def has_image(surf):
    return surf is not None and surf.get_width() > 10


def blit_scaled(surface, img, rect):
    scaled = pygame.transform.smoothscale(img, rect.size)
    surface.blit(scaled, rect.topleft)


def load_sound(filename):
    """Carrega um efeito sonoro de assets/. Devolve None se não
    existir ou se o mixer não estiver disponível — nesse caso o som é
    simplesmente ignorado (play_sfx não faz nada com None)."""
    if not MIXER_OK:
        return None
    path = os.path.join(ASSETS_DIR, filename)
    if os.path.isfile(path):
        try:
            return pygame.mixer.Sound(path)
        except pygame.error:
            return None
    return None


def play_sfx(sound, volume=0.7):
    if sound is not None:
        sound.set_volume(volume)
        sound.play()


def play_music(filename, volume=0.6, loops=-1):
    """Toca uma música de fundo (assets/filename) se ela existir. Se
    não existir, o jogo simplesmente continua sem música de fundo."""
    if not MIXER_OK:
        return False
    path = os.path.join(ASSETS_DIR, filename)
    if not os.path.isfile(path):
        return False
    try:
        pygame.mixer.music.load(path)
        pygame.mixer.music.set_volume(volume)
        pygame.mixer.music.play(loops)
        return True
    except pygame.error:
        return False


# =========================================================================
#  MATEMÁTICA / ANIMAÇÃO
# =========================================================================


def lerp(a, b, t):
    return a + (b - a) * t


def ease_towards(current, target, dt, speed=10.0):
    """Aproxima 'current' de 'target' suavemente (independente de FPS)."""
    t = 1 - math.exp(-speed * dt)
    return lerp(current, target, t)


def clamp(value, lo, hi):
    return max(lo, min(hi, value))


# =========================================================================
#  DESENHO
# =========================================================================


def draw_bar(surface, rect, ratio, fg_color, bg_color=(30, 30, 30), border_color=(0, 0, 0)):
    ratio = clamp(ratio, 0.0, 1.0)
    pygame.draw.rect(surface, bg_color, rect, border_radius=3)
    fill_rect = pygame.Rect(rect.x, rect.y, int(rect.width * ratio), rect.height)
    if fill_rect.width > 0:
        pygame.draw.rect(surface, fg_color, fill_rect, border_radius=3)
    pygame.draw.rect(surface, border_color, rect, width=1, border_radius=3)


_FONT_CACHE = {}


def get_font(size, bold=False):
    key = (size, bold)
    if key not in _FONT_CACHE:
        _FONT_CACHE[key] = pygame.font.SysFont(
            "consolas,couriernew,monospace", size, bold=bold
        )
    return _FONT_CACHE[key]


COL_TEXT = (230, 235, 225)
COL_TEXT_DIM = (170, 178, 170)
COL_GOLD = (240, 210, 120)
COL_RED = (205, 45, 45)
COL_GREEN = (90, 200, 80)
COL_PURPLE = (150, 60, 220)


# =========================================================================
#  ESTATÍSTICAS DOS ITENS (DEFESAS / ATAQUES / ZUMBIS)
# =========================================================================
# "image" é o nome do arquivo que cada item procura em assets/. Se o
# arquivo não existir, o jogo desenha um retângulo/círculo colorido
# no lugar (fallback), então nada trava por falta de arte ainda.

DEFENSE_STATS = {
    "mina": {
        "label": "Mina", "cost": 25, "category": "defense",
        "hp": 1, "color": (150, 130, 40), "image": "defesa_mina.png",
    },
    "barreira": {
        "label": "Barreira", "cost": 50, "category": "defense",
        "hp": 120, "color": (150, 115, 70), "image": "defesa_barreira.png",
    },
    "onibus": {
        "label": "Ônibus", "cost": 125, "category": "defense",
        "hp": 320, "color": (210, 195, 40), "image": "defesa_onibus.png",
    },
    "fosso": {
        "label": "Fosso", "cost": 60, "category": "defense",
        "hp": 999999, "color": (60, 100, 150), "image": "defesa_fosso.png",
    },
    "espinhos": {
        "label": "Espinhos", "cost": 40, "category": "defense",
        "hp": 45, "color": (150, 40, 40), "image": "defesa_espinhos.png",
    },
}

ATTACK_STATS = {
    "laser": {
        "label": "LAISER", "cost": 100, "category": "attack",
        "color": (200, 60, 60), "image": "ataque_laser.png",
    },
    "computador": {
        "label": "PC", "cost": 75, "category": "attack",
        "color": (60, 180, 200), "image": "ataque_computador.png",
    },
    "canhao": {
        "label": "Canhão", "cost": 150, "category": "attack",
        "color": (95, 95, 95), "image": "ataque_canhao.png",
    },
}

HOTBAR_ITEMS = [
    "mina", "barreira", "onibus", "fosso", "espinhos",
    "laser", "computador", "canhao",
]

ZOMBIE_STATS = {
    "estudante": {
        "label": "Estudante", "hp": 30, "speed": 55, "damage": 4, "coins": 3,
        "color": (110, 150, 90), "image": "zumbi_estudante.png",
    },
    "professor": {
        "label": "Professor", "hp": 75, "speed": 42, "damage": 9, "coins": 8,
        "color": (90, 110, 150), "image": "zumbi_professor.png",
    },
    "diretor": {
        "label": "Diretor", "hp": 420, "speed": 30, "damage": 22, "coins": 60,
        "color": (150, 40, 40), "image": "zumbi_diretor.png",
    },
}
