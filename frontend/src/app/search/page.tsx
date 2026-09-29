"use client";

import { Search } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { PageHeader } from "@/components/page-header";
import { PaperCard } from "@/components/paper-card";
import { apiGet, apiSend, mapPaper, type ApiPaper } from "@/lib/api";
import type { FeedbackPayload, Paper } from "@/lib/types";

const PAGE_SIZE = 50;

export default function SearchPage() {
  const [papers, setPapers] = useState<Paper[]>([]);
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [classification, setClassification] = useState("");
  const [hasMore, setHasMore] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const requestId = useRef(0);

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedQuery(query.trim()), 250);
    return () => window.clearTimeout(timer);
  }, [query]);

  const loadPapers = useCallback(async (offset = 0) => {
    const currentRequest = ++requestId.current;
    if (offset === 0) {
      setIsLoading(true);
    } else {
      setIsLoadingMore(true);
    }
    setError(null);
    const params = new URLSearchParams({
      limit: String(PAGE_SIZE),
      offset: String(offset),
    });
    if (classification) params.set("classification", classification);
    if (debouncedQuery) params.set("q", debouncedQuery);
    try {
      const data = await apiGet<ApiPaper[]>(`/papers?${params.toString()}`);
      if (currentRequest !== requestId.current) return;
      setPapers((current) =>
        offset === 0 ? data.map(mapPaper) : [...current, ...data.map(mapPaper)],
      );
      setHasMore(data.length === PAGE_SIZE);
    } catch (err) {
      if (currentRequest === requestId.current) {
        setError(err instanceof Error ? err.message : "搜索失败");
      }
    } finally {
      if (currentRequest === requestId.current) {
        setIsLoading(false);
        setIsLoadingMore(false);
      }
    }
  }, [classification, debouncedQuery]);

  useEffect(() => {
    loadPapers();
  }, [loadPapers]);

  const updateFeedback = async (paperId: number, payload: FeedbackPayload) => {
    await apiSend(`/papers/${paperId}/feedback`, "PUT", payload);
    await loadPapers();
  };

  return (
    <>
      <PageHeader title="本地搜索" description="在本地数据库中按标题、摘要、作者和标签检索。" />
      <div className="mb-5 flex flex-col gap-3 rounded-md border border-zinc-200 bg-white p-4 md:flex-row">
        <label className="relative flex-1">
          <Search
            className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400"
            size={18}
            aria-hidden="true"
          />
          <input
            className="h-11 w-full rounded-md border border-zinc-200 pl-10 pr-3 text-sm"
            placeholder="搜索 title / abstract / author / keyword"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </label>
        <select
          className="h-11 rounded-md border border-zinc-200 px-3 text-sm"
          value={classification}
          onChange={(event) => setClassification(event.target.value)}
        >
          <option value="">全部分类</option>
          <option>Highly Relevant</option>
          <option>Worth Checking</option>
          <option>Low Priority</option>
          <option>Filtered</option>
        </select>
      </div>
      {error ? <p className="mb-4 text-sm text-rose-700">{error}</p> : null}
      {isLoading ? (
        <div className="rounded-md border border-zinc-200 bg-white p-6 text-sm text-zinc-500">正在搜索...</div>
      ) : papers.length ? (
        <div className="space-y-4">
          {papers.map((paper) => (
            <PaperCard key={paper.id} paper={paper} onFeedback={updateFeedback} />
          ))}
        </div>
      ) : (
        <div className="rounded-md border border-zinc-200 bg-white p-6 text-sm text-zinc-500">
          没有匹配结果。
        </div>
      )}
      {hasMore && !isLoading ? (
        <button className="mt-5 w-full rounded-md border border-zinc-200 bg-white p-3 text-sm font-medium hover:bg-zinc-50 disabled:text-zinc-400" disabled={isLoadingMore} onClick={() => loadPapers(papers.length)}>
          {isLoadingMore ? "加载中..." : "加载更多"}
        </button>
      ) : null}
    </>
  );
}
