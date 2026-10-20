---
name: database-content-interpretation
description: Interpretation guidelines for data retrieved from the database. Use whenever data has been retrieved from the postgres- (plus pgvector) databse and the results need to be assessed with respect to an input question.
license: MIT
metadata:
  version: 0.2
allowed-tools: write_todos, read_file, write_file, edit_file, grep
---

# Interpreting database content

How to read what the database returns: what its records, notations and markers say, and what they do not say. How to query is covered by the search-database skill ([../search-database/SKILL.md](../search-database/SKILL.md)). How to weigh uncertainty in a conclusion is covered by the reasoning-about-uncertainty skill ([../reasoning-about-uncertainty/SKILL.md](../reasoning-about-uncertainty/SKILL.md)).

The table semantics from `get_table_semantics` give the meaning of each field and its values. Read them first. This skill adds only what they do not show.

## Missing documents

A document missing from the results may not be in the database, or may be described differently from how it was searched for. The database is not the whole of published papyrology, so the absence of a document from the results does not show that no such document exists.

## Where the data comes from

Readings, dates, places and classifications are editors' and cataloguers' assessments, not observations of the papyrus. Attribute them as such, but do not distrust them only because they are mediated. The markers described below show how an assessment was reached and how firm the editor considered it.

## Empty fields and missing rows

An empty field means the source records nothing, not that the property is lacking. A missing row means the same:

- **No date row.** The source may give a date without machine-readable bounds, or no date at all. The document is not thereby undated.
- **No place row.** The source usually gives the origin as unknown (`unbekannt`). The document is not thereby without a place.

## Papyri and texts

A Trismegistos id stands for one papyrus. Several metadata records with the same id are several texts on that papyrus, for example a contract with its registration docket, or a roll of many receipts.

A text edited more than once can appear under two Trismegistos ids. Compare the texts before treating them as two documents.

## Texts

### Plain text and XML

The plain text prints restorations of lost text and expanded abbreviations as if they were written, prints unclear letters as if certain, drops gaps (joining the words on either side) and marks of doubt, and gives the editor's regularized or corrected spelling and the accepted reading of a corrected passage. Letters the scribe omitted and the editor supplied are left out, and text the scribe deleted may still appear. Where an argument turns on wording, read the XML of that passage.

### Markers in the XML

These markers record editorial interventions and the condition of the text. They are not confidence grades: a restoration may be well constrained, and the absence of a doubt marker does not guarantee certainty.

| Marker | Meaning |
|---|---|
| `<unclear>` | Letters partly visible; the reading is the editor's. |
| `<gap reason="lost">`, `<gap reason="illegible">` | Text lost or unreadable. `quantity` gives its length in characters or lines; `extent="unknown"` means the length is unknown. |
| `<supplied reason="lost">` | The editor's restoration of lost text. `cert="low"` marks a doubtful one. |
| `<supplied evidence="parallel">` | Restored from a parallel text. |
| `<supplied evidence="apograph">` | Taken from an earlier copy or drawing, not from the papyrus as it is now. |
| `<supplied reason="omitted">` | Letters the scribe left out, added by the editor. |
| `<expan>`, `<ex>` | An abbreviation expanded by the editor; the `<ex>` part is the editor's. `<ex cert="low">` marks a doubtful expansion. |
| `<choice><reg>…</reg><orig>…</orig></choice>` | The scribe's spelling (`orig`) and the editor's standard form (`reg`). |
| `<certainty match=".." locus="value"/>` | The editor's "(?)": the enclosing reading is doubtful. |
| `<app type="editorial">` | A later correction. `<lem resp="BL …">` is the current reading, from the *Berichtigungsliste*; `<rdg>` is the reading it replaced. |
| `<app type="alternative">` | The editor offers more than one possible reading. |
| `<del>`, `<add>`, `<subst>` | The scribe's own corrections. |

### Translations

A translation is a modern interpretation of the text. Wording a claim depends on is checked in the original text.

## Dates

### Date notation

The date text is in German and keeps distinctions the numeric bounds lose. Read it alongside the bounds and the date's certainty.

- **Qualifiers.** `ca.`, `(?)`, `Anfang` (beginning), `Mitte` (middle), `Ende` (end), `nach` (after) and `vor` (before) qualify a date. `v.Chr.` means BCE. Roman numerals are centuries: `Ende II` is the end of the 2nd century CE, converted to the bounds 176–200.
- **Open bounds.** `nach 161` leaves the upper bound empty. A missing bound means the date is open on that side, not bounded.

### Uncertainty and precision

- **Doubt about part of a date is only in the date text.** `(Jahr unsicher)`, `(Monat unsicher)`, `(Tag unsicher)` and their combinations mark an uncertain year, month or day. The date's certainty stays empty for these. Low certainty marks doubt about the date as a whole and usually goes with `(?)`.
- **What precision means in practice.** Low precision is a century or part of one (`II`, `1. Hälfte VII`). Medium precision is an approximate year (`ca. 150`). Precision is granularity, not reliability: a broad range can be secure, and a precise-looking year can be doubtful.
- **Alternative dates.** When a source proposes several dates, all of them are flagged as alternatives, including the first. None of them is the primary date.

### How a date was obtained

How tight a date is depends on its basis, which the date text and the edition usually show:

- a date written out in full;
- a regnal year without the ruler's name, which fits several years;
- an indiction year alone, which repeats every 15 years;
- a known official's term of office;
- the archive the document belongs to;
- the handwriting, which often allows only a century or more.

## Places

- **One origin statement per document.** The full place name is the source's origin statement, repeated on every place row of the document. A `(?)` in it, as in `Pathyris (?)`, marks the whole attribution as doubtful, not one row.
- **One place at several levels.** Rows for a settlement, its nome and its region describe one place, not several.
- **Relation matters.** A findspot or a place of purchase is not necessarily where the text was written.

## Keywords and titles

Keywords and titles are cataloguers' descriptions, not the document's own words. They are in several languages, so one concept can carry several labels.

## Semantic search results

- **Closeness is not relevance.** A result is close to the query in the embedding model's sense of meaning. It may share vocabulary or topic without bearing on the question. Read the document before drawing on it.
- **Chunks, not documents.** A text result is one passage of a longer text. Several results can come from the same document.
- **A sample, not an inventory.** Each search returns a fixed number of results. They show neither completeness nor how common something is.
