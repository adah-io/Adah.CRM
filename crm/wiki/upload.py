"""Whitelisted entry point for the protected Wiki asset uploader."""

import frappe


@frappe.whitelist()
def upload_wiki_asset():
	from crm.wiki.security import upload_wiki_asset as upload

	return upload()
