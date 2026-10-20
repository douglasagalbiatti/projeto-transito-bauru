#!/usr/bin/env python3
"""
Keep-Alive e Wake-Up Automático para Aplicações no Streamlit Community Cloud.

Contexto:
    O Streamlit Community Cloud coloca aplicações em modo sleep (dormência) após
    períodos de inatividade. Requisições HTTP puras (requests, curl) não acordam
    a aplicação, pois não executam o motor JavaScript, não estabelecem a conexão
    interativa via WebSocket e não interagem com o botão de wake-up.
    
    Este script utiliza Selenium WebDriver com Google Chrome Headless para:
    1. Acessar a aplicação de forma resiliente.
    2. Detectar se a aplicação está em modo sleep ("Yes, get this app back up!").
    3. Clicar no botão de acordar, se necessário.
    4. Aguardar a montagem do elemento '[data-testid="stAppViewContainer"]',
       suportando tanto instâncias diretas quanto o iframe do Streamlit Community Cloud,
       assegurando o handshake completo de WebSocket e mantendo a aplicação ativa.
"""

import argparse
import logging
import os
import sys
import time
from typing import Optional

from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# ==============================================================================
# CONFIGURAÇÕES E CONSTANTES PADRÃO
# ==============================================================================
DEFAULT_APP_URL = "https://observatoriotransitobauru.streamlit.app"
DEFAULT_TIMEOUT_SECONDS = 90
DEFAULT_SETTLE_SECONDS = 5
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# Configuração de Logging com formato legível e timestamps
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("keep_alive_streamlit")


# ==============================================================================
# FUNÇÕES DE RESOLUÇÃO E NORMALIZAÇÃO DE URL
# ==============================================================================
def normalize_url(url: Optional[str]) -> str:
    """
    Normaliza uma URL:
    - Trata valores None ou vazios.
    - Remove espaços nas extremidades.
    - Remove aspas (simples ou duplas) e colchetes acidentais (ex: '[https://...]').
    - Adiciona automaticamente 'https://' caso nenhum protocolo (http/https) esteja presente.
    """
    if not url:
        return ""

    # Remove espaços, aspas simples/duplas e colchetes
    cleaned = url.strip().strip("'\"[]").strip()
    if not cleaned:
        return ""

    # Adiciona https:// se não possuir esquema
    if not (cleaned.startswith("http://") or cleaned.startswith("https://")):
        cleaned = f"https://{cleaned}"

    return cleaned


def resolve_app_url(
    cli_url: Optional[str] = None,
    env_var_name: str = "STREAMLIT_APP_URL",
    default_url: str = DEFAULT_APP_URL,
) -> str:
    """
    Resolve a URL de destino respeitando a seguinte ordem de prioridade:
    1. Argumento passado via CLI (--url)
    2. Variável de ambiente (por padrão STREAMLIT_APP_URL)
    3. URL padrão oficial da aplicação
    """
    if cli_url and cli_url.strip():
        logger.info("URL resolvida a partir de argumento CLI (--url).")
        return normalize_url(cli_url)

    env_val = os.environ.get(env_var_name)
    if env_val and env_val.strip():
        logger.info(f"URL resolvida a partir da variável de ambiente '{env_var_name}'.")
        return normalize_url(env_val)

    logger.info("URL resolvida a partir do fallback padrão da aplicação.")
    return normalize_url(default_url)


# ==============================================================================
# CONFIGURAÇÃO DO SELENIUM WEBDRIVER
# ==============================================================================
def get_chrome_options(
    headless: bool = True,
    user_agent: str = DEFAULT_USER_AGENT,
) -> Options:
    """
    Configura e retorna as opções do Chrome para execução confiável em ambientes CI/CD Linux.
    """
    options = Options()

    if headless:
        # Nova implementação de headless do Chrome (mais moderna e compatível com WebSockets)
        options.add_argument("--headless=new")

    # Flags recomendadas para execução em contêineres e runners de CI (ex: GitHub Actions)
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(f"user-agent={user_agent}")

    # Atenua detecção de automação
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    return options


def create_driver(
    headless: bool = True,
    user_agent: str = DEFAULT_USER_AGENT,
) -> WebDriver:
    """
    Inicializa o driver Chrome utilizando Selenium Manager nativo (Selenium >= 4.15).
    """
    options = get_chrome_options(headless=headless, user_agent=user_agent)
    logger.info("Inicializando Google Chrome WebDriver...")
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(60)
    return driver


# ==============================================================================
# FLUXO DE DETECÇÃO E WAKE-UP DO STREAMLIT
# ==============================================================================
def check_and_wake_app(driver: WebDriver, verbose: bool = True) -> bool:
    """
    Verifica de forma resiliente a presença do botão de 'wake-up' do Streamlit Community Cloud
    ("Yes, get this app back up!") sem quebrar o fluxo. Se visível, efetua o clique.

    Retorna:
        bool: True se o botão foi detectado e clicado; False caso contrário.
    """
    if verbose:
        logger.info("Verificando se a aplicação está em modo sleep...")

    xpath_wake_button = (
        "//button["
        "contains(normalize-space(.), 'Yes, get this app back up!') or "
        "contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), "
        "'get this app back up')"
        "]"
    )

    try:
        driver.switch_to.default_content()
        wake_buttons = driver.find_elements(By.XPATH, xpath_wake_button)

        if not wake_buttons:
            # Checa se o botão está dentro de algum iframe
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            for ifr in iframes:
                try:
                    driver.switch_to.frame(ifr)
                    nested_buttons = driver.find_elements(By.XPATH, xpath_wake_button)
                    if nested_buttons:
                        wake_buttons = nested_buttons
                        break
                except Exception:
                    continue
                finally:
                    driver.switch_to.default_content()

        if not wake_buttons:
            if verbose:
                logger.info("Nenhum botão de sono detectado. A aplicação já está acordada ou carregando.")
            return False

        for btn in wake_buttons:
            if btn.is_displayed() and btn.is_enabled():
                logger.warning("MODO SLEEP DETECTADO! Botão 'Yes, get this app back up!' encontrado.")
                try:
                    btn.click()
                except Exception as click_err:
                    logger.info(f"Clique nativo interceptado ({click_err}), tentando via JavaScript executor.")
                    driver.execute_script("arguments[0].click();", btn)

                logger.info("Botão de acordar acionado com sucesso. Aguardando inicialização...")
                return True

        logger.info("Botões encontrados não estavam interativos no momento.")
        return False

    except NoSuchElementException:
        return False
    except Exception as exc:
        logger.warning(f"Aviso durante checagem de modo sleep (fluxo prossegue normalmente): {exc}")
        return False


def wait_for_active_session(
    driver: WebDriver,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    settle_seconds: int = DEFAULT_SETTLE_SECONDS,
) -> bool:
    """
    Aguarda a montagem do container principal da aplicação Streamlit ([data-testid="stAppViewContainer"]).
    Trata com resiliência:
    1. Instâncias diretas (onde stAppViewContainer fica no documento principal).
    2. Streamlit Community Cloud (onde o app roda encapsulado em um iframe, ex: title="streamlitApp").

    Assegura que o handshake bidirecional de WebSocket foi concluído com sucesso.
    """
    logger.info(
        f"Aguardando confirmação de sessão ativa ('[data-testid=\"stAppViewContainer\"]', timeout={timeout}s)..."
    )

    end_time = time.time() + timeout
    found = False

    while time.time() < end_time:
        # 1. Verifica no documento principal
        driver.switch_to.default_content()
        containers = driver.find_elements(By.CSS_SELECTOR, '[data-testid="stAppViewContainer"]')
        if containers:
            logger.info("ELEMENTO ENCONTRADO: '[data-testid=\"stAppViewContainer\"]' no documento principal!")
            found = True
            break

        # 2. Verifica se o Streamlit está encapsulado em um iframe (padrão Community Cloud)
        iframes = driver.find_elements(
            By.CSS_SELECTOR,
            'iframe[title="streamlitApp"], iframe#streamlitApp, iframe[src*="/~/+/"]'
        )
        if not iframes:
            iframes = driver.find_elements(By.TAG_NAME, "iframe")

        for ifr in iframes:
            try:
                driver.switch_to.default_content()
                driver.switch_to.frame(ifr)
                sub_containers = driver.find_elements(By.CSS_SELECTOR, '[data-testid="stAppViewContainer"]')
                if sub_containers:
                    logger.info("ELEMENTO ENCONTRADO: '[data-testid=\"stAppViewContainer\"]' dentro de iframe do Streamlit!")
                    found = True
                    break
            except Exception:
                continue

        if found:
            break

        # Caso ainda esteja na tela de boot/sleep, tenta novamente acionar o wake-up se reaparecer
        driver.switch_to.default_content()
        check_and_wake_app(driver, verbose=False)

        time.sleep(2)

    if found:
        if settle_seconds > 0:
            logger.info(
                f"Aguardando {settle_seconds}s para consolidação dos frames de WebSocket e heartbeat da sessão..."
            )
            time.sleep(settle_seconds)
        return True

    raise TimeoutException(
        f"Elemento '[data-testid=\"stAppViewContainer\"]' não montado após {timeout}s."
    )


# ==============================================================================
# EXECUÇÃO PRINCIPAL
# ==============================================================================
def run_keep_alive(
    url: str,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    settle_seconds: int = DEFAULT_SETTLE_SECONDS,
    headless: bool = True,
) -> bool:
    """
    Executa o fluxo completo de Keep-Alive:
    - Abre o navegador headless.
    - Navega até a URL especificada.
    - Detecta e clica no botão de acordar se a aplicação estiver dormindo.
    - Confirma a conexão ativa via WebSocket aguardando o container do Streamlit.
    - Garante o encerramento limpo do WebDriver via bloco finally.
    """
    driver: Optional[WebDriver] = None

    logger.info("=" * 70)
    logger.info("INICIANDO PROCESSO DE KEEP-ALIVE STREAMLIT")
    logger.info(f"URL de Destino : {url}")
    logger.info(f"Timeout        : {timeout}s")
    logger.info(f"Modo Headless  : {headless}")
    logger.info("=" * 70)

    try:
        driver = create_driver(headless=headless)

        logger.info(f"Navegando para: {url}...")
        driver.get(url)

        # Pequena pausa para carregamento inicial da casca da página
        time.sleep(4)

        # Checa e clica no botão de acordar se o app estiver dormindo
        check_and_wake_app(driver)

        # Aguarda a montagem do container e handshake de WebSocket
        success = wait_for_active_session(
            driver=driver,
            timeout=timeout,
            settle_seconds=settle_seconds,
        )

        if success:
            logger.info("SUCESSO: Aplicação Streamlit está 100% ONLINE e ATIVA!")
            logger.info(f"Título da página: '{driver.title}'")
            return True
        else:
            logger.error("FALHA: Não foi possível confirmar a sessão ativa da aplicação.")
            return False

    except TimeoutException as te:
        logger.error(
            f"FALHA POR TIMEOUT: O Streamlit não montou 'stAppViewContainer' no tempo limite ({timeout}s). {te}"
        )
        return False
    except WebDriverException as we:
        logger.error(f"ERRO DE WEBDRIVER: Falha de comunicação com o navegador Chrome: {we}")
        return False
    except Exception as exc:
        logger.error(f"ERRO INESPERADO no processo de Keep-Alive: {exc}", exc_info=True)
        return False
    finally:
        if driver is not None:
            logger.info("Finalizando e destruindo instância do WebDriver...")
            try:
                driver.quit()
                logger.info("WebDriver encerrado com segurança.")
            except Exception as quit_err:
                logger.warning(f"Aviso ao encerrar driver: {quit_err}")


def build_arg_parser() -> argparse.ArgumentParser:
    """Constrói o parser de argumentos CLI."""
    parser = argparse.ArgumentParser(
        description="Streamlit Community Cloud Keep-Alive & Anti-Sleep Bot",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--url",
        type=str,
        default=None,
        help="URL pública da aplicação Streamlit (sobrescreve STREAMLIT_APP_URL e o fallback)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="Tempo máximo de espera em segundos para o carregamento do Streamlit",
    )
    parser.add_argument(
        "--settle",
        type=int,
        default=DEFAULT_SETTLE_SECONDS,
        help="Segundos de estabilização pós-carregamento para handshake WebSocket",
    )
    parser.add_argument(
        "--no-headless",
        dest="headless",
        action="store_false",
        default=True,
        help="Desativa o modo headless para depuração visual em ambiente local",
    )
    return parser


def main() -> int:
    """Ponto de entrada do script."""
    parser = build_arg_parser()
    args = parser.parse_args()

    target_url = resolve_app_url(cli_url=args.url)
    if not target_url:
        logger.error("Nenhuma URL válida pôde ser resolvida. Abortando execução.")
        return 1

    ok = run_keep_alive(
        url=target_url,
        timeout=args.timeout,
        settle_seconds=args.settle,
        headless=args.headless,
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
