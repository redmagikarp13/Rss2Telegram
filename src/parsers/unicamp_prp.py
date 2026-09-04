"""
Parser para os editais FAEPEX / PRP da UNICAMP:
https://prp.unicamp.br/faepex/editais/

A PRP-Unicamp lista os editais de apoio à pesquisa/extensão como âncoras cujo
texto segue o padrão "Edital [FAEPEX] N° NN/AAAA", apontando para páginas em
/arquivo/uploads/. Cada item vive num card que também traz o nome do programa e
o período de inscrição ("Data de Inscrição dd/mm/aaaa a dd/mm/aaaa").

Estratégia:
- Selecionar <a> cujo texto case com "(Edital|Chamada) ... <num>/<ano>".
- Enriquecer com uma descricao vinda do card vizinho (programa + datas).
- Não emitir data como campo de data (o N/ano é identificador, não publicação);
  mesma regra que evitou a armadilha do proxy-date na FINATEC/CNPq.
- Exige render=True no config (o menu/conteudo é montado via JavaScript e o
  host www.prp.unicamp.br/pt-br retorna 404; o caminho correto é prp.unicamp.br).
"""
import re
from bs4 import BeautifulSoup
from .base import BaseParser


class UnicampPrpParser(BaseParser):

    PADRAO = re.compile(
        r'\b(?:edital|chamada)\b.{0,40}?\b\d{1,4}\s*/\s*(20\d{2})',
        re.IGNORECASE,
    )

    def parse(self, html, url_base):
        soup = BeautifulSoup(html, 'html.parser')
        editais = []
        vistos = set()

        for a in soup.find_all('a', href=True):
            texto = self.limpar_texto(a.get_text())
            href = a.get('href', '')

            if not texto or len(texto) < 8:
                continue
            if href.strip().startswith('#'):
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
            # Sem descricao: os cards tem acordeoes aninhados por arquivo
            # (Edital/Retificacao/Resultado) e extrair o nome do programa de
            # forma confiavel exigiria casar a estrutura exata, o que e fragil
            # demais. O botao "Ver na fonte" leva ao edital completo.
            editais.append(item)

        return editais
