"""
Parser para PROEX IFES (proex.ifes.edu.br/editais).
Estrutura: Joomla com editais em fluxo linear.

Organização:
- <h2>Editais abertos</h2>
- <h3>2026</h3> (agrupamento por ano)
- <hr> (separador — NÃO confiável)
- <p><strong>TÍTULO DO EDITAL n.º XX/AAAA - descrição</strong></p>
- <p><a href="...pdf">Link do documento</a></p> (N links pertencem ao edital acima)

Estratégia: percorre os filhos de .item-page em ordem, usa <strong> e <h3> como
âncoras de título de edital, e associa os <a> seguintes ao grupo.
"""
import re
from bs4 import BeautifulSoup
from .base import BaseParser


class ProexIfesParser(BaseParser):

    # Palavras que indicam um edital relevante no texto do <strong>
    TITLE_PATTERNS = re.compile(
        r'(edital|chamada|sele[çc][ãa]o|processo\s*seletivo|bolsa|aux[íi]lio|pr[êe]mio)',
        re.IGNORECASE
    )

    # Filtrar links de ruído (formulários Google, YouTube, navegação)
    EXCLUDE_URL_PATTERNS = re.compile(
        r'(docs\.google\.com|forms\.gle|youtube\.com|youtu\.be|'
        r'instagram\.com|facebook\.com|#|javascript:)',
        re.IGNORECASE
    )

    # Regex para extrair data da URL (ex: /uploads/2026/05/)
    URL_DATE_PATTERN = re.compile(r'/(\d{4})/(\d{2})/')

    # Regex para extrair número/ano do edital (ex: "07/2026" do título)
    EDITAL_NUMERO_PATTERN = re.compile(r'(\d{1,2})\s*/\s*(\d{4})')

    def parse(self, html, url_base):
        soup = BeautifulSoup(html, 'html.parser')
        editais = []

        # Remover blocos de navegação e rodapé
        for tag in soup.select('header, footer, nav, #nav-main, .breadcrumbs, '
                               '.pull-right.article-index, .pagenav, #backtoTop, '
                               '.document-actions, .content-footer, #spc, '
                               'ul.actions, .btns-social-like'):
            tag.decompose()

        # Encontrar o container de conteúdo
        content = soup.select_one('div.item-page, #content-core, #content, main')
        if not content:
            content = soup.body if soup.body else soup

        # Coletar elementos na ordem DOM
        # Estratégia: encontrar todos os <p><strong>, e para cada um, coletar
        # os <a> seguintes até o próximo <strong> ou <h3> de seção.
        elements = self._flatten_content(content)

        current_title = None
        current_year = None  # do <h3>
        urls_vistas = set()

        for elem in elements:
            # Atualizar ano corrente se encontrar <h3> ou <h2>
            if elem.name in ('h2', 'h3'):
                text = self.limpar_texto(elem.get_text())
                # <h3>2026</h3> = apenas o ano
                if re.match(r'^\d{4}$', text):
                    current_year = int(text)
                # <h2>Editais encerrados</h2> = parar
                elif 'encerrado' in text.lower():
                    break
                # <h2>Editais abertos</h2> = resetar título
                elif 'aberto' in text.lower() or 'chamada' in text.lower():
                    current_title = None
                else:
                    # Título em <h3> (exceção citada na análise)
                    if self.TITLE_PATTERNS.search(text) and len(text) > 15:
                        current_title = text
                        current_year = self._extrair_ano_do_titulo(text) or current_year
                continue

            # <p><strong> = título de edital
            if elem.name == 'p':
                strong = elem.find('strong')
                if strong:
                    strong_text = self.limpar_texto(strong.get_text())
                    # Só atualizar título se for relevante (contém keyword)
                    if strong_text and len(strong_text) > 10:
                        if self.TITLE_PATTERNS.search(strong_text):
                            current_title = self._normalizar_titulo(strong_text)
                            current_year = self._extrair_ano_do_titulo(strong_text) or current_year
                        elif current_title:
                            # Link/parágrafo de resultado pertence ao edital atual
                            # (deixa current_title intacto)
                            pass
                    else:
                        current_title = None  # <p><strong></strong> vazio ou irrelevante
                    continue

            # Se este <p> (sem strong) contém um <a>, processar link
            for link in elem.find_all('a', href=True):
                href = link.get('href', '')
                link_text = self.limpar_texto(link.get_text())
                result = self._processar_link(
                    href, link_text, current_title, current_year, url_base
                )
                if result and result['url'] not in urls_vistas:
                    urls_vistas.add(result['url'])
                    editais.append(result)
                continue

        # Também cobrir o caso em que <a> está solto (fora de <p>)
        for elem in elements:
            if elem.name == 'a' and elem.get('href'):
                if elem.parent and elem.parent.name == 'p':
                    continue  # já processado acima
                href = elem.get('href', '')
                link_text = self.limpar_texto(elem.get_text())
                result = self._processar_link(
                    href, link_text, current_title, current_year, url_base
                )
                if result and result['url'] not in urls_vistas:
                    urls_vistas.add(result['url'])
                    editais.append(result)

        return editais

    def _flatten_content(self, container):
        """Retorna elementos relevantes na ordem de documento (sem duplicar)."""
        seen = set()
        out = []
        for el in container.descendants:
            if el.name in ('h2', 'h3', 'p') and id(el) not in seen:
                seen.add(id(el))
                out.append(el)
        return out

    def _processar_link(self, href, link_text, current_title, current_year, url_base):
        """Retorna dict de edital se o link for válido, senão None."""
        if not href:
            return None

        # Ignorar ruído
        if self.EXCLUDE_URL_PATTERNS.search(href):
            return None

        # Resolver URL relativa
        url = self.resolver_url(href, url_base)
        if not url:
            return None

        # Ignorar link sem texto E sem título de edital
        if not link_text and not current_title:
            return None

        # Construir título: edital + descrição do anexo
        if current_title:
            if link_text and link_text.lower() not in ('clique aqui', 'aqui', ''):
                titulo = f"{current_title} — {link_text}"
            else:
                titulo = current_title
        else:
            if len(link_text) < 15:
                return None
            if not self.TITLE_PATTERNS.search(link_text):
                return None
            titulo = link_text

        # Extrair data: prioriza da URL (ex: /2026/05/), senão do ano atual
        data = self._extrair_data_da_url(href) or ''

        return {
            'titulo': self._normalizar_titulo(titulo),
            'url': url,
            'data': data,
        }

    def _extrair_data_da_url(self, href):
        """Extrai 'dd/mm/aaaa' (usando dia=01) do padrão /YYYY/MM/ na URL."""
        if not href:
            return ''
        match = self.URL_DATE_PATTERN.search(href)
        if match:
            ano = int(match.group(1))
            mes = int(match.group(2))
            if 1990 <= ano <= 2100 and 1 <= mes <= 12:
                return f"01/{mes:02d}/{ano}"
        return ''

    def _extrair_ano_do_titulo(self, titulo):
        """Extrai o ano do edital (ex: 'Edital 07/2026' → 2026)."""
        if not titulo:
            return None
        match = self.EDITAL_NUMERO_PATTERN.search(titulo)
        if match:
            ano = int(match.group(2))
            if 2000 <= ano <= 2100:
                return ano
        return None

    def _normalizar_titulo(self, texto):
        """Normaliza espaços, &nbsp; e caracteres especiais."""
        if not texto:
            return ''
        texto = texto.replace('\xa0', ' ').replace('&nbsp;', ' ')
        texto = re.sub(r'\s+', ' ', texto)
        return texto.strip()
