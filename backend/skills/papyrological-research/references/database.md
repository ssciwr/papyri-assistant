# The papyrological database

What the database holds, where it misleads, and query patterns that work. Read this before your first query. For the full schema use `inspect_sql`; for the meaning of a column query `scrapyrus_semantic_catalog`.

## Contents

- Tables
- Coverage
- Pitfalls
- Query patterns
- Building source entries

## Tables

The data comes from papyri.info: DDbDP and DCLP texts, HGV metadata, and Trismegistos (TM) ids. `tm_id` links all tables and is the id of a document.

| Table | Holds |
|---|---|
| `papyri` | One row per metadata record: title, material, current location, edition ids (`ddb_hybrid_id`, `dclp_hybrid_id`, `hgv_id`). Several rows can share a `tm_id`. |
| `orig_dates` | Date of origin: `date_text`, year/month/day bounds (`not_before_*`, `not_after_*`), `certainty`, `precision`, `alternative`. |
| `orig_places` | Place of origin, one row per level (settlement, nome, region), with `place_type` and Trismegistos/Pleiades place ids. |
| `keywords` | Subject keywords with `scheme`, `qualifier` and an `uncertain` flag. |
| `principal_editions` | The principal edition: series `title`, `volume`, `number`, `page`, `author`. |
| `ancient_editions` | Literary works: ancient `author` and `title`. |
| `transcriptions` | Texts. `type` is `transcription` (the edition text) or `translation` (with `language`). `text` is plain text, `xml_content` is the EpiDoc XML, `text_vector` is a tsvector of `text`. |
| `scrapyrus_semantic_catalog` | Descriptions and caveats for every table and column, as JSON in `semantics`. |
| `*_embeddings` | The vector tables behind `similarity_search` and `mmr_search`. Use the search tools, not SQL, for these. |

## Coverage

Counted when this reference was written; check with `count(DISTINCT tm_id)` when the numbers matter for an argument.

- About 81,000 documents (distinct `tm_id`) in about 83,000 `papyri` records.
- About 62,000 documents have a transcription. The rest are metadata only, so a text search cannot find them.
- About 6,500 documents have a translation, most in English. Semantic search on `translations` therefore sees fewer than one document in ten.
- `current_location` is filled for about 33,000 records.
- Transcriptions are in Greek (about 59,700), Coptic (about 2,400) and Latin (about 830); only 3 are in Demotic. `transcriptions.language` is empty for transcriptions; read the language from the XML with `substring(xml_content::text from 'xml:lang="([^"]+)"')`.
- `lemma_text` and `lemma_vector` are empty.

The database is not the whole of published papyrology. A count from it is a lower bound.

## Pitfalls

**Decide what you count: papyri or texts.** A `tm_id` stands for one papyrus. HGV gives a papyrus that carries several texts one metadata record per text (`source_path` ending in `a.xml`, `b.xml`, ...). About 1,000 papyri have several records: a contract with its registration docket has two, and a roll of receipts can have dozens (TM 44371 has 67). Count `DISTINCT tm_id` to count papyri, and count `papyri` rows to count texts. Say in the record which one you counted and why.

**Joins multiply rows.** A papyrus can have several rows in `orig_dates`, `orig_places`, `keywords` and `papyri`. A join of these tables repeats each papyrus once per combination, so `count(*)` over a join overcounts. Use `count(DISTINCT tm_id)`.

**Duplicate editions.** A DDbDP id ending in `dupl` (e.g. `bgu;3;993dupl`, 237 records) marks a text that was edited more than once. Such a text can appear under two Trismegistos ids. Compare the texts before you count both.

**Metadata is in several languages.** `date_text` (`17. Juni 250`, `22. Aug. 124 v.Chr.`) and region names (`Ägypten`) are in German. Keywords are mostly German (`Quittung`, `Brief`, `Opfer`, `Eingabe`). DCLP keywords for literary texts are mostly English (`literature`, `christian`, `bible`). Some HGV keywords are French (`Lettre`, `Contrat de prêt en argent`, `Compte`) or Latin (`res privata`). Titles are in German, English or Italian (`Frammento di Libellus della persecuzione Deciana`), and translations are mostly English, with some German, French and Italian. One topic is therefore spread over many keyword strings: magic appears as `magic`, `Magic`, `magical`, `Magie`, `Zauber` and `magisch`, and fishing as `Fisch`, `Fische`, `Fischer`, `Fischerei` and `Fischfang`. Collect all variants before you count, with `similarity_search` on the `keywords` corpus and with `ILIKE` on stems in each language.

**`text` is an edited rendering, not what is preserved.** Compared with the XML, `text`:
- prints text supplied by the editor (`<supplied>`) as if it were preserved, including supplements of low certainty;
- prints the regularized spelling (`<reg>`) and drops the scribe's spelling (`<orig>`);
- drops gaps (`<gap>`) and the marks for unclear letters (`<unclear>`), so words on either side of a gap can run together.

A text search can therefore match a word that the papyrus does not preserve, and it misses the scribe's own spelling. Before you rest an argument on a reading, read `xml_content` for that passage.

**Words are split across lines.** `text` keeps the line breaks, and a word can run over two lines (`ἐγευσά` / `μεθα`). Remove whitespace before matching a formula.

**Accents count.** There is no `unaccent` extension, and `text_vector` uses the `simple` configuration, which keeps accents. Search for each accent and spelling variant, or match on a short stem that avoids the variable part.

**Dates are ranges.** Years before the common era are negative (`-124` is 124 BCE). A date is often a range from `not_before_year` to `not_after_year`, or a guess from the handwriting with `certainty` = `low`. To find documents in a period, test for overlap with both bounds, and say whether you counted documents that only overlap the period. A document can have several date rows; `alternative` marks an alternative date.

**Places have types and levels.** `place_type` gives the place's relation to the document: `located` (where the document was, the usual provenance), `found` (findspot), `composed`, `sent`, `received` or `acquired`. A findspot is not necessarily where a text was written. A document has a row for each level of a place (`granularity`: `settlement`, `nome`, `region`) and can have rows of several types. Count `DISTINCT tm_id` and filter on `place_type` and `granularity` when you count by place.

**Semantic search does not count.** It returns a fixed number of results per call. Use it to discover vocabulary and candidates, then search exactly with SQL.

## Query patterns

These patterns have been checked against the database and pass the `query_sql` validator.

Keyword search, distinct documents:

```sql
SELECT keyword, count(DISTINCT tm_id)
FROM keywords
WHERE keyword ILIKE 'opfer%'
GROUP BY keyword ORDER BY 2 DESC
```

Formula search with whitespace removed, scoring how many formula elements a text contains:

```sql
WITH t AS (
  SELECT tm_id, regexp_replace(text, '\s+', '', 'g') AS s
  FROM transcriptions WHERE type = 'transcription'
)
SELECT tm_id FROM t
WHERE ((s LIKE '%ἐπὶτῶνθυσιῶν%')::int
     + (s LIKE '%ἔσπεισα%' OR s LIKE '%ἐσπείσα%')::int
     + (s LIKE '%ἐγευσάμ%')::int
     + (s LIKE '%θύων%' OR s LIKE '%θύοντ%')::int) >= 2
```

A scan over all transcriptions like this takes about 15 seconds. Narrow it first where you can, e.g. with a date range or a `text_vector` match.

Word search with the tsvector (whole words only, exact accents):

```sql
SELECT tm_id FROM transcriptions
WHERE type = 'transcription' AND text_vector @@ to_tsquery('simple', 'ἐγευσάμην')
```

Show the context of a match:

```sql
SELECT tm_id, substring(text from '.{0,40}θύων.{0,40}')
FROM transcriptions
WHERE type = 'transcription' AND text LIKE '%θύων%'
```

Documents dated within a period (overlap with both bounds):

```sql
SELECT count(DISTINCT tm_id) FROM orig_dates
WHERE not_before_year <= 260 AND not_after_year >= 240
```

Candidate details for checking:

```sql
SELECT p.tm_id, p.title, p.ddb_hybrid_id, d.date_text, d.certainty, pl.full_place_name
FROM papyri p
LEFT JOIN orig_dates d ON d.tm_id = p.tm_id
LEFT JOIN orig_places pl ON pl.tm_id = p.tm_id AND pl.granularity = 'settlement'
WHERE p.tm_id IN (11977, 13792)
```

Column meanings and caveats:

```sql
SELECT semantics -> 'columns' -> 'certainty'
FROM scrapyrus_semantic_catalog WHERE table_name = 'orig_dates'
```

## Building source entries

For each cited document collect:

- **TM id**: `tm_id`.
- **Edition**: from `principal_editions` (`title`, `volume`, `number`), e.g. `P.Mich.` + `3` + `157` gives P.Mich. III 157. `papyri.ddb_hybrid_id` (`p.mich;3;157`) gives the same.
- **Title**: `papyri.title`.
- **Date**: `orig_dates.date_text`, with its certainty if it is not certain.
- **Place**: `orig_places.full_place_name`.
- **Link**: from `ddb_hybrid_id`, or from `dclp_hybrid_id` if that is empty. Split the id at `;`, drop the empty parts, and join the rest with `/`: `p.mich;3;157` gives `https://papyri.info/editions/p.mich/3/157`, and `t.varie;;71` gives `https://papyri.info/editions/t.varie/71`. If both ids are empty, use `https://www.trismegistos.org/text/<tm_id>`.
- **Current location**: `papyri.current_location`, if filled. If it is empty, say that the database does not record it.
