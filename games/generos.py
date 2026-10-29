# Nomes exatos devolvidos por GET /genres do RAWG (19 gêneros)
GENEROS_PT = {
    'Action': 'Ação',
    'Adventure': 'Aventura',
    'Arcade': 'Arcade',
    'Board Games': 'Jogos de tabuleiro',
    'Card': 'Cartas',
    'Casual': 'Casual',
    'Educational': 'Educativo',
    'Family': 'Família',
    'Fighting': 'Luta',
    'Indie': 'Indie',
    'Massively Multiplayer': 'Multijogador massivo',
    'Platformer': 'Plataforma',
    'Puzzle': 'Quebra-cabeça',
    'Racing': 'Corrida',
    'RPG': 'RPG',
    'Shooter': 'Tiro',
    'Simulation': 'Simulação',
    'Sports': 'Esportes',
    'Strategy': 'Estratégia',
}


def traduzir_genero(nome):
    return GENEROS_PT.get(nome, nome)
