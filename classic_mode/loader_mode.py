# -*- coding: utf-8 -*-
"""
IF DEFENSE - classic_mode/loader_mode.py
==========================================
Ponto de entrada do modo clássico. Este arquivo é autocontido: ele
mesmo inicializa o pygame, abre a janela, carrega o fundo do jogo
(assets/backgroundgame.png) e roda o loop principal - não depende do
sistema de hooks genérico do general_loader.py, que apenas descobre
este arquivo e chama run() (ver system/general_loader.py, GAME_MODES).

O QUE ESTE ARQUIVO FAZ NESTA ETAPA
-------------------------------------
1. Abre a janela do jogo, do mesmo tamanho da imagem de fundo
   (assets/backgroundgame.png), pra não distorcer nem desalinhar os
   8 espaços de slot já desenhados na própria arte do fundo.
2. Importa e reaproveita system/attacks/loader.py e domain.py (já
   existentes): eles descobrem os arquivos de ataque em
   system/attacks/, sorteiam até 8 quando há mais que isso disponível,
   e sabem desenhar os ícones nos slots / tratar clique.
3. Roda um loop pygame simples: desenha o fundo, depois deixa o
   loader.py de ataques desenhar os slots por cima, e repassa eventos
   de mouse pra ele tratar clique/custo em moedas.

O que ainda NÃO está aqui (fica pra próxima etapa, quando você pedir):
zumbis, HUD de dinheiro, tela de derrota, etc. Este arquivo já reserva
o campo pra esses módulos serem plugados do mesmo jeito (basta importar
e chamar os hooks, como já é feito com o loader.py de ataques).
"""

import os
import sys

import pygame


CLASSIC_MODE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(CLASSIC_MODE_DIR)
SYSTEM_DIR = os.path.join(PROJECT_DIR, "system")
ATTACKS_DIR = os.path.join(SYSTEM_DIR, "attacks")
ASSETS_DIR = os.path.join(PROJECT_DIR, "assets")

BACKGROUND_PATH = os.path.join(ASSETS_DIR, "backgroundgame.png")
MUSIC_PATH = os.path.join(ASSETS_DIR, "TIMER1.mp3")

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


def _play_background_music(music_path):
    """Para qualquer áudio anterior e inicia o novo áudio em loop."""
    if os.path.isfile(music_path):
        try:
            pygame.mixer.music.stop()
            pygame.mixer.music.load(music_path)
            pygame.mixer.music.play(loops=-1)
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

    import importlib.util

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
    # qualquer módulo plugado aqui (ataques, e futuramente zumbis, HUD,
    # etc.) lê/escreve livremente nessas chaves. width/height refletem
    # o espaço VIRTUAL (tamanho do fundo), não o da janela real, já
    # que é nesse espaço que os módulos desenham e calculam posições.
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

    try:
        while context.get("running", True):
            dt = clock.tick(FPS) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    context["running"] = False

                # eventos de mouse chegam em coordenadas da janela
                # real (1280x720) - convertidos pro espaço virtual
                # antes de repassar, senão o teste de clique nos
                # slots (calibrado no espaço virtual) erra a posição.
                event = _rescale_event_pos(event, scale_x, scale_y)

                if attacks_module is not None:
                    handle_event = getattr(attacks_module, "handle_event", None)
                    if callable(handle_event):
                        handle_event(context, event)

            if attacks_module is not None:
                update = getattr(attacks_module, "update", None)
                if callable(update):
                    update(context, dt)

            virtual_surface.blit(background, (0, 0))

            if attacks_module is not None:
                draw = getattr(attacks_module, "draw", None)
                if callable(draw):
                    draw(context, virtual_surface)

            # escala a superfície virtual inteira de uma vez pra
            # janela real - é o único lugar onde a escala acontece,
            # então nada dentro do jogo precisa saber sobre isso.
            pygame.transform.smoothscale(virtual_surface, WINDOW_SIZE, screen)
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