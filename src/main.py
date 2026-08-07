import sys
import os
from config import SITES, BOT_TOKEN, CHAT_ID, DRYRUN, FIRST_RUN_SILENT, DB_PATH
from scraper import ScraperEngine
from storage import Storage
from notifier import Notifier

def main():
    print("🚀 Iniciando Feed Oportunidades - Scraper Híbrido...")

    # Configuração de variáveis obrigatórias apenas se não estiver em DRYRUN
    if not DRYRUN and (not BOT_TOKEN or not CHAT_ID):
        print("❌ ERRO: Variáveis BOT_TOKEN ou CHAT_ID (DESTINATION) não foram configuradas.")
        print("Configure-as no arquivo .txt, nas variáveis de ambiente ou no GitHub Secrets.")
        sys.exit(1)

    # Instanciar componentes
    storage = Storage(DB_PATH)
    notifier = Notifier(BOT_TOKEN, CHAT_ID, dryrun=DRYRUN)
    engine = ScraperEngine(SITES)

    # 1. Executar scraper em todas as fontes
    todos_editais = engine.scrape_todos()

    if not todos_editais:
        print("⚠️ Nenhum edital encontrado em nenhuma das fontes.")
        sys.exit(0)

    # 2. Filtrar editais já vistos
    total_registrados = storage.total_registrados()
    primeira_execucao = (total_registrados == 0)

    novos_editais = storage.filtrar_novos(todos_editais)

    print(f"📂 Editais no histórico: {total_registrados}")
    print(f"✨ Novos editais detectados: {len(novos_editais)}")

    if not novos_editais:
        print("✅ Todos os editais encontrados já foram notificados anteriormente.")
        sys.exit(0)

    # 3. Lidar com a primeira execução (Silenciosa por padrão para não floodar)
    if primeira_execucao and FIRST_RUN_SILENT:
        print("🤫 Primeira execução detectada. Registrando todos os editais silenciosamente...")
        storage.registrar_lote(novos_editais)
        
        status_msg = (
            f"🤖 *Bot do Feed de Oportunidades Iniciado!*\n\n"
            f"✅ Monitoramento ativo em {len(SITES)} fontes.\n"
            f"📂 {len(novos_editais)} editais existentes foram registrados silenciosamente no histórico.\n"
            f"Abaixo segue um resumo com o edital mais recente de cada site:"
        )
        notifier.enviar_status(status_msg)
        
        # Enviar Resumo por Estado
        from collections import defaultdict
        
        estados = {
            'Espírito Santo (ES)': ['IFES', 'UFES', 'FAPES', 'SEAD UFES'],
            'Minas Gerais (MG)': ['UFMG', 'IFMG', 'FAPEMIG', 'FUNDEP'],
            'São Paulo (SP)': ['USP', 'FAPESP', 'FUSP'],
            'Santa Catarina (SC)': ['UFSC', 'IFSC', 'FAPEU'],
            'Rio de Janeiro (RJ)': ['UFRJ'],
            'Bahia (BA)': ['UFBA'],
            'Pernambuco (PE)': ['UFPE'],
            'Rio Grande do Sul (RS)': ['UFRGS'],
            'Distrito Federal (DF)': ['UnB'],
            'Pará (PA)': ['FADESP'],
            'Nacional / Fundações': ['FACTO', 'CAPES', 'CNPq', 'FetchRSS']
        }
        
        # Pega só o primeiro edital (mais recente) de cada site
        primeiros_por_site = {}
        for edital in novos_editais:
            if edital['site'] not in primeiros_por_site:
                primeiros_por_site[edital['site']] = edital
                
        resumo_por_estado = defaultdict(list)
        for site, edital in primeiros_por_site.items():
            estado_encontrado = 'Outros'
            for estado, keywords in estados.items():
                if any(kw in site for kw in keywords):
                    estado_encontrado = estado
                    break
            resumo_por_estado[estado_encontrado].append(edital)
            
        import time
        for estado, lista in sorted(resumo_por_estado.items()):
            msg = f"📍 *{estado}*\n\n"
            for ed in lista:
                titulo = ed['titulo']
                if len(titulo) > 90:
                    titulo = titulo[:87] + "..."
                titulo_limpo = titulo.replace('[', '(').replace(']', ')')
                msg += f"{ed.get('emoji', '📋')} *{ed['site']}*\n[{titulo_limpo}]({ed['url']})\n\n"
            
            notifier.enviar_status(msg)
            time.sleep(1) # evita rate limit do Telegram

        print("✅ Registro concluído com sucesso.")
        sys.exit(0)

    # 4. Agrupar editais por site para o resumo
    novos_por_site = {}
    for edital in novos_editais:
        site = edital['site']
        if site not in novos_por_site:
            novos_por_site[site] = []
        novos_por_site[site].append(edital)

    # 5. Enviar notificações individuais e registrar no banco
    print("📤 Enviando notificações...")
    for edital in novos_editais:
        if notifier.enviar_edital(edital):
            storage.registrar(edital['titulo'], edital['url'], edital['site'])

    # 6. Enviar mensagem de resumo se houver mais de um edital
    if len(novos_editais) > 1:
        notifier.enviar_resumo(novos_por_site)

    print("🎉 Processo concluído com sucesso!")

if __name__ == '__main__':
    # Modifica o diretório atual para garantir que caminhos relativos funcionem 
    # dependendo de onde o script foi chamado
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    main()
