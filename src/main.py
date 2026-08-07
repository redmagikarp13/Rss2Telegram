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
            f"A partir de agora, enviarei notificação apenas quando novos editais surgirem!"
        )
        notifier.enviar_status(status_msg)
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
