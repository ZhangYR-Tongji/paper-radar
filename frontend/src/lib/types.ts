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
  date: string;
  source: string;
  venue: string;
  abstract: string;
  matchedKeywordGroups: string[];
  matchedKeywords: string[];
  negativeKeywordHits: string[];
  isSaved?: boolean;
  isRead?: boolean;
  isCore?: boolean;
  url?: string;
  pdfUrl?: string;
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
  paperTitle: string;
  rating: number;
  tags: string[];
  note: string;
  updatedAt: string;
};
