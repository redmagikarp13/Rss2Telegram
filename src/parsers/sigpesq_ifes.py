"""
Parser para SIGPesq IFES (sigpesq.ifes.edu.br/publico/Editais.aspx).
Portal de editais internos de pesquisa do IFES.

Estrutura: ASP.NET WebForms com GridView server-rendered.
Cada edital é uma <tr> dentro de <table id="Conteudo_gvwLista">, com uma
sub-tabela contendo:
  - Badge de status (Aberto/Em Andamento/Encerrado/Divulgação)
  - Cabeçalho: <campus> <numero>/<ano> - <linha>
  - Descrição completa
  - Período de inscrições (dd/MM/yyyy até dd/MM/yyyy)
  - Botão "Detalhes" (usa __doPostBack; o cod real não aparece no HTML)

Como o `cod` só aparece em postbacks, geramos uma URL sintética estável
baseada em <campus + numero/ano>. Isso permite dedup entre execuções mesmo
quando o status do edital muda (Aberto → Em Andamento).

Observação: o robots.txt do host traz `Disallow: /`. O uso aqui é de baixo
volume (1 GET/dia) em conteúdo público de órgão federal — se preferir,
remova essa fonte da lista em config.py.
"""
import re
from bs4 import BeautifulSoup
from .base import BaseParser


class SigpesqIfesParser(BaseParser):

    # URL base canônica usada para montar o link sintético
    BASE_URL = 'https://sigpesq.ifes.edu.br/publico/Editais.aspx'

    # Classes de badge aceitas (na ordem de prioridade de status)
    STATUS_CLASSES = ['badge-success', 'badge-warning', 'badge-danger', 'badge-info']

    # Regex do cabeçalho: "Reitoria 16/2026 - Outros"
    HEADER_PATTERN = re.compile(
        r'^\s*(\w[\w\s]*?)\s+(\d{1,4})\s*/\s*(\d{4})\s*(?:-\s*(.+?))?\s*$'
    )

    def parse(self, html, url_base):
        soup = BeautifulSoup(html, 'html.parser')
        editais = []

        grid = soup.find('table', id='Conteudo_gvwLista')
        if not grid:
            return editais

        # Itera apenas nas <tr> filhas diretas do grid (evita <tr> aninhadas)
        for tr in grid.find_all('tr', recursive=False):
            # Cabeçalho e paginador não têm <td align="center"> com sub-tabela w-100
            inner = tr.find('table', class_='w-100')
            if not inner:
                continue

            edital = self._parse_item(inner)
            if edital:
                editais.append(edital)

        return editais

    def _parse_item(self, inner):
        # 1. Badge de status — primeiro <span> filho com classe badge-*
        badge = inner.find('span', class_=lambda x: x and 'badge-' in x)
        status_text = self.limpar_texto(badge.get_text()) if badge else ''

        # 2. Cabeçalho: <td class="font-weight-bold"> "Reitoria 16/2026 - Outros"
        head_td = inner.find('td', class_='font-weight-bold')
        if not head_td:
            return None

        # O texto direto do td vem ANTES do <div class="float-right"> (período)
        header_text = ''
        for child in head_td.children:
            if isinstance(child, str):
                header_text += child
            else:
                # Parou ao encontrar <div> ou outro elemento
                if getattr(child, 'name', None) == 'div':
                    break
                # <br> e afins ainda contam como separador
        header_text = self.limpar_texto(header_text)

        if not header_text:
            return None

        # 3. Período de inscrições: <span class="badge badge-outline-dark">
        period_text = ''
        float_div = head_td.find('div', class_='float-right')
        if float_div:
            period_span = float_div.find('span')
            if period_span:
                period_text = self.limpar_texto(period_span.get_text())

        # 4. Descrição longa: segundo <td colspan="2">
        tds = inner.find_all('td', colspan=True)
        desc_text = ''
        # tds[0] é o td com font-weight-bold (cabeçalho), tds[1] é a descrição
        for td in tds:
            if 'font-weight-bold' in (td.get('class') or []):
                continue
            text = self.limpar_texto(td.get_text())
            # Ignora o td do botão "Detalhes"
            if 'Detalhes' in text and len(text) < 30:
                continue
            if text and len(text) > 5:
                desc_text = text
                break

        # 5. Construir título composto e limpo
        titulo = header_text
        extras = []
        if status_text:
            extras.append(f'[{status_text}]')
        if period_text and period_text != 'Não Informado':
            extras.append(period_text)
        if extras:
            titulo += ' ' + ' '.join(extras)

        # Anexar parte da descrição para ter contexto
        if desc_text:
            # Evita duplicar se desc_text já começa com o numero/ano
            desc_short = desc_text[:150] + ('...' if len(desc_text) > 150 else '')
            if desc_short.lower()[:20] not in titulo.lower():
                titulo += f' — {desc_short}'

        # 6. URL sintética estável (independente do status atual)
        slug = self._make_slug(header_text)
        url = f'{self.BASE_URL}#{slug}'

        # 7. Data: usa a primeira data do período (início das inscrições)
        data = self._extrair_data_inicio(period_text)

        return {
            'titulo': titulo,
            'url': url,
            'data': data,
        }

    def _make_slug(self, header_text):
        """Gera slug estável a partir do cabeçalho (ex.: 'Reitoria 16/2026')."""
        match = self.HEADER_PATTERN.match(header_text)
        if match:
            campus, numero, ano = match.group(1), match.group(2), match.group(3)
            campus_slug = re.sub(r'[^a-z0-9]+', '-', campus.lower()).strip('-')
            return f'{campus_slug}-{int(numero):02d}-{ano}'
        # Fallback: slugify o header inteiro
        slug = re.sub(r'[^a-z0-9]+', '-', header_text.lower()).strip('-')
        return slug[:60] or 'edital'

    def _extrair_data_inicio(self, period_text):
        """Extrai a primeira data (início) de 'dd/MM/aaaa até dd/MM/aaaa'."""
        if not period_text or 'Não Informado' in period_text:
            return ''
        dates = re.findall(r'\d{1,2}/\d{1,2}/\d{4}', period_text)
        if dates:
            return dates[0]
        return ''
