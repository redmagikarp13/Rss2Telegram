"""
Engine principal do scraper — abordagem HÍBRIDA.
1. Tenta ler o feed RSS (feedparser)
2. Se falhar ou retornar vazio, faz web scraping (BeautifulSoup)
"""
import requests
import feedparser
import time
import re
from datetime import datetime, timedelta
from parsers import get_parser


# ══════════════════════════════════════════════════════════
# Utilidades de parsing de data
# ══════════════════════════════════════════════════════════

def _parse_date(data_str):
    """Tenta converter uma string de data em datetime. Suporta vários formatos."""
    if not data_str:
        return None

    data_str = data_str.strip()

    # Formato dd/mm/aaaa ou d/m/aaaa
    match = re.search(r'(\d{1,2})/(\d{1,2})/(\d{2,4})', data_str)
    if match:
        dia, mes, ano = int(match.group(1)), int(match.group(2)), int(match.group(3))
        if ano < 100:
            ano += 2000
        try:
            return datetime(ano, mes, dia)
        except ValueError:
            pass

    # Formato ISO: aaaa-mm-dd
    match = re.search(r'(\d{4})-(\d{2})-(\d{2})', data_str)
    if match:
        try:
            return datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except ValueError:
            pass

    # Meses em português (abreviado e completo)
    meses_pt = {
        'janeiro': 1, 'fevereiro': 2, 'março': 3, 'marco': 3, 'abril': 4,
        'maio': 5, 'junho': 6, 'julho': 7, 'agosto': 8,
        'setembro': 9, 'outubro': 10, 'novembro': 11, 'dezembro': 12,
        'jan': 1, 'fev': 2, 'mar': 3, 'abr': 4, 'mai': 5, 'jun': 6,
        'jul': 7, 'ago': 8, 'set': 9, 'out': 10, 'nov': 11, 'dez': 12,
    }
    for nome_mes, num_mes in meses_pt.items():
        if nome_mes in data_str.lower():
            match = re.search(r'(\d{1,2})\s+de\s+(\w+)', data_str, re.IGNORECASE)
            if not match:
                match = re.search(r'(\d{1,2})\s+(\w+)', data_str, re.IGNORECASE)
            if match:
                dia = int(match.group(1))
                ano_match = re.search(r'(\d{4})', data_str)
                ano = int(ano_match.group(1)) if ano_match else datetime.now().year
                try:
                    return datetime(ano, num_mes, dia)
                except ValueError:
                    pass

    return None


def _filtrar_por_data(editais, max_dias):
    """Remove editais com data mais antiga que max_dias. Editais sem data são mantidos."""
    if max_dias <= 0:
        return editais

    cutoff = datetime.now() - timedelta(days=max_dias)
    filtrados = []
    for edital in editais:
        data_str = edital.get('data', '')
        if not data_str:
            # Sem data → mantém (não podemos filtrar sem informação)
            filtrados.append(edital)
            continue
        data_parsed = _parse_date(data_str)
        if data_parsed is None:
            # Data não parseável → mantém
            filtrados.append(edital)
            continue
        if data_parsed >= cutoff:
            filtrados.append(edital)
    return filtrados


class ScraperEngine:
    """Motor híbrido: RSS + Web Scraping."""

    HEADERS = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/120.0.0.0 Safari/537.36'
        ),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
    }

    def __init__(self, sites, timeout=30, max_dias=0, max_itens_por_fonte=0):
        self.sites = sites
        self.timeout = timeout
        self.max_dias = max_dias
        self.max_itens_por_fonte = max_itens_por_fonte

    def _tentar_rss(self, feed_url):
        """Tenta ler editais via RSS feed. Retorna lista de editais ou None se falhar."""
        if not feed_url:
            return None

        try:
            response = requests.get(
                feed_url,
                headers=self.HEADERS,
                timeout=self.timeout,
                allow_redirects=True
            )

            if response.status_code != 200:
                return None

            # Verificar se o conteúdo é realmente RSS/XML
            content_type = response.headers.get('Content-Type', '')
            texto = response.text.strip()

            if not texto or (
                'xml' not in content_type.lower() and
                'rss' not in content_type.lower() and
                not texto.startswith('<?xml') and
                not texto.startswith('<rss') and
                not texto.startswith('<feed')
            ):
                return None

            feed = feedparser.parse(texto)

            if not feed.entries:
                return None

            editais = []
            for entry in feed.entries:
                titulo = entry.get('title', '').strip()
                url = entry.get('link', '').strip()
                data = entry.get('published', entry.get('updated', '')).strip()

                # Tentar converter data do feedparser para string dd/mm/aaaa
                data_str = data
                if not data_str:
                    published = entry.get('published_parsed') or entry.get('updated_parsed')
                    if published:
                        try:
                            dt = datetime(*published[:6])
                            data_str = dt.strftime('%d/%m/%Y')
                        except Exception:
                            pass

                # Filtro de data
                if self.max_dias > 0 and data_str:
                    data_parsed = _parse_date(data_str)
                    if data_parsed:
                        cutoff = datetime.now() - timedelta(days=self.max_dias)
                        if data_parsed < cutoff:
                            continue

                if titulo and url:
                    editais.append({
                        'titulo': titulo,
                        'url': url,
                        'data': data_str,
                    })

            return editais if editais else None

        except Exception:
            return None

    def _tentar_scraping(self, scrape_url, parser_nome):
        """Tenta ler editais via web scraping. Retorna lista de editais ou lista vazia."""
        if not scrape_url or not parser_nome:
            return []

        try:
            response = requests.get(
                scrape_url,
                headers=self.HEADERS,
                timeout=self.timeout,
                verify=True,
                allow_redirects=True
            )
            response.raise_for_status()
            response.encoding = response.apparent_encoding or 'utf-8'

            parser = get_parser(parser_nome)
            return parser.parse(response.text, scrape_url)

        except requests.exceptions.SSLError:
            # Fallback sem verificação SSL
            try:
                response = requests.get(
                    scrape_url,
                    headers=self.HEADERS,
                    timeout=self.timeout,
                    verify=False,
                    allow_redirects=True
                )
                response.encoding = response.apparent_encoding or 'utf-8'
                parser = get_parser(parser_nome)
                return parser.parse(response.text, scrape_url)
            except Exception:
                return []

        except Exception:
            return []

    def scrape_site(self, site):
        """Faz scraping de um único site usando abordagem híbrida."""
        nome = site['name']
        feed_url = site.get('feed_url')
        scrape_url = site.get('scrape_url')
        parser_nome = site.get('parser')

        print(f"  🔍 {nome}... ", end='', flush=True)

        # 1. Tentar RSS primeiro
        editais = self._tentar_rss(feed_url)
        if editais:
            metodo = 'RSS'
        else:
            # 2. Fallback para web scraping
            editais = self._tentar_scraping(scrape_url, parser_nome)
            metodo = 'Scraping'

        if editais:
            # Adicionar metadados do site
            for edital in editais:
                edital['site'] = nome
                edital['site_url'] = scrape_url or feed_url
                edital['emoji'] = site.get('emoji', '📋')

            print(f"✅ {len(editais)} edital(is) via {metodo}")
        else:
            editais = []
            print(f"⚠️ Nenhum edital encontrado")

        return editais

    def scrape_todos(self):
        """Faz scraping de todos os sites configurados."""
        print(f"\n🌐 Iniciando varredura de {len(self.sites)} fonte(s)...\n")

        todos_editais = []

        for site in self.sites:
            editais = self.scrape_site(site)
            if editais:
                todos_editais.extend(editais)

            # Pausa entre requisições
            time.sleep(1.5)

        print(f"\n📋 {len(todos_editais)} edital(is) encontrado(s) antes dos filtros")

        # Filtro por data (janela deslizante)
        if self.max_dias > 0:
            antes = len(todos_editais)
            todos_editais = _filtrar_por_data(todos_editais, self.max_dias)
            removidos = antes - len(todos_editais)
            if removidos > 0:
                print(f"📅 Filtro de data (>{self.max_dias} dias): {removidos} edital(is) antigo(s) removido(s)")

        # Limite de itens por fonte
        if self.max_itens_por_fonte > 0:
            por_site = {}
            for edital in todos_editais:
                site = edital['site']
                if site not in por_site:
                    por_site[site] = []
                por_site[site].append(edital)

            todos_editais = []
            for site, editais in por_site.items():
                if len(editais) > self.max_itens_por_fonte:
                    print(f"   ⚡ {site}: limitado de {len(editais)} para {self.max_itens_por_fonte}")
                todos_editais.extend(editais[:self.max_itens_por_fonte])

        print(f"📋 {len(todos_editais)} edital(is) após filtros\n")

        return todos_editais
