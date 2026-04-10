# -*- coding: utf-8 -*-
"""Salesforce 接続管理"""

from simple_salesforce import Salesforce, SalesforceAuthenticationFailed


class SalesforceConnector:
    """Salesforce org への接続を管理するクラス"""

    def __init__(self, username: str, password: str, security_token: str, domain: str = "login"):
        self._username = username
        self._password = password
        self._security_token = security_token
        self._domain = domain
        self._sf: Salesforce | None = None

    def connect(self) -> "SalesforceConnector":
        """パスワード認証で接続（チェーン可能）"""
        try:
            self._sf = Salesforce(
                username=self._username,
                password=self._password,
                security_token=self._security_token,
                domain=self._domain,
            )
            print(f"[接続OK] {self._username} ({self._domain})")
        except SalesforceAuthenticationFailed as e:
            raise ConnectionError(f"Salesforce 認証失敗: {e}") from e
        return self

    @classmethod
    def from_session(cls, session_id: str, instance_url: str, username: str = "") -> "SalesforceConnector":
        """SF CLI のアクセストークンで接続"""
        obj = cls.__new__(cls)
        obj._username = username
        obj._sf = Salesforce(session_id=session_id, instance_url=instance_url)
        return obj

    @property
    def sf(self) -> Salesforce:
        if self._sf is None:
            raise RuntimeError("connect() を先に呼んでください")
        return self._sf

    @property
    def instance_url(self) -> str:
        return self.sf.base_url.split("/services/")[0]
