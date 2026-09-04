"""
Camada opcional de renderização via Playwright (Chromium headless).

Objetivo: sites que carregam os editais via JavaScript só revelam o conteúdo
depois que o browser executa o bundle. Este módulo renderiza a página e devolve
o HTML "pós-JS" para os parsers bs4 trabalharem em cima.

Tudo é deliberadamente OPCIONAL e resiliente:
- Se Playwright/Chromium não estiver instalado, renderizar() retorna None e o
  ScraperEngine simplesmente cai no caminho requests de sempre.
- O navegador é criado de forma preguiçosa (lazy) e reusado entre as chamadas
  dentro da mesma execução, fechando no fim via fechar_navegador().
"""
import threading

_LOCK = threading.Lock()
_PLAYWRIGHT = None
_BROWSER = None

_UA = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
)


def disponivel():
    """True se playwright está importável (não garante browser instalado)."""
    try:
        import playwright  # noqa: F401
        return True
    except Exception:
        return False


def _garantir_navegador():
    """Inicializa (uma vez) o Playwright e o Chromium headless. Propaga erros."""
    global _PLAYWRIGHT, _BROWSER
    with _LOCK:
        if _BROWSER is not None:
            return _BROWSER
        from playwright.sync_api import sync_playwright
        _PLAYWRIGHT = sync_playwright().start()
        _BROWSER = _PLAYWRIGHT.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-dev-shm-usage'],
        )
        return _BROWSER


def renderizar(url, timeout_ms=45000, espera_ms=3000, seletor_espera=None):
    """
    Renderiza `url` executando o JavaScript e retorna o HTML resultante.

    Args:
        url: endereço a carregar.
        timeout_ms: timeout da navegação.
        espera_ms: pausa extra após 'domcontentloaded' para o JS popular o DOM.
        seletor_espera: opcional — espera por este seletor CSS antes de capturar.

    Retorna None quando Playwright não está disponível ou a navegação falhou,
    permitindo ao chamador cair no caminho requests sem quebrar a execução.
    """
    if not disponivel():
        return None
    try:
        browser = _garantir_navegador()
    except Exception as e:
        print(f"      [browser] Chromium indisponível ({e.__class__.__name__}); usando requests")
        return None

    contexto = None
    try:
        contexto = browser.new_context(locale='pt-BR', user_agent=_UA)
        page = contexto.new_page()
        page.goto(url, timeout=timeout_ms, wait_until='domcontentloaded')
        if seletor_espera:
            try:
                page.wait_for_selector(seletor_espera, timeout=8000)
            except Exception:
                pass
        page.wait_for_timeout(espera_ms)
        html = page.content()
        contexto.close()
        return html
    except Exception as e:
        if contexto is not None:
            try:
                contexto.close()
            except Exception:
                pass
        print(f"      [browser] falha ao renderizar {url}: {str(e)[:80]}")
        return None


def fechar_navegador():
    """Encerra o Chromium e o driver Playwright (chamado ao final do scrape)."""
    global _PLAYWRIGHT, _BROWSER
    with _LOCK:
        if _BROWSER is not None:
            try:
                _BROWSER.close()
            except Exception:
                pass
            _BROWSER = None
        if _PLAYWRIGHT is not None:
            try:
                _PLAYWRIGHT.stop()
            except Exception:
                pass
            _PLAYWRIGHT = None
