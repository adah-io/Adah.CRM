#!/usr/bin/env python3
"""HTTP and source-pin smoke checks for the disposable Phase 1 site."""

from __future__ import annotations

import http.cookiejar
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


BASE_URL = os.environ.get("PHASE1_BASE_URL", "http://localhost:8000")
SITE = os.environ.get("PHASE1_SITE", "wiki-phase1.localhost")
ADMIN_PASSWORD = os.environ.get("PHASE1_ADMIN_PASSWORD", "admin")
EXPECTED_PINS = {
    "frappe": "ba36d03916ee05391bee0cf0f979ab97d552eede",
    "crm": "4ccd8dfc166c2e7203aba5aca57b1545700c966b",
    "wiki": "2e4e4f215368387c08553c3c59723c7a2e1bf306",
}


cookie_jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))


def request(path: str, *, data: dict | None = None, method: str | None = None):
    body = None
    headers = {"Host": SITE}
    if data is not None:
        body = json.dumps(data).encode()
        headers["Content-Type"] = "application/json"
    response = opener.open(
        urllib.request.Request(
            f"{BASE_URL}{path}", data=body, headers=headers, method=method
        ),
        timeout=30,
    )
    return response.status, response.headers, response.read().decode(errors="replace")


def wait_for_site():
    last_error = None
    for _ in range(90):
        try:
            status, _, body = request("/api/method/ping")
            if status == 200 and "pong" in body:
                return
        except (OSError, urllib.error.URLError) as error:
            last_error = error
        time.sleep(2)
    raise RuntimeError(f"site did not become ready: {last_error}")


def assert_source_pins():
    for app, expected in EXPECTED_PINS.items():
        actual = subprocess.check_output(
            ["git", "-C", f"apps/{app}", "rev-parse", "HEAD"], text=True
        ).strip()
        assert actual == expected, f"{app}: expected {expected}, got {actual}"


def assert_apps():
    output = subprocess.check_output(
        ["bench", "--site", SITE, "list-apps", "--format", "json"], text=True
    )
    installed = json.loads(output)
    names = {
        item["app_name"] if isinstance(item, dict) else item for item in installed
    }
    assert {"frappe", "crm", "wiki"}.issubset(names), installed


def assert_page_and_assets(path: str, asset_prefix: str):
    status, _, body = request(path)
    assert status == 200, f"{path}: HTTP {status}"
    matches = re.findall(r'''(?:src|href)=["']([^"']+)''', body)
    assets = [asset for asset in matches if asset.startswith(asset_prefix)]
    assert assets, f"{path}: no {asset_prefix} asset reference"
    asset_status, _, _ = request(assets[0])
    assert asset_status == 200, f"{assets[0]}: HTTP {asset_status}"


def assert_shared_session_and_wiki_crud():
    request(
        "/api/method/login",
        data={"usr": "Administrator", "pwd": ADMIN_PASSWORD},
        method="POST",
    )
    _, _, user_body = request("/api/method/frappe.auth.get_logged_user")
    assert json.loads(user_body)["message"] == "Administrator"

    query = urllib.parse.urlencode(
        {"fields": json.dumps(["name", "root_group", "route"]), "limit_page_length": 1}
    )
    _, _, spaces_body = request(f"/api/resource/Wiki Space?{query}")
    spaces = json.loads(spaces_body)["data"]
    assert spaces and spaces[0]["route"] == "docs", spaces

    title = "Phase 1 Compatibility Page"
    create_status, _, create_body = request(
        "/api/resource/Wiki Document",
        data={
            "title": title,
            "parent_wiki_document": spaces[0]["root_group"],
            "content": "# Phase 1\nCreated by the compatibility smoke test.",
            "is_published": 1,
        },
        method="POST",
    )
    assert create_status == 200, create_body
    created = json.loads(create_body)["data"]
    name = urllib.parse.quote(created["name"], safe="")

    update_status, _, update_body = request(
        f"/api/resource/Wiki Document/{name}",
        data={"content": "# Phase 1\nEdited and rendered successfully."},
        method="PUT",
    )
    assert update_status == 200, update_body
    _, _, read_body = request(f"/api/resource/Wiki Document/{name}")
    assert "Edited and rendered successfully" in read_body

    route = json.loads(read_body)["data"]["route"]
    rendered_status, _, rendered_body = request(f"/{route.lstrip('/')}")
    assert rendered_status == 200 and "Edited and rendered successfully" in rendered_body


def main():
    wait_for_site()
    assert_source_pins()
    assert_apps()
    assert_page_and_assets("/crm", "/assets/crm/")
    assert_page_and_assets("/wiki-app", "/assets/wiki/")
    status, _, _ = request("/docs")
    assert status == 200, f"/docs: HTTP {status}"
    assert_shared_session_and_wiki_crud()
    print(json.dumps({"result": "PASS", "pins": EXPECTED_PINS}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(json.dumps({"result": "FAIL", "error": repr(error)}, indent=2))
        raise
