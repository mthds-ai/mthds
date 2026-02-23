---
description: "MTHDS is an open standard for defining, packaging, and sharing AI methods — giving agents the ability to discover and execute structured, composable AI workflows."
---

# Overview

AI workflows today are written in code that domain experts cannot read, described in prompts that carry no structure, or wired together in automation platforms not designed for cognitive work. MTHDS bridges these approaches: a typed, declarative language for AI methods that is readable by domain experts, validatable by engineers, and executable by agents.

MTHDS (pronounced "methods") is an open standard for defining, packaging, and distributing AI methods. It provides a typed language for describing what an AI should do, with what inputs, and what outputs to produce — all in plain-text files that humans and machines can read alike.

Here is what a `.mthds` file looks like:
**cv_match.mthds**
```toml
domain = "cv_match"
description = "Matching CVs with job offers and generating interview questions"
main_pipe = "analyze_cv_job_match_and_generate_questions"

[concept.MatchAnalysis]
description = """
Analysis of alignment between a candidate and a position, including strengths, gaps, and areas requiring further exploration.
"""

[concept.MatchAnalysis.structure]
strengths = { type = "text", description = "Areas where the candidate's profile aligns well with the requirements", required = true }
gaps = { type = "text", description = "Areas where the candidate's profile does not meet the requirements or lacks evidence", required = true }
areas_to_probe = { type = "text", description = "Topics or competencies that need clarification or deeper assessment during the interview", required = true }

[concept.Question]
description = "A single interview question designed to assess a candidate."
refines = "Text"

[pipe.analyze_cv_job_match_and_generate_questions]
type = "PipeSequence"
description = """
Takes a CV and a job offer, extracts their content, analyzes strengths and gaps, \
and generates 5 targeted interview questions.
"""
inputs = { cv = "Document", job_offer = "Document" }
output = "Question[5]"
steps = [
    { pipe = "extract_documents_parallel", result = "extracted_documents" },
    { pipe = "analyze_match", result = "match_analysis" },
    { pipe = "generate_interview_questions", result = "interview_questions" },
]
```

***Concepts*** carry business meaning directly — `ContractClause`, `CandidateProfile`, `Joke` — and ***Pipes*** read as declarative intent: "given this input, produce that output." Domain experts can read a `.mthds` file without programming skills.

The standard has two pillars. **The Language** lets you define typed data and transformations in `.mthds` files — plain text, version-controllable, readable by anyone on the team. A single file works on its own, no setup required. **The Package System** adds distribution: give your methods an identity, declare dependencies, control visibility, and share them across projects and organizations.

<div class="grid cards" markdown>

-   **Learn the Language**

    Concepts, pipes, domains — everything you need to write `.mthds` files.

    [:octicons-arrow-right-24: The Language](language/bundles.md)

-   **Read the Specification**

    The normative reference for file formats, validation rules, and resolution algorithms.

    [:octicons-arrow-right-24: Specification](spec/mthds-format.md)

-   **Get Started**

    Set up your editor and write your first method in a few steps.

    [:octicons-arrow-right-24: Write Your First Method](getting-started/first-method.md)

</div>
