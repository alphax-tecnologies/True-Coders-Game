# -*- coding: utf-8 -*-
"""
IF DEFENSE - system/zombies/loader.py
=======================================
Define os TIPOS de zumbi do jogo e devolve, para classic_mode/loader_mode.py,
uma lista de fábricas (classes chamáveis) que ele usa para criar os zumbis
de cada onda.

O QUE ESTE ARQUIVO FAZ (e o que NÃO faz)
------------------------------------------
Faz: carregar a imagem do zumbi, animá-la, desenhá-la com a barra de vida
e tocar a animação de morte antes de o zumbi sumir.

NÃO faz: mover o zumbi, spawnar ondas, cobrar recompensa ou detectar chegada
à casa. Isso é do loader_mode.py. Como este zumbi NÃO define update(), o
loader_mode o move sozinho (usando .speed, em px/s) e o faz parar para
atacar torretas à frente (usando .damage, em dano/s).

COMO ADICIONAR OU EDITAR UM TIPO DE ZUMBI
-------------------------------------------
Cada tipo é um dicionário em ZOMBIE_TYPES, com a mesma ideia do ATTACK/TURRET
dos ataques: a imagem vem da chave "source".

    "source":  caminho da imagem (spritesheet), relativo à RAIZ do projeto
               (a pasta que contém system/ e assets/), ex.: "assets/zombie.png",
               ou absoluto. Aceita "/" e "\\".
    Spritesheet em grade (colunas x linhas), todas as células do mesmo tamanho:
    "sprite_grid_cols", "sprite_grid_rows", "sprite_cell_width",
    "sprite_cell_height".
    "sprite_rows": faixas de linhas usadas em cada animação, (inicial, final),
                   0-indexado e inclusivo:
                       "walk"  (obrigatória)  animação em loop andando
                       "death" (opcional)     tocada uma vez ao morrer
    "sprite_fps":  velocidade da animação.
    "draw_size":   (largura, altura) em px, no espaço do jogo, para desenhar.

Se a imagem não existir, um zumbi placeholder é desenhado e o console avisa
QUAL caminho foi tentado (para achar erro de digitação em "source").
"""

import os

import pygame


# este arquivo fica em <raiz>/system/zombies/ -> a raiz está 3 níveis acima.
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# =========================================================================
#  TIPOS DE ZUMBI  (edite aqui)
# =========================================================================

ZOMBIE_TYPES = [
    {
        "name": "Zumbi",
        "source": "assets/zombie.png",

        "hp": 100,
        "damage": 20,          # dano/s em torretas quando está mordendo

        # spritesheet: 1 linha de frames de andar, opcionalmente uma de morte
        "sprite_grid_cols": 4,
        "sprite_grid_rows": 1,
        "sprite_cell_width": 256,
        "sprite_cell_height": 256,
        "sprite_rows": {
            "walk": (0, 0),
        },
        "sprite_fps": 8,
        "draw_size": (110, 130),
    },
]


# =========================================================================
#  CARREGAMENTO DE IMAGEM (por "source")
# =========================================================================


def resolve_source(source):
    """Caminho absoluto da imagem a partir do valor de "source" (relativo à
    raiz do projeto, ou absoluto). Aceita "/" e "\\"."""
    normalized = os.path.normpath(str(source).replace("\\", "/"))
    if os.path.isabs(normalized):
        return normalized
    return os.path.join(PROJECT_DIR, normalized)


def _load_sheet(source, label):
    """Carrega a imagem; devolve None (com aviso claro) se não existir."""
    if not source:
        print(f"[IF DEFENSE] Aviso: o zumbi '{label}' não tem \"source\". Usando placeholder.")
        return None
    path = resolve_source(source)
    if not os.path.isfile(path):
        print(f"[IF DEFENSE] Aviso: imagem do zumbi '{label}' não encontrada em '{path}'. Usando placeholder.")
        return None
    try:
        return pygame.image.load(path).convert_alpha()
    except Exception as error:
        print(f"[IF DEFENSE] Aviso: não consegui ler a imagem do zumbi '{label}' em '{path}' ({error}).")
        return None


def _slice_rows(sheet, cell_w, cell_h, cols, row_range):
    """Recorta as células das linhas (inicial, final) do spritesheet."""
    frames = []
    first, last = row_range
    for row in range(first, last + 1):
        for col in range(cols):
            x, y = col * cell_w, row * cell_h
            if x + cell_w > sheet.get_width() or y + cell_h > sheet.get_height():
                continue
            frame = pygame.Surface((cell_w, cell_h), pygame.SRCALPHA)
            frame.blit(sheet, (0, 0), pygame.Rect(x, y, cell_w, cell_h))
            frames.append(frame)
    return frames


def _placeholder_frames(size, count=4):
    """Frames de um zumbi desenhado por código, para quando falta a imagem."""
    w, h = size
    frames = []
    for i in range(count):
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        bob = int(3 * (1 if i % 2 else -1))               # balanço simples
        body = pygame.Rect(int(w * 0.18), int(h * 0.38) + bob, int(w * 0.64), int(h * 0.62) - 2)
        pygame.draw.rect(surf, (70, 110, 60), body, border_radius=10)
        pygame.draw.rect(surf, (20, 40, 20), body, 2, border_radius=10)
        head = (w // 2, int(h * 0.24) + bob)
        pygame.draw.circle(surf, (85, 130, 70), head, int(w * 0.24))
        pygame.draw.circle(surf, (20, 40, 20), head, int(w * 0.24), 2)
        for dx in (-int(w * 0.09), int(w * 0.09)):
            pygame.draw.circle(surf, (210, 40, 40), (head[0] + dx, head[1]), 3)
        frames.append(surf)
    return frames


class _ZombieArt:
    """Animações já carregadas de UM tipo (walk e death), compartilhadas por
    todas as instâncias desse tipo (a imagem é lida uma vez só)."""

    def __init__(self, data):
        self.name = data.get("name", "Zumbi")
        self.max_hp = float(data.get("hp", 100))
        self.damage = float(data.get("damage", 20))
        self.fps = max(1, int(data.get("sprite_fps", 8)))
        self.draw_size = tuple(data.get("draw_size", (110, 130)))

        cell_w = int(data.get("sprite_cell_width", 64))
        cell_h = int(data.get("sprite_cell_height", 64))
        cols = max(1, int(data.get("sprite_grid_cols", 1)))
        rows = data.get("sprite_rows", {"walk": (0, 0)})
        walk_range = rows.get("walk", (0, 0))
        death_range = rows.get("death")

        sheet = _load_sheet(data.get("source"), self.name)
        walk, death = [], []
        if sheet is not None:
            walk = _slice_rows(sheet, cell_w, cell_h, cols, walk_range)
            if death_range is not None:
                death = _slice_rows(sheet, cell_w, cell_h, cols, death_range)

        if not walk:                                       # sem imagem/recorte válido
            walk = _placeholder_frames(self.draw_size)
        # escala uma única vez, aqui, e não a cada frame de jogo
        self.walk = [pygame.transform.smoothscale(f, self.draw_size) for f in walk]
        self.death = [pygame.transform.smoothscale(f, self.draw_size) for f in death]


# =========================================================================
#  O ZUMBI EM SI
# =========================================================================


class Zombie:
    """Uma instância de zumbi. Contrato com o loader_mode: .row, .x, .y,
    .speed, .alive, .take_damage(), .animate(dt), .draw(surface), .is_done()."""

    DEATH_HOLD = 0.5   # s que o último frame fica na tela quando não há anim. de morte

    def __init__(self, art, row=0, x=0.0, y=0.0, speed=0.0):
        self.art = art
        self.row = row
        self.x = float(x)
        self.y = float(y)
        self.speed = speed
        self.max_hp = art.max_hp
        self.hp = art.max_hp
        self.damage = art.damage
        self.alive = True
        self._clock = 0.0          # tempo de animação
        self._death_clock = 0.0

    def take_damage(self, amount):
        if not self.alive:
            return
        self.hp -= amount
        if self.hp <= 0:
            self.hp = 0
            self.alive = False
            self._death_clock = 0.0

    def animate(self, dt):
        if self.alive:
            self._clock += dt
        else:
            self._death_clock += dt

    def _death_length(self):
        return len(self.art.death) / self.art.fps if self.art.death else self.DEATH_HOLD

    def is_done(self):
        return (not self.alive) and self._death_clock >= self._death_length()

    def _current_frame(self):
        if self.alive:
            frames, t, loop = self.art.walk, self._clock, True
        elif self.art.death:
            frames, t, loop = self.art.death, self._death_clock, False
        else:
            return self.art.walk[-1]
        index = int(t * self.art.fps)
        index = index % len(frames) if loop else min(index, len(frames) - 1)
        return frames[index]

    def draw(self, surface):
        frame = self._current_frame()
        rect = frame.get_rect(midbottom=(int(self.x), int(self.y) + frame.get_height() // 2))
        surface.blit(frame, rect)
        if self.alive:
            self._draw_health_bar(surface, rect)

    def _draw_health_bar(self, surface, sprite_rect):
        width = int(sprite_rect.width * 0.6)
        bar = pygame.Rect(0, 0, width, 7)
        bar.midbottom = (sprite_rect.centerx, sprite_rect.top + 4)
        ratio = max(0.0, self.hp / self.max_hp)
        pygame.draw.rect(surface, (60, 0, 0), bar, border_radius=3)
        if ratio > 0:
            color = (40, 200, 40) if ratio > 0.3 else (220, 160, 30)
            pygame.draw.rect(surface, color, (bar.x, bar.y, int(width * ratio), bar.h), border_radius=3)
        pygame.draw.rect(surface, (10, 10, 10), bar, 1, border_radius=3)


# =========================================================================
#  CONTRATO COM classic_mode/loader_mode.py
# =========================================================================


class ZombieType:
    """Fábrica de um tipo. O loader_mode a chama com (row=, x=, y=, speed=)."""

    def __init__(self, data):
        self.art = _ZombieArt(data)
        self.name = self.art.name

    def __call__(self, row=0, x=0.0, y=0.0, speed=0.0):
        return Zombie(self.art, row=row, x=x, y=y, speed=speed)

    def __repr__(self):
        return f"<ZombieType {self.name}>"


def load_available_zombies():
    """Lida pelo loader_mode. Precisa de pygame já inicializado (a imagem é
    convertida com convert_alpha), e o loader_mode só chama isto depois."""
    return [ZombieType(data) for data in ZOMBIE_TYPES]