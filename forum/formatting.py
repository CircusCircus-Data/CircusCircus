"""Safe formatting helpers for user-authored content."""

import markdown
import nh3
from markupsafe import Markup


ALLOWED_TAGS = {
    "a",
    "blockquote",
    "br",
    "code",
    "em",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hr",
    "li",
    "ol",
    "p",
    "pre",
    "strong",
    "ul",
}

ALLOWED_ATTRIBUTES = {
    "a": {"href", "title"},
}

ALLOWED_URL_SCHEMES = {"http", "https", "mailto"}


def render_markdown(content):
    """Convert Markdown to sanitized HTML safe for template rendering."""

    rendered_html = markdown.markdown(content or "", extensions=["sane_lists"])
    sanitized_html = nh3.clean(
        rendered_html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        clean_content_tags={"script", "style"},
        url_schemes=ALLOWED_URL_SCHEMES,
        link_rel="noopener noreferrer",
    )
    return Markup(sanitized_html)
