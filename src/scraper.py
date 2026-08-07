"""
Engine principal do scraper — abordagem HÍBRIDA.
1. Tenta ler o feed RSS (feedparser)
2. Se falhar ou retornar vazio, faz web scraping (BeautifulSoup)
"""
import requests
import feedparser
import time
from parsers import get_parser


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

    def __init__(self, sites, timeout=30):
        self.sites = sites
        self.timeout = timeout

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

                if titulo and url:
                    editais.append({
                        'titulo': titulo,
                        'url': url,
                        'data': data,
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
        stats = {'rss': 0, 'scraping': 0, 'vazio': 0}

        for site in self.sites:
            editais = self.scrape_site(site)
            if editais:
                todos_editais.extend(editais)
            else:
                stats['vazio'] += 1

            # Pausa entre requisições
            time.sleep(1.5)

        print(f"\n📊 Varredura finalizada:")
        print(f"   📋 {len(todos_editais)} edital(is) encontrado(s)")
        print(f"   ⚠️ {stats['vazio']} fonte(s) sem resultado\n")

        return todos_editais
