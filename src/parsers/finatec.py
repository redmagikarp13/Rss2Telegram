"""
Parser para FINATEC (finatec.org.br/transparencia/licitacoes/...).

A página https://www.finatec.org.br/compras-e-licitacoes/ é apenas uma casca
WordPress que embute dois <iframe>:
  - /transparencia/licitacoes/informacoes  (abertas — usar esta)
  - /transparencia/licitacoes/encerradas   (fechadas — ignorar)

Cada item é um <div class="accordion-group"> do Bootstrap legado:

    div.accordion-group
    ├── div.accordion-heading
    │   └── a.accordion-toggle href="#23479"  ← título + ID estável
    └── div.accordion-body
        └── div.accordion-inner
            └── a[href="....pdf"]  "Edital"          ← primeiro anexo
            └── a[href="....pdf"]  "Anexo I ..."     ← outros anexos

Estratégia: usar a âncora estável (#23479) como URL (persiste entre renomeações
de PDF e transições de status). Adicionalmente, expor o primeiro PDF como
`pdf_url` para que o notifier envie inline quando disponível.
"""
from urllib.parse import quote, urlparse
from bs4 import BeautifulSoup
from .base import BaseParser


class FinatecParser(BaseParser):

    # Âncora de listagem oficial (usar sempre esta URL base para os links)
    LIST_URL = 'https://www.finatec.org.br/transparencia/licitacoes/informacoes'

    def parse(self, html, url_base):
        soup = BeautifulSoup(html, 'html.parser')
        editais = []
        vistos = set()

        # Base da página atual (para compor URLs absolutas das âncoras)
        current_base = url_base.split('#')[0] if url_base else self.LIST_URL

        for item in soup.select('.accordion-group'):
            a_titulo = item.select_one('.accordion-heading a.accordion-toggle')
            inner = item.select_one('.accordion-inner')
            if not a_titulo:
                continue

            titulo = self.limpar_texto(a_titulo.get_text())
            if not titulo or len(titulo) < 5:
                continue

            # ID estável: href="#23479" → âncora
            anchor = a_titulo.get('href', '')
            if anchor.startswith('#'):
                # URL canônica aponta para a LISTA (não para a página do item,
                # porque não existe página individual).
                url = f'{current_base}{anchor}'
                chave_dedup = anchor
            else:
                url = self.resolver_url(anchor, url_base)
                chave_dedup = url

            if chave_dedup in vistos:
                continue
            vistos.add(chave_dedup)

            # PDF principal: primeiro <a> cujo texto contenha "edital"; senão o 1º <a>
            pdf_url = ''
            if inner:
                links = [a for a in inner.find_all('a', href=True) if a.get('href')]
                link_edital = next(
                    (a for a in links if 'edital' in a.get_text().lower()),
                    None
                )
                chosen = link_edital or (links[0] if links else None)
                if chosen:
                    pdf_url = self._normalizar_url_pdf(
                        self.resolver_url(chosen['href'], url_base)
                    )

            # Data: esta página lista apenas licitações ABERTAS agora, e o ano já
            # vem embutido no título ("nº 165/2026"). NÃO emitimos data de propósito:
            # um proxy 01/01/AAAA faria a fonte inteira parecer antiga e seria
            # descartada pelo filtro EDITAL_MAX_DIAS. Sem data, o item só é derrubado
            # se o título trouxer palavra-chave + número/ano antigo (não é o caso
            # aqui, e a página só lista abertas). Volume: MAX_ITENS_POR_FONTE.
            edital = {
                'titulo': titulo,
                'url': url,       # URL estável da listagem (link "Ver na fonte")
                'data': '',
            }
            if pdf_url:
                # Campo extra: o notifier usa para enviar PDF inline se existir
                edital['pdf_url'] = pdf_url

            editais.append(edital)

        return editais

    def _normalizar_url_pdf(self, url):
        """Garante https:// e escapamento de caracteres especiais (espaço, acento)."""
        if not url:
            return ''
        if url.startswith('http://'):
            url = 'https://' + url[len('http://'):]
        # Escapa path mas mantém /
        try:
            p = urlparse(url)
            safe_path = quote(p.path)
            url = f'{p.scheme}://{p.netloc}{safe_path}'
            if p.query:
                url += f'?{p.query}'
        except Exception:
            pass
        return url
