import logging
import os
import subprocess
from distutils.dir_util import remove_tree
from glob import glob
from os import path
from posixpath import dirname
from typing import Dict, List, Optional, Set
from urllib.parse import parse_qs, urlparse

from steam import webapi

from nfcli import STEAM_API_KEY, STEAM_USERNAME

STEAM_APP_ID = 887570
WORKSHOP_DIR = "~/.steam/steamapps/workshop/content/{}/{}"


def get_local_path(workshop_id: int) -> str:
    return path.expanduser(WORKSHOP_DIR.format(STEAM_APP_ID, workshop_id))


def get_files(directory: str) -> List[str]:
    return glob(path.join(directory, "*.fleet")) + glob(path.join(directory, "*.ship"))


def get_workshop_files(workshop_id: int) -> List[str]:
    """Get cached copy of workshop files, or download on the fly."""
    workshop_path = get_local_path(workshop_id)
    files = get_files(workshop_path)
    if files:
        return files
    workshop_ids = find_all()
    if workshop_id not in workshop_ids:
        logging.warning(f"Workshop item {workshop_id} is not a fleet or ship entry!")
        return []
    logging.info(f"Downloading workshop item {workshop_id}.")
    download_bulk([workshop_id])
    return get_files(workshop_path)


def download_bulk(workshop_ids: List[int], timeout: Optional[int] = 30):
    steam_cmd = ["steamcmd", "+login", STEAM_USERNAME]
    steam_cmd += ["+workshop_download_item {} {}".format(STEAM_APP_ID, workshop_id) for workshop_id in workshop_ids]
    steam_cmd.append("+quit")
    subprocess.run(steam_cmd, timeout=timeout)


def cache_workshop_files():
    workshop_items = find_all()
    invalidate_cache(workshop_items)
    workshop_ids = set(workshop_items.keys())
    existing_ids = find_existing()
    missing_ids = workshop_ids.difference(existing_ids)
    if missing_ids:
        download_bulk(missing_ids, 3600)


def invalidate_cache(workshop_items: Dict[str, Dict]) -> None:
    for workshop_id, workshop_item in workshop_items.items():
        workshop_path = get_local_path(workshop_id)
        if not os.path.exists(workshop_path):
            continue
        mtime = os.path.getmtime(workshop_path)
        if mtime < workshop_item["time_updated"]:
            logging.info(f"Invalidating workshop item {workshop_id}.")
            remove_tree(workshop_path)


def is_valid(tags: List[str]) -> bool:
    return any([tag["tag"].lower() in ["fleet", "ship template"] for tag in tags])


def find_all() -> Dict:
    cursor = "*"
    all_items = {}
    while cursor:
        params = {
            "appid": STEAM_APP_ID,
            "cursor": cursor,
            "return_tags": True,
            "key": STEAM_API_KEY,
            "numperpage": 100,
            "query_type": 21,
        }
        results = webapi.get("IPublishedFileService", "QueryFiles", params=params)["response"]
        if "publishedfiledetails" not in results:
            break
        cursor = results["next_cursor"]
        items = results["publishedfiledetails"]
        add_items(all_items, items)
    total = results["total"]
    valid = len(all_items)
    logging.info(f"Found {total} workshop files with {valid} being valid...")
    return all_items


def add_items(all_items: Dict[int, Dict], items: List[Dict]) -> None:
    valid_items = [item for item in items if is_valid(item["tags"])]
    for valid_item in valid_items:
        item_id = int(valid_item["publishedfileid"])
        all_items[item_id] = valid_item


def find_existing() -> Set[int]:
    local_path = dirname(get_local_path(0))
    return set([int(x) for x in os.listdir(local_path)])


def get_workshop_id(link: str) -> int:
    url = urlparse(link)
    if url.hostname != "steamcommunity.com" or url.path != "/sharedfiles/filedetails/":
        return 0
    params = parse_qs(url.query)
    if "id" not in params:
        return 0
    return int(params["id"][0])
