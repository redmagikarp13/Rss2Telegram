"""
Parser para o site do IFES - PRPPG (prppg.ifes.edu.br).
Estrutura: Joomla + K2, template padrão governo federal.
URL: https://prppg.ifes.edu.br/editais
"""
from bs4 import BeautifulSoup
from .base import BaseParser


class IfesParser(BaseParser):
    def parse(self, html, url_base):
        editais = []
        soup = BeautifulSoup(html, 'html.parser')

        # O IFES usa Joomla com K2 - editais ficam em listas de itens
        # Tentar múltiplos seletores comuns do template gov
        seletores = [
            '.itemList .itemContainer',      # K2 item list
            '.items-row .item',              # Joomla category list
            '#content .item-page',           # Joomla article
            '.blog-items .blog-item',        # Blog layout
            '.category-list .category-item', # Category layout
            'table.category tbody tr',       # Tabela de categorias
            '#content ul li',                # Lista simples
            '#system-message-container ~ div ul li',  # Lista após mensagem
            '.itemListView .itemList .itemContainer',
        ]

        for seletor in seletores:
            items = soup.select(seletor)
            if items:
                for item in items:
                    link = item.find('a', href=True)
                    if link:
                        titulo = self.limpar_texto(link.get_text())
                        url = self.resolver_url(link.get('href', ''), url_base)

                        if titulo and url and len(titulo) > 5:
                            # Tentar extrair data
                            data = ''
                            data_elem = item.find(class_=lambda x: x and ('date' in x.lower() or 'data' in x.lower())) if item else None
                            if data_elem:
                                data = self.limpar_texto(data_elem.get_text())
                            if not data:
                                data = self.extrair_data_do_element_pai(link)

                            editais.append({
                                'titulo': titulo,
                                'url': url,
                                'data': data,
                            })
                if editais:
                    break

        # Fallback: buscar todos os links com "edital" no texto ou href
        if not editais:
            all_links = soup.find_all('a', href=True)
            for link in all_links:
                texto = self.limpar_texto(link.get_text())
                href = link.get('href', '')

                if ('edital' in texto.lower() or 'edital' in href.lower() or
                    'bolsa' in texto.lower() or 'seleção' in texto.lower() or
                    'seletivo' in texto.lower()):

                    url = self.resolver_url(href, url_base)

                    if texto and url and len(texto) > 10:
                        data = self.extrair_data_do_element_pai(link)
                        editais.append({
                            'titulo': texto,
                            'url': url,
                            'data': data,
                        })

        return editais
