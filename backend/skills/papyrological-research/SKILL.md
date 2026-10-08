---
name: papyrological-research
description: Research an interpreted papyrological question in the database and record the evidence the report is written from. Use once the question has been interpreted.
license: MIT
metadata:
  version: 0.2
allowed-tools: write_todos, read_file, write_file, edit_file, grep, task, list_sql_tables, inspect_sql, query_sql, similarity_search, mmr_search
---

# Papyrological research

Research answers the user's question from the database and records everything the report needs. It starts from the interpretation file written with the question-interpretation skill, which defines the question, its axes and its sub-questions. The report-writing skill turns the research record into the final report, and it needs these items from the record:

- the user's question and how it was interpreted, with its sub-questions;
- the workflow and methods used, step by step, with the limits of each step;
- the conclusions drawn, each set out as a claim with its certainty;
- the evidence for and against each claim, with every source verified;
- the alternatives that were considered, and why each was rejected or remains open;
- the gaps: what the database could not answer.

Keep the record like a lab notebook: write each step into it as you take it, with its exact query and result, including the searches that found nothing. A step that is not in the record is lost for the report, and the reader of the report must be able to retrace every step and check every source.

## Sub-questions and claims

A **sub-question** comes from the interpretation. It says what has to be found out, and it changes only by a recorded revision.

A **claim** comes from the evidence. It is a statement that answers a sub-question, or the main question, in whole or in part, for example "The database holds 47 records of Decian certificates". Sub-questions stay questions; claims are the answers the evidence gives to them. One sub-question can lead to several claims.

A claim starts as **provisional**, as soon as the evidence suggests an answer. It is then put through a falsification search and source criticism, and only then recorded as a claim with its evidence for and against, its reasoning and its certainty. A provisional claim that does not survive is recorded under Alternatives, with the reason it was rejected.

## Input and output

Input: the interpretation file `/scratchpad/interpretation-<topic>.md`. If there is none, interpret the question with the question-interpretation skill first.

In a revision round, the input also includes the review file `/scratchpad/review-<topic>-<round>.md`. Resolve every issue that goes to research: run the searches it requires, record them as steps, and update the claims, alternatives and gaps in the existing record.

Output: a research record at `/scratchpad/research-<topic>.md`, with the same `<topic>` as the interpretation file, in the structure under "Research record" below. Once the record meets the acceptance criteria, write the report with the report-writing skill, or pass the record's path to the agent that writes it.

## Workflow

1. **Start the record.** Read the interpretation file. Copy its question, interpretation, axes and sub-questions into the record, and name the file's path.
2. **Plan with `write_todos`,** sub-question by sub-question. The interpretation contains only what the user's question says, so the points it leaves open (terms, periods, categories) come first: the sub-questions that establish them go before the sub-questions that depend on them. For every sub-question about a set of documents, plan to triangulate with at least two independent search routes (see "Search routes").
3. **Orient in the database.** Read [references/database.md](references/database.md) before your first query. Use `inspect_sql` for the schema, and query `scrapyrus_semantic_catalog` for the meaning and caveats of each column you will use.

Then work through steps 4–8 for each sub-question, in the planned order.

4. **Search.** Run the planned routes, and record each step: the sub-question it serves, its purpose, the tool, the exact query or search text, the number of results, and its limitation.
5. **Check every candidate.** Read its date, place, title and text, decide whether it belongs to the answer, and record the decision and the reason. Look into every document that only one route found, and every document a route should have found but did not.
6. **Formulate provisional claims:** one sentence each for what the evidence so far suggests as the answer to the sub-question.
7. **Try to falsify each provisional claim** with at least one search aimed at evidence against it: an exception, a document outside the expected date or place, a different meaning of the key word. Record what the search finds, including nothing. New candidates go through step 5, and the provisional claims are revised to match.
8. **Apply source criticism** to every document a provisional claim rests on (see "Source criticism"), and check the reasoning against the inference errors of each involved axis (see "Inference along the axes"). Record each uncertainty next to the evidence it affects.

When every sub-question has been through steps 4–8:

9. **Record the claims.** Keep, revise or reject each provisional claim in the light of steps 7 and 8, and record the claims that answer each sub-question. Where there are several sub-questions, add the claims that answer the main question (see "Synthesis"). Then list the other answers that were considered, including the rejected provisional claims.
10. **Verify the sources.** Cite only documents confirmed with `query_sql`, and collect for each its Trismegistos id, edition, title, date, place, link and current location (see "Building source entries" in [references/database.md](references/database.md)).
11. **Check the record** against the acceptance criteria. Fill the gaps, then hand over to report writing.

## Revising the interpretation

The interpretation is a starting point, not a fixed frame. The evidence may show that a term shifts its meaning, that the scope is too narrow or too wide, that a point needed for the answer was not foreseen, or that a sub-question is wrongly put. Then revise it: record the revision under "Revisions" in the record's interpretation, with the evidence that prompted it, and continue with the revised version. The interpretation file itself stays as it was, so that the original remains visible. If a revision changes what the user's question is taken to mean, tell the user.

## Search routes

Each route sees a different part of the corpus. Triangulate: two routes that agree are strong evidence, and two that disagree show you where to look.

- **Metadata (`query_sql`)**: keywords, titles, dates, places, editions. Good for complete lists and counts within what the metadata records. Misses every document that was not tagged or described accordingly.
- **Text (`query_sql` on `transcriptions`)**: words and formulae in the original language. Good for finding documents by their wording. Misses spelling variants, damaged passages and documents without a transcription.
- **Semantic (`similarity_search`, `mmr_search`)**: closeness in meaning to a question. Good for discovering candidates and vocabulary you did not know to search for; the `keywords` corpus yields the exact keyword strings to query. It returns a fixed number of results, so it shows neither completeness nor counts: build exact SQL searches from what it finds, and count with those.

How to search each route well (the languages of the metadata, words split across lines, editorial supplements in the text, the coverage of the translations) is in [references/database.md](references/database.md).

You may delegate independent sub-questions or search routes to subagents with `task`. Tell each subagent to return its exact queries, its result counts, the list of Trismegistos ids it found, and its limitations, so that its steps can go into the record.

## Source criticism

Check every document a claim rests on against each point, and record what makes it weaker or stronger:

- **Date**: a precise date, a range, or a guess from the handwriting? Read `certainty` and `precision` in `orig_dates`; a document can have alternative dates.
- **Place**: where the document was written, found, or sent? Read `place_type` in `orig_places`.
- **Reading**: is the decisive word preserved, or supplied by the editor? The `text` column does not show the difference; `xml_content` does. Is the text a fragment?
- **Orthography**: does the spelling vary in ways that a search may miss, or that change the reading?
- **Semantics**: what does the word mean in this document's period and context? (*Libellus*, for example, means "petition" in late antiquity, not only "certificate".)
- **Author and purpose**: who wrote the document, for whom, and why? An official report, a petition and a private letter each present facts in their own interest.
- **Edition and research history**: how old is the edition? Have the reading, the date or the interpretation been revised since? Is the record a duplicate (`dupl` in the edition id) or a re-edition of a text already counted?

## Grounding

Every claim is grounded in evidence from the database: documents, their texts and their metadata, each found by a recorded step. Knowledge you bring yourself, about the literature, the history or the meaning of a term, can suggest where to search; run the search, and the result is the evidence. Such knowledge never enters the record as a fact, a source or a figure. A sub-question that only sources outside the database could answer, such as a count in the scholarly literature, is recorded as unanswered under Gaps, with the source that would answer it.

## Inference along the axes

Source criticism tests each document; these are the errors of reasoning from documents to claims. Check the reasoning for each primary and auxiliary axis of the interpretation:

- **Temporal**: attributing a document to a period or event because its date fits; comparing raw counts from periods or places that are preserved unequally. Most papyri come from a few places, above all the Fayum and Oxyrhynchos, and from some periods more than others, so count the documents in the database for each period or place, and compare shares.
- **Material**: counting records instead of papyri; taking a database count for the number preserved. The database holds the papyri.info data, not every published papyrus, so its count is a lower bound.
- **Relational**: taking two persons with the same name for one person, or one person under variant names for two; inferring a relationship from two names or topics occurring in the same document.
- **Semantic**: carrying a meaning from one period or context into another; reading a formula as a description of what happened, when it may only be the conventional wording.

Papyri rarely narrate events or describe institutions. They mostly show them through their effects: dating formulas, requisitions, taxes, soldiers and settlers, prices, complaints. For each claim, say whether it rests on direct or indirect evidence, and attribute a document to an event or institution only when its text links it to one.

## Synthesis

Where the interpretation has several sub-questions, the answer is more than their sum. Follow the synthesis plan of the interpretation, and check whether the evidence supports it:

- Build each claim on the main question from the claims that answer the sub-questions, and name them.
- Where the sub-questions' answers pull in different directions, say so, and explain which weighs more and why.
- Where a sub-question could not be answered, say how that limits the answer to the main question.

## Research record

Write the record in this structure. The report-writing skill relies on it.

```markdown
# Research record: <short title>

## Question
<the user's question, verbatim>

## Interpretation
Interpretation file: /scratchpad/interpretation-<topic>.md
<restatement, terms, scope, readings and axes, copied from the interpretation file>

### Sub-questions
- SQ1 (<axis>, <role>): <sub-question>

### Revisions
- <what was revised, the evidence that prompted it, and the effect on the research; "none" if none>

## Steps
### Step <n> (SQ<m>): <purpose>
- Tool: <tool name>
- Query: <exact SQL, or search text and corpus>
- Result: <number of rows or documents; where the full result is stored>
- Limitation: <what this step can miss or get wrong>

## Candidates
| TM | Edition | Date | Place | Found by | Decision | Reason |

## Claims
### Claim <n> (SQ<m>, or main question): <the claim in one sentence>
- Evidence for: <documents by TM id, with what each shows; for a main-question claim, the claims answering the sub-questions that it builds on>
- Evidence against and uncertainties: <documents, gaps and uncertainties>
- Reasoning: <how the evidence leads to the claim>
- Certainty: <high, medium or low, and why>

## Alternatives
- <other answer>: <why it was rejected, or why it remains open>

## Draft answer
<a short answer to the question, and how certain it is>

## Gaps
- <what was not checked, and how it could be checked>

## Sources
| TM | Edition | Title | Date | Place | Link | Current location |
<one row per cited document, verified with query_sql>
```

## Acceptance criteria

- The interpretation is copied from the interpretation file, and every revision is recorded with its reason.
- Every step is recorded with its sub-question, its exact query, its result count and its limitation.
- Every claim about a set of documents rests on at least two independent search routes, or the record says why only one was possible.
- Every candidate has a recorded decision and reason.
- Every sub-question is answered by at least one claim, or the record says why it could not be answered.
- Where there are several sub-questions, the main question is answered by claims that build on them.
- Every claim has evidence for and against, reasoning, and a stated certainty.
- At least one falsification search is recorded for each claim.
- Every document a claim rests on has been through source criticism.
- Alternatives and gaps are listed.
- Every cited document has been verified with `query_sql`, and its source entry is complete.
- Every claim is grounded in database evidence. No fact, source or figure in the record comes from your own knowledge.

## Example

[references/example-research-record.md](references/example-research-record.md) is the research record for the question "How many Libelli from the persecution of Christians under Decius are preserved?". It starts from the example interpretation file in the question-interpretation skill, and the good report in the report-writing skill was written from it. Read it before your first research record.
