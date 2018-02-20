from typing import Any, Dict

import aiohttp
import json


class TableTransport:
    def __init__(self, ip):
        self.ip = ip

    async def post(
            self,
            endpoint: str,
            data: Dict[str, Any] = None,
            timeout: float = 5):
        return await post(self.ip, endpoint, data, timeout)


async def post(
        ip: str,
        endpoint: str,
        data: Dict[str, Any] = None,
        timeout: float = 5):
    data = data or {}
    try:
        url = "http://{ip}/sisbot/{endpoint}".format(ip=ip,
                                                     endpoint=endpoint)

        json_data = {
            "data": data,
        }

        form_data = {"data": json.dumps(json_data)}

        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=form_data,
                                    timeout=timeout) as r:
                r = await r.json()
                if r["err"]:
                    raise Exception(r["error"])

                return r["resp"]
    except:
        raise
