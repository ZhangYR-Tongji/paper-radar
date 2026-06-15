import { AlertTriangle, CheckCircle2 } from "lucide-react";

import { Metric } from "@/components/metric";
import { PageHeader } from "@/components/page-header";
import { PaperCard } from "@/components/paper-card";
import { latestFetchSummary, papers } from "@/lib/mock-data";

const runItems = [
  ["arXiv", "AI-assisted conceptual design", "success", 42, 11, 9, ""],
  ["OpenAlex", "Design cognition and reasoning", "success", 76, 18, 12, ""],
  ["Crossref", "FBS / IBIS / Design Rationale", "failed", 0, 0, 0, "API timeout"],
];

export default async function FetchRunPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  return (
    <>
      <PageHeader
        title={`Fetch Run #${id}`}
        description="每个 source × keyword group 都会单独记录状态，只有成功项会推进 cursor。"
      />

      <section className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <Metric label="原始结果" value={latestFetchSummary.rawResults} />
        <Metric label="新增论文" value={latestFetchSummary.newPapers} tone="good" />
        <Metric label="重复结果" value={latestFetchSummary.duplicates} />
        <Metric
          label="高相关"
          value={latestFetchSummary.highlyRelevant}
          tone="good"
        />
        <Metric label="错误" value={latestFetchSummary.errors} tone="warn" />
      </section>

      <section className="mb-8">
        <h2 className="mb-3 text-base font-semibold text-zinc-950">运行项状态</h2>
        <div className="overflow-hidden rounded-md border border-zinc-200 bg-white">
          <table className="w-full min-w-[820px] border-collapse text-sm">
            <thead className="bg-zinc-50 text-left text-zinc-600">
              <tr>
                <th className="px-4 py-3 font-medium">状态</th>
                <th className="px-4 py-3 font-medium">来源</th>
                <th className="px-4 py-3 font-medium">关键词组</th>
                <th className="px-4 py-3 font-medium">原始</th>
                <th className="px-4 py-3 font-medium">新增</th>
                <th className="px-4 py-3 font-medium">重复</th>
                <th className="px-4 py-3 font-medium">错误</th>
              </tr>
            </thead>
            <tbody>
              {runItems.map(([source, group, status, raw, added, dup, error]) => (
                <tr key={`${source}-${group}`} className="border-t border-zinc-200">
                  <td className="px-4 py-3">
                    {status === "success" ? (
                      <span className="inline-flex items-center gap-1 text-emerald-700">
                        <CheckCircle2 size={16} aria-hidden="true" />
                        success
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-amber-700">
                        <AlertTriangle size={16} aria-hidden="true" />
                        failed
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 font-medium">{source}</td>
                  <td className="px-4 py-3">{group}</td>
                  <td className="px-4 py-3">{raw}</td>
                  <td className="px-4 py-3">{added}</td>
                  <td className="px-4 py-3">{dup}</td>
                  <td className="px-4 py-3 text-zinc-500">{error || "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <h2 className="mb-3 text-base font-semibold text-zinc-950">新增论文</h2>
        <div className="space-y-4">
          {papers.map((paper) => (
            <PaperCard key={paper.id} paper={paper} />
          ))}
        </div>
      </section>
    </>
  );
}
