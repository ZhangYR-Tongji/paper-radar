"use client";

import { CalendarClock, Play, RotateCw, Trash2 } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { Metric } from "@/components/metric";
import { PageHeader } from "@/components/page-header";
import { PaperCard } from "@/components/paper-card";
import {
  apiGet,
  apiSend,
  mapFetchRun,
  mapPaper,
  type ApiPaper,
} from "@/lib/api";
import type { FeedbackPayload, FetchRun, Paper } from "@/lib/types";

type LatestResponse = {
  latest_fetch_run: Record<string, unknown> | null;
  recommendation_min_score: number;
  papers: ApiPaper[];
};

const backfillPresets = [
  { value: "1y", label: "最近 1 年", years: 1 },
  { value: "3y", label: "最近 3 年", years: 3 },
  { value: "5y", label: "最近 5 年", years: 5 },
  { value: "custom", label: "自定义", years: null },
] as const;

type BackfillPreset = (typeof backfillPresets)[number]["value"];

const dateInputValue = (date: Date) => {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
};

const yearsAgoInputValue = (years: number) => {
  const date = new Date();
  date.setFullYear(date.getFullYear() - years);
  return dateInputValue(date);
};

const dateStartIso = (value: string) => new Date(`${value}T00:00:00`).toISOString();
const dateEndIso = (value: string) =>
  new Date(`${value}T23:59:59.999`).toISOString();

const filters = ["最新运行", "近 7 天", "近 30 天", "全部未读"];

export default function Home() {
  const [papers, setPapers] = useState<Paper[]>([]);
  const [latestRun, setLatestRun] = useState<FetchRun | null>(null);
  const [activeFilter, setActiveFilter] = useState(filters[0]);
  const [isLoading, setIsLoading] = useState(true);
  const [isFetching, setIsFetching] = useState(false);
  const [isBackfilling, setIsBackfilling] = useState(false);
  const [isClearingRuns, setIsClearingRuns] = useState(false);
  const [isBackfillOpen, setIsBackfillOpen] = useState(false);
  const [backfillPreset, setBackfillPreset] = useState<BackfillPreset>("1y");
  const [backfillFrom, setBackfillFrom] = useState(() => yearsAgoInputValue(1));
  const [backfillTo, setBackfillTo] = useState(() => dateInputValue(new Date()));
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadLatest = useCallback(async () => {
    setError(null);
    const data = await apiGet<LatestResponse>("/papers/latest");
    setLatestRun(mapFetchRun(data.latest_fetch_run));
    setPapers(data.papers.map(mapPaper));
  }, []);

  useEffect(() => {
    loadLatest()
      .catch((err: Error) => setError(err.message))
      .finally(() => setIsLoading(false));
  }, [loadLatest]);

  const startFetch = async () => {
    setIsFetching(true);
    setError(null);
    setMessage(null);
    try {
      await apiSend("/fetch/manual", "POST", {
        mode: "since_last_success",
        source_names: [],
        keyword_group_ids: [],
        date_from: null,
        date_to: null,
        overlap_buffer_days: 3,
      });
      await loadLatest();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Fetch failed");
    } finally {
      setIsFetching(false);
    }
  };

  const changeBackfillPreset = (value: BackfillPreset) => {
    setBackfillPreset(value);
    const preset = backfillPresets.find((item) => item.value === value);
    if (!preset?.years) {
      return;
    }
    setBackfillFrom(yearsAgoInputValue(preset.years));
    setBackfillTo(dateInputValue(new Date()));
  };

  const startHistoricalBackfill = async () => {
    if (!backfillFrom || !backfillTo) {
      setError("请选择历史回溯检索的起止日期");
      return;
    }
    if (new Date(dateStartIso(backfillFrom)) > new Date(dateEndIso(backfillTo))) {
      setError("历史回溯检索的开始日期不能晚于结束日期");
      return;
    }

    setIsBackfilling(true);
    setError(null);
    setMessage(null);
    try {
      const run = await apiSend<Record<string, unknown>>("/fetch/manual", "POST", {
        mode: "historical_backfill",
        source_names: [],
        keyword_group_ids: [],
        date_from: dateStartIso(backfillFrom),
        date_to: dateEndIso(backfillTo),
        overlap_buffer_days: 0,
      });
      await loadLatest();
      setMessage(
        `历史回溯检索完成：新增 ${Number(
          run.total_new_papers ?? 0,
        )} 篇，原始结果 ${Number(run.total_raw_results ?? 0)} 条。`,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "历史回溯检索失败");
    } finally {
      setIsBackfilling(false);
    }
  };

  const clearFetchRuns = async () => {
    const confirmed = window.confirm(
      "确认清空所有检索记录？已入库论文、文献库、反馈、数据源和关键词组都会保留。",
    );
    if (!confirmed) {
      return;
    }

    setIsClearingRuns(true);
    setError(null);
    setMessage(null);
    try {
      const result = await apiSend<Record<string, number>>("/fetch/runs/clear", "POST");
      await loadLatest();
      setMessage(
        `检索记录已清空：${result.deleted_runs ?? 0} 次运行，${
          result.deleted_run_items ?? 0
        } 条运行项，${result.deleted_cursors ?? 0} 个 cursor。`,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "清空检索记录失败");
    } finally {
      setIsClearingRuns(false);
    }
  };

  const updateFeedback = async (paperId: number, payload: FeedbackPayload) => {
    await apiSend(`/papers/${paperId}/feedback`, "PUT", payload);
    await loadLatest();
  };

  const filteredPapers = useMemo(() => {
    const now = new Date();
    return papers.filter((paper) => {
      if (activeFilter === "全部未读") {
        return !paper.isRead;
      }
      if (!paper.date) {
        return true;
      }
      const ageDays = (now.getTime() - new Date(paper.date).getTime()) / 86400000;
      if (activeFilter === "近 7 天") {
        return ageDays <= 7;
      }
      if (activeFilter === "近 30 天") {
        return ageDays <= 30;
      }
      return true;
    });
  }, [activeFilter, papers]);

  return (
    <>
      <PageHeader
        title="最新推荐"
        description="按当前数据源、关键词组、评分权重和历史反馈排序的新论文。"
        action={
          <div className="flex flex-wrap gap-2">
            <button
              className="inline-flex h-10 items-center gap-2 rounded-md border border-zinc-200 bg-white px-4 text-sm font-semibold text-zinc-700 hover:bg-zinc-50 disabled:cursor-not-allowed disabled:text-zinc-400"
              onClick={() => setIsBackfillOpen((value) => !value)}
              disabled={isFetching || isBackfilling}
            >
              <CalendarClock size={16} aria-hidden="true" />
              历史回溯
            </button>
            <button
              className="inline-flex h-10 items-center gap-2 rounded-md bg-emerald-700 px-4 text-sm font-semibold text-white hover:bg-emerald-800 disabled:cursor-not-allowed disabled:bg-zinc-400"
              onClick={startFetch}
              disabled={isFetching || isBackfilling}
            >
            <Play size={16} aria-hidden="true" />
            {isFetching ? "检索中..." : "开始检索新论文"}
            </button>
          </div>
        }
      />

      {error ? (
        <div className="mb-5 rounded-md border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">
          {error}
        </div>
      ) : null}

      {message ? (
        <div className="mb-5 rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">
          {message}
        </div>
      ) : null}

      {isBackfillOpen ? (
        <section className="mb-6 rounded-md border border-zinc-200 bg-white p-4">
          <div className="mb-4">
            <h2 className="text-base font-semibold text-zinc-950">历史回溯检索</h2>
          </div>
          <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_minmax(0,1fr)_auto] md:items-end">
            <label className="grid gap-1 text-sm font-medium text-zinc-700">
              时间范围
              <select
                className="h-10 rounded-md border border-zinc-200 bg-white px-3 text-sm font-normal text-zinc-950"
                value={backfillPreset}
                onChange={(event) =>
                  changeBackfillPreset(event.target.value as BackfillPreset)
                }
                disabled={isBackfilling}
              >
                {backfillPresets.map((preset) => (
                  <option key={preset.value} value={preset.value}>
                    {preset.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="grid gap-1 text-sm font-medium text-zinc-700">
              开始日期
              <input
                className="h-10 rounded-md border border-zinc-200 bg-white px-3 text-sm font-normal text-zinc-950"
                type="date"
                value={backfillFrom}
                onChange={(event) => {
                  setBackfillPreset("custom");
                  setBackfillFrom(event.target.value);
                }}
                disabled={isBackfilling}
              />
            </label>
            <label className="grid gap-1 text-sm font-medium text-zinc-700">
              结束日期
              <input
                className="h-10 rounded-md border border-zinc-200 bg-white px-3 text-sm font-normal text-zinc-950"
                type="date"
                value={backfillTo}
                onChange={(event) => {
                  setBackfillPreset("custom");
                  setBackfillTo(event.target.value);
                }}
                disabled={isBackfilling}
              />
            </label>
            <button
              className="inline-flex h-10 items-center justify-center gap-2 rounded-md bg-zinc-900 px-4 text-sm font-semibold text-white hover:bg-zinc-800 disabled:cursor-not-allowed disabled:bg-zinc-400"
              onClick={startHistoricalBackfill}
              disabled={isFetching || isBackfilling}
            >
              <CalendarClock size={16} aria-hidden="true" />
              {isBackfilling ? "回溯中..." : "开始回溯"}
            </button>
          </div>
        </section>
      ) : null}

      <section className="mb-6 border-b border-zinc-200 pb-6">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-base font-semibold text-zinc-950">
              最近一次检索
            </h2>
            <p className="mt-1 text-sm text-zinc-500">
              {latestRun ? (
                <>
                  <Link
                    className="font-medium text-emerald-700 hover:text-emerald-800"
                    href={`/fetch-runs/${latestRun.id}`}
                  >
                    抓取记录 #{latestRun.id}
                  </Link>
                  {` · ${latestRun.requestedFrom ?? "-"} 至 ${
                    latestRun.requestedTo ?? "-"
                  } · ${latestRun.status}`}
                </>
              ) : (
                "尚未执行检索"
              )}
            </p>
          </div>
          <button
            className="inline-flex h-9 items-center gap-2 rounded-md border border-zinc-200 bg-white px-3 text-sm font-medium text-zinc-700 hover:bg-zinc-50"
            onClick={loadLatest}
          >
            <RotateCw size={15} aria-hidden="true" />
            刷新状态
          </button>
          <button
            className="inline-flex h-9 items-center gap-2 rounded-md border border-rose-200 bg-white px-3 text-sm font-medium text-rose-700 hover:bg-rose-50 disabled:cursor-not-allowed disabled:text-zinc-400"
            onClick={clearFetchRuns}
            disabled={isFetching || isBackfilling || isClearingRuns}
          >
            <Trash2 size={15} aria-hidden="true" />
            {isClearingRuns ? "正在清空..." : "清空检索记录"}
          </button>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          <Metric label="原始结果" value={latestRun?.totalRawResults ?? 0} />
          <Metric label="新增论文" value={latestRun?.totalNewPapers ?? 0} tone="good" />
          <Metric label="重复结果" value={latestRun?.totalDuplicatePapers ?? 0} />
          <Metric label="高相关" value={latestRun?.totalHighlyRelevant ?? 0} tone="good" />
          <Metric label="错误" value={latestRun?.errorCount ?? 0} tone="warn" />
        </div>
      </section>

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

      {isLoading ? (
        <div className="rounded-md border border-zinc-200 bg-white p-6 text-sm text-zinc-500">
          正在加载推荐...
        </div>
      ) : filteredPapers.length ? (
        <div className="space-y-4">
          {filteredPapers.map((paper) => (
            <PaperCard key={paper.id} paper={paper} onFeedback={updateFeedback} />
          ))}
        </div>
      ) : (
        <div className="rounded-md border border-zinc-200 bg-white p-6 text-sm text-zinc-500">
          暂无论文。点击“开始检索新论文”获取最新结果。
        </div>
      )}
    </>
  );
}
