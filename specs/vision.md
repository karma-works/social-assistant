The system is an AI-powered social media orchestration platform built with LangChain and LangGraph.

Goal: automatically generate high-quality, honest, source-aware social media post suggestions for X and Bluesky based on:

* GitHub repositories
* personal homepage / portfolio
* shared tweets / reposts
* external research sources (papers, Hugging Face, blogs, docs)

The system uses multiple sub-agents:

* GitHub ingestion agent
* Website ingestion agent
* Social/repost ingestion agent
* Source resolver agent
* Summarization agent
* Draft/post generation agent
* Media generation agent
* Quality/eval agent

Core orchestration uses a ReAct-style agent inside LangGraph.

Important architectural principles:

* Never copy tweets or reposts verbatim.
* Always summarize external content in original wording.
* Prefer primary sources over tweets:

  * arXiv papers
  * Hugging Face
  * GitHub repos
  * official project websites
  * documentation
* Tweets are secondary references only.
* Avoid copyright risks and low-value reposting.

For personal projects:

* Communication must be honest and transparent.
* Explicitly mention if:

  * project is experimental
  * untested
  * early-stage
  * has no active users
  * has unknown traction
* Also mention real positive signals when available:

  * GitHub stars
  * releases
  * demos
  * community feedback
  * benchmarks
  * adoption metrics

The writing style must NOT be distilled from existing tweets.
Instead:

* use configurable master prompts / brand voice configs
* prompts should define:

  * tone
  * honesty constraints
  * anti-hype rules
  * formatting rules
  * platform-specific behavior
* prompts should be versioned like code

The system should enrich posts with media:

* screenshots
* diagrams
* architecture graphics
* code visualizations
* interactive graphics
* generated images

Workflow:

1. Detect new signals/content
2. Normalize and deduplicate
3. Resolve primary sources
4. Generate factual summary
5. Generate draft post
6. Generate media
7. Run quality gates/evals
8. Send human-in-the-loop approval request
9. Publish only after approval

Human approval flow:

* send proposal via email or Telegram
* user can approve/reject/edit/regenerate
* publishing only happens after explicit confirmation

Quality system requirements:

* factuality checks
* hallucination checks
* copyright/repost checks
* honesty checks
* source attribution checks
* style compliance checks
* platform constraint checks
* media relevance checks

The system should support automated evals with reusable test datasets.

Example eval categories:

* source attribution evals
* repost summarization evals
* anti-copying evals
* honesty evals
* hallucination evals
* style/master-prompt compliance evals
* platform formatting evals

Suggested stack:

* Python
* LangChain
* LangGraph
* FastAPI
* PostgreSQL
* pgvector/Qdrant
* Redis
* GitHub API
* X API
* Bluesky API
* Telegram Bot API
* email provider
* containerized deployment

Core philosophy:

* truthful over hype
* source-first over social-first
* summarization over copying
* human-approved automation
* configurable brand voice
* eval-driven development and QA
