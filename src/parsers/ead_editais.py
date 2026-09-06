"""
Parser para paginas de polos de Educacao a Distancia (CEAD/NEAD/DEDD/CRead) que
listam os proprios editais como links "Edital/Chamada N/AAAA" no corpo da pagina.

Usado por fontes como:
- UFMG DEDD  -> https://www.ufmg.br/dedd/selecoes/
- IFMG CRead -> https://www.ifmg.edu.br/portal/educacao-a-distancia/editais-ead

Essas paginas ja sao especificas de EaD, entao basta capturar as ancoras que
seguem o padrao "Edital/Chamada <numero>/<ano>" (o numero/ano e identificador,
nao data de publicacao). Nao emitimos data: um proxy 01/01/AAAA seria descartado
pelo EDITAL_MAX_DIAS (armadilha ja evitada em FINATEC/CNPq/UNICAMP). O scraper tem
fallback proprio para essas fontes -- usa o ano do identificador do titulo como
31/12/AAAA --, entao um 'Edital 12/2020' cai fora da janela sem aqui emitir data.
"""
import re
from bs4 import BeautifulSoup
from .base import BaseParser


class EadEditaisParser(BaseParser):

    # "Edital Nº 1823/2026", "Edital 279-2026", "Chamada 12/2026"
    PADRAO = re.compile(
        r'\b(?:edital|chamada)\b.{0,24}?\b\d{1,4}\s*[/-]\s*(20\d{2})',
        re.IGNORECASE,
    )

    def parse(self, html, url_base):
        soup = BeautifulSoup(html, 'html.parser')
        editais = []
        vistos = set()

        for a in soup.find_all('a', href=True):
            texto = self.limpar_texto(a.get_text())
            href = a.get('href', '')

            if not texto or len(texto) < 12:
                continue
            if href.strip().startswith('#') or href.lower().startswith('javascript'):
                continue
            if not self.PADRAO.search(texto):
                continue

            url = self.resolver_url(href, url_base)
            if not url or url in vistos:
                continue
            vistos.add(url)

            editais.append({
                'titulo': texto,
                'url': url,
                'data': '',
            })

        return editais
