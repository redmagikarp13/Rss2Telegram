"""
Parser para o portal UnAC - Universidade Aberta do espirito Santo:
https://universidades.es.gov.br/editaisabertos

Os editais abertos sao links cujo href aponta para o PDF do edital em
/Media/Universidades/... (prefixo 'UnAC_' no nome do arquivo). Ja os itens de
menu/navegacao ('Programa Nossa Bolsa', 'Escola de Servico Publico', etc.) usam
outros caminhos, entao filtrar por '/media/' separa de forma robusta os editais
reais do ruido de navegacao.

O link do proprio edital ja e um PDF, entao emitimos tambem pdf_url (mesmo url)
para o notifier exibir o botao 'Ler PDF' inline no Telegram.

Nao emite data (o '/AAAA' no titulo e identificador, nao publicacao) - mesma
regra que evita a armadilha do proxy-date no filtro EDITAL_MAX_DIAS.
"""
import re
from bs4 import BeautifulSoup
from .base import BaseParser


class UnacEsParser(BaseParser):

    # Texto precisa indicar que e um edital/processo seletivo, nao um logo/arquivo solto
    PADRAO = re.compile(
        r'\b(edital|processo seletivo|retifica|retifica[cç][aã]o|chamada|sele[çc][aã]o)\b',
        re.IGNORECASE,
    )

    def parse(self, html, url_base):
        soup = BeautifulSoup(html, 'html.parser')
        editais = []
        vistos = set()

        for a in soup.find_all('a', href=True):
            href = a.get('href', '')
            # So os links de edital apontam para /Media/...; o menu nao.
            if '/media/' not in href.lower():
                continue

            texto = self.limpar_texto(a.get_text())
            if not texto or len(texto) < 8:
                continue
            if not self.PADRAO.search(texto):
                continue

            url = self.resolver_url(href, url_base)
            if not url or url in vistos:
                continue
            vistos.add(url)

            item = {
                'titulo': texto,
                'url': url,
                'data': '',
            }
            if url.lower().split('?')[0].endswith('.pdf'):
                item['pdf_url'] = url
            editais.append(item)

        return editais
