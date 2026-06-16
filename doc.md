# CODEX_INSTRUCTIONS.md

## Project: Paper Radar

Build a local-first web app for finding and ranking new academic papers across research fields.

No LLM in this phase. Do not use OpenAI API, local LLMs, LangChain, automatic summarization, or PDF full-text analysis.

Core goal:

```text
User configures sources + keyword groups
↓
User manually clicks Fetch
↓
System searches papers published since last successful fetch
↓
System deduplicates, scores, classifies, and displays papers
↓
User rates papers
↓
System updates preference weights for future ranking
```

## 1. Tech Stack

Use this stack unless repo already has another reasonable setup:

```text
Frontend: Next.js + React + TypeScript + Tailwind CSS
Backend: Python FastAPI + SQLAlchemy + Pydantic
Database: PostgreSQL; SQLite acceptable for local dev if schema stays compatible
```

No background-only cron required for MVP. Manual fetch is the main mechanism.

## 2. Core Principles

```text
Configuration over hardcoding
Manual fetch over background daemon
Incremental fetch over daily-only fetch
Explainable scoring over black-box model
Failure recovery over perfect automation
```

Do not hardcode keyword groups, sources, or scoring weights in fetch logic. Read them from database.

## 3. Pages

Implement these pages:

```text
/                       Latest Recommendations
/settings               Source + keyword + scoring configuration
/library                Saved / read / core papers
/feedback               Rating history
/search                 Local database search
/fetch-runs/[id]        Fetch run details
```

## 4. Configurable Data Sources

Support source configs for:

```text
arXiv
OpenAlex
Crossref
Semantic Scholar
OSF Preprints
```

Each source has:

```text
source_name
display_name
description
is_enabled
daily_limit
participates_in_ranking
metadata_only
last_success_at
last_error_at
last_error_message
```

Manual fetch must only call sources where `is_enabled = true`.

Implement source adapters under:

```text
backend/app/sources/
  base.py
  arxiv_adapter.py
  openalex_adapter.py
  crossref_adapter.py
  semantic_scholar_adapter.py
  osf_adapter.py
```

Each adapter exposes:

```python
class BaseSourceAdapter:
    source_name: str

    def search(self, query: str, limit: int, date_from=None, date_to=None) -> list[PaperResult]:
        pass
```

If one adapter fails, log the error and continue other sources.

## 5. Configurable Keyword Groups

Keyword groups are user-editable in Settings.

Fields:

```text
id
name
description
is_enabled
priority_weight
positive_keywords
negative_keywords
required_keywords
optional_keywords
related_tags
created_at
updated_at
```

User must be able to:

```text
enable / disable group
create group
edit group
delete group
edit positive keywords
edit negative keywords
edit required keywords
edit optional keywords
set priority weight
clear local keyword groups
```

Keyword editing can use textarea, one keyword per line.

## 6. Manual Incremental Fetch

Main fetch mode: manual-first incremental fetch.

User clicks:

```text
Start Fetch / 开始检索新论文
```

System fetches papers from the time range:

```text
fetch_to = now
fetch_from = last_successful_until - overlap_buffer_days
```

Default:

```text
overlap_buffer_days = 3
first_run_lookback_days = 90
```

Do not use only one global `last_fetch_time`.

Maintain cursor per:

```text
source_name × keyword_group_id
```

Reason: if arXiv succeeds but OSF fails, OSF cursor must not update.

Only update cursor when that specific source × keyword group succeeds.

## 7. Fetch Tables

Create `fetch_cursors`:

```text
id
source_name
keyword_group_id
last_successful_until
last_run_id
last_status
last_error_message
created_at
updated_at
```

Create `fetch_runs`:

```text
id
trigger_type              # manual / scheduled
status                    # running / success / partial_success / failed
started_at
finished_at
requested_from
requested_to
overlap_buffer_days
enabled_sources
enabled_keyword_groups
total_raw_results
total_new_papers
total_duplicate_papers
total_scored_papers
total_highly_relevant
total_low_priority
error_count
error_summary
created_at
updated_at
```

Create `fetch_run_items`:

```text
id
fetch_run_id
source_name
keyword_group_id
fetch_from
fetch_to
status
raw_result_count
new_paper_count
duplicate_count
error_message
started_at
finished_at
created_at
updated_at
```

## 8. Manual Fetch API

Implement:

```text
POST /api/fetch/manual
GET  /api/fetch/status
GET  /api/fetch/runs
GET  /api/fetch/runs/{run_id}
```

`POST /api/fetch/manual` body:

```json
{
  "mode": "since_last_success",
  "source_names": [],
  "keyword_group_ids": [],
  "date_from": null,
  "date_to": null,
  "overlap_buffer_days": 3
}
```

Rules:

```text
If source_names empty, use all enabled sources.
If keyword_group_ids empty, use all enabled keyword groups.
If mode = since_last_success, use fetch_cursors.
If mode = custom_range, use date_from and date_to.
Prevent duplicate fetch jobs while one is running.
```

## 9. Manual Fetch Flow

Implement `run_manual_fetch()`:

```text
1. Reject if another fetch is running
2. Create fetch_run with status = running
3. Load enabled sources
4. Load enabled keyword groups
5. For each source × keyword group:
   a. Read fetch_cursor
   b. Compute fetch_from and fetch_to
   c. Generate query from keyword group
   d. Call source adapter
   e. Normalize metadata
   f. Filter by published_date / updated_date
   g. Deduplicate
   h. Save new papers
   i. Score new papers
   j. Write fetch_run_item
   k. If success, update fetch_cursor
6. Update fetch_run summary
7. Mark run as success / partial_success / failed
```

If a source × keyword group fails, do not update its cursor.

## 10. Paper Model

Create `papers`:

```text
id
title
normalized_title
abstract
authors
published_date
updated_date
source
source_id
doi
arxiv_id
url
pdf_url
venue
journal
conference
year
created_at
updated_at
```

Normalize source result into this shape:

```text
title
abstract
authors
published_date
updated_date
source
source_id
doi
arxiv_id
url
pdf_url
venue
journal
conference
year
```

## 11. Deduplication

Deduplicate by priority:

```text
1. DOI exact match
2. arXiv ID exact match
3. normalized_title exact match
4. title similarity > 0.92 using rapidfuzz
5. title similarity + overlapping authors
```

Because fetch uses overlap buffer, repeated results are expected. Do not treat duplicates as errors.

## 12. Scoring

Create `scoring_weights`:

```text
id
topic_weight
method_weight
venue_weight
freshness_weight
user_preference_weight
negative_filter_weight
updated_at
```

Default:

```text
topic_weight = 0.30
method_weight = 0.20
venue_weight = 0.15
freshness_weight = 0.15
user_preference_weight = 0.10
negative_filter_weight = 0.10
```

Create `paper_features`:

```text
id
paper_id
matched_keyword_groups
matched_positive_keywords
matched_negative_keywords
topic_tags
method_tags
venue_score
topic_score
method_score
freshness_score
user_preference_score
negative_filter_penalty
final_score
classification
created_at
updated_at
```

Final score:

```text
Final Score =
topic_score * topic_weight
+ method_score * method_weight
+ venue_score * venue_weight
+ freshness_score * freshness_weight
+ user_preference_score * user_preference_weight
- negative_filter_penalty * negative_filter_weight
```

Disabled keyword groups must not contribute to score.

Classify papers:

```text
Highly Relevant: final_score >= 80
Worth Checking: 60 <= final_score < 80
Low Priority: 40 <= final_score < 60
Filtered: final_score < 40
```

Default list should show Highly Relevant + Worth Checking first. Low Priority collapsed. Filtered hidden unless user selects filter.

## 13. Feedback

Create `user_feedback`:

```text
id
paper_id
rating                  # 1-5
positive_feedback_tags
negative_feedback_tags
is_saved
is_core
is_read
is_ignored
personal_note
created_at
updated_at
```

Create `user_preferences`:

```text
id
keyword_weights
venue_weights
method_weights
topic_weights
negative_keyword_weights
updated_at
```

User can:

```text
rate 1-5
save / unsave
mark read / unread
mark core
ignore
select positive tags
select negative tags
add personal note
```

Rating meaning:

```text
5 = must read / core
4 = worth reading
3 = maybe useful
2 = weak relation
1 = not relevant
```

Feedback tags:

Positive:

```text
theory useful
method useful
metrics useful
related work useful
writing structure useful
dataset useful
benchmark useful
review useful
implementation useful
domain background useful
```

Negative:

```text
out of scope
too application-specific
too theoretical
too engineering
too clinical
too algorithmic
no empirical evidence
weak method
abstract not relevant
duplicate recommendation
```

Implement:

```text
update_user_preferences_after_feedback(paper_id, feedback)
```

Simple rules:

```text
Rating 5:
- increase matched keyword weights
- increase matched keyword group weight slightly
- increase venue weights
- increase method tag weights

Rating 1:
- decrease matched keyword weights
- increase negative keyword weights
- increase penalty for selected negative tags
```

No ML model required.

## 14. Settings API

Implement:

```text
GET    /api/settings/sources
PUT    /api/settings/sources/{id}

GET    /api/settings/keyword-groups
POST   /api/settings/keyword-groups
PUT    /api/settings/keyword-groups/{id}
DELETE /api/settings/keyword-groups/{id}
POST   /api/settings/keyword-groups/clear

GET    /api/settings/scoring-weights
PUT    /api/settings/scoring-weights
```

## 15. Paper / Feedback API

Implement:

```text
GET /api/papers
GET /api/papers/{paper_id}
GET /api/papers/latest
GET /api/papers/library

POST /api/papers/{paper_id}/feedback
PUT  /api/papers/{paper_id}/feedback
GET  /api/feedback/history
```

`GET /api/papers` supports filters:

```text
min_score
classification
source
keyword_group
is_saved
is_read
is_core
date_from
date_to
sort_by
```

## 16. UI Requirements

Use clean academic card UI. Default language Chinese for system labels. Keep paper title and abstract in original English.

Paper card shows:

```text
score
classification
title
authors
date
source
venue / journal / conference
abstract
matched keyword groups
matched keywords
negative keyword hits
rating control
library button
core paper button
original link
PDF link
```

Settings page must prioritize:

```text
Source enable/disable
Source daily limit
Keyword group enable/disable
Keyword group edit
Scoring weight edit
```

Latest Recommendations page should show:

```text
latest fetch summary
start fetch button
fetch status/progress
paper list from latest fetch run
filters for latest run / last 7 days / last 30 days / all unread
```

Fetch run detail page shows:

```text
run time range
enabled sources
enabled keyword groups
raw results
new papers
duplicates
highly relevant count
errors
source × keyword group item status
new paper list
```

## 17. Seed Data

On initialization, seed:

```text
source_configs
scoring_weights
empty user_preferences
```

Default enabled sources:

```text
arXiv
OpenAlex
Crossref
Semantic Scholar
```

Default disabled source:

```text
OSF Preprints
```

Do not seed keyword groups. Users define keyword groups in Settings, and the local database reloads them on the next start.

## 18. Development Order

Follow this order:

```text
1. Project scaffold
2. Database models + migrations
3. Seed default sources / scoring weights
4. Settings APIs
5. Settings frontend
6. Source adapter interface
7. Implement arXiv + OpenAlex first
8. Implement Crossref + Semantic Scholar
9. Implement manual fetch flow
10. Implement deduplication
11. Implement scoring + classification
12. Implement Latest Recommendations page
13. Implement feedback + preference update
14. Implement Library page
15. Implement Fetch run detail page
16. Implement Search page
17. Polish errors, loading states, and logs
```

## 19. MVP Acceptance Criteria

MVP is complete when:

```text
User can enable / disable sources
User can create / edit / delete keyword groups
User can change keyword group weights
User can click a button to fetch papers manually
System fetches incrementally since last successful cursor
System maintains cursor per source × keyword group
Failed source does not update cursor
System uses overlap buffer to prevent missing delayed papers
System deduplicates repeated papers
System scores and classifies papers
Latest page shows newest recommendations sorted by score
User can rate papers 1-5
User can add papers to library, mark core papers, auto-mark read when opening original/PDF, ignore
Feedback updates user preferences
Library page shows saved/core/read papers
Fetch run page shows success/failure details
```

## 20. Do Not Implement Yet

Do not implement in MVP:

```text
LLM summary
LLM recommendation reason
PDF full-text analysis
automatic literature review
Zotero sync
Notion sync
WeChat push
background-only cron
complex ML ranking
multi-user accounts
```

Focus on local-first, manual, reliable, configurable paper search and ranking.
