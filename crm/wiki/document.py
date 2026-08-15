"""Small compatibility extension for Wiki's live-document merge path."""


class WikiDocumentIntegration:
	def check_permission(self, permtype="read", permlevel=None):
		"""Stamp a new document's space before Wiki evaluates create access.

		The pinned Wiki merge code sets ``parent_wiki_document`` before insert but
		does not set ``wiki_space`` until validation, which runs after Frappe's
		permission check. Resolving only from an existing parent keeps Wiki's
		native space-level permission hook authoritative.
		"""
		if permtype == "create" and self.is_new() and not self.get("wiki_space"):
			parent = self.get("parent_wiki_document")
			if parent:
				import frappe

				self.wiki_space = frappe.db.get_value("Wiki Document", parent, "wiki_space")

		return super().check_permission(permtype, permlevel)
