"""Security boundary for internal Wiki content and editor uploads.

Wiki intentionally renders raw HTML. Adah's internal documentation policy does
not need that feature, so CRM rejects raw HTML at persistence time instead of
trying to maintain a second HTML sanitizer. Markdown inside code spans/fences is
left untouched so documentation can still show HTML examples safely.
"""

from __future__ import annotations

import os
import re

SAFE_ASSET_EXTENSIONS = frozenset(
	{
		".gif",
		".jpeg",
		".jpg",
		".m4v",
		".mkv",
		".mov",
		".mp4",
		".ogg",
		".pdf",
		".png",
		".webm",
		".webp",
	}
)

_FENCE = re.compile(r"^[ \t]{0,3}(`{3,}|~{3,})")
_INLINE_CODE = re.compile(r"(`+)(.*?)\1")
_RAW_HTML = re.compile(
	r"<!--|<![A-Z]|<\?|<\s*/?\s*[A-Za-z][A-Za-z0-9:-]*(?:\s|/?>|$)",
	re.IGNORECASE,
)
_DANGEROUS_MARKDOWN_URL = re.compile(r"!?\[[^\]]*\]\(\s*<?\s*(?:javascript|vbscript|data)\s*:", re.IGNORECASE)


class UnsafeWikiContentError(ValueError):
	pass


def _content_outside_code(markdown: str) -> str:
	lines: list[str] = []
	fence_character = None
	fence_length = 0

	for line in (markdown or "").splitlines():
		match = _FENCE.match(line)
		if match:
			marker = match.group(1)
			if fence_character is None:
				fence_character = marker[0]
				fence_length = len(marker)
			elif marker[0] == fence_character and len(marker) >= fence_length:
				fence_character = None
				fence_length = 0
			lines.append("")
			continue

		if fence_character is not None:
			lines.append("")
			continue

		lines.append(_INLINE_CODE.sub("", line))

	return "\n".join(lines)


def validate_markdown(markdown: str | None) -> None:
	"""Reject active-content features that the pinned Wiki renderer would emit."""
	content = _content_outside_code(markdown or "")
	if _RAW_HTML.search(content):
		raise UnsafeWikiContentError("Raw HTML is disabled in Adah Docs.")
	if _DANGEROUS_MARKDOWN_URL.search(content):
		raise UnsafeWikiContentError("Unsafe URL schemes are disabled in Adah Docs.")


def is_safe_asset_filename(filename: str | None) -> bool:
	return os.path.splitext(filename or "")[1].lower() in SAFE_ASSET_EXTENSIONS


def validate_wiki_document(doc, method=None) -> None:
	"""Frappe doc-event adapter for Wiki Document persistence."""
	import frappe

	try:
		validate_markdown(doc.get("content"))
	except UnsafeWikiContentError as error:
		frappe.throw(str(error), frappe.ValidationError)


def upload_wiki_asset():
	"""Store editor assets privately and attach them to the protected Wiki Space."""
	import frappe
	from wiki.api import upload_wiki_asset as upstream_upload_wiki_asset
	from wiki.permissions import can_write_space

	from crm.wiki.setup import get_adah_space

	space = get_adah_space()
	if not space or not can_write_space(space.name):
		frappe.throw("You are not permitted to upload Adah Docs assets.", frappe.PermissionError)

	uploaded = next(iter(frappe.request.files.values()), None)
	if not uploaded or not is_safe_asset_filename(uploaded.filename):
		frappe.throw("This file type is not allowed in Adah Docs.", frappe.ValidationError)

	# Frappe's File permission check follows this attachment back to Wiki Space,
	# so readers can fetch it while Guest remains denied by native Wiki roles.
	frappe.form_dict.is_private = 1
	frappe.form_dict.private = 1
	frappe.form_dict.doctype = "Wiki Space"
	frappe.form_dict.docname = space.name
	return upstream_upload_wiki_asset()
