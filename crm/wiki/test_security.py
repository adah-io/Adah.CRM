import unittest

from crm.wiki.security import UnsafeWikiContentError, is_safe_asset_filename, validate_markdown


class TestWikiContentSecurity(unittest.TestCase):
	def assert_rejected(self, value):
		with self.assertRaises(UnsafeWikiContentError):
			validate_markdown(value)

	def test_rejects_executable_and_embedded_html(self):
		for payload in (
			"<script>alert(1)</script>",
			'<img src=x onerror="alert(1)">',
			'<a href="javascript:alert(1)">click</a>',
			"<svg><script>alert(1)</script></svg>",
			"<script",
			'<iframe src="https://example.com"></iframe>',
		):
			with self.subTest(payload=payload):
				self.assert_rejected(payload)

	def test_rejects_dangerous_markdown_urls(self):
		for payload in ("[x](javascript:alert(1))", "![x](data:image/svg+xml,<svg>)"):
			with self.subTest(payload=payload):
				self.assert_rejected(payload)

	def test_allows_markdown_arabic_and_code_examples(self):
		for payload in (
			"# دليل المبيعات\n\nمحتوى عربي آمن.",
			"`<script>alert(1)</script>`",
			"```html\n<img onerror=alert(1)>\n```",
			"[safe](https://example.com)",
		):
			with self.subTest(payload=payload):
				validate_markdown(payload)

	def test_asset_allowlist_excludes_active_content(self):
		for filename in ("diagram.svg", "page.html", "payload.js", "no-extension"):
			self.assertFalse(is_safe_asset_filename(filename))
		for filename in ("diagram.PNG", "guide.pdf", "demo.webm"):
			self.assertTrue(is_safe_asset_filename(filename))


if __name__ == "__main__":
	unittest.main()
