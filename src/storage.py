"""
Persistência dos editais já vistos usando SQLite.
Compatível com o padrão do projeto Rss2Telegram anterior.
Inclui detecção de atualizações em editais existentes (mesma URL, conteúdo diferente).
"""
import sqlite3
import hashlib
import os


class Storage:
    def __init__(self, db_path):
        self.db_path = db_path
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Cria as tabelas de histórico se não existirem."""
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
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS url_hashes (
                url_hash TEXT PRIMARY KEY,
                titulo_hash TEXT NOT NULL
            )
        ''')
        conn.commit()
        conn.close()

    @staticmethod
    def _gerar_hash(titulo, url):
        """Gera hash único baseado no título + URL do edital."""
        chave = f"{titulo.strip().lower()}|{url.strip().lower()}"
        return hashlib.md5(chave.encode('utf-8')).hexdigest()

    @staticmethod
    def _gerar_hash_url(url):
        """Gera hash baseado apenas na URL do edital."""
        return hashlib.md5(url.strip().lower().encode('utf-8')).hexdigest()

    def eh_novo(self, titulo, url):
        """
        Verifica o status de um edital.
        Retorna:
            'novo'     — URL nunca vista antes
            'atualizacao' — URL já vista, mas título mudou
            'duplicado'  — já visto exatamente como está
        """
        h = self._gerar_hash(titulo, url)
        uh = self._gerar_hash_url(url)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 1. Hash exato já existe?
        cursor.execute('SELECT 1 FROM history WHERE hash = ?', (h,))
        if cursor.fetchone():
            conn.close()
            return 'duplicado'

        # 2. URL já foi vista com título diferente?
        cursor.execute('SELECT titulo_hash FROM url_hashes WHERE url_hash = ?', (uh,))
        row = cursor.fetchone()
        conn.close()

        if row:
            titulo_hash = self._gerar_hash(titulo, '')
            if row[0] != titulo_hash:
                return 'atualizacao'
            return 'duplicado'

        return 'novo'

    def registrar(self, titulo, url, site):
        """Registra um edital como visto (novo ou atualização)."""
        h = self._gerar_hash(titulo, url)
        uh = self._gerar_hash_url(url)
        th = self._gerar_hash(titulo, '')

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute(
                'INSERT OR IGNORE INTO history (hash, titulo, url, site) VALUES (?, ?, ?, ?)',
                (h, titulo, url, site)
            )
            cursor.execute(
                'INSERT OR REPLACE INTO url_hashes (url_hash, titulo_hash) VALUES (?, ?)',
                (uh, th)
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
            uh = self._gerar_hash_url(edital['url'])
            th = self._gerar_hash(edital['titulo'], '')
            cursor.execute(
                'INSERT OR IGNORE INTO history (hash, titulo, url, site) VALUES (?, ?, ?, ?)',
                (h, edital['titulo'], edital['url'], edital.get('site', ''))
            )
            cursor.execute(
                'INSERT OR REPLACE INTO url_hashes (url_hash, titulo_hash) VALUES (?, ?)',
                (uh, th)
            )
        conn.commit()
        conn.close()

    def filtrar_novos(self, editais):
        """
        Retorna apenas editais novos ou com atualização detectada.
        Cada item terá um campo extra 'status' = 'novo' | 'atualizacao'.
        """
        novos = []
        for edital in editais:
            status = self.eh_novo(edital['titulo'], edital['url'])
            if status in ('novo', 'atualizacao'):
                edital['status'] = status
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
