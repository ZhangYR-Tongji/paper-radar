import { Play, RotateCw } from "lucide-react";

import { Metric } from "@/components/metric";
import { PageHeader } from "@/components/page-header";
import { PaperCard } from "@/components/paper-card";
import { latestFetchSummary, papers } from "@/lib/mock-data";

const filters = ["最新运行", "近 7 天", "近 30 天", "全部未读"];

export default function Home() {
  return (
    <>
      <PageHeader
        title="最新推荐"
        description="按当前数据源、关键词组、评分权重和历史反馈排序的新论文。"
        action={
          <button className="inline-flex h-10 items-center gap-2 rounded-md bg-emerald-700 px-4 text-sm font-semibold text-white hover:bg-emerald-800">
            <Play size={16} aria-hidden="true" />
            开始检索新论文
          </button>
        }
      />

      <section className="mb-6 border-b border-zinc-200 pb-6">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-base font-semibold text-zinc-950">
              最近一次 Fetch
            </h2>
            <p className="mt-1 text-sm text-zinc-500">
              #{latestFetchSummary.id} · {latestFetchSummary.timeRange} ·{" "}
              {latestFetchSummary.status}
            </p>
          </div>
          <button className="inline-flex h-9 items-center gap-2 rounded-md border border-zinc-200 bg-white px-3 text-sm font-medium text-zinc-700 hover:bg-zinc-50">
            <RotateCw size={15} aria-hidden="true" />
            刷新状态
          </button>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          <Metric label="原始结果" value={latestFetchSummary.rawResults} />
          <Metric label="新增论文" value={latestFetchSummary.newPapers} tone="good" />
          <Metric label="重复结果" value={latestFetchSummary.duplicates} />
          <Metric
            label="高相关"
            value={latestFetchSummary.highlyRelevant}
            tone="good"
          />
          <Metric label="错误" value={latestFetchSummary.errors} tone="warn" />
        </div>
      </section>

      <div className="mb-4 flex flex-wrap gap-2">
        {filters.map((filter, index) => (
          <button
            key={filter}
            className={`h-9 rounded-md px-3 text-sm font-medium ${
              index === 0
                ? "bg-zinc-900 text-white"
                : "border border-zinc-200 bg-white text-zinc-700 hover:bg-zinc-50"
            }`}
          >
            {filter}
          </button>
        ))}
      </div>

      <div className="space-y-4">
        {papers.map((paper) => (
          <PaperCard key={paper.id} paper={paper} />
        ))}
      </div>
    </>
  );
}
