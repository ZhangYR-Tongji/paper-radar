"use client";

import {
  Bookmark,
  ExternalLink,
  FileText,
  Star,
  StarOff,
  XCircle,
} from "lucide-react";

import type { FeedbackPayload, Paper } from "@/lib/types";

const classificationStyles: Record<Paper["classification"], string> = {
  "Highly Relevant": "bg-emerald-100 text-emerald-800",
  "Worth Checking": "bg-blue-100 text-blue-800",
  "Low Priority": "bg-amber-100 text-amber-800",
  Filtered: "bg-zinc-100 text-zinc-700",
};

export function PaperCard({
  paper,
  onFeedback,
}: {
  paper: Paper;
  onFeedback?: (paperId: number, payload: FeedbackPayload) => Promise<void>;
}) {
  const feedbackPayload = (patch: Partial<FeedbackPayload>): FeedbackPayload => ({
    rating: paper.rating,
    positive_feedback_tags: [],
    negative_feedback_tags: paper.negativeKeywordHits,
    is_saved: paper.isSaved,
    is_core: paper.isCore,
    is_read: paper.isRead,
    is_ignored: paper.isIgnored,
    personal_note: paper.personalNote,
    ...patch,
  });

  const submit = async (patch: Partial<FeedbackPayload>) => {
    if (!onFeedback) {
      return;
    }
    await onFeedback(paper.id, feedbackPayload(patch));
  };

  const markAsRead = () => {
    if (!paper.isRead) {
      void submit({ is_read: true });
    }
  };

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
              {paper.source} · {paper.date ?? "未知日期"}
            </span>
            {paper.isRead ? (
              <span className="rounded-md bg-zinc-100 px-2.5 py-1 text-xs font-medium text-zinc-600">
                已读
              </span>
            ) : null}
          </div>
          <h2 className="text-lg font-semibold leading-7 text-zinc-950">
            {paper.title}
          </h2>
          <p className="mt-1 text-sm text-zinc-500">
            {paper.authors.join(", ") || "Unknown authors"} ·{" "}
            {paper.venue ?? "Unknown venue"}
          </p>
          <p className="mt-3 line-clamp-3 text-sm leading-6 text-zinc-700">
            {paper.abstract}
          </p>
        </div>
        <div className="flex shrink-0 flex-col items-start gap-2 lg:w-[13rem] lg:items-end">
          <div className="grid grid-cols-5 gap-2" aria-label="论文评分">
            {[1, 2, 3, 4, 5].map((rating) => (
              <button
                key={rating}
                className={`inline-flex size-8 items-center justify-center rounded-md border text-xs font-semibold ${
                  paper.rating === rating
                    ? "border-amber-300 bg-amber-100 text-amber-800"
                    : "border-zinc-200 bg-white text-zinc-500 hover:bg-zinc-50"
                }`}
                onClick={() => submit({ rating })}
                title={`评分 ${rating}`}
              >
                {rating}
              </button>
            ))}
          </div>
          <div className="flex gap-2">
            <button
              className={`inline-flex size-9 items-center justify-center rounded-md border ${
                paper.isSaved
                  ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                  : "border-zinc-200 bg-white text-zinc-600 hover:bg-zinc-50"
              }`}
              onClick={() =>
                submit(
                  paper.isSaved
                    ? { is_saved: false, is_core: false }
                    : { is_saved: true },
                )
              }
              title={paper.isSaved ? "移出文献库" : "加入文献库"}
            >
              <Bookmark
                size={16}
                aria-label={paper.isSaved ? "移出文献库" : "加入文献库"}
              />
            </button>
            <button
              className={`inline-flex size-9 items-center justify-center rounded-md border ${
                paper.isCore
                  ? "border-amber-200 bg-amber-50 text-amber-700"
                  : "border-zinc-200 bg-white text-zinc-600 hover:bg-zinc-50"
              }`}
              onClick={() =>
                submit(
                  paper.isCore
                    ? { is_core: false }
                    : { is_core: true, is_saved: true },
                )
              }
              title={paper.isCore ? "取消重点文献" : "设为重点文献"}
            >
              <Star
                size={16}
                aria-label={paper.isCore ? "取消重点文献" : "设为重点文献"}
              />
            </button>
            <button
              className={`inline-flex size-9 items-center justify-center rounded-md border ${
                paper.isIgnored
                  ? "border-rose-200 bg-rose-50 text-rose-700"
                  : "border-zinc-200 bg-white text-zinc-600 hover:bg-zinc-50"
              }`}
              onClick={() => submit({ is_ignored: !paper.isIgnored })}
              title={paper.isIgnored ? "取消忽略" : "忽略"}
            >
              {paper.isIgnored ? (
                <XCircle size={16} aria-label="取消忽略" />
              ) : (
                <StarOff size={16} aria-label="忽略" />
              )}
            </button>
          </div>
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
          target="_blank"
          rel="noreferrer"
          onClick={paper.url ? markAsRead : undefined}
        >
          <ExternalLink size={15} aria-hidden="true" />
          原文
        </a>
        {paper.pdfUrl ? (
          <a
            href={paper.pdfUrl}
            className="inline-flex h-9 items-center gap-2 rounded-md border border-zinc-200 px-3 text-sm font-medium text-zinc-700 hover:bg-zinc-50"
            target="_blank"
            rel="noreferrer"
            onClick={markAsRead}
          >
            <FileText size={15} aria-hidden="true" />
            PDF
          </a>
        ) : null}
      </div>
    </article>
  );
}
