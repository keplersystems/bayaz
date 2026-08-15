"""Response models.

Two shapes per resource: a summary carrying what a listing renders, and a detail carrying
the whole thing. Listings never return bodies, because a page of twenty ghazals with their
text in three scripts is an order of magnitude more bytes than the page needs.
"""

from pydantic import BaseModel, Field


class Page[T](BaseModel):
    """A slice of a listing. `total` is the count matching the filters, not the page size."""

    items: list[T]
    total: int
    limit: int
    offset: int


class SiteSummary(BaseModel):
    site: str
    works: int
    entries: int
    entities: int


class WorkTypeSummary(BaseModel):
    work_type: str
    works: int


class EntitySummary(BaseModel):
    site: str
    slug: str
    entity_type: str
    name: str | None
    name_hindi: str | None
    name_urdu: str | None
    name_translit: str | None
    born: str | None
    died: str | None


class EntityDetail(EntitySummary):
    description: str | None
    works: int


class WorkSummary(BaseModel):
    site: str
    slug: str
    work_type: str
    title: str | None
    title_translit: str | None
    title_hindi: str | None
    title_urdu: str | None
    author_name: str | None
    author_slug: str | None = Field(
        default=None, description="`entities.slug` of the author, when the poet page was captured"
    )


class WorkDetail(WorkSummary):
    body: str | None
    body_hindi: str | None
    body_urdu: str | None
    explanation: str | None = Field(default=None, description="the site's own prose gloss, kept out of the verse")
    translation: str | None = Field(default=None, description="the site's English rendering, kept out of the verse")
    source: str | None
    tags: list[str]
    has_words: bool = Field(description="whether word-level positions exist, so a reader can offer word lookup")


class Word(BaseModel):
    """One word occurrence in reading order.

    `code` is the source's own token, returned as it was captured. Rekhta's poetry codes
    resolve through `/entries/lookup`; the codes on hindwi and sufinama works, and on the
    prose recovered from rekhta.org's pages, use other encodings and resolve to nothing. A
    client cannot tell which from the code alone, so treat a 404 from lookup as normal.
    """

    line: int
    ord: int
    word: str
    code: str | None


class WorkWords(BaseModel):
    lang: str
    lines: list[list[Word]]


class Sense(BaseModel):
    lang: str
    pos: str | None
    definition: str


class Relation(BaseModel):
    rel_type: str
    target_text: str
    target_meaning: str | None


class Sher(BaseModel):
    lines: str
    lines_alt: str | None
    poet: str | None


class EntrySummary(BaseModel):
    site: str
    slug: str
    headword: str | None
    headword_hindi: str | None
    headword_urdu: str | None


class EntryGloss(EntrySummary):
    """What a reader needs when they tap a word: the headword and what it means.

    A summary alone is useless at the point of use, because the three headword scripts are
    three spellings of the word already on the page. The senses are the answer.
    """

    senses: list[Sense]


class EntryDetail(EntrySummary):
    vazn: str | None
    trivia: str | None
    audio_url: str | None
    video_url: str | None
    senses: list[Sense]
    examples: list[str]
    relations: list[Relation]
    shers: list[Sher]


class TagSummary(BaseModel):
    tag: str
    works: int


class SearchHit(BaseModel):
    site: str
    slug: str
    kind: str
    title: str | None
    snippet: str


class Health(BaseModel):
    status: str
    works: int
