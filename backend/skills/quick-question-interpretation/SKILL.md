---
name: quick-question-interpretation
description: Interpret a quick papyrological question before searching for the answer. Use when the user asks a question that a few database lookups or a short explanation answer, such as a count, a fact about a document or group of documents, or the meaning of a term. For a question that needs grounded argumentation from sources or a research report, use the question-interpretation skill instead.
license: MIT
metadata:
  version: 0.1
allowed-tools: task
---

# Quick question interpretation

A quick question is answered directly from a few lookups, without a research report. Interpretation makes explicit what the question asks before the first search, so the lookups answer the question the user asked. It does not answer the question.

## Input and output

Input: the user's question, and anything the conversation already says about it.

Output: the interpreted question, written into your context as the block under "Interpreted question" below, before the first search. There is no interpretation file. Answer from the block with the search-database skill ([../search-database/SKILL.md](../search-database/SKILL.md)). If you delegate the search with `task`, pass the block as the task description. Review the drafted answer with the answer-review skill ([../answer-review/SKILL.md](../answer-review/SKILL.md)) before it goes to the user.

## Possible topical axes

Each axis is a dimension along which evidence is gathered. A quick question usually has one primary axis, sometimes multiple auxiliary ones. These axes are not all there can be, but they are commonly involved.

- **Temporal (diachronic):** change over time. How a practice, term, institution or frequency developed; sequences of events; before and after. A single date or a date window is not temporal; it is an observation (material).
- **Material (observational):** the observable properties of documents and objects: date, place of writing or finding, material, format, handwriting, language, document type. Also which documents exist and how many.
- **Relational:** relationships between persons, names, places, times, topics or documents: families, officials and their offices, archives and dossiers, networks of trade or correspondence, and how one practice or institution relates to another.
- **Semantic:** wording and meaning: terms, formulae, idioms, genre conventions, and what a word or phrase meant in a given period and context.

## What the interpretation covers

- **Reading.** Where the wording allows several readings, take the most plausible one in the context of the conversation and state it, so the user can correct it from the answer. Flag that you did so in the answer.
- **Key terms.** The terms the lookups depend on, and how each is recognized in the database (a metadata value, a formula, a keyword). Mark as open what the lookups must establish.
- **Scope.** What the question and the conversation fix about period, region, document types and languages, and whether counts mean the database or the published literature. Mark everything else as open. Make no a-priori assumptions about facts.
- **Axes.** Which axes are involved, and what the question asks along each.
- **Lookups.** The lookups that answer the question, and how their results combine into the answer.

## Interpreted question

```markdown
Question: <the user's question, verbatim>
Interpreted as: <the question in its final form, with the reading and scope made explicit>
Terms:
- <term>: <what it is taken to mean; how it is recognized in the database, or open>
Scope: period <...>; region <...>; document types <...>; languages <...>; counts <database, literature or open>
Axes:
- <axis> (<primary or auxiliary>): <what the question asks along this axis>
Lookups:
1. <lookup>
2. ...
Combination: <how the results of the lookups form the answer>
```

### Example

```markdown
Question: How many papyri from Oxyrhynchus mention wine?
Interpreted as: How many distinct documents in the database whose place of origin is Oxyrhynchus mention wine in their text or metadata?
Terms:
- Oxyrhynchus: place of origin of the document, not only its findspot; how origin and findspot are distinguished in the place metadata is open.
- Mention wine: the Greek word for wine (οἶνος and its forms, in all spellings) in the transcription, or wine in the keywords or translation.
Scope: period open; region Oxyrhynchus; document types open; languages open; counts database
Axes:
- Material (primary): which documents from Oxyrhynchus exist, and how many.
- Semantic (auxiliary): by which words and spellings a mention of wine is recognized.
Lookups:
1. Documents with Oxyrhynchus as place of origin.
2. Among them, documents whose transcription, translation or keywords mention wine.
Combination: The count of distinct documents from lookup 2, with the coverage of transcriptions and translations among the documents of lookup 1.
```

## When the question is not quick

Switch to the question-interpretation skill ([../question-interpretation/SKILL.md](../question-interpretation/SKILL.md)) when the interpretation shows any of these:

- The answer needs more than five to seven lookups, or combining them needs argumentation from evidence: weighing conflicting records, establishing periods or categories first, or tracing change over time.
- The question has several sub-questions along different primary axes.
- The user asks for a scientifically grounded answer or a report.

## Acceptance criteria

- The block is written before the first search.
- The interpreted question states the reading taken and the scope, with open points marked.
- Every term the lookups depend on says how it is recognized in the database, or that this is open.
- The axes involved are stated, with what the question asks along each.
- The lookups answer the interpreted question, and the combination says how.
- The block contains no database results and no answer yet.
