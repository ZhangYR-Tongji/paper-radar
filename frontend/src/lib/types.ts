export type Classification =
  | "Highly Relevant"
  | "Worth Checking"
  | "Low Priority"
  | "Filtered";

export type Paper = {
  id: number;
  score: number;
  classification: Classification;
  title: string;
  authors: string[];
  date: string | null;
  source: string;
  venue: string | null;
  abstract: string;
  matchedKeywordGroups: string[];
  matchedKeywords: string[];
  negativeKeywordHits: string[];
  rating: number | null;
  isSaved: boolean;
  isRead: boolean;
  isCore: boolean;
  isIgnored: boolean;
  personalNote: string;
  url: string | null;
  pdfUrl: string | null;
};

export type SourceConfig = {
  id: number;
  sourceName: string;
  displayName: string;
  description: string;
  isEnabled: boolean;
  dailyLimit: number;
  participatesInRanking: boolean;
  metadataOnly: boolean;
};

export type KeywordGroup = {
  id: number;
  name: string;
  description: string;
  isEnabled: boolean;
  priorityWeight: number;
  positiveKeywords: string[];
  negativeKeywords: string[];
  requiredKeywords: string[];
  optionalKeywords: string[];
};

export type FeedbackItem = {
  id: number;
  paperId: number;
  paperTitle: string;
  rating: number | null;
  positiveTags: string[];
  negativeTags: string[];
  note: string;
  updatedAt: string;
};

export type FetchRunItem = {
  id: number;
  sourceName: string;
  keywordGroupId: number;
  fetchFrom: string | null;
  fetchTo: string | null;
  status: string;
  rawResultCount: number;
  newPaperCount: number;
  duplicateCount: number;
  errorMessage: string | null;
};

export type FetchRun = {
  id: number;
  status: string;
  startedAt: string | null;
  finishedAt: string | null;
  requestedFrom: string | null;
  requestedTo: string | null;
  enabledSources: string[];
  enabledKeywordGroups: Array<{ id: number; name: string }>;
  totalRawResults: number;
  totalNewPapers: number;
  totalDuplicatePapers: number;
  totalScoredPapers: number;
  totalHighlyRelevant: number;
  totalLowPriority: number;
  errorCount: number;
  errorSummary: string | null;
  items: FetchRunItem[];
  papers: Paper[];
};

export type FeedbackPayload = {
  rating: number | null;
  positive_feedback_tags: string[];
  negative_feedback_tags: string[];
  is_saved: boolean;
  is_core: boolean;
  is_read: boolean;
  is_ignored: boolean;
  personal_note: string;
};
