import sys
import os
from datetime import datetime
from config import (
    SITES, BOT_TOKEN, CHAT_ID, DRYRUN, FIRST_RUN_SILENT, DB_PATH,
    EDITAL_MAX_DIAS, MAX_ITENS_POR_FONTE, MAX_ITENS_POR_ESTADO,
    MARCADOR_PRIMEIRA_EXEC_PATH, classificar_estado,
)
from scraper import ScraperEngine, data_efetiva
from storage import Storage
from notifier import Notifier


def _aplicar_teto_por_estado(editais, teto):
    """Mantém os `teto` editais mais recentes de cada estado -> (mantidos, suprimidos).

    Complementa o teto por fonte: ele é individual, então não limita o total
    entregue ao chat. Este corte só faz sentido DEPOIS do dedup — aplicado antes,
    itens já vistos consumariam a cota e a rodada poderia não notificar nada.
    """
    baldes = {}
    for edital in editais:
        baldes.setdefault(classificar_estado(edital['site']), []).append(edital)

    mantidos, suprimidos = [], 0
    for estado, itens in sorted(baldes.items()):
        # Mais recentes primeiro. Sem sinal de data vai para o fim e a ordenação
        # estável conserva a ordem da própria listagem da fonte.
        itens.sort(key=lambda e: data_efetiva(e) or datetime.min, reverse=True)
        if len(itens) > teto:
            excedente = len(itens) - teto
            suprimidos += excedente
            print(f"   🚫 {estado}: limitado de {len(itens)} para {teto} "
                  f"({excedente} suprimido(s))")
        mantidos.extend(itens[:teto])
    return mantidos, suprimidos


def main():
    print("🚀 Iniciando Feed Oportunidades - Scraper Híbrido...")
    print(f"   📅 Janela de recência: {EDITAL_MAX_DIAS} dias | "
          f"🔢 Teto por fonte: {MAX_ITENS_POR_FONTE} | "
          f"🗺️ Teto por estado: {MAX_ITENS_POR_ESTADO} | 🌐 Fontes: {len(SITES)}")

    # Configuração de variáveis obrigatórias apenas se não estiver em DRYRUN
    if not DRYRUN and (not BOT_TOKEN or not CHAT_ID):
        print("❌ ERRO: Variáveis BOT_TOKEN ou CHAT_ID (DESTINATION) não foram configuradas.")
        print("Configure-as no arquivo .txt, nas variáveis de ambiente ou no GitHub Secrets.")
        sys.exit(1)

    # Instanciar componentes
    storage = Storage(DB_PATH)
    notifier = Notifier(BOT_TOKEN, CHAT_ID, dryrun=DRYRUN)
    engine = ScraperEngine(
        SITES,
        max_dias=EDITAL_MAX_DIAS,
        max_itens_por_fonte=MAX_ITENS_POR_FONTE,
    )

    # ── Proteção contra banco vazio ──────────────────────────
    # Se o marcador existe (primeira execução já ocorreu) mas o DB está vazio,
    # isso indica perda do banco de dados. Não re-enviar tudo como "novo".
    marcador_existe = os.path.exists(MARCADOR_PRIMEIRA_EXEC_PATH)
    total_registrados = storage.total_registrados()
    primeira_execucao = (total_registrados == 0)

    if primeira_execucao and marcador_existe and not DRYRUN:
        # Banco perdido (artifact não restaurou, ou expirou os 90 dias de retenção).
        # Com FIRST_RUN_SILENT, o caminho abaixo regrava tudo sem notificar — o bot
        # sobrevive e o resumo enviado ao chat avisa da reinicialização. Encerrar com
        # erro aqui transformaria um evento auto-curável em bot morto até alguém
        # aparecer; só abortamos quando a regravação ficaria explícita demais, ou
        # seja, FIRST_RUN_SILENT desligado = re-enviaria tudo como novo.
        print("⚠️  Banco de dados vazio embora a primeira execução já tenha concluído.")
        print("   O histórico foi perdido (artifact não restaurou?).")
        if not FIRST_RUN_SILENT:
            print("   FIRST_RUN_SILENT está desligado, então a rodada reenviaria tudo.")
            print("   Encerrando para evitar re-envio em massa de editais antigos.")
            print("   Para forçar uma nova primeira execução, remova o arquivo:")
            print(f"   {MARCADOR_PRIMEIRA_EXEC_PATH}")
            sys.exit(1)
        aviso = ("histórico de editais perdido — regravando tudo silenciosamente; "
                 "nenhum edital antigo será reenviado nesta rodada")
        print(f"   ➡️  {aviso}")
        if os.environ.get('GITHUB_ACTIONS'):
            print(f"::warning::{aviso}")

    # 1. Executar scraper em todas as fontes
    todos_editais = engine.scrape_todos()

    if not todos_editais:
        print("⚠️ Nenhum edital encontrado em nenhuma das fontes.")
        sys.exit(0)

    # 2. Filtrar editais já vistos (inclui detecção de atualizações)
    novos_editais = storage.filtrar_novos(todos_editais)

    # Separar novos de atualizações
    novos = [e for e in novos_editais if e.get('status') == 'novo']
    atualizacoes = [e for e in novos_editais if e.get('status') == 'atualizacao']

    print(f"📂 Editais no histórico: {total_registrados}")
    print(f"✨ Novos editais detectados: {len(novos)}")
    print(f"🔄 Atualizações detectadas: {len(atualizacoes)}")

    if not novos_editais:
        print("✅ Todos os editais encontrados já foram notificados anteriormente.")
        sys.exit(0)

    # 3. Lidar com a primeira execução (Silenciosa por padrão para não floodar)
    if primeira_execucao and FIRST_RUN_SILENT:
        print("🤫 Primeira execução detectada. Registrando todos os editais silenciosamente...")
        storage.registrar_lote(novos_editais)

        # Criar marcador de primeira execução concluída
        try:
            with open(MARCADOR_PRIMEIRA_EXEC_PATH, 'w') as f:
                f.write('true')
            print("📝 Marcador de primeira execução criado.")
        except Exception as e:
            print(f"⚠️ Não foi possível criar marcador: {e}")
        
        status_msg = (
            f"🤖 *Bot do Feed de Oportunidades Iniciado!*\n\n"
            f"✅ Monitoramento ativo em {len(SITES)} fontes.\n"
            f"📂 {len(novos_editais)} editais existentes foram registrados silenciosamente no histórico.\n"
            f"Abaixo segue um resumo com o edital mais recente de cada site:"
        )
        notifier.enviar_status(status_msg)
        
        # Enviar Resumo por Estado
        from collections import defaultdict
        
        # Mapeamento de estados compartilhado com o teto: config.SITE_ESTADOS
        
        # Pega só o primeiro edital (mais recente) de cada site
        primeiros_por_site = {}
        for edital in novos_editais:
            if edital['site'] not in primeiros_por_site:
                primeiros_por_site[edital['site']] = edital
                
        resumo_por_estado = defaultdict(list)
        for site, edital in primeiros_por_site.items():
            estado_encontrado = classificar_estado(site)
            if estado_encontrado == 'Outros':
                print(f"   ⚠️ fonte sem mapeamento de estado em config.SITE_ESTADOS: {site}")
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

    # 4. Teto por estado — corte final de volume, depois do dedup
    suprimidos = 0
    if MAX_ITENS_POR_ESTADO > 0:
        antes = len(novos_editais)
        novos_editais, suprimidos = _aplicar_teto_por_estado(
            novos_editais, MAX_ITENS_POR_ESTADO
        )
        print(f"🗺️ Teto por estado ({MAX_ITENS_POR_ESTADO}): {antes} → "
              f"{len(novos_editais)} notificação(ões)")

    if not novos_editais:
        print("✅ Nada a notificar após os tetos.")
        sys.exit(0)

    # 5. Agrupar editais por site para o resumo
    novos_por_site = {}
    for edital in novos_editais:
        site = edital['site']
        if site not in novos_por_site:
            novos_por_site[site] = []
        novos_por_site[site].append(edital)

    # 6. Enviar notificações individuais e registrar no banco
    print("📤 Enviando notificações...")
    falhas = 0
    for edital in novos_editais:
        if edital.get('status') == 'atualizacao':
            sucesso = notifier.enviar_atualizacao(edital)
        else:
            sucesso = notifier.enviar_edital(edital)

        if sucesso:
            storage.registrar(edital['titulo'], edital['url'], edital['site'])
        else:
            falhas += 1

    # 7. Enviar mensagem de resumo se houver mais de um edital
    if len(novos_editais) > 1:
        notifier.enviar_resumo(novos_por_site)

    # 8. Avisar no chat que houve corte — sem isso, a supressão parece falha
    if suprimidos > 0:
        notifier.enviar_status(
            f"⚠️ *{suprimidos}* edital(is) mais antigo(s) foram *suprimidos* nesta "
            f"rodada pelo teto de {MAX_ITENS_POR_ESTADO} por estado.\n"
            f"Eles não foram registrados no histórico e podem voltar a aparecer "
            f"em rodadas seguintes."
        )

    # 9. Expôr envio parcial — sem isso, uma rodada onde nada chega ao chat encerra
    # em "sucesso" (foi assim que o flood de 05/09 passou verde: 34 erros de taxa e
    # nada avisado). Não uso exit(1) de propósito: falhar o job faria o upload do
    # artifact ser pulado, e o histórico dos itens que chegaram se perderia.
    # Não atribuo causa neste texto: um envio pode falhar por limite de taxa, token
    # inválido ou chat removido. O motivo real sai no log (`[ERRO] Falha ao enviar
    # mensagem: ...`), então aqui só digo que não chegou e que o item ficou pendente.
    if falhas > 0:
        aviso = (f"⚠️ {falhas} de {len(novos_editais)} notificação(ões) não chegaram ao chat "
                 f"(motivo no log desta rodada). Ficaram fora do histórico e serão "
                 f"tentadas de novo na próxima rodada.")
        print(aviso)
        if os.environ.get('GITHUB_ACTIONS'):
            print(f"::warning::{aviso}")
        notifier.enviar_status(
            f"⚠️ *{falhas}* de *{len(novos_editais)}* notificação(ões) não chegaram "
            f"(veja o log desta rodada). Serão tentadas de novo na próxima rodada."
        )

    print("🎉 Processo concluído com sucesso!")

if __name__ == '__main__':
    # Modifica o diretório atual para garantir que caminhos relativos funcionem 
    # dependendo de onde o script foi chamado
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    main()
