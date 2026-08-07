"""
Notificador via Telegram usando pyTelegramBotAPI (mesma lib do projeto anterior).
"""
import telebot
import time


class Notifier:
    def __init__(self, bot_token, chat_id, dryrun=False):
        self.chat_id = chat_id
        self.dryrun = dryrun
        if bot_token and not dryrun:
            self.bot = telebot.TeleBot(bot_token)
        else:
            self.bot = None

    def enviar_edital(self, edital):
        """Envia um único edital formatado para o Telegram."""
        emoji = edital.get('emoji', '📋')
        site = edital.get('site', 'Desconhecido')
        titulo = edital.get('titulo', 'Sem título')
        url = edital.get('url', '')
        data = edital.get('data', '')

        mensagem = f"{emoji} *Novo Edital Encontrado!*\n\n"
        mensagem += f"📌 *{self._escape_md(titulo)}*\n"
        mensagem += f"🏛️ {self._escape_md(site)}\n"
        if data:
            mensagem += f"📅 {self._escape_md(data)}\n"
        if url:
            mensagem += f"🔗 [Ver edital]({url})\n"

        if self.dryrun:
            print(f"[DRYRUN] Enviaria para {self.chat_id}:")
            print(mensagem)
            print("---")
            return True

        try:
            self.bot.send_message(
                self.chat_id,
                mensagem,
                parse_mode='Markdown',
                disable_web_page_preview=False
            )
            time.sleep(1)  # Rate limit do Telegram
            return True
        except Exception as e:
            print(f"[ERRO] Falha ao enviar mensagem: {e}")
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
