"""
Configuração dos sites monitorados e variáveis de ambiente.
Baseado nas URLs do projeto original Rss2Telegram + universidades e fundações adicionais.
"""
import os
from datetime import datetime


def get_variable(variable, default=None):
    """Lê variável de ambiente ou de arquivo .txt (compatível com projeto anterior)."""
    env_val = os.environ.get(variable)
    if env_val:
        return env_val
    try:
        with open(f'{variable}.txt', 'r', encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        return default


# Telegram
BOT_TOKEN = get_variable('BOT_TOKEN')
CHAT_ID = get_variable('DESTINATION', get_variable('CHAT_ID'))
DRYRUN = get_variable('DRYRUN', 'false').lower() in ('true', '1', 'yes')
FIRST_RUN_SILENT = get_variable('FIRST_RUN_SILENT', 'true').lower() in ('true', '1', 'yes')

# Filtro de data — janela deslizante (em dias). 0 = desativado
EDITAL_MAX_DIAS = int(get_variable('EDITAL_MAX_DIAS', '0'))

# Limite de itens por fonte por execução. 0 = sem limite
MAX_ITENS_POR_FONTE = int(get_variable('MAX_ITENS_POR_FONTE', '0'))

# Arquivo marcador de primeira execução já concluída (proteção contra DB vazio)
MARCADOR_PRIMEIRA_EXEC_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', '.primeira_exec_concluida'
)

# Banco de dados
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'editais.db')

# Ano atual para sites que usam URL por ano
ANO_ATUAL = datetime.now().year

# ══════════════════════════════════════════════════════════
# REGISTRO DE TODOS OS SITES MONITORADOS
# ══════════════════════════════════════════════════════════
# Estratégia híbrida:
#   1. Tenta feed_url (RSS) primeiro
#   2. Se falhar → faz scraping na scrape_url
# ══════════════════════════════════════════════════════════

SITES = [

    # ┌─────────────────────────────────────┐
    # │         FACTO (Fundação)            │
    # └─────────────────────────────────────┘
    {
        'name': 'FACTO - Editais',
        'feed_url': f'https://facto.org.br/editais-{ANO_ATUAL}/feed',
        'scrape_url': f'https://facto.org.br/editais-{ANO_ATUAL}/',
        'parser': 'facto',
        'emoji': '🏛️',
    },
    {
        'name': 'FACTO - Pregões',
        'feed_url': f'https://facto.org.br/categoria-de-edital/edital-pregoes-{ANO_ATUAL}/feed',
        'scrape_url': f'https://facto.org.br/editais-{ANO_ATUAL}/',
        'parser': 'facto',
        'emoji': '🏛️',
    },

    # ┌─────────────────────────────────────┐
    # │       IFES - Cefor                  │
    # └─────────────────────────────────────┘
    {
        'name': 'IFES Cefor - Bolsistas',
        'feed_url': 'https://cefor.ifes.edu.br/index.php/processo-seletivo/bolsistas-e-estagiarios?format=feed&type=rss',
        'scrape_url': 'https://cefor.ifes.edu.br/index.php/processo-seletivo/bolsistas-e-estagiarios',
        'parser': 'ifes',
        'emoji': '🟢',
    },
    {
        'name': 'IFES Cefor - UAB',
        'feed_url': 'https://cefor.ifes.edu.br/index.php/prog-federais/universidade-aberta-do-brasil/editais-e-oportunidades-uab?format=feed&type=rss',
        'scrape_url': 'https://cefor.ifes.edu.br/index.php/prog-federais/universidade-aberta-do-brasil/editais-e-oportunidades-uab',
        'parser': 'ifes',
        'emoji': '🟢',
    },

    # ┌─────────────────────────────────────┐
    # │       SEAD UFES                     │
    # └─────────────────────────────────────┘
    {
        'name': 'SEAD UFES - Editais',
        'feed_url': 'https://sead.ufes.br/editais/feed/',
        'scrape_url': 'https://sead.ufes.br/editais/',
        'parser': 'generico',
        'emoji': '📘',
    },

    # ┌─────────────────────────────────────┐
    # │       IFES - Campus Cachoeiro       │
    # └─────────────────────────────────────┘
    {
        'name': 'IFES Cachoeiro - Bolsistas',
        'feed_url': 'https://cachoeiro.ifes.edu.br/processosseletivos/bolsistas-e-estagiarios?format=feed&type=rss',
        'scrape_url': 'https://cachoeiro.ifes.edu.br/processosseletivos/bolsistas-e-estagiarios',
        'parser': 'ifes',
        'emoji': '🟢',
    },

    # ┌─────────────────────────────────────┐
    # │       IFES - Sede (Geral)           │
    # └─────────────────────────────────────┘
    {
        'name': 'IFES - Servidores',
        'feed_url': 'https://www.ifes.edu.br/processosseletivos/servidores?format=feed&type=rss',
        'scrape_url': 'https://www.ifes.edu.br/processosseletivos/servidores',
        'parser': 'ifes',
        'emoji': '🟢',
    },
    {
        'name': 'IFES - Chamadas Internas',
        'feed_url': 'https://ifes.edu.br/chamadas-internas?format=feed&type=rss',
        'scrape_url': 'https://ifes.edu.br/chamadas-internas',
        'parser': 'ifes',
        'emoji': '🟢',
    },

    # ┌─────────────────────────────────────┐
    # │       IFES - Campus Vitória         │
    # └─────────────────────────────────────┘
    {
        'name': 'IFES Vitória - Bolsistas',
        'feed_url': 'https://vitoria.ifes.edu.br/processos-seletivos/bolsistas-e-estagiarios?format=feed&type=rss',
        'scrape_url': 'https://vitoria.ifes.edu.br/processos-seletivos/bolsistas-e-estagiarios',
        'parser': 'ifes',
        'emoji': '🟢',
    },
    {
        'name': 'IFES Vitória - Editais Internos',
        'feed_url': 'https://vitoria.ifes.edu.br/processos-seletivos/editais-internos?format=feed&type=rss',
        'scrape_url': 'https://vitoria.ifes.edu.br/processos-seletivos/editais-internos',
        'parser': 'ifes',
        'emoji': '🟢',
    },

    # ┌─────────────────────────────────────┐
    # │       IFES - Campus Serra           │
    # └─────────────────────────────────────┘
    {
        'name': 'IFES Serra - Bolsistas',
        'feed_url': 'https://serra.ifes.edu.br/processos-seletivos/bolsistas-e-estagiarios?format=feed&type=rss',
        'scrape_url': 'https://serra.ifes.edu.br/processos-seletivos/bolsistas-e-estagiarios',
        'parser': 'ifes',
        'emoji': '🟢',
    },
    {
        'name': 'IFES Serra - Editais Internos',
        'feed_url': 'https://serra.ifes.edu.br/processos-seletivos/editais-internos?format=feed&type=rss',
        'scrape_url': 'https://serra.ifes.edu.br/processos-seletivos/editais-internos',
        'parser': 'ifes',
        'emoji': '🟢',
    },

    # ┌─────────────────────────────────────┐
    # │       IFES - Campus Cariacica       │
    # └─────────────────────────────────────┘
    {
        'name': 'IFES Cariacica - Bolsistas',
        'feed_url': 'https://cariacica.ifes.edu.br/processos-seletivos/bolsistas-e-estagiarios?format=feed&type=rss',
        'scrape_url': 'https://cariacica.ifes.edu.br/processos-seletivos/bolsistas-e-estagiarios',
        'parser': 'ifes',
        'emoji': '🟢',
    },
    {
        'name': 'IFES Cariacica - Editais Internos',
        'feed_url': 'https://cariacica.ifes.edu.br/processos-seletivos/editais-internos?format=feed&type=rss',
        'scrape_url': 'https://cariacica.ifes.edu.br/processos-seletivos/editais-internos',
        'parser': 'ifes',
        'emoji': '🟢',
    },

    # ┌─────────────────────────────────────┐
    # │       IFES - Campus Vila Velha      │
    # └─────────────────────────────────────┘
    {
        'name': 'IFES Vila Velha - Servidores',
        'feed_url': 'https://vilavelha.ifes.edu.br/processosseletivos/editais-servidores.html?format=feed&type=rss',
        'scrape_url': 'https://vilavelha.ifes.edu.br/processosseletivos/editais-servidores.html',
        'parser': 'ifes',
        'emoji': '🟢',
    },
    {
        'name': 'IFES Vila Velha - Bolsistas',
        'feed_url': 'https://vilavelha.ifes.edu.br/processosseletivos/bolsistas-estagiarios-e-intercambistas.html?format=feed&type=rss',
        'scrape_url': 'https://vilavelha.ifes.edu.br/processosseletivos/bolsistas-estagiarios-e-intercambistas.html',
        'parser': 'ifes',
        'emoji': '🟢',
    },
    {
        'name': 'IFES Vila Velha - Editais Internos',
        'feed_url': 'https://vilavelha.ifes.edu.br/processosseletivos/editais-internos.html?format=feed&type=rss',
        'scrape_url': 'https://vilavelha.ifes.edu.br/processosseletivos/editais-internos.html',
        'parser': 'ifes',
        'emoji': '🟢',
    },

    # ┌─────────────────────────────────────┐
    # │   IFES - Pró-Reitorias e Agências   │
    # └─────────────────────────────────────┘
    {
        'name': 'IFES Proex - Editais',
        'feed_url': 'https://proex.ifes.edu.br/editais?format=feed&type=rss',
        'scrape_url': 'https://proex.ifes.edu.br/editais?showall=1',
        'parser': 'proex_ifes',
        'emoji': '🟢',
    },
    {
        'name': 'IFES Agifes - Editais',
        'feed_url': 'https://agifes.ifes.edu.br/editais?format=feed&type=rss',
        'scrape_url': 'https://agifes.ifes.edu.br/editais',
        'parser': 'ifes',
        'emoji': '🟢',
    },
    {
        'name': 'IFES Polo - Editais',
        'feed_url': 'https://polo.ifes.edu.br/editais-polo?format=feed&type=rss',
        'scrape_url': 'https://polo.ifes.edu.br/editais-polo',
        'parser': 'ifes',
        'emoji': '🟢',
    },
    {
        'name': 'IFES PRPPG - Editais',
        'feed_url': None,
        'scrape_url': 'https://prppg.ifes.edu.br/editais',
        'parser': 'ifes',
        'emoji': '🟢',
    },

    # ┌─────────────────────────────────────┐
    # │   IFES - SIGPesq (Editais Pesquisa) │
    # └─────────────────────────────────────┘
    {
        'name': 'IFES SIGPesq - Abertos',
        'feed_url': None,
        'scrape_url': 'https://sigpesq.ifes.edu.br/publico/Editais.aspx?s=Aberto',
        'parser': 'sigpesq_ifes',
        'emoji': '🔎',
    },
    {
        'name': 'IFES SIGPesq - Em Andamento',
        'feed_url': None,
        'scrape_url': 'https://sigpesq.ifes.edu.br/publico/Editais.aspx?s=Em+Andamento',
        'parser': 'sigpesq_ifes',
        'emoji': '🔎',
    },

    # ┌─────────────────────────────────────┐
    # │       FetchRSS (feeds externos)     │
    # └─────────────────────────────────────┘
    {
        'name': 'FetchRSS - Feed 1',
        'feed_url': 'https://fetchrss.com/feed/aLIfefetLhGyaLIfY0tsJkZy.rss',
        'scrape_url': None,
        'parser': None,
        'emoji': '📡',
    },
    {
        'name': 'FetchRSS - Feed 2',
        'feed_url': 'https://fetchrss.com/feed/aLIfefetLhGyaLW_wYnKIIlC.rss',
        'scrape_url': None,
        'parser': None,
        'emoji': '📡',
    },

    # ╔═════════════════════════════════════╗
    # ║  UNIVERSIDADES FEDERAIS             ║
    # ╚═════════════════════════════════════╝

    # ┌─────────────────────────────────────┐
    # │       UFMG                          │
    # └─────────────────────────────────────┘
    {
        'name': 'UFMG - PRPq Editais',
        'feed_url': None,
        'scrape_url': 'https://www.ufmg.br/prpq/editais/?o=aberto',
        'parser': 'ufmg',
        'emoji': '🔴',
    },
    {
        'name': 'UFMG - PROEX Bolsas',
        'feed_url': None,
        'scrape_url': 'https://www.ufmg.br/proex/oportunidades-de-bolsas/',
        'parser': 'generico',
        'emoji': '🔴',
    },

    # ┌─────────────────────────────────────┐
    # │       UFES                          │
    # └─────────────────────────────────────┘
    {
        'name': 'UFES - PRPPG Editais',
        'feed_url': None,
        'scrape_url': 'https://prppg.ufes.br/editais',
        'parser': 'generico',
        'emoji': '🟤',
    },

    # ┌─────────────────────────────────────┐
    # │       USP                           │
    # └─────────────────────────────────────┘
    {
        'name': 'USP - PRP Editais',
        'feed_url': None,
        'scrape_url': 'https://prp.usp.br/editais/',
        'parser': 'generico',
        'emoji': '⚫',
    },

    # ┌─────────────────────────────────────┐
    # │       UFRJ                          │
    # └─────────────────────────────────────┘
    {
        'name': 'UFRJ - Pós-Graduação',
        'feed_url': None,
        'scrape_url': 'https://posgraduacao.ufrj.br/editais',
        'parser': 'generico',
        'emoji': '🔵',
    },

    # ┌─────────────────────────────────────┐
    # │       UFBA                          │
    # └─────────────────────────────────────┘
    {
        'name': 'UFBA - PROPCI',
        'feed_url': None,
        'scrape_url': 'https://propci.ufba.br/editais',
        'parser': 'generico',
        'emoji': '🔵',
    },

    # ┌─────────────────────────────────────┐
    # │       UFPE                          │
    # └─────────────────────────────────────┘
    {
        'name': 'UFPE - PROPESQI',
        'feed_url': None,
        'scrape_url': 'https://www.ufpe.br/propesqi/editais',
        'parser': 'generico',
        'emoji': '🟣',
    },

    # ┌─────────────────────────────────────┐
    # │       UFSC                          │
    # └─────────────────────────────────────┘
    {
        'name': 'UFSC - PROPESQ',
        'feed_url': None,
        'scrape_url': 'https://propesq.ufsc.br/editais/',
        'parser': 'generico',
        'emoji': '🔺',
    },

    # ┌─────────────────────────────────────┐
    # │       UNICAMP                       │
    # └─────────────────────────────────────┘
    {
        'name': 'UNICAMP - PRP',
        'feed_url': None,
        'scrape_url': 'https://www.prp.unicamp.br/pt-br/editais',
        'parser': 'generico',
        'emoji': '🦄',
    },

    # ┌─────────────────────────────────────┐
    # │       UnB                           │
    # └─────────────────────────────────────┘
    {
        'name': 'UnB - DPG',
        'feed_url': None,
        'scrape_url': 'https://dpg.unb.br/editais',
        'parser': 'generico',
        'emoji': '🏫',
    },

    # ┌─────────────────────────────────────┐
    # │       UFRGS                         │
    # └─────────────────────────────────────┘
    {
        'name': 'UFRGS - PROPESQ',
        'feed_url': None,
        'scrape_url': 'https://www.ufrgs.br/propesq/editais/',
        'parser': 'generico',
        'emoji': '📗',
    },

    # ╔═════════════════════════════════════╗
    # ║  INSTITUTOS FEDERAIS               ║
    # ╚═════════════════════════════════════╝

    # ┌─────────────────────────────────────┐
    # │       IFMG                          │
    # └─────────────────────────────────────┘
    {
        'name': 'IFMG - Pesquisa',
        'feed_url': None,
        'scrape_url': 'https://www.ifmg.edu.br/portal/pesquisa',
        'parser': 'generico',
        'emoji': '🟡',
    },

    # ┌─────────────────────────────────────┐
    # │       IFSC                          │
    # └─────────────────────────────────────┘
    {
        'name': 'IFSC - Editais',
        'feed_url': None,
        'scrape_url': 'https://www.ifsc.edu.br/editais',
        'parser': 'generico',
        'emoji': '🟠',
    },

    # ╔═════════════════════════════════════╗
    # ║  AGÊNCIAS DE FOMENTO               ║
    # ╚═════════════════════════════════════╝

    # ┌─────────────────────────────────────┐
    # │       CNPq                          │
    # └─────────────────────────────────────┘
    {
        'name': 'CNPq - Chamadas Públicas',
        'feed_url': None,
        'scrape_url': 'https://www.cnpq.br/web/guest/chamadas-publicas',
        'parser': 'cnpq',
        'emoji': '🔬',
    },

    # ┌─────────────────────────────────────┐
    # │       CAPES                         │
    # └─────────────────────────────────────┘
    {
        'name': 'CAPES - Bolsas',
        'feed_url': None,
        'scrape_url': 'https://www.gov.br/capes/pt-br/acesso-a-informacao/acoes-e-programas/bolsas',
        'parser': 'generico_govbr',
        'emoji': '📘',
    },

    # ┌─────────────────────────────────────┐
    # │       FAPES (ES)                    │
    # └─────────────────────────────────────┘
    {
        'name': 'FAPES - Editais',
        'feed_url': None,
        'scrape_url': 'https://fapes.es.gov.br/editais',
        'parser': 'generico_govbr',
        'emoji': '🌴',
    },

    # ┌─────────────────────────────────────┐
    # │       FAPESP (SP)                   │
    # └─────────────────────────────────────┘
    {
        'name': 'FAPESP - Chamadas',
        'feed_url': None,
        'scrape_url': 'https://fapesp.br/chamadas',
        'parser': 'generico',
        'emoji': '🏛️',
    },

    # ┌─────────────────────────────────────┐
    # │       FAPEMIG (MG)                  │
    # └─────────────────────────────────────┘
    {
        'name': 'FAPEMIG - Editais',
        'feed_url': None,
        'scrape_url': 'https://fapemig.br/pt/editais/',
        'parser': 'generico',
        'emoji': '⛰️',
    },

    # ╔═════════════════════════════════════╗
    # ║  FUNDAÇÕES DE APOIO                 ║
    # ╚═════════════════════════════════════╝

    # ┌─────────────────────────────────────┐
    # │       FEESC (UFSC)                  │
    # └─────────────────────────────────────┘
    {
        'name': 'FEESC - Conexões para Inovar',
        'feed_url': 'https://www.conexoesparainovar.org.br/blog-feed.xml',
        'scrape_url': 'https://www.conexoesparainovar.org.br/editais-conexoes-para-inovar',
        'parser': None,
        'emoji': '💡',
    },

    # ┌─────────────────────────────────────┐
    # │       FAPEU (UFSC)                  │
    # └─────────────────────────────────────┘
    {
        'name': 'FAPEU - Editais',
        'feed_url': None,
        'scrape_url': 'https://fapeu.org.br/editais/',
        'parser': 'generico',
        'emoji': '🏢',
    },

    # ┌─────────────────────────────────────┐
    # │       PRÓ-IFF (IFF)                 │
    # └─────────────────────────────────────┘
    {
        'name': 'PRÓ-IFF - Editais Abertos',
        'feed_url': None,
        'scrape_url': 'https://pro-iff.org.br/editais-abertos/',
        'parser': 'proiff',
        'emoji': '🏢',
    },

    # ┌─────────────────────────────────────┐
    # │       FINATEC (UnB)                 │
    # └─────────────────────────────────────┘
    {
        'name': 'FINATEC - Licitações Abertas',
        'feed_url': None,
        'scrape_url': 'https://www.finatec.org.br/transparencia/licitacoes/informacoes',
        'parser': 'finatec',
        'emoji': '🏢',
    },

    # ┌─────────────────────────────────────┐
    # │       FUNCAMP (Unicamp)             │
    # └─────────────────────────────────────┘
    {
        'name': 'FUNCAMP - Processos Seletivos',
        'feed_url': None,
        'scrape_url': 'https://www.funcamp.unicamp.br/',
        'parser': 'generico',
        'emoji': '🏢',
    },

    # ┌─────────────────────────────────────┐
    # │       FAPUR (UFRRJ)                 │
    # └─────────────────────────────────────┘
    {
        'name': 'FAPUR - Processos Abertos',
        'feed_url': None,
        'scrape_url': 'https://www.fapur.org.br/',
        'parser': 'generico',
        'emoji': '🏢',
    },

    # ┌─────────────────────────────────────┐
    # │       FAPEX (UFBA)                  │
    # └─────────────────────────────────────┘
    {
        'name': 'FAPEX - Editais',
        'feed_url': None,
        'scrape_url': 'https://www.fapex.org.br/Fapex/Site/Principal/Edital/index',
        'parser': 'generico',
        'emoji': '🏢',
    },

    # ┌─────────────────────────────────────┐
    # │       FAURGS (UFRGS)                │
    # └─────────────────────────────────────┘
    {
        'name': 'FAURGS - Editais',
        'feed_url': None,
        'scrape_url': 'https://portalfaurgs.com.br/',
        'parser': 'generico',
        'emoji': '🏢',
    },

    # ┌─────────────────────────────────────┐
    # │       FADEX (UFPI)                  │
    # └─────────────────────────────────────┘
    {
        'name': 'FADEX - Editais',
        'feed_url': None,
        'scrape_url': 'https://www.fadex.org.br/',
        'parser': 'generico',
        'emoji': '🏢',
    },

    # ┌─────────────────────────────────────┐
    # │       FUNDEP (UFMG)                 │
    # └─────────────────────────────────────┘
    {
        'name': 'FUNDEP - Editais',
        'feed_url': None,
        'scrape_url': 'https://www.fundep.ufmg.br/editais/',
        'parser': 'generico',
        'emoji': '🏢',
    },

    # ┌─────────────────────────────────────┐
    # │       FUSP (USP)                    │
    # └─────────────────────────────────────┘
    {
        'name': 'FUSP - Editais',
        'feed_url': None,
        'scrape_url': 'https://www.fusp.org.br/editais',
        'parser': 'generico',
        'emoji': '🏢',
    },

    # ┌─────────────────────────────────────┐
    # │       FADESP (UFPA)                 │
    # └─────────────────────────────────────┘
    {
        'name': 'FADESP - Editais',
        'feed_url': None,
        'scrape_url': 'https://www.fadesp.org.br/editais/',
        'parser': 'generico',
        'emoji': '🏢',
    },
]
