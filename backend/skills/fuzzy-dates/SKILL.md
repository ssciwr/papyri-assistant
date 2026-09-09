---
name: fuzzy-dates
description: Map fuzzy natural language date descriptions to precise date ranges
---

# fuzzy-dates

## When to use this skill

If the prompt mentions dates and date ranges that cannot be uniquely mapped to
a lower and upper bound.

## Workflow

Apply these example conventions:

- 5th century CE: `0401..0500`
- beginning 5th century CE: `0401..0425`
- middle 5th century CE: `0426..0475`
- end 5th century CE: `0476..0500`
- 5th century BCE: `-0500..-0401`
- beginning 5th century BCE: `-0500..-0476`
- middle 5th century BCE: `-0475..-0426`
- end 5th century BCE: `-0425..-0401`
