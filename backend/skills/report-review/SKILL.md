---
name: report-review
description: Review a written research report and decide whether it goes to the user. Use once a report has been written.
license: MIT
metadata:
  version: 0.1
allowed-tools: write_todos, read_file, write_file, grep, list_sql_tables, inspect_sql, query_sql, similarity_search, mmr_search
---

# Report review

The review decides whether a report may go to the user. It checks the report against the acceptance criteria of report writing and research, follows its arguments, checks the integrity of the research, cross-checks the load-bearing claims against the database, and acts as the report's devil's advocate.

Read the report with fresh eyes, as a reader who has not seen the research. The user will have only the report, so judge only what the report and the database show. If you took part in the research, set aside what you remember of it.

## Issues

An **issue** is anything that affects whether the answer is correct, grounded, complete or followable. The review reports issues and nothing else. For each issue it names what must change and why; the researcher or the report writer makes the change.

## Input and output

Input: the report `/scratchpad/report-<topic>.md`, and every earlier review file of this report (`/scratchpad/review-<topic>-<round>.md`). The research record `/scratchpad/research-<topic>.md` may be consulted to find the exact query behind a step you cross-check; the review judges the report, not the record.

The **round** is 1 if there is no earlier review file, and otherwise one more than the highest earlier round.

Output: the review file `/scratchpad/review-<topic>-<round>.md`, and one of three verdicts, returned as a label with the file paths:

| Verdict | When | What the user receives in the chat |
|---|---|---|
| `accepted` | no issue remains | the full text of the report |
| `revise` | issues remain, in rounds 1–4 | nothing yet; the report goes back for revision |
| `rejected` | issues remain in round 5, after four revisions | the rejection reason, then the full text of the report, then the unresolved issues |

The paths are for the agents that pass the work on. The user works in a chat and sees only what is written into it, so what reaches the user is always the content of the files.

## Workflow

1. **Read the report and the earlier review files,** and plan the checks with `write_todos`.
2. **From round 2 on, check the previous issues first.** Mark each one resolved or not resolved, with the reason.
3. **Check the report criteria** (see "Report criteria").
4. **Follow every argument** (see "Following the arguments").
5. **Check research integrity** for the whole report (see "Research integrity").
6. **Cross-check the load-bearing claims** (see "Cross-checks").
7. **Play devil's advocate** (see "Devil's advocate").
8. **Decide the verdict** by the table under "Input and output", and write the review file.

## Report criteria

Check the report against the acceptance criteria of the report-writing skill ([../report-writing/SKILL.md](../report-writing/SKILL.md)) and the readiness criteria of the papyrological-research skill ([../papyrological-research/SKILL.md](../papyrological-research/SKILL.md)) that affect the report. Judge whether the checks are appropriate to the conclusions: coverage checks for counts or complete lists, plausible alternatives for load-bearing interpretations, and source criticism of the features each claim depends on. Do not require a fixed number of search routes, a separate falsification search for every claim, or irrelevant source checks. A missing check is an issue when it leaves a material risk to the answer unresolved, not merely because it was omitted.

These criteria check that the report contains what it must. The checks below test whether what it contains holds.

## Following the arguments

For every argument, check:

- **Steps**: does the reasoning lead from the evidence to the claim with every step stated?
- **Strength**: is the claim no stronger than its evidence, and does its stated certainty match the evidence and the uncertainties named?
- **Circularity**: does the evidence already presuppose the claim, for example criteria derived from the very documents they are then used to select?
- **Synthesis**: does each claim on the main question build on the claims it names, and does the summary say no more than the findings?
- **Repeatability**: is each step of the methods described well enough to be repeated?

## Research integrity

- **Grounding**: database findings, figures, quotations and document-specific assertions have retrieved evidence behind them. Background knowledge and interpretive hypotheses are clearly labeled and not presented as verified sources or database findings. If a conclusion depends on an unverified premise, check that it is appropriately qualified; labeling alone does not establish the premise.
- **Whole evidence**: the evidence against a claim is given wherever the methods found any, and every document is presented with what it shows against the claim as well as for it.
- **Counting**: counts are of distinct papyri, or say that they count records or texts.
- **Faithful interpretation**: the interpretation is faithful to the user's question, and the answer answers the question as interpreted.

## Cross-checks

Cross-checks are targeted: they cover the three kinds below, and the rest of the research is trusted to its described methods. Record every cross-check in the review file with its query and result.

- **Sources**: verify with one query over all cited Trismegistos ids that every cited document exists, and compare its date, place and edition with its reference entry.
- **Load-bearing claims**: every claim on the main question, and every claim whose failure would change the answer, such as the claim that carries a count. Repeat or reconstruct at least one step behind each, and compare the result with the report.
- **Readings**: for every quotation or reading an argument turns on, read the document's text, and its `xml_content` for supplied text, and confirm it says what the report says.

## Devil's advocate

Try to break the answer. For every claim on the main question, consider at least one other reading of the question and one other explanation of the evidence.

- **Other readings of the question** that the interpretation did not list, and that would change the answer.
- **Other explanations of the evidence**: could the same documents support a different claim? A formula may record a convention rather than a practice; a date may fit several events; an absence may reflect what survived rather than what happened.
- **Counter-evidence the research did not look for**: a search route not used, a variant of a term, a period, place or language left out. Where you suspect such a gap, run one search and record it.
- **Unexamined assumptions**: anything the report treats as established without evidence.

An alternative is an issue when it is plausible on the evidence and the report neither considers it nor rules it out. Its required change asks the research to test it.

## Review file

Write the review file in this structure, whatever the verdict:

```markdown
# Review: <report title>, round <n>

Report: /scratchpad/report-<topic>.md
Verdict: <accepted, revise or rejected>

## Rejection reason
<only when rejected, written for the user: why the report cannot be accepted, which issues remain unresolved after four revisions, and what they mean for how far the answer can be relied on>

## Previous issues
- Round <n-1>, issue <m>: <resolved or not resolved, and why>

## Issues
### Issue <m>: <the problem in one sentence>
- Where: <section, finding or reference number>
- Kind: <report criterion, argument, integrity, cross-check or alternative>
- Problem: <what is wrong, and why it matters for the answer>
- Evidence: <the criterion it fails, the passage, or the query and its result>
- Required change: <what must change>
- Goes to: <research, if new or repeated searches are needed; report writing, if the research record already supports the change>

## Cross-checks
- <claim checked>: <query>, <result>, <agrees or disagrees with the report>

## Alternatives considered
- <claim on the main question>: <the other reading or explanation, and whether the report covers it>
```

## Acceptance criteria

- From round 2 on, every previous issue is marked resolved or not resolved.
- Every report criterion has been checked, every argument followed, and the integrity of the whole report checked.
- Every cited source has been verified, and every load-bearing claim has been cross-checked with at least one recorded query.
- For every claim on the main question, at least one other reading of the question and one other explanation of the evidence are recorded under "Alternatives considered".
- Every issue states where it is, what is wrong, the evidence, the required change, and where it goes.
- The verdict follows the table under "Input and output", and a rejection reason is written for the user when the verdict is `rejected`.
