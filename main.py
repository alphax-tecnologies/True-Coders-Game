# -*- coding: utf-8 -*-
"""
IF DEFENSE - main.py
=====================
Ponto de entrada do JOGO (chamado pela tela de título através de
title_screen.py -> launch_main_game()).

Este arquivo contém o MENU DE SELEÇÃO DE MODO:

    - Texto "ESCOLHA O MODO DE JOGO" no topo (assets/textmode.png),
      com uma leve flutuação e pulso de brilho;
    - Fundo em tela cheia (assets/backgroundmode.png), com um véu
      escurecido para manter os elementos acima legíveis;
    - Botão CLÁSSICO (assets/classicmode.png) no canto ESQUERDO da
      tela -> ao ser escolhido, imprime "0" no terminal;
    - Botão ENDLESS (assets/endlessmode.png) no canto DIREITO da
      tela -> ao ser escolhido, imprime "1" no terminal;
    - Ambos os botões reagem com animação de escala + brilho ao
      passar o mouse por cima / serem selecionados pelo teclado, e
      têm uma leve flutuação constante (efeito "vivo" de menu).

Depois de escolhido o modo, main.py importa e chama
system/general_loader.py -> run_game(game_mode=...), repassando o
valor escolhido (0 = Clássico, 1 = Endless) para todos os módulos do
jogo através de context["game_mode"].

Estrutura de pastas esperada:
    title_screen.py
    main.py                     <- este arquivo
    system/
        general_loader.py        (varre as subpastas e monta o jogo)
    assets/
        classicmode.png           (botão "CLÁSSICO", canto esquerdo)
        endlessmode.png            (botão "ENDLESS", canto direito)
        backgroundmode.png          (fundo da tela de seleção)
        textmode.png                 ("ESCOLHA O MODO DE JOGO")
        sfx_hover.wav                (opcional - som ao trocar o modo selecionado)
        sfx_confirm.wav               (opcional - som ao confirmar o modo)
        musicmode.mp3                  (opcional - música de fundo desta tela)
"""

import os
import sys
import math

import pygame


# =========================================================================
#  CONFIGURAÇÃO GERAL
# =========================================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
SYSTEM_DIR = os.path.join(BASE_DIR, "system")

# Garante que a pasta do projeto E a pasta system/ estão no sys.path,
# independentemente de main.py ter sido executado diretamente
# (python main.py) ou chamado por outro script (runpy.run_path a partir
# de title_screen.py).
for _path in (BASE_DIR, SYSTEM_DIR):
    if _path not in sys.path:
        sys.path.insert(0, _path)

WIDTH, HEIGHT = 1280, 720
FPS = 60

COL_TEXT_DIM = (170, 178, 170)
COL_GOLD = (240, 210, 120)

MODE_CLASSICO = 0
MODE_ENDLESS = 1


# =========================================================================
#  CARREGAMENTO SEGURO DE ASSETS
# =========================================================================


def _load_image(filename):
    """Carrega uma imagem de assets/. Devolve None se não existir ou
    se der erro, pra quem desenha decidir um fallback em vez de
    travar o jogo."""
    path = os.path.join(ASSETS_DIR, filename)
    if not os.path.isfile(path):
        print(f"[IF DEFENSE] Aviso: asset não encontrado: '{path}'.")
        return None
    try:
        return pygame.image.load(path)
    except pygame.error as exc:
        print(f"[IF DEFENSE] Erro ao carregar '{path}': {exc}")
        return None


try:
    pygame.mixer.init()
    MIXER_OK = True
except pygame.error:
    MIXER_OK = False


def _load_sound(filename):
    """Carrega um efeito sonoro de assets/. Devolve None se não existir
    ou se o mixer não estiver disponível, pra não travar o jogo."""
    if not MIXER_OK:
        return None
    path = os.path.join(ASSETS_DIR, filename)
    if os.path.isfile(path):
        try:
            return pygame.mixer.Sound(path)
        except pygame.error:
            return None
    return None


def _play_sfx(sound, volume=0.7):
    if sound is not None:
        sound.set_volume(volume)
        sound.play()


def _lerp(a, b, t):
    return a + (b - a) * t


def _ease_towards(current, target, dt, speed=10.0):
    """Aproxima 'current' de 'target' suavemente (independente de FPS)."""
    t = 1 - math.exp(-speed * dt)
    return _lerp(current, target, t)


def _make_cover_surface(image, target_size):
    """Escala a imagem pra preencher target_size inteiro SEM distorcer
    (equivalente a background-size: cover do CSS), cortando o excesso."""
    tw, th = target_size
    iw, ih = image.get_size()
    scale = max(tw / iw, th / ih)
    new_size = (max(1, int(iw * scale) + 1), max(1, int(ih * scale) + 1))
    scaled = pygame.transform.smoothscale(image, new_size)
    x = (new_size[0] - tw) // 2
    y = (new_size[1] - th) // 2
    cropped = pygame.Surface((tw, th))
    cropped.blit(scaled, (0, 0), area=pygame.Rect(x, y, tw, th))
    return cropped


# =========================================================================
#  BOTÃO DE MODO (com animação de escala/brilho/flutuação)
# =========================================================================


class ModeButton:
    """Botão de modo de jogo baseado num sprite (com fallback desenhado
    caso a imagem não exista). A proporção original da imagem é sempre
    preservada."""

    def __init__(self, label, mode_value, center_pos, image=None,
                 target_width=460, float_phase=0.0):
        self.label = label
        self.mode_value = mode_value
        self.center_pos = center_pos
        self.image_raw = image
        self.float_phase = float_phase

        if image is not None and image.get_width() > 1:
            aspect = image.get_height() / image.get_width()
            self.base_size = (target_width, int(target_width * aspect))
        else:
            self.base_size = (target_width, int(target_width * 0.42))

        self.scale = 0.0          # começa "fechado" pra animar entrada
        self.target_scale = 1.0
        self.glow = 0.0
        self.target_glow = 0.0
        self.float_offset = 0.0

    def set_selected(self, selected):
        self.target_scale = 1.10 if selected else 1.0
        self.target_glow = 1.0 if selected else 0.0

    def update(self, dt, time_now):
        self.scale = _ease_towards(self.scale, self.target_scale, dt, speed=10.0)
        self.glow = _ease_towards(self.glow, self.target_glow, dt, speed=9.0)
        # flutuação suave e constante, independente da seleção
        self.float_offset = 10 * math.sin(time_now * 1.3 + self.float_phase)

    def get_rect(self):
        w = self.base_size[0] * self.scale
        h = self.base_size[1] * self.scale
        rect = pygame.Rect(0, 0, int(w), int(h))
        rect.center = (self.center_pos[0], int(self.center_pos[1] + self.float_offset))
        return rect

    def contains_point(self, pos):
        return self.get_rect().collidepoint(pos)

    def draw(self, surface, font_button, font_hint):
        rect = self.get_rect()
        if rect.width <= 0 or rect.height <= 0:
            return
        has_image = self.image_raw is not None and self.image_raw.get_width() > 1

        # halo suave (pulsante) quando selecionado, acompanhando a
        # silhueta real do sprite (em vez de uma elipse genérica)
        if self.glow > 0.01 and has_image:
            pulse = 0.85 + 0.15 * math.sin(pygame.time.get_ticks() * 0.006)
            glow_strength = self.glow * pulse
            base_for_glow = pygame.transform.smoothscale(self.image_raw, rect.size)
            for expand, alpha_mul in ((1.08, 0.45), (1.16, 0.22)):
                glow_size = (int(rect.width * expand), int(rect.height * expand))
                glow_layer = pygame.transform.smoothscale(base_for_glow, glow_size)
                tint = glow_layer.copy()
                tint.fill(
                    (*COL_GOLD, int(220 * glow_strength * alpha_mul)),
                    special_flags=pygame.BLEND_RGBA_MULT,
                )
                glow_rect = tint.get_rect(center=rect.center)
                surface.blit(tint, glow_rect.topleft)
        elif self.glow > 0.01:
            pulse = 0.85 + 0.15 * math.sin(pygame.time.get_ticks() * 0.006)
            glow_strength = self.glow * pulse
            glow_alpha = int(130 * glow_strength)
            glow_size = (int(rect.width * 1.15), int(rect.height * 1.3))
            glow_surf = pygame.Surface(glow_size, pygame.SRCALPHA)
            pygame.draw.ellipse(glow_surf, (*COL_GOLD, glow_alpha), glow_surf.get_rect())
            glow_rect = glow_surf.get_rect(center=rect.center)
            surface.blit(glow_surf, glow_rect.topleft)

        if has_image:
            scaled_img = pygame.transform.smoothscale(self.image_raw, rect.size)
            if self.glow > 0.01:
                bright = scaled_img.copy()
                add_amount = int(70 * self.glow)
                bright.fill(
                    (add_amount, add_amount, add_amount, 0),
                    special_flags=pygame.BLEND_RGBA_ADD,
                )
                scaled_img = bright
            surface.blit(scaled_img, rect.topleft)
        else:
            # fallback desenhado, só usado se a imagem não existir
            border_col = tuple(int(_lerp(60, 240, self.glow)) for _ in range(3))
            box = pygame.Surface(rect.size, pygame.SRCALPHA)
            pygame.draw.rect(box, (20, 30, 22, 235), box.get_rect(), border_radius=16)
            pygame.draw.rect(box, border_col, box.get_rect(), width=4, border_radius=16)
            surface.blit(box, rect.topleft)

            text_col = tuple(int(_lerp(230, 240, self.glow)) for _ in range(3))
            label_surf = font_button.render(self.label, True, text_col)
            label_rect = label_surf.get_rect(center=rect.center)
            surface.blit(label_surf, label_rect)

        # dica discreta embaixo do botão
        hint_col = COL_GOLD if self.glow > 0.5 else COL_TEXT_DIM
        hint_surf = font_hint.render(self.label, True, hint_col)
        hint_rect = hint_surf.get_rect(midtop=(rect.centerx, rect.bottom + 16))
        surface.blit(hint_surf, hint_rect)


# =========================================================================
#  TELA DE SELEÇÃO DE MODO
# =========================================================================


def choose_game_mode():
    """Mostra a tela de seleção de modo e BLOQUEIA até o jogador
    escolher CLÁSSICO (0, esquerda) ou ENDLESS (1, direita), ou fechar
    a janela.

    Ao confirmar uma escolha válida, imprime o valor no terminal
    (0 ou 1) e retorna esse valor. Se a janela for fechada sem
    escolher, retorna None.
    """
    owns_display = pygame.display.get_surface() is None
    if owns_display:
        pygame.init()
        screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("IF DEFENSE - Selecione o Modo")
    else:
        screen = pygame.display.get_surface()

    clock = pygame.time.Clock()

    font_button = pygame.font.SysFont("consolas,couriernew,monospace", 30, bold=True)
    font_hint = pygame.font.SysFont("consolas,couriernew,monospace", 20, bold=True)

    # ---- carregar assets (só agora, depois que existe um display) ----
    background_raw = _load_image("backgroundmode.png")
    text_raw = _load_image("textmode.png")
    classico_raw = _load_image("classicmode.png")
    endless_raw = _load_image("endlessmode.png")

    # ---- sons (hover, confirm) e música de fundo desta tela ----
    sfx_hover = _load_sound("sfx_hover.wav")
    sfx_confirm = _load_sound("sfx_confirm.wav")

    if MIXER_OK:
        music_path = os.path.join(ASSETS_DIR, "music.mp3")
        if os.path.isfile(music_path):
            try:
                pygame.mixer.music.load(music_path)
                pygame.mixer.music.set_volume(0.5)
                pygame.mixer.music.play(-1)
            except pygame.error:
                pass

    if background_raw is not None:
        background_raw = background_raw.convert()
        background_cover = _make_cover_surface(background_raw, (WIDTH, HEIGHT))
    else:
        background_cover = pygame.Surface((WIDTH, HEIGHT))
        background_cover.fill((12, 16, 14))

    # véu escuro sobre o fundo, pra manter texto/botões legíveis
    dark_overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    dark_overlay.fill((5, 6, 8, 140))

    if text_raw is not None:
        text_raw = text_raw.convert_alpha()
        text_target_w = 760
        text_aspect = text_raw.get_height() / text_raw.get_width()
        text_img = pygame.transform.smoothscale(
            text_raw, (text_target_w, int(text_target_w * text_aspect))
        )
    else:
        text_img = None

    if classico_raw is not None:
        classico_raw = classico_raw.convert_alpha()
    if endless_raw is not None:
        endless_raw = endless_raw.convert_alpha()

    button_width = 460
    margin_x = 90
    center_y = HEIGHT * 0.62

    btn_classico = ModeButton(
        "CLÁSSICO", MODE_CLASSICO,
        center_pos=(margin_x + button_width / 2, center_y),
        image=classico_raw, target_width=button_width, float_phase=0.0,
    )
    btn_endless = ModeButton(
        "ENDLESS", MODE_ENDLESS,
        center_pos=(WIDTH - margin_x - button_width / 2, center_y),
        image=endless_raw, target_width=button_width, float_phase=math.pi,
    )
    buttons = [btn_classico, btn_endless]  # ordem = ordem de navegação (setas)
    selected_index = 0

    text_base_y = HEIGHT * 0.16
    text_float_amplitude = 8
    text_glow_t = 0.0

    chosen_mode = None
    running = True
    time_now = 0.0

    while running:
        dt = clock.tick(FPS) / 1000.0
        time_now += dt

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_LEFT, pygame.K_a):
                    if selected_index != 0:
                        _play_sfx(sfx_hover)
                    selected_index = 0
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    if selected_index != 1:
                        _play_sfx(sfx_hover)
                    selected_index = 1
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                    _play_sfx(sfx_confirm)
                    chosen_mode = buttons[selected_index].mode_value
                    running = False
                elif event.key == pygame.K_ESCAPE:
                    running = False

            elif event.type == pygame.MOUSEMOTION:
                for i, btn in enumerate(buttons):
                    if btn.contains_point(event.pos) and selected_index != i:
                        _play_sfx(sfx_hover)
                        selected_index = i

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for btn in buttons:
                    if btn.contains_point(event.pos):
                        _play_sfx(sfx_confirm)
                        chosen_mode = btn.mode_value
                        running = False

        for i, btn in enumerate(buttons):
            btn.set_selected(i == selected_index)
            btn.update(dt, time_now)

        text_glow_t += dt

        # ---- desenho ----
        screen.blit(background_cover, (0, 0))
        screen.blit(dark_overlay, (0, 0))

        if text_img is not None:
            float_y = text_float_amplitude * math.sin(time_now * 1.1)
            glow_pulse = 0.5 + 0.5 * math.sin(text_glow_t * 2.2)

            # halo pulsante atrás do texto (acompanha a silhueta via alpha)
            glow_layer = text_img.copy()
            glow_alpha = int(90 + 90 * glow_pulse)
            glow_layer.fill((255, 60, 40, max(0, min(255, glow_alpha))),
                             special_flags=pygame.BLEND_RGBA_MULT)
            glow_scaled = pygame.transform.smoothscale(
                glow_layer,
                (int(text_img.get_width() * 1.05), int(text_img.get_height() * 1.05)),
            )
            glow_rect = glow_scaled.get_rect(
                center=(WIDTH // 2, int(text_base_y + text_img.get_height() / 2 + float_y))
            )
            screen.blit(glow_scaled, glow_rect.topleft)

            text_rect = text_img.get_rect(
                center=(WIDTH // 2, int(text_base_y + text_img.get_height() / 2 + float_y))
            )
            screen.blit(text_img, text_rect)
        else:
            # fallback caso textmode.png não exista
            fallback_font = pygame.font.SysFont(
                "consolas,couriernew,monospace", 42, bold=True
            )
            fallback_surf = fallback_font.render("ESCOLHA O MODO DE JOGO", True, (230, 235, 225))
            fallback_rect = fallback_surf.get_rect(midtop=(WIDTH // 2, int(text_base_y)))
            screen.blit(fallback_surf, fallback_rect)

        for btn in buttons:
            btn.draw(screen, font_button, font_hint)

        hint_surf = font_hint.render(
            "SETAS/A-D: navegar   ENTER: confirmar   Mouse: clicar",
            True, COL_TEXT_DIM,
        )
        hint_rect = hint_surf.get_rect(midbottom=(WIDTH // 2, HEIGHT - 26))
        screen.blit(hint_surf, hint_rect)

        pygame.display.flip()

    if chosen_mode is not None:
        # "printado no terminal", representando o valor enviado ao servidor
        print(chosen_mode)

    return chosen_mode


# =========================================================================
#  IMPORTAÇÃO E CHAMADA DO JOGO (system/general_loader.py)
# =========================================================================


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
    """Ponto de entrada do jogo:
    1. Mostra o menu de seleção de modo (CLÁSSICO=0 / ENDLESS=1);
    2. Delega o restante da execução para general_loader.py, que deve
       expor uma função run_game(game_mode=...)."""
    game_mode = choose_game_mode()
    if game_mode is None:
        # jogador fechou a janela de seleção sem escolher um modo -
        # não faz sentido continuar pro jogo em si.
        print("[IF DEFENSE] Nenhum modo selecionado. Encerrando.")
        return

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
        general_loader.run_game(game_mode=game_mode)
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