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
	"crm": os.environ.get("CRM_COMMIT", "4ccd8dfc166c2e7203aba5aca57b1545700c966b"),
	"wiki": "2e4e4f215368387c08553c3c59723c7a2e1bf306",
}
WIKI_CR_API = "/api/method/wiki.frappe_wiki.doctype.wiki_change_request.wiki_change_request."


def new_opener():
	return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))


guest_opener = new_opener()


def request(
	path: str,
	*,
	data: dict | None = None,
	method: str | None = None,
	opener=None,
	headers: dict | None = None,
):
	body = None
	request_headers = {"Host": SITE, **(headers or {})}
	if data is not None:
		body = json.dumps(data).encode()
		request_headers["Content-Type"] = "application/json"
	response = (opener or guest_opener).open(
		urllib.request.Request(f"{BASE_URL}{path}", data=body, headers=request_headers, method=method),
		timeout=30,
	)
	return response.status, response.headers, response.read().decode(errors="replace")


def request_status(*args, **kwargs):
	try:
		return request(*args, **kwargs)
	except urllib.error.HTTPError as error:
		return error.code, error.headers, error.read().decode(errors="replace")


def login(user: str, password: str):
	opener = new_opener()
	status, _, body = request(
		"/api/method/login",
		data={"usr": user, "pwd": password},
		method="POST",
		opener=opener,
	)
	assert status == 200, body
	_, _, desk = request("/app", opener=opener)
	csrf_match = re.search(r'frappe\.csrf_token\s*=\s*"([^"]+)"', desk)
	assert csrf_match, "authenticated desk response did not expose a CSRF token"
	opener.addheaders = [("X-Frappe-CSRF-Token", csrf_match.group(1))]
	return opener


def wiki_cr_call(opener, method: str, data: dict):
	status, _, body = request(WIKI_CR_API + method, data=data, method="POST", opener=opener)
	assert status == 200, body
	return json.loads(body).get("message")


def wiki_cr_status(opener, method: str, data: dict):
	return request_status(WIKI_CR_API + method, data=data, method="POST", opener=opener)


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
		actual = subprocess.check_output(["git", "-C", f"apps/{app}", "rev-parse", "HEAD"], text=True).strip()
		assert actual == expected, f"{app}: expected {expected}, got {actual}"


def assert_apps():
	output = subprocess.check_output(["bench", "--site", SITE, "list-apps", "--format", "json"], text=True)
	installed = json.loads(output)
	if isinstance(installed, dict):
		app_rows = [item for site_apps in installed.values() for item in site_apps]
	else:
		app_rows = installed
	names = {item["app_name"] if isinstance(item, dict) else item for item in app_rows}
	assert {"frappe", "crm", "wiki"}.issubset(names), installed


def assert_page_and_assets(path: str, asset_prefix: str, opener):
	status, _, body = request(path, opener=opener)
	assert status == 200, f"{path}: HTTP {status}"
	matches = re.findall(r"""(?:src|href)=["']([^"']+)""", body)
	assets = [asset for asset in matches if asset.startswith(asset_prefix)]
	assert assets, f"{path}: no {asset_prefix} asset reference"
	asset_status, _, _ = request(assets[0], opener=opener)
	assert asset_status == 200, f"{assets[0]}: HTTP {asset_status}"


def ensure_user(admin, email: str, role: str, password: str):
	encoded = urllib.parse.quote(email, safe="")
	status, _, _ = request_status(f"/api/resource/User/{encoded}", opener=admin)
	if status == 404:
		status, _, body = request(
			"/api/resource/User",
			data={
				"email": email,
				"first_name": "Wiki compatibility",
				"enabled": 1,
				"send_welcome_email": 0,
				"roles": [{"role": role}, {"role": "Wiki User"}],
			},
			method="POST",
			opener=admin,
		)
		assert status == 200, body
	subprocess.check_call(
		[
			"bench",
			"--site",
			SITE,
			"execute",
			"frappe.utils.password.update_password",
			"--kwargs",
			json.dumps({"user": email, "pwd": password}),
		]
	)


def multipart_upload(opener, filename: str, content: bytes):
	boundary = "----adah-wiki-phase1"
	body = (
		(
			f"--{boundary}\r\n"
			f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
			"Content-Type: image/png\r\n\r\n"
		).encode()
		+ content
		+ f"\r\n--{boundary}--\r\n".encode()
	)
	upload_request = urllib.request.Request(
		f"{BASE_URL}/api/method/wiki.api.upload_wiki_asset",
		data=body,
		headers={"Host": SITE, "Content-Type": f"multipart/form-data; boundary={boundary}"},
		method="POST",
	)
	try:
		response = opener.open(upload_request, timeout=30)
		return response.status, response.read().decode(errors="replace")
	except urllib.error.HTTPError as error:
		return error.code, error.read().decode(errors="replace")


def assert_shared_session_permissions_and_security():
	admin = login("Administrator", ADMIN_PASSWORD)
	_, _, user_body = request("/api/method/frappe.auth.get_logged_user", opener=admin)
	assert json.loads(user_body)["message"] == "Administrator"
	assert_page_and_assets("/crm", "/assets/crm/", admin)
	assert_page_and_assets("/wiki-app", "/assets/wiki/", admin)
	assert request("/docs", opener=admin)[0] == 200

	query = urllib.parse.urlencode(
		{"fields": json.dumps(["name", "root_group", "route"]), "limit_page_length": 1}
	)
	_, _, spaces_body = request(f"/api/resource/Wiki%20Space?{query}", opener=admin)
	spaces = json.loads(spaces_body)["data"]
	assert spaces and spaces[0]["route"] == "docs", spaces
	space_name = spaces[0]["name"]
	_, _, space_body = request(
		f"/api/resource/Wiki%20Space/{urllib.parse.quote(space_name, safe='')}", opener=admin
	)
	space = json.loads(space_body)["data"]
	assert space["allow_contributions"] == 0
	assert {(row["role"], row["permission_level"]) for row in space["roles"]} == {
		("Sales User", "Read"),
		("Sales Manager", "Write"),
	}

	reader_email = "wiki-reader@example.com"
	manager_email = "wiki-manager@example.com"
	password = "WikiPhase1!234"
	ensure_user(admin, reader_email, "Sales User", password)
	ensure_user(admin, manager_email, "Sales Manager", password)
	reader = login(reader_email, password)
	manager = login(manager_email, password)

	reader_draft_status, _, _ = wiki_cr_status(
		reader, "get_or_create_draft_change_request", {"wiki_space": space_name}
	)
	assert reader_draft_status in (403, 417), reader_draft_status

	draft = wiki_cr_call(
		manager,
		"get_or_create_draft_change_request",
		{"wiki_space": space_name, "title": "Phase 1 compatibility changes"},
	)
	cr_name = draft["name"]
	tree = wiki_cr_call(manager, "get_cr_tree", {"name": cr_name})
	root_key = tree["root_group"]
	assert root_key, tree
	doc_key = wiki_cr_call(
		manager,
		"create_cr_page",
		{
			"name": cr_name,
			"parent_key": root_key,
			"title": "Phase 1 Compatibility Page",
			"content": "# Phase 1\nCreated by the compatibility smoke test.",
		},
	)
	arabic_key = wiki_cr_call(
		manager,
		"create_cr_page",
		{
			"name": cr_name,
			"parent_key": root_key,
			"title": "دليل المبيعات",
			"slug": "arabic-sales-guide",
			"content": "# دليل المبيعات\n\nمحتوى عربي آمن.",
		},
	)
	wiki_cr_call(
		manager,
		"update_cr_page",
		{
			"name": cr_name,
			"doc_key": doc_key,
			"fields": {"content": "# Phase 1\nEdited and rendered successfully."},
		},
	)

	for payload in (
		"<script>alert(1)</script>",
		'<img src=x onerror="alert(1)">',
		"[x](javascript:alert(1))",
		"<svg><script>alert(1)</script></svg>",
		"<script",
		'<iframe src="https://example.com"></iframe>',
	):
		status, _, body = wiki_cr_status(
			manager,
			"update_cr_page",
			{"name": cr_name, "doc_key": doc_key, "fields": {"content": payload}},
		)
		assert status in (400, 417), (payload, status, body)

	page = wiki_cr_call(manager, "get_cr_page", {"name": cr_name, "doc_key": doc_key})
	arabic_page = wiki_cr_call(manager, "get_cr_page", {"name": cr_name, "doc_key": arabic_key})
	wiki_cr_call(manager, "submit_change_request", {"name": cr_name})
	wiki_cr_call(manager, "approve_change_request", {"name": cr_name})
	wiki_cr_call(manager, "merge_change_request", {"name": cr_name})

	document_query = urllib.parse.urlencode(
		{"filters": json.dumps([["doc_key", "=", doc_key]]), "fields": json.dumps(["name", "content"])}
	)
	_, _, documents_body = request(f"/api/resource/Wiki%20Document?{document_query}", opener=reader)
	documents = json.loads(documents_body)["data"]
	assert len(documents) == 1 and "Edited and rendered successfully" in documents[0]["content"]
	name = urllib.parse.quote(documents[0]["name"], safe="")
	denied_status, _, _ = request_status(
		f"/api/resource/Wiki%20Document/{name}",
		data={"content": "reader must not write"},
		method="PUT",
		opener=reader,
	)
	assert denied_status in (403, 417), denied_status
	assert "Edited and rendered successfully" in request(f"/{page['route'].lstrip('/')}", opener=reader)[2]
	assert "محتوى عربي آمن" in request(f"/{arabic_page['route'].lstrip('/')}", opener=reader)[2]

	# A minimal valid PNG exercises Wiki's endpoint, CRM's override, private
	# storage, and Frappe's attachment permission chain.
	png = bytes.fromhex(
		"89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
		"0000000d49444154789c6360f8cfc0000004010100c9fe92ef0000000049454e44ae426082"
	)
	upload_status, upload_body = multipart_upload(manager, "pixel.png", png)
	assert upload_status == 200, upload_body
	file_url = json.loads(upload_body)["message"]["file_url"]
	assert file_url.startswith("/private/files/"), file_url
	assert request(file_url, opener=reader)[0] == 200
	assert request_status(file_url, opener=guest_opener)[0] in (401, 403), file_url

	svg_status, svg_body = multipart_upload(manager, "payload.svg", b'<svg onload="alert(1)"></svg>')
	assert svg_status in (400, 417), svg_body

	assert request_status("/docs", opener=guest_opener)[0] in (401, 403), "Guest could read /docs"


def main():
	wait_for_site()
	assert_source_pins()
	assert_apps()
	assert_shared_session_permissions_and_security()
	print(json.dumps({"result": "PASS", "pins": EXPECTED_PINS}, indent=2))


if __name__ == "__main__":
	try:
		main()
	except Exception as error:
		print(json.dumps({"result": "FAIL", "error": repr(error)}, indent=2))
		raise
