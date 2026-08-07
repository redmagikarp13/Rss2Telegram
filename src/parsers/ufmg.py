"""
Parser para o site da UFMG - PRPq (ufmg.br/prpq/editais/).
Estrutura: WordPress com template customizado.
Editais em .editals .page-list ul li com links e datas.
"""
from bs4 import BeautifulSoup
from .base import BaseParser
import re


class UfmgParser(BaseParser):
    def parse(self, html, url_base):
        editais = []
        soup = BeautifulSoup(html, 'html.parser')

        # Estrutura confirmada: .editals .page-list ul li
        items = soup.select('.editals .page-list ul li')

        if not items:
            # Fallback: tentar .page-list-box ul li
            items = soup.select('.page-list-box ul li')

        if not items:
            # Fallback: tentar qualquer li dentro de .editals
            items = soup.select('.editals li')

        for item in items:
            link = item.find('a', href=True)
            if not link:
                continue

            titulo = self.limpar_texto(link.get_text())
            url = self.resolver_url(link.get('href', ''), url_base)

            # Extrair data do span dentro do li
            data = ''
            span = item.find('span')
            if span:
                data_texto = self.limpar_texto(span.get_text())
                # Tentar extrair padrão "Aberto em: DD/MM/YYYY"
                match = re.search(r'(\d{2}/\d{2}/\d{4})', data_texto)
                if match:
                    data = match.group(1)
                else:
                    data = data_texto

            if titulo and url:
                editais.append({
                    'titulo': titulo,
                    'url': url,
                    'data': data,
                })

        return editais
