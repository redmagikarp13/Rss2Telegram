"""
Parser para o Portal Integra do IFES (https://integra.ifes.edu.br), usado pelo
Polo de Inovacao para publicar avisos/vinculacoes de projetos (o Polo anunciou
que passara a divulgar editais apenas la).

O frontend e uma SPA (Angular): a pagina /institucional/eventos nao traz links no
HTML estatico. Os dados vem de uma API JSON estilo Spring Boot:
    https://integra.ifes.edu.br/api/inovacao/eventos/data
que retorna {"content": [ {nome, slug, tipo:{nome}, campus:{nome},
dataInicio, dataTermino, publicado, ...} ], "totalElements": N, ...}.

O endpoint PUBLICO ignora os parametros page/size/sort: devolve sempre o mesmo
conjunto de ~10 eventos tidos como ativos/publicados. Nao ha como paginar as
outras paginas pela rota publica. Vale monitorar mesmo assim: o notifier
deduplica por URL, entao um evento novo do Polo que entre nesse conjunto gera
alerta uma unica vez.

Por isso a fonte e configurada com scrape_url apontando para a API e NAO usa
render: o scraper entrega o corpo JSON cru (response.text) direto ao parse(), que
faz json.loads.

Cada evento vira um edital:
- titulo  = nome
- url     = rota de detalhe da SPA  {origem}/institucional/eventos/{slug}
- data    = dataInicio (dd/mm/aaaa). E uma data REAL de evento, entao o filtro de
  recencia (EDITAL_MAX_DIAS) descarta sozinho eventos ja passados - sem proxy-date.
- descricao = "campus - tipo" (ex.: "Campus Colatina - Mostra"), info util e curta.
Ordena por dataInicio decrescente para que os mais recentes sobrevivam ao
MAX_ITENS_POR_FONTE.
"""
import json
from urllib.parse import urlparse

from .base import BaseParser


class IntegraEventosParser(BaseParser):

    def _fmt_data(self, iso):
        # "2026-09-01T07:00:00" -> "01/09/2026"
        if not iso or 'T' not in str(iso) and len(str(iso)) < 10:
            return ''
        try:
            parte = str(iso)[:10]
            a, m, d = parte.split('-')
            return f'{d}/{m}/{a}'
        except Exception:
            return ''

    def parse(self, html, url_base):
        try:
            data = json.loads(html)
        except Exception:
            return []

        eventos = data.get('content') if isinstance(data, dict) else data
        if not isinstance(eventos, list):
            return []

        # Origem (scheme+host) a partir da url_base (a propria API).
        p = urlparse(url_base)
        base = f'{p.scheme}://{p.netloc}/institucional/eventos/'

        editais = []
        vistos = set()
        for ev in eventos:
            if not isinstance(ev, dict):
                continue
            if ev.get('publicado') is False:
                continue

            nome = self.limpar_texto(ev.get('nome', ''))
            slug = (ev.get('slug') or '').strip()
            if not nome or not slug or nome in vistos:
                continue
            vistos.add(nome)

            item = {
                'titulo': nome,
                'url': base + slug,
                'data': self._fmt_data(ev.get('dataInicio')),
            }

            campus = (ev.get('campus') or {}).get('nome') if isinstance(ev.get('campus'), dict) else None
            tipo = (ev.get('tipo') or {}).get('nome') if isinstance(ev.get('tipo'), dict) else None
            partes = [x for x in (campus, tipo) if x]
            if partes:
                item['descricao'] = ' - '.join(partes)

            editais.append(item)

        # Mais recentes primeiro (para sobreviver ao corte por MAX_ITENS).
        editais.sort(key=lambda e: e['data'][6:10] + e['data'][3:5] + e['data'][0:2]
                     if len(e['data']) == 10 else '00000000', reverse=True)
        return editais
