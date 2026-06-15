import type { FeedbackItem, KeywordGroup, Paper, SourceConfig } from "./types";

export const latestFetchSummary = {
  id: 1,
  status: "partial_success",
  timeRange: "2026-03-18 至 2026-06-16",
  rawResults: 186,
  newPapers: 42,
  duplicates: 31,
  highlyRelevant: 8,
  errors: 1,
};

export const papers: Paper[] = [
  {
    id: 101,
    score: 88,
    classification: "Highly Relevant",
    title:
      "Human-AI Co-Creation for Early-Stage Conceptual Design: A Mixed-Methods Study",
    authors: ["M. Chen", "L. Garcia", "T. Fischer"],
    date: "2026-06-02",
    source: "OpenAlex",
    venue: "Design Studies",
    abstract:
      "This paper investigates how designers use generative AI support during early conceptual design tasks, focusing on cognition, task framing, and evaluation behavior.",
    matchedKeywordGroups: [
      "AI-assisted conceptual design",
      "Creativity support and Human-AI collaboration",
    ],
    matchedKeywords: ["conceptual design", "human-AI collaboration", "user study"],
    negativeKeywordHits: [],
    isSaved: true,
    isCore: true,
    url: "#",
    pdfUrl: "#",
  },
  {
    id: 102,
    score: 74,
    classification: "Worth Checking",
    title:
      "Graph-Based Design Rationale Capture in AI-Augmented Engineering Workflows",
    authors: ["A. Rossi", "Y. Wang"],
    date: "2026-05-21",
    source: "arXiv",
    venue: "arXiv preprint",
    abstract:
      "The work proposes a graph representation for design rationale capture and evaluates node-link interfaces for collaborative decision tracking.",
    matchedKeywordGroups: [
      "FBS / IBIS / Design Rationale",
      "Node-based and graph-based design tools",
    ],
    matchedKeywords: ["design rationale", "graph-based", "node-link"],
    negativeKeywordHits: ["too engineering"],
    isRead: false,
    url: "#",
    pdfUrl: "#",
  },
  {
    id: 103,
    score: 55,
    classification: "Low Priority",
    title: "Benchmarking Visual Generative Models for Product Concept Images",
    authors: ["S. Patel", "J. Kim"],
    date: "2026-04-18",
    source: "Semantic Scholar",
    venue: "CHI Extended Abstracts",
    abstract:
      "A benchmark of image-generation models for producing product concept visuals with emphasis on visual quality metrics.",
    matchedKeywordGroups: ["AI-assisted conceptual design"],
    matchedKeywords: ["product concept", "generative models"],
    negativeKeywordHits: ["too image-generation focused"],
    isSaved: false,
    url: "#",
  },
];

export const sourceConfigs: SourceConfig[] = [
  {
    id: 1,
    sourceName: "arxiv",
    displayName: "arXiv",
    description: "预印本元数据检索",
    isEnabled: true,
    dailyLimit: 100,
    participatesInRanking: true,
    metadataOnly: true,
  },
  {
    id: 2,
    sourceName: "openalex",
    displayName: "OpenAlex",
    description: "开放学术元数据索引",
    isEnabled: true,
    dailyLimit: 100,
    participatesInRanking: true,
    metadataOnly: true,
  },
  {
    id: 3,
    sourceName: "crossref",
    displayName: "Crossref",
    description: "DOI 与出版方元数据",
    isEnabled: true,
    dailyLimit: 100,
    participatesInRanking: true,
    metadataOnly: true,
  },
  {
    id: 4,
    sourceName: "semantic_scholar",
    displayName: "Semantic Scholar",
    description: "语义学者论文元数据",
    isEnabled: true,
    dailyLimit: 100,
    participatesInRanking: true,
    metadataOnly: true,
  },
  {
    id: 5,
    sourceName: "osf",
    displayName: "OSF Preprints",
    description: "OSF 预印本元数据",
    isEnabled: false,
    dailyLimit: 50,
    participatesInRanking: true,
    metadataOnly: true,
  },
];

export const keywordGroups: KeywordGroup[] = [
  {
    id: 1,
    name: "AI-assisted conceptual design",
    description: "早期概念设计、构思和 AI 辅助设计过程",
    isEnabled: true,
    priorityWeight: 1.2,
    positiveKeywords: ["AI-assisted design", "conceptual design", "design ideation"],
    negativeKeywords: ["image generation only"],
    requiredKeywords: ["design"],
    optionalKeywords: ["human-AI", "ideation"],
  },
  {
    id: 2,
    name: "Design cognition and reasoning",
    description: "设计认知、推理、决策和设计思维",
    isEnabled: true,
    priorityWeight: 1,
    positiveKeywords: ["design cognition", "design reasoning", "design thinking"],
    negativeKeywords: ["pure optimization"],
    requiredKeywords: ["design"],
    optionalKeywords: ["cognition", "reasoning"],
  },
  {
    id: 3,
    name: "FBS / IBIS / Design Rationale",
    description: "FBS、IBIS、设计理由和论证结构",
    isEnabled: true,
    priorityWeight: 1.1,
    positiveKeywords: ["FBS", "IBIS", "design rationale"],
    negativeKeywords: [],
    requiredKeywords: [],
    optionalKeywords: ["argumentation", "function behavior structure"],
  },
];

export const feedbackHistory: FeedbackItem[] = [
  {
    id: 1,
    paperTitle:
      "Human-AI Co-Creation for Early-Stage Conceptual Design: A Mixed-Methods Study",
    rating: 5,
    tags: ["method useful", "Human-AI collaboration related"],
    note: "可作为核心相关工作。",
    updatedAt: "2026-06-15 22:10",
  },
  {
    id: 2,
    paperTitle: "Benchmarking Visual Generative Models for Product Concept Images",
    rating: 2,
    tags: ["too image-generation focused"],
    note: "偏图像生成，和概念设计过程关系弱。",
    updatedAt: "2026-06-14 18:32",
  },
];
