"""
Parser para a FAPEX (Fundacao de Apoio a Pesquisa e Extensao / UFBA):
https://www.fapex.org.br/Fapex/Site/Principal/Edital/index

O site e um portal ASP.NET. A pagina de index lista os editais como linhas
(div.span3), cada uma com o texto:
    "Lançamento: DD/MM/AAAA Inscrições: DD/MM/AAAA a DD/MM/AAAA <titulo/do edital> ... DETALHE"
e um link 'DETALHE' apontando para /Fapex/Site/Principal/Edital/detalhe/id/<x>.

O texto da ancora e sempre "DETALHE" (generico), por isso o titulo real e a data
sao extraidos do CONTEINADOR da ancora. Usamos a data de 'Lancamento' (data REAL
de publicacao) para o item - assim o filtro EDITAL_MAX_DIAS funciona corretamente
(sem proxy-date). Descartamos os links de 'EDITAR' (area administrativa).
"""
import re
from bs4 import BeautifulSoup
from .base import BaseParser


class FapexParser(BaseParser):

    DETALHE = re.compile(r'/Edital/detalhe/', re.I)
    LANCAMENTO = re.compile(r'Lan[çc]amento:\s*(\d{2}/\d{2}/\d{4})', re.I)
    # Remove o cabecalho "Lancamento: ... Inscricoes: ... a ..." e palavras de acao
    _RUISO = re.compile(
        r'(Lan[çc]amento:\s*\d{2}/\d{2}/\d{4}|'
        r'Inscri[çc][õo]es:\s*\d{2}/\d{2}/\d{4}\s*a\s*\d{2}/\d{2}/\d{4}|'
        r'\bDETALHE\b|\bEDITAR\b|\bANEXOS?\b|\bPRORROGA[ÇC][ÃA]O\b)',
        re.IGNORECASE,
    )

    def parse(self, html, url_base):
        soup = BeautifulSoup(html, 'html.parser')
        editais = []
        vistos = set()

        for a in soup.find_all('a', href=True):
            href = a.get('href', '')
            if not self.DETALHE.search(href):
                continue

            url = self.resolver_url(href.replace(':443', ''), url_base)
            if not url or url in vistos:
                continue

            cont = a.find_parent('div', class_='span3') or a.find_parent(['li', 'tr', 'article', 'div'])
            if not cont:
                continue
            full = self.limpar_texto(cont.get_text(' ', strip=True))
            if not full:
                continue

            m = self.LANCAMENTO.search(full)
            data = m.group(1) if m else ''

            titulo = self.limpar_texto(self._RUISO.sub(' ', full))
            if len(titulo) < 10:
                continue
            # Titulos aqui vem com o texto-inteiro do card; limita o comprimento
            if len(titulo) > 140:
                titulo = titulo[:137].rstrip() + '...'

            vistos.add(url)
            editais.append({
                'titulo': titulo,
                'url': url,
                'data': data,
            })

        return editais
