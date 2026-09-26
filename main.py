# -*- coding: utf-8 -*-
"""
IF DEFENSE - main.py
=====================
Ponto de entrada do JOGO em si (chamado pela tela de título através de
title_screen.py -> launch_main_game()).

Este arquivo é propositalmente enxuto: toda a lógica de fato do jogo
(entidades, ondas de zumbis, defesas, HUD, loop de gameplay, etc.) mora
em "general_loader.py". O main.py só é responsável por:

    1. Garantir que a pasta do projeto está no sys.path (pra
       "import general_loader" funcionar não importa de onde o
       processo foi iniciado);
    2. Importar o general_loader;
    3. Chamar a função de entrada dele (run_game), passando adiante
       qualquer coisa que o chamador (title_screen.py) tenha
       inicializado, se for o caso;
    4. Tratar erros de forma segura (arquivo faltando, pygame não
       encerrando "sujo", etc.) sem travar o processo.

Estrutura de pastas esperada:
    title_screen.py
    main.py                 <- este arquivo
    system/
        general_loader.py    (todas as funções/loop do jogo)
    assets/
        ...
"""

import os
import sys


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SYSTEM_DIR = os.path.join(BASE_DIR, "system")

# Garante que a pasta do projeto E a pasta system/ estão no sys.path,
# independentemente de main.py ter sido executado diretamente
# (python main.py) ou chamado por outro script (runpy.run_path a partir
# de title_screen.py).
for _path in (BASE_DIR, SYSTEM_DIR):
    if _path not in sys.path:
        sys.path.insert(0, _path)


def _import_general_loader():
    """Importa o módulo general_loader.py (dentro da pasta system/) com
    uma mensagem de erro amigável caso o arquivo não exista ou tenha
    algum problema."""
    loader_path = os.path.join(SYSTEM_DIR, "general_loader.py")
    if not os.path.isfile(loader_path):
        print(
            f"[IF DEFENSE] Erro: não encontrei 'general_loader.py' em "
            f"'{SYSTEM_DIR}'. Coloque o arquivo com as funções do jogo "
            f"dentro da pasta 'system/'."
        )
        return None

    try:
        import general_loader
        return general_loader
    except Exception as exc:  # captura qualquer erro de import/execução
        print(f"[IF DEFENSE] Erro ao importar 'general_loader.py': {exc}")
        return None


def main():
    """Ponto de entrada do jogo. Delega toda a lógica para
    general_loader.py, que deve expor uma função run_game()."""
    general_loader = _import_general_loader()
    if general_loader is None:
        return

    if not hasattr(general_loader, "run_game"):
        print(
            "[IF DEFENSE] Erro: 'general_loader.py' precisa definir uma "
            "função run_game() como ponto de entrada do jogo."
        )
        return

    try:
        general_loader.run_game()
    except SystemExit:
        # Caso general_loader.py chame sys.exit() ao final (comum em
        # jogos pygame quando o jogador fecha a janela) - isso não deve
        # ser tratado como erro.
        pass
    except Exception as exc:
        print(f"[IF DEFENSE] Erro durante a execução do jogo: {exc}")
        raise


if __name__ == "__main__":
    main()