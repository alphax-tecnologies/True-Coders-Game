# -*- coding: utf-8 -*-
"""
IF DEFENSE - Tela de Título
============================
Tela de título estilo "Five Nights at Freddy's 3": menu lateral com
JOGAR / AJUDA / OPÇÕES, navegação por setas + Enter, painéis que
deslizam suavemente para AJUDA e OPÇÕES, e fade-to-black ao iniciar
o jogo (que agora chama o conteúdo de main.py em vez de apenas encerrar).

Requisitos: pip install pygame

Estrutura de pastas esperada:
    title_screen.py
    main.py                (arquivo do jogo em si, chamado ao clicar em JOGAR)
    assets/
        logo.png            (logo "IF DEFENSE")
        btn_jogar.png        (botão "JOGAR" já pronto, estilo pixel art)
        music.mp3             (opcional - música de fundo do menu)
        sfx_hover.wav          (opcional - som ao trocar o botão selecionado)
        sfx_click.wav          (opcional - som ao confirmar/clicar um botão)
        sfx_open.wav           (opcional - som ao abrir um painel)
        sfx_back.wav           (opcional - som ao voltar do painel)

Todos os áudios são carregados com segurança: se o arquivo não
existir, o jogo simplesmente roda sem som em vez de travar. Basta
colocar os arquivos .mp3/.wav na pasta assets/ com os nomes acima
que eles passam a funcionar automaticamente.
"""

import sys
import os
import math
import random
import runpy
import pygame

# =========================================================================
#  CONFIGURAÇÃO GERAL
# =========================================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
MAIN_PY_PATH = os.path.join(BASE_DIR, "main.py")

WIDTH, HEIGHT = 1280, 720
FPS = 60

# --- Paleta (combina com a arte fornecida: verde zumbi, vermelho sangue) ---
COL_BG_TOP = (10, 14, 22)
COL_BG_BOTTOM = (18, 26, 20)
COL_PANEL = (16, 22, 18, 235)
COL_PANEL_BORDER = (70, 150, 60)
COL_BLOOD = (150, 20, 20)
COL_TEXT = (230, 235, 225)
COL_TEXT_DIM = (150, 160, 150)
COL_GREEN = (90, 200, 80)
COL_GREEN_DARK = (35, 90, 35)
COL_GOLD = (240, 210, 120)

pygame.init()
try:
    pygame.mixer.init()
    MIXER_OK = True
except pygame.error:
    MIXER_OK = False

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("IF DEFENSE")
clock = pygame.time.Clock()

# =========================================================================
#  CARREGAMENTO SEGURO DE ASSETS (imagens e sons)
# =========================================================================


def load_image(filename, fallback_size=None):
    """Carrega uma imagem de assets/. Se não existir, devolve uma
    superfície vazia (transparente) do tamanho indicado, pra não travar."""
    path = os.path.join(ASSETS_DIR, filename)
    if os.path.isfile(path):
        img = pygame.image.load(path).convert_alpha()
        return img
    surf = pygame.Surface(fallback_size or (10, 10), pygame.SRCALPHA)
    return surf


def load_sound(filename):
    """Carrega um efeito sonoro de assets/. Devolve None se não existir
    ou se o mixer não estiver disponível - nesse caso o som é ignorado."""
    if not MIXER_OK:
        return None
    path = os.path.join(ASSETS_DIR, filename)
    if os.path.isfile(path):
        try:
            return pygame.mixer.Sound(path)
        except pygame.error:
            return None
    return None


def load_music(filename):
    """Carrega e toca a música de fundo em loop, se o arquivo existir."""
    if not MIXER_OK:
        return
    path = os.path.join(ASSETS_DIR, filename)
    if os.path.isfile(path):
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(0.5)
            pygame.mixer.music.play(-1)
        except pygame.error:
            pass


# ---- imagens ----
logo_img_raw = load_image("logo.png", (700, 500))
jogar_img_raw = load_image("btn_jogar.png", (360, 110))
ajuda_img_raw = load_image("btn_ajuda.png", (360, 110))
opcoes_img_raw = load_image("btn_opcoes.png", (360, 110))
background_img_raw = load_image("background.png", (WIDTH, HEIGHT))

# ---- sons (linha central pra trocar/adicionar facilmente) ----
sfx_hover = load_sound("sfx_hover.wav")
sfx_click = load_sound("sfx_click.wav")
sfx_open = load_sound("sfx_open.wav")
sfx_back = load_sound("sfx_back.wav")
load_music("music.mp3")


def play_sfx(sound, volume=0.7):
    if sound is not None:
        sound.set_volume(volume)
        sound.play()


# =========================================================================
#  FONTES
# =========================================================================

FONT_DIR = os.path.join(ASSETS_DIR, "fonts")


def load_font(size, bold=False):
    # Usa uma fonte de sistema, já que não há garantia de fonte pixel
    # customizada na pasta assets/fonts. Troque aqui se adicionar uma .ttf.
    return pygame.font.SysFont("consolas,couriernew,monospace", size, bold=bold)


font_button = load_font(34, bold=True)
font_button_small = load_font(30, bold=True)
font_title_panel = load_font(40, bold=True)
font_text = load_font(24)
font_hint = load_font(18)

# =========================================================================
#  FUNÇÕES AUXILIARES
# =========================================================================


def lerp(a, b, t):
    return a + (b - a) * t


def ease_towards(current, target, dt, speed=10.0):
    """Aproxima 'current' de 'target' suavemente (independente de FPS)."""
    t = 1 - math.exp(-speed * dt)
    return lerp(current, target, t)


def draw_vertical_gradient(surface, top_color, bottom_color):
    h = surface.get_height()
    w = surface.get_width()
    for y in range(h):
        t = y / h
        color = (
            int(lerp(top_color[0], bottom_color[0], t)),
            int(lerp(top_color[1], bottom_color[1], t)),
            int(lerp(top_color[2], bottom_color[2], t)),
        )
        pygame.draw.line(surface, color, (0, y), (w, y))


def wrap_text(text, font, max_width):
    """Quebra um texto em linhas que cabem em max_width pixels,
    respeitando também quebras de linha manuais ('\\n') que o usuário
    escrever no texto de ajuda."""
    lines = []
    for paragraph in text.split("\n"):
        if paragraph.strip() == "":
            lines.append("")
            continue
        words = paragraph.split(" ")
        current_line = ""
        for word in words:
            test_line = (current_line + " " + word).strip()
            if font.size(test_line)[0] <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)
    return lines


def draw_panel_rect(surface, rect, border_color=COL_PANEL_BORDER, border_width=3):
    """Painel com fundo semitransparente + borda, no estilo da arte enviada."""
    panel_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    pygame.draw.rect(panel_surf, COL_PANEL, panel_surf.get_rect(), border_radius=14)
    pygame.draw.rect(
        panel_surf, border_color, panel_surf.get_rect(), width=border_width, border_radius=14
    )
    surface.blit(panel_surf, rect.topleft)


# =========================================================================
#  BOTÃO DO MENU (com animação suave de escala/brilho ao ser selecionado)
# =========================================================================


class MenuButton:
    """Botão do menu baseado num sprite. A proporção original da imagem
    é sempre preservada (nunca esticamos largura/altura de forma
    independente) - só definimos uma LARGURA alvo e a altura é calculada
    a partir do aspect ratio real do PNG."""

    def __init__(self, label, center_pos, image=None, target_width=460):
        self.label = label
        self.center_pos = center_pos
        self.image_raw = image

        if image is not None and image.get_width() > 10:
            aspect = image.get_height() / image.get_width()
            self.base_size = (target_width, int(target_width * aspect))
        else:
            self.base_size = (target_width, int(target_width * 0.30))

        self.scale = 1.0          # escala atual (animada)
        self.target_scale = 1.0
        self.glow = 0.0           # brilho atual (0-1, animado)
        self.target_glow = 0.0

    def set_selected(self, selected):
        self.target_scale = 1.08 if selected else 1.0
        self.target_glow = 1.0 if selected else 0.0

    def update(self, dt):
        self.scale = ease_towards(self.scale, self.target_scale, dt, speed=12.0)
        self.glow = ease_towards(self.glow, self.target_glow, dt, speed=9.0)

    def get_rect(self):
        w = self.base_size[0] * self.scale
        h = self.base_size[1] * self.scale
        rect = pygame.Rect(0, 0, int(w), int(h))
        rect.center = self.center_pos
        return rect

    def _make_tinted_layer(self, base_img, tint, alpha):
        """Recolore uma cópia da imagem usando a MESMA silhueta (alpha
        original) - usado pra fazer o halo acompanhar o formato real do
        sprite em vez de um círculo genérico atrás do botão."""
        layer = base_img.copy()
        layer.fill((*tint, max(0, min(255, alpha))), special_flags=pygame.BLEND_RGBA_MULT)
        return layer

    def draw(self, surface):
        rect = self.get_rect()
        has_image = self.image_raw is not None and self.image_raw.get_width() > 10

        if self.glow > 0.01:
            pulse = 0.85 + 0.15 * math.sin(pygame.time.get_ticks() * 0.006)
            glow_strength = self.glow * pulse

            if has_image:
                # halo com o mesmo contorno do sprite (2 camadas, um pouco
                # maiores e mais transparentes, simulando um brilho suave)
                base_for_glow = pygame.transform.smoothscale(self.image_raw, rect.size)
                for i, (expand, alpha_mul) in enumerate(((1.10, 0.35), (1.22, 0.18))):
                    glow_size = (int(rect.width * expand), int(rect.height * expand))
                    glow_layer = pygame.transform.smoothscale(base_for_glow, glow_size)
                    glow_layer = self._make_tinted_layer(
                        glow_layer, COL_GOLD, int(200 * glow_strength * alpha_mul)
                    )
                    glow_rect = glow_layer.get_rect(center=rect.center)
                    surface.blit(glow_layer, glow_rect.topleft)
            else:
                glow_alpha = int(120 * glow_strength)
                glow_size = (int(rect.width * 1.2), int(rect.height * 1.4))
                glow_surf = pygame.Surface(glow_size, pygame.SRCALPHA)
                pygame.draw.ellipse(glow_surf, (*COL_GREEN, glow_alpha), glow_surf.get_rect())
                glow_rect = glow_surf.get_rect(center=rect.center)
                surface.blit(glow_surf, glow_rect.topleft)

        if has_image:
            scaled_img = pygame.transform.smoothscale(self.image_raw, rect.size)
            if self.glow > 0.01:
                # clareia o próprio sprite (não só o halo por trás dele)
                bright = scaled_img.copy()
                add_amount = int(75 * self.glow)
                bright.fill(
                    (add_amount, int(add_amount * 0.92), int(add_amount * 0.65), 0),
                    special_flags=pygame.BLEND_RGB_ADD,
                )
                scaled_img = bright
            surface.blit(scaled_img, rect.topleft)
        else:
            # fallback: botão desenhado (só é usado se o PNG não for encontrado)
            border_col = tuple(int(lerp(COL_GREEN_DARK[i], COL_GOLD[i], self.glow)) for i in range(3))
            btn_surf = pygame.Surface(rect.size, pygame.SRCALPHA)
            body_rect = btn_surf.get_rect()
            pts = [
                (18, 0), (body_rect.width, 0),
                (body_rect.width - 18, body_rect.height),
                (0, body_rect.height),
            ]
            pygame.draw.polygon(btn_surf, (22, 40, 24, 235), pts)
            pygame.draw.polygon(btn_surf, border_col, pts, width=4)
            surface.blit(btn_surf, rect.topleft)

            text_col = tuple(int(lerp(COL_TEXT[i], COL_GOLD[i], self.glow)) for i in range(3))
            label_surf = font_button.render(self.label, True, text_col)
            label_rect = label_surf.get_rect(center=rect.center)
            surface.blit(label_surf, label_rect)


# =========================================================================
#  PAINEL DESLIZANTE (OPÇÕES / AJUDA)
# =========================================================================


class SlidePanel:
    """Painel que entra suavemente pela direita da tela."""

    def __init__(self, rect_open):
        self.rect_open = rect_open  # posição final (aberto)
        self.x = WIDTH + 50         # posição atual (começa fora da tela)
        self.target_x = WIDTH + 50
        self.open = False

    def show(self):
        self.open = True
        self.target_x = self.rect_open.x

    def hide(self):
        self.open = False
        self.target_x = WIDTH + 50

    def update(self, dt):
        self.x = ease_towards(self.x, self.target_x, dt, speed=8.0)

    def current_rect(self):
        r = self.rect_open.copy()
        r.x = int(self.x)
        return r

    def is_fully_hidden(self):
        return (not self.open) and abs(self.x - self.target_x) < 1


# =========================================================================
#  ESTADO DO MENU
# =========================================================================

STATE_MAIN = "main"
STATE_OPTIONS = "options"
STATE_HELP = "help"
STATE_FADING = "fading"

state = STATE_MAIN
selected_index = 0  # 0 = JOGAR, 1 = AJUDA, 2 = OPÇÕES

# --- texto de ajuda: edite este texto livremente, ele quebra linha sozinho ---
HELP_TEXT = (
    "COMO JOGAR\n"
    "\n"
    "Use as setas PARA CIMA e PARA BAIXO para navegar entre os botoes "
    "do menu principal, e pressione ENTER para confirmar a opcao "
    "selecionada.\n"
    "\n"
    "Sobreviva as ondas de zumbis defendendo a base ate o amanhecer. "
    "Posicione suas defesas com cuidado e gerencie seus recursos.\n"
    "\n"
    "Pressione ENTER ou clique em VOLTAR para retornar ao menu principal."
)

# --- posicionamento: logo um pouco acima do meio, à esquerda ---
# (o logo_base_rect é a posição de "repouso"; a animação de flutuar é
# aplicada por cima dela a cada frame, sem esticar a imagem)
logo_target_w = 560
logo_scale_ratio = logo_target_w / logo_img_raw.get_width()
logo_img = pygame.transform.smoothscale(
    logo_img_raw,
    (int(logo_img_raw.get_width() * logo_scale_ratio), int(logo_img_raw.get_height() * logo_scale_ratio)),
)
logo_base_rect = logo_img.get_rect(center=(WIDTH * 0.32, HEIGHT * 0.42))

LOGO_FLOAT_AMPLITUDE = 12   # pixels pra cima/baixo
LOGO_FLOAT_SPEED = 1.1      # velocidade do balanço (rad/s aprox.)

# --- botões do menu, empilhados verticalmente à direita ---
# a largura de cada sprite é fixada (BUTTON_TARGET_WIDTH) e a altura é
# calculada a partir do aspect ratio real do PNG, pra nunca esticar a arte
BUTTON_TARGET_WIDTH = 460
BUTTON_GAP = 34  # espaço vertical entre um botão e o próximo

menu_center_x = WIDTH * 0.80
_button_specs = [
    ("JOGAR", jogar_img_raw),
    ("AJUDA", ajuda_img_raw),
    ("OPÇÕES", opcoes_img_raw),
]
_button_heights = []
for _label, _img in _button_specs:
    if _img is not None and _img.get_width() > 10:
        _aspect = _img.get_height() / _img.get_width()
    else:
        _aspect = 0.30
    _button_heights.append(int(BUTTON_TARGET_WIDTH * _aspect))

_stack_total_h = sum(_button_heights) + BUTTON_GAP * (len(_button_specs) - 1)
_stack_y = HEIGHT * 0.52 - _stack_total_h / 2

menu_buttons = []
for (_label, _img), _h in zip(_button_specs, _button_heights):
    _center_y = _stack_y + _h / 2
    menu_buttons.append(
        MenuButton(_label, (menu_center_x, _center_y), image=_img, target_width=BUTTON_TARGET_WIDTH)
    )
    _stack_y += _h + BUTTON_GAP

btn_jogar, btn_ajuda, btn_opcoes = menu_buttons

# --- painel de opções ---
options_panel_w, options_panel_h = 620, 480
options_rect_open = pygame.Rect(
    WIDTH - options_panel_w - 70, (HEIGHT - options_panel_h) // 2, options_panel_w, options_panel_h
)
options_panel = SlidePanel(options_rect_open)

# --- painel de ajuda ---
help_panel_w, help_panel_h = 760, 540
help_rect_open = pygame.Rect(
    WIDTH - help_panel_w - 70, (HEIGHT - help_panel_h) // 2, help_panel_w, help_panel_h
)
help_panel = SlidePanel(help_rect_open)

# --- opções configuráveis dentro do painel OPÇÕES ---
music_volume = 0.5
sfx_volume = 0.7
fullscreen_on = False
options_items = ["musica", "sfx", "tela_cheia", "voltar"]
options_selected = 0

# --- item selecionado dentro do painel AJUDA (só tem "voltar") ---
help_selected = 0
help_items = ["voltar"]

# --- fade final ao clicar em jogar ---
fade_alpha = 0.0
FADE_SPEED = 480  # alpha por segundo


def set_fullscreen(value):
    global screen
    if value:
        screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
    else:
        screen = pygame.display.set_mode((WIDTH, HEIGHT))


def apply_volumes():
    if MIXER_OK:
        pygame.mixer.music.set_volume(music_volume)


# =========================================================================
#  AÇÕES DE NAVEGAÇÃO
# =========================================================================


def enter_options():
    global state, options_selected
    state = STATE_OPTIONS
    options_selected = 0
    options_panel.show()
    play_sfx(sfx_open, sfx_volume)


def enter_help():
    global state, help_selected
    state = STATE_HELP
    help_selected = 0
    help_panel.show()
    play_sfx(sfx_open, sfx_volume)


def back_to_main():
    global state
    state = STATE_MAIN
    options_panel.hide()
    help_panel.hide()
    play_sfx(sfx_back, sfx_volume)


def confirm_main_menu():
    global state
    if selected_index == 0:
        play_sfx(sfx_click, sfx_volume)
        state = STATE_FADING
    elif selected_index == 1:
        play_sfx(sfx_click, sfx_volume)
        enter_help()
    elif selected_index == 2:
        play_sfx(sfx_click, sfx_volume)
        enter_options()


def adjust_option(direction):
    """direction: -1 (esquerda) ou +1 (direita), pra sliders."""
    global music_volume, sfx_volume, fullscreen_on
    item = options_items[options_selected]
    if item == "musica":
        music_volume = max(0.0, min(1.0, music_volume + direction * 0.1))
        apply_volumes()
    elif item == "sfx":
        sfx_volume = max(0.0, min(1.0, sfx_volume + direction * 0.1))
    elif item == "tela_cheia":
        fullscreen_on = not fullscreen_on
        set_fullscreen(fullscreen_on)


def confirm_options():
    item = options_items[options_selected]
    if item == "voltar":
        back_to_main()
    elif item == "tela_cheia":
        adjust_option(1)
        play_sfx(sfx_click, sfx_volume)


def confirm_help():
    if help_items[help_selected] == "voltar":
        back_to_main()


# =========================================================================
#  DESENHO DOS PAINÉIS
# =========================================================================


def draw_options_panel(surface):
    if options_panel.is_fully_hidden():
        return
    rect = options_panel.current_rect()
    draw_panel_rect(surface, rect)

    pad = 40
    title_surf = font_title_panel.render("OPÇÕES", True, COL_GOLD)
    surface.blit(title_surf, (rect.x + pad, rect.y + 26))

    pygame.draw.line(
        surface, COL_PANEL_BORDER,
        (rect.x + pad, rect.y + 80), (rect.x + rect.width - pad, rect.y + 80), 2,
    )

    rows = [
        ("Volume da Música", music_volume),
        ("Volume dos Efeitos", sfx_volume),
        ("Tela Cheia", 1.0 if fullscreen_on else 0.0),
    ]
    row_y = rect.y + 120
    row_h = 78

    for i, (label, value) in enumerate(rows):
        selected = (options_selected == i)
        label_col = COL_GOLD if selected else COL_TEXT
        label_surf = font_text.render(label, True, label_col)
        surface.blit(label_surf, (rect.x + pad, row_y))

        if options_items[i] == "tela_cheia":
            state_txt = "LIGADA" if fullscreen_on else "DESLIGADA"
            val_surf = font_text.render(state_txt, True, label_col)
            surface.blit(val_surf, (rect.x + rect.width - pad - val_surf.get_width(), row_y))
        else:
            # barra de volume
            bar_w = rect.width - pad * 2
            bar_x = rect.x + pad
            bar_y = row_y + 34
            bar_rect = pygame.Rect(bar_x, bar_y, bar_w, 10)
            pygame.draw.rect(surface, COL_GREEN_DARK, bar_rect, border_radius=5)
            fill_rect = pygame.Rect(bar_x, bar_y, int(bar_w * value), 10)
            fill_col = COL_GOLD if selected else COL_GREEN
            pygame.draw.rect(surface, fill_col, fill_rect, border_radius=5)
            knob_x = bar_x + int(bar_w * value)
            pygame.draw.circle(surface, fill_col, (knob_x, bar_y + 5), 9)

        if selected:
            arrow_col = COL_GOLD
            arrow_l = font_text.render("<", True, arrow_col)
            arrow_r = font_text.render(">", True, arrow_col)
            surface.blit(arrow_l, (rect.x + pad - 26, row_y))
            surface.blit(arrow_r, (rect.x + rect.width - pad + 10, row_y))

        row_y += row_h

    # rodapé do painel: divisória + dica (em cima) + botão voltar (embaixo),
    # com espaçamento fixo entre eles pra nunca se sobreporem
    footer_top = rect.y + rect.height - 96
    pygame.draw.line(
        surface, COL_PANEL_BORDER,
        (rect.x + pad, footer_top), (rect.x + rect.width - pad, footer_top), 1,
    )

    hint_surf = font_hint.render("SETAS: navegar   ENTER/ESQ/DIR: ajustar", True, COL_TEXT_DIM)
    surface.blit(hint_surf, (rect.x + pad, footer_top + 14))

    back_selected = (options_selected == len(options_items) - 1)
    back_col = COL_GOLD if back_selected else COL_TEXT_DIM
    back_surf = font_button_small.render("< VOLTAR", True, back_col)
    back_rect = back_surf.get_rect(topleft=(rect.x + pad, footer_top + 44))
    surface.blit(back_surf, back_rect)


def draw_help_panel(surface):
    if help_panel.is_fully_hidden():
        return
    rect = help_panel.current_rect()
    draw_panel_rect(surface, rect)

    pad = 40
    title_surf = font_title_panel.render("AJUDA", True, COL_GOLD)
    surface.blit(title_surf, (rect.x + pad, rect.y + 26))
    pygame.draw.line(
        surface, COL_PANEL_BORDER,
        (rect.x + pad, rect.y + 80), (rect.x + rect.width - pad, rect.y + 80), 2,
    )

    # rodapé reservado (mesma altura fixa usada no painel de OPÇÕES) pra
    # garantir que o texto nunca invada o espaço da dica + botão voltar
    footer_h = 96
    footer_top = rect.y + rect.height - footer_h

    # área de texto delimitada pelas paredes do painel (com padding),
    # terminando ANTES do rodapé
    text_area = pygame.Rect(
        rect.x + pad, rect.y + 100, rect.width - pad * 2, footer_top - (rect.y + 100) - 10
    )
    # recorte para garantir que nada vaze da caixa do painel
    old_clip = surface.get_clip()
    surface.set_clip(text_area)

    lines = wrap_text(HELP_TEXT, font_text, text_area.width)
    line_h = font_text.get_linesize() + 6
    y = text_area.y
    for line in lines:
        if y + line_h > text_area.bottom:
            break  # evita desenhar texto além da parede inferior do painel
        line_surf = font_text.render(line, True, COL_TEXT)
        surface.blit(line_surf, (text_area.x, y))
        y += line_h

    surface.set_clip(old_clip)

    pygame.draw.line(
        surface, COL_PANEL_BORDER,
        (rect.x + pad, footer_top), (rect.x + rect.width - pad, footer_top), 1,
    )

    hint_surf = font_hint.render("ENTER: voltar", True, COL_TEXT_DIM)
    surface.blit(hint_surf, (rect.x + pad, footer_top + 14))

    back_selected = True
    back_col = COL_GOLD if back_selected else COL_TEXT_DIM
    back_surf = font_button_small.render("< VOLTAR", True, back_col)
    back_rect = back_surf.get_rect(topleft=(rect.x + pad, footer_top + 44))
    surface.blit(back_surf, back_rect)


# =========================================================================
#  FUNDO
# =========================================================================


def make_cover_background(image, target_size):
    """Escala a imagem pra preencher target_size inteiro SEM distorcer
    (equivalente a background-size: cover do CSS), cortando o excesso."""
    tw, th = target_size
    iw, ih = image.get_size()
    scale = max(tw / iw, th / ih)
    new_size = (int(iw * scale) + 1, int(ih * scale) + 1)
    scaled = pygame.transform.smoothscale(image, new_size)
    x = (new_size[0] - tw) // 2
    y = (new_size[1] - th) // 2
    cropped = pygame.Surface((tw, th))
    cropped.blit(scaled, (0, 0), area=pygame.Rect(x, y, tw, th))
    return cropped


if background_img_raw.get_width() > 10:
    background = make_cover_background(background_img_raw, (WIDTH, HEIGHT))
    # leve escurecida pra manter o texto/menu legível por cima da foto
    dark_overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    dark_overlay.fill((5, 8, 10, 95))
    background.blit(dark_overlay, (0, 0))
else:
    # fallback: gradiente gerado, caso assets/background.png não exista
    background = pygame.Surface((WIDTH, HEIGHT))
    draw_vertical_gradient(background, COL_BG_TOP, COL_BG_BOTTOM)
    random.seed(7)
    fog_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    for _ in range(6):
        fx = random.randint(0, WIDTH)
        fy = random.randint(HEIGHT // 3, HEIGHT)
        fr = random.randint(150, 320)
        pygame.draw.circle(fog_surf, (40, 60, 45, 18), (fx, fy), fr)
    background.blit(fog_surf, (0, 0))


# =========================================================================
#  CHAMADA DO JOGO (main.py) AO CLICAR EM JOGAR
# =========================================================================


def launch_main_game():
    """Executa todo o conteúdo de main.py quando o jogador clica em JOGAR.

    Usa runpy.run_path, que roda o arquivo main.py como se fosse o
    script principal (__name__ == "__main__"), no mesmo processo -
    então tudo que main.py fizer (abrir sua própria janela pygame,
    rodar seu próprio loop, etc.) é executado normalmente aqui.

    Se main.py não existir na mesma pasta, o erro é reportado no
    console em vez de travar a tela de título silenciosamente.
    """
    if not os.path.isfile(MAIN_PY_PATH):
        print(f"[IF DEFENSE] Aviso: não encontrei '{MAIN_PY_PATH}'. "
              f"Coloque o arquivo main.py na mesma pasta de title_screen.py.")
        return
    try:
        runpy.run_path(MAIN_PY_PATH, run_name="__main__")
    except SystemExit:
        # main.py pode chamar sys.exit() ao terminar (comum em jogos
        # pygame) - isso não deve derrubar a tela de título/processo.
        pass


# =========================================================================
#  LOOP PRINCIPAL
# =========================================================================


def handle_keydown(event):
    global selected_index, state, options_selected, help_selected

    if state == STATE_MAIN:
        if event.key in (pygame.K_UP, pygame.K_w):
            selected_index = (selected_index - 1) % len(menu_buttons)
            play_sfx(sfx_hover, sfx_volume)
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            selected_index = (selected_index + 1) % len(menu_buttons)
            play_sfx(sfx_hover, sfx_volume)
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            confirm_main_menu()

    elif state == STATE_OPTIONS:
        if event.key in (pygame.K_UP, pygame.K_w):
            options_selected = (options_selected - 1) % len(options_items)
            play_sfx(sfx_hover, sfx_volume)
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            options_selected = (options_selected + 1) % len(options_items)
            play_sfx(sfx_hover, sfx_volume)
        elif event.key == pygame.K_LEFT:
            adjust_option(-1)
        elif event.key == pygame.K_RIGHT:
            adjust_option(1)
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            confirm_options()
        elif event.key == pygame.K_ESCAPE:
            back_to_main()

    elif state == STATE_HELP:
        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            confirm_help()
        elif event.key == pygame.K_ESCAPE:
            back_to_main()


def main():
    global state, fade_alpha

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and state != STATE_FADING:
                handle_keydown(event)

        # ---- atualizar animações ----
        for i, btn in enumerate(menu_buttons):
            btn.set_selected(state == STATE_MAIN and i == selected_index)
            btn.update(dt)

        options_panel.update(dt)
        help_panel.update(dt)

        if state == STATE_FADING:
            fade_alpha = min(255, fade_alpha + FADE_SPEED * dt)
            if MIXER_OK:
                pygame.mixer.music.set_volume(max(0.0, music_volume * (1 - fade_alpha / 255)))
            if fade_alpha >= 255:
                # tela totalmente escura: agora é aqui que o jogo de
                # verdade começa de fato - chamamos todo o conteúdo de
                # main.py. Quando main.py terminar (ou fechar sua janela),
                # o programa é encerrado normalmente.
                launch_main_game()
                running = False

        # ---- desenhar ----
        screen.blit(background, (0, 0))
        # flutuar suavemente pra cima/baixo (sem distorcer a imagem)
        float_offset = LOGO_FLOAT_AMPLITUDE * math.sin(pygame.time.get_ticks() * 0.001 * LOGO_FLOAT_SPEED)
        logo_rect = logo_base_rect.copy()
        logo_rect.centery = int(logo_base_rect.centery + float_offset)
        screen.blit(logo_img, logo_rect)

        for btn in menu_buttons:
            btn.draw(screen)

        draw_options_panel(screen)
        draw_help_panel(screen)

        if not (options_panel.open or help_panel.open):
            hint = font_hint.render("SETAS: navegar   ENTER: selecionar", True, COL_TEXT_DIM)
            screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, HEIGHT - 40))

        if fade_alpha > 0:
            fade_surf = pygame.Surface((WIDTH, HEIGHT))
            fade_surf.fill((0, 0, 0))
            fade_surf.set_alpha(int(fade_alpha))
            screen.blit(fade_surf, (0, 0))

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()