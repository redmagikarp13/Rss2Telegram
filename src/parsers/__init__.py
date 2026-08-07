from .facto import FactoParser
from .ifes import IfesParser
from .ufmg import UfmgParser
from .generico_govbr import GenericoGovBrParser
from .generico import GenericoParser
from .cnpq import CnpqParser

# Mapa de parsers disponíveis (nome -> classe)
PARSERS = {
    'facto': FactoParser,
    'ifes': IfesParser,
    'ufmg': UfmgParser,
    'generico_govbr': GenericoGovBrParser,
    'generico': GenericoParser,
    'cnpq': CnpqParser,
}


def get_parser(nome):
    """Retorna uma instância do parser pelo nome."""
    parser_class = PARSERS.get(nome)
    if not parser_class:
        print(f"[AVISO] Parser '{nome}' não encontrado. Usando genérico.")
        parser_class = GenericoParser
    return parser_class()
