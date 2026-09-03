"""
Parser para o site da Fundação PRÓ-IFF (pro-iff.org.br/editais-abertos).
Estrutura: Elementor Accordion.
Editais em .elementor-accordion-item
"""
from bs4 import BeautifulSoup
from .base import BaseParser


class ProIffParser(BaseParser):
    def parse(self, html, url_base):
        editais = []
        soup = BeautifulSoup(html, 'html.parser')

        items = soup.select('.elementor-accordion-item')

        for item in items:
            title_tag = item.find('a', class_='elementor-accordion-title')
            if not title_tag:
                continue
                
            titulo = self.limpar_texto(title_tag.get_text())
            
            content_div = item.find('div', class_='elementor-tab-content')
            if not content_div:
                continue
                
            link_tag = content_div.find('a', href=True)
            if not link_tag:
                continue

            url = self.resolver_url(link_tag.get('href', ''), url_base)

            # Data: vamos tentar extrair do título ou deixar vazio (já que o título costuma ter a data)
            data = ''

            if titulo and url:
                editais.append({
                    'titulo': titulo,
                    'url': url,
                    'data': data,
                })

        return editais
