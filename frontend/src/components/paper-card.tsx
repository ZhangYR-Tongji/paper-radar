import { Bookmark, CheckCircle2, ExternalLink, FileText, Star } from "lucide-react";

import type { Paper } from "@/lib/types";

const classificationStyles: Record<Paper["classification"], string> = {
  "Highly Relevant": "bg-emerald-100 text-emerald-800",
  "Worth Checking": "bg-blue-100 text-blue-800",
  "Low Priority": "bg-amber-100 text-amber-800",
  Filtered: "bg-zinc-100 text-zinc-700",
};

export function PaperCard({ paper }: { paper: Paper }) {
  return (
    <article className="rounded-md border border-zinc-200 bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0 flex-1">
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <span className="rounded-md bg-zinc-950 px-2.5 py-1 text-sm font-semibold text-white">
              {paper.score}
            </span>
            <span
              className={`rounded-md px-2.5 py-1 text-xs font-semibold ${classificationStyles[paper.classification]}`}
            >
              {paper.classification}
            </span>
            <span className="text-sm text-zinc-500">
              {paper.source} · {paper.date}
            </span>
          </div>
          <h2 className="text-lg font-semibold leading-7 text-zinc-950">
            {paper.title}
          </h2>
          <p className="mt-1 text-sm text-zinc-500">
            {paper.authors.join(", ")} · {paper.venue}
          </p>
          <p className="mt-3 line-clamp-3 text-sm leading-6 text-zinc-700">
            {paper.abstract}
          </p>
        </div>
        <div className="flex shrink-0 flex-wrap gap-2 lg:w-44 lg:justify-end">
          <button className="inline-flex size-9 items-center justify-center rounded-md border border-zinc-200 bg-white text-zinc-600 hover:bg-zinc-50">
            <Star size={16} aria-label="评分" />
          </button>
          <button className="inline-flex size-9 items-center justify-center rounded-md border border-zinc-200 bg-white text-zinc-600 hover:bg-zinc-50">
            <Bookmark size={16} aria-label="保存" />
          </button>
          <button className="inline-flex size-9 items-center justify-center rounded-md border border-zinc-200 bg-white text-zinc-600 hover:bg-zinc-50">
            <CheckCircle2 size={16} aria-label="已读" />
          </button>
        </div>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        {paper.matchedKeywordGroups.map((group) => (
          <span
            key={group}
            className="rounded-md bg-teal-50 px-2.5 py-1 text-xs font-medium text-teal-800"
          >
            {group}
          </span>
        ))}
        {paper.matchedKeywords.map((keyword) => (
          <span
            key={keyword}
            className="rounded-md bg-indigo-50 px-2.5 py-1 text-xs font-medium text-indigo-800"
          >
            {keyword}
          </span>
        ))}
        {paper.negativeKeywordHits.map((keyword) => (
          <span
            key={keyword}
            className="rounded-md bg-rose-50 px-2.5 py-1 text-xs font-medium text-rose-800"
          >
            {keyword}
          </span>
        ))}
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <a
          href={paper.url ?? "#"}
          className="inline-flex h-9 items-center gap-2 rounded-md border border-zinc-200 px-3 text-sm font-medium text-zinc-700 hover:bg-zinc-50"
        >
          <ExternalLink size={15} aria-hidden="true" />
          原文
        </a>
        {paper.pdfUrl ? (
          <a
            href={paper.pdfUrl}
            className="inline-flex h-9 items-center gap-2 rounded-md border border-zinc-200 px-3 text-sm font-medium text-zinc-700 hover:bg-zinc-50"
          >
            <FileText size={15} aria-hidden="true" />
            PDF
          </a>
        ) : null}
      </div>
    </article>
  );
}
