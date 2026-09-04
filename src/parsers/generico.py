"""
Parser genérico para sites institucionais (IFMG, IFSC, UFRJ, USP, etc.).
Busca links com palavras-chave relacionadas a editais.
"""
from bs4 import BeautifulSoup
from .base import BaseParser


class GenericoParser(BaseParser):
    """Parser genérico que funciona para a maioria dos sites institucionais."""

    # Palavras-chave que indicam editais relevantes
    KEYWORDS = [
        'edital', 'bolsa', 'chamada', 'seleção', 'seletivo', 'processo',
        'pibic', 'pibiti', 'pibex', 'pesquisa', 'extensão', 'monitoria',
        'programa', 'iniciação', 'científica', 'auxílio', 'oportunidade',
    ]

    # Seletores da área de conteúdo, do mais específico ao mais genérico
    CONTENT_SELECTORS = (
        '#content, #conteudo, .content, .conteudo, main, '
        '[role="main"], .page-content, .entry-content, '
        '#content-core, .main-content, article'
    )

    def parse(self, html, url_base):
        soup = BeautifulSoup(html, 'html.parser')

        # Remover header, footer, nav, sidebar para evitar links de navegação
        for tag in soup.select('header, footer, nav, .sidebar, .menu, #menu, .breadcrumb'):
            tag.decompose()

        root_body = soup.body if soup.body else soup

        # 1. Tenta o container de conteúdo identificado pelos seletores
        conteudo = soup.select_one(self.CONTENT_SELECTORS)
        vistos = set()
        editais = []
        if conteudo is not None:
            editais, vistos = self._coletar(conteudo, url_base, vistos, set())

        # 2. Fallback: se o container escolhido veio praticamente vazio
        #    (ex: Drupal que coloca o conteúdo num bloco fora de #content),
        #    varre o body inteiro — já sem a "chrome" removida acima.
        if not editais and conteudo is not root_body:
            editais, vistos = self._coletar(root_body, url_base, vistos, set())

        return editais

    def _coletar(self, raiz, url_base, vistos, textos_vistos):
        """Varre os <a> de `raiz`, coletando editais que casem com as keywords."""
        resultados = []
        links = raiz.find_all('a', href=True) if raiz else []

        for link in links:
            texto = self.limpar_texto(link.get_text())
            href = link.get('href', '')

            if not texto or not href or len(texto) < 10:
                continue

            url = self.resolver_url(href, url_base)

            # Evitar duplicatas de URL e de texto
            if url in vistos or texto in textos_vistos:
                continue

            texto_lower = texto.lower()
            href_lower = href.lower()
            if any(kw in texto_lower or kw in href_lower for kw in self.KEYWORDS):
                data = self.extrair_data_do_element_pai(link)
                vistos.add(url)
                textos_vistos.add(texto)
                item = {
                    'titulo': texto,
                    'url': url,
                    'data': data,
                }
                descricao = self.extrair_descricao_do_contexto(link, texto)
                if descricao:
                    item['descricao'] = descricao
                resultados.append(item)

        return resultados, vistos
