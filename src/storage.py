"""
Persistência dos editais já vistos usando SQLite.
Compatível com o padrão do projeto Rss2Telegram anterior.
"""
import sqlite3
import hashlib
import os


class Storage:
    def __init__(self, db_path):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Cria a tabela de histórico se não existir."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hash TEXT UNIQUE NOT NULL,
                titulo TEXT,
                url TEXT,
                site TEXT,
                data_encontrado TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()

    @staticmethod
    def _gerar_hash(titulo, url):
        """Gera hash único baseado no título + URL do edital."""
        chave = f"{titulo.strip().lower()}|{url.strip().lower()}"
        return hashlib.md5(chave.encode('utf-8')).hexdigest()

    def ja_visto(self, titulo, url):
        """Verifica se o edital já foi notificado."""
        h = self._gerar_hash(titulo, url)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT 1 FROM history WHERE hash = ?', (h,))
        resultado = cursor.fetchone()
        conn.close()
        return resultado is not None

    def registrar(self, titulo, url, site):
        """Registra um edital como já visto."""
        h = self._gerar_hash(titulo, url)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute(
                'INSERT OR IGNORE INTO history (hash, titulo, url, site) VALUES (?, ?, ?, ?)',
                (h, titulo, url, site)
            )
            conn.commit()
        finally:
            conn.close()

    def registrar_lote(self, editais):
        """Registra múltiplos editais de uma vez (para primeira execução silenciosa)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        for edital in editais:
            h = self._gerar_hash(edital['titulo'], edital['url'])
            cursor.execute(
                'INSERT OR IGNORE INTO history (hash, titulo, url, site) VALUES (?, ?, ?, ?)',
                (h, edital['titulo'], edital['url'], edital.get('site', ''))
            )
        conn.commit()
        conn.close()

    def filtrar_novos(self, editais):
        """Retorna apenas editais que ainda não foram vistos."""
        novos = []
        for edital in editais:
            if not self.ja_visto(edital['titulo'], edital['url']):
                novos.append(edital)
        return novos

    def total_registrados(self):
        """Retorna o total de editais no histórico."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM history')
        total = cursor.fetchone()[0]
        conn.close()
        return total
