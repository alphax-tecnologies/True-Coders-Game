# -*- coding: utf-8 -*-
"""
Exemplo de ataque: Bola de Fogo.

Este é só um MODELO de como criar um novo ataque. Copie este arquivo
com outro nome (ex: gelo.py, raio.py) e ajuste os valores de ATTACK.
O spritesheet correspondente deve ir em assets/exemplo_fogo.png -
enquanto ele não existir, um placeholder colorido é usado
automaticamente, então o jogo funciona normalmente mesmo sem arte
pronta.
"""

ATTACK = {
    "name": "Bola de Fogo",
    "cost": 40,
    "damage": 25,
    "source":"assets/fogo.png",
    "sprite_frame_width": 64,
    "sprite_frame_height": 64,
    "sprite_frame_count": 4,
    "sprite_fps": 10,
}