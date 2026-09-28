# -*- coding: utf-8 -*-
"""
Laiser - torreta robótica plantável.

Diferente de um ataque comum (efeito instantâneo, ver exemplo_fogo.py),
o Laiser é uma TURRET: o jogador clica no slot pra selecioná-lo, depois
clica numa casa do tabuleiro pra plantá-lo ali. Uma vez plantado, ele
fica parado e dispara sozinho no zumbi mais próximo da sua linha, a
cada `fire_interval` segundos, até sua vida (max_hp) chegar a zero.

O spritesheet (assets/laiser.png) é uma grade 4x4 de células 384x384
(imagem total 1536x1536, PNG com transparência real):
    - linhas 0 e 1 (8 frames): robô ativo, com aura verde -> "idle"
    - linha 2 (4 frames): sequência de dano -> pegando fogo -> explodindo -> "destroy"
    - linha 3 (4 frames): fumaça residual se dissipando -> "aftermath"

Se assets/laiser.png não existir (ou tiver dimensões diferentes das
declaradas abaixo), o loader usa um placeholder gerado automaticamente
com a mesma estrutura de grade, então o jogo nunca quebra por isso -
mas para usar a arte de verdade, sprite_cell_width/height precisam
bater exatamente com o arquivo (célula = tamanho_da_imagem / colunas).
"""

TURRET = {
    "name": "Laiser",
    "cost": 100,
    "damage": 15,
    "fire_interval": 3.0,
    "max_hp": 150,

    # caminho da imagem do spritesheet, relativo à raiz do projeto
    "source": "assets/laiser_parcial.png",

    "sprite_grid_cols": 4,
    "sprite_grid_rows": 4,
    "sprite_cell_width": 384,
    "sprite_cell_height": 384,

    "sprite_rows": {
        "idle": (0, 1),
        "destroy": (2, 2),
        "aftermath": (3, 3),
    },
    "sprite_fps": 8,
}