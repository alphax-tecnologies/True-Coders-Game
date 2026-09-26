IF DEFENSE - Tela de Título (Pygame)
=====================================

Como rodar:
1. pip install pygame
2. python3 title_screen.py

Estrutura:
  title_screen.py       -> o código da tela de título
  assets/logo.png        -> a logo do jogo (já incluída)
  assets/btn_jogar.png   -> o botão JOGAR (já incluído)

Sons (opcionais - o jogo funciona sem eles):
  Coloque estes arquivos dentro de assets/ com esses nomes exatos
  para eles serem carregados automaticamente:
    assets/music.mp3        -> música de fundo do menu (toca em loop)
    assets/sfx_hover.wav    -> som ao trocar o botão selecionado
    assets/sfx_click.wav    -> som ao confirmar/clicar um botão
    assets/sfx_open.wav     -> som ao abrir um painel (opções/ajuda)
    assets/sfx_back.wav     -> som ao voltar de um painel

Controles:
  Setas Cima/Baixo -> navegar entre JOGAR / AJUDA / OPÇÕES
  Enter / Espaço    -> confirmar
  Dentro de OPÇÕES: Setas Cima/Baixo escolhem o item, Esquerda/Direita
                     ajustam volume ou ligam/desligam a tela cheia
  Esc               -> voltar ao menu principal (dentro de um painel)

Editar o texto de AJUDA:
  Procure a variável HELP_TEXT perto do topo do arquivo (seção "ESTADO
  DO MENU") e escreva o que quiser ali. O texto quebra linha sozinho
  para nunca vazar da caixa do painel.

Ao selecionar JOGAR:
  A tela escurece suavemente (fade to black) e o programa é encerrado
  - é o ponto onde você entraria com o código do jogo em si.
