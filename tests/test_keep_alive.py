#!/usr/bin/env python3
"""
Testes unitários para o script de Keep-Alive e Wake-Up do Streamlit Community Cloud.
"""

import os
import unittest
from unittest.mock import MagicMock, patch

from selenium.common.exceptions import TimeoutException, WebDriverException

from src.keep_alive_streamlit import (
    DEFAULT_APP_URL,
    DEFAULT_USER_AGENT,
    build_arg_parser,
    check_and_wake_app,
    get_chrome_options,
    normalize_url,
    resolve_app_url,
    run_keep_alive,
    wait_for_active_session,
)


class TestUrlNormalization(unittest.TestCase):
    """Testes para a função normalize_url."""

    def test_url_already_valid_https(self):
        url = "https://observatoriotransitobauru.streamlit.app"
        self.assertEqual(normalize_url(url), url)

    def test_url_valid_http(self):
        url = "http://meu-app-teste.streamlit.app"
        self.assertEqual(normalize_url(url), url)

    def test_url_without_protocol_adds_https(self):
        raw = "observatoriotransitobauru.streamlit.app"
        expected = "https://observatoriotransitobauru.streamlit.app"
        self.assertEqual(normalize_url(raw), expected)

    def test_url_with_whitespace(self):
        raw = "   https://observatoriotransitobauru.streamlit.app   "
        expected = "https://observatoriotransitobauru.streamlit.app"
        self.assertEqual(normalize_url(raw), expected)

    def test_url_with_single_and_double_quotes(self):
        # Aspas duplas
        raw_double = '"https://observatoriotransitobauru.streamlit.app"'
        self.assertEqual(normalize_url(raw_double), "https://observatoriotransitobauru.streamlit.app")

        # Aspas simples
        raw_single = "'https://observatoriotransitobauru.streamlit.app'"
        self.assertEqual(normalize_url(raw_single), "https://observatoriotransitobauru.streamlit.app")

        # Aspas aninhadas e espaços
        raw_nested = " '\"observatoriotransitobauru.streamlit.app\"' "
        self.assertEqual(normalize_url(raw_nested), "https://observatoriotransitobauru.streamlit.app")

    def test_url_with_brackets(self):
        raw_brackets = "[https://observatoriotransitobauru.streamlit.app]"
        self.assertEqual(normalize_url(raw_brackets), "https://observatoriotransitobauru.streamlit.app")

        raw_brackets_no_proto = "[observatoriotransitobauru.streamlit.app]"
        self.assertEqual(normalize_url(raw_brackets_no_proto), "https://observatoriotransitobauru.streamlit.app")

    def test_url_empty_or_none(self):
        self.assertEqual(normalize_url(""), "")
        self.assertEqual(normalize_url(None), "")
        self.assertEqual(normalize_url("   "), "")


class TestUrlResolutionPriority(unittest.TestCase):
    """Testes para resolução de prioridade da URL (CLI > ENV > DEFAULT)."""

    def setUp(self):
        self.original_env = os.environ.get("STREAMLIT_APP_URL")

    def tearDown(self):
        if self.original_env is not None:
            os.environ["STREAMLIT_APP_URL"] = self.original_env
        else:
            os.environ.pop("STREAMLIT_APP_URL", None)

    def test_priority_cli_over_env_and_default(self):
        os.environ["STREAMLIT_APP_URL"] = "https://env-app.streamlit.app"
        cli_input = "https://cli-app.streamlit.app"

        resolved = resolve_app_url(cli_url=cli_input)
        self.assertEqual(resolved, "https://cli-app.streamlit.app")

    def test_priority_env_over_default_when_no_cli(self):
        os.environ["STREAMLIT_APP_URL"] = "https://env-app.streamlit.app"

        resolved = resolve_app_url(cli_url=None)
        self.assertEqual(resolved, "https://env-app.streamlit.app")

    def test_fallback_to_default_when_cli_and_env_absent(self):
        os.environ.pop("STREAMLIT_APP_URL", None)

        resolved = resolve_app_url(cli_url=None)
        self.assertEqual(resolved, DEFAULT_APP_URL)

    def test_fallback_when_cli_and_env_are_empty_strings(self):
        os.environ["STREAMLIT_APP_URL"] = "   "

        resolved = resolve_app_url(cli_url="")
        self.assertEqual(resolved, DEFAULT_APP_URL)

    def test_cli_and_env_with_formatting_quirks(self):
        # CLI com aspas e sem protocolo
        resolved_cli = resolve_app_url(cli_url="'custom-cli.streamlit.app'")
        self.assertEqual(resolved_cli, "https://custom-cli.streamlit.app")

        # Env com colchetes e espaços
        os.environ["STREAMLIT_APP_URL"] = " [custom-env.streamlit.app] "
        resolved_env = resolve_app_url(cli_url=None)
        self.assertEqual(resolved_env, "https://custom-env.streamlit.app")


class TestArgParser(unittest.TestCase):
    """Testes para o parser de linha de comando."""

    def setUp(self):
        self.parser = build_arg_parser()

    def test_defaults(self):
        args = self.parser.parse_args([])
        self.assertIsNone(args.url)
        self.assertEqual(args.timeout, 90)
        self.assertEqual(args.settle, 5)
        self.assertTrue(args.headless)

    def test_custom_arguments(self):
        args = self.parser.parse_args([
            "--url", "https://custom.streamlit.app",
            "--timeout", "120",
            "--settle", "10",
            "--no-headless",
        ])
        self.assertEqual(args.url, "https://custom.streamlit.app")
        self.assertEqual(args.timeout, 120)
        self.assertEqual(args.settle, 10)
        self.assertFalse(args.headless)


class TestChromeOptions(unittest.TestCase):
    """Testes para as opções do Chrome WebDriver."""

    def test_chrome_options_headless(self):
        options = get_chrome_options(headless=True)
        args = options.arguments

        self.assertIn("--headless=new", args)
        self.assertIn("--no-sandbox", args)
        self.assertIn("--disable-dev-shm-usage", args)
        self.assertIn("--disable-gpu", args)
        self.assertIn("--window-size=1920,1080", args)
        self.assertTrue(any("user-agent=" in arg for arg in args))

    def test_chrome_options_non_headless(self):
        options = get_chrome_options(headless=False)
        args = options.arguments

        self.assertNotIn("--headless=new", args)
        self.assertIn("--no-sandbox", args)


class TestKeepAliveSeleniumLogic(unittest.TestCase):
    """Testes unitários para a lógica de detecção e confirmação com mocks."""

    def test_check_and_wake_app_when_sleeping(self):
        mock_driver = MagicMock()
        mock_button = MagicMock()
        mock_button.is_displayed.return_value = True
        mock_button.is_enabled.return_value = True
        mock_driver.find_elements.return_value = [mock_button]

        woken = check_and_wake_app(mock_driver)

        self.assertTrue(woken)
        mock_button.click.assert_called_once()

    def test_check_and_wake_app_js_fallback_on_click_failure(self):
        mock_driver = MagicMock()
        mock_button = MagicMock()
        mock_button.is_displayed.return_value = True
        mock_button.is_enabled.return_value = True
        mock_button.click.side_effect = Exception("Element Click Intercepted")
        mock_driver.find_elements.return_value = [mock_button]

        woken = check_and_wake_app(mock_driver)

        self.assertTrue(woken)
        mock_driver.execute_script.assert_called_once_with("arguments[0].click();", mock_button)

    def test_check_and_wake_app_when_already_awake(self):
        mock_driver = MagicMock()
        mock_driver.find_elements.return_value = []

        woken = check_and_wake_app(mock_driver)

        self.assertFalse(woken)

    def test_wait_for_active_session_found_in_main_document(self):
        mock_driver = MagicMock()
        mock_container = MagicMock()
        # Primeiro find_elements retorna container no documento principal
        mock_driver.find_elements.return_value = [mock_container]

        active = wait_for_active_session(mock_driver, timeout=5, settle_seconds=0)

        self.assertTrue(active)
        mock_driver.switch_to.default_content.assert_called()

    def test_wait_for_active_session_found_in_iframe(self):
        mock_driver = MagicMock()
        mock_iframe = MagicMock()
        mock_container = MagicMock()

        # Simula: main doc não tem container (retorna vazio), depois encontra iframe, depois dentro do iframe encontra container
        def fake_find_elements(by, selector):
            if selector == '[data-testid="stAppViewContainer"]':
                # Se estivermos no iframe, retorna container
                if mock_driver.current_frame == "iframe":
                    return [mock_container]
                return []
            elif "iframe" in selector or selector == "iframe":
                return [mock_iframe]
            return []

        mock_driver.current_frame = None

        def fake_switch_frame(frame):
            mock_driver.current_frame = "iframe"

        def fake_switch_default():
            mock_driver.current_frame = None

        mock_driver.find_elements.side_effect = fake_find_elements
        mock_driver.switch_to.frame.side_effect = fake_switch_frame
        mock_driver.switch_to.default_content.side_effect = fake_switch_default

        active = wait_for_active_session(mock_driver, timeout=5, settle_seconds=0)
        self.assertTrue(active)

    def test_wait_for_active_session_timeout(self):
        mock_driver = MagicMock()
        # Sempre retorna vazio
        mock_driver.find_elements.return_value = []

        with self.assertRaises(TimeoutException):
            wait_for_active_session(mock_driver, timeout=1, settle_seconds=0)

    @patch("src.keep_alive_streamlit.time.sleep", return_value=None)
    @patch("src.keep_alive_streamlit.create_driver")
    @patch("src.keep_alive_streamlit.check_and_wake_app")
    @patch("src.keep_alive_streamlit.wait_for_active_session")
    def test_run_keep_alive_success(self, mock_wait, mock_wake, mock_create, mock_sleep):
        mock_driver = MagicMock()
        mock_driver.title = "Segurança Viária — Bauru/SP"
        mock_create.return_value = mock_driver
        mock_wake.return_value = True
        mock_wait.return_value = True

        result = run_keep_alive("https://observatoriotransitobauru.streamlit.app", settle_seconds=0)

        self.assertTrue(result)
        mock_driver.get.assert_called_once_with("https://observatoriotransitobauru.streamlit.app")
        mock_driver.quit.assert_called_once()

    @patch("src.keep_alive_streamlit.time.sleep", return_value=None)
    @patch("src.keep_alive_streamlit.create_driver")
    def test_run_keep_alive_timeout_exception_handling(self, mock_create, mock_sleep):
        mock_driver = MagicMock()
        mock_driver.get.side_effect = TimeoutException("Timeout loading page")
        mock_create.return_value = mock_driver

        result = run_keep_alive("https://observatoriotransitobauru.streamlit.app", settle_seconds=0)

        self.assertFalse(result)
        mock_driver.quit.assert_called_once()

    @patch("src.keep_alive_streamlit.time.sleep", return_value=None)
    @patch("src.keep_alive_streamlit.create_driver")
    def test_run_keep_alive_webdriver_exception_handling(self, mock_create, mock_sleep):
        mock_driver = MagicMock()
        mock_driver.get.side_effect = WebDriverException("Cannot connect to Chrome")
        mock_create.return_value = mock_driver

        result = run_keep_alive("https://observatoriotransitobauru.streamlit.app", settle_seconds=0)

        self.assertFalse(result)
        mock_driver.quit.assert_called_once()


if __name__ == "__main__":
    unittest.main()
