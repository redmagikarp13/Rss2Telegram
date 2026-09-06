"""
Configuração dos sites monitorados e variáveis de ambiente.
Baseado nas URLs do projeto original Rss2Telegram + universidades e fundações adicionais.
"""
import os
from datetime import datetime


def get_variable(variable, default=None):
    """Lê variável de ambiente ou de arquivo .txt (compatível com projeto anterior).

    String vazia/so-espaços conta como NAO configurada. Sem isso, uma GitHub
    Variable inexistente chegava como '' e o valor caia silenciosamente no
    default 0, desligando os filtros de volume (causa do flood de editais de 2020).
    """
    env_val = os.environ.get(variable)
    if env_val is not None and env_val.strip():
        return env_val.strip()
    try:
        with open(f'{variable}.txt', 'r', encoding='utf-8') as f:
            arquivo = f.read().strip()
        if arquivo:
            return arquivo
    except FileNotFoundError:
        pass
    return default


def get_int_variable(variable, default, descricao):
    """get_variable + validacao de inteiro, avisando alto quando o recurso desliga."""
    bruto = get_variable(variable, str(default))
    try:
        valor = int(bruto)
    except ValueError:
        print(f"⚠️  {variable}={bruto!r} não é um inteiro válido. Usando {default} ({descricao}).")
        return default
    if valor <= 0:
        print(f"⚠️  {variable}={valor}: {descricao} está DESATIVADO — esperado > 0.")
    return valor


# Telegram
BOT_TOKEN = get_variable('BOT_TOKEN')
CHAT_ID = get_variable('DESTINATION', get_variable('CHAT_ID'))
DRYRUN = get_variable('DRYRUN', 'false').lower() in ('true', '1', 'yes')
FIRST_RUN_SILENT = get_variable('FIRST_RUN_SILENT', 'true').lower() in ('true', '1', 'yes')

# Filtro de data — janela deslizante (em dias). 0 = desativado
# No GitHub Actions o valor vem de Settings → Secrets and variables → Actions,
# como Secret OU Variable, injetado em .github/workflows/scraper.yml (que usa
# fallback '90' se nenhuma das duas existir). Defaults locais em 0 para que uma
# execução fora do Actions não esconda itens por um critério não configurado.
EDITAL_MAX_DIAS = get_int_variable('EDITAL_MAX_DIAS', 0, 'filtro de recência')

# Limite de itens por fonte por execução. 0 = sem limite
MAX_ITENS_POR_FONTE = get_int_variable('MAX_ITENS_POR_FONTE', 0, 'teto por fonte')

# Máximo de NOTIFICAÇÕES por estado por execução. 0 = desativado.
# Proteção final contra flood: o teto por fonte é individual, então 51 fontes × 10
# ainda podem somar centenas de mensagens numa mesma rodada. Este teto é aplicado
# depois do dedup, contando mensagens reais.
MAX_ITENS_POR_ESTADO = get_int_variable('MAX_ITENS_POR_ESTADO', 0, 'teto por estado')

# ──────────────────────────────────────────────────────────
# AGRUPAMENTO DAS FONTES POR ESTADO
# Único dono desse mapeamento: é usado no resumo da primeira execução e no teto
# por estado. Fonte não listada cai em 'Outros' e divide o bucket com as demais
# não mapeadas, entao o main avisa no log quando isso acontece.
# ──────────────────────────────────────────────────────────
SITE_ESTADOS = {
    'Espírito Santo (ES)': ['SEAD UFES', 'IFES', 'UFES', 'FAPES', 'UnAC'],
    'Minas Gerais (MG)': ['IFSULDEMINAS', 'UFVJM', 'IFNMG', 'UFMG', 'IFMG',
                          'FAPEMIG', 'FUNDEP'],
    'São Paulo (SP)': ['FAPESP', 'FUNCAMP', 'UNICAMP', 'FUSP', 'USP'],
    'Santa Catarina (SC)': ['UFSC', 'IFSC', 'FAPEU', 'FEESC'],
    'Rio de Janeiro (RJ)': ['PRÓ-IFF', 'UNIRIO', 'UFRJ', 'FAPUR'],
    'Bahia (BA)': ['FAPEX', 'UFBA'],
    'Pernambuco (PE)': ['UFPE'],
    'Rio Grande do Sul (RS)': ['UFRGS', 'FAURGS'],
    'Distrito Federal (DF)': ['FINATEC', 'UnB'],
    'Piauí (PI)': ['FADEX'],
    'Pará (PA)': ['FADESP'],
    'Nacional / Fundações': ['FACTO', 'CNPq', 'CAPES'],
}

ESTADO_PADRAO = 'Outros'

# Casar a keyword MAIS LONGA é obrigatório: 'FAPESP' contém 'FAPES' e 'FUSP'
# contém 'USP'. Sem isso, a FAPESP-SP caía no bucket do ES pelo keyword 'FAPES'.
_PAR_ESTADO = sorted(
    ((kw, estado) for estado, kws in SITE_ESTADOS.items() for kw in kws),
    key=lambda par: len(par[0]),
    reverse=True,
)


def classificar_estado(nome_site):
    """Estado de uma fonte pelo nome; ESTADO_PADRAO quando nao mapeada."""
    for keyword, estado in _PAR_ESTADO:
        if keyword in (nome_site or ''):
            return estado
    return ESTADO_PADRAO


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
    # IFES Polo e IFES PRPPG removidos: o Polo nao publica mais la (migrou
    # para o integra.ifes.edu.br) e o '/editais' da PRPPG esta 404 - os
    # editais da PRPPG vao para o SIGPesq (ifes.edu.br/publico/Editais), ja
    # monitorado pelas fontes 'IFES SIGPesq' abaixo.

    # Portal Integra (SPA): o Polo de Inovacao passou a divulgar suas
    # vinculacoes/editais como "eventos" aqui. scrape_url e a API JSON; o
    # parser integra_eventos faz json.loads (sem render). Obs: o endpoint
    # publica ignora page/size/sort e devolve sempre ~10 eventos ativos; o
    # notifier deduplica por URL, entao so eventos NOVOS geram alerta.
    {
        'name': 'IFES Integra - Eventos (Polo)',
        'feed_url': None,
        'scrape_url': 'https://integra.ifes.edu.br/api/inovacao/eventos/data',
        'parser': 'integra_eventos',
        'emoji': '📅',
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
    {
        'name': 'UFMG - EaD (DEDD)',
        'feed_url': None,
        'scrape_url': 'https://www.ufmg.br/dedd/selecoes/',
        'parser': 'ead_editais',
        'emoji': '🔴',
    },

    # ┌─────────────────────────────────────┐
    # │       UNIRIO - CEAD (EaD)           │
    # └─────────────────────────────────────┘
    {
        'name': 'UNIRIO - EaD (CEAD/UAB)',
        'feed_url': None,
        'scrape_url': 'https://www.unirio.br/cead/editais',
        'parser': 'ead_editais',
        'emoji': '🟣',
    },

    # ┌─────────────────────────────────────┐
    # │       UFVJM - DEAD (EaD)            │
    # └─────────────────────────────────────┘
    {
        'name': 'UFVJM - EaD (DEAD/UAB)',
        'feed_url': None,
        'scrape_url': 'https://www.ead.ufvjm.edu.br/',
        'parser': 'generico',
        'emoji': '🟩',
    },

    # ┌─────────────────────────────────────┐
    # │  UnAC - Universidade Aberta do ES   │
    # └─────────────────────────────────────┘
    {
        'name': 'UnAC - Editais Abertos (ES)',
        'feed_url': None,
        'scrape_url': 'https://universidades.es.gov.br/editaisabertos',
        'parser': 'unac_es',
        'emoji': '🎓',
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
        'scrape_url': 'https://prp.unicamp.br/faepex/editais/',
        'parser': 'unicamp_prp',
        'render': True,
        'emoji': '🦄',
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
    # │       IFMG - Centro Ref. EaD        │
    # └─────────────────────────────────────┘
    {
        'name': 'IFMG - EaD (CRead/UAB)',
        'feed_url': None,
        'scrape_url': 'https://www.ifmg.edu.br/portal/educacao-a-distancia/editais-ead',
        'parser': 'ead_editais',
        # render=False: o portal oscila no browser headless (devolvia 0),
        # mas entrega os editais via requests simples.
        'render': False,
        'emoji': '🟡',
    },

    # ┌─────────────────────────────────────┐
    # │       IFNMG - CEAD / UAB            │
    # └─────────────────────────────────────┘
    {
        # Atencao: URL por ano. Atualizar o /2026 -> /AAAA a cada virada.
        'name': 'IFNMG - EaD (CEAD/UAB)',
        'feed_url': None,
        'scrape_url': 'https://www.ifnmg.edu.br/editais-uab/2026',
        'parser': 'ead_editais',
        'emoji': '🟢',
    },

    # ┌─────────────────────────────────────┐
    # │       IFSULDEMINAS - EaD            │
    # └─────────────────────────────────────┘
    {
        'name': 'IFSULDEMINAS - EaD',
        'feed_url': None,
        'scrape_url': 'http://portal.ifsuldeminas.edu.br/index.php/pro-reitoria-ensino/ead/editais-ead-geral',
        'parser': 'ead_editais',
        'emoji': '🟢',
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
        'scrape_url': 'https://www.gov.br/cnpq/pt-br/chamadas/abertas-para-submissao',
        'parser': 'cnpq_govbr',
        'render': True,
        'emoji': '🔬',
    },

    # ┌─────────────────────────────────────┐
    # │       CAPES                         │
    # └─────────────────────────────────────┘
    {
        'name': 'CAPES - Editais',
        'feed_url': None,
        # '/acoes-e-programas/bolsas' era so menu; a listagem de editais
        # abertos fica em 'assuntos/editais-e-resultados-capes'.
        'scrape_url': 'https://www.gov.br/capes/pt-br/assuntos/editais-e-resultados-capes',
        'parser': 'ead_editais',
        'render': True,
        'emoji': '📘',
    },

    # ┌─────────────────────────────────────┐
    # │       FAPES (ES)                    │
    # └─────────────────────────────────────┘
    {
        # '/editais' era so o menu; os editais reais ficam nestas subpaginas.
        'name': 'FAPES - Chamadas Publicas (ES)',
        'feed_url': None,
        'scrape_url': 'https://fapes.es.gov.br/chamamento-publico',
        'parser': 'fapes_es',
        'emoji': '🌴',
    },
    {
        'name': 'FAPES - Chamadas Internacionais (ES)',
        'feed_url': None,
        'scrape_url': 'https://fapes.es.gov.br/chamadas-internacionais',
        'parser': 'fapes_es',
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

    # ╔═════════════════════════════════════╗
    # ║  FUNDAÇÕES DE APOIO                 ║
    # ╚═════════════════════════════════════╝

    # FEESC removida: a pagina so tem editais encerrados/suspensos atras de
    # iframe (nenhum link acionavel de edital vigente).

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
        'parser': 'fapex',
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
    # │       FUSP (USP)                    │
    # └─────────────────────────────────────┘
    {
        'name': 'FUSP - Editais',
        'feed_url': None,
        'scrape_url': 'https://www.fusp.org.br/editais',
        'parser': 'generico',
        'emoji': '🏢',
    },

    # FADESP removida: o dominio fadesp.org.br nao existe mais e o novo
    # portal so repassa para um portal ASP de licitacoes sem lista limpa.
]
