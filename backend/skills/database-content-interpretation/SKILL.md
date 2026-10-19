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

The table descriptions from `get_table_semantics` give the meaning of each field and its values. This skill explains how to read them together.

## What a record reports

- **An editor's assessment.** Readings, dates, places and classifications come from editors and cataloguers, not from your own inspection of the papyrus. Attribute them as such, but do not distrust them only because they are mediated.
- **Recorded, established, inferred.** Keep apart what a record reports, how the editor established it (preserved wording, restoration, handwriting, parallel), and what you infer from it.
- **Missing is not absent.** An empty field means the source records nothing, not that the property is lacking. A document missing from the results may simply not be in the database or not be described that way. The database is not the whole of published papyrology.

## Documents, records and texts

- **A Trismegistos id is one papyrus.** One papyrus can carry several texts, each with its own metadata record, for example a contract with its registration docket, or a roll of many receipts. Rows sharing an id are parts of one papyrus.
- **Repeated rows.** A document with several dates, places or keywords appears once per combination in joined results. Repetition does not mean several documents or several attestations.
- **Duplicate editions.** A text edited more than once can appear under two Trismegistos ids. An edition id ending in `dupl` marks one. Compare the texts before treating them as two documents.

## Texts

### Plain text and XML

The plain text is an editor's rendering derived from the EpiDoc XML. It shows restorations as if they were preserved, drops gaps and marks of doubt, keeps the regularized spelling instead of the scribe's, and keeps only the accepted reading of a corrected passage. Where an argument turns on wording, read the XML of that passage. You need not read the whole text.

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

The source date text is in German and keeps distinctions the numeric year bounds lose. Read it alongside the bounds.

- **Qualifiers.** `ca.`, `(?)`, `Anfang` (beginning), `Mitte` (middle), `Ende` (end), `nach` (after) and `vor` (before) qualify a date. `v.Chr.` means BCE. Roman numerals are centuries: `Ende II` is the end of the 2nd century CE.
- **Converted bounds.** The bounds turn a description into numbers: `Ende II` becomes 176–200. Years BCE are negative.
- **Open bounds.** `nach 161` leaves the upper bound empty. A missing bound means the date is open on that side, not bounded.

### Date markers

| Marker | Meaning |
|---|---|
| certainty `low` | The date is doubtful; it almost always goes with `(?)` in the date text. An empty certainty does not rule out a `(?)` there, so read both. |
| precision `low` | Dated to a century or part of one (`III`, `Anfang IV`). |
| precision `medium` | An approximate year (`ca. 297`). |
| alternative | One of several dates proposed for the document. |

Precision is granularity, not reliability. A broad range can be secure, and a precise-looking year can be doubtful.

### How a date was obtained

How tight a date is depends on its basis, which the date text and the edition usually show:

- a date written out in full;
- a regnal year without the ruler's name, which fits several years;
- an indiction year alone, which repeats every 15 years;
- a known official's term of office;
- the archive the document belongs to;
- the handwriting, which often allows only a century or more.

## Places

- **Relation to the document.** A place is recorded with its relation: `composed` is where the text was written, `located` is the usual provenance, `found` is the findspot, `acquired` is where it was bought, and `sent` and `received` are a letter's ends. A findspot or a place of purchase is not necessarily where the text was written.
- **Levels.** One place appears at several levels (settlement, nome, region). These are one place, not several.
- **Doubtful attributions.** `(?)` in a place name marks a doubtful attribution, as in `Pathyris (?)`.

## Keywords and titles

- **Modern classifications.** Keywords and titles are cataloguers' descriptions, not the document's own words. They are in several languages, so one concept can carry several labels.
- **Uncertain classification.** A keyword flagged as uncertain means the classification itself is doubtful.

## Semantic search results

- **Closeness is not relevance.** A result is close to the query in the embedding model's sense of meaning. It may share vocabulary or topic without bearing on the question. Read the document before drawing on it.
- **Chunks, not documents.** A text result is one passage of a longer text. Several results can come from the same document.
- **A sample, not an inventory.** Each search returns a fixed number of results. They show neither completeness nor how common something is.
