"""
Parser para o site da FACTO (facto.org.br).
Estrutura: WordPress + Elementor, editais em accordions por ano.
URL: https://facto.org.br/editais-{ano}/
"""
from bs4 import BeautifulSoup
from .base import BaseParser
import re


class FactoParser(BaseParser):
    def parse(self, html, url_base):
        editais = []
        soup = BeautifulSoup(html, 'html.parser')

        # Os editais ficam dentro de accordions do Elementor
        # Cada accordion-item tem um título (tab-title) e conteúdo (tab-content)
        accordion_items = soup.select('.elementor-accordion-item')

        for item in accordion_items:
            titulo_elem = item.select_one('.elementor-tab-title')
            conteudo_elem = item.select_one('.elementor-tab-content')

            if not titulo_elem:
                continue

            titulo_accordion = self.limpar_texto(titulo_elem.get_text())

            # Dentro do conteúdo, buscar links para PDFs e documentos
            if conteudo_elem:
                links = conteudo_elem.find_all('a', href=True)
                for link in links:
                    href = link.get('href', '')
                    texto_link = self.limpar_texto(link.get_text())

                    if not texto_link or not href:
                        continue

                    # Montar título: "Accordion Title - Link Text" se forem diferentes
                    if texto_link.lower() != titulo_accordion.lower():
                        titulo_final = f"{titulo_accordion} — {texto_link}"
                    else:
                        titulo_final = titulo_accordion

                    url_final = self.resolver_url(href, url_base)

                    editais.append({
                        'titulo': titulo_final,
                        'url': url_final,
                        'data': '',
                    })

            # Se não tem conteúdo com links, registrar o próprio accordion
            if not conteudo_elem or not conteudo_elem.find_all('a', href=True):
                editais.append({
                    'titulo': titulo_accordion,
                    'url': url_base,
                    'data': '',
                })

        # Também buscar links na lista de páginas (wpr-page-list)
        page_list_items = soup.select('.wpr-page-list-item')
        for item in page_list_items:
            link = item.find('a', href=True)
            titulo_elem = item.select_one('.wpr-pl-title')

            if link:
                titulo = self.limpar_texto(
                    titulo_elem.get_text() if titulo_elem else link.get_text()
                )
                url = self.resolver_url(link.get('href', ''), url_base)

                if titulo and url:
                    editais.append({
                        'titulo': titulo,
                        'url': url,
                        'data': '',
                    })

        return editais
