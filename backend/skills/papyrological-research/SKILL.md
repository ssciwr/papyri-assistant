---
name: papyrological-research
description: Investigate an interpreted complex papyrological research question using the database, record the evidence and reasoning, and write the final research report. Use once the research question has been interpreted or when you have to revise an existing research report.
license: MIT
metadata:
  version: 0.4
allowed-tools: write_todos, read_file, write_file, edit_file, grep, task, list_sql_tables, get_table_semantics, query_sql, similarity_search, mmr_search
---

# Papyrological research

Investigate the user's question, following the evidence rather than a fixed sequence of checks. Start from the question-interpretation file generated using the question-interpretation skill and leave a research record from which you write the final report: what you found, how you found it, why it supports your conclusions, what remains uncertain and how certain and precise the used records are on the content inquestion.

The aim is a useful, defensible answer, not an exhaustive audit of the database. Scale the research to the question and the strength of the claims you make. Be thorough where a mistake would change the answer; keep routine checks and notes brief.

## Input and output

Input: `/scratchpad/interpretation-<topic>.md`, which contains the input question, it's sub questions and useful axis of evidence. If there is none, use the question-interpretation skill first.

In a revision round, also read `/scratchpad/review-<topic>-<round>.md`, which has been generated using the report-review skill, and address research issues in the existing record.

Output: `/scratchpad/research-<topic>.md`, using the same `<topic>` as the interpretation file. Keep the sections under "Research record" so the report writer can find the findings and their support. When the record is ready, write the report from it as described in "Ready for report writing".

## Research approach

1. **Establish the question.** Read the question interpretation and start the record with the question, scope and sub-questions. Identify which uncertainties actually affect the answer.
2. **Orient in the database.** Use the search-database skill ([../search-database/SKILL.md](../search-database/SKILL.md)) for every database search. It explains how to read the semantic catalog, choose search routes and avoid counting and reading pitfalls. Do not duplicate work that's described there if you already have retrieved what you need before.
3. **Search and inspect.** Choose the route you consider most likely to find useful evidence given your current context and your knowledge. Inspect promising documents and refine vocabulary, dates, places or classifications as needed. Use additional search routes when it offers a meaningful check for a preliminary result or is likely to give new evidence.
5. **Develop and test answers.** Form provisional claims as the evidence develops. For conclusions the answer depends on, consider plausible alternatives and look for evidence that could change them or falsify them.
6. **Assess the sources.** Check the features each claim depends on, using "Source criticism" below. Distinguish what a document records from what you infer, and record material uncertainty together with the affected claim.
7. **Synthesize and answer.** Answer the main question from the findings, including tensions, limits of the evidence and uncertainties. Verify cited documents, assemble their source entries, and check whether the record supports the proposed answer.
8. **Write research report.** Present the record to the user as a report whose findings are arguments the reader can retrace: each claim with its evidence for and against, the source criticism it depends on, the reasoning and its certainty, together with the methods used, the alternatives considered and what remains unanswered. The report adds no new evidence; see "Ready for report writing" below.

Points 1. through 7. are recurring activities, not gates. You can search, interpret, check and synthesize in whatever order helps answer the question.

### Choosing depth and stopping

Stop when you can give a supported answer at the requested depth and further searches are unlikely to change it materially. Also stop or narrow the claim when the database cannot resolve a remaining uncertainty. Record what was not checked rather than continuing indefinitely or treating a partial answer as a failure. If the user gives a time or scope limit, prioritize the conclusions most important according to the input question document and state the parts that have been left out.

## Sub-questions, claims and revisions
Treat answers suggested by currently known evidence as provisional while researching. Keep, revise or reject them as you learn more. Record significant changes and plausible competing answers, but do not manufacture alternatives or counter-evidence for straightforward observations.

The question interpretation documnet is a starting point, not a fixed frame. If the evidence exposes a shifting term, an unsuitable scope or a missing sub-question, record the revision and its reason in the research record. Leave the original interpretation file intact. Tell the user if the revision materially changes what their question is taken to mean.

## Search routes

The search-database skill describes the possible search routes and how to use them. For research, agreement between routes helps, but shared metadata or editorial assumptions can make apparently different searches less independent than they seem. When routes disagree, investigate discrepancies that could affect your answer. An exploratory search does not require resolving every unmatched hit.

You may delegate independent sub-questions or routes to sub-agents. Ask for the findings, exact consequential queries, relevant result counts, Trismegistos ids, uncertainties and limitations so you can integrate their evidence without rerunning the work.

## Source criticism

Criticism should follow the claim: examine the aspects that could change the conclusion, not every possible property of every document. A metadata inventory does not require the same close reading as an argument about a restored phrase.

- **Date:** precise, certain, approximate or palaeographic?
- **Place:** written, found, acquired, sent or received where? how certain and precise?
- **Reading:** preserved wording or editorial restoration? Note fragmentary evidence.
- **Orthography and semantics:** could spelling variants affect retrieval? Does the term have the same meaning in this period and context? Compare relevant parallels where useful.
- **Author and purpose:** what can this genre and writer reasonably establish? Different genres like petitions, official reports or private letters have their particular purposes; a statement in one is not automatically proof that the event occurred as described, but might rather reflect subjective agendas, knowledge or interpretations of events.
- **Edition and research history:** check available revisions where they affect a reading or attribution. Do not imply you have checked anything the database does not provide.
- **Treating uncertainty:** Explain uncertainties that affect the answer and frame your answer taking into account this evidence strength. If competing evidence lead to the same conclusion, a brief note is enough.

## Grounding and interpretation

Database findings, counts, quotations and document-specific assertions must be supported by retrieved evidence. Read that evidence as the database-content-interpretation skill ([../database-content-interpretation/SKILL.md](../database-content-interpretation/SKILL.md)) describes. Verify documents with `query_sql` before citing them; semantic hits and remembered examples are leads, not verified sources. Never invent a source, quotation, figure or bibliographic detail.

Use your linguistic and historical knowledge to choose searches, understand documents and propose explanations where the interpetation of the user's question you received is not enough. It may appear in the record as explicitly labeled background knowledge or an interpretive hypothesis, with its basis and uncertainty. Where a conclusion depends on such an assumption, seek supporting evidence or qualify the conclusion. Labeling it as such is not a substitute for verification, so do not skip the verification step.

If the question needs unavailable external scholarship, identify that limit and the kind of source needed. Still offer a qualified database-based answer rather than withholding all interpretation.

## Inference along different axes of evidence

Use the interpretation's evidence axes to notice relevant reasoning risks, not as a checklist for unrelated checks. The following gives examplesf or how to work with different axes. The axes listed are not exclusive or exhaustive.

- **Temporal:** a date compatible with an event does not itself link the document to that event. Uneven survival limits comparisons of frequencies. If frequency matters, consider an appropriate corpus baseline; even normalized shares are not automatically historical rates.
- **Material:** distinguish records, texts and physical objects. Define the unit in a count and account for duplicates. The database is not all published papyrology; avoid treating a database total as the total preserved. Uncertain classifications may also prevent a count from being a firm lower bound.
- **Relational:** shared names do not establish identity, and co-occurrence does not establish a relationship. Look for contextual links.
- **Semantic:** meanings change across periods and genres. Conventional formulae may show how something was represented rather than what actually happened, or give context to the wider interaction the document is a part of.

Indirect evidence can support historical interpretations. Say what connects it to the proposed event or institution, why that explanation is plausible, and what alternatives remain. Reserve direct attribution for explicit links in the evidence.

## Synthesis

Use the interpretation's synthesis plan as a guide. Explain how the sub-question findings combine into an answer, rather than merely listing them. Where they pull in different directions, weigh the evidence taking into account their uncertainty and say why they are relevant. Where a sub-question remains unanswered, explain whether it limits the main conclusion or only a secondary detail.

## Research record

Keep a concise working notebook as you go, or after a coherent batch of searches. Preserve the queries and results needed to reproduce consequential findings, including negative searches that affect the answer. Routine lookups can be grouped; large results and candidate inventories can live in linked files. Do not copy every raw tool response into the record, but keep the parts that are relevant for reproducibility and the final answer.

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

Fill each source entry from the database. Build the link to the papyri.info edition from the document's DDbDP or DCLP id, or to Trismegistos if it has neither. Batch verification is fine, and previously retrieved SQL evidence can serve as verification without another identical query. Missing metadata is a limitation to report, not something to fill from memory or a reason to withhold an otherwise useful source.

[references/example-research-record.md](references/example-research-record.md) illustrates a detailed investigation of "How many Libelli from the persecution of Christians under Decius are preserved?". Consult it for query and record examples, not as a minimum workload or a source of current counts. Its exhaustive candidate treatment suits a counting question; other questions may need a much shorter record.

## Ready for report writing

The following criteria concern the reliability and usefulness of the handover, not the number of steps or the length of the notebook.

- The record answers the user's question as interpreted, or gives a useful partial answer with explicit limits.
- Consequential searches and findings are traceable; counts have a defined unit, criteria and coverage limits.
- The conclusions that matter have appropriate checks for alternatives, omissions or uncertain readings. The checks are chosen for their value, not their number.
- Claims have evidence, reasoning and a justified certainty; contrary evidence and material uncertainty are not hidden.
- The main answer follows from the findings. Unanswered sub-questions and significant revisions are visible.
- Cited documents have SQL verification and source entries; unavailable metadata is marked.
- Retrieved findings are distinguishable from background knowledge and hypotheses. Unverified external scholarship is not presented as checked evidence.

## Writing the report

The report presents the final research record: the question and its interpretation, how it was researched, the reasoning that led to the answer (or why several answers remain possible, or none can be reached), the rejected alternatives and a summary. Set out the reasoning as **arguments**: a claim, the evidence for and against it, and the reasoning from the evidence to the claim, so the reader can retrace every step and check every source.

Findings, figures and sources come from the record's retrieved evidence. Background knowledge and interpretive hypotheses keep the labels the record gives them, and a point the record leaves open stays open in the report. New evidence goes into the record first.

Write the report to `/scratchpad/report-<topic>.md` and hand it to review with the report-review skill. In a revision round, resolve the review's research issues in the record first, then address every report issue and rewrite the report from the updated record.

Structure:

1. **Question and approach**: the user's question, its interpretation including revisions, the sub-questions, and a few sentences on how it was researched.
2. **Methods and sources**: the corpora and tools, and the workflow step by step, saying where a step limits what the evidence can show.
3. **Findings**: arguments per claim in the record, grouped by sub-question, with the claims on the main question last. Each argument states the claim; gives the supporting and relevant contrary evidence with references, saying where it matters that none was found or a check was not performed; assesses the source features the claim depends on (date, place, reading, semantics, authorial purpose, edition history); gives the reasoning; and states the certainty.
4. **Alternatives**: other answers considered and why each was rejected or remains open. If the evidence does not decide between them, say so and why.
5. **Summary**: a short answer to the question with its certainty, and what the database could not answer (the record's gaps).
6. **References**: a numbered list matching the in-text citations, taken from the record's Sources table: Trismegistos id, edition, title, date, place, link and the institution currently holding the material, with unavailable fields marked as not recorded.

The report is finished when:

- The user's question is answered directly; where several answers remain possible or no conclusion is drawn, the report explains why.
- Every claim in the record appears as an argument, and every argument comes from a claim in the record.
- Every argument has evidence, relevant contrary evidence or limitations, reasoning the reader can retrace and a stated certainty, with the uncertainties named wherever they weaken or strengthen it.
- Every sub-question is answered by an argument or named as unanswered with the reason.
- Every cited source is SQL-verified and has a reference entry.

Both examples answer "How many Libelli from the persecution of Christians under Decius are preserved?" from the example research record below. Read them before writing your first report.

- [references/good-report-example.md](references/good-report-example.md): a report that meets every criterion.
- [references/bad-report-example.md](references/bad-report-example.md): a report that fails them, followed by a list of its faults.

Hand it over to the report-review skill when you are done.

## Revising a reviewed report
Address the issues flagged by the reviewer one by one.
Run useful follow-up searches, revise flagged claims, or explain why a requested check is unavailable or would not resolve the issue. Do not repeat completed work merely to recreate the workflow. Write directly to the existing report and hand it over to the report-review skill again when you are done.
