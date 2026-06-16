"use client";

import { Download } from "lucide-react";
import { useEffect, useState } from "react";

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

const filters = ["全部", "文献库", "重点文献", "已读"];

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
    if (activeFilter === "文献库") {
      return paper.isSaved;
    }
    if (activeFilter === "重点文献") {
      return paper.isCore;
    }
    if (activeFilter === "已读") {
      return paper.isRead;
    }
    return true;
  });

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
          暂无文献库记录。可在最新推荐中加入文献库、设为重点，或打开原文/PDF 形成已读记录。
        </div>
      )}
    </>
  );
}
