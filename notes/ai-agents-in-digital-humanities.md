# Research: Current uses of AI agents in digital humanities

## Summary

The evidence base is real but still small. The strongest documented uses are not autonomous “AI humanists”; they are bounded, semi-autonomous systems for archival source discovery, text-to-code analysis, corpus-scale extraction, and multi-stage evidence synthesis, usually with human review. One system is internally deployed to 24 researchers, while several others have completed substantial corpus runs or benchmark evaluations; independent, long-term field evidence remains rare.

## Practical threshold and scope

For this brief, an **AI agent** must do more than generate a response. It must have an LLM-controlled loop that performs at least two of the following: (1) decomposes/plans a task, (2) selects and invokes external tools or executable code, (3) observes results and replans/retries, (4) coordinates specialized agents, or (5) persists workflow state toward a goal. Human approval may bound the workflow.

Accordingly, a chatbot, classifier, OCR model, embedding search, fixed RAG pipeline, or one-shot text-to-SQL/prompt is **not** an agent merely because its authors call it one. Agent-based historical simulations are also excluded: their simulated people/ships may be software “agents,” but they are a different methodological tradition from tool-using AI agents. The included cases concern recognizably DH activities—digitized archives, computational history, philology, cultural-heritage records, or digital architectural historiography—not generic humanities teaching or essay writing.

## Findings

### 1. TRACE — operational, accountable source discovery in French historical archives (May 22, 2026)

- **DH task/domain:** Finding evidence across OCR-noisy 1887 French parliamentary debates and newspapers for the DECIDON project on circulation of political discourse.
- **What the agent did:** A planner decomposes questions (up to four subquestions), targets corpora, and runs iterative search/review loops (up to 13 steps) over BM25, semantic, date/metadata, and grep tools. It accepts/holds/rejects chunks, writes briefings, replans, merges, and reranks results. This comfortably meets the threshold.
- **Status/evidence:** Internally deployed and accessible to **24 researchers at six partner institutions**. On **1,752** HistoriQA-ThirdRepublic questions, it achieved **Recall@10 0.856** and **MRR 0.653**, outperforming sparse, dense, graph, and agentic-RAG baselines; reported hosted cost was about **$0.02/question**. The implementation is released.
- **Limitations:** Preprint/working paper rather than mature longitudinal study; internal availability is not evidence of active use by all 24 researchers; results concern retrieval, not correctness of finished historical interpretations; prompts require corpus adaptation.
- **Sources:** [HAL/ISIDORE record and abstract](https://isidore.science/index.php/document/10670/1.d8cd1a1f9703fbe27cc0fbf8717d6322e513a6cf); [official repository and architecture](https://github.com/Kepler1908/TRACE).

### 2. Venice cadastre coding agent — executable historical urban analysis (published Oct. 1, 2025)

- **DH task/domain:** Natural-language exploration of Venice’s 1740 and 1808 cadastral records: property, population, land-use, spatial, and diachronic questions.
- **What the agent did:** The qualifying component is a LangChain-orchestrated **entity extractor → planner → coder** workflow. It maps concepts to three datasets, plans spatial/statistical/temporal operations, writes and executes Python, and debugs errors up to a retry limit. (The paper’s separate one-shot SQL generator plus majority vote is useful, but below this brief’s strict agent threshold.)
- **Status/evidence:** Peer-reviewed application on **34,000+ cadastral rows** and **240 expert-curated questions** (100 browsing, 140 complex). For the SQL adjunct, three-shot exact match was **79%**, unigram overlap **92%**, with no runtime errors. For the true coding agent, about **80–95%** of responses were fully repeatable across three runs depending on question type; however, manual review found **12 errors among 79** fully consistent answers (**15.2%**). It produced verifiable executable analyses such as correlations, chi-square tests, and cross-period comparisons.
- **Limitations:** An evaluated research framework, not documented public/production deployment. Consistency is not correctness; entity-name answers were only about **60%** fully consistent. Semantic drift, synonyms, historical terminology, and ambiguous entity mapping remain weaknesses; GPT-4 substantially outperformed Llama-3 70B.
- **Sources:** [Computational Humanities Research article](https://www.cambridge.org/core/journals/computational-humanities-research/article/llm-agents-for-interactive-exploration-of-historical-cadastre-data-framework-and-application-to-venice/9EF07CEC477F080CF329C301E74D4C51); [project code](https://github.com/dhlab-epfl/venice-agents).

### 3. Grounded intertextuality agent — completed corpus-scale classical Chinese analysis (July 30, 2026)

- **DH task/domain:** Detecting and classifying reuse of the *Analects* in the *Twenty-Four Histories*, including exact spans, quotation form, source marking, function, and stance.
- **What the agent did:** For each text pair, a tool-constrained LLM commits proposed reuse through a schema that verifies exact character spans, validates labels, deduplicates at write time, and permits abstention. It is less open-ended than TRACE, but qualifies through tool-mediated iterative commitments and validation rather than one-shot prose extraction.
- **Status/evidence:** A completed validate-then-scale study. Three experts produced an adjudicated benchmark of **2,533** intertextual pairs from **3,489** candidates; 12 models showed **56–93% precision**. The selected extractor then completed **65,380 comparisons** over about **28.5 million characters**, with **no failed tasks**, yielding **5,766 pairs** and a reported historical result: aggregate citation composition stayed stable while literal fidelity declined over eighteen centuries.
- **Limitations:** Very recent preprint; full-corpus precision was extrapolated from the *Book of Han* validation subset. At the selected model’s validated precision, the authors expect roughly **one in eight pairs to be spurious**. Expert agreement was strong for surface features but weaker for inferred function and stance, so those labels remain exploratory.
- **Source:** [arXiv paper](https://arxiv.org/html/2607.27595v1).

### 4. Eight-agent CIA archive workflow — completed extraction and narrative production (published Jan. 22, 2026)

- **DH task/domain:** Computational history of the 1968 Prague Spring and invasion using declassified CIA President’s Daily Briefs (1968–69).
- **What the agent did:** Eight specialized stages decomposed archive acquisition/processing, OCR-dependent text extraction, relevance and information extraction, summarization, entity work, thematic quantification, and narrative assembly. It produced a time-resolved historical account rather than only answering isolated prompts.
- **Status/evidence:** Peer-reviewed completed run over **2,122 pages**. Outputs were a comprehensive monthly summary, a structured key-entity list, and thematic content quantification. Four LLMs were compared; **GPT-5 obtained F1 0.731**, Claude Sonnet 4.5 was reported faster/more cost-efficient, and Claude and Grok had flawless operational stability in the study.
- **Limitations:** A conceptual/evaluated pipeline, not an ongoing service. The paper explicitly concludes that fully automated historical analysis is not yet credible and requires expert oversight. OCR errors propagate; lack of an API for the canonical CIA source harms long-term reproducibility; model/vendor comparisons will age quickly.
- **Sources:** [eScholarship record](https://escholarship.org/uc/item/6sb0915x); [publisher record](https://www.emerald.com/el/article/doi/10.1108/EL-06-2025-0272/1336865/A-multi-stage-agentic-AI-system-for-extracting); [institutional case report](https://update.lib.berkeley.edu/2026/01/26/international-collaboration-vse-prague-ut-austin-uc-berkeley-builds-agentic-ai-system-for-cia-foia-archives/).

### 5. ChatLoS v3 — provenance-aware exploration of Maryland’s Legacy of Slavery archive (published Feb. 2026)

- **DH task/domain:** Cross-collection inquiry in Maryland State Archives’ Legacy of Slavery records.
- **What the agent did:** It translates natural-language questions to Cypher, executes graph queries across three linked archival datasets, and synthesizes provenance-linked answers. This is a narrow, semi-agentic tool-execution workflow rather than a general research agent.
- **Status/evidence:** Applied prototype evaluated in structured sessions by **two Maryland State Archives archivists**. It linked John Howard across an 1829 sale advertisement, an 1830 manumission record, and an 1830 Certificate of Freedom, and returned the correct count (**78**) for a tested Dorchester County advertisement query. The paper reports correct aggregate counts in all test cases and higher archivist confidence due to visible queries and records.
- **Limitations:** Tiny expert sample and no published large quantitative benchmark or public usage statistics. “All test cases” is not meaningful without a reported test-set size. Entity normalization and knowledge-graph construction are prerequisites and can encode archival bias; the authors call for larger evaluation and bias mitigation.
- **Sources:** [Society of American Archivists paper](https://www2.archivists.org/sites/all/files/Gnanasekaran_Marciano_paper.pdf); [2025 SAA Research Forum listing](https://www2.archivists.org/am2025/research-forum-2025/agenda).

### 6. SPIRE — multi-agent evidence synthesis for classics (May 29, 2026)

- **DH task/domain:** Evidence-grounded interpretive essays over classical Chinese and Greco-Roman Latin primary texts.
- **What the agent did:** Seven role agents discover, annotate, compare, check provenance, sample, bind citations, synthesize an argument, and re-ground it for up to two reflection rounds over a shared EvidencePool and multi-scale text/graph/cluster store.
- **Status/evidence:** Implemented and evaluated, not deployed. Against a **406-paper** benchmark manually assembled by two graduate researchers, SPIRE recovered **44.3%** of cited primary-source evidence versus **≤22.4%** for the strongest baseline. On a blind 100-paper subset, two human and two LLM raters scored it higher across accuracy, depth, coverage, and evidence quality; raters preferred it to each baseline on at least **96/100** papers. Ablations showed every agent/retrieval tier contributed.
- **Limitations:** Preprint; recreating evidence from published papers is a proxy, not evidence that scholars used the system to produce new scholarship. Evidence recall remains below half, sentence-level recall was only **5.6%**, and latency was about **3×** text RAG. Two traditions/corpora limit generalizability; some judging relies on LLMs.
- **Source:** [arXiv paper](https://arxiv.org/html/2605.30947v1).

### 7. HistAgent — multimodal historical-reasoning benchmark system (May 26, 2025)

- **DH task/domain:** Source-grounded historical reasoning across manuscripts, images, inscriptions, audio/video, multiple languages, and scholarly literature.
- **What the agent did:** A manager decomposes questions, dispatches OCR, translation, web/archive search, literature retrieval, reverse-image, document, and media-analysis agents, verifies evidence, and assembles cited answers.
- **Status/evidence:** Implemented benchmark system, not a field deployment. On **414 expert-authored questions** spanning 29 languages, 20+ regions, and at least 36 subfields, GPT-4o HistAgent achieved **27.54% pass@1 / 36.47% pass@2**, above GPT-4o with online search (**18.60%**) and Open Deep Research-smolagents (**20.29% / 25.12%**). More than 40 historians and researchers contributed benchmark questions.
- **Limitations:** Success is relative: it still failed almost three quarters of tasks at pass@1. It supports general historical research and only partly overlaps DH; its DH relevance comes from computational processing of digitized, multimodal sources, not from documented adoption in a DH project. Benchmark gains are not evidence of completed scholarship or users.
- **Sources:** [arXiv record](https://arxiv.org/abs/2505.20246); [paper PDF](https://www.arxiv.org/pdf/2505.20246v2).

### 8. ODALC knowledge agent — operational architectural-history corpus access, but vendor-attested only (Jan. 21, 2026)

- **DH task/domain:** Search, comparison, concept clustering, co-occurrence mapping, and longitudinal study of Latin American architectural theory.
- **What the agent did:** A Dataiku RAG knowledge agent queries the corpus while orchestrated NLP workflows ingest and clean texts, extract keywords, cluster concepts, and track theoretical change. It is a borderline case: the self-service query agent appears tool-backed, but the public description does not establish how much planning/replanning is LLM-controlled versus fixed pipelines.
- **Status/evidence:** Reported operational research platform over **800+ multilingual articles**, with an **80% reduction in manual processing time** and access for faculty, students, and researchers.
- **Limitations:** All outcome evidence comes from Dataiku’s customer story; no methods paper, independent audit, user count, task definition for the 80% figure, or accuracy evaluation was found. Treat this as a credible deployment lead, not strong scientific evidence.
- **Source:** [Dataiku case study](https://www.dataiku.com/stories/blog/odalc).

## What was deliberately not counted

- **Ordinary RAG/chatbots:** KleioGPT, Prozhito “Talking to Data,” Ask Mona museum assistants, and most historical-character chatbots retrieve and answer but do not document agent-controlled planning/tool loops. They may be useful, but they are not evidence for agents under this threshold.
- **OCR/classification/embeddings:** Transkribus-style OCR, named-entity recognition, semantic search, and the DATS LLM Assistant automate DH tasks but do not independently plan and execute workflows.
- **Agent-based simulation:** MWGrid, Voyager, and correspondence-network ABMs are genuine computational humanities applications but simulate historical actors or vessels; they are not modern tool-using AI research agents.
- **Implemented but insufficiently attested:** Chronos (Aug. 11, 2026) clearly meets the architectural threshold—filesystem/UI/VLM tools, reusable skills, batch execution, validation, and provenance—but its technical progress report provides no user count or end-to-end quantitative evaluation of Chronos itself, so it is not promoted as a success case here. [Paper](https://arxiv.org/html/2604.03553v1); [repository](https://github.com/ai-historian/chronos).
- **Repositories and prototypes without independent outcomes:** EleutherIA, Kyber, MCP servers for digital scholarly editions/heritage records, and numismatic agents demonstrate working architectures, but public READMEs alone do not establish successful scholarly use.
- **Proposals/blueprints:** Museum “agent” design papers that only recommend an architecture or evaluation protocol were excluded.

## Synthesis

1. **Current success is strongest in bounded infrastructural tasks.** Retrieval (TRACE), executable data analysis (Venice), constrained annotation (intertextuality), and staged extraction (CIA) let agents act where steps and outputs can be inspected. There is little credible evidence for autonomous hypothesis formation and defensible end-to-end DH scholarship.
2. **Verification mechanisms matter more than conversational fluency.** The strongest systems expose source IDs, exact spans, Cypher/Python, provenance, abstention, or expert review. Ordinary chatbot UX is not evidence of reliable DH work.
3. **Operational evidence is much weaker than benchmark evidence.** TRACE’s 24-researcher internal deployment is the clearest scholarly-use claim. ODALC supplies an operational metric but only through a vendor. Most other cases are completed experiments, not sustained services with measured users.
4. **“Successful” remains qualified.** Venice produced stable wrong answers; intertextuality expects about 12.5% spurious pairs; SPIRE recovers under half of cited evidence; HistAgent pass@1 is 27.54%. These are useful research aids, not replacements for historians, philologists, archivists, or curators.

## Sources

### Kept

- [TRACE paper record](https://isidore.science/index.php/document/10670/1.d8cd1a1f9703fbe27cc0fbf8717d6322e513a6cf) and [repository](https://github.com/Kepler1908/TRACE) — deployment, benchmark, and inspectable agent loop.
- [Karch et al., Computational Humanities Research (2025)](https://www.cambridge.org/core/journals/computational-humanities-research/article/llm-agents-for-interactive-exploration-of-historical-cadastre-data-framework-and-application-to-venice/9EF07CEC477F080CF329C301E74D4C51) — peer-reviewed real-data evaluation with error analysis.
- [Beyond Similarity (2026)](https://arxiv.org/html/2607.27595v1) — completed corpus-scale run plus expert adjudication.
- [Zahorak et al., The Electronic Library (2026)](https://escholarship.org/uc/item/6sb0915x) — completed archival pipeline and outputs.
- [Gnanasekaran & Marciano, SAA (2026)](https://www2.archivists.org/sites/all/files/Gnanasekaran_Marciano_paper.pdf) — applied archival prototype with professional archivist evaluation.
- [SPIRE (2026)](https://arxiv.org/html/2605.30947v1) — explicit multi-agent DH evaluation and ablations.
- [HistBench/HistAgent (2025)](https://arxiv.org/abs/2505.20246) — domain-agent benchmark with concrete comparative results.
- [ODALC/Dataiku (2026)](https://www.dataiku.com/stories/blog/odalc) — operational use and scale claim, retained with vendor-evidence warning.

### Dropped

- Ask Mona, Casa Batlló, and similar museum vendor stories — operational chatbots, but insufficient evidence of planning/tool-execution loops and mostly visitor service rather than DH research.
- *Talking to Data* / Prozhito and KleioGPT — evaluated RAG assistants, not agents under the stated threshold.
- MWGrid, Voyager, and historical correspondence ABMs — agent-based modeling, a materially different use of “agent.”
- EpiAgent, Oracle Bone multi-agent interpretation, VaseMuseum, and several 2026 repositories — promising evaluations or implementations, but adding them would broaden into cultural-heritage computer vision without improving the central evidence about actual DH use.
- Generic humanities essay scoring, teaching chatbots, and role-playing characters — humanities applications, not digital-humanities research workflows.

## Gaps

No comprehensive registry tracks agent deployment in DH. Public evidence rarely reports active users, frequency of use, longitudinal accuracy, downstream scholarly publications, labor saved under a defined protocol, or independent reproduction. The next useful research step would be to interview the six DECIDON partners and ODALC, audit interaction logs and completed scholarly outputs, and seek independent reproductions of the Venice, CIA, intertextuality, and SPIRE results. Until then, claims that AI agents are “currently transforming” DH should be treated cautiously.
