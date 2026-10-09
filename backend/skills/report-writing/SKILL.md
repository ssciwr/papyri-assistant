---
name: report-writing
description: Write the final research report answering a user's papyrological question. Use once the research is done and the findings must be written up for the user.
license: MIT
metadata:
  version: 0.2
allowed-tools: write_todos, read_file, write_file, grep, edit_file, task, query_sql
---

# Report writing

The report is a structured presentation of the user's question and how it was interpreted, the workflow and methods used to answer it, the reasoning that led to the answer (or why several answers remain possible, or no conclusion can be reached), the alternatives that were rejected, and a closing summary.

The reasoning is set out as **arguments**. An argument is a claim, the evidence for and against it, and the reasoning that leads from the evidence to the claim, set out so the reader can retrace every step and check every source.

The report presents the research record; it adds no new evidence or unsupported conclusions. Database findings, figures and sources come from the record's retrieved evidence. Background knowledge and interpretive hypotheses may be used as the record labels them, not promoted into verified facts. A point the record leaves open stays open in the report.

## Input and output

Input: the research record `/scratchpad/research-<topic>.md`, written with the papyrological-research skill. It holds the user's question and its interpretation with the sub-questions, the steps of the research, the claims with the evidence for and against them, the alternatives, the gaps, and the verified sources.

If there is no research record, or it lacks any of these:
- When you were handed the task by another agent, return a list of the missing items instead of a report.
- Otherwise, complete the research with the papyrological-research skill first.

In a revision round, the input also includes the review file `/scratchpad/review-<topic>-<round>.md`. Address every issue that goes to report writing. Issues that go to research are resolved in the research record first; then write the report from the updated record.

Output: the report at `/scratchpad/report-<topic>.md`, with the same `<topic>` as the research record, in the structure below. Hand it to review with the report-review skill.

## Workflow

1. Plan the report sections with `write_todos`.
2. Verify every source you will cite: confirm with `query_sql` that it exists in the database, and check its entry in the record's Sources table.
3. Write the report in the structure below.
4. Check the draft against the acceptance criteria, and revise until every criterion is met.

## Structure

1. **Question and approach**: Restate the user's question and how it was interpreted, including any revisions, and list the sub-questions. Then summarize in a few sentences how it was researched.
2. **Methods and sources**: Name the corpora and tools used. Describe the workflow step by step, and say where a step limits what the evidence can show.
3. **Findings**: One argument per claim in the record, grouped by sub-question, with the claims on the main question last. For each one:
   - State the claim.
   - Give the supporting evidence and any relevant contrary evidence, with references. If none was found or a check was not performed, say so where it matters; do not manufacture opposition to straightforward observations.
   - Assess the aspects of the sources that affect the claim, following the record's source criticism. Discuss date, place, reading, semantics, authorial purpose or edition history where relevant, rather than requiring every category for every source.
   - Give the reasoning from the evidence to the claim.
   - State how certain the claim is.
4. **Alternatives**: Other answers that were considered, and why each was rejected or remains open. If the evidence does not decide between answers, say so and explain why.
5. **Summary**: A short answer to the question, stating how certain it is, and what the database could not answer (the record's gaps).
6. **References**: A numbered list that matches the in-text citations, taken from the record's Sources table. Each entry gives the Trismegistos id, edition, title, date, place and link, and the institution that currently holds the material where the database records it.

## Acceptance criteria

- The user's question is answered directly.
- Every claim in the record appears as an argument, and every argument comes from a claim in the record.
- Every argument has supporting evidence, any relevant contrary evidence or limitations, reasoning the reader can retrace, and a stated certainty.
- Every sub-question is addressed: answered by an argument, or named as unanswered with the reason.
- Uncertainties in the evidence are named wherever they weaken or strengthen an argument.
- Where several answers remain possible, or no conclusion is drawn, the report says so and explains why.
- Methods, workflow and tools are described step by step.
- Every cited source has been verified to exist, and its reference entry includes available metadata, with unavailable fields marked as not recorded.
- Every finding, figure, source and interpretive premise comes from the research record, preserving the distinction between retrieved evidence, background knowledge and hypotheses.

## Examples

Both examples answer the question "How many Libelli from the persecution of Christians under Decius are preserved?". Read them before writing your first report.

- [references/good-report-example.md](references/good-report-example.md): a report that meets every acceptance criterion.
- [references/bad-report-example.md](references/bad-report-example.md): a report that fails them, followed by a list of its faults.
