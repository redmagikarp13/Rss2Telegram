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

    @staticmethod
    def extrair_data_do_element_pai(link, max_profundidade=3):
        """Tenta extrair uma data (dd/mm/aaaa) de elementos próximos ao link."""
        import re
        pai = link.parent
        for _ in range(max_profundidade):
            if not pai or pai.name is None:
                break
            # Buscar em elementos com classe de data
            for elem in pai.find_all(class_=lambda x: x and any(
                kw in x.lower() for kw in ['date', 'data', 'time', 'published']
            )):
                texto = elem.get_text()
                match = re.search(r'(\d{1,2}/\d{1,2}/\d{2,4})', texto)
                if match:
                    return match.group(1)
            # Buscar em tags <time>
            for time_tag in pai.find_all('time'):
                datetime_attr = time_tag.get('datetime', '')
                # Formato ISO (aaaa-mm-dd)
                match = re.search(r'(\d{4})-(\d{2})-(\d{2})', datetime_attr)
                if match:
                    return f"{match.group(3)}/{match.group(2)}/{match.group(1)}"
                # Formato dd/mm/aaaa
                match = re.search(r'(\d{1,2}/\d{1,2}/\d{2,4})', datetime_attr)
                if match:
                    return match.group(1)
                match = re.search(r'(\d{1,2}/\d{1,2}/\d{2,4})', time_tag.get_text())
                if match:
                    return match.group(1)
            # Buscar no texto direto do pai (excluindo textos de links filhos)
            textos = pai.find_all(string=True)
            for texto in textos:
                if texto.parent == link or link in texto.parent.parents:
                    continue
                match = re.search(r'(\d{1,2}/\d{1,2}/\d{2,4})', str(texto))
                if match:
                    return match.group(1)
            pai = pai.parent
        return ''
