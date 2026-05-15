"""
Playwright UI tests for RAG From Scratch.

Requirements:
    pip install pytest pytest-playwright
    playwright install chromium

Run:
    pytest -m ui
    pytest tests/test_ui.py -v --headed   # with visible browser
"""

import pytest
from playwright.sync_api import Page, expect


BASE_URL = "http://localhost:8001"


@pytest.fixture(scope="module")
def page_loaded(page: Page):
    """Navigate to the app and wait for it to be ready."""
    page.goto(BASE_URL)
    page.wait_for_load_state("networkidle", timeout=15000)
    return page


# ═══════════════════════════════════════════════════════════════
# Page Load
# ═══════════════════════════════════════════════════════════════

@pytest.mark.ui
def test_page_loads(page: Page):
    page.goto(BASE_URL)
    expect(page).to_have_title("RAG From Scratch")


@pytest.mark.ui
def test_sidebar_visible(page_loaded: Page):
    expect(page_loaded.locator(".sidebar")).to_be_visible()


@pytest.mark.ui
def test_chat_area_visible(page_loaded: Page):
    expect(page_loaded.locator("#chatArea")).to_be_visible()


@pytest.mark.ui
def test_welcome_message_shown(page_loaded: Page):
    expect(page_loaded.locator("#welcomeMessage")).to_be_visible()


@pytest.mark.ui
def test_query_input_present(page_loaded: Page):
    expect(page_loaded.locator("#queryInput")).to_be_visible()


@pytest.mark.ui
def test_send_button_present(page_loaded: Page):
    expect(page_loaded.locator("#sendBtn")).to_be_visible()


# ═══════════════════════════════════════════════════════════════
# Sidebar Interactions
# ═══════════════════════════════════════════════════════════════

@pytest.mark.ui
def test_new_chat_button_clickable(page: Page):
    page.goto(BASE_URL)
    page.wait_for_load_state("networkidle", timeout=15000)
    btn = page.locator(".btn-icon").first
    expect(btn).to_be_visible()
    btn.click()
    page.wait_for_timeout(500)


@pytest.mark.ui
def test_upload_zone_visible(page: Page):
    page.goto(BASE_URL)
    page.wait_for_load_state("networkidle", timeout=15000)
    expect(page.locator("#uploadZone")).to_be_visible()
