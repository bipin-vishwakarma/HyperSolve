import asyncio
import json
import os
from typing import Dict, List, Optional, Any
from playwright.async_api import Browser, BrowserContext

class CookieVault:
    """
    Cookie & Authentication Harvester.
    Harvests active session cookies, auth tokens, and credentials from
    the user's Chrome browser without requiring any paid/developer API keys.
    """

    TARGET_DOMAINS = {
        "chatgpt": ["https://chatgpt.com", "https://chat.openai.com"],
        "gemini": ["https://gemini.google.com", "https://google.com"],
        "claude": ["https://claude.ai"]
    }

    def __init__(self, browser: Optional[Browser] = None):
        self.browser = browser
        self._cached_cookies: Dict[str, List[Dict[str, Any]]] = {}

    async def harvest_all(self, browser: Optional[Browser] = None) -> Dict[str, List[Dict[str, Any]]]:
        """Harvests cookies for all supported AI providers across open contexts."""
        b = browser or self.browser
        if not b:
            return {}

        results: Dict[str, List[Dict[str, Any]]] = {k: [] for k in self.TARGET_DOMAINS}
        try:
            for ctx in b.contexts:
                for provider, urls in self.TARGET_DOMAINS.items():
                    try:
                        cookies = await ctx.cookies(urls)
                        if cookies:
                            results[provider].extend(cookies)
                    except Exception:
                        pass
        except Exception as e:
            print(f"[COOKIE VAULT] Error harvesting cookies: {e}")

        self._cached_cookies = results
        return results

    def get_cookie_header(self, provider: str) -> str:
        """Returns Cookie header string format: name=val; name2=val2."""
        cookies = self._cached_cookies.get(provider, [])
        return "; ".join(f"{c['name']}={c['value']}" for c in cookies if 'name' in c and 'value' in c)

    def has_session(self, provider: str) -> bool:
        """Checks if there are valid session cookies for provider."""
        cookies = self._cached_cookies.get(provider, [])
        if not cookies:
            return False

        if provider == "chatgpt":
            return any(
                c.get("name") in (
                    "__Secure-next-auth.session-token",
                    "_puid",
                    "cf_clearance",
                    "oai-did"
                )
                for c in cookies
            )
        elif provider == "gemini":
            return any(
                c.get("name") in ("__Secure-1PSID", "__Secure-1PSIDTS", "SID", "SSID")
                for c in cookies
            )
        elif provider == "claude":
            return any(
                c.get("name") in ("sessionKey", "cf_clearance")
                for c in cookies
            )
        return len(cookies) > 0

    def get_summary(self) -> Dict[str, bool]:
        """Returns status summary of available AI provider sessions."""
        return {
            provider: self.has_session(provider)
            for provider in self.TARGET_DOMAINS
        }
