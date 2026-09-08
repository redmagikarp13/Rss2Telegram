"""
Parser para o site do IFES - PRPPG (prppg.ifes.edu.br).
Estrutura: Joomla + K2, template padrão governo federal.
URL: https://prppg.ifes.edu.br/editais
"""
from bs4 import BeautifulSoup
import re
from urllib.parse import urlsplit

from .base import BaseParser


class IfesParser(BaseParser):
    # Cromo de navegação: item de menu, cabeçalho ou rodapé nunca é um edital.
    # Medido em 08/09/2026 no HTML vivo das 15 fontes que usam este parser: 137 das 629
    # saídas que o parser produzia estavam dentro de uma dessas estruturas. Isoladas da
    # regra de auto-referência abaixo, estas etiquetas e classes cortam 7 saídas, todas
    # menu ou link institucional: 'Processos Seletivos' (breadcrumb e item de menu da
    # seção-mãe) e 'Acesse processos seletivos de outros campi'. Dois títulos desse tipo
    # foram notificados como 'novo edital' em 08/09/2026, porque o feed da fonte tinha
    # esvaziado a janela de 90 dias e o scraper caiu no HTML -- ver
    # ScraperEngine._tentar_rss.
    _CROMO_ETIQUETAS = ('nav', 'header', 'footer', 'aside')

    # Nome de classe de estrutura de navegação. 'menu' e 'navbar' já bastavam para o
    # menu; 'breadcrumb', 'pagination' e as duas grafias de 'navegação' entraram por
    # causa do que medi no corpus de 08/09/2026:
    #   - o template do IFES renderiza a trilha de navegação como
    #     <div class="rastro-navegacao row-flutuante">, que não contém 'menu' e por
    #     isso deixava passar o link da seção-mãe ('Processos Seletivos');
    #   - a paginação é <li class="pagination-next"><a>Próximo</a>, e o 'Próximo' era
    #     coletado como item (dois campi), ou seja: ia chegar ao chat como edital.
    # Nas 15 páginas, 28 anchors estão dentro de uma classe de navegação/breadcrumb e
    # exatamente 10 deles ainda eram aceitos pelo parser -- todos 'Processos Seletivos'.
    _CROMO_CLASSE = re.compile(r'menu|navbar|pagination|breadcrumb|navegac|navigac', re.I)

    @classmethod
    def _eh_cromo_navegacao(cls, link):
        """True se o <a> está dentro de estrutura de navegação, não de lista de editais."""
        for ancestral in link.parents:
            nome = (ancestral.name or '').lower()
            if nome in cls._CROMO_ETIQUETAS:
                return True
            if (ancestral.get('role') or '').lower() == 'navigation':
                return True
            classes = ancestral.get('class') or []
            if any(cls._CROMO_CLASSE.search(c) for c in classes):
                return True
            # Item de menu do Joomla é sempre <li class="item-<número> [parent]">.
            # O prefixo sozinho não basta: 'item-container' não é número.
            if nome == 'li' and any(
                c.startswith('item-') and c[5:].isdigit() for c in classes
            ):
                return True
        return False

    @staticmethod
    def _mesma_pagina(url, url_base):
        """True se o link aponta para a própria página da lista, e não para um edital.

        Regra estrutural, complementar ao filtro de menu acima, porque o cromo aparece
        em mais de um lugar do DOM: 132 das 629 saídas que o parser commitado produzia
        para as 15 fontes deste parser apontavam para a própria página -- o item de
        menu da seção atual ('li.item-530 current active') e dez repetições do módulo de
        tiles de seção ('div.tileItem > span3.tileInfo'), cada uma com uma data vizinha
        diferente. Um edital sempre tem página própria; se o link leva de volta à lista,
        ele não é um item da lista.

        Compara o query string também, e não só o path. Entre as 132, isto deixa de
        fora apenas os dois 'Próximo' de ?start=10 (que a regra de 'pagination' acima já
        cobre), e evita o modo de falha silencioso: uma fonte cujos editais se distinguem
        por query ('lista.php?id=123') teria a lista inteira descartada se a comparação
        ignorasse o ?... . Na dúvida entre um incômodo visível e um desaparecimento
        mudo, o código escolhe o incômodo visível.
        """
        def chave(u):
            parte = urlsplit(u or '')
            return (parte.netloc.lower().removeprefix('www.'),
                    parte.path.rstrip('/').lower(), parte.query)
        return bool(url_base) and chave(url) == chave(url_base)

    def parse(self, html, url_base):
        editais = []
        soup = BeautifulSoup(html, 'html.parser')

        # O IFES usa Joomla com K2 - editais ficam em listas de itens
        # Tentar múltiplos seletores comuns do template gov
        seletores = [
            '.itemList .itemContainer',      # K2 item list
            '.items-row .item',              # Joomla category list
            '#content .item-page',           # Joomla article
            '.blog-items .blog-item',        # Blog layout
            '.category-list .category-item', # Category layout
            'table.category tbody tr',       # Tabela de categorias
            '#content ul li',                # Lista simples
            '#system-message-container ~ div ul li',  # Lista após mensagem
            '.itemListView .itemList .itemContainer',
        ]

        for seletor in seletores:
            items = soup.select(seletor)
            if items:
                for item in items:
                    link = item.find('a', href=True)
                    # Um dos seletores é largo o bastante para casar um módulo de menu
                    # dentro do conteúdo ('#content ul li'), então o filtro de cromo vale
                    # aqui também, não só no fallback lá embaixo.
                    if link and self._eh_cromo_navegacao(link):
                        continue
                    if link:
                        titulo = self.limpar_texto(link.get_text())
                        url = self.resolver_url(link.get('href', ''), url_base)
                        if self._mesma_pagina(url, url_base):
                            continue

                        if titulo and url and len(titulo) > 5:
                            # Tentar extrair data
                            data = ''
                            data_elem = item.find(class_=lambda x: x and ('date' in x.lower() or 'data' in x.lower())) if item else None
                            if data_elem:
                                data = self.limpar_texto(data_elem.get_text())
                            if not data:
                                data = self.extrair_data_do_element_pai(link)

                            editais.append({
                                'titulo': titulo,
                                'url': url,
                                'data': data,
                            })
                # O break só pode existir porque os filtros acima existem. Ele para no
                # primeiro seletor que produzir qualquer coisa, então um seletor que
                # devolva apenas cromo entope a cascata e a lista real de editais nunca
                # chega a ser tentada: foi o que aconteceu com 9 das 15 fontes deste
                # parser, que entregavam um único link de menu repetido ~10 vezes e
                # nenhum edital. Por isso os filtros vêm antes, e não depois do break.
                if editais:
                    break

        # Fallback: buscar todos os links com "edital" no texto ou href
        if not editais:
            all_links = soup.find_all('a', href=True)
            for link in all_links:
                if self._eh_cromo_navegacao(link):
                    continue
                texto = self.limpar_texto(link.get_text())
                href = link.get('href', '')

                if ('edital' in texto.lower() or 'edital' in href.lower() or
                    'bolsa' in texto.lower() or 'seleção' in texto.lower() or
                    'seletivo' in texto.lower()):

                    url = self.resolver_url(href, url_base)

                    if self._mesma_pagina(url, url_base):
                        continue

                    if texto and url and len(texto) > 10:
                        data = self.extrair_data_do_element_pai(link)
                        editais.append({
                            'titulo': texto,
                            'url': url,
                            'data': data,
                        })

        return editais
