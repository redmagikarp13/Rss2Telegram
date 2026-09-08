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
from parsers.base import BaseParser
import browser


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


# Identificador de edital com ano embutido: "Edital Nº 1823/2026",
# "Chamada 12/2026", "Processo Seletivo 279-2026", "EDITAL n.º 165/2020".
# Exige a palavra-chave por perto para não confundir o número/ano com um valor
# qualquer do título (um falso-positivo antigo descartaria um edital vigente).
_SINAL_ANO_TITULO = re.compile(
    r'\b(?:edital|chamada|processo\s*seletivo|sele[çc][ãa]o|concurso|bolsa|'
    r'aux[íi]lio|licita[çc][ãa]o|preg[ãa]o|termo|conv[êe]nio|projeto|fomento|'
    r'pr[êe]mio|fluxo\s*cont[íi]nuo)\b'
    r'[^\d]{0,24}?\d{1,4}\s*[/\-]\s*(20\d{2})\b',
    re.IGNORECASE,
)


# Mesmo sinal, mas sem a palavra-chave. Necessário porque há fontes cujo título
# veio pronto do <a> e é só o número: o SEAD UFES publica '23/2026', '22/2026',
# '01/2026 – Chamada – Livro comemorativo' (88 itens do histórico de produção só
# com o ano como título). O anchor em ^ é o que torna isso seguro: um valor
# qualquer no meio da frase ('auxílio de R$ 1.200/2025') não pode virar
# evidência de descarte.
_SINAL_ANO_LIVRE = re.compile(r'^\s*(\d{1,4})\s*[/\-]\s*(20\d{2})(?!\d)')

# Ano no caminho da URL: uploads do WordPress por data, slug de notícia, carimbo
# no nome do arquivo. Evidência FRACA — um edital de 2026 pode apontar para um
# anexo gravado em /uploads/2022/05/ — então só ordena, nunca descarta.
_SINAL_ANO_URL = (
    re.compile(r'/uploads/(20\d{2})/(\d{1,2})/'),
    re.compile(r'/(20\d{2})/(\d{1,2})/'),
    re.compile(r'/(20\d{2})-(\d{1,2})/'),
    re.compile(r'[-_](20\d{2})(\d{2})(\d{2})'),
    re.compile(r'(20\d{2})(\d{2})(\d{2})'),
    re.compile(r'[?&](?:data|dt|ano|year)=(20\d{2})'),
    # Ano sozinho, delimitado, dentro do slug: 'edital-05-dead-2026-processo-…'.
    # Visto na rodada de ensaio — é a forma do WordPress para notícia SEM data no
    # slug, e sem este padrão o item cai no fim da fila (data_efetiva None ordena
    # com datetime.min), justamente o perfil que o teto por estado corta primeiro.
    # Exige delimitador dos dois lados para não ler '20260' como ano.
    re.compile(r'[-_/.](20\d{2})(?=[-_/.?&]|$)'),
)


def _ano_valido(ano):
    """Ano plausível de edital: não o século I nem um ano futurista além do próximo."""
    return 2000 <= ano <= datetime.now().year + 1


def _ano_do_titulo(titulo):
    """Ano do identificador do edital ('Edital 1823/2026' -> 2026), ou None.

    Muitas fontes não publicam data de listagem: emitem data='' de propósito
    (ead_editais, fapes_es, unac_es, cnpq_govbr, finatec, unicamp_prp) porque um
    proxy 01/01/AAAA faria a fonte inteira parecer velha. O ano do identificador
    é o único sinal de recência disponível nelas.
    """
    if not titulo:
        return None
    anos = []
    match = _SINAL_ANO_TITULO.search(titulo)
    if match and _ano_valido(int(match.group(1))):
        anos.append(int(match.group(1)))
    livre = _SINAL_ANO_LIVRE.search(titulo)
    if livre and _ano_valido(int(livre.group(2))):
        anos.append(int(livre.group(2)))
    if not anos:
        return None
    # max(): mesma lógica benéfica do 31/12 abaixo. Um título que cita o edital
    # antigo e a retificação vigente não deve cair por mencionar o ano velho.
    return max(anos)


def _ano_da_url(url):
    """Ano mais recente encontrado na URL, ou None. Ver _SINAL_ANO_URL: só ordena.

    max() entre os padrões e entre as ocorrências pela mesma razão de
    _ano_do_titulo: '/2020/01/noticia-20260512.html' é uma página de 2020 com
    carimbo de 2026, e a leitura benéfica fica com 2026.
    """
    anos = []
    for rx in _SINAL_ANO_URL:
        for grupos in rx.findall(url or ''):
            for token in (grupos if isinstance(grupos, tuple) else (grupos,)):
                if token.startswith('20') and _ano_valido(int(token)):
                    anos.append(int(token))
    return max(anos) if anos else None


def data_efetiva(edital):
    """Melhor estimativa de publicação, ou None quando não há sinal nenhum.

    Ordem: data real do feed/listagem -> 31/12 do ano mais recente entre título e
    URL. Usamos 31/12 (e não 01/01) de propósito: é a leitura mais benéfica do
    ano, então um edital do ano corrente nunca cai por causa da janela
    deslizante, enquanto 'Edital 12/2020' continua caindo fora de 90 dias.

    Esta função responde "o que é mais recente" e por isso aceita a URL: ela
    define a ordem (quem sobrevive aos tetos por fonte e por estado). Para
    DESCARTAR use data_filtravel(), que ignora a evidência fraca.
    """
    data = _parse_date(edital.get('data', ''))
    if data:
        return data
    anos = [a for a in (_ano_do_titulo(edital.get('titulo', '')),
                        _ano_da_url(edital.get('url', ''))) if a]
    if anos:
        return datetime(max(anos), 12, 31)
    return None


def data_filtravel(edital):
    """Estimativa usada para DESCARTAR: apenas evidência forte.

    Data real do feed/listagem ou ano do identificador no título. A URL fica de
    fora porque o caminho de upload data o ARQUIVO, não o edital. Mantém o viés
    fail-open do filtro: sem evidência forte o item fica, porque descartar por
    palpite silenciaria uma fonte inteira.
    """
    data = _parse_date(edital.get('data', ''))
    if data:
        return data
    ano = _ano_do_titulo(edital.get('titulo', ''))
    if ano:
        return datetime(ano, 12, 31)
    return None


def _filtrar_por_data(editais, max_dias):
    """Remove editais cuja evidência forte de data cai fora da janela.

    Usa data_filtravel(), não data_efetiva(): o ano no caminho da URL data o
    arquivo anexado, não a oportunidade, e serviria para descartar um edital
    vigente.

    Itens sem NENHUM sinal forte (nem campo `data`, nem número/ano no título)
    continuam mantidos: sem informação não há como julgar, e descartá-los
    silenciaria fontes inteiras.
    """
    if max_dias <= 0:
        return editais

    cutoff = datetime.now() - timedelta(days=max_dias)
    filtrados = []
    sem_sinal = 0
    for edital in editais:
        data_ref = data_filtravel(edital)
        if data_ref is None:
            sem_sinal += 1
            filtrados.append(edital)
            continue
        if data_ref >= cutoff:
            filtrados.append(edital)
    if sem_sinal:
        print(f"   ℹ️  {sem_sinal} edital(is) sem nenhum sinal de data foram mantidos")
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
        """Lê o feed RSS. Retorna (editais, motivo).

        O ponto inteiro é a diferença entre os dois valores possíveis de `editais`:

          - lista, mesmo vazia -> o feed foi lido com sucesso. Lista vazia significa
            'nenhum item dentro da janela de recência', que é o resultado esperado de
            uma fonte quieta, e NÃO é motivo para ir raspar o HTML da página.
          - None -> não consegui ler o feed; `motivo` diz por quê.

        Antes, o `return editais if editais else None` colapsava os dois casos em
        'falhou'. Resultado: toda fonte cujo último edital era mais velho que a janela
        passava a ser raspada pelo HTML da página -- e página tem menu, rodapé e link
        institucional. Em 08/09/2026 o feed do Cefor-UAB esvaziou a janela de 90 dias
        (último edital em 10/06), o scraper foi para o HTML e dois itens do cardápio
        do site chegaram ao chat como 'Novo Edital Encontrado!'.
        """
        if not feed_url:
            return None, 'sem feed configurado'

        try:
            response = requests.get(
                feed_url,
                headers=self.HEADERS,
                timeout=self.timeout,
                allow_redirects=True
            )

            if response.status_code != 200:
                return None, f'HTTP {response.status_code}'

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
                ct = content_type.strip() or 'indisponivel'
                return None, f'resposta não é XML (Content-Type: {ct})'

            feed = feedparser.parse(texto)

            if not feed.entries:
                return None, 'feed sem entries'

            editais = []
            for entry in feed.entries:
                titulo = entry.get('title', '').strip()
                url = entry.get('link', '').strip()

                # Data: prioriza struct_time parseado (vira dd/mm/aaaa amigável e
                # filtrável); cai para a string crua apenas se não houver parsed.
                data_str = ''
                published = entry.get('published_parsed') or entry.get('updated_parsed')
                if published:
                    try:
                        data_str = datetime(*published[:6]).strftime('%d/%m/%Y')
                    except Exception:
                        data_str = ''
                if not data_str:
                    data_str = (entry.get('published') or entry.get('updated') or '').strip()

                # Filtro de data — mesma regra do passe global (feed → título),
                # incluindo o fail-open quando nem o feed nem o título dão sinal.
                if self.max_dias > 0:
                    data_ref = data_filtravel({'data': data_str, 'titulo': titulo})
                    if data_ref and data_ref < datetime.now() - timedelta(days=self.max_dias):
                        continue

                if titulo and url:
                    item = {
                        'titulo': titulo,
                        'url': url,
                        'data': data_str,
                    }
                    # Descrição: RSS traz summary e/ou content (possivelmente HTML)
                    descricao_bruta = entry.get('summary') or entry.get('description') or ''
                    if not descricao_bruta:
                        content = entry.get('content')
                        if content and isinstance(content, list):
                            descricao_bruta = content[0].get('value', '')
                    descricao = BaseParser.limpar_descricao(descricao_bruta)
                    # Não deixar a descrição repetindo exatamente o título
                    if descricao and descricao.lower().strip() != titulo.lower().strip():
                        item['descricao'] = descricao
                    editais.append(item)

            lidos = len(feed.entries)
            if self.max_dias > 0:
                resumo = f'{len(editais)}/{lidos} entries na janela de {self.max_dias} dias'
            else:
                resumo = f'{len(editais)}/{lidos} entries (recência desligada)'
            return editais, resumo

        except Exception as exc:
            return None, f'{type(exc).__name__}: {exc}'

    def _tentar_scraping(self, scrape_url, parser_nome, render=False):
        """Tenta ler editais via web scraping. Retorna lista de editais ou lista vazia."""
        if not scrape_url or not parser_nome:
            return []

        parser = get_parser(parser_nome)

        # 0. Renderização via browser headless (para portais que exigem JavaScript).
        #    Se Playwright não estiver disponível, renderizar() retorna None e
        #    seguimos para o caminho requests padrão.
        if render:
            html = browser.renderizar(scrape_url)
            if html:
                try:
                    return parser.parse(html, scrape_url)
                except Exception:
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
        render = site.get('render', False)

        print(f"  🔍 {nome}... ", end='', flush=True)

        # 1. Tentar RSS primeiro. O teste é `is not None`, e não a truthiness da
        # lista: foi confundir 'feed lido e vazio na janela' com 'falha de leitura'
        # que mandou uma fonte quieta para a raspagem do HTML da página (causa dos
        # links de menu notificados como edital em 08/09/2026).
        editais, motivo_rss = self._tentar_rss(feed_url)
        rss_lido = editais is not None
        if rss_lido:
            metodo = 'RSS'
        else:
            # 2. Fallback para web scraping (com browser headless se render=True)
            editais = self._tentar_scraping(scrape_url, parser_nome, render)
            metodo = 'Browser' if (render and editais) else 'Scraping'

        # Só vale reclamar do RSS quando havia RSS para tentar: fonte configurada sem
        # feed_url raspa HTML por decisão, não por falha.
        rss_falhou = (not rss_lido) and bool(feed_url)

        if editais:
            # Adicionar metadados do site
            for edital in editais:
                edital['site'] = nome
                edital['site_url'] = scrape_url or feed_url
                edital['emoji'] = site.get('emoji', '📋')

            # Todo fallback sai no log com o motivo. Sem isto, 'via Scraping' não
            # dizia que o RSS tinha falhado nem por quê -- foi o que tornou o
            # incidente de 08/09 caro de rastrear (precisei diffar dois bancos de
            # estado para chegar a dois títulos).
            sufixo = f' | RSS falhou: {motivo_rss}' if rss_falhou else ''
            print(f"✅ {len(editais)} edital(is) via {metodo}{sufixo}")
        elif rss_lido:
            # Fonte quieta e saudável: o feed respondeu, só não há nada na janela.
            # Sai como OK e não como aviso, porque não há nada errado com a fonte.
            print(f"✅ 0 edital(is) via RSS ({motivo_rss})")
        else:
            editais = []
            detalhe = f' | RSS: {motivo_rss}' if rss_falhou else ''
            print(f"⚠️ Nenhum edital encontrado{detalhe}")

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
        else:
            print("📅 Filtro de data DESATIVADO (EDITAL_MAX_DIAS=0): qualquer ano passa")

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
                # Ordena do mais recente para o mais antigo ANTES de cortar, para que
                # o teto preserve os novos. Arquivos Joomla/WordPress (Proex, Agifes,
                # FACTO) entregam o historico inteiro e o corte na ordem da pagina
                # manteria justamente os mais velhos. Sem sinal de data vai para o fim
                # e a ordenacao estavel preserva a ordem da propria listagem.
                editais.sort(key=lambda e: data_efetiva(e) or datetime.min, reverse=True)
                if len(editais) > self.max_itens_por_fonte:
                    print(f"   ⚡ {site}: limitado de {len(editais)} para {self.max_itens_por_fonte}")
                todos_editais.extend(editais[:self.max_itens_por_fonte])
        else:
            print("🔢 Teto por fonte DESATIVADO (MAX_ITENS_POR_FONTE=0): listagens completas passam")

        print(f"📋 {len(todos_editais)} edital(is) após filtros\n")

        # Libera o Chromium headless, se tiver sido usado
        browser.fechar_navegador()

        return todos_editais
