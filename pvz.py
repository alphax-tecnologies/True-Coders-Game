import pygame
import sys
pygame.init()
LARGURA, ALTURA = 1280, 720
tela = pygame.display.set_mode((LARGURA, ALTURA))
pygame.display.set_caption("Gulosinhos FC")
relogio = pygame.time.Clock()
COR_DE_FUNDO = (30, 50, 30)
fonte = pygame.font.Font(None, 36)
texto1 = fonte.render("Jogo legal williamzao", True, (255, 255, 255))
rodando = True
while rodando:
    for evento in pygame.event.get():
        if evento.type == pygame.QUIT:
            rodando = False
    tela.fill(COR_DE_FUNDO)
    tela.blit(texto1, (20, 20))
    pygame.display.flip()

    relogio.tick(60)
pygame.quit()
sys.quit()