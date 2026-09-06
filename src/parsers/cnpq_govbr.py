"""
Parser para o novo portal do CNPq em gov.br:
https://www.gov.br/cnpq/pt-br/chamadas/abertas-para-submissao

O CNPq migrou do antigo www.cnpq.br/web/guest/chamadas-publicas (Liferay) para o
portal gov.br. A lista de chamadas abertas traz âncoras cujo texto segue o padrão
"Chamada Pública CNPq/CAPES Nº 30/2026 – ...", apontando para a página da chamada.

Estratégia:
- Selecionar <a> cujo href contenha '/chamadas/' e cujo texto case com o padrão
  "(Chamada|Edital) ... <num>/<ano>".
- Não emitir data: o número/ano no título é só identificador (não é data de
  publicação), e um proxy 01/01/AAAA seria descartado pelo EDITAL_MAX_DIAS
  (mesma armadilha já evitada na FINATEC). O scraper usa o ano do título como
  fallback de recência (31/12/AAAA); MAX_ITENS_POR_FONTE segue sendo o teto.
- Exige render=True no config (o gov.br monta a lista via JavaScript).
"""
import re
from bs4 import BeautifulSoup
from .base import BaseParser


class CnpqGovBrParser(BaseParser):

    # Título de chamada: "Chamada ... 30/2026", "Chamada Pública ... Nº 13/2026"
    PADRAO = re.compile(
        r'\b(?:chamada|edital)\b.*?\b\d{1,4}\s*/\s*(20\d{2})',
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
            if '/chamadas/' not in href.lower():
                continue
            if not self.PADRAO.search(texto):
                continue

            url = self.resolver_url(href, url_base)
            chave = url or texto
            if chave in vistos:
                continue
            vistos.add(chave)

            editais.append({
                'titulo': texto,
                'url': url,
                'data': '',
            })

        return editais
