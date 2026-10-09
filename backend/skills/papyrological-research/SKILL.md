---
name: papyrological-research
description: Investigate an interpreted complex papyrological research question using the database, and record the evidence and reasoning for the final research report. Use once the research question has been interpreted.
license: MIT
metadata:
  version: 0.3
allowed-tools: write_todos, read_file, write_file, edit_file, grep, task, list_sql_tables, inspect_sql, query_sql, similarity_search, mmr_search
---

# Papyrological research

Investigate the user's question, following the evidence rather than a fixed sequence of checks. Start from the question-interpretation file and leave a research record that the report-writing skill can turn into an answer: what you found, how you found it, why it supports your conclusions, and what remains uncertain.

The aim is a useful, defensible answer, not an exhaustive audit of the database. Scale the research to the question and the strength of the claims you intend to make. A representative example, a corpus count and a historical explanation need different kinds of support. Be thorough where a mistake would change the answer; keep routine checks and notes brief.

## Input and output

Input: `/scratchpad/interpretation-<topic>.md`. If there is none, use the question-interpretation skill first.

In a revision round, also read `/scratchpad/review-<topic>-<round>.md`. Address research issues in the existing record: run useful follow-up searches, revise unsupported claims, or explain why a requested check is unavailable or would not resolve the issue. Do not repeat completed work merely to recreate the workflow.

Output: `/scratchpad/research-<topic>.md`, using the same `<topic>` as the interpretation file. Keep the sections under "Research record" so the report writer can find the findings and their support. When the record is ready, use the report-writing skill or pass its path to the report-writing agent.

## Research approach

1. **Establish the question.** Read the interpretation and start the record with the question, scope and sub-questions. Identify which uncertainties actually affect the answer.
2. **Make a working plan.** Use `write_todos` for substantial investigations. Start with dependencies that matter, but interleave sub-questions and revise the plan as discoveries suggest better routes. Do not turn every open term into a separate research project if it does not change the answer.
3. **Orient in the database.** Read [references/database.md](references/database.md) before your first query. Inspect the relevant schema with `inspect_sql`; consult `scrapyrus_semantic_catalog` for unfamiliar fields or caveats that matter to your searches and conclusions.
4. **Search and inspect.** Choose the route most likely to find useful evidence. Inspect promising documents and refine vocabulary, dates, places or classifications as needed. Add another route when it offers a meaningful coverage check or new evidence, not simply to meet a quota.
5. **Develop and test answers.** Form provisional claims as the evidence develops. For conclusions the answer depends on, consider plausible alternatives and look for evidence that could change them. A targeted query, a closer reading, a comparison or an existing search result may provide the check; there is no requirement for a separate falsification search for every claim.
6. **Assess the sources.** Check the features each claim depends on, using "Source criticism" below. Distinguish what a document records from what you infer, and keep material uncertainty beside the affected claim.
7. **Synthesize and hand over.** Answer the main question from the findings, including tensions and limits. Verify cited documents, assemble their source entries, and check whether the record supports the proposed answer.

These are recurring activities, not gates. You can search, interpret, check and synthesize in whatever order helps answer the question.

### Choosing depth and stopping

- **Examples or exploratory questions:** inspect a useful selection and state how it was chosen. Do not imply that it represents the whole corpus or exhausts the relevant documents.
- **Counts or complete lists:** define the inclusion criteria and counting unit, check duplicates, and investigate likely omissions. Independent search routes are especially useful here; where feasible, cross-check coverage with another route and explain remaining blind spots.
- **Broad historical or semantic claims:** look for comparable documents, exceptions and rival explanations. A few examples may establish that something occurred without establishing how common it was.

Stop when you can give a supported answer at the requested depth and further searches are unlikely to change it materially. Also stop or narrow the claim when the database cannot resolve a remaining uncertainty. Record what was not checked rather than continuing indefinitely or treating a partial answer as a failure. If the user gives a time or scope limit, prioritize the conclusions most important to them.

## Sub-questions, claims and revisions

A **sub-question** identifies what needs to be found out. A **claim** is an answer suggested by the evidence; one sub-question may yield several claims, or remain open.

Treat claims as provisional while researching. Keep, revise or reject them as you learn more. Record significant changes and plausible competing answers, but do not manufacture alternatives or counter-evidence for straightforward observations.

The interpretation is a starting point, not a fixed frame. If the evidence exposes a shifting term, an unsuitable scope or a missing sub-question, record the revision and its reason in the research record. Leave the original interpretation file intact. Tell the user if the revision materially changes what their question is taken to mean.

## Search routes

Each route has different strengths and blind spots. Agreement helps, but shared metadata or editorial assumptions can make apparently different searches less independent than they seem.

- **Metadata (`query_sql`)**: keywords, titles, dates, places and editions. Useful for lists and counts within the recorded classifications; misses documents tagged or described differently.
- **Text (`query_sql` on `transcriptions`)**: original-language words and formulae. Useful for wording and context; misses variants, damaged passages and documents without transcriptions.
- **Semantic (`similarity_search`, `mmr_search`)**: useful for discovering candidates, parallels and vocabulary. The `keywords` corpus can reveal exact keyword strings for SQL searches. Fixed-size semantic results do not establish completeness or counts; use SQL for those.

Use the guidance in [references/database.md](references/database.md) for multilingual metadata, split words, editorial supplements and translation coverage. When routes disagree, investigate discrepancies that could affect your answer. An exploratory search does not require resolving every unmatched hit.

You may delegate independent sub-questions or routes with `task`. Ask for the findings, exact consequential queries, relevant result counts, Trismegistos ids and limitations so you can integrate their evidence without rerunning the work.

## Source criticism

Criticism should follow the claim: examine the aspects that could change the conclusion, not every possible property of every document. A metadata inventory does not require the same close reading as an argument about a restored phrase.

- **Date:** precise, approximate or palaeographic? Read `date_text` alongside `certainty`, `precision` and any alternative dates in `orig_dates` when chronology matters.
- **Place:** written, found, acquired, sent or received where? Check `place_type` and any uncertainty in the full place name when provenance matters.
- **Reading:** preserved wording or editorial restoration? Check the decisive passage in `xml_content` when an argument depends on its wording; plain `text` hides supplements and uncertainty. Note fragmentary evidence.
- **Orthography and semantics:** could spelling variants affect retrieval? Does the term have the same meaning in this period and context? Compare relevant parallels where useful.
- **Author and purpose:** what can this genre and writer reasonably establish? A petition, official report or private letter has its own purposes; a statement in it is not automatically proof that the event occurred as described.
- **Edition and research history:** check available revisions or duplicate editions where they affect a reading, attribution or count. Do not imply you have checked scholarship the database does not provide.

Use [../reasoning-about-uncertainty/SKILL.md](../reasoning-about-uncertainty/SKILL.md) when interpreting uncertain dates, places, readings or meanings. Explain uncertainties that affect the answer; if competing readings lead to the same conclusion, a brief note is enough.

## Grounding and interpretation

Database findings, counts, quotations and document-specific assertions must be supported by retrieved evidence. Verify documents with `query_sql` before citing them; semantic hits and remembered examples are leads, not verified sources. Never invent a source, quotation, figure or bibliographic detail.

Use your linguistic and historical knowledge to choose searches, understand documents and propose explanations. It may appear in the record as explicitly labeled background knowledge or an interpretive hypothesis, with its basis and uncertainty. Distinguish it from what the retrieved documents establish. Where a conclusion depends on such an assumption, seek supporting evidence or qualify the conclusion; labeling it is not a substitute for verification.

If the question needs unavailable external scholarship, identify that limit and the kind of source needed. You can still offer a qualified database-based answer rather than withholding all interpretation.

## Inference along the axes

Use the interpretation's axes to notice relevant reasoning risks, not as a checklist for unrelated checks:

- **Temporal:** a date compatible with an event does not itself link the document to that event. Uneven survival and database coverage limit comparisons of frequencies. If frequency matters, consider an appropriate corpus baseline; even normalized shares are not automatically historical rates.
- **Material:** distinguish records, texts and physical objects. Define the unit in a count and account for duplicates. The database is not all published papyrology; avoid treating a database total as the total preserved. Uncertain classifications may also prevent a count from being a firm lower bound.
- **Relational:** shared names do not establish identity, and co-occurrence does not establish a relationship. Look for contextual links.
- **Semantic:** meanings change across periods and genres. Conventional formulae may show how something was represented rather than what actually happened.

Indirect evidence can support historical interpretations. Say what connects it to the proposed event or institution, why that explanation is plausible, and what alternatives remain. Reserve direct attribution for explicit links in the evidence.

## Synthesis

Use the interpretation's synthesis plan as a guide. Explain how the sub-question findings combine into an answer, rather than merely listing them. Where they pull in different directions, weigh the evidence and say why. Where one remains unanswered, explain whether it limits the main conclusion or only a secondary detail.

## Research record

Keep a concise working notebook as you go, or after a coherent batch of searches. Preserve the queries and results needed to reproduce consequential findings, including negative searches that affect the answer. Routine lookups can be grouped; large results and candidate inventories can live in linked files. Do not copy every raw tool response into the record.

Use this structure, scaling the detail to the investigation. "None found", "not checked" or "not applicable", with a brief explanation where needed, are valid entries; empty quotas are not reasons to invent work.

```markdown
# Research record: <short title>

## Question
<the user's question, verbatim>

## Interpretation
Interpretation file: /scratchpad/interpretation-<topic>.md
<question as interpreted, key terms, scope and axes>

### Sub-questions
- SQ1 (<axis>, <role>): <sub-question>

### Revisions
- <significant revision, why it was made and its effect; or none>

## Steps
### Step <n> (SQ<m>, or several): <purpose>
- Tool: <tool name>
- Query: <exact consequential SQL, or search text, corpus and relevant parameters; routine lookups may be grouped>
- Result: <finding; count and location of full results where relevant>
- Limitation: <material limitation, or reference to a shared limitation>

## Candidates
<documents used and significant inclusion/exclusion decisions, or link to an inventory>
| TM | Edition | Date | Place | Found by | Decision | Reason |

## Claims
### Claim <n> (SQ<m>, or main question): <claim>
- Evidence for: <verified documents by TM id and what they show; or supporting sub-question claims>
- Evidence against and uncertainties: <contrary evidence, plausible alternatives, assumptions and relevant limits; distinguish not found from not checked>
- Reasoning: <how the evidence supports the claim; label background knowledge and interpretive hypotheses>
- Certainty: <grade or plain-language assessment, with its basis>

## Alternatives
- <plausible competing answer and why it was rejected or remains open; or none relevant>

## Draft answer
<direct answer at the strength the evidence supports>

## Gaps
- <unanswered point or material check not performed, its effect on the answer, and possible follow-up>

## Sources
| TM | Edition | Title | Date | Place | Link | Current location |
<one row per cited document, verified with query_sql; mark unavailable fields as not recorded>
```

For a count or complete list, retain the included ids and enough inclusion/exclusion decisions to audit the total. For an exploratory investigation, record the documents actually used and important exclusions; you need not adjudicate every search hit.

Build source entries using [references/database.md](references/database.md). Batch verification is fine, and previously retrieved SQL evidence can serve as verification without another identical query. Missing metadata is a limitation to report, not something to fill from memory or a reason to withhold an otherwise useful source.

## Ready for report writing

- The record answers the user's question as interpreted, or gives a useful partial answer with explicit limits.
- Consequential searches and findings are traceable; counts have a defined unit, criteria and coverage limits.
- The conclusions that matter have appropriate checks for alternatives, omissions or uncertain readings. The checks are chosen for their value, not their number.
- Claims have evidence, reasoning and a justified certainty; contrary evidence and material uncertainty are not hidden.
- The main answer follows from the findings. Unanswered sub-questions and significant revisions are visible.
- Cited documents have SQL verification and source entries; unavailable metadata is marked.
- Retrieved findings are distinguishable from background knowledge and hypotheses. Unverified external scholarship is not presented as checked evidence.

These criteria concern the reliability and usefulness of the handover, not the number of steps or the length of the notebook.

## Example

[references/example-research-record.md](references/example-research-record.md) illustrates a detailed investigation of "How many Libelli from the persecution of Christians under Decius are preserved?". Consult it for query and record examples, not as a minimum workload or a source of current counts. Its exhaustive candidate treatment suits a counting question; other questions may need a much shorter record.
