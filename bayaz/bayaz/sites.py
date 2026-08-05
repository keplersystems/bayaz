"""The sites and how their sitemaps map to page kinds.

Two templates exist. rekhtadictionary.com is its own dictionary application; hindwi.org and
sufinama.org share the Rekhta platform layout, with identical sitemap families, so one kind
map describes them both. Ebook sitemaps are excluded: the reader serves scanned page images,
out of scope for now.

`kinds` maps a sitemap's basename, digits stripped, to the kind its pages are recorded
under. A sitemap whose basename is in neither `kinds` nor `excluded` is a change on the
site's side and is logged as such rather than silently skipped.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Site:
    name: str
    sitemap_index: str
    hosts: tuple[str, ...]
    kinds: dict[str, str]
    excluded: tuple[str, ...] = ()
    # Whether content links found on captured pages are recorded as discovered pages.
    # Only meaningful where a URL's first path segment identifies its kind, which holds on
    # the platform sites and not on rekhtadictionary, where words live at the root.
    discover_links: bool = False
    # Kinds whose pages page their listings through /PartialWordLoading fragments.
    paginated: frozenset[str] = field(default_factory=frozenset)
    # Kinds whose listings page through /CollectionLoading fragments and whose items are the
    # content itself rather than links to it. Their first page holds only 50 of them, and the
    # rest exist nowhere else, so the fragments have to be captured to hold the archive.
    gathered: frozenset[str] = field(default_factory=frozenset)


REKHTA_DICTIONARY = Site(
    name="rekhtadictionary",
    sitemap_index="https://rekhtadictionary.com/sitemap.xml",
    hosts=("rekhtadictionary.com", "www.rekhtadictionary.com"),
    kinds={
        "Words": "word",
        "Synonym": "synonym",
        "Antonym": "antonym",
        "CompoundWords": "compound",
        "Idioms": "idiom",
        "Proverbs": "proverb",
        "WordFamily": "word-family",
        "Tags": "tag",
        "Blog": "blog",
        "Static": "static",
    },
    paginated=frozenset({"word", "synonym", "antonym", "compound", "idiom", "proverb", "word-family", "tag"}),
)

_PLATFORM_KINDS = {
    "Content": "work",
    "Dictionary": "dict",
    "EntityDetail": "entity",
    "EntityType": "entity-type",
    "ContentType": "work-type",
    "Collection": "collection",
    "Tag": "tag",
    "Emagazines": "emagazine",
    "Static": "static",
}

_EBOOKS = ("EBookCategory", "EBookContributor", "EBookDetail", "EBookSubcategory")

HINDWI = Site(
    name="hindwi",
    sitemap_index="https://hindwi.org/sitemap.xml",
    hosts=("hindwi.org", "www.hindwi.org"),
    kinds=_PLATFORM_KINDS,
    excluded=_EBOOKS,
    discover_links=True,
    gathered=frozenset({"tag"}),
)

SUFINAMA = Site(
    name="sufinama",
    sitemap_index="https://www.sufinama.org/sitemap.xml",
    hosts=("sufinama.org", "www.sufinama.org"),
    kinds=_PLATFORM_KINDS,
    excluded=_EBOOKS,
    discover_links=True,
    gathered=frozenset({"tag"}),
)

# rekhta.org is reached entirely through its mobile API, so it has no sitemap index and no
# kind map: the corpus is discovered from the API itself, seeded by the content-type and
# poet lists. See bayaz/rekhta.py.
REKHTA = Site(
    name="rekhta",
    sitemap_index="",
    hosts=("app-rekhta.rekhta.org",),
    kinds={},
)

SITES = {site.name: site for site in (REKHTA_DICTIONARY, HINDWI, SUFINAMA, REKHTA)}
