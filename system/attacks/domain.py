# -*- coding: utf-8 -*-
"""
IF DEFENSE - system/atacks/domain.py
=====================================
Define o "contrato" de um ataque e utilitários compartilhados por todo
o sistema de ataques: carregar spritesheet, recortar frames e animar.

CONTRATO DE UM ARQUIVO DE ATAQUE (ex: system/atacks/fogo.py)
--------------------------------------------------------------
Cada arquivo de ataque é um módulo .py solto direto dentro de
system/atacks/ (nunca dentro de atacks/domain.py, loader.py ou
qualquer arquivo que já exista no sistema — esses são ignorados
automaticamente pelo loader). Ele deve terminar definindo uma
variável de módulo chamada ATTACK, um dicionário com este formato:

    ATTACK = {
        "name": "Bola de Fogo",       # nome mostrado (opcional, usa o
                                       # nome do arquivo se ausente)
        "cost": 50,                   # custo em moedas pra usar
        "damage": 20,                 # dano causado ao zumbi mais
                                       # próximo do ataque, por uso
        "source": "assets/fogo.png",  # caminho da imagem do spritesheet
        "sprite_frame_width": 64,     # largura de cada frame (px)
        "sprite_frame_height": 64,    # altura de cada frame (px)
        "sprite_frame_count": 4,      # quantos frames tem o spritesheet
        "sprite_fps": 8,              # velocidade da animação
    }

A chave "source" diz onde está a imagem do spritesheet. É um caminho
relativo à RAIZ do projeto (a pasta que contém system/ e assets/), como
"assets/fogo.png" ou "assets/ataques/fogo.png", ou um caminho absoluto.
Pode usar "/" ou "\\", em qualquer sistema. Sem "source", o loader usa
o comportamento antigo: assets/<nome_do_arquivo>.png. Se a imagem não
existir, um placeholder colorido é gerado e o console avisa QUAL caminho
foi tentado, então o jogo nunca quebra por falta de asset.

O spritesheet é usado em dois lugares:
    - Ícone do slot: primeiro frame, redimensionado pro tamanho do slot.
    - Efeito no campo: animação completa, tocada uma vez sobre o
      zumbi mais próximo quando o ataque é usado.

CONTRATO DE UM ARQUIVO DE TORRETA (ex: system/atacks/laiser.py)
-------------------------------------------------------------------
Além do formato ATTACK acima (efeito instantâneo de uso único), um
arquivo de ataque pode em vez disso definir uma TURRET: uma defesa que
o jogador planta numa casa do tabuleiro, fica parada, e atira sozinha
nos zumbis que passarem pela mesma linha, em intervalos de tempo,
até ser destruída (vida própria) ou o jogo acabar.

    TURRET = {
        "name": "Laiser",             # nome mostrado (opcional)
        "cost": 100,                  # custo em moedas pra plantar
        "damage": 15,                 # dano por disparo
        "fire_interval": 3.0,         # segundos entre disparos
        "max_hp": 150,                # vida da torreta
        "source": "assets/laiser.png",  # caminho da imagem do spritesheet

        # spritesheet em grade, lido de "source" (mesmas regras do
        # ATTACK acima), dividido
        # em sprite_grid_cols colunas x sprite_grid_rows linhas, todas
        # as células do mesmo tamanho (sprite_cell_width x
        # sprite_cell_height). Cada "linha nomeada" abaixo é uma faixa
        # dentro dessa grade usada como uma animação específica.
        "sprite_grid_cols": 4,
        "sprite_grid_rows": 4,
        "sprite_cell_width": 384,
        "sprite_cell_height": 384,

        # cada entrada é (linha_inicial, linha_final) na grade,
        # 0-indexado, inclusive - todas as células dessas linhas,
        # lidas da esquerda pra direita, topo pra baixo, formam os
        # frames dessa animação. "idle" é obrigatória; as outras têm
        # fallback pra "idle" se ausentes.
        "sprite_rows": {
            "idle": (0, 1),          # torreta ativa, plantada (loop)
            "destroy": (2, 2),       # sequência de dano -> explosão
            "aftermath": (3, 3),     # fumaça residual após explodir
        },
        "sprite_fps": 8,
    }

O ciclo de vida de uma torreta plantada é todo gerenciado por
system/attacks/loader.py (turret_manager): ele guarda a lista de
torretas plantadas no context, atualiza cooldown de tiro, aplica dano
recebido, e toca destroy -> aftermath quando a vida chega a zero.
"""

import os
import hashlib

import pygame


# domain.py fica em <raiz>/system/attacks/, então a raiz do projeto está
# TRÊS níveis acima do arquivo (attacks -> system -> raiz), e os
# spritesheets ficam em <raiz>/assets/.
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ASSETS_DIR = os.path.join(PROJECT_DIR, "assets")


def resolve_source(source, ability_id):
    """Converte o valor da chave "source" de um ATTACK/TURRET no caminho
    absoluto da imagem do spritesheet.

    "source" é o caminho da imagem, e pode ser:
        - relativo à raiz do projeto: "assets/laiser.png" (o mais comum);
        - absoluto: "/home/user/jogo/assets/laiser.png".

    Barras "/" e "\\" são aceitas nos dois sistemas. Se "source" não for
    informado (None ou vazio), mantém o comportamento antigo:
    assets/<nome_do_arquivo_do_ataque>.png."""
    if not source:
        return os.path.join(ASSETS_DIR, f"{ability_id}.png")

    normalized = os.path.normpath(str(source).replace("\\", "/"))
    if os.path.isabs(normalized):
        return normalized
    return os.path.join(PROJECT_DIR, normalized)


# =========================================================================
#  SPRITESHEET: CARREGAMENTO E RECORTE DE FRAMES
# =========================================================================


def _color_from_name(name):
    """Gera uma cor determinística a partir de uma string (nome do
    ataque), usada pra colorir o placeholder quando não há spritesheet
    de verdade ainda."""
    digest = hashlib.md5(name.encode("utf-8")).hexdigest()
    r = int(digest[0:2], 16)
    g = int(digest[2:4], 16)
    b = int(digest[4:6], 16)
    # evita cores escuras demais (ruins de ver sobre fundo escuro)
    r = max(r, 80)
    g = max(g, 80)
    b = max(b, 80)
    return (r, g, b)


def _build_placeholder_sheet(attack_id, frame_w, frame_h, frame_count):
    """Cria um spritesheet placeholder em memória: frame_count
    quadrados coloridos lado a lado, com um número escrito em cada
    frame indicando o índice, só pra ficar visualmente distinguível
    enquanto não há arte de verdade."""
    color = _color_from_name(attack_id)
    sheet = pygame.Surface((frame_w * frame_count, frame_h), pygame.SRCALPHA)

    font = pygame.font.SysFont(None, max(12, frame_h // 3))
    for i in range(frame_count):
        rect = pygame.Rect(i * frame_w, 0, frame_w, frame_h)
        # leve variação de brilho por frame pra "animação" ficar visível
        shade = 1.0 - (i * 0.08)
        frame_color = tuple(max(0, min(255, int(c * shade))) for c in color)
        pygame.draw.rect(sheet, frame_color, rect)
        pygame.draw.rect(sheet, (20, 20, 20), rect, 2)

        label = font.render(str(i + 1), True, (255, 255, 255))
        label_rect = label.get_rect(center=rect.center)
        sheet.blit(label, label_rect)

    return sheet


def _load_image_or_none(path, ability_id):
    """Carrega a imagem em `path`. Se o arquivo não existir ou não puder
    ser lido, avisa no console (dizendo QUAL caminho foi tentado, pra
    facilitar achar erro de digitação em "source") e devolve None."""
    if not os.path.isfile(path):
        print(
            f"[IF DEFENSE] Aviso: imagem de '{ability_id}' não encontrada em "
            f"'{path}'. Usando placeholder."
        )
        return None
    try:
        return pygame.image.load(path).convert_alpha()
    except Exception as error:
        print(
            f"[IF DEFENSE] Aviso: não consegui ler a imagem de '{ability_id}' "
            f"em '{path}' ({error}). Usando placeholder."
        )
        return None


def load_spritesheet(attack_id, frame_w, frame_h, frame_count, source=None):
    """Carrega o spritesheet horizontal do ataque a partir de `source`
    (ver resolve_source); sem `source`, usa assets/<attack_id>.png. Se a
    imagem não existir, devolve um placeholder gerado."""
    path = resolve_source(source, attack_id)
    sheet = _load_image_or_none(path, attack_id)
    if sheet is not None:
        return sheet
    return _build_placeholder_sheet(attack_id, frame_w, frame_h, frame_count)


def slice_frames(sheet, frame_w, frame_h, frame_count):
    """Recorta um spritesheet horizontal (frames lado a lado, uma única
    linha) em uma lista de Surfaces, uma por frame."""
    frames = []
    sheet_w = sheet.get_width()
    sheet_h = sheet.get_height()
    for i in range(frame_count):
        x = i * frame_w
        if x + frame_w > sheet_w or frame_h > sheet_h:
            # spritesheet fornecido é menor que o esperado: recorta o
            # que der e completa com o último frame válido, pra não
            # estourar limites.
            if frames:
                frames.append(frames[-1])
                continue
            x = 0
        rect = pygame.Rect(x, 0, frame_w, frame_h)
        frame = pygame.Surface((frame_w, frame_h), pygame.SRCALPHA)
        frame.blit(sheet, (0, 0), rect)
        frames.append(frame)
    return frames


def slice_grid_frames(sheet, cell_w, cell_h, cols, rows, row_range):
    """Recorta uma faixa de linhas de um spritesheet organizado em
    grade (cols x rows células de tamanho cell_w x cell_h) e devolve a
    lista de frames dessa faixa, lidos da esquerda pra direita, linha
    por linha, de cima pra baixo.

    row_range é uma tupla (linha_inicial, linha_final), ambas
    inclusive, 0-indexadas. Ex: (0, 1) pega todas as células das duas
    primeiras linhas da grade, em ordem."""
    start_row, end_row = row_range
    sheet_w = sheet.get_width()
    sheet_h = sheet.get_height()

    frames = []
    for row in range(start_row, end_row + 1):
        for col in range(cols):
            x = col * cell_w
            y = row * cell_h
            frame = pygame.Surface((cell_w, cell_h), pygame.SRCALPHA)
            if x + cell_w <= sheet_w and y + cell_h <= sheet_h:
                rect = pygame.Rect(x, y, cell_w, cell_h)
                frame.blit(sheet, (0, 0), rect)
            elif frames:
                # célula fora dos limites do spritesheet fornecido:
                # repete o último frame válido, pra não estourar
                # limites nem devolver superfície vazia.
                frame = frames[-1].copy()
            frames.append(frame)
    return frames


def _build_placeholder_grid_sheet(turret_id, cell_w, cell_h, cols, rows):
    """Placeholder de spritesheet em grade completo (cols x rows
    células), usado quando assets/<turret_id>.png ainda não existe.
    Cada linha recebe uma cor um pouco diferente pra facilitar
    distinguir visualmente as diferentes animações (idle/destroy/
    aftermath) enquanto não há arte de verdade."""
    base_color = _color_from_name(turret_id)
    sheet = pygame.Surface((cell_w * cols, cell_h * rows), pygame.SRCALPHA)
    font = pygame.font.SysFont(None, max(12, cell_h // 6))

    for row in range(rows):
        row_shade = 1.0 - (row * 0.18)
        row_color = tuple(max(0, min(255, int(c * row_shade))) for c in base_color)
        for col in range(cols):
            rect = pygame.Rect(col * cell_w, row * cell_h, cell_w, cell_h)
            col_shade = 1.0 - (col * 0.06)
            cell_color = tuple(max(0, min(255, int(c * col_shade))) for c in row_color)
            pygame.draw.rect(sheet, cell_color, rect)
            pygame.draw.rect(sheet, (20, 20, 20), rect, 2)
            label = font.render(f"{row},{col}", True, (255, 255, 255))
            sheet.blit(label, label.get_rect(center=rect.center))

    return sheet


def load_grid_spritesheet(turret_id, cell_w, cell_h, cols, rows, source=None):
    """Carrega o spritesheet em grade da torreta a partir de `source`
    (ver resolve_source); sem `source`, usa assets/<turret_id>.png. Se a
    imagem não existir, devolve um placeholder com o tamanho de grade
    esperado."""
    path = resolve_source(source, turret_id)
    sheet = _load_image_or_none(path, turret_id)
    if sheet is not None:
        return sheet
    return _build_placeholder_grid_sheet(turret_id, cell_w, cell_h, cols, rows)


class SpriteAnimation:
    """Pequeno player de animação de spritesheet: guarda a lista de
    frames e o fps, e sabe qual frame mostrar dado um tempo acumulado.
    Não depende de estado global — cada instância de animação em uso
    no campo (ex: efeito de um ataque específico voando até um zumbi)
    tem seu próprio "elapsed"."""

    def __init__(self, frames, fps, loop=False):
        self.frames = frames
        self.fps = max(1, fps)
        self.frame_duration = 1.0 / self.fps
        self.total_duration = self.frame_duration * len(frames)
        self.loop = loop

    def frame_at(self, elapsed):
        """Devolve a Surface do frame correspondente ao tempo `elapsed`
        (segundos) desde o início da animação. Se loop=True, a
        animação recomeça ao chegar no fim (usado pra animações
        contínuas, tipo uma torreta "ativa" parada no campo). Se
        loop=False, trava no último frame após o fim — chame
        is_finished() para saber quando remover o efeito."""
        if self.loop and self.total_duration > 0:
            elapsed = elapsed % self.total_duration
        index = int(elapsed / self.frame_duration)
        index = max(0, min(index, len(self.frames) - 1))
        return self.frames[index]

    def is_finished(self, elapsed):
        if self.loop:
            return False
        return elapsed >= self.total_duration

    def first_frame(self):
        return self.frames[0]


# =========================================================================
#  ESTRUTURA DE UM ATAQUE CARREGADO
# =========================================================================


class Attack:
    """Representa um ataque já carregado e pronto pra uso: dados de
    balanceamento (nome, custo, dano) + animação (ícone e efeito)."""

    def __init__(self, attack_id, data):
        self.id = attack_id
        self.name = data.get("name", attack_id.replace("_", " ").title())
        self.cost = int(data.get("cost", 50))
        self.damage = int(data.get("damage", 10))

        frame_w = int(data.get("sprite_frame_width", 64))
        frame_h = int(data.get("sprite_frame_height", 64))
        frame_count = max(1, int(data.get("sprite_frame_count", 1)))
        fps = int(data.get("sprite_fps", 8))

        self.source = data.get("source")
        sheet = load_spritesheet(
            attack_id, frame_w, frame_h, frame_count, source=self.source
        )
        frames = slice_frames(sheet, frame_w, frame_h, frame_count)

        self.animation = SpriteAnimation(frames, fps)
        self.icon = pygame.transform.smoothscale(frames[0], (frame_w, frame_h))

    def icon_scaled(self, size):
        return pygame.transform.smoothscale(self.icon, size)

    def __repr__(self):
        return f"<Attack {self.id} cost={self.cost} damage={self.damage}>"


# =========================================================================
#  ESTRUTURA DE UMA TORRETA CARREGADA (definição, não instância plantada)
# =========================================================================


class Turret:
    """Representa o TIPO de uma torreta (ex: Laiser) já carregado e
    pronto pra uso: dados de balanceamento + as três animações lidas
    do spritesheet em grade (idle, destroy, aftermath).

    Isto é a DEFINIÇÃO da torreta (uma por tipo, carregada uma vez).
    Cada torreta que o jogador planta no tabuleiro é uma instância de
    PlacedTurret (ver mais abaixo), que referencia esta definição pra
    saber como se desenhar e se comportar."""

    def __init__(self, turret_id, data):
        self.id = turret_id
        self.name = data.get("name", turret_id.replace("_", " ").title())
        self.cost = int(data.get("cost", 100))
        self.damage = int(data.get("damage", 15))
        self.fire_interval = float(data.get("fire_interval", 3.0))
        self.max_hp = int(data.get("max_hp", 150))

        cell_w = int(data.get("sprite_cell_width", 64))
        cell_h = int(data.get("sprite_cell_height", 64))
        cols = max(1, int(data.get("sprite_grid_cols", 1)))
        rows = max(1, int(data.get("sprite_grid_rows", 1)))
        fps = int(data.get("sprite_fps", 8))

        sprite_rows = data.get("sprite_rows", {})
        idle_range = sprite_rows.get("idle", (0, 0))
        destroy_range = sprite_rows.get("destroy", idle_range)
        aftermath_range = sprite_rows.get("aftermath", destroy_range)

        self.source = data.get("source")
        sheet = load_grid_spritesheet(
            turret_id, cell_w, cell_h, cols, rows, source=self.source
        )

        idle_frames = slice_grid_frames(sheet, cell_w, cell_h, cols, rows, idle_range)
        destroy_frames = slice_grid_frames(sheet, cell_w, cell_h, cols, rows, destroy_range)
        aftermath_frames = slice_grid_frames(sheet, cell_w, cell_h, cols, rows, aftermath_range)

        self.idle_animation = SpriteAnimation(idle_frames, fps, loop=True)
        self.destroy_animation = SpriteAnimation(destroy_frames, fps, loop=False)
        self.aftermath_animation = SpriteAnimation(aftermath_frames, fps, loop=False)

        self.cell_size = (cell_w, cell_h)
        self.icon = pygame.transform.smoothscale(idle_frames[0], (cell_w, cell_h))

    def icon_scaled(self, size):
        return pygame.transform.smoothscale(self.icon, size)

    def __repr__(self):
        return f"<Turret {self.id} cost={self.cost} damage={self.damage}>"