"use client";

import { Plus, Save, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";

import { PageHeader } from "@/components/page-header";
import {
  apiGet,
  apiSend,
  mapKeywordGroup,
  mapSourceConfig,
} from "@/lib/api";
import type { KeywordGroup, SourceConfig } from "@/lib/types";

const splitKeywordDraft = (value: string) => value.split("\n");

const normalizeKeywords = (keywords: string[]) =>
  keywords.map((item) => item.trim()).filter(Boolean);

export default function SettingsPage() {
  const [sources, setSources] = useState<SourceConfig[]>([]);
  const [groups, setGroups] = useState<KeywordGroup[]>([]);
  const [weights, setWeights] = useState<Record<string, number>>({});
  const [recommendationMinScore, setRecommendationMinScore] = useState(50);
  const [message, setMessage] = useState<string | null>(null);

  const loadSettings = async () => {
    const [sourceData, groupData, scoringData, preferencesData] = await Promise.all([
      apiGet<Record<string, unknown>[]>("/settings/sources"),
      apiGet<Record<string, unknown>[]>("/settings/keyword-groups"),
      apiGet<Record<string, unknown>>("/settings/scoring-weights"),
      apiGet<Record<string, unknown>>("/settings/preferences"),
    ]);
    setSources(sourceData.map(mapSourceConfig));
    setGroups(groupData.map(mapKeywordGroup));
    setWeights({
      topic_weight: Number(scoringData.topic_weight ?? 0),
      method_weight: Number(scoringData.method_weight ?? 0),
      venue_weight: Number(scoringData.venue_weight ?? 0),
      freshness_weight: Number(scoringData.freshness_weight ?? 0),
      user_preference_weight: Number(scoringData.user_preference_weight ?? 0),
      negative_filter_weight: Number(scoringData.negative_filter_weight ?? 0),
    });
    setRecommendationMinScore(
      Number(preferencesData.recommendation_min_score ?? 50),
    );
  };

  useEffect(() => {
    loadSettings().catch((err: Error) => setMessage(err.message));
  }, []);

  const updateSource = async (id: number, patch: Partial<SourceConfig>) => {
    const payload = {
      display_name: patch.displayName,
      description: patch.description,
      is_enabled: patch.isEnabled,
      daily_limit: patch.dailyLimit,
      participates_in_ranking: patch.participatesInRanking,
      metadata_only: patch.metadataOnly,
    };
    await apiSend(`/settings/sources/${id}`, "PUT", payload);
    await loadSettings();
    setMessage("数据源已保存");
  };

  const updateGroup = async (group: KeywordGroup) => {
    await apiSend(`/settings/keyword-groups/${group.id}`, "PUT", {
      name: group.name,
      description: group.description,
      is_enabled: group.isEnabled,
      priority_weight: group.priorityWeight,
      positive_keywords: normalizeKeywords(group.positiveKeywords),
      negative_keywords: normalizeKeywords(group.negativeKeywords),
      required_keywords: normalizeKeywords(group.requiredKeywords),
      optional_keywords: normalizeKeywords(group.optionalKeywords),
    });
    await loadSettings();
    setMessage("关键词组已保存");
  };

  const createGroup = async () => {
    await apiSend("/settings/keyword-groups", "POST", {
      name: `新关键词组 ${Date.now()}`,
      description: "",
      is_enabled: true,
      priority_weight: 1,
      positive_keywords: [],
      negative_keywords: [],
      required_keywords: [],
      optional_keywords: [],
      related_tags: [],
    });
    await loadSettings();
  };

  const deleteGroup = async (id: number) => {
    await apiSend(`/settings/keyword-groups/${id}`, "DELETE");
    await loadSettings();
  };

  const clearGroups = async () => {
    await apiSend("/settings/keyword-groups/clear", "POST");
    await loadSettings();
    setMessage("关键词组已清空");
  };

  const saveWeights = async () => {
    await apiSend("/settings/scoring-weights", "PUT", weights);
    setMessage("评分权重已保存");
  };

  const savePreferences = async () => {
    const nextScore = Math.max(0, Math.min(100, recommendationMinScore));
    await apiSend("/settings/preferences", "PUT", {
      recommendation_min_score: nextScore,
    });
    setRecommendationMinScore(nextScore);
    setMessage("推荐过滤已保存");
  };

  return (
    <>
      <PageHeader
        title="设置"
        description="配置数据源、关键词组和评分权重。配置保存在本地数据库中。"
        action={
          <button
            className="inline-flex h-10 items-center gap-2 rounded-md bg-zinc-900 px-4 text-sm font-semibold text-white hover:bg-zinc-800"
            onClick={saveWeights}
          >
            <Save size={16} aria-hidden="true" />
            保存权重
          </button>
        }
      />

      {message ? (
        <div className="mb-5 rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">
          {message}
        </div>
      ) : null}

      <section className="mb-8">
        <h2 className="mb-3 text-base font-semibold text-zinc-950">数据源</h2>
        <div className="overflow-hidden rounded-md border border-zinc-200 bg-white">
          <table className="w-full min-w-[760px] border-collapse text-sm">
            <thead className="bg-zinc-50 text-left text-zinc-600">
              <tr>
                <th className="px-4 py-3 font-medium">启用</th>
                <th className="px-4 py-3 font-medium">来源</th>
                <th className="px-4 py-3 font-medium">说明</th>
                <th className="px-4 py-3 font-medium">每日限制</th>
                <th className="px-4 py-3 font-medium">参与排序</th>
              </tr>
            </thead>
            <tbody>
              {sources.map((source) => (
                <tr key={source.id} className="border-t border-zinc-200">
                  <td className="px-4 py-3">
                    <input
                      type="checkbox"
                      checked={source.isEnabled}
                      onChange={(event) =>
                        updateSource(source.id, { isEnabled: event.target.checked })
                      }
                    />
                  </td>
                  <td className="px-4 py-3 font-medium text-zinc-950">
                    {source.displayName}
                  </td>
                  <td className="px-4 py-3 text-zinc-600">{source.description}</td>
                  <td className="px-4 py-3">
                    <input
                      className="h-9 w-24 rounded-md border border-zinc-200 px-2"
                      value={source.dailyLimit}
                      type="number"
                      onChange={(event) =>
                        setSources((current) =>
                          current.map((item) =>
                            item.id === source.id
                              ? { ...item, dailyLimit: Number(event.target.value) }
                              : item,
                          ),
                        )
                      }
                      onBlur={() =>
                        updateSource(source.id, { dailyLimit: source.dailyLimit })
                      }
                    />
                  </td>
                  <td className="px-4 py-3">
                    <input
                      type="checkbox"
                      checked={source.participatesInRanking}
                      onChange={(event) =>
                        updateSource(source.id, {
                          participatesInRanking: event.target.checked,
                        })
                      }
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="mb-8">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-base font-semibold text-zinc-950">关键词组</h2>
          <div className="flex gap-2">
            {groups.length ? (
              <button
                className="inline-flex h-9 items-center gap-2 rounded-md border border-zinc-200 bg-white px-3 text-sm font-medium text-zinc-700 hover:bg-zinc-50"
                onClick={clearGroups}
              >
                <Trash2 size={15} aria-hidden="true" />
                清空
              </button>
            ) : null}
            <button
              className="inline-flex h-9 items-center gap-2 rounded-md border border-zinc-200 bg-white px-3 text-sm font-medium text-zinc-700 hover:bg-zinc-50"
              onClick={createGroup}
            >
              <Plus size={15} aria-hidden="true" />
              新建
            </button>
          </div>
        </div>
        {groups.length ? (
          <div className="grid gap-4 lg:grid-cols-3">
            {groups.map((group) => (
              <KeywordGroupEditor
                key={group.id}
                group={group}
                onChange={(next) =>
                  setGroups((current) =>
                    current.map((item) => (item.id === next.id ? next : item)),
                  )
                }
                onSave={updateGroup}
                onDelete={deleteGroup}
              />
            ))}
          </div>
        ) : (
          <div className="rounded-md border border-zinc-200 bg-white p-6 text-sm text-zinc-500">
            暂无关键词组。新建研究主题后即可检索。
          </div>
        )}
      </section>

      <section className="mb-8">
        <div className="mb-3 flex items-center justify-between gap-3">
          <h2 className="text-base font-semibold text-zinc-950">推荐过滤</h2>
          <button
            className="inline-flex h-9 items-center gap-2 rounded-md border border-zinc-200 bg-white px-3 text-sm font-medium text-zinc-700 hover:bg-zinc-50"
            onClick={savePreferences}
          >
            <Save size={15} aria-hidden="true" />
            保存过滤
          </button>
        </div>
        <div className="grid gap-4 rounded-md border border-zinc-200 bg-white p-4 sm:grid-cols-[minmax(0,1fr)_8rem] sm:items-end">
          <label className="text-sm font-medium text-zinc-700">
            最低推荐评分
            <input
              className="mt-3 block w-full accent-zinc-900"
              type="range"
              min="0"
              max="100"
              step="1"
              value={recommendationMinScore}
              onChange={(event) =>
                setRecommendationMinScore(Number(event.target.value))
              }
            />
          </label>
          <label className="text-sm font-medium text-zinc-700">
            分数
            <input
              className="mt-1 h-9 w-full rounded-md border border-zinc-200 px-2"
              type="number"
              min="0"
              max="100"
              step="1"
              value={recommendationMinScore}
              onChange={(event) =>
                setRecommendationMinScore(Number(event.target.value))
              }
            />
          </label>
        </div>
      </section>

      <section>
        <h2 className="mb-3 text-base font-semibold text-zinc-950">评分权重</h2>
        <div className="grid gap-3 rounded-md border border-zinc-200 bg-white p-4 sm:grid-cols-2 lg:grid-cols-6">
          {[
            ["topic_weight", "主题"],
            ["method_weight", "方法"],
            ["venue_weight", "来源"],
            ["freshness_weight", "新鲜度"],
            ["user_preference_weight", "用户偏好"],
            ["negative_filter_weight", "负向过滤"],
          ].map(([key, label]) => (
            <label key={key} className="text-sm font-medium text-zinc-700">
              {label}
              <input
                className="mt-1 h-9 w-full rounded-md border border-zinc-200 px-2"
                value={weights[key] ?? 0}
                type="number"
                step="0.01"
                onChange={(event) =>
                  setWeights((current) => ({
                    ...current,
                    [key]: Number(event.target.value),
                  }))
                }
              />
            </label>
          ))}
        </div>
      </section>
    </>
  );
}

function KeywordGroupEditor({
  group,
  onChange,
  onSave,
  onDelete,
}: {
  group: KeywordGroup;
  onChange: (group: KeywordGroup) => void;
  onSave: (group: KeywordGroup) => void;
  onDelete: (id: number) => void;
}) {
  return (
    <article className="rounded-md border border-zinc-200 bg-white p-4 shadow-sm">
      <div className="mb-3 flex items-start justify-between gap-3">
        <label className="flex-1 text-sm font-medium text-zinc-700">
          名称
          <input
            className="mt-1 h-9 w-full rounded-md border border-zinc-200 px-2"
            value={group.name}
            onChange={(event) => onChange({ ...group, name: event.target.value })}
          />
        </label>
        <input
          className="mt-7"
          type="checkbox"
          checked={group.isEnabled}
          onChange={(event) => onChange({ ...group, isEnabled: event.target.checked })}
        />
      </div>
      <label className="mb-2 block text-sm font-medium text-zinc-700">
        说明
        <textarea
          className="mt-1 min-h-16 w-full rounded-md border border-zinc-200 p-2 text-sm leading-5"
          value={group.description}
          onChange={(event) => onChange({ ...group, description: event.target.value })}
        />
      </label>
      <label className="mb-2 block text-sm font-medium text-zinc-700">
        优先权重
        <input
          className="mt-1 h-9 w-full rounded-md border border-zinc-200 px-2"
          type="number"
          step="0.1"
          value={group.priorityWeight}
          onChange={(event) =>
            onChange({ ...group, priorityWeight: Number(event.target.value) })
          }
        />
      </label>
      {[
        ["positiveKeywords", "正向关键词"],
        ["negativeKeywords", "负向关键词"],
        ["requiredKeywords", "必须关键词"],
        ["optionalKeywords", "可选关键词"],
      ].map(([key, label]) => (
        <label key={key} className="mb-2 block text-sm font-medium text-zinc-700">
          {label}
          <textarea
            className="mt-1 min-h-20 w-full rounded-md border border-zinc-200 p-2 text-sm leading-5"
            value={(group[key as keyof KeywordGroup] as string[]).join("\n")}
            onChange={(event) =>
              onChange({
                ...group,
                [key]: splitKeywordDraft(event.target.value),
              })
            }
          />
        </label>
      ))}
      <div className="mt-3 flex gap-2">
        <button
          className="inline-flex h-9 flex-1 items-center justify-center gap-2 rounded-md bg-zinc-900 px-3 text-sm font-semibold text-white hover:bg-zinc-800"
          onClick={() => onSave(group)}
        >
          <Save size={15} aria-hidden="true" />
          保存
        </button>
        <button
          className="inline-flex h-9 items-center justify-center rounded-md border border-zinc-200 px-3 text-zinc-600 hover:bg-zinc-50"
          onClick={() => onDelete(group.id)}
        >
          <Trash2 size={15} aria-label="删除" />
        </button>
      </div>
    </article>
  );
}
