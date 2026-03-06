"""
services/crawler.py — Service d'extraction web via HTTPX + BeautifulSoup4.

Responsabilité : extraire du Markdown sémantiquement dense depuis n'importe quelle URL.
Filtre le bruit (nav, footer, scripts, publicités) pour minimiser la fenêtre de contexte LLM.

Alternative à Crawl4AI qui évite les dépendances problématiques (greenlet/playwright)
pour une meilleure compatibilité Python 3.13+.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Optional
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup, NavigableString
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from backend.core.config import get_settings

logger = logging.getLogger(__name__)


class CrawlerService:
    """Service crawler HTTPX + BeautifulSoup4 — Extraction de contenu web en Markdown propre.

    Configure le crawler pour exclure les balises parasites :
        - <nav>, <header>, <footer> (navigation)
        - <script>, <style>, <noscript> (code client)
        - <aside>, [role="complementary"] (sidebars)
        - .ad, .advertisement, .cookie-banner (publicités)

    Utilise Markdownify pour convertir le HTML nettoyé en Markdown.
    """

    _EXCLUDED_TAGS = [
        "nav", "header", "footer", "aside",
        "script", "style", "noscript", "iframe",
        "form", "button", "input", "select", "textarea",
        "svg", "canvas", "video", "audio", "embed", "object",
    ]

    _EXCLUDED_SELECTORS = [
        ".ad", ".ads", ".advertisement",
        ".cookie-banner", ".cookie-notice", ".gdpr-banner",
        ".social-share", ".social-media", ".share-buttons",
        ".comments", ".comment-section",
        ".related-posts", ".related-articles", ".recommended",
        ".newsletter", ".subscribe", ".signup",
        ".popup", ".modal", ".overlay",
        '[role="complementary"]', '[role="banner"]', '[role="contentinfo"]',
        "[aria-hidden='true']",
    ]

    _USER_AGENT = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    def __init__(self) -> None:
        self._settings = get_settings()
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Retourne ou crée le client HTTPX avec configuration."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                headers={"User-Agent": self._USER_AGENT},
                follow_redirects=True,
                timeout=httpx.Timeout(
                    connect=10.0,
                    read=self._settings.crawl4ai_timeout,
                    write=10.0,
                    pool=10.0,
                ),
                limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
            )
        return self._client

    async def close(self) -> None:
        """Ferme proprement le client HTTPX."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    def _clean_html(self, soup: BeautifulSoup) -> BeautifulSoup:
        """Nettoie le HTML en supprimant les éléments parasites."""
        # Supprimer les balises exclues
        for tag_name in self._EXCLUDED_TAGS:
            for tag in soup.find_all(tag_name):
                tag.decompose()

        # Supprimer les éléments par sélecteur CSS
        for selector in self._EXCLUDED_SELECTORS:
            try:
                for element in soup.select(selector):
                    element.decompose()
            except Exception:
                continue

        # Supprimer les éléments vides ou sans texte significatif
        for element in soup.find_all():
            if element.name not in ["br", "hr", "img"]:
                text = element.get_text(strip=True)
                if not text or len(text) < 3:
                    children_text = " ".join(
                        child.get_text(strip=True)
                        for child in element.find_all(string=True)
                        if isinstance(child, NavigableString)
                    )
                    if not children_text.strip():
                        element.decompose()

        return soup

    def _html_to_markdown(self, soup: BeautifulSoup, base_url: str = "") -> str:
        """Convertit le HTML nettoyé en Markdown simple."""
        lines: list[str] = []

        # Titre de la page
        title_tag = soup.find("title")
        if title_tag and title_tag.get_text(strip=True):
            lines.append(f"# {title_tag.get_text(strip=True)}")
            lines.append("")

        # Meta description
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            lines.append(f"> {meta_desc['content']}")
            lines.append("")

        # Contenu principal
        main_content = (
            soup.find("article")
            or soup.find("main")
            or soup.find("div", class_=re.compile(r"content|main|body", re.I))
            or soup.find("body")
            or soup
        )

        if not main_content:
            return "\n".join(lines)

        seen_texts: set[str] = set()

        for elem in main_content.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "ul", "ol", "li", "a", "strong", "em", "blockquote"]):
            text = elem.get_text(strip=True)
            if not text or len(text) < 10:
                continue

            # Éviter les doublons
            if text in seen_texts:
                continue
            seen_texts.add(text)

            if elem.name == "h1":
                lines.append(f"# {text}")
            elif elem.name == "h2":
                lines.append(f"## {text}")
            elif elem.name == "h3":
                lines.append(f"### {text}")
            elif elem.name == "h4":
                lines.append(f"#### {text}")
            elif elem.name in ["ul", "ol"]:
                continue
            elif elem.name == "li":
                lines.append(f"- {text}")
            elif elem.name == "blockquote":
                lines.append(f"> {text}")
            elif elem.name == "a":
                href = elem.get("href", "")
                if href and not href.startswith(("#", "javascript:", "mailto:")):
                    if not href.startswith(("http://", "https://")):
                        href = urljoin(base_url, href)
                    lines.append(f"[{text}]({href})")
                else:
                    lines.append(text)
            else:
                lines.append(text)

            lines.append("")

        result = "\n".join(lines)
        result = re.sub(r"\n{3,}", "\n\n", result)

        return result.strip()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError)),
        reraise=True,
    )
    async def extract_markdown(self, url: str) -> str:
        """Extrait le contenu principal d'une URL en Markdown dense.

        Args:
            url: URL cible à crawler.

        Returns:
            Markdown nettoyé du contenu principal (sans nav/footer/scripts).

        Raises:
            ValueError: si l'URL est invalide.
            RuntimeError: si le crawl échoue après 3 tentatives.
        """
        if not url or not url.startswith(("http://", "https://")):
            logger.error(f"URL invalide fournie au crawler : '{url}'")
            raise ValueError(f"URL invalide : '{url}'. Doit commencer par http:// ou https://")

        logger.info(f"🔍 Scouting started for URL: {url}")

        client = await self._get_client()

        try:
            response = await client.get(url)
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            logger.error(f"⏱️ Timeout pour {url}: {exc}")
            raise RuntimeError(f"Timeout dépassé pour l'URL '{url}'") from exc
        except httpx.HTTPStatusError as exc:
            logger.error(f"🚫 Erreur HTTP {exc.response.status_code} pour {url}")
            raise RuntimeError(f"Erreur HTTP {exc.response.status_code} pour '{url}'") from exc
        except httpx.RequestError as exc:
            logger.error(f"🚫 Erreur réseau pour {url}: {exc}")
            raise RuntimeError(f"Impossible de joindre l'URL '{url}': {exc}") from exc

        try:
            soup = BeautifulSoup(response.content, "html.parser", from_encoding=response.encoding)
        except Exception as exc:
            logger.error(f"❌ Erreur parsing HTML pour {url}: {exc}")
            raise RuntimeError(f"Échec du parsing HTML pour '{url}': {exc}") from exc

        cleaned_soup = self._clean_html(soup)
        markdown = self._html_to_markdown(cleaned_soup, base_url=url)

        if not markdown.strip():
            logger.warning(f"⚠️ Aucun contenu extrait de {url}. Page vide ou bloquée.")
            raise RuntimeError(f"Aucun contenu significatif extrait de '{url}'")

        char_count = len(markdown)
        word_count = len(markdown.split())
        logger.info(f"✅ Markdown extracted from {url}: {char_count} chars, ~{word_count} words")

        return markdown

    async def extract_with_metadata(self, url: str) -> dict[str, Optional[str]]:
        """Extrait le Markdown + métadonnées basiques (titre, description).

        Utilisé si on veut récupérer le <title> et <meta description> originaux
        avant de passer au LLM de synthèse.
        """
        markdown = await self.extract_markdown(url)

        return {
            "markdown": markdown,
            "url": url,
        }
