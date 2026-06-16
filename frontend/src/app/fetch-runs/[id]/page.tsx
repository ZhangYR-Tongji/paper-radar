"use client";

import { AlertTriangle, CheckCircle2 } from "lucide-react";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { Metric } from "@/components/metric";
import { PageHeader } from "@/components/page-header";
import { PaperCard } from "@/components/paper-card";
import { apiGet, apiSend, mapFetchRun } from "@/lib/api";
import type { FeedbackPayload, FetchRun } from "@/lib/types";

export default function FetchRunPage() {
  const params = useParams<{ id: string }>();
  const [run, setRun] = useState<FetchRun | null>(null);

  const loadRun = useCallback(async () => {
    const data = await apiGet<Record<string, unknown>>(`/fetch/runs/${params.id}`);
    setRun(mapFetchRun(data));
  }, [params.id]);

  useEffect(() => {
    loadRun().catch(console.error);
  }, [loadRun]);

  const updateFeedback = async (paperId: number, payload: FeedbackPayload) => {
    await apiSend(`/papers/${paperId}/feedback`, "PUT", payload);
    await loadRun();
  };

  return (
    <>
      <PageHeader
        title={`抓取记录 #${params.id}`}
        description="用于排查一次检索运行的过程、错误和去重结果。每个数据源 × 关键词组都会单独记录状态，只有成功项会推进 cursor。"
      />

      <section className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <Metric label="原始结果" value={run?.totalRawResults ?? 0} />
        <Metric label="新增论文" value={run?.totalNewPapers ?? 0} tone="good" />
        <Metric label="重复结果" value={run?.totalDuplicatePapers ?? 0} />
        <Metric label="高相关" value={run?.totalHighlyRelevant ?? 0} tone="good" />
        <Metric label="错误" value={run?.errorCount ?? 0} tone="warn" />
      </section>

      <section className="mb-8">
        <h2 className="mb-3 text-base font-semibold text-zinc-950">运行项状态</h2>
        <div className="overflow-hidden rounded-md border border-zinc-200 bg-white">
          <table className="w-full min-w-[820px] border-collapse text-sm">
            <thead className="bg-zinc-50 text-left text-zinc-600">
              <tr>
                <th className="px-4 py-3 font-medium">状态</th>
                <th className="px-4 py-3 font-medium">来源</th>
                <th className="px-4 py-3 font-medium">关键词组 ID</th>
                <th className="px-4 py-3 font-medium">原始</th>
                <th className="px-4 py-3 font-medium">新增</th>
                <th className="px-4 py-3 font-medium">重复</th>
                <th className="px-4 py-3 font-medium">错误</th>
              </tr>
            </thead>
            <tbody>
              {(run?.items ?? []).map((item) => (
                <tr key={item.id} className="border-t border-zinc-200">
                  <td className="px-4 py-3">
                    {item.status === "success" ? (
                      <span className="inline-flex items-center gap-1 text-emerald-700">
                        <CheckCircle2 size={16} aria-hidden="true" />
                        success
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-amber-700">
                        <AlertTriangle size={16} aria-hidden="true" />
                        {item.status}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 font-medium">{item.sourceName}</td>
                  <td className="px-4 py-3">{item.keywordGroupId}</td>
                  <td className="px-4 py-3">{item.rawResultCount}</td>
                  <td className="px-4 py-3">{item.newPaperCount}</td>
                  <td className="px-4 py-3">{item.duplicateCount}</td>
                  <td className="px-4 py-3 text-zinc-500">
                    {item.errorMessage || "-"}
                  </td>
                </tr>
              ))}
              {!run?.items.length ? (
                <tr>
                  <td className="px-4 py-6 text-zinc-500" colSpan={7}>
                    暂无运行项。
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <h2 className="mb-3 text-base font-semibold text-zinc-950">本次新增论文</h2>
        {run?.papers.length ? (
          <div className="space-y-4">
            {run.papers.map((paper) => (
              <PaperCard key={paper.id} paper={paper} onFeedback={updateFeedback} />
            ))}
          </div>
        ) : (
          <div className="rounded-md border border-zinc-200 bg-white p-6 text-sm text-zinc-500">
            暂无新增论文。
          </div>
        )}
      </section>
    </>
  );
}
