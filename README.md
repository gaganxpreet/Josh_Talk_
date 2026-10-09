# Josh Talks AI Product Task

**Evaluation design and product prototypes | July 2026**

This project builds two practical systems for evaluating AI work in Indian contexts: **Dukaan
Bench**, a text to image evaluation framework for small business creatives, and a **transcriber
quality review system** that turns task level behavior into a careful review workflow.

## What's Built

* **Q1: Dukaan Bench**. A focused benchmark design, Indic script prompt suite, generation harness,
  offline human rating tool, analysis pipeline, and interactive dashboard.
* **Q2: Transcriber quality**. Six behavioral quality signals, cohort aware analysis, a review
  queue, and an engineering response ladder with human review safeguards.

## Q1: Dukaan Bench

Dukaan Bench evaluates whether image models can create useful festival and offer posters for
Indian small businesses. It compares **OpenAI GPT Image 1**, **Google Gemini 2.5 Flash Image**,
and **Google Gemini 3.1 Flash Image Preview** using the same prompt set.

The 10 prompts cover six Indic scripts and include a matched English control. The evaluation
combines text fidelity, cultural authenticity, composition and usability, and a direct "would you
post it?" judgment. A **None of these** option captures cases where none of the outputs is
usable. Per script analysis makes differences visible that a single overall ranking can hide.

The repository includes:

* A prompt set with exact target strings and prompt level rationale
* A Python generation harness for API and manual workflows, with a provenance manifest
* An offline browser rating tool and rating protocol
* Analysis for Usable Poster Rate, Indic Text Penalty, confidence intervals, and inter rater reliability
* An interactive dashboard with script filtering and model comparisons
* A timed walkthrough outline

Start with the [one page report](Q1_dukaan_bench/02_ONE_PAGE_REPORT.md), then explore the
[main document](Q1_dukaan_bench/01_MAIN_DOCUMENT.md) and the
[dashboard prototype](Q1_dukaan_bench/dashboard/dukaan_bench_dashboard.html).

### Q1 workflow

The workflow moves from the prompt set through model generation, blinded human ratings,
analysis, and dashboard review.

Generation and rating details are in the
[manual workflow](Q1_dukaan_bench/generation/MANUAL_WORKFLOW.md) and
[rating protocol](Q1_dukaan_bench/rating/RATING_PROTOCOL.md).

## Q2: Transcriber Quality

Question 2 applies the same evaluation discipline to human transcription work. The analysis
tool derives behavioral indicators from task rows, summarizes distributions, compares workers
within language, device, and task cohorts, and produces a queue for review.

The system separates review signals from consequential decisions. Behavioral signals route
attention, while known answer checks and human review support high impact actions. The Python
tool reports review signals without emitting automated block recommendations.

Read the [warning sign analysis](Q2_transcriber_quality/01_PART_I_warning_signs.md) and
[detection system design](Q2_transcriber_quality/02_PART_II_detection_system.md). The Python
analysis tool accepts a task level CSV and can compare workers by language, device, and task
type.

## Shared Principle

Both projects define what quality means, then build measurement around the decisions the results
need to support. Dukaan Bench uses human judgment to compare model outputs. The transcriber
quality system uses behavioral evidence to route review and keeps high impact decisions grounded
in known answers and human judgment.
