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

    def parse(self, html, url_base):
        editais = []
        soup = BeautifulSoup(html, 'html.parser')

        # Remover header, footer, nav, sidebar para evitar links de navegação
        for tag in soup.select('header, footer, nav, .sidebar, .menu, #menu, .breadcrumb'):
            tag.decompose()

        # Buscar todos os links na área de conteúdo
        conteudo = soup.select_one(
            '#content, #conteudo, .content, .conteudo, main, '
            '[role="main"], .page-content, .entry-content, '
            '#content-core, .main-content, article'
        )

        if not conteudo:
            conteudo = soup.body if soup.body else soup

        links = conteudo.find_all('a', href=True) if conteudo else []

        urls_vistas = set()
        for link in links:
            texto = self.limpar_texto(link.get_text())
            href = link.get('href', '')

            if not texto or not href or len(texto) < 10:
                continue

            url = self.resolver_url(href, url_base)

            # Evitar duplicatas
            if url in urls_vistas:
                continue

            # Verificar se o texto contém alguma keyword relevante
            texto_lower = texto.lower()
            href_lower = href.lower()
            if any(kw in texto_lower or kw in href_lower for kw in self.KEYWORDS):
                data = self.extrair_data_do_element_pai(link)
                urls_vistas.add(url)
                editais.append({
                    'titulo': texto,
                    'url': url,
                    'data': data,
                })

        return editais
