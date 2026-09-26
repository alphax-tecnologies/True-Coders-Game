# -*- coding: utf-8 -*-
"""
IF DEFENSE - system/general_loader.py
=======================================
Este arquivo é o "montador" do jogo: ele varre TODAS as subpastas
dentro de system/, procura em cada uma por um arquivo chamado
"loader.py" e, se encontrar, importa esse módulo e guarda seu
conteúdo. Ao final, tudo que foi carregado é reunido e exposto através
da função run_game(), que é o ponto de entrada chamado por main.py.

Isso permite organizar o jogo em módulos independentes, um por
subpasta, sem que main.py precise saber quantos módulos existem ou
onde estão:

    system/
        general_loader.py      <- este arquivo
        player/
            loader.py
        enemies/
            loader.py
        waves/
            loader.py
        ui/
            loader.py
        ...

CONTRATO DE CADA "loader.py"
-----------------------------
Cada loader.py encontrado é totalmente opcional em relação ao que
define, mas para ser aproveitado pelo general_loader ele pode (não é
obrigatório usar todos) expor:

    - setup(context) -> None
        Chamada UMA VEZ, na ordem em que as subpastas foram
        encontradas (ordem alfabética), antes do jogo começar a
        rodar. Útil para registrar classes, carregar assets do
        próprio módulo, inicializar variáveis, etc. Recebe um dict
        "context" compartilhado entre todos os módulos - qualquer
        módulo pode ler/gravar chaves nesse dict pra se comunicar
        com os outros (ex.: context["player"] = Player(...)).

    - update(context, dt) -> None
        Chamada a cada frame do loop principal do jogo, na mesma
        ordem em que os módulos foram carregados. "dt" é o tempo em
        segundos desde o último frame.

    - draw(context, surface) -> None
        Chamada a cada frame, depois de todos os updates, também na
        ordem de carregamento. Recebe a superfície pygame onde o
        módulo deve desenhar o que for de sua responsabilidade.

    - handle_event(context, event) -> None
        Chamada para cada evento pygame (teclado, mouse, etc.),
        antes do update do frame.

    - teardown(context) -> None
        Chamada uma vez ao final do jogo (jogador fechou a janela,
        ou o jogo terminou), na ordem INVERSA de carregamento -
        último módulo carregado é o primeiro a ser encerrado. Útil
        pra liberar recursos.

Nenhuma dessas funções é obrigatória: um loader.py pode definir só
setup(), só draw(), todas, ou nenhuma (nesse caso ele só é importado,
o que pode ser útil se ele só precisa rodar código no nível do
módulo, tipo registrar algo em outro lugar).

O general_loader detecta automaticamente quais dessas funções cada
módulo define e só as chama quando existem, então módulos "incompletos"
não geram erro.
"""

import os
import sys
import importlib
import traceback

import pygame


# =========================================================================
#  CONFIGURAÇÃO
# =========================================================================

SYSTEM_DIR = os.path.dirname(os.path.abspath(__file__))
LOADER_FILENAME = "loader.py"

WIDTH, HEIGHT = 1280, 720
FPS = 60

# Nomes de função reconhecidos em cada loader.py (nesta ordem de
# relevância dentro do ciclo de vida do jogo).
HOOK_NAMES = ("setup", "handle_event", "update", "draw", "teardown")


# =========================================================================
#  DESCOBERTA E IMPORTAÇÃO DOS MÓDULOS (loader.py de cada subpasta)
# =========================================================================


def discover_module_folders():
    """Retorna, em ordem alfabética, os caminhos das subpastas dentro de
    system/ que contêm um arquivo loader.py."""
    if not os.path.isdir(SYSTEM_DIR):
        return []

    folders = []
    for entry in sorted(os.listdir(SYSTEM_DIR)):
        full_path = os.path.join(SYSTEM_DIR, entry)
        if not os.path.isdir(full_path):
            continue
        loader_path = os.path.join(full_path, LOADER_FILENAME)
        if os.path.isfile(loader_path):
            folders.append(full_path)
    return folders


def _folder_to_module_name(folder_path):
    """Gera um nome de módulo único e importável a partir do caminho da
    subpasta, ex: system/enemies -> game_modules.enemies_loader"""
    folder_name = os.path.basename(folder_path.rstrip(os.sep))
    safe_name = "".join(ch if ch.isalnum() else "_" for ch in folder_name)
    return f"game_modules.{safe_name}_loader"


def load_all_modules():
    """Importa o loader.py de cada subpasta encontrada dentro de
    system/, guardando o conteúdo (o módulo já importado) numa lista,
    na mesma ordem em que as pastas foram descobertas.

    Devolve uma lista de tuplas (nome_da_pasta, modulo)."""
    loaded_modules = []

    for folder_path in discover_module_folders():
        folder_name = os.path.basename(folder_path.rstrip(os.sep))
        loader_path = os.path.join(folder_path, LOADER_FILENAME)
        module_name = _folder_to_module_name(folder_path)

        try:
            spec = importlib.util.spec_from_file_location(module_name, loader_path)
            module = importlib.util.module_from_spec(spec)
            # registra em sys.modules ANTES de executar, pra suportar
            # imports internos/relativos que o próprio loader.py possa
            # precisar fazer (e evitar re-execução em imports futuros)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
        except Exception:
            print(
                f"[IF DEFENSE] Erro ao carregar '{loader_path}':\n"
                f"{traceback.format_exc()}"
            )
            continue

        loaded_modules.append((folder_name, module))
        print(f"[IF DEFENSE] Módulo carregado: {folder_name}/loader.py")

    return loaded_modules


def _call_hook_safely(module, folder_name, hook_name, *args):
    """Chama uma função (hook) de um módulo se ela existir, protegendo
    o loop principal do jogo contra uma exceção de um módulo específico
    derrubar o jogo inteiro."""
    hook = getattr(module, hook_name, None)
    if hook is None:
        return
    try:
        hook(*args)
    except Exception:
        print(
            f"[IF DEFENSE] Erro em {folder_name}/loader.py -> {hook_name}():\n"
            f"{traceback.format_exc()}"
        )


# =========================================================================
#  MONTAGEM E EXECUÇÃO DO JOGO
# =========================================================================


def run_game():
    """Ponto de entrada do jogo, chamado por main.py.

    1. Descobre e importa todos os loader.py dentro das subpastas de
       system/;
    2. Inicializa o pygame e cria a janela/tela do jogo;
    3. Roda setup() de cada módulo (na ordem em que foram carregados);
    4. Roda o loop principal, repassando eventos, update e draw pra
       cada módulo, na ordem em que foram carregados;
    5. Ao final, roda teardown() de cada módulo, na ordem inversa.
    """
    loaded_modules = load_all_modules()

    if not loaded_modules:
        print(
            f"[IF DEFENSE] Aviso: nenhum '{LOADER_FILENAME}' encontrado em "
            f"nenhuma subpasta de '{SYSTEM_DIR}'. Nada para rodar."
        )
        return

    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("IF DEFENSE")
    clock = pygame.time.Clock()

    # "context" é o dicionário compartilhado entre todos os módulos -
    # cada loader.py pode ler e escrever livremente nele pra trocar
    # informação com os demais (posição do jogador, pontuação, estado
    # das ondas de zumbis, etc.)
    context = {
        "screen": screen,
        "width": WIDTH,
        "height": HEIGHT,
        "clock": clock,
        "running": True,
    }

    # ---- setup() de cada módulo, na ordem de carregamento ----
    for folder_name, module in loaded_modules:
        _call_hook_safely(module, folder_name, "setup", context)

    # ---- loop principal ----
    try:
        while context.get("running", True):
            dt = clock.tick(FPS) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    context["running"] = False
                for folder_name, module in loaded_modules:
                    _call_hook_safely(module, folder_name, "handle_event", context, event)

            for folder_name, module in loaded_modules:
                _call_hook_safely(module, folder_name, "update", context, dt)

            screen.fill((0, 0, 0))
            for folder_name, module in loaded_modules:
                _call_hook_safely(module, folder_name, "draw", context, screen)

            pygame.display.flip()
    finally:
        # ---- teardown() de cada módulo, na ordem INVERSA ----
        for folder_name, module in reversed(loaded_modules):
            _call_hook_safely(module, folder_name, "teardown", context)

        pygame.quit()


if __name__ == "__main__":
    # Permite testar o general_loader isoladamente (sem passar por
    # title_screen.py / main.py), rodando: python general_loader.py
    run_game()