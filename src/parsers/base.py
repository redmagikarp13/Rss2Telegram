"""
Classe base para todos os parsers de sites.
"""
from abc import ABC, abstractmethod
import re


class BaseParser(ABC):
    """Interface base que todos os parsers devem implementar."""

    @abstractmethod
    def parse(self, html, url_base):
        """
        Faz o parsing do HTML e retorna lista de editais encontrados.

        Args:
            html: conteúdo HTML da página
            url_base: URL base do site para resolver links relativos

        Returns:
            Lista de dicts com: {titulo, url, data}
        """
        pass

    @staticmethod
    def limpar_texto(texto):
        """Remove espaços extras e quebras de linha desnecessárias."""
        if not texto:
            return ''
        texto = re.sub(r'\s+', ' ', texto)
        return texto.strip()

    @staticmethod
    def resolver_url(href, url_base):
        """Resolve URLs relativas em absolutas."""
        if not href:
            return ''
        if href.startswith('http'):
            return href
        if href.startswith('//'):
            return 'https:' + href
        if href.startswith('/'):
            # Extrair domínio base
            from urllib.parse import urlparse
            parsed = urlparse(url_base)
            return f"{parsed.scheme}://{parsed.netloc}{href}"
        return url_base.rstrip('/') + '/' + href
