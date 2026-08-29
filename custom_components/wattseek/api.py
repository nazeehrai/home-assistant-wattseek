from __future__ import annotations

import asyncio
import hashlib
from typing import Any

from aiohttp import ClientSession, ClientResponseError

from .const import BASE_URL, API_PREFIX


class WattSeekApiError(Exception):
    pass


class WattSeekAuthError(WattSeekApiError):
    pass


class WattSeekApi:
    def __init__(self, session: ClientSession, username: str, password: str) -> None:
        self._session = session
        self.username = username.strip()
        self.password = password
        self.token: str | None = None
        self.user: dict[str, Any] | None = None
        self.plant: dict[str, Any] | None = None
        self.device: dict[str, Any] | None = None

    async def login(self) -> None:
        password_md5 = hashlib.md5(self.password.encode("utf-8")).hexdigest()
        payload = {"username": self.username, "password": password_md5}
        async with self._session.post(
            f"{BASE_URL}/apis/account/login/by/password",
            json=payload,
            timeout=20,
        ) as resp:
            data = await resp.json(content_type=None)

        if resp.status != 200 or data.get("status") not in (0, None):
            raise WattSeekAuthError(data.get("message") or "WattSeek login failed")

        token = (data.get("data") or {}).get("token")
        if not token:
            raise WattSeekAuthError("WattSeek login returned no token")
        self.token = token

        # The web UI calls /apis/account/user immediately after login.
        self.user = await self.request(
            "GET",
            "/apis/account/user",
            params={"url": "/pages/web/home/index"},
            prefix=False,
            retry_auth=False,
        )

    def _headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "x-auth-token": self.token or "",
            "x-org-id": "",
            "x-locale": "en",
        }

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
        prefix: bool = True,
        retry_auth: bool = True,
    ) -> Any:
        if not self.token:
            await self.login()

        url = f"{BASE_URL}{API_PREFIX if prefix else ''}{path}"
        cookies = {"x-auth-token": self.token or ""}

        async with self._session.request(
            method,
            url,
            headers=self._headers(),
            cookies=cookies,
            params=params,
            json=json_data,
            timeout=25,
        ) as resp:
            data = await resp.json(content_type=None)

        unauthorized = (
            resp.status == 401
            or data.get("status") in (401, "010000")
            or data.get("code") == "010000"
        )
        if unauthorized and retry_auth:
            self.token = None
            await self.login()
            return await self.request(
                method,
                path,
                params=params,
                json_data=json_data,
                prefix=prefix,
                retry_auth=False,
            )
        if unauthorized:
            raise WattSeekAuthError(data.get("message") or data.get("msg") or "Unauthorized")

        if resp.status >= 400:
            raise WattSeekApiError(f"HTTP {resp.status}: {data}")

        # Account endpoints use {status,httpStatus,data}; sysApiCommon uses {code,msg,data}.
        if prefix and data.get("code") not in (None, "000200"):
            raise WattSeekApiError(data.get("msg") or str(data))
        if not prefix and data.get("status") not in (None, 0):
            raise WattSeekApiError(data.get("message") or str(data))

        return data.get("data", data)

    async def discover(self) -> None:
        plants = await self.request(
            "GET", "/plant/page", params={"current": 1, "pageSize": 50}
        )
        plant_list = (plants or {}).get("data", [])
        if not plant_list:
            raise WattSeekApiError("No WattSeek plants found")
        self.plant = plant_list[0]

        devices = await self.request(
            "GET",
            "/device/page",
            params={
                "current": 1,
                "pageSize": 50,
                "plantId": self.plant["plantId"],
            },
        )
        device_list = (devices or {}).get("data", [])
        inverter = next((d for d in device_list if d.get("deviceType") == "INVERTER"), None)
        if not inverter:
            raise WattSeekApiError("No inverter found in WattSeek account")
        self.device = inverter

    @property
    def device_id(self) -> str:
        if not self.device:
            raise WattSeekApiError("Device not discovered")
        return str(self.device["deviceId"])

    async def get_flow(self) -> dict[str, Any]:
        return await self.request("GET", f"/statistic/realtime/device/{self.device_id}/flow")

    async def get_detail(self) -> dict[str, Any]:
        return await self.request(
            "GET",
            f"/device/{self.device_id}/detailInfo",
            params={"barType": "REALTIME_INFO,BASE_INFO"},
        )

    async def get_protocol(self) -> dict[str, Any]:
        return await self.request("GET", f"/cmd/protocol/{self.device_id}")

    async def get_command_values(self) -> list[dict[str, Any]]:
        return await self.request("GET", f"/device/cmd/value/{self.device_id}")

    async def send_command(self, group_id: str, cmd_id: str, value: Any) -> None:
        # Matches the WattSeek web UI's GROUP/WRITE request body.
        payload = {
            "cmdGroupId": str(group_id),
            "operationType": "GROUP",
            "functionType": "WRITE",
            "deviceId": self.device_id,
            "cmdList": [{"cmdId": str(cmd_id), "cmdValue": value}],
        }
        result = await self.request("POST", "/device/command/send", json_data=payload)

        execute_id = None
        if isinstance(result, dict):
            execute_id = result.get("executeId") or result.get("id")
        elif isinstance(result, str):
            execute_id = result

        if execute_id:
            await self._wait_for_execution(str(execute_id))

    async def _wait_for_execution(self, execute_id: str) -> None:
        # The WattSeek UI polls every 2 seconds, up to 15 times.
        for _ in range(15):
            rec = await self.request("GET", f"/device/cmd/execute/record/{execute_id}")
            status = (rec or {}).get("executeStatus")
            if status == "SUCCESS":
                return
            if status and status != "CMD_SEND_SUCCESS":
                raise WattSeekApiError(f"Command failed: {status}")
            await asyncio.sleep(2)
        raise WattSeekApiError("Command execution timed out")
