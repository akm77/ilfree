"""
API wrapper for Outline VPN
"""
import logging
from dataclasses import dataclass
from typing import Optional

import aiohttp
from aiohttp import ClientSession
from aiohttp.typedefs import StrOrURL


@dataclass(frozen=True)
class OutlineKey:
    """
    Describes a key in the Outline server
    """

    key_id: int
    name: str
    password: str
    port: int
    method: str
    access_url: str
    used_bytes: int


class OutlineVPNException(BaseException):
    pass


class OutlineVPN:
    """
    An Outline VPN connection
    """

    def __init__(self, api_url: Optional[StrOrURL] = None,
                 session: Optional[ClientSession] = None,
                 logger: Optional[logging.Logger] = None, ):
        self.__session = session or ClientSession()
        self.__api_url = api_url
        self.__keys_url = f"{api_url}/access-keys/"
        self.__metrics_url = f"{api_url}/metrics/transfer"
        self.__logger = logger or logging.getLogger(self.__class__.__module__)

    @property
    def session(self):
        return self.__session

    @session.setter
    def session(self, session: ClientSession):
        self.__session = session

    @property
    def api_url(self) -> StrOrURL:
        return self.__api_url

    @api_url.setter
    def api_url(self, api_url: StrOrURL):
        self.__keys_url = f"{api_url}/access-keys/"
        self.__metrics_url = f"{api_url}/metrics/transfer"
        self.__api_url = api_url

    async def get_keys(self):
        """Get all keys in the outline server"""
        server_keys = None
        metrics = None

        async with self.session.get(self.__keys_url, verify_ssl=False) as response:
            if response.status == 200:
                try:
                    server_keys = await response.json(encoding='utf-8')
                except aiohttp.ClientError as err:
                    self.__logger.error("Error while fetching keys: %r.", err)

        if server_keys and "accessKeys" in server_keys:
            metrics = await self.get_transferred_data()

        if not server_keys or not metrics:
            raise Exception("Unable to retrieve keys")
        result = []
        for key in server_keys["accessKeys"]:
            result.append(
                OutlineKey(
                    key_id=int(key.get("id")),
                    name=key.get("name"),
                    password=key.get("password"),
                    port=key.get("port"),
                    method=key.get("method"),
                    access_url=key.get("accessUrl"),
                    used_bytes=metrics.get("bytesTransferredByUserId").get(key.get("id")) or 0,
                )
            )
        return result

    async def create_key(self) -> OutlineKey:
        """Create a new key"""
        key = None
        async with self.session.post(self.__keys_url, verify_ssl=False) as response:
            if response.status == 201:
                try:
                    key = await response.json(encoding='utf-8')
                except aiohttp.ClientError as err:
                    self.__logger.error("Error while creating keys: %r.", err)
        if key:
            return OutlineKey(
                key_id=int(key.get("id")),
                name=key.get("name"),
                password=key.get("password"),
                port=key.get("port"),
                method=key.get("method"),
                access_url=key.get("accessUrl"),
                used_bytes=0,
            )

        raise Exception("Unable to create key")

    async def delete_key(self, key_id: int) -> bool:
        """Delete a key"""
        async with self.session.delete(f"{self.__keys_url}/{key_id}", verify_ssl=False) as response:
            return response.status == 204

    async def rename_key(self, key_id: int, new_name: str):
        """Rename a key"""
        data = {"name": new_name}
        async with self.session.put(f"{self.__keys_url}/{key_id}/name", json=data, verify_ssl=False) as response:
            return response.status == 204

    async def add_data_limit(self, key_id: int, limit_bytes: int) -> bool:
        """Set data limit for a key (in bytes)"""
        data = {"limit": {"bytes": limit_bytes}}
        async with self.session.put(f"self.__keys_url/{key_id}/data-limit", json=data, verify_ssl=False) as response:
            return response.status == 204

    async def delete_data_limit(self, key_id: int) -> bool:
        """Removes data limit for a key"""
        async with self.session.delete(f"self.__keys_url/{key_id}/data-limit", verify_ssl=False) as response:
            return response.status == 204

    async def get_transferred_data(self):
        """Gets how much data all keys have used"""
        metrics = None
        async with self.session.get(self.__metrics_url, verify_ssl=False) as response:
            if response.status == 200:
                try:
                    metrics = await response.json(encoding='utf-8')
                except aiohttp.ClientError as err:
                    self.__logger.error("Error while fetching metrics: %r.", err)

        if not metrics:
            raise Exception("Unable to retrieve keys")
        return metrics
