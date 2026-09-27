# -*- coding: utf-8 -*-
"""
IF DEFENSE - system/atacks/loader.py
=====================================
Módulo plugável (contrato definido em system/general_loader.py) que:

  1. Varre system/atacks/ procurando arquivos .py de habilidade
     (qualquer .py que não seja domain.py, loader.py, ou comece com
     "_"). Cada arquivo define OU:
       - ATTACK = {...}  -> efeito instantâneo de uso único (ver
         domain.py, classe Attack). Ex: exemplo_fogo.py.
       - TURRET = {...}  -> torreta plantável no tabuleiro, com vida
         própria e disparo automático (ver domain.py, classe Turret).
         Ex: laiser.py.
  2. Se houver mais de 8 habilidades disponíveis (somando ATTACK +
     TURRET) do que slots, sorteia 8 aleatoriamente para a partida.
     Esse sorteio acontece uma vez em setup().
  3. Desenha os slots na barra (canto superior, onde na imagem de
     fundo já existem 8 espaços reservados) com o ícone de cada
     habilidade sorteada.
  4. Trata clique do mouse:
       - Slot de ATTACK: se o jogador tiver moedas suficientes,
         desconta o custo, dispara o efeito visual sobre o zumbi mais
         próximo (de toda a tela) e aplica o dano.
       - Slot de TURRET: primeiro clique SELECIONA a torreta (não
         gasta moeda ainda). Com uma torreta selecionada, o próximo
         clique numa casa livre do tabuleiro a PLANTA ali (agora sim
         descontando o custo). Clicar em outro slot troca a seleção;
         clicar fora do tabuleiro com uma torreta selecionada cancela
         a seleção.
  5. Gerencia as torretas já plantadas: cada uma dispara sozinha no
     zumbi mais próximo da SUA linha a cada `fire_interval` segundos,
     recebe dano dos zumbis que a alcançarem (ver zombies/loader.py) e
     toca a sequência de destruição + fumaça residual ao morrer.

CONTRATO COM OUTROS MÓDULOS (via context)
-------------------------------------------
Lido deste módulo:
    context["money"]              -> int, moedas atuais do jogador
                                      (criado aqui se não existir)

Lido de outros módulos (ex: system/zombies/loader.py):
    context["zombies"]            -> lista de objetos zumbi vivos,
                                      cada um esperado ter:
                                          .row        (int, linha)
                                          .x          (float, px;
                                                       menor x = mais
                                                       avançado)
                                          .y          (float, px)
                                          .alive      (bool)
                                          .take_damage(amount) -> None
                                      Ausente/vazio = ataques e
                                      torretas simplesmente não têm
                                      alvo (torretas não disparam,
                                      ataques instantâneos não gastam
                                      moeda ao clicar).

Exposto por este módulo:
    context["attacks_loaded"]     -> lista de Attack/Turret sorteados
                                      para a partida (até 8, mistos)
    context["active_effects"]     -> efeitos de ataque instantâneo
                                      voando em direção a um zumbi
    context["placed_turrets"]     -> lista de PlacedTurret no tabuleiro
                                      (outros módulos, ex. zumbis,
                                      podem ler pra saber onde há
                                      obstáculos e aplicar dano nelas
                                      via .take_damage(amount))
    context["selected_turret"]    -> Turret atualmente selecionada
                                      aguardando clique no tabuleiro,
                                      ou None

GRADE DO TABULEIRO
--------------------
5 linhas x 8 colunas. O gramado em background.png é desenhado em
perspectiva (trapézio): as bordas esquerda/direita de cada fileira
ficam mais afastadas quanto mais perto da câmera (fileiras de baixo),
então NÃO dá pra usar um retângulo simples com largura/altura de
célula fixas. A geometria abaixo (BOARD_ROW_EDGES_Y + os ajustes
lineares BOARD_LEFT_EDGE_FIT/BOARD_RIGHT_EDGE_FIT) foi calibrada
medindo, pixel a pixel, os cantos de cada fileira diretamente em
background.png (ver _cell_corners). Mesma geometria conceitual usada
por system/zombies/loader.py para saber em que célula cada zumbi
anda - se o background mudar, recalibre os dois módulos juntos.
"""

import os
import random
import importlib
import importlib.util
import traceback

import pygame

from domain import Attack, Turret


ATTACKS_DIR = os.path.dirname(os.path.abspath(__file__))
IGNORED_FILES = {"domain.py", "loader.py", "__init__.py"}
MAX_SLOTS = 8

# ---- geometria da barra de slots -----------------------------------
# Ajustada para bater com a barra desenhada no background.png (canto
# superior, entre ~x=460 e x=1160, altura ~110px). Se o seu background
# mudar de posição, ajuste só estes números.
SLOTS_AREA_X = 468
SLOTS_AREA_Y = 20
SLOT_SIZE = 82
SLOT_GAP = 6

# ---- geometria do efeito voando até o zumbi (ataques instantâneos) --
EFFECT_SPEED = 900  # pixels por segundo

# ---- geometria do tabuleiro (mesma referência de system/zombies) ----
BOARD_ROWS = 5
BOARD_COLS = 8

# Y (em pixels) de cada linha divisória horizontal do tabuleiro em
# background.png - 6 valores pra 5 fileiras (edge[r] = topo da
# fileira r, edge[r+1] = base da fileira r). Medidos diretamente na
# imagem (detecção de borda nas linhas de grade do gramado).
BOARD_ROW_EDGES_Y = [230, 342, 464, 589, 722, 867]

# O tabuleiro é um trapézio: a borda esquerda e a borda direita do
# gramado não têm x fixo, elas se deslocam conforme a fileira (y).
# Cada tupla é (a, b) de um ajuste linear x(y) = a*y + b, calibrado
# medindo os cantos esquerdo/direito de cada fileira em
# background.png e ajustando uma reta.
BOARD_LEFT_EDGE_FIT = (-0.2047, 519.75)   # left_x(y)  = a*y + b
BOARD_RIGHT_EDGE_FIT = (0.0766, 1592.82)  # right_x(y) = a*y + b


def _edge_x(y, fit):
    a, b = fit
    return a * y + b


def _row_left_x(y):
    """x da borda esquerda do gramado na altura y (leva em conta a
    perspectiva do tabuleiro)."""
    return _edge_x(y, BOARD_LEFT_EDGE_FIT)


def _row_right_x(y):
    """x da borda direita do gramado na altura y (leva em conta a
    perspectiva do tabuleiro)."""
    return _edge_x(y, BOARD_RIGHT_EDGE_FIT)


def _cell_corners(row, col):
    """Devolve os 4 cantos da célula (row, col) - (topo-esq, topo-dir,
    base-dir, base-esq), em pixels, já respeitando a perspectiva
    (trapézio) do tabuleiro desenhado em background.png. É a base de
    tudo que precisa saber "onde exatamente está essa célula na tela"
    (destaque de posicionamento, centro da célula, tamanho pra
    escalar sprite)."""
    y_top = BOARD_ROW_EDGES_Y[row]
    y_bot = BOARD_ROW_EDGES_Y[row + 1]

    left_top, right_top = _row_left_x(y_top), _row_right_x(y_top)
    left_bot, right_bot = _row_left_x(y_bot), _row_right_x(y_bot)

    col_w_top = (right_top - left_top) / BOARD_COLS
    col_w_bot = (right_bot - left_bot) / BOARD_COLS

    top_left = (left_top + col * col_w_top, y_top)
    top_right = (left_top + (col + 1) * col_w_top, y_top)
    bottom_right = (left_bot + (col + 1) * col_w_bot, y_bot)
    bottom_left = (left_bot + col * col_w_bot, y_bot)
    return top_left, top_right, bottom_right, bottom_left


def _cell_size(row, col):
    """Largura/altura aproximadas da célula (médias entre topo/base e
    entre esquerda/direita) - usadas só pra escalar sprites (torretas)
    dentro da célula, não precisa ser exata a ponto de pixel."""
    tl, tr, br, bl = _cell_corners(row, col)
    width = ((tr[0] - tl[0]) + (br[0] - bl[0])) / 2
    height = ((bl[1] - tl[1]) + (br[1] - tr[1])) / 2
    return (width, height)


def _shrink_quad(corners, factor=0.08):
    """Encolhe um quadrilátero em direção ao seu centro (uso puramente
    estético, pra deixar uma pequena margem entre o destaque e a
    linha de grade real do tile ao lado)."""
    cx = sum(p[0] for p in corners) / 4
    cy = sum(p[1] for p in corners) / 4
    return [
        (cx + (px - cx) * (1 - factor), cy + (py - cy) * (1 - factor))
        for px, py in corners
    ]


# =========================================================================
#  DESCOBERTA E CARREGAMENTO DAS HABILIDADES DISPONÍVEIS (ATTACK/TURRET)
# =========================================================================


def _discover_ability_files():
    """Lista os arquivos .py de habilidade válidos dentro desta pasta,
    em ordem alfabética (a aleatoriedade entra depois, no sorteio)."""
    if not os.path.isdir(ATTACKS_DIR):
        return []

    files = []
    for entry in sorted(os.listdir(ATTACKS_DIR)):
        if not entry.endswith(".py"):
            continue
        if entry in IGNORED_FILES or entry.startswith("_"):
            continue
        files.append(entry)
    return files


def _import_ability_module(filename):
    """Importa um arquivo de habilidade isoladamente e devolve o
    módulo importado, ou None se der erro (arquivo malformado não deve
    derrubar o jogo)."""
    ability_id = filename[:-3]  # remove ".py"
    module_name = f"attack_modules.{ability_id}"
    path = os.path.join(ATTACKS_DIR, filename)

    try:
        spec = importlib.util.spec_from_file_location(module_name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except Exception:
        print(
            f"[IF DEFENSE] Erro ao carregar habilidade '{filename}':\n"
            f"{traceback.format_exc()}"
        )
        return None


def load_available_abilities():
    """Importa todos os arquivos de habilidade válidos e devolve uma
    lista de instâncias Attack e/ou Turret já prontas (spritesheet
    carregado). Arquivos sem ATTACK nem TURRET, ou que falham ao
    importar/montar, são ignorados."""
    abilities = []
    for filename in _discover_ability_files():
        module = _import_ability_module(filename)
        if module is None:
            continue

        ability_id = filename[:-3]

        attack_data = getattr(module, "ATTACK", None)
        turret_data = getattr(module, "TURRET", None)

        if isinstance(attack_data, dict):
            try:
                abilities.append(Attack(ability_id, attack_data))
                continue
            except Exception:
                print(
                    f"[IF DEFENSE] Erro ao montar ataque '{filename}':\n"
                    f"{traceback.format_exc()}"
                )
                continue

        if isinstance(turret_data, dict):
            try:
                abilities.append(Turret(ability_id, turret_data))
                continue
            except Exception:
                print(
                    f"[IF DEFENSE] Erro ao montar torreta '{filename}':\n"
                    f"{traceback.format_exc()}"
                )
                continue

        print(
            f"[IF DEFENSE] Aviso: '{filename}' não define ATTACK nem "
            f"TURRET e será ignorado."
        )
    return abilities


def pick_abilities_for_match(all_abilities, max_slots=MAX_SLOTS):
    """Se houver mais habilidades disponíveis do que slots, sorteia
    aleatoriamente `max_slots` delas para a partida. Caso contrário,
    usa todas as disponíveis (na ordem em que foram descobertas)."""
    if len(all_abilities) <= max_slots:
        return list(all_abilities)
    return random.sample(all_abilities, max_slots)


# =========================================================================
#  EFEITO VISUAL DE UM ATAQUE INSTANTÂNEO EM VOO ATÉ O ZUMBI
# =========================================================================


class ActiveEffect:
    """Um ataque instantâneo disparado, ainda voando/animando até
    acertar o zumbi alvo. Guarda o próprio tempo decorrido (elapsed)
    para tocar a animação do spritesheet do ataque."""

    def __init__(self, attack, target_zombie, start_pos):
        self.attack = attack
        self.target = target_zombie
        self.x, self.y = start_pos
        self.elapsed = 0.0
        self.hit_applied = False

    def update(self, dt):
        self.elapsed += dt

        if self.hit_applied or self.target is None or not getattr(self.target, "alive", False):
            return

        target_x = self.target.x
        target_y = getattr(self.target, "y", self.y)

        dx = target_x - self.x
        dy = target_y - self.y
        dist = (dx ** 2 + dy ** 2) ** 0.5

        step = EFFECT_SPEED * dt
        if dist <= step or dist == 0:
            self.x, self.y = target_x, target_y
            self._apply_hit()
        else:
            self.x += dx / dist * step
            self.y += dy / dist * step

    def _apply_hit(self):
        if self.hit_applied:
            return
        self.hit_applied = True
        if self.target is not None and getattr(self.target, "alive", False):
            take_damage = getattr(self.target, "take_damage", None)
            if callable(take_damage):
                take_damage(self.attack.damage)

    def is_finished(self):
        # o efeito acaba quando o dano já foi aplicado E a animação
        # (visual) também já terminou de tocar, pra não sumir o
        # sprite abruptamente antes de completar os frames.
        return self.hit_applied and self.attack.animation.is_finished(self.elapsed)

    def draw(self, surface):
        frame = self.attack.animation.frame_at(self.elapsed)
        rect = frame.get_rect(center=(int(self.x), int(self.y)))
        surface.blit(frame, rect)


class TurretProjectile:
    """Projétil simples (efeito visual, sem sprite próprio ainda -
    ver domain deste ataque) disparado por uma torreta plantada em
    direção ao zumbi mais próximo da sua linha. Puramente visual: o
    dano já foi aplicado no instante do disparo (PlacedTurret.update),
    este objeto só anima o traço até o alvo."""

    SPEED = 1400  # pixels por segundo - mais rápido que efeitos manuais
    COLOR = (80, 220, 120)
    RADIUS = 6

    def __init__(self, start_pos, target_zombie):
        self.x, self.y = start_pos
        self.target = target_zombie
        self.finished = False

    def update(self, dt):
        if self.finished:
            return
        if self.target is None or not getattr(self.target, "alive", False):
            self.finished = True
            return

        dx = self.target.x - self.x
        dy = getattr(self.target, "y", self.y) - self.y
        dist = (dx ** 2 + dy ** 2) ** 0.5

        step = self.SPEED * dt
        if dist <= step or dist == 0:
            self.finished = True
        else:
            self.x += dx / dist * step
            self.y += dy / dist * step

    def is_finished(self):
        return self.finished

    def draw(self, surface):
        pygame.draw.circle(surface, self.COLOR, (int(self.x), int(self.y)), self.RADIUS)


# =========================================================================
#  TORRETA PLANTADA NO TABULEIRO
# =========================================================================


class PlacedTurret:
    """Uma instância de torreta (ex: Laiser) já plantada numa célula
    específica do tabuleiro. Guarda seu próprio HP, cooldown de tiro e
    estado de animação (idle -> destroy -> aftermath -> remoção)."""

    STATE_IDLE = "idle"
    STATE_DESTROYING = "destroying"
    STATE_AFTERMATH = "aftermath"
    STATE_DONE = "done"

    def __init__(self, turret_def, row, col, pos):
        self.turret_def = turret_def
        self.row = row
        self.col = col
        self.x, self.y = pos

        self.hp = turret_def.max_hp
        self.max_hp = turret_def.max_hp
        self.alive = True

        self.cooldown = 0.0
        self.state = self.STATE_IDLE
        self.state_elapsed = 0.0

    def take_damage(self, amount):
        if self.state != self.STATE_IDLE:
            return
        self.hp -= amount
        if self.hp <= 0:
            self.hp = 0
            self.alive = False
            self.state = self.STATE_DESTROYING
            self.state_elapsed = 0.0

    def _find_target(self, context):
        """Zumbi vivo mais próximo (menor x) na MESMA linha da
        torreta."""
        zombies = context.get("zombies")
        if not zombies:
            return None
        same_row_alive = [
            z for z in zombies
            if getattr(z, "alive", False) and getattr(z, "row", None) == self.row
        ]
        if not same_row_alive:
            return None
        return min(same_row_alive, key=lambda z: z.x)

    def update(self, context, dt):
        self.state_elapsed += dt

        if self.state == self.STATE_IDLE:
            self.cooldown -= dt
            if self.cooldown <= 0:
                target = self._find_target(context)
                if target is not None:
                    take_damage = getattr(target, "take_damage", None)
                    if callable(take_damage):
                        take_damage(self.turret_def.damage)
                    context.setdefault("active_effects", [])
                    context["_turret_projectiles"] = context.get("_turret_projectiles", [])
                    context["_turret_projectiles"].append(
                        TurretProjectile((self.x, self.y), target)
                    )
                    self.cooldown = self.turret_def.fire_interval

        elif self.state == self.STATE_DESTROYING:
            if self.turret_def.destroy_animation.is_finished(self.state_elapsed):
                self.state = self.STATE_AFTERMATH
                self.state_elapsed = 0.0

        elif self.state == self.STATE_AFTERMATH:
            if self.turret_def.aftermath_animation.is_finished(self.state_elapsed):
                self.state = self.STATE_DONE

    def is_done(self):
        return self.state == self.STATE_DONE

    def draw(self, surface, cell_size=None):
        if self.state == self.STATE_IDLE:
            frame = self.turret_def.idle_animation.frame_at(self.state_elapsed)
        elif self.state == self.STATE_DESTROYING:
            frame = self.turret_def.destroy_animation.frame_at(self.state_elapsed)
        else:
            frame = self.turret_def.aftermath_animation.frame_at(self.state_elapsed)

        if cell_size is not None:
            # encolhe o sprite pra caber confortavelmente dentro da
            # célula do tabuleiro (com uma margem), mantendo proporção,
            # já que o spritesheet original é maior que uma célula.
            cell_w, cell_h = cell_size
            target_size = int(min(cell_w, cell_h) * 0.85)
            frame = pygame.transform.smoothscale(frame, (target_size, target_size))

        rect = frame.get_rect(center=(int(self.x), int(self.y)))
        surface.blit(frame, rect)

        if self.state == self.STATE_IDLE:
            self._draw_health_bar(surface, rect)

    def _draw_health_bar(self, surface, sprite_rect):
        if self.hp >= self.max_hp:
            return  # não polui a tela com barra cheia
        bar_width = int(sprite_rect.width * 0.7)
        bar_height = 7
        bar_x = sprite_rect.centerx - bar_width // 2
        bar_y = sprite_rect.top - bar_height - 6

        ratio = max(0.0, self.hp / self.max_hp)
        pygame.draw.rect(surface, (60, 0, 0), (bar_x, bar_y, bar_width, bar_height), border_radius=3)
        if ratio > 0:
            fill_color = (40, 200, 40) if ratio > 0.3 else (220, 160, 30)
            pygame.draw.rect(
                surface, fill_color, (bar_x, bar_y, int(bar_width * ratio), bar_height), border_radius=3
            )
        pygame.draw.rect(surface, (10, 10, 10), (bar_x, bar_y, bar_width, bar_height), 1, border_radius=3)


# =========================================================================
#  LÓGICA DE ALVO (ataques instantâneos - qualquer zumbi na tela)
# =========================================================================


def _find_nearest_zombie(context):
    """Devolve o zumbi vivo mais próximo da casa (menor valor de x),
    entre TODOS os zumbis na tela (usado por ataques instantâneos, que
    não têm linha fixa). Se não houver lista de zumbis ainda, devolve
    None."""
    zombies = context.get("zombies")
    if not zombies:
        return None

    alive = [z for z in zombies if getattr(z, "alive", False)]
    if not alive:
        return None

    return min(alive, key=lambda z: z.x)


# =========================================================================
#  TABULEIRO: GEOMETRIA E OCUPAÇÃO
# =========================================================================


def _cell_center(row, col):
    tl, tr, br, bl = _cell_corners(row, col)
    x = (tl[0] + tr[0] + br[0] + bl[0]) / 4
    y = (tl[1] + tr[1] + br[1] + bl[1]) / 4
    return (x, y)


def _cell_at_pos(pos):
    """Devolve (row, col) da célula do tabuleiro sob a posição `pos`,
    ou None se estiver fora da área do tabuleiro. Já leva em conta a
    perspectiva (trapézio): a fileira é achada pelo y (as divisórias
    de fileira são horizontais), e dentro da fileira a borda
    esquerda/direita é interpolada pro y exato do clique antes de
    calcular a coluna."""
    x, y = pos
    if y < BOARD_ROW_EDGES_Y[0] or y > BOARD_ROW_EDGES_Y[-1]:
        return None

    row = None
    for r in range(BOARD_ROWS):
        if BOARD_ROW_EDGES_Y[r] <= y <= BOARD_ROW_EDGES_Y[r + 1]:
            row = r
            break
    if row is None:
        return None

    y_top = BOARD_ROW_EDGES_Y[row]
    y_bot = BOARD_ROW_EDGES_Y[row + 1]
    t = (y - y_top) / (y_bot - y_top) if y_bot != y_top else 0.0

    left = _row_left_x(y_top) + t * (_row_left_x(y_bot) - _row_left_x(y_top))
    right = _row_right_x(y_top) + t * (_row_right_x(y_bot) - _row_right_x(y_top))
    if x < left or x > right:
        return None

    col = int((x - left) / (right - left) * BOARD_COLS)
    col = max(0, min(col, BOARD_COLS - 1))
    return (row, col)


def _cell_is_occupied(context, row, col):
    for turret in context.get("placed_turrets", []):
        if turret.row == row and turret.col == col and turret.state != PlacedTurret.STATE_DONE:
            return True
    return False


# =========================================================================
#  SLOTS: GEOMETRIA E DESENHO
# =========================================================================


def _slot_rect(index):
    x = SLOTS_AREA_X + index * (SLOT_SIZE + SLOT_GAP)
    y = SLOTS_AREA_Y
    return pygame.Rect(x, y, SLOT_SIZE, SLOT_SIZE)


def _draw_slots(context, surface):
    abilities = context.get("attacks_loaded", [])
    money = context.get("money", 0)
    font = context.get("_atacks_font")
    selected = context.get("selected_turret")

    for index, ability in enumerate(abilities):
        rect = _slot_rect(index)
        icon = ability.icon_scaled((SLOT_SIZE - 8, SLOT_SIZE - 8))
        icon_rect = icon.get_rect(center=rect.center)
        surface.blit(icon, icon_rect)

        affordable = money >= ability.cost
        is_selected = ability is selected

        if is_selected:
            border_color = (100, 220, 255)
        elif affordable:
            border_color = (255, 215, 0)
        else:
            border_color = (120, 30, 30)
        pygame.draw.rect(surface, border_color, rect, 3, border_radius=6)

        if not affordable:
            dim = pygame.Surface(rect.size, pygame.SRCALPHA)
            dim.fill((0, 0, 0, 140))
            surface.blit(dim, rect)

        if font is not None:
            cost_label = font.render(str(ability.cost), True, (255, 255, 255))
            label_rect = cost_label.get_rect(
                midbottom=(rect.centerx, rect.bottom - 2)
            )
            shadow = font.render(str(ability.cost), True, (0, 0, 0))
            surface.blit(shadow, label_rect.move(1, 1))
            surface.blit(cost_label, label_rect)


def _slot_index_at_pos(pos, slot_count):
    for index in range(slot_count):
        if _slot_rect(index).collidepoint(pos):
            return index
    return None


# =========================================================================
#  HOOKS DO CONTRATO general_loader (setup/handle_event/update/draw)
# =========================================================================


def setup(context):
    pygame.font.init()
    context["_atacks_font"] = pygame.font.SysFont(None, 20)

    all_abilities = load_available_abilities()
    if not all_abilities:
        print(
            "[IF DEFENSE] Aviso: nenhuma habilidade válida encontrada em "
            "system/atacks/. Adicione arquivos .py com uma variável "
            "ATTACK = {...} ou TURRET = {...} (veja domain.py)."
        )

    context["attacks_loaded"] = pick_abilities_for_match(all_abilities)
    context["active_effects"] = []
    context["placed_turrets"] = []
    context["selected_turret"] = None
    context["_turret_projectiles"] = []

    if "money" not in context:
        context["money"] = 200

    print(
        f"[IF DEFENSE] {len(all_abilities)} habilidade(s) encontrada(s), "
        f"{len(context['attacks_loaded'])} sorteada(s) para a partida."
    )


def _handle_slot_click(context, ability):
    """Trata clique num slot: ataque instantâneo é resolvido na hora
    (precisa de alvo na tela); torreta apenas entra em modo "selecionada",
    aguardando o próximo clique numa célula do tabuleiro."""
    if isinstance(ability, Turret):
        # clicar de novo no mesmo slot já selecionado cancela a seleção
        if context.get("selected_turret") is ability:
            context["selected_turret"] = None
        else:
            context["selected_turret"] = ability
        return

    # ATTACK: efeito instantâneo, como antes
    money = context.get("money", 0)
    if money < ability.cost:
        return

    target = _find_nearest_zombie(context)
    if target is None:
        # sem zumbi na tela pra atacar: não gasta moeda à toa
        return

    index = context["attacks_loaded"].index(ability)
    context["money"] = money - ability.cost
    start_pos = _slot_rect(index).center
    context["active_effects"].append(ActiveEffect(ability, target, start_pos))


def _handle_board_click(context, pos):
    """Trata clique no tabuleiro enquanto há uma torreta selecionada:
    tenta plantá-la na célula clicada, se estiver livre e o jogador
    tiver moedas suficientes."""
    selected = context.get("selected_turret")
    if selected is None:
        return

    cell = _cell_at_pos(pos)
    if cell is None:
        # clique fora do tabuleiro com torreta selecionada: cancela
        context["selected_turret"] = None
        return

    row, col = cell
    if _cell_is_occupied(context, row, col):
        return  # célula ocupada, ignora silenciosamente

    money = context.get("money", 0)
    if money < selected.cost:
        return

    context["money"] = money - selected.cost
    turret = PlacedTurret(selected, row, col, _cell_center(row, col))
    context["placed_turrets"].append(turret)
    context["selected_turret"] = None


def handle_event(context, event):
    if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
        return

    abilities = context.get("attacks_loaded", [])
    slot_index = _slot_index_at_pos(event.pos, len(abilities))

    if slot_index is not None:
        _handle_slot_click(context, abilities[slot_index])
        return

    # clique fora dos slots: só importa se houver torreta selecionada
    # aguardando posicionamento no tabuleiro.
    if context.get("selected_turret") is not None:
        _handle_board_click(context, event.pos)


def update(context, dt):
    effects = context.get("active_effects", [])
    for effect in effects:
        effect.update(dt)
    context["active_effects"] = [e for e in effects if not e.is_finished()]

    turrets = context.get("placed_turrets", [])
    for turret in turrets:
        turret.update(context, dt)
    context["placed_turrets"] = [t for t in turrets if not t.is_done()]

    projectiles = context.get("_turret_projectiles", [])
    for projectile in projectiles:
        projectile.update(dt)
    context["_turret_projectiles"] = [p for p in projectiles if not p.is_finished()]


def draw(context, surface):
    for turret in context.get("placed_turrets", []):
        turret.draw(surface, cell_size=_cell_size(turret.row, turret.col))

    for projectile in context.get("_turret_projectiles", []):
        projectile.draw(surface)

    for effect in context.get("active_effects", []):
        effect.draw(surface)

    _draw_slots(context, surface)

    selected = context.get("selected_turret")
    if selected is not None:
        _draw_placement_hint(context, surface, selected)


def _draw_cell_highlight(surface, corners, fill_rgba=(100, 220, 255, 60),
                          border_color=(100, 220, 255), border_width=2):
    """Desenha um destaque preenchido + contorno sobre um quadrilátero
    qualquer (os 4 cantos de uma célula do tabuleiro, já em
    perspectiva). Só aloca uma superfície do tamanho da caixa
    delimitadora do quadrilátero, não da tela inteira."""
    xs = [p[0] for p in corners]
    ys = [p[1] for p in corners]
    min_x, min_y = min(xs), min(ys)
    width = max(1, int(max(xs) - min_x))
    height = max(1, int(max(ys) - min_y))

    local_points = [(px - min_x, py - min_y) for px, py in corners]

    patch = pygame.Surface((width, height), pygame.SRCALPHA)
    pygame.draw.polygon(patch, fill_rgba, local_points)
    pygame.draw.polygon(patch, border_color, local_points, border_width)
    surface.blit(patch, (int(min_x), int(min_y)))


def _draw_placement_hint(context, surface, selected_turret):
    """Enquanto uma torreta está selecionada aguardando ser plantada,
    destaca as células livres do tabuleiro pra deixar claro onde ela
    pode ser colocada. O destaque é desenhado como um quadrilátero
    (não um retângulo) pra se enquadrar perfeitamente na forma real de
    cada tile em background.png, incluindo a perspectiva das
    fileiras mais próximas da câmera."""
    for row in range(BOARD_ROWS):
        for col in range(BOARD_COLS):
            if _cell_is_occupied(context, row, col):
                continue
            corners = _shrink_quad(_cell_corners(row, col))
            _draw_cell_highlight(surface, corners)