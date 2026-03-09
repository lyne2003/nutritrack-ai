# app/services/fatsecret/client.py
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests

@dataclass
class FatSecretConfig:
    client_id: str
    client_secret: str
    token_url: str
    api_base: str

class FatSecretClient:
    """
    OAuth2 (client_credentials) FatSecret Platform client with in-memory token caching.
    This backend acts as the proxy server (mobile never calls FatSecret directly).
    """
    def __init__(self, cfg: FatSecretConfig) -> None:
        self.cfg = cfg
        self._access_token: Optional[str] = None
        self._expires_at: float = 0.0  # unix time

    def _token_valid(self) -> bool:
        # refresh a bit early (30s) to avoid edge cases
        return self._access_token is not None and time.time() < (self._expires_at - 30)

    def _fetch_token(self) -> str:
        data = {
            "grant_type": "client_credentials",
            "scope": "basic",  # FatSecret commonly uses "basic". If your docs specify another scope, change it.
        }
        r = requests.post(
            self.cfg.token_url,
            data=data,
            auth=(self.cfg.client_id, self.cfg.client_secret),
            timeout=30,
        )
        r.raise_for_status()
        payload = r.json()

        token = payload.get("access_token")
        expires_in = payload.get("expires_in", 3600)

        if not token:
            raise RuntimeError(f"FatSecret token response missing access_token: {payload}")

        self._access_token = token
        self._expires_at = time.time() + float(expires_in)
        return token

    def _get_token(self) -> str:
        if self._token_valid():
            return self._access_token  # type: ignore[return-value]
        return self._fetch_token()

    def _request(self, method: str, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        token = self._get_token()
        url = self.cfg.api_base.rstrip("/") + "/" + path.lstrip("/")

        headers = {
            "Authorization": f"Bearer {token}",
        }

        r = requests.request(
            method=method,
            url=url,
            headers=headers,
            params=params,
            timeout=45,
        )
        r.raise_for_status()
        return r.json()

    # ---------- High-level helpers we’ll use in /generate ----------

    def recipes_search_v3(
        self,
        search_expression: str,
        max_results: int = 20,
        region: str = "United States",
        recipe_type: str = "main dish",
        include_images: bool = False,
        page_number: int = 0,
    ) -> Dict[str, Any]:
        """
        Maps to recipes.search (v3).
        """
        params = {
            "method": "recipes.search.v3",
            "search_expression": search_expression,
            "max_results": max_results,
            "page_number": page_number,
            "region": region,
            "recipe_type": recipe_type,
            "include_images": "true" if include_images else "false",
            "format": "json",
        }
        return self._request("GET", "/server.api", params=params)

    def recipe_get_v2(self, recipe_id: str) -> Dict[str, Any]:
        """
        Maps to recipe.get (v2).
        """
        params = {
            "method": "recipe.get.v2",
            "recipe_id": recipe_id,
            "format": "json",
        }
        return self._request("GET", "/server.api", params=params)
