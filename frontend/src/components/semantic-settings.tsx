"use client";

import { Download, LoaderCircle, RefreshCw, Save } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { apiGet, apiSend } from "@/lib/api";
import type { SemanticSettingsResponse } from "@/lib/types";

const isRunning = (settings: SemanticSettingsResponse | null) =>
  settings?.status === "preparing" || settings?.status === "indexing";

const errorMessage = (error: unknown) =>
  error instanceof Error ? error.message : "请求失败，请重试";

export function SemanticSettings({ refreshVersion = 0 }: { refreshVersion?: number }) {
  const [settings, setSettings] = useState<SemanticSettingsResponse | null>(null);
  const [isEnabled, setIsEnabled] = useState(false);
  const [minSimilarity, setMinSimilarity] = useState("0.82");
  const [semanticWeight, setSemanticWeight] = useState("0.75");
  const [pending, setPending] = useState(false);
  const [requestError, setRequestError] = useState<string | null>(null);
  const [statusError, setStatusError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const requestInFlight = useRef(false);
  const draftInitialized = useRef(false);
  const busy = pending || isRunning(settings);
  const running = isRunning(settings);

  useEffect(() => {
    if (pending) return;
    let active = true;
    apiGet<SemanticSettingsResponse>("/settings/semantic")
      .then((next) => {
        if (!active) return;
        setSettings(next);
        setStatusError(null);
        if (!draftInitialized.current) {
          setIsEnabled(next.is_enabled);
          setMinSimilarity(String(next.min_similarity));
          setSemanticWeight(String(next.semantic_weight));
          draftInitialized.current = true;
        }
      })
      .catch((error: unknown) => {
        if (active) setStatusError(errorMessage(error));
      });
    return () => {
      active = false;
    };
  }, [refreshVersion, pending]);

  useEffect(() => {
    if (!running) return;
    let active = true;
    let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      let keepPolling = true;
      try {
        const next = await apiGet<SemanticSettingsResponse>("/settings/semantic");
        if (!active) return;
        setSettings(next);
        setStatusError(null);
        keepPolling = isRunning(next);
      } catch (error: unknown) {
        if (active) {
          setStatusError(`读取进度失败，将自动重试：${errorMessage(error)}`);
        }
      }
      if (active && keepPolling) timer = setTimeout(poll, 2000);
    };
    timer = setTimeout(poll, 2000);
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [running]);

  const retryLoad = async () => {
    if (requestInFlight.current) return;
    requestInFlight.current = true;
    setPending(true);
    setStatusError(null);
    try {
      const next = await apiGet<SemanticSettingsResponse>("/settings/semantic");
      setSettings(next);
      setIsEnabled(next.is_enabled);
      setMinSimilarity(String(next.min_similarity));
      setSemanticWeight(String(next.semantic_weight));
      draftInitialized.current = true;
    } catch (error: unknown) {
      setStatusError(errorMessage(error));
    } finally {
      requestInFlight.current = false;
      setPending(false);
    }
  };

  const save = async () => {
    if (requestInFlight.current || running) return;
    const nextSimilarity = Number(minSimilarity);
    const nextWeight = Number(semanticWeight);
    if (
      !minSimilarity.trim() ||
      !semanticWeight.trim() ||
      !Number.isFinite(nextSimilarity) ||
      nextSimilarity < 0.5 ||
      nextSimilarity > 0.98 ||
      !Number.isFinite(nextWeight) ||
      nextWeight < 0 ||
      nextWeight > 1
    ) {
      setRequestError("相似度门槛需要在 0.5 到 0.98 之间，影响强度需要在 0 到 1 之间");
      return;
    }
    requestInFlight.current = true;
    setPending(true);
    setRequestError(null);
    setNotice(null);
    try {
      const next = await apiSend<SemanticSettingsResponse>("/settings/semantic", "PUT", {
        is_enabled: isEnabled,
        min_similarity: nextSimilarity,
        semantic_weight: nextWeight,
      });
      setSettings(next);
      setMinSimilarity(String(next.min_similarity));
      setSemanticWeight(String(next.semantic_weight));
      setNotice("语义设置已保存");
    } catch (error: unknown) {
      setRequestError(errorMessage(error));
    } finally {
      requestInFlight.current = false;
      setPending(false);
    }
  };

  const startTask = async (action: "prepare" | "reindex") => {
    if (requestInFlight.current || running) return;
    requestInFlight.current = true;
    setPending(true);
    setRequestError(null);
    setNotice(null);
    try {
      const next = await apiSend<SemanticSettingsResponse>(
        `/settings/semantic/${action}`,
        "POST",
      );
      setSettings(next);
    } catch (error: unknown) {
      setRequestError(errorMessage(error));
    } finally {
      requestInFlight.current = false;
      setPending(false);
    }
  };

  const needsPreparation = settings && !settings.model_ready;
  const taskError = settings?.status === "failed" ? settings.error : null;
  const runtimeError = settings?.runtime_status === "error" ? settings.error : null;
  const visibleError = requestError || statusError || taskError || runtimeError;
  const hasUnsavedChanges = settings && (
    isEnabled !== settings.is_enabled ||
    !minSimilarity.trim() ||
    !semanticWeight.trim() ||
    Number(minSimilarity) !== settings.min_similarity ||
    Number(semanticWeight) !== settings.semantic_weight
  );

  return (
    <section className="mb-8" aria-labelledby="semantic-settings-heading">
      <h2 id="semantic-settings-heading" className="mb-3 text-base font-semibold text-zinc-950">
        语义候选
      </h2>
      <p className="mb-4 text-sm leading-6 text-zinc-500">
        轻量本地模型根据研究方向描述与论文标题摘要，发现可能相关的语义候选，补充关键词匹配。候选仍需结合摘要判断。首次下载完成后在本机离线运行，无需模型 API 费用。请在关键词组中写清你希望寻找的研究对象、方法和目标，并保存该组。
      </p>
      <div className="rounded-md border border-zinc-200 bg-white p-4">
        {settings ? (
          <>
            <label className="flex items-center gap-2 text-sm font-medium text-zinc-700">
              <input
                type="checkbox"
                checked={isEnabled}
                disabled={busy}
                onChange={(event) => setIsEnabled(event.target.checked)}
              />
              启用本地语义评分
            </label>
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              <label className="text-sm font-medium text-zinc-700">
                相似度门槛
                <input
                  className="mt-1 h-9 w-full rounded-md border border-zinc-200 px-2 disabled:bg-zinc-50"
                  type="number"
                  min="0.5"
                  max="0.98"
                  step="0.01"
                  value={minSimilarity}
                  disabled={busy}
                  onChange={(event) => setMinSimilarity(event.target.value)}
                />
                <span className="mt-1 block text-xs font-normal leading-5 text-zinc-500">
                  0.5–0.98，越高越严格。这是模型相似度，不代表相关概率。
                </span>
              </label>
              <label className="text-sm font-medium text-zinc-700">
                语义影响强度
                <input
                  className="mt-1 h-9 w-full rounded-md border border-zinc-200 px-2 disabled:bg-zinc-50"
                  type="number"
                  min="0"
                  max="1"
                  step="0.05"
                  value={semanticWeight}
                  disabled={busy}
                  onChange={(event) => setSemanticWeight(event.target.value)}
                />
                <span className="mt-1 block text-xs font-normal leading-5 text-zinc-500">
                  0–1，控制语义候选对主题评分的影响。
                </span>
              </label>
            </div>
            <div className="mt-4 flex flex-wrap items-center gap-2">
              <button
                className="inline-flex h-9 items-center gap-2 rounded-md bg-zinc-900 px-3 text-sm font-semibold text-white hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-50"
                disabled={busy}
                onClick={() => void save()}
              >
                <Save size={15} aria-hidden="true" />
                保存语义设置
              </button>
              <button
                className="inline-flex h-9 items-center gap-2 rounded-md border border-zinc-200 px-3 text-sm font-medium text-zinc-700 hover:bg-zinc-50 disabled:cursor-not-allowed disabled:opacity-50"
                disabled={busy || !settings.dependencies_ready || Boolean(hasUnsavedChanges)}
                onClick={() => void startTask(needsPreparation ? "prepare" : "reindex")}
              >
                {busy ? (
                  <LoaderCircle size={15} className="animate-spin" aria-hidden="true" />
                ) : needsPreparation ? (
                  <Download size={15} aria-hidden="true" />
                ) : (
                  <RefreshCw size={15} aria-hidden="true" />
                )}
                {needsPreparation ? "下载并准备本地模型" : "重算已有论文"}
              </button>
              {hasUnsavedChanges ? (
                <span className="text-xs text-zinc-500">请先保存语义设置</span>
              ) : null}
            </div>
            <div className="mt-4 text-sm leading-6 text-zinc-600" role="status" aria-live="polite">
              {settings.status === "preparing" ? (
                <p>正在下载并准备本地模型，首次准备可能需要几分钟。</p>
              ) : settings.status === "indexing" ? (
                <>
                  <p>正在重算论文：{settings.processed_papers} / {settings.total_papers}</p>
                  {settings.total_papers > 0 ? (
                    <progress
                      className="mt-2 h-2 w-full accent-zinc-900"
                      value={settings.processed_papers}
                      max={settings.total_papers}
                      aria-label="论文语义评分进度"
                    />
                  ) : null}
                </>
              ) : !settings.dependencies_ready ? (
                <p>本地语义组件尚未安装，请按项目说明安装并重启后端。</p>
              ) : needsPreparation ? (
                <p>尚未准备模型。点击下载按钮后会联网下载，完成后可离线使用。</p>
              ) : settings.status === "completed" ? (
                <p>语义评分已完成，已处理 {settings.processed_papers} 篇论文。</p>
              ) : (
                <p>本地模型已就绪，已缓存 {settings.cached_papers} 篇论文。</p>
              )}
              {settings.is_enabled && needsPreparation && !running ? (
                <p>完成模型准备后，语义候选即可参与评分。</p>
              ) : null}
            </div>
          </>
        ) : (
          <div className="flex items-center gap-3 text-sm text-zinc-500">
            <span>{statusError ? "语义设置加载失败" : "正在加载语义设置…"}</span>
            {statusError ? (
              <button
                className="rounded-md border border-zinc-200 px-3 py-1.5 font-medium text-zinc-700 disabled:opacity-50"
                disabled={pending}
                onClick={() => void retryLoad()}
              >
                重试
              </button>
            ) : null}
          </div>
        )}
        {notice ? (
          <p className="mt-3 text-sm text-emerald-700" role="status">{notice}</p>
        ) : null}
        {visibleError ? (
          <p className="mt-3 break-words rounded-md bg-rose-50 p-3 text-sm text-rose-800" role="alert">
            {visibleError}
          </p>
        ) : null}
      </div>
    </section>
  );
}
