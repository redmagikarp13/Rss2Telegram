"""
Notificador via Telegram usando pyTelegramBotAPI.
Esquema "iluminati": PDFs são enviados como documentos inline (visualizável no Telegram),
páginas HTML são enviadas com preview de link.
"""
import telebot
import requests
import time
from urllib.parse import urlparse


def _detectar_tipo_url(url):
    """
    Detecta se a URL aponta para um PDF ou uma página HTML.
    Retorna: 'pdf' ou 'pagina'
    """
    if not url:
        return 'pagina'

    # Checa extensão direta (rápido, sem request)
    path = urlparse(url).path.lower()
    if path.endswith('.pdf'):
        return 'pdf'

    # Checa query params que indicam download/PDF
    query = urlparse(url).query.lower()
    if 'format=pdf' in query or 'type=pdf' in query or 'download=1' in query:
        return 'pdf'

    # HEAD request para detectar content-type (sem baixar o corpo)
    try:
        r = requests.head(
            url,
            timeout=5,
            allow_redirects=True,
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        ct = r.headers.get('Content-Type', '').lower()
        if 'application/pdf' in ct:
            return 'pdf'
        if 'octet-stream' in ct and url.lower().endswith('.pdf'):
            return 'pdf'
    except Exception:
        pass

    return 'pagina'


class Notifier:
    def __init__(self, bot_token, chat_id, dryrun=False):
        self.chat_id = chat_id
        self.dryrun = dryrun
        self._cache_tipo = {}  # Cache para não repetir HEAD na mesma URL
        if bot_token and not dryrun:
            self.bot = telebot.TeleBot(bot_token)
        else:
            self.bot = None

    def _tipo_url(self, url):
        """Versão com cache da detecção de tipo de URL."""
        if url not in self._cache_tipo:
            self._cache_tipo[url] = _detectar_tipo_url(url)
        return self._cache_tipo[url]

    def _resolver_urls(self, edital):
        """
        Retorna (pdf_url, page_url) considerando os campos disponíveis.

        Casos suportados:
        - Parser fornece 'pdf_url' separado (ex: FINATEC): pdf=pdf_url, page=url
        - 'url' é PDF direto (ex: PROEX): pdf=url, page=site_url
        - 'url' é página HTML: pdf='', page=url
        """
        url = edital.get('url', '')
        pdf_url = edital.get('pdf_url', '')
        site_url = edital.get('site_url', '')

        if pdf_url:
            return pdf_url, url
        if url and self._tipo_url(url) == 'pdf':
            return url, (site_url or url)
        return '', url

    def _montar_mensagem(self, edital, titulo_header):
        """Monta o texto base da mensagem."""
        emoji = edital.get('emoji', '📋')
        site = edital.get('site', 'Desconhecido')
        titulo = edital.get('titulo', 'Sem título')
        data = edital.get('data', '')

        pdf_url, page_url = self._resolver_urls(edital)

        mensagem = f"{emoji} *{titulo_header}*\n\n"
        mensagem += f"📌 *{self._escape_md(titulo)}*\n"
        mensagem += f"🏛️ {self._escape_md(site)}\n"
        if data:
            mensagem += f"📅 {self._escape_md(data)}\n"

        # Link sempre aponta para a PÁGINA (não pro PDF)
        if page_url:
            mensagem += f"🔗 [Ver na fonte]({page_url})\n"

        return mensagem

    def enviar_edital(self, edital):
        """Envia um edital — PDF como documento inline, página como mensagem com preview."""
        pdf_url, _ = self._resolver_urls(edital)
        mensagem = self._montar_mensagem(edital, 'Novo Edital Encontrado!')

        if self.dryrun:
            print(f"[DRYRUN] PDF={'sim' if pdf_url else 'não'} — Enviaria para {self.chat_id}:")
            print(mensagem)
            print("---")
            return True

        try:
            if pdf_url:
                # Envia PDF como documento — visualizável dentro do Telegram
                self.bot.send_document(
                    self.chat_id,
                    pdf_url,
                    caption=mensagem,
                    parse_mode='Markdown',
                )
            else:
                # Envia como mensagem com preview de link (thumbnail da página)
                self.bot.send_message(
                    self.chat_id,
                    mensagem,
                    parse_mode='Markdown',
                    disable_web_page_preview=False,
                )

            time.sleep(1)  # Rate limit do Telegram
            return True
        except Exception as e:
            print(f"[ERRO] Falha ao enviar mensagem: {e}")
            # Fallback: se sendDocument falhar (PDF muito grande, timeout), manda como mensagem
            try:
                self.bot.send_message(
                    self.chat_id,
                    mensagem,
                    parse_mode='Markdown',
                    disable_web_page_preview=False,
                )
                time.sleep(1)
                return True
            except Exception as e2:
                print(f"[ERRO] Fallback também falhou: {e2}")
                return False

    def enviar_atualizacao(self, edital):
        """Envia atualização de edital — mesma lógica de PDF/página."""
        pdf_url, _ = self._resolver_urls(edital)
        mensagem = self._montar_mensagem(edital, 'Edital Atualizado!')

        if self.dryrun:
            print(f"[DRYRUN] PDF={'sim' if pdf_url else 'não'} — Atualização para {self.chat_id}:")
            print(mensagem)
            print("---")
            return True

        try:
            if pdf_url:
                self.bot.send_document(
                    self.chat_id,
                    pdf_url,
                    caption=mensagem,
                    parse_mode='Markdown',
                )
            else:
                self.bot.send_message(
                    self.chat_id,
                    mensagem,
                    parse_mode='Markdown',
                    disable_web_page_preview=False,
                )

            time.sleep(1)
            return True
        except Exception as e:
            print(f"[ERRO] Falha ao enviar atualização: {e}")
            try:
                self.bot.send_message(
                    self.chat_id,
                    mensagem,
                    parse_mode='Markdown',
                    disable_web_page_preview=False,
                )
                time.sleep(1)
                return True
            except Exception as e2:
                print(f"[ERRO] Fallback da atualização falhou: {e2}")
                return False

    def enviar_resumo(self, novos_por_site):
        """Envia um resumo de todos os novos editais encontrados."""
        if not novos_por_site:
            return

        total = sum(len(editais) for editais in novos_por_site.values())
        mensagem = f"📊 *Resumo — {total} novo(s) edital(is) encontrado(s):*\n\n"

        for site, editais in novos_por_site.items():
            mensagem += f"▸ *{self._escape_md(site)}*: {len(editais)} edital(is)\n"

        if self.dryrun:
            print(f"[DRYRUN] Resumo:")
            print(mensagem)
            return

        try:
            self.bot.send_message(
                self.chat_id,
                mensagem,
                parse_mode='Markdown'
            )
        except Exception as e:
            print(f"[ERRO] Falha ao enviar resumo: {e}")

    def enviar_status(self, mensagem_texto):
        """Envia mensagem de status (ex: primeira execução)."""
        if self.dryrun:
            print(f"[DRYRUN] Status: {mensagem_texto}")
            return

        try:
            self.bot.send_message(
                self.chat_id,
                mensagem_texto,
                parse_mode='Markdown'
            )
        except Exception as e:
            print(f"[ERRO] Falha ao enviar status: {e}")

    @staticmethod
    def _escape_md(text):
        """Escapa caracteres especiais do Markdown do Telegram."""
        chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        for char in chars:
            text = text.replace(char, f'\\{char}')
        return text
