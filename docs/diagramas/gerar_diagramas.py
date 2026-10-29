"""Gera os diagramas da página Sobre em SVG, sem dependências externas.

O diagrama de classes lê os campos direto dos models; o de casos de uso segue
os atores e funcionalidades de docs/proposta.md. Rode de novo quando um model
ou uma funcionalidade mudar:

    python manage.py shell < docs/diagramas/gerar_diagramas.py
"""

import math
from pathlib import Path
from xml.sax.saxutils import escape

from django.apps import apps
from django.conf import settings

DESTINO = Path(settings.BASE_DIR) / 'static' / 'img'
FONTE = 'Archivo, Segoe UI, Roboto, Helvetica, Arial, sans-serif'
TINTA = '#141a2e'
LINHA = '#46527a'
CORES = {'games': '#ffd23f', 'ia': '#2ec4b6', 'auth': '#d7dee8'}

LARGURA_LETRA = 7.0
ALTURA_LINHA = 17
CABECALHO = 30

TIPOS = {
    'CharField': 'str',
    'TextField': 'str',
    'URLField': 'url',
    'IntegerField': 'int',
    'PositiveIntegerField': 'int',
    'FloatField': 'float',
    'BooleanField': 'bool',
    'DateField': 'date',
    'DateTimeField': 'datetime',
}


def texto(x, y, conteudo, tamanho=12, peso='400', ancora='start', cor=TINTA, italico=False):
    estilo = ' font-style="italic"' if italico else ''
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-family="{FONTE}" font-size="{tamanho}" '
        f'font-weight="{peso}" text-anchor="{ancora}" fill="{cor}"{estilo}>{escape(conteudo)}</text>'
    )


def svg(largura, altura, titulo, corpo):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {largura} {altura}" '
        f'width="{largura}" height="{altura}" role="img" aria-label="{escape(titulo)}">\n'
        f'<title>{escape(titulo)}</title>\n'
        f'<rect width="{largura}" height="{altura}" fill="#ffffff"/>\n'
        + '\n'.join(corpo)
        + '\n</svg>\n'
    )


# ---------------------------------------------------------------- classes


def linhas_do_model(model):
    linhas = []
    for campo in model._meta.fields + model._meta.many_to_many:
        if campo.name == 'id':
            continue
        tipo = type(campo).__name__
        if campo.many_to_many:
            linhas.append(f'{campo.name}: {campo.related_model.__name__}[*]')
        elif campo.is_relation:
            linhas.append(f'{campo.name}: {campo.related_model.__name__}')
        else:
            linhas.append(f'{campo.name}: {TIPOS.get(tipo, tipo)}')
    return linhas


METODOS = {
    'Game': ['update_local_rating()', 'pode_retraduzir: bool'],
    'Review': ['save() recalcula a nota do jogo'],
    'ConfiguracaoIA': ['atual(): ConfiguracaoIA'],
}

# Canto superior esquerdo de cada classe.
POSICOES = {
    'Genre': (40, 40),
    'Platform': (40, 160),
    'Game': (360, 40),
    'Activity': (720, 40),
    'Review': (40, 400),
    'User': (360, 400),
    'UserGameList': (720, 400),
    'CotaUsuario': (40, 640),
    'RequisicaoIA': (360, 640),
    'MensagemAssistente': (720, 640),
    'ConfiguracaoIA': (1040, 640),
}

RELACOES = [
    # (origem, destino, multiplicidade na origem, no destino)
    ('Game', 'Genre', '*', '*'),
    ('Game', 'Platform', '*', '*'),
    ('Activity', 'Game', '*', '1'),
    ('Activity', 'User', '*', '1'),
    ('Review', 'Game', '*', '1'),
    ('Review', 'User', '*', '1'),
    ('UserGameList', 'Game', '*', '1'),
    ('UserGameList', 'User', '*', '1'),
    ('CotaUsuario', 'User', '0..1', '1'),
    ('RequisicaoIA', 'User', '*', '0..1'),
    ('MensagemAssistente', 'User', '*', '1'),
]


class Caixa:
    def __init__(self, nome, app, linhas, metodos, posicao):
        self.nome, self.app, self.linhas, self.metodos = nome, app, linhas, metodos
        maior = max([len(nome) + 4] + [len(linha) for linha in linhas + metodos])
        self.x, self.y = posicao
        self.w = max(200, maior * LARGURA_LETRA + 24)
        extra = len(metodos) * ALTURA_LINHA + 10 if metodos else 0
        self.h = CABECALHO + len(linhas) * ALTURA_LINHA + 14 + extra

    @property
    def centro(self):
        return self.x + self.w / 2, self.y + self.h / 2

    def borda(self, alvo_x, alvo_y):
        """Ponto da borda na direção de (alvo_x, alvo_y)."""
        cx, cy = self.centro
        dx, dy = alvo_x - cx, alvo_y - cy
        escalas = []
        if dx:
            escalas.append(abs(self.w / 2 / dx))
        if dy:
            escalas.append(abs(self.h / 2 / dy))
        escala = min(escalas)
        return cx + dx * escala, cy + dy * escala

    def desenhar(self):
        partes = [
            f'<rect x="{self.x}" y="{self.y}" width="{self.w:.0f}" height="{self.h}" rx="6" '
            f'fill="#f7f8fc" stroke="{TINTA}" stroke-width="1.5"/>',
            f'<path d="M{self.x} {self.y + CABECALHO} V{self.y + 6} Q{self.x} {self.y} {self.x + 6} {self.y} '
            f'H{self.x + self.w - 6:.0f} Q{self.x + self.w:.0f} {self.y} {self.x + self.w:.0f} {self.y + 6} '
            f'V{self.y + CABECALHO} Z" fill="{CORES[self.app]}" stroke="{TINTA}" stroke-width="1.5"/>',
            texto(self.x + self.w / 2, self.y + 20, self.nome, 14, '700', 'middle'),
        ]
        y = self.y + CABECALHO + 18
        for linha in self.linhas:
            partes.append(texto(self.x + 12, y, linha))
            y += ALTURA_LINHA
        if self.metodos:
            y += 2
            partes.append(
                f'<line x1="{self.x}" y1="{y - 12}" x2="{self.x + self.w:.0f}" y2="{y - 12}" '
                f'stroke="{TINTA}" stroke-width="1"/>'
            )
            y += 6
            for metodo in self.metodos:
                partes.append(texto(self.x + 12, y, f'+ {metodo}', italico=True))
                y += ALTURA_LINHA
        return '\n'.join(partes)


def rotulo_na_ponta(x, y, outro_x, outro_y, conteudo):
    distancia = math.hypot(outro_x - x, outro_y - y) or 1
    ux, uy = (outro_x - x) / distancia, (outro_y - y) / distancia
    # 16 px ao longo da linha e 10 px para o lado.
    lx, ly = x + ux * 16 - uy * 10, y + uy * 16 + ux * 10
    return texto(lx, ly + 4, conteudo, 12, '700', 'middle', LINHA)


def diagrama_de_classes():
    usuario = apps.get_model('auth', 'User')
    caixas = {
        'User': Caixa(
            'User', 'auth',
            ['username: str', 'email: str', 'password: str', 'groups: Group[*]'],
            [], POSICOES['User'],
        )
    }
    for app in ('games', 'ia'):
        for model in apps.get_app_config(app).get_models():
            nome = model.__name__
            caixas[nome] = Caixa(nome, app, linhas_do_model(model), METODOS.get(nome, []), POSICOES[nome])
    assert usuario.__name__ == 'User'

    corpo = []
    for origem, destino, mult_origem, mult_destino in RELACOES:
        a, b = caixas[origem], caixas[destino]
        x1, y1 = a.borda(*b.centro)
        x2, y2 = b.borda(*a.centro)
        corpo.append(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{LINHA}" stroke-width="1.6"/>'
        )
        corpo.append(rotulo_na_ponta(x1, y1, x2, y2, mult_origem))
        corpo.append(rotulo_na_ponta(x2, y2, x1, y1, mult_destino))
    corpo.extend(caixa.desenhar() for caixa in caixas.values())

    # Legenda das cores por app.
    lx, ly = 1040, 40
    corpo.append(texto(lx, ly + 14, 'Legenda', 14, '700'))
    for i, (app, legenda) in enumerate(
        [('games', 'app games'), ('ia', 'app ia'), ('auth', 'Django (auth)')]
    ):
        y = ly + 32 + i * 26
        corpo.append(
            f'<rect x="{lx}" y="{y}" width="22" height="16" rx="3" fill="{CORES[app]}" '
            f'stroke="{TINTA}" stroke-width="1.2"/>'
        )
        corpo.append(texto(lx + 32, y + 13, legenda))
    corpo.append(texto(lx, ly + 132, '* = muitos, 1 = um,', 12, cor=LINHA))
    corpo.append(texto(lx, ly + 150, '0..1 = nenhum ou um', 12, cor=LINHA))

    largura = max([c.x + c.w for c in caixas.values()] + [lx + 220]) + 40
    altura = max(c.y + c.h for c in caixas.values()) + 40
    return svg(largura, altura, 'Diagrama de classes do MyGamesList', corpo)


# ---------------------------------------------------------- casos de uso

CASOS = {
    'Visitante': [
        'Ver a página inicial e os destaques',
        'Buscar jogos',
        'Ver a página do jogo',
        'Ler reviews',
        'Cadastrar-se',
        'Entrar no site',
    ],
    'Jogador': [
        'Importar jogo do RAWG',
        'Adicionar, mudar status e remover da lista',
        'Filtrar a minha lista',
        'Escrever, editar e excluir review',
        'Conversar com o assistente',
        'Ver meu consumo de IA',
        'Trocar a senha',
    ],
    'Moderador': [
        'Excluir qualquer review',
        'Filtrar reviews no painel',
        'Pedir nova tradução da descrição',
        'Ver as requisições de IA',
        'Configurar a IA e testar a conexão',
        'Ajustar a cota de IA por usuário',
    ],
}

EXTERNOS = {
    'RAWG': ['Buscar jogos', 'Importar jogo do RAWG'],
    'Steam': ['Importar jogo do RAWG'],
    'Gemini': [
        'Importar jogo do RAWG',
        'Conversar com o assistente',
        'Pedir nova tradução da descrição',
        'Configurar a IA e testar a conexão',
    ],
}


def boneco(x, y, nome):
    """Ator: cabeça em (x, y - 38), pés em y + 20, nome embaixo."""
    return '\n'.join([
        f'<circle cx="{x}" cy="{y - 38}" r="11" fill="#ffffff" stroke="{TINTA}" stroke-width="2"/>',
        f'<line x1="{x}" y1="{y - 27}" x2="{x}" y2="{y}" stroke="{TINTA}" stroke-width="2"/>',
        f'<line x1="{x - 18}" y1="{y - 18}" x2="{x + 18}" y2="{y - 18}" stroke="{TINTA}" stroke-width="2"/>',
        f'<line x1="{x}" y1="{y}" x2="{x - 14}" y2="{y + 20}" stroke="{TINTA}" stroke-width="2"/>',
        f'<line x1="{x}" y1="{y}" x2="{x + 14}" y2="{y + 20}" stroke="{TINTA}" stroke-width="2"/>',
        texto(x, y + 40, nome, 14, '700', 'middle'),
    ])


def generalizacao(x, y_filho, y_pai):
    """Seta de herança (triângulo vazado) do ator filho para o pai."""
    ponta = y_pai + 10
    return '\n'.join([
        f'<line x1="{x}" y1="{y_filho}" x2="{x}" y2="{ponta + 14}" stroke="{TINTA}" stroke-width="1.6"/>',
        f'<polygon points="{x},{ponta} {x - 9},{ponta + 14} {x + 9},{ponta + 14}" '
        f'fill="#ffffff" stroke="{TINTA}" stroke-width="1.6"/>',
    ])


def diagrama_de_casos_de_uso():
    ator_x, sistema_x, sistema_w = 110, 270, 520
    caso_cx, caso_rx, caso_ry = sistema_x + sistema_w / 2, 215, 21
    externo_x = 980
    passo, intervalo_faixa, topo = 52, 34, 90

    corpo, centros, faixas = [], {}, {}
    y = topo
    for ator, casos in CASOS.items():
        inicio = y
        for caso in casos:
            centros[caso] = y
            y += passo
        faixas[ator] = (inicio, y - passo)
        y += intervalo_faixa
    altura_sistema = y - intervalo_faixa - topo + 70
    altura = topo + altura_sistema + 30

    corpo.append(
        f'<rect x="{sistema_x}" y="{topo - 50}" width="{sistema_w}" height="{altura_sistema}" rx="10" '
        f'fill="#f7f8fc" stroke="{TINTA}" stroke-width="1.8"/>'
    )
    corpo.append(texto(caso_cx, topo - 22, 'MyGamesList', 16, '700', 'middle'))

    # Separadores no meio do espaço entre uma faixa e a seguinte.
    intervalos = list(faixas.values())
    for (_, fim_anterior), (inicio, _) in zip(intervalos, intervalos[1:]):
        ys = (fim_anterior + inicio) / 2
        corpo.append(
            f'<line x1="{sistema_x + 16}" y1="{ys:.0f}" x2="{sistema_x + sistema_w - 16}" y2="{ys:.0f}" '
            f'stroke="{LINHA}" stroke-width="1" stroke-dasharray="5 5"/>'
        )

    atores_y = {}
    for ator, (inicio, fim) in faixas.items():
        atores_y[ator] = (inicio + fim) / 2 + 10
        for caso in CASOS[ator]:
            corpo.append(
                f'<line x1="{ator_x + 24}" y1="{atores_y[ator] - 18:.1f}" x2="{caso_cx - caso_rx:.1f}" '
                f'y2="{centros[caso]}" stroke="{LINHA}" stroke-width="1.3"/>'
            )

    externos_y = {}
    for externo, casos in EXTERNOS.items():
        externos_y[externo] = sum(centros[c] for c in casos) / len(casos)
    # Afasta os sistemas externos que ficariam sobrepostos.
    ordem = sorted(externos_y, key=externos_y.get)
    for anterior, atual in zip(ordem, ordem[1:]):
        externos_y[atual] = max(externos_y[atual], externos_y[anterior] + 110)
    for externo, casos in EXTERNOS.items():
        for caso in casos:
            corpo.append(
                f'<line x1="{caso_cx + caso_rx:.1f}" y1="{centros[caso]}" x2="{externo_x - 70}" '
                f'y2="{externos_y[externo]:.1f}" stroke="{LINHA}" stroke-width="1.3" stroke-dasharray="6 4"/>'
            )

    for caso, cy in centros.items():
        corpo.append(
            f'<ellipse cx="{caso_cx:.1f}" cy="{cy}" rx="{caso_rx}" ry="{caso_ry}" fill="#fff6cf" '
            f'stroke="{TINTA}" stroke-width="1.5"/>'
        )
        corpo.append(texto(caso_cx, cy + 4, caso, 13, '500', 'middle'))

    for ator, y_ator in atores_y.items():
        corpo.append(boneco(ator_x, y_ator, ator))
    corpo.append(generalizacao(ator_x, atores_y['Jogador'] - 50, atores_y['Visitante'] + 62))
    corpo.append(generalizacao(ator_x, atores_y['Moderador'] - 50, atores_y['Jogador'] + 62))

    for externo, y_externo in externos_y.items():
        x = externo_x - 70
        corpo.append(
            f'<rect x="{x}" y="{y_externo - 26:.1f}" width="150" height="52" rx="6" fill="{CORES["ia"]}" '
            f'fill-opacity="0.25" stroke="{TINTA}" stroke-width="1.5"/>'
        )
        corpo.append(texto(x + 75, y_externo - 6, '«sistema externo»', 11, '400', 'middle', LINHA))
        corpo.append(texto(x + 75, y_externo + 13, externo, 14, '700', 'middle'))

    legenda_y = altura - 14
    corpo.append(texto(
        40, legenda_y,
        'Jogador herda os casos do Visitante e Moderador herda os do Jogador. '
        'Linhas tracejadas: serviços externos usados pelo caso.',
        12, cor=LINHA,
    ))
    return svg(externo_x + 120, altura + 10, 'Diagrama de casos de uso do MyGamesList', corpo)


DESTINO.mkdir(parents=True, exist_ok=True)
(DESTINO / 'diagrama-classes.svg').write_text(diagrama_de_classes(), encoding='utf-8')
(DESTINO / 'diagrama-casos-de-uso.svg').write_text(diagrama_de_casos_de_uso(), encoding='utf-8')
print('Diagramas gerados em', DESTINO)
