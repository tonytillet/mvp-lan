import asyncio
import httpx
from app.config import settings
from urllib.parse import quote

BASE_URL = f"https://{settings.riot_region}.api.riotgames.com"

def _headers():
    return {"X-Riot-Token": settings.riot_api_key}


async def _riot_get(url: str, *, params: dict | None = None, timeout: float = 15.0):
    delays = [1, 2, 4]
    last_exc: Exception | None = None

    for attempt in range(len(delays) + 1):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                r = await client.get(url, params=params, headers=_headers())

            if r.status_code == 429 and attempt < len(delays):
                await asyncio.sleep(delays[attempt])
                continue

            r.raise_for_status()
            return r
        except httpx.RequestError as e:
            last_exc = e
            if attempt < len(delays):
                await asyncio.sleep(delays[attempt])
                continue
            raise
        except httpx.HTTPStatusError as e:
            last_exc = e
            status = e.response.status_code
            if status >= 500 and attempt < len(delays):
                await asyncio.sleep(delays[attempt])
                continue
            raise

    if last_exc:
        raise last_exc
    raise RuntimeError("Riot request failed")

async def get_account_by_riot_id(game_name: str, tag_line: str):
    # account-v1 uses regional routing: europe / americas / asia
    safe_game_name = quote(game_name, safe="")
    safe_tag_line = quote(tag_line, safe="")
    url = f"{BASE_URL}/riot/account/v1/accounts/by-riot-id/{safe_game_name}/{safe_tag_line}"

    r = await _riot_get(url)
    return r.json()


async def get_match_ids_by_puuid(puuid: str, *, start: int = 0, count: int = 10, queue_id: int | None = None):
    url = f"{BASE_URL}/lol/match/v5/matches/by-puuid/{puuid}/ids"
    params: dict = {"start": start, "count": count}
    if queue_id is not None:
        params["queue"] = queue_id

    r = await _riot_get(url, params=params)
    data = r.json()
    return data if isinstance(data, list) else []

async def get_last_match_id(puuid: str):
    # Chercher en priorité Flex (440) puis Clash (700)
    for queue_id in [440, 700]:
        ids = await get_match_ids_by_puuid(puuid, start=0, count=1, queue_id=queue_id)
        if ids:
            return ids[0]
    return None

async def get_match_details(match_id: str):
    url = f"{BASE_URL}/lol/match/v5/matches/{match_id}"

    r = await _riot_get(url)
    return r.json()


async def find_common_match_id(puuids: list[str], *, queue_id: int | None = None, max_count: int = 50):
    if len(puuids) < 2:
        raise ValueError("Need at least 2 puuids")

    counts = [10, 20, 30, 50]
    counts = [c for c in counts if c <= max_count]
    if not counts:
        counts = [max_count]

    for c in counts:
        match_lists = await asyncio.gather(
            *[get_match_ids_by_puuid(p, count=c, queue_id=queue_id) for p in puuids]
        )
        sets = [set(lst) for lst in match_lists if lst]
        if len(sets) != len(puuids):
            continue

        common = set.intersection(*sets)
        if common:
            for mid in match_lists[0]:
                if mid in common:
                    return mid

    return None
