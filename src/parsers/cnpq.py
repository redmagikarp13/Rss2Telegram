"""
Parser para o site do CNPq (cnpq.br).
Nota: O site pode ter problemas de TLS. Usa fallback com headers customizados.
"""
from bs4 import BeautifulSoup
from .base import BaseParser


class CnpqParser(BaseParser):
    def parse(self, html, url_base):
        editais = []
        soup = BeautifulSoup(html, 'html.parser')

        # CNPq usa Liferay - tentar múltiplos seletores
        seletores = [
            '.journal-content-article a',  # Liferay journal
            '.asset-abstract a',           # Liferay assets
            '.entry-title a',              # Entry titles
            '.portlet-body a',             # Portlet body
            'table.table tbody tr td a',   # Tabela de chamadas
            '.results-row a',              # Resultados
            '#portlet_resultados a',       # Portlet resultados
            '.asset-list-content a',       # Lista de assets
        ]

        for seletor in seletores:
            links = soup.select(seletor)
            for link in links:
                texto = self.limpar_texto(link.get_text())
                href = link.get('href', '')

                if not texto or not href or len(texto) < 10:
                    continue

                url = self.resolver_url(href, url_base)
                data = self.extrair_data_do_element_pai(link)
                editais.append({
                    'titulo': texto,
                    'url': url,
                    'data': data,
                })

            if editais:
                break

        # Fallback: links com texto relevante
        if not editais:
            all_links = soup.find_all('a', href=True)
            for link in all_links:
                texto = self.limpar_texto(link.get_text())
                href = link.get('href', '')
                texto_lower = texto.lower()

                if len(texto) > 15 and any(kw in texto_lower for kw in [
                    'chamada', 'edital', 'bolsa', 'programa', 'seleção'
                ]):
                    url = self.resolver_url(href, url_base)
                    data = self.extrair_data_do_element_pai(link)
                    editais.append({
                        'titulo': texto,
                        'url': url,
                        'data': data,
                    })

        return editais
