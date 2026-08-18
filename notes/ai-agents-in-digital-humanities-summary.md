# AI Agents in Digital Humanities: Current Reported Uses

_As of August 2026_

## Summary

There are genuine uses of AI agents in digital humanities, but the evidence base remains small. The strongest systems are bounded research assistants for archival retrieval, text-to-code analysis, corpus-scale extraction, provenance-aware querying, and evidence synthesis—not autonomous historians or humanists.

Here, an **AI agent** means a system that does more than generate a response: it plans or decomposes work, invokes tools or executable code, inspects results, retries or replans, coordinates specialized components, or maintains workflow state. Ordinary RAG chatbots, OCR, classifiers, embeddings, and one-shot prompting are excluded.

## Strongest reported cases

### 1. TRACE: historical archive search

TRACE searches OCR-degraded French parliamentary debates and newspapers. It decomposes research questions, selects corpora and retrieval tools, evaluates documents iteratively, replans, and returns traceable sources.

- Internally deployed in the DECIDON project
- Accessible to **24 researchers across six institutions**
- Evaluated on **1,752 historical questions**
- Recall@10: **0.856**; MRR: **0.653**
- Approximate hosted cost: **$0.02 per question**

This is the clearest example found of an agent available to a working DH research consortium.

Sources: [paper record](https://isidore.science/index.php/document/10670/1.d8cd1a1f9703fbe27cc0fbf8717d6322e513a6cf), [implementation](https://github.com/Kepler1908/TRACE)

### 2. Venice cadastral agent: executable historical analysis

EPFL researchers built an agent for Venice's 1740 and 1808 cadastral records. It extracts relevant entities, plans an analysis, generates and executes Python, and debugs failures.

- Tested on **34,000+ cadastral records**
- Benchmark of **240 expert-written questions**
- Produced inspectable statistical, spatial, and cross-period analyses
- Roughly **80–95%** of results were repeatable, depending on question type

Repeatability did not guarantee correctness: manual inspection found **12 errors among 79 fully consistent answers**.

Sources: [peer-reviewed article](https://www.cambridge.org/core/journals/computational-humanities-research/article/llm-agents-for-interactive-exploration-of-historical-cadastre-data-framework-and-application-to-venice/9EF07CEC477F080CF329C301E74D4C51), [code](https://github.com/dhlab-epfl/venice-agents)

### 3. Classical Chinese intertextuality extraction

A tool-constrained agent detected and classified reuse of the *Analects* across the *Twenty-Four Histories*.

- Expert-adjudicated benchmark: **2,533** accepted pairs
- Full run: **65,380 comparisons** over approximately **28.5 million characters**
- Produced **5,766 intertextual pairs** with no failed tasks
- Supported a historical finding about declining literal quotation fidelity over eighteen centuries

The authors estimate that approximately **one result in eight may be spurious**, so aggregate patterns are more trustworthy than individual records.

Source: [paper](https://arxiv.org/html/2607.27595v1)

### 4. CIA archive workflow

An eight-stage workflow processed declassified CIA President's Daily Briefs concerning the 1968 Prague Spring and invasion.

- Processed **2,122 pages**
- Performed extraction, relevance classification, entity analysis, summarization, thematic quantification, and narrative assembly
- Produced monthly summaries, entity lists, and thematic results
- Best reported model reached **F1 0.731**

This was a completed archival analysis, although the researchers concluded that expert oversight remained necessary.

Sources: [publication record](https://escholarship.org/uc/item/6sb0915x), [publisher](https://www.emerald.com/el/article/doi/10.1108/EL-06-2025-0272/1336865/A-multi-stage-agentic-AI-system-for-extracting), [institutional report](https://update.lib.berkeley.edu/2026/01/26/international-collaboration-vse-prague-ut-austin-uc-berkeley-builds-agentic-ai-system-for-cia-foia-archives/)

### 5. ChatLoS: provenance-aware archival exploration

ChatLoS v3 queries linked Maryland State Archives *Legacy of Slavery* datasets. It generates and executes Cypher queries and returns answers connected to underlying records.

Reported tests included linking a person across sale, manumission, and freedom-certificate records and correctly returning **78** records for an aggregate query. Two professional archivists evaluated it, but the sample and reported test set were very small.

Sources: [SAA paper](https://www2.archivists.org/sites/all/files/Gnanasekaran_Marciano_paper.pdf), [SAA Research Forum](https://www2.archivists.org/am2025/research-forum-2025/agenda)

### 6. SPIRE: multi-agent evidence gathering

SPIRE uses seven agents to discover passages, annotate and compare them, check provenance, bind citations, and compose evidence-grounded arguments over classical Chinese and Latin texts.

- Evaluated against **406 peer-reviewed papers**
- Recovered **44.3%** of cited primary-source evidence, versus at most **22.4%** for the strongest baseline
- In a blind 100-paper evaluation, raters preferred SPIRE to each baseline in at least **96 cases**

This is a substantial benchmark evaluation, but not yet evidence of routine scholarly adoption.

Source: [paper](https://arxiv.org/html/2605.30947v1)

## What agents are currently useful for

Reported successes cluster around:

1. Archival source discovery across noisy collections.
2. Text-to-code analysis of structured historical data.
3. Constrained extraction and annotation at corpus scale.
4. Multi-stage document processing with inspectable intermediate results.
5. Provenance-aware graph querying across linked collections.
6. Evidence gathering and citation binding.

The common success factor is **inspectability**: source identifiers, exact spans, executable Python or Cypher, provenance links, validation rules, abstention, and expert review.

## Conclusion

AI agents are producing useful DH infrastructure and completed corpus analyses, but most evidence still comes from one-off evaluations or preprints. Longitudinal usage, independent reproduction, and agent-assisted scholarly publications remain uncommon.

The defensible conclusion is therefore:

> **AI agents are becoming effective assistants for bounded, verifiable digital-humanities workflows—not autonomous digital humanists.**
