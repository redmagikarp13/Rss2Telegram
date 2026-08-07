"""
Parser genérico para sites gov.br (CAPES e similares).
Estrutura: Portal Plone do governo federal.
"""
from bs4 import BeautifulSoup
from .base import BaseParser


class GenericoGovBrParser(BaseParser):
    def parse(self, html, url_base):
        editais = []
        soup = BeautifulSoup(html, 'html.parser')

        # Sites gov.br usam Plone com várias estruturas possíveis
        seletores = [
            '.tileBody a',                    # Tile layout
            '.tile-content a',                # Tile content
            '#content-core .tileItem a',      # Content core tiles
            '.documentDescription + ul li a', # Lista após descrição
            '#content-core ul li a',          # Lista no content core
            '.listingBar + ul li a',          # Lista com paginação
            '.entries .entry a',              # Entradas
            'article a',                      # Artigos
            '.conteudo a',                    # Conteúdo
            '.row .card a',                   # Cards Bootstrap
        ]

        for seletor in seletores:
            links = soup.select(seletor)
            for link in links:
                texto = self.limpar_texto(link.get_text())
                href = link.get('href', '')

                if not texto or not href or len(texto) < 10:
                    continue

                # Filtrar apenas links relevantes
                texto_lower = texto.lower()
                if any(kw in texto_lower for kw in [
                    'edital', 'bolsa', 'chamada', 'seleção', 'seletivo',
                    'programa', 'pibic', 'pibiti', 'pesquisa', 'extensão'
                ]):
                    url = self.resolver_url(href, url_base)
                    editais.append({
                        'titulo': texto,
                        'url': url,
                        'data': '',
                    })

            if editais:
                break

        return editais
