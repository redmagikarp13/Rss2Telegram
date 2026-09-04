from .facto import FactoParser
from .ifes import IfesParser
from .ufmg import UfmgParser
from .generico_govbr import GenericoGovBrParser
from .generico import GenericoParser
from .cnpq import CnpqParser
from .cnpq_govbr import CnpqGovBrParser
from .unicamp_prp import UnicampPrpParser
from .ead_editais import EadEditaisParser
from .unac_es import UnacEsParser
from .proiff import ProIffParser
from .proex_ifes import ProexIfesParser
from .sigpesq_ifes import SigpesqIfesParser
from .finatec import FinatecParser

# Mapa de parsers disponíveis (nome -> classe)
PARSERS = {
    'facto': FactoParser,
    'ifes': IfesParser,
    'ufmg': UfmgParser,
    'generico_govbr': GenericoGovBrParser,
    'generico': GenericoParser,
    'cnpq': CnpqParser,
    'cnpq_govbr': CnpqGovBrParser,
    'unicamp_prp': UnicampPrpParser,
    'ead_editais': EadEditaisParser,
    'unac_es': UnacEsParser,
    'proiff': ProIffParser,
    'proex_ifes': ProexIfesParser,
    'sigpesq_ifes': SigpesqIfesParser,
    'finatec': FinatecParser,
}


def get_parser(nome):
    """Retorna uma instância do parser pelo nome."""
    parser_class = PARSERS.get(nome)
    if not parser_class:
        print(f"[AVISO] Parser '{nome}' não encontrado. Usando genérico.")
        parser_class = GenericoParser
    return parser_class()
