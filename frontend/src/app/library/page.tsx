"use client";

import { Download } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { PageHeader } from "@/components/page-header";
import { PaperCard } from "@/components/paper-card";
import {
  apiGet,
  apiSend,
  libraryExportUrl,
  mapPaper,
  type ApiPaper,
} from "@/lib/api";
import type { FeedbackPayload, Paper } from "@/lib/types";

const filters = [
  { label: "全部", value: "all" },
  { label: "文献库", value: "saved" },
  { label: "重点文献", value: "core" },
  { label: "已读", value: "read" },
] as const;
const PAGE_SIZE = 50;

export default function LibraryPage() {
  const [papers, setPapers] = useState<Paper[]>([]);
  const [activeFilter, setActiveFilter] = useState<(typeof filters)[number]["value"]>("all");
  const [hasMore, setHasMore] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const requestId = useRef(0);

  const loadLibrary = useCallback(async (offset = 0) => {
    const currentRequest = ++requestId.current;
    if (offset === 0) setIsLoading(true);
    else setIsLoadingMore(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        filter: activeFilter,
        limit: String(PAGE_SIZE),
        offset: String(offset),
      });
      const data = await apiGet<ApiPaper[]>(`/papers/library?${params.toString()}`);
      if (currentRequest !== requestId.current) return;
      setPapers((current) =>
        offset === 0 ? data.map(mapPaper) : [...current, ...data.map(mapPaper)],
      );
      setHasMore(data.length === PAGE_SIZE);
    } catch (err) {
      if (currentRequest === requestId.current) {
        setError(err instanceof Error ? err.message : "加载文献库失败");
      }
    } finally {
      if (currentRequest === requestId.current) {
        setIsLoading(false);
        setIsLoadingMore(false);
      }
    }
  }, [activeFilter]);

  useEffect(() => {
    loadLibrary();
  }, [loadLibrary]);

  const updateFeedback = async (paperId: number, payload: FeedbackPayload) => {
    await apiSend(`/papers/${paperId}/feedback`, "PUT", payload);
    await loadLibrary();
  };

  return (
    <>
      <PageHeader
        title="文献库"
        description="入库文献、重点文献和已读记录会汇总到这里。"
        action={
          papers.length ? (
            <div className="flex flex-wrap gap-2">
              <a
                className="inline-flex h-10 items-center gap-2 rounded-md border border-zinc-200 bg-white px-3 text-sm font-medium text-zinc-700 hover:bg-zinc-50"
                href={libraryExportUrl("ris")}
                title="导出文献库 RIS，可导入 Zotero"
              >
                <Download size={16} aria-hidden="true" />
                导出 RIS
              </a>
              <a
                className="inline-flex h-10 items-center gap-2 rounded-md border border-zinc-200 bg-white px-3 text-sm font-medium text-zinc-700 hover:bg-zinc-50"
                href={libraryExportUrl("bibtex")}
                title="导出文献库 BibTeX，可导入 Zotero"
              >
                <Download size={16} aria-hidden="true" />
                导出 BibTeX
              </a>
            </div>
          ) : null
        }
      />
      <div className="mb-4 flex flex-wrap gap-2">
        {filters.map((filter) => (
          <button
            key={filter.value}
            className={`h-9 rounded-md px-3 text-sm font-medium ${
              activeFilter === filter.value
                ? "bg-zinc-900 text-white"
                : "border border-zinc-200 bg-white text-zinc-700 hover:bg-zinc-50"
            }`}
            onClick={() => setActiveFilter(filter.value)}
          >
            {filter.label}
          </button>
        ))}
      </div>
      {error ? <p className="mb-4 text-sm text-rose-700">{error}</p> : null}
      {isLoading ? (
        <div className="rounded-md border border-zinc-200 bg-white p-6 text-sm text-zinc-500">正在加载文献库...</div>
      ) : papers.length ? (
        <div className="space-y-4">
          {papers.map((paper) => (
            <PaperCard key={paper.id} paper={paper} onFeedback={updateFeedback} />
          ))}
        </div>
      ) : (
        <div className="rounded-md border border-zinc-200 bg-white p-6 text-sm text-zinc-500">
          暂无文献库记录。可在最新推荐中加入文献库、设为重点，或打开原文/PDF 形成已读记录。
        </div>
      )}
      {hasMore && !isLoading ? (
        <button className="mt-5 w-full rounded-md border border-zinc-200 bg-white p-3 text-sm font-medium hover:bg-zinc-50 disabled:text-zinc-400" disabled={isLoadingMore} onClick={() => loadLibrary(papers.length)}>
          {isLoadingMore ? "加载中..." : "加载更多"}
        </button>
      ) : null}
    </>
  );
}
