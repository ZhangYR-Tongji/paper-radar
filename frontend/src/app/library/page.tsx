"use client";

import { useEffect, useState } from "react";

import { PageHeader } from "@/components/page-header";
import { PaperCard } from "@/components/paper-card";
import { apiGet, apiSend, mapPaper, type ApiPaper } from "@/lib/api";
import type { FeedbackPayload, Paper } from "@/lib/types";

const filters = ["全部", "已保存", "核心", "已读", "未读"];

export default function LibraryPage() {
  const [papers, setPapers] = useState<Paper[]>([]);
  const [activeFilter, setActiveFilter] = useState(filters[0]);

  const loadLibrary = async () => {
    const data = await apiGet<ApiPaper[]>("/papers/library");
    setPapers(data.map(mapPaper));
  };

  useEffect(() => {
    loadLibrary().catch(console.error);
  }, []);

  const updateFeedback = async (paperId: number, payload: FeedbackPayload) => {
    await apiSend(`/papers/${paperId}/feedback`, "PUT", payload);
    await loadLibrary();
  };

  const visible = papers.filter((paper) => {
    if (activeFilter === "已保存") {
      return paper.isSaved;
    }
    if (activeFilter === "核心") {
      return paper.isCore;
    }
    if (activeFilter === "已读") {
      return paper.isRead;
    }
    if (activeFilter === "未读") {
      return !paper.isRead;
    }
    return true;
  });

  return (
    <>
      <PageHeader
        title="文献库"
        description="保存、已读、核心和忽略状态会汇总到这里。"
      />
      <div className="mb-4 flex flex-wrap gap-2">
        {filters.map((filter) => (
          <button
            key={filter}
            className={`h-9 rounded-md px-3 text-sm font-medium ${
              activeFilter === filter
                ? "bg-zinc-900 text-white"
                : "border border-zinc-200 bg-white text-zinc-700 hover:bg-zinc-50"
            }`}
            onClick={() => setActiveFilter(filter)}
          >
            {filter}
          </button>
        ))}
      </div>
      {visible.length ? (
        <div className="space-y-4">
          {visible.map((paper) => (
            <PaperCard key={paper.id} paper={paper} onFeedback={updateFeedback} />
          ))}
        </div>
      ) : (
        <div className="rounded-md border border-zinc-200 bg-white p-6 text-sm text-zinc-500">
          暂无文献库记录。可在最新推荐中保存、标记已读或设为核心。
        </div>
      )}
    </>
  );
}
