# -*- coding: utf-8 -*-
"""
IF DEFENSE - classic_mode/loader_mode.py
==========================================
Ponto de entrada do modo clássico. Este arquivo é autocontido: ele
mesmo inicializa o pygame, abre a janela, carrega o fundo do jogo
(assets/backgroundgame.png) e roda o loop principal - não depende do
sistema de hooks genérico do general_loader.py, que apenas descobre
este arquivo e chama run() (ver system/general_loader.py, GAME_MODES).

O QUE ESTE ARQUIVO FAZ
------------------------
1. Abre a janela do jogo e desenha tudo numa superfície "virtual" do
   tamanho ORIGINAL do fundo (ver WINDOW_SIZE mais abaixo).
2. Reaproveita system/attacks/loader.py (slots de ataque/torreta,
   cliques, custo em moedas). Ele lê/escreve context["money"].
3. HUD:
     - canto superior ESQUERDO: total de moedas do jogador;
     - canto superior DIREITO: ondas geradas / total de ondas (0/N).
4. Fases (classic_mode/fases/fase1.json, fase2.json, ...): cada fase
   define moedas iniciais, total de zumbis, velocidade dos zumbis (em
   blocos por segundo) e total de ondas. Quando as ondas acabam e não
   sobra nenhum zumbi vivo, o jogo carrega a fase seguinte. Sem mais
   fases, mostra a tela de vitória.
5. Zumbis: todos os tipos definidos em system/zumbi/loader_zumbis.py
   são carregados; a cada onda, cada zumbi nasce numa linha aleatória
   do tabuleiro e anda até a casa (lado esquerdo).
6. Cada zumbi morto rende KILL_REWARD moedas (+40).
7. Se um zumbi chegar à casa: game over (assets/gameover.png +
   assets/GAMEOVER.mp3).

FORMATO DE classic_mode/fases/faseN.json
-------------------------------------------
    {
      "moedas_iniciais": 200,
      "total_zumbis": 12,
      "velocidade_zumbis": 0.25,
      "total_ondas": 4,
      "intervalo_ondas": 12
    }
"intervalo_ondas" (segundos entre ondas) é opcional. Os zumbis do
total são divididos igualmente entre as ondas (a sobra vai pras
primeiras). Os nomes das chaves aceitam também as variações listadas
em PHASE_KEYS.

CONTRATO COM system/zumbi/loader_zumbis.py
---------------------------------------------
O arquivo pode expor os tipos de zumbi por qualquer um destes nomes:
    load_available_zombies() / load_zombies() /
    load_available_zumbis()  / load_zumbis()   -> lista (ou dict)
    ZOMBIES / ZUMBIS                           -> lista (ou dict)
Cada item pode ser:
    - dict com dados (hp/vida, damage/dano, color)  -> zumbi básico;
    - classe/função chamável, criada com (row=, x=, y=, speed=);
    - objeto com método spawn(row=, x=, y=, speed=).
O zumbi criado deve ter .row, .x, .y, .alive, .take_damage(amount) e,
opcionalmente, .update(context, dt) ou .update(dt), .draw(surface) e
.is_done() (para tocar animação de morte antes de sumir). Sem
.update(), este módulo o move (velocidade em pixels/s no atributo
.speed) e faz o zumbi parar e atacar torretas à frente. Se o arquivo
não existir, um zumbi básico é usado, pra o jogo continuar jogável.
"""

import importlib.util
import inspect
import json
import os
import random
import sys
import traceback

import pygame


CLASSIC_MODE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(CLASSIC_MODE_DIR)
SYSTEM_DIR = os.path.join(PROJECT_DIR, "system")
ATTACKS_DIR = os.path.join(SYSTEM_DIR, "attacks")
ZOMBIES_DIR = os.path.join(SYSTEM_DIR, "zumbi")
ASSETS_DIR = os.path.join(PROJECT_DIR, "assets")
PHASES_DIR = os.path.join(CLASSIC_MODE_DIR, "fases")

BACKGROUND_PATH = os.path.join(ASSETS_DIR, "backgroundgame.png")
MUSIC_PATH = os.path.join(ASSETS_DIR, "TIMER1.mp3")
GAMEOVER_IMAGE_PATH = os.path.join(ASSETS_DIR, "gameover.png")
GAMEOVER_MUSIC_PATH = os.path.join(ASSETS_DIR, "GAMEOVER.mp3")
ZOMBIES_LOADER_PATH = os.path.join(ZOMBIES_DIR, "loader_zumbis.py")

FPS = 60

# ---- janela do jogo -----------------------------------------------------
# A janela é sempre 1280x720 (cabe em qualquer tela comum). O fundo e
# todos os elementos (slots, campo, zumbis) são desenhados numa
# superfície "virtual" do tamanho ORIGINAL do backgroundgame.png -
# mesmo espaço de coordenadas em que os slots já foram calibrados em
# system/attacks/loader.py (SLOTS_AREA_X/Y, SLOT_SIZE etc.) - e essa
# superfície inteira é escalada de uma vez só para a janela real. Isso
# evita ter que recalibrar cada coordenada manualmente: tudo continua
# no mesmo lugar relativo, só menor.
WINDOW_SIZE = (1280, 720)

# ---- regras do jogo -------------------------------------------------------
KILL_REWARD = 40            # moedas ganhas por zumbi morto
FIRST_WAVE_DELAY = 3.0      # segundos até a 1ª onda de cada fase
DEFAULT_WAVE_INTERVAL = 12.0
PHASE_BANNER_TIME = 2.5     # segundos mostrando "FASE N" ao começar
BITE_RANGE = 70             # px: distância em que o zumbi ataca uma torreta

# ---- posições do HUD (espaço virtual, calibradas no backgroundgame.png) --
COIN_TEXT_MIDRIGHT = (292, 56)   # número de moedas, encostado antes do "$"
WAVE_TEXT_CENTER = (1523, 93)    # "0/N", na caixa escura abaixo de "ONDA"

# ---- fase padrão (usada se classic_mode/fases/fase1.json não existir) ----
DEFAULT_PHASE = {
    "coins": 200,
    "total_zombies": 10,
    "speed": 0.15,
    "total_waves": 3,
    "wave_interval": DEFAULT_WAVE_INTERVAL,
}

PHASE_KEYS = {
    "coins": ("moedas_iniciais", "moedas", "coins", "start_coins"),
    "total_zombies": ("total_zumbis", "zumbis", "total_zombies", "zombies"),
    "speed": ("velocidade_zumbis", "velocidade", "speed", "zombie_speed"),
    "total_waves": ("total_ondas", "ondas", "total_waves", "waves"),
    "wave_interval": ("intervalo_ondas", "intervalo", "wave_interval"),
}

ZOMBIE_LOADER_FUNCTIONS = (
    "load_available_zombies",
    "load_available_zumbis",
    "load_zombies",
    "load_zumbis",
)
ZOMBIE_LOADER_CONSTANTS = ("ZOMBIES", "ZUMBIS")


# =========================================================================
#  CARREGAMENTO DO FUNDO E ÁUDIO
# =========================================================================


def _load_background(fallback_size):
    """Carrega assets/backgroundgame.png. Se não existir (projeto ainda
    incompleto, ou rodando num ambiente sem os assets), gera um fundo
    verde liso do tamanho padrão, pra não travar o jogo."""
    if os.path.isfile(BACKGROUND_PATH):
        try:
            image = pygame.image.load(BACKGROUND_PATH).convert()
            return image
        except Exception:
            print(f"[IF DEFENSE] Erro ao carregar '{BACKGROUND_PATH}', usando fundo padrão.")

    surface = pygame.Surface(fallback_size)
    surface.fill((40, 110, 40))
    return surface


def _play_background_music(music_path, loops=-1):
    """Para qualquer áudio anterior e inicia o novo áudio (em loop por
    padrão; loops=0 toca uma vez só)."""
    if os.path.isfile(music_path):
        try:
            pygame.mixer.music.stop()
            pygame.mixer.music.load(music_path)
            pygame.mixer.music.play(loops=loops)
        except Exception as e:
            print(f"[IF DEFENSE] Erro ao carregar a música '{music_path}': {e}")
    else:
        print(f"[IF DEFENSE] Aviso: Música '{music_path}' não encontrada.")


# =========================================================================
#  IMPORTAÇÃO DO MÓDULO DE ATAQUES (system/attacks/loader.py + domain.py)
# =========================================================================


def _import_attacks_module():
    """Importa system/attacks/loader.py isoladamente. Esse loader.py
    faz `from domain import Attack`, então system/attacks/ precisa
    estar no sys.path antes de importá-lo, pra ele achar domain.py
    como import de nível de módulo."""
    if ATTACKS_DIR not in sys.path:
        sys.path.insert(0, ATTACKS_DIR)

    loader_path = os.path.join(ATTACKS_DIR, "loader.py")
    if not os.path.isfile(loader_path):
        print(
            f"[IF DEFENSE] Aviso: '{loader_path}' não encontrado. "
            f"Nenhum ataque será carregado."
        )
        return None

    spec = importlib.util.spec_from_file_location("attacks_module", loader_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["attacks_module"] = module
    spec.loader.exec_module(module)
    return module


# =========================================================================
#  CONVERSÃO DE COORDENADAS (janela real -> superfície virtual)
# =========================================================================


def _rescale_event_pos(event, scale_x, scale_y):
    """Devolve uma cópia do evento com .pos (e .rel, se houver)
    convertidos de coordenadas da janela real para coordenadas da
    superfície virtual, usando os fatores de escala calculados a
    partir do tamanho do fundo. Eventos sem posição (teclado, etc.)
    voltam inalterados."""
    if not hasattr(event, "pos"):
        return event

    new_pos = (int(event.pos[0] * scale_x), int(event.pos[1] * scale_y))
    kwargs = {"pos": new_pos}

    if hasattr(event, "rel"):
        kwargs["rel"] = (int(event.rel[0] * scale_x), int(event.rel[1] * scale_y))
    if hasattr(event, "button"):
        kwargs["button"] = event.button
    if hasattr(event, "buttons"):
        kwargs["buttons"] = event.buttons

    return pygame.event.Event(event.type, **kwargs)


# =========================================================================
#  FASES (classic_mode/fases/faseN.json)
# =========================================================================


def _first_key(data, keys, default=None):
    """Primeiro valor encontrado em `data` entre as chaves `keys`."""
    for key in keys:
        if key in data:
            return data[key]
    return default


def load_phase(number):
    """Lê classic_mode/fases/fase{number}.json e devolve um dict
    normalizado (coins, total_zombies, speed, total_waves,
    wave_interval, number). Devolve None se o arquivo não existir ou
    for inválido."""
    path = os.path.join(PHASES_DIR, f"fase{number}.json")
    if not os.path.isfile(path):
        return None

    try:
        with open(path, "r", encoding="utf-8") as file:
            raw = json.load(file)

        phase = dict(DEFAULT_PHASE)
        for key, aliases in PHASE_KEYS.items():
            phase[key] = _first_key(raw, aliases, phase[key])

        phase["coins"] = max(0, int(phase["coins"]))
        phase["total_zombies"] = max(0, int(phase["total_zombies"]))
        phase["total_waves"] = max(1, int(phase["total_waves"]))
        phase["speed"] = max(0.0, float(phase["speed"]))
        phase["wave_interval"] = max(0.5, float(phase["wave_interval"]))
    except Exception:
        print(f"[IF DEFENSE] Erro ao ler '{path}':\n{traceback.format_exc()}")
        return None

    phase["number"] = number
    return phase


# =========================================================================
#  TABULEIRO (geometria compartilhada com system/attacks/loader.py)
# =========================================================================


class Board:
    """Geometria do tabuleiro em perspectiva. Usa as funções de
    system/attacks/loader.py (a mesma calibração usada pra plantar
    torretas), pra zumbis e torretas nunca ficarem dessincronizados.
    Se o loader de ataques não estiver disponível, usa uma cópia da
    mesma calibração."""

    _EDGES_Y = [230, 342, 464, 589, 722, 867]
    _LEFT_FIT = (-0.2047, 519.75)
    _RIGHT_FIT = (0.0766, 1592.82)

    def __init__(self, attacks_module):
        left = getattr(attacks_module, "_row_left_x", None)
        right = getattr(attacks_module, "_row_right_x", None)
        center = getattr(attacks_module, "_cell_center", None)

        if callable(left) and callable(right) and callable(center):
            self.rows = getattr(attacks_module, "BOARD_ROWS", 5)
            self.cols = getattr(attacks_module, "BOARD_COLS", 8)
            self._left, self._right, self._center = left, right, center
        else:
            self.rows, self.cols = 5, 8
            self._left = lambda y: self._LEFT_FIT[0] * y + self._LEFT_FIT[1]
            self._right = lambda y: self._RIGHT_FIT[0] * y + self._RIGHT_FIT[1]
            self._center = self._fallback_center

    def _fallback_center(self, row, col):
        return (0, (self._EDGES_Y[row] + self._EDGES_Y[row + 1]) / 2)

    def row_center_y(self, row):
        return self._center(row, 0)[1]

    def left_x(self, row):
        """x da borda esquerda do gramado (onde fica a casa)."""
        return self._left(self.row_center_y(row))

    def right_x(self, row):
        return self._right(self.row_center_y(row))

    def col_width(self, row):
        return (self.right_x(row) - self.left_x(row)) / self.cols

    def spawn_x(self, row):
        """Logo fora da borda direita do gramado."""
        return self.right_x(row) + self.col_width(row) * 0.8


# =========================================================================
#  ZUMBIS
# =========================================================================


class BuiltinZombie:
    """Zumbi básico, usado quando loader_zumbis.py entrega só dados
    (dict) ou quando o arquivo não existe. Desenho provisório."""

    WIDTH = 64
    HEIGHT = 104

    def __init__(self, data, row, x, y, speed):
        self.data = data
        self.row = row
        self.x = float(x)
        self.y = float(y)
        self.speed = speed  # pixels por segundo
        self.max_hp = float(_first_key(data, ("hp", "vida", "health"), 100))
        self.hp = self.max_hp
        self.damage = float(_first_key(data, ("damage", "dano"), 20))  # dano/s em torretas
        self.color = tuple(data.get("color", (110, 140, 110)))
        self.alive = True

    def take_damage(self, amount):
        if not self.alive:
            return
        self.hp -= amount
        if self.hp <= 0:
            self.hp = 0
            self.alive = False

    def is_done(self):
        return not self.alive

    def draw(self, surface):
        body = pygame.Rect(0, 0, self.WIDTH, self.HEIGHT)
        body.midbottom = (int(self.x), int(self.y) + self.HEIGHT // 2)
        pygame.draw.ellipse(surface, self.color, body)
        pygame.draw.ellipse(surface, (20, 30, 20), body, 3)
        for eye_dx in (-10, 10):
            pygame.draw.circle(surface, (240, 240, 230), (body.centerx + eye_dx, body.top + 30), 7)
            pygame.draw.circle(surface, (20, 20, 20), (body.centerx + eye_dx - 2, body.top + 31), 3)

        bar_w = self.WIDTH
        bar = pygame.Rect(body.left, body.top - 12, bar_w, 6)
        pygame.draw.rect(surface, (60, 0, 0), bar)
        pygame.draw.rect(surface, (40, 200, 40), (bar.x, bar.y, int(bar_w * self.hp / self.max_hp), bar.h))


def _as_list(found):
    if isinstance(found, dict):
        return list(found.values())
    return list(found or [])


def _extract_zombie_templates(module):
    """Descobre os tipos de zumbi expostos pelo módulo (ver contrato no
    topo do arquivo)."""
    for name in ZOMBIE_LOADER_FUNCTIONS:
        function = getattr(module, name, None)
        if callable(function):
            try:
                return _as_list(function())
            except Exception:
                print(f"[IF DEFENSE] Erro em {name}():\n{traceback.format_exc()}")
                return []

    for name in ZOMBIE_LOADER_CONSTANTS:
        if hasattr(module, name):
            return _as_list(getattr(module, name))

    print(
        "[IF DEFENSE] Aviso: loader_zumbis.py não expõe nenhum tipo de zumbi "
        f"({', '.join(ZOMBIE_LOADER_FUNCTIONS + ZOMBIE_LOADER_CONSTANTS)})."
    )
    return []


def _import_zombie_templates():
    """Importa system/zumbi/loader_zumbis.py e devolve a lista de tipos
    de zumbi. Devolve [] se o arquivo não existir ou falhar."""
    if not os.path.isfile(ZOMBIES_LOADER_PATH):
        print(f"[IF DEFENSE] Aviso: '{ZOMBIES_LOADER_PATH}' não encontrado. Usando zumbi básico.")
        return []

    # Ataques e zumbis podem ter, cada um, um domain.py próprio. O
    # `import domain` guarda o primeiro em sys.modules, então o do
    # ataque é retirado durante este import e devolvido no final.
    attacks_domain = sys.modules.pop("domain", None)
    sys.path.insert(0, ZOMBIES_DIR)
    try:
        spec = importlib.util.spec_from_file_location("zombies_module", ZOMBIES_LOADER_PATH)
        module = importlib.util.module_from_spec(spec)
        sys.modules["zombies_module"] = module
        spec.loader.exec_module(module)
        return _extract_zombie_templates(module)
    except Exception:
        print(f"[IF DEFENSE] Erro ao carregar loader_zumbis.py:\n{traceback.format_exc()}")
        return []
    finally:
        if ZOMBIES_DIR in sys.path:
            sys.path.remove(ZOMBIES_DIR)
        zombies_domain = sys.modules.pop("domain", None)
        if zombies_domain is not None:
            sys.modules["zombies_domain"] = zombies_domain
        if attacks_domain is not None:
            sys.modules["domain"] = attacks_domain


def _spawn_zombie(template, row, x, y, speed_px):
    """Cria uma instância de zumbi a partir de um tipo (ver contrato no
    topo do arquivo). Devolve None se não conseguir."""
    if isinstance(template, dict):
        return BuiltinZombie(template, row, x, y, speed_px)

    factory = getattr(template, "spawn", None)
    if not callable(factory):
        factory = template if callable(template) else None
    if factory is None:
        return None

    attempts = (
        ((), {"row": row, "x": x, "y": y, "speed": speed_px}),
        ((row, x, y), {}),
        ((), {}),
    )
    zombie = None
    for args, kwargs in attempts:
        try:
            zombie = factory(*args, **kwargs)
            break
        except TypeError:
            continue

    if zombie is None:
        print(f"[IF DEFENSE] Aviso: não consegui criar um zumbi a partir de {template!r}.")
        return None

    # garante posição/velocidade da onda, mesmo que o construtor ignore
    for name, value in (("row", row), ("x", x), ("y", y), ("speed", speed_px)):
        try:
            setattr(zombie, name, value)
        except AttributeError:
            pass
    if not hasattr(zombie, "alive"):
        zombie.alive = True
    return zombie


def _call_update(zombie, context, dt):
    """Chama zombie.update(context, dt) ou zombie.update(dt), conforme
    a assinatura do método."""
    update = zombie.update
    try:
        params = inspect.signature(update).parameters
    except (TypeError, ValueError):
        params = ()
    if len(params) >= 2:
        update(context, dt)
    else:
        update(dt)


def _advance_zombie(context, zombie, dt):
    """Movimento padrão: anda para a esquerda; se houver torreta viva
    logo à frente (mesma linha), para e a ataca."""
    for turret in context.get("placed_turrets", []):
        if turret.row != zombie.row or not getattr(turret, "alive", False):
            continue
        if 0 <= zombie.x - turret.x <= BITE_RANGE:
            turret.take_damage(getattr(zombie, "damage", 20) * dt)
            return
    zombie.x -= zombie.speed * dt


# =========================================================================
#  CONTROLE DE FASES, ONDAS, MOEDAS E HUD
# =========================================================================


def _make_font(size):
    return pygame.font.SysFont("arial,dejavusans", size, bold=True)


def _blit_text(surface, font, text, color, **anchor):
    """Desenha `text` com sombra. `anchor` é um kwarg do Rect
    (center=..., midright=...)."""
    label = font.render(text, True, color)
    rect = label.get_rect(**anchor)
    surface.blit(font.render(text, True, (0, 0, 0)), rect.move(2, 2))
    surface.blit(label, rect)


class PhaseController:
    STATE_PLAYING = "playing"
    STATE_GAME_OVER = "game_over"
    STATE_VICTORY = "victory"

    def __init__(self, context, board, templates):
        self.context = context
        self.board = board
        self.templates = templates or [{"nome": "Zumbi", "hp": 100}]
        self.state = self.STATE_PLAYING

        self.zombies = []
        context["zombies"] = self.zombies  # lido por system/attacks/loader.py
        self._rewarded = set()

        self.phase = None
        self.wave_counts = []
        self.waves_spawned = 0
        self.wave_timer = 0.0
        self.banner_timer = 0.0

        self.font_money = _make_font(44)
        self.font_wave = _make_font(40)
        self.font_banner = _make_font(110)

    # ---- fases ---------------------------------------------------------

    def start_phase(self, number):
        """Carrega faseN.json e reinicia o campo. Sem o arquivo: a
        fase 1 usa DEFAULT_PHASE; as seguintes encerram o jogo com
        vitória."""
        phase = load_phase(number)
        if phase is None:
            if number != 1:
                self.state = self.STATE_VICTORY
                return False
            print(f"[IF DEFENSE] Aviso: fase1.json não encontrada em '{PHASES_DIR}'. Usando fase padrão.")
            phase = dict(DEFAULT_PHASE, number=1)

        self.phase = phase
        ctx = self.context
        ctx["money"] = phase["coins"]
        ctx["placed_turrets"] = []
        ctx["active_effects"] = []
        ctx["_turret_projectiles"] = []
        ctx["selected_turret"] = None
        self.zombies.clear()
        self._rewarded.clear()

        base, extra = divmod(phase["total_zombies"], phase["total_waves"])
        self.wave_counts = [base + (1 if i < extra else 0) for i in range(phase["total_waves"])]
        self.waves_spawned = 0
        self.wave_timer = FIRST_WAVE_DELAY
        self.banner_timer = PHASE_BANNER_TIME
        return True

    # ---- ondas e zumbis -------------------------------------------------

    def _spawn_wave(self, count):
        """Cria `count` zumbis, cada um numa linha aleatória. Zumbis
        que caem na mesma linha nascem um atrás do outro."""
        board = self.board
        queue_in_row = {}
        for _ in range(count):
            row = random.randrange(board.rows)
            col_w = board.col_width(row)
            position_in_queue = queue_in_row.get(row, 0)
            queue_in_row[row] = position_in_queue + 1

            zombie = _spawn_zombie(
                random.choice(self.templates),
                row,
                board.spawn_x(row) + position_in_queue * col_w * 0.9,
                board.row_center_y(row),
                self.phase["speed"] * col_w,  # blocos/s -> pixels/s
            )
            if zombie is not None:
                self.zombies.append(zombie)

    def _update_waves(self, dt):
        if self.waves_spawned >= len(self.wave_counts):
            return
        self.wave_timer -= dt
        if self.wave_timer <= 0:
            self._spawn_wave(self.wave_counts[self.waves_spawned])
            self.waves_spawned += 1
            self.wave_timer = self.phase["wave_interval"]

    def _update_zombies(self, dt):
        for zombie in list(self.zombies):
            if callable(getattr(zombie, "update", None)):
                _call_update(zombie, self.context, dt)
            elif zombie.alive:
                _advance_zombie(self.context, zombie, dt)

            if zombie.alive:
                continue

            if id(zombie) not in self._rewarded:  # recompensa uma única vez
                self._rewarded.add(id(zombie))
                self.context["money"] = self.context.get("money", 0) + KILL_REWARD

            is_done = getattr(zombie, "is_done", None)
            if not callable(is_done) or is_done():
                self.zombies.remove(zombie)
                self._rewarded.discard(id(zombie))

    def _zombie_reached_house(self):
        return any(
            z.alive and z.x <= self.board.left_x(min(max(z.row, 0), self.board.rows - 1))
            for z in self.zombies
        )

    def _phase_cleared(self):
        return self.waves_spawned >= len(self.wave_counts) and not self.zombies

    # ---- hooks do loop ---------------------------------------------------

    def update(self, dt):
        if self.state != self.STATE_PLAYING:
            return
        self.banner_timer = max(0.0, self.banner_timer - dt)
        self._update_waves(dt)
        self._update_zombies(dt)

        if self._zombie_reached_house():
            self.state = self.STATE_GAME_OVER
        elif self._phase_cleared():
            self.start_phase(self.phase["number"] + 1)

    def draw_zombies(self, surface):
        for zombie in sorted(self.zombies, key=lambda z: getattr(z, "y", 0)):
            draw = getattr(zombie, "draw", None)
            if callable(draw):
                draw(surface)

    def draw_hud(self, surface):
        white = (255, 255, 255)

        _blit_text(surface, self.font_money, str(self.context.get("money", 0)), white,
                   midright=COIN_TEXT_MIDRIGHT)

        if self.phase is not None:
            _blit_text(surface, self.font_wave, f"{self.waves_spawned}/{len(self.wave_counts)}", white,
                       center=WAVE_TEXT_CENTER)

        width, height = surface.get_size()
        if self.state == self.STATE_PLAYING and self.banner_timer > 0 and self.phase is not None:
            _blit_text(surface, self.font_banner, f"FASE {self.phase['number']}", (255, 215, 0),
                       center=(width // 2, int(height * 0.45)))

        if self.state == self.STATE_VICTORY:
            dim = pygame.Surface((width, height), pygame.SRCALPHA)
            dim.fill((0, 0, 0, 150))
            surface.blit(dim, (0, 0))
            _blit_text(surface, self.font_banner, "VOCÊ VENCEU!", (255, 215, 0),
                       center=(width // 2, height // 2))


# =========================================================================
#  GAME OVER
# =========================================================================


def _start_game_over(window_size):
    """Troca a música pela de game over (toca uma vez) e devolve a
    superfície da tela de game over, já no tamanho da janela."""
    _play_background_music(GAMEOVER_MUSIC_PATH, loops=0)

    if os.path.isfile(GAMEOVER_IMAGE_PATH):
        try:
            image = pygame.image.load(GAMEOVER_IMAGE_PATH).convert_alpha()
            return pygame.transform.smoothscale(image, window_size)
        except Exception:
            print(f"[IF DEFENSE] Erro ao carregar '{GAMEOVER_IMAGE_PATH}', usando tela padrão.")
    else:
        print(f"[IF DEFENSE] Aviso: '{GAMEOVER_IMAGE_PATH}' não encontrada.")

    surface = pygame.Surface(window_size)
    surface.fill((10, 0, 0))
    _blit_text(surface, _make_font(120), "GAME OVER", (200, 20, 20),
               center=(window_size[0] // 2, window_size[1] // 2))
    return surface


# =========================================================================
#  PONTO DE ENTRADA (chamado pelo general_loader.py quando game_mode == 0)
# =========================================================================


def run():
    pygame.init()
    if not pygame.mixer.get_init():
        pygame.mixer.init()

    _play_background_music(MUSIC_PATH)

    screen = pygame.display.set_mode(WINDOW_SIZE)
    pygame.display.set_caption("IF DEFENSE - Modo Clássico")
    clock = pygame.time.Clock()

    # fundo carregado no seu tamanho ORIGINAL - é também o tamanho da
    # superfície virtual onde tudo é desenhado antes de escalar pra
    # janela real.
    background = _load_background(fallback_size=WINDOW_SIZE)
    virtual_size = background.get_size()
    virtual_surface = pygame.Surface(virtual_size)

    # fator de escala pra converter posição do mouse (coordenadas da
    # janela real) para coordenadas da superfície virtual, já que os
    # slots em system/attacks/loader.py testam clique nesse espaço
    # virtual.
    scale_x = virtual_size[0] / WINDOW_SIZE[0]
    scale_y = virtual_size[1] / WINDOW_SIZE[1]

    attacks_module = _import_attacks_module()

    # context compartilhado, no mesmo espírito do general_loader.py:
    # qualquer módulo plugado aqui (ataques, zumbis, HUD, etc.)
    # lê/escreve livremente nessas chaves. width/height refletem o
    # espaço VIRTUAL (tamanho do fundo), não o da janela real, já que
    # é nesse espaço que os módulos desenham e calculam posições.
    context = {
        "screen": virtual_surface,
        "width": virtual_size[0],
        "height": virtual_size[1],
        "clock": clock,
        "running": True,
    }

    if attacks_module is not None:
        setup = getattr(attacks_module, "setup", None)
        if callable(setup):
            setup(context)

    # depois do setup dos ataques (que já importou o domain.py deles)
    controller = PhaseController(context, Board(attacks_module), _import_zombie_templates())
    controller.start_phase(1)

    game_over_screen = None

    try:
        while context.get("running", True):
            dt = clock.tick(FPS) / 1000.0
            game_over = controller.state == PhaseController.STATE_GAME_OVER

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    context["running"] = False

                # eventos de mouse chegam em coordenadas da janela
                # real (1280x720) - convertidos pro espaço virtual
                # antes de repassar, senão o teste de clique nos
                # slots (calibrado no espaço virtual) erra a posição.
                event = _rescale_event_pos(event, scale_x, scale_y)

                if attacks_module is not None and not game_over:
                    handle_event = getattr(attacks_module, "handle_event", None)
                    if callable(handle_event):
                        handle_event(context, event)

            if not game_over:
                if attacks_module is not None:
                    update = getattr(attacks_module, "update", None)
                    if callable(update):
                        update(context, dt)
                controller.update(dt)

            virtual_surface.blit(background, (0, 0))
            controller.draw_zombies(virtual_surface)

            if attacks_module is not None:
                draw = getattr(attacks_module, "draw", None)
                if callable(draw):
                    draw(context, virtual_surface)

            controller.draw_hud(virtual_surface)

            # escala a superfície virtual inteira de uma vez pra
            # janela real - é o único lugar onde a escala acontece,
            # então nada dentro do jogo precisa saber sobre isso.
            pygame.transform.smoothscale(virtual_surface, WINDOW_SIZE, screen)

            if controller.state == PhaseController.STATE_GAME_OVER:
                if game_over_screen is None:
                    game_over_screen = _start_game_over(WINDOW_SIZE)
                screen.blit(game_over_screen, (0, 0))

            pygame.display.flip()
    finally:
        if attacks_module is not None:
            teardown = getattr(attacks_module, "teardown", None)
            if callable(teardown):
                teardown(context)
        pygame.quit()


if __name__ == "__main__":
    # permite testar este modo isoladamente: python classic_mode/loader_mode.py
    run()