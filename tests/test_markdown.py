"""Tests for safe Markdown rendering."""

import unittest

from forum.formatting import render_markdown


class MarkdownRenderingTests(unittest.TestCase):
    def test_headings(self):
        rendered = str(render_markdown("# Main heading\n\n## Subheading"))
        self.assertIn("<h1>Main heading</h1>", rendered)
        self.assertIn("<h2>Subheading</h2>", rendered)

    def test_lists(self):
        rendered = str(render_markdown("- first\n- second"))
        self.assertIn("<ul>", rendered)
        self.assertIn("<li>first</li>", rendered)
        self.assertIn("<li>second</li>", rendered)

    def test_links(self):
        rendered = str(render_markdown("[Example](https://example.com)"))
        self.assertIn('href="https://example.com"', rendered)
        self.assertIn('rel="noopener noreferrer"', rendered)

    def test_bold_and_italic_text(self):
        rendered = str(render_markdown("**bold** and *italic*"))
        self.assertIn("<strong>bold</strong>", rendered)
        self.assertIn("<em>italic</em>", rendered)

    def test_unsafe_html_is_removed(self):
        rendered = str(
            render_markdown(
                '<script>alert("unsafe")</script>'
                '<img src=x onerror="alert(1)">'
                '[bad link](javascript:alert(1))'
            )
        )
        self.assertNotIn("<script", rendered)
        self.assertNotIn("alert", rendered)
        self.assertNotIn("<img", rendered)
        self.assertNotIn("javascript:", rendered)


if __name__ == "__main__":
    unittest.main()
