"""
Parser para a FAPES-ES (Fundacao de Amparo a Pesquisa e Inovacao do ES),
portais estaduais:
  https://fapes.es.gov.br/chamamento-publico        (Chamadas Publicas)
  https://fapes.es.gov.br/chamadas-internacionais   (Editais Abertos - Internacionais)

O '/editais' do site e apenas um MENU (por isso o generico_govbr capturava
'Chamadas Publicas', 'Nossa Bolsa' etc). As chamadas/edital REAIS ficam em
subpaginas, como anchors para PDFs em /Media/fapes/....pdf.

Cada chamada e desdobrada em varios arquivos (EDITAL, ANEXO, TERMO DE ADESAO,
FORMULARIO, PUBLICACAO/POSTAGEM...). Para gerar um alerta acionavel por
oportunidade, mantemos apenas o documento principal (cujo texto contem
'edital' ou 'chamada') e descartamos os auxiliares via EXCLUSAO.

O conteudo ja vem no HTML estatico (acordeons server-side), entao NAO precisa de
render. Emite pdf_url = proprio link (ativa o botao 'Ler PDF'). data='' para nao
cair na armadilha do proxy-date no EDITAL_MAX_DIAS (o scraper recupera a recencia
pelo ano do identificador no titulo).
"""
import re
from bs4 import BeautifulSoup
from .base import BaseParser


class FapesEsParser(BaseParser):

    # Documento principal da oportunidade
    PADRAO = re.compile(r'\b(edital|chamada|chamamento)\b', re.IGNORECASE)

    # Arquivos auxiliares / desdobramentos que NAO devem virar alerta separado
    EXCLUSAO = re.compile(
        r'\b(anexo|anexos|ap[eê]ndice|termo|publica[cç][aã]o|postagem|formul[aá]rio|'
        r'guia|modelo|planilha|minuta|instru[cç][aã]o|resultado|homologa|convoca|'
        r'classifica[çc]ao|ata|recurso|parecer|errata)\b',
        re.IGNORECASE,
    )

    def parse(self, html, url_base):
        soup = BeautifulSoup(html, 'html.parser')
        editais = []
        vistos = set()

        for a in soup.find_all('a', href=True):
            href = a.get('href', '')
            # So os documentos apontam para /Media/fapes/... ; o menu nao.
            if '/media/fapes/' not in href.lower():
                continue

            texto = self.limpar_texto(a.get_text())
            if not texto or len(texto) < 8:
                continue
            if not self.PADRAO.search(texto):
                continue
            if self.EXCLUSAO.search(texto):
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
            if url.lower().split('?')[0].endswith('.pdf'):
                item['pdf_url'] = url
            editais.append(item)

        return editais
