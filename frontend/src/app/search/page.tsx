"use client";

import { Search } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { PageHeader } from "@/components/page-header";
import { PaperCard } from "@/components/paper-card";
import { apiGet, apiSend, mapPaper, type ApiPaper } from "@/lib/api";
import type { FeedbackPayload, Paper } from "@/lib/types";

export default function SearchPage() {
  const [papers, setPapers] = useState<Paper[]>([]);
  const [query, setQuery] = useState("");
  const [classification, setClassification] = useState("");

  const loadPapers = useCallback(async () => {
    const params = new URLSearchParams();
    if (classification) {
      params.set("classification", classification);
    }
    const data = await apiGet<ApiPaper[]>(`/papers?${params.toString()}`);
    setPapers(data.map(mapPaper));
  }, [classification]);

  useEffect(() => {
    loadPapers().catch(console.error);
  }, [loadPapers]);

  const updateFeedback = async (paperId: number, payload: FeedbackPayload) => {
    await apiSend(`/papers/${paperId}/feedback`, "PUT", payload);
    await loadPapers();
  };

  const visible = useMemo(() => {
    const needle = query.toLowerCase();
    if (!needle) {
      return papers;
    }
    return papers.filter((paper) => {
      const text = [
        paper.title,
        paper.abstract,
        paper.authors.join(" "),
        paper.matchedKeywordGroups.join(" "),
        paper.matchedKeywords.join(" "),
      ]
        .join(" ")
        .toLowerCase();
      return text.includes(needle);
    });
  }, [papers, query]);

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
      {visible.length ? (
        <div className="space-y-4">
          {visible.map((paper) => (
            <PaperCard key={paper.id} paper={paper} onFeedback={updateFeedback} />
          ))}
        </div>
      ) : (
        <div className="rounded-md border border-zinc-200 bg-white p-6 text-sm text-zinc-500">
          没有匹配结果。
        </div>
      )}
    </>
  );
}
