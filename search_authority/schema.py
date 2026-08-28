"""JSON-LD schema generator for blog posts.

Generates BlogPosting + BreadcrumbList schemas following Google's structured
data guidelines. Only marks up visible, truthful content.
"""

from __future__ import annotations

import json
from datetime import date
from typing import Optional


def generate_blog_schema(
    headline: str,
    description: str,
    url: str,
    date_published: str,
    date_modified: Optional[str] = None,
    author_name: str = "County Group",
    author_url: Optional[str] = None,
    image_url: Optional[str] = None,
    image_width: Optional[int] = None,
    image_height: Optional[int] = None,
    publisher_name: str = "County Group",
    publisher_url: Optional[str] = None,
    publisher_logo: Optional[str] = None,
    word_count: Optional[int] = None,
    keywords: Optional[list[str]] = None,
) -> dict:
    """Generate BlogPosting JSON-LD schema.

    Only includes properties that have truthful, visible values.
    Never fabricates data.
    """
    schema = {
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "headline": headline[:110],  # Google recommends under 110 chars
        "description": description[:300],
        "url": url,
        "datePublished": date_published,
        "dateModified": date_modified or date_published,
        "author": {
            "@type": "Organization",
            "name": author_name,
        },
        "publisher": {
            "@type": "Organization",
            "name": publisher_name,
        },
        "mainEntityOfPage": {
            "@type": "WebPage",
            "@id": url,
        },
    }

    if author_url:
        schema["author"]["url"] = author_url
    if publisher_url:
        schema["publisher"]["url"] = publisher_url
    if publisher_logo:
        schema["publisher"]["logo"] = {
            "@type": "ImageObject",
            "url": publisher_logo,
        }

    if image_url:
        img = {"@type": "ImageObject", "url": image_url}
        if image_width:
            img["width"] = image_width
        if image_height:
            img["height"] = image_height
        schema["image"] = img

    if word_count:
        schema["wordCount"] = word_count

    if keywords:
        schema["keywords"] = keywords

    return schema


def generate_breadcrumb_schema(
    items: list[dict],
) -> dict:
    """Generate BreadcrumbList JSON-LD.

    items: list of {"name": "...", "url": "..."} in order from home to current page.
    """
    schema = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [],
    }

    for i, item in enumerate(items, 1):
        element = {
            "@type": "ListItem",
            "position": i,
            "name": item["name"],
        }
        if "url" in item:
            element["item"] = item["url"]
        schema["itemListElement"].append(element)

    return schema


def generate_organization_schema(
    name: str = "County Group",
    url: Optional[str] = None,
    logo: Optional[str] = None,
    description: Optional[str] = None,
    address_locality: Optional[str] = None,
    address_region: Optional[str] = None,
    address_country: str = "IN",
) -> dict:
    """Generate Organization JSON-LD for site-wide use."""
    schema = {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": name,
    }

    if url:
        schema["url"] = url
    if logo:
        schema["logo"] = logo
    if description:
        schema["description"] = description

    if address_locality:
        schema["address"] = {
            "@type": "PostalAddress",
            "addressLocality": address_locality,
            "addressRegion": address_region or "",
            "addressCountry": address_country,
        }

    return schema


def schemas_to_jsonld(*schemas: dict) -> str:
    """Combine multiple schemas into a single JSON-LD script tag."""
    if len(schemas) == 1:
        return json.dumps(schemas[0], indent=2, ensure_ascii=False)

    graph = {
        "@context": "https://schema.org",
        "@graph": list(schemas),
    }
    # Remove individual @context from graph items
    for s in graph["@graph"]:
        s.pop("@context", None)

    return json.dumps(graph, indent=2, ensure_ascii=False)


def validate_schema(schema: dict, visible_text: str) -> list[str]:
    """Basic schema validation against visible content.

    Returns list of warnings/errors.
    """
    warnings = []

    if "@type" not in schema:
        warnings.append("ERROR: Missing @type")

    schema_type = schema.get("@type", "")

    if schema_type in ("BlogPosting", "Article"):
        headline = schema.get("headline", "")
        if not headline:
            warnings.append("ERROR: Missing headline")
        elif headline.lower() not in visible_text.lower():
            warnings.append(f"WARNING: Headline '{headline[:50]}...' not found in visible content")

        if not schema.get("datePublished"):
            warnings.append("ERROR: Missing datePublished")

        if not schema.get("author"):
            warnings.append("WARNING: Missing author")

        if not schema.get("image"):
            warnings.append("WARNING: Missing image — recommended for BlogPosting")

    return warnings
