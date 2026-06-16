export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api";

import type {
  FeedbackItem,
  FetchRun,
  FetchRunItem,
  KeywordGroup,
  Paper,
  SourceConfig,
} from "./types";

export type CitationExportFormat = "ris" | "bibtex";

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function apiSend<T>(
  path: string,
  method: "POST" | "PUT" | "DELETE",
  body?: unknown,
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) {
    const message = await parseErrorMessage(response);
    throw new Error(message || `API request failed: ${response.status}`);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

async function parseErrorMessage(response: Response): Promise<string> {
  const text = await response.text();
  if (!text) {
    return "";
  }
  try {
    const data = JSON.parse(text) as { detail?: unknown };
    if (typeof data.detail === "string") {
      return data.detail;
    }
  } catch {
    return text;
  }
  return text;
}

export type ApiPaper = Record<string, unknown>;

export function mapPaper(item: ApiPaper): Paper {
  return {
    id: Number(item.id),
    score: Number(item.score ?? 0),
    classification: String(item.classification ?? "Filtered") as Paper["classification"],
    title: String(item.title ?? ""),
    authors: (item.authors as string[]) ?? [],
    date: (item.published_date as string | null) ?? null,
    source: String(item.source ?? ""),
    venue: (item.venue as string | null) ?? null,
    abstract: String(item.abstract ?? ""),
    matchedKeywordGroups: (item.matched_keyword_groups as string[]) ?? [],
    matchedKeywords: (item.matched_positive_keywords as string[]) ?? [],
    negativeKeywordHits: (item.matched_negative_keywords as string[]) ?? [],
    rating: (item.rating as number | null) ?? null,
    isSaved: Boolean(item.is_saved),
    isRead: Boolean(item.is_read),
    isCore: Boolean(item.is_core),
    isIgnored: Boolean(item.is_ignored),
    personalNote: String(item.personal_note ?? ""),
    url: (item.url as string | null) ?? null,
    pdfUrl: (item.pdf_url as string | null) ?? null,
  };
}

export function mapSourceConfig(item: Record<string, unknown>): SourceConfig {
  return {
    id: Number(item.id),
    sourceName: String(item.source_name),
    displayName: String(item.display_name),
    description: String(item.description ?? ""),
    isEnabled: Boolean(item.is_enabled),
    dailyLimit: Number(item.daily_limit ?? 0),
    participatesInRanking: Boolean(item.participates_in_ranking),
    metadataOnly: Boolean(item.metadata_only),
  };
}

export function mapKeywordGroup(item: Record<string, unknown>): KeywordGroup {
  return {
    id: Number(item.id),
    name: String(item.name),
    description: String(item.description ?? ""),
    isEnabled: Boolean(item.is_enabled),
    priorityWeight: Number(item.priority_weight ?? 1),
    positiveKeywords: (item.positive_keywords as string[]) ?? [],
    negativeKeywords: (item.negative_keywords as string[]) ?? [],
    requiredKeywords: (item.required_keywords as string[]) ?? [],
    optionalKeywords: (item.optional_keywords as string[]) ?? [],
  };
}

export function mapFeedbackItem(item: Record<string, unknown>): FeedbackItem {
  return {
    id: Number(item.id),
    paperId: Number(item.paper_id),
    paperTitle: String(item.paper_title ?? ""),
    rating: (item.rating as number | null) ?? null,
    positiveTags: (item.positive_feedback_tags as string[]) ?? [],
    negativeTags: (item.negative_feedback_tags as string[]) ?? [],
    note: String(item.personal_note ?? ""),
    updatedAt: String(item.updated_at ?? ""),
  };
}

export function mapFetchRunItem(item: Record<string, unknown>): FetchRunItem {
  return {
    id: Number(item.id),
    sourceName: String(item.source_name),
    keywordGroupId: Number(item.keyword_group_id),
    fetchFrom: (item.fetch_from as string | null) ?? null,
    fetchTo: (item.fetch_to as string | null) ?? null,
    status: String(item.status),
    rawResultCount: Number(item.raw_result_count ?? 0),
    newPaperCount: Number(item.new_paper_count ?? 0),
    duplicateCount: Number(item.duplicate_count ?? 0),
    errorMessage: (item.error_message as string | null) ?? null,
  };
}

export function mapFetchRun(item: Record<string, unknown> | null): FetchRun | null {
  if (!item) {
    return null;
  }
  return {
    id: Number(item.id),
    status: String(item.status),
    startedAt: (item.started_at as string | null) ?? null,
    finishedAt: (item.finished_at as string | null) ?? null,
    requestedFrom: (item.requested_from as string | null) ?? null,
    requestedTo: (item.requested_to as string | null) ?? null,
    enabledSources: (item.enabled_sources as string[]) ?? [],
    enabledKeywordGroups:
      (item.enabled_keyword_groups as Array<{ id: number; name: string }>) ?? [],
    totalRawResults: Number(item.total_raw_results ?? 0),
    totalNewPapers: Number(item.total_new_papers ?? 0),
    totalDuplicatePapers: Number(item.total_duplicate_papers ?? 0),
    totalScoredPapers: Number(item.total_scored_papers ?? 0),
    totalHighlyRelevant: Number(item.total_highly_relevant ?? 0),
    totalLowPriority: Number(item.total_low_priority ?? 0),
    errorCount: Number(item.error_count ?? 0),
    errorSummary: (item.error_summary as string | null) ?? null,
    items: ((item.items as Record<string, unknown>[]) ?? []).map(mapFetchRunItem),
    papers: ((item.papers as ApiPaper[]) ?? []).map(mapPaper),
  };
}

export function paperExportUrl(
  paperId: number,
  format: CitationExportFormat,
): string {
  return `${API_BASE_URL}/papers/${paperId}/export?format=${format}`;
}

export function libraryExportUrl(format: CitationExportFormat): string {
  return `${API_BASE_URL}/papers/export/library?format=${format}`;
}
