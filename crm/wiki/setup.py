"""Idempotent configuration for the Adah Docs Wiki Space."""

from __future__ import annotations

ADAH_SPACE_ROUTE = "docs"
ADAH_SPACE_NAME = "Adah Docs"
SPACE_ROLES = (("Sales User", "Read"), ("Sales Manager", "Write"))


def wiki_is_installed() -> bool:
	import frappe

	return "wiki" in frappe.get_installed_apps()


def get_adah_space():
	import frappe

	name = frappe.db.get_value("Wiki Space", {"route": ADAH_SPACE_ROUTE}, "name")
	return frappe.get_doc("Wiki Space", name) if name else None


def configure_wiki() -> None:
	"""Apply the V1 private-space policy after Wiki installation/migration."""
	import frappe

	if not wiki_is_installed():
		return

	_audit_existing_content()
	space = get_adah_space()
	if not space:
		space = frappe.new_doc("Wiki Space")
		space.route = ADAH_SPACE_ROUTE

	space.space_name = ADAH_SPACE_NAME
	space.is_published = 1
	space.allow_contributions = 0
	space.set("roles", [])
	for role, permission_level in SPACE_ROLES:
		space.append("roles", {"role": role, "permission_level": permission_level})

	if space.is_new():
		space.insert(ignore_permissions=True)
	else:
		space.save(ignore_permissions=True)

	_configure_landing_page(space)
	_assign_wiki_user_role()
	frappe.clear_cache()


def _audit_existing_content() -> None:
	import frappe

	from crm.wiki.security import UnsafeWikiContentError, validate_markdown

	for page in frappe.get_all("Wiki Document", fields=["name", "content"]):
		try:
			validate_markdown(page.content)
		except UnsafeWikiContentError as error:
			frappe.throw(
				f"Wiki Document {page.name} violates the Adah Docs content policy: {error}",
				frappe.ValidationError,
			)


def _configure_landing_page(space) -> None:
	import frappe

	page_name = frappe.db.get_value(
		"Wiki Document",
		{"parent_wiki_document": space.root_group, "title": "Welcome to Frappe Wiki"},
		"name",
	)
	if not page_name:
		return
	page = frappe.get_doc("Wiki Document", page_name)
	if (page.content or "").strip() != "# Welcome to Frappe Wiki!":
		return
	page.title = "Welcome to Adah Docs"
	# Serve the initial leaf at the space root instead of requiring a redirect
	# through the generated welcome-page slug.
	page.route = ADAH_SPACE_ROUTE
	page.is_published = 1
	page.content = "# Welcome to Adah Docs\n\nInternal documentation for the Adah team."
	page.save(ignore_permissions=True)


def _assign_wiki_user_role() -> None:
	import frappe

	users = frappe.get_all(
		"Has Role",
		filters={
			"parenttype": "User",
			"role": ("in", ["Sales User", "Sales Manager"]),
		},
		pluck="parent",
	)
	for user_name in set(users):
		user = frappe.get_doc("User", user_name)
		if not any(row.role == "Wiki User" for row in user.roles):
			user.add_roles("Wiki User")


def after_app_install(app_name: str) -> None:
	if app_name == "wiki":
		configure_wiki()
