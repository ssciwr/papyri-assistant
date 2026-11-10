---
name: answer-review
description: Review a drafted answer before it goes to the user, checking that every claim states its evidence and every cited document is linked. Use once an answer that makes claims about papyri, documents, dates, places, people or counts is drafted. Research reports are reviewed with the report-review skill instead.
license: MIT
metadata:
  version: 0.1
---

# Answer review

The review decides whether a drafted answer may go to the user. It asks closed questions about an answer already written: whether each claim states the evidence behind it, whether that evidence supports it, and whether each cited document is linked. It does not answer the question itself.

An answer goes through at most four review rounds. The **round** is 1 for the first review, and one more for each review after a revision.

## Evidence in the answer

The answer carries its own evidence, so the user can check every claim from its text. Evidence is what the database returned: the documents a claim rests on, linked, with what each shows (date, place, a quoted reading); and for a count, what was counted and how. A claim with its evidence only in your context, not in the answer, has no evidence for the user.

## Steps

1. **Review the answer** by the checks and rules below, and write the verdict block. Read the answer as the user will, who has only its text: judge what it says, not what you meant it to say.
2. **Act on the verdict** by the table under "Verdicts". On `fail`, revise the answer: add or retrieve the missing evidence, correct or remove the problematic parts of the answer, and fix the links. Then review the revised answer as the next round, starting with the previous problems.

## Checks

Judge the answer on these questions, in this order:

1. **Evidence stated.** Does every claim about papyri, documents, dates, places, people or counts state its evidence in the answer? General background is acceptable when the answer labels it as such and no claim about the documents rests on it.
2. **Support.** Does the stated evidence support its claim? A claim that goes further than its evidence is an issue to be reported, even when it is plausible. Evidence about one name, date range or place does not support a claim about another automatically, even if the names are the same.
3. **Strength.** Does the answer overstate what the evidence shows?
4. **The question asked.** Does the answer address the question that was asked, or a narrower one that happens to be easier?
5. **Links.** Does every document the answer cites carry a markdown link, built from the document's DDbDP or DCLP id, or from its Trismegistos id if it has neither, as retrieved from the database? Links must lead to the documents they claim to link to, and must be relevant to the claim under scrutiny.
6. **Previous issues.** From round 2 on, is each previous issues resolved?

### Rules

- **Negative findings are answers.** An answer that reports it found nothing is right when it says what was searched.
- **Your knowledge is not evidence.** Judge each claim only against the evidence the answer states.
- **Name every problem before fixing any.** Quote each problem sentence and say what is wrong with it; the revision in step 2 writes the fixes.

## Verdict

Write the verdict in this block:

```markdown
Round: <n>
Verdict: <pass or fail>
Previous issues:
- <previous issues>: <resolved or not resolved, and why>
Issues:
- "<the problem sentence>": <what is wrong with it>
```

The verdict is `pass` when no problem remains, and `fail` otherwise.

## Verdicts

| Verdict | Round | What the user receives |
|---|---|---|
| `pass` | any | the answer |
| `fail` | 1 to 3 | nothing yet; the answer is revised and reviewed again |
| `fail` | 4 | the answer, preceded by a note that it did not pass review and naming the problems that remain |

## Acceptance criteria

- Every claim of the answer has been checked for stated evidence and against it, and every cited document for its link.
- From round 2 on, every previous problem is marked resolved or not resolved.
- Every problem quotes its sentence and says what is wrong with it.
- The verdict is `pass` only when no problem remains, and the user receives what the table under "Verdicts" says.
