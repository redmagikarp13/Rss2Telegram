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
    def limpar_descricao(texto_bruto, max_chars=280):
        """
        Converte um trecho (possivelmente HTML) em texto plano de descrição.

        - Remove tags HTML
        - Descarta o rodapé padrão do WordPress ('O post X apareceu primeiro em Y')
        - Colapsa espaços e trunca em max_chars cortando na última palavra
        Retorna '' quando não há conteúdo útil.
        """
        if not texto_bruto:
            return ''
        texto = re.sub(r'<[^>]+>', ' ', texto_bruto)
        # WordPress feed trailer
        texto = re.sub(r'O\s+post\s+.{0,200}?apareceu\s+primeiro\s+em\s+[^.]+\.?\s*$',
                       '', texto, flags=re.IGNORECASE)
        texto = re.sub(r'\s+', ' ', texto).strip()
        if len(texto) > max_chars:
            corte = texto[:max_chars]
            espaco = corte.rfind(' ')
            if espaco > max_chars * 0.6:
                corte = corte[:espaco]
            texto = corte.rstrip(' ,;:.') + '…'
        return texto

    @staticmethod
    def extrair_descricao_do_contexto(link, titulo, max_chars=280):
        """
        Best-effort: procura um texto descritivo na vizinhança do link de edital.

        Percorre os ancestrais até achar um contêiner (li/article/div/p) que tenha
        mais texto além do próprio link, usa esse excedente como descrição.
        """
        pai = link.parent
        for _ in range(4):
            if pai is None or pai.name is None:
                break
            if pai.name in ('body', 'html', 'main', 'ul', 'ol', 'table'):
                break
            texto = BaseParser.limpar_texto(pai.get_text())
            # Remove o título para sobrar só a descrição
            resto = texto
            if titulo:
                resto = texto.replace(titulo, ' ', 1)
            resto = BaseParser.limpar_descricao(resto, max_chars)
            # Só aceita se houver texto relevante além do link
            if len(resto) >= 25:
                return resto
            pai = pai.parent
        return ''

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
