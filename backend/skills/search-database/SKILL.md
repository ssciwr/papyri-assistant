---
name: search-database
description: Search the postgres-database (tabular and vector via pgvector) for information about papyri using the available database tools. Use whenever a database search is asked for or you deem it necessary to answer a user question.
license: MIT
metadata:
  version: 0.1
allowed-tools: write_todos, task, list_sql_tables, get_table_semantics, query_sql, similarity_search, mmr_search
---

# Search database

The database is PostgreSQL with pgvector. It holds papyri.info metadata, transcriptions and translations as tables, and embeddings of the texts and keywords as vector tables. The Trismegistos id links all tables and identifies a document.

- **The SQL tables hold the facts.** Query them with `query_sql`.
- **The vector tables hold meaning.** `similarity_search` and `mmr_search` find passages and keyword strings that match a query in meaning.

This skill covers how to retrieve data. To assess what the retrieved data means for a question, use the database-content-interpretation skill ([../database-content-interpretation/SKILL.md](../database-content-interpretation/SKILL.md)).

## Before you query

1. **Orient.** Call `list_sql_tables` once per task to see which tables can answer the question.
2. **Understand.** Before querying a table, call `get_table_semantics` for it. Read what one row represents, what the columns and their values mean, what a missing value means, how the table relates to others, and its caveats. Do not guess what a column means from its name. The semantic catalog is the authority on the database's structure.

## Choosing a route

Pick the routes the question needs, and combine them when one alone falls short:

- **Metadata only.** Questions about date, place, material, edition or classification can often be answered with sql queries.
- **Vocabulary.** Keywords have their own embeddings table, which can be used to quickly find candidate documents via a similarity or mmr search.
- **Content.** When the question is about what texts say, search `transcriptions` or `translations` semantically for candidates, then retrieve and filter them with SQL.

Translation- and transcription coverage is limited. Not all document have translation or transcription. So take this into account when choosing a route.

## Querying with SQL

- **Read only.** `query_sql` runs one `SELECT` at a time and validates it against the live schema. A failed query returns its error text. If that happens, read the error, fix the query and try again.
- **Vector tables through the vector search tools.** Always query the vector tables with `similarity_search` or `mmr_search`, never with `query_sql`. A semantic search needs your query turned into a vector by the same embedding model the corpus was built with, and only the search tools do that. Selecting the stored vectors with SQL returns only long lists of numbers.
- **Full-text scans are slow.** A pattern match over all texts can take a while. Combine it with the question's other filters where it has any.

### Counting

Count distinct documents, not joined rows, and state what you counted.

### Dates and places

- **Dates.** When you search a period, state whether the results include documents that only partly overlap it. Retrieve the date text, certainty, precision and alternative flag along with the bounds. Do not exclude alternative dates to find a document's primary date: when a source proposes several dates, all of them are flagged as alternatives.
- **Places.** Filter on both the place's relation to the document and its level when you search or count by place.

### Texts

- **Plain text or XML.** Retrieve the XML when the editorial markup is needed: supplements, regularized and original spellings, gaps and unclear letters.
- **Words run over line breaks.** Remove whitespace before matching a formula.
- **Accents and spelling count.** Search each accent and spelling variant, or match a short stem that avoids the variable part.

### Multilingual metadata

Metadata comes from several projects and languages. Match stems in each language, together with the keyword embeddings.

### Coverage

Not every document has a transcription, and far fewer have a translation, so text and translation searches cannot find documents that only have metadata. When it matters for the question, measure the coverage of the route you used with SQL.

## Semantic search with pgvector

The search tools embed your query with the model each corpus was built with and rank the returned vectors by a mathematical measure. Choose the corpus by what you need:

- `transcriptions`: original-language wording (Greek, Coptic, Latin). Returns text chunks.
- `translations`: a document's meaning in a modern language. Covers only a small share of documents.
- `keywords`: controlled vocabulary. Returns keyword strings, not documents.

Choosing between the tools:

- **`similarity_search`** returns the closest results. Use it for a focused query.
- **`mmr_search`** returns close but varied results. Use it when a question has several aspects, or when `similarity_search` returns near-duplicates, such as chunks of the same document.

Search habits:

- **Phrase the query as the passage would say it.** Write it as a statement or question in the corpus's language: Greek, Coptic or Latin wording for `transcriptions`, and a modern language for `translations`.
- **Vary the query, not the call.** Each call returns a fixed number of results. Rephrase, switch language or switch corpus to see more.
- **Follow up in SQL.** Text results carry their document's Trismegistos id; use it to retrieve the document.
- **Semantic search does not count.** Its results are not complete or ranked by importance. Counts and lists come from SQL.

## Keyword embeddings

The `keywords` corpus embeds every distinct keyword string in the database, so you can find terms by meaning across languages. One concept is often spread over many strings in several languages: grain appears as `Getreide`, `Weizen`, `Getreidelieferung` and `Zahlung von Getreide`.

- Search the concept in several languages and with both tools, and collect every relevant string.
- A returned string may combine a keyword with its qualifier. Check the keyword table's semantics for how to match it.
- A document usually has several keywords, so a compound concept such as "grain receipt" may be two keywords on one document.
- Match the collected strings exactly in SQL, and add stem matches to catch variants the embeddings missed.

## Report what you did

When you return results, give for each search route the exact queries (semantic query and corpus, or SQL), the counts you obtained and what they count, the Trismegistos ids found, and the limits of the route, such as translation coverage or keyword variants that might be missing.
