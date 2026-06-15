import { RotateCcw, Save } from "lucide-react";

import { PageHeader } from "@/components/page-header";
import { keywordGroups, sourceConfigs } from "@/lib/mock-data";

export default function SettingsPage() {
  return (
    <>
      <PageHeader
        title="设置"
        description="配置数据源、关键词组和评分权重。当前页面已按后端 Settings API 的数据结构组织。"
        action={
          <div className="flex gap-2">
            <button className="inline-flex h-10 items-center gap-2 rounded-md border border-zinc-200 bg-white px-3 text-sm font-medium text-zinc-700 hover:bg-zinc-50">
              <RotateCcw size={16} aria-hidden="true" />
              重置默认
            </button>
            <button className="inline-flex h-10 items-center gap-2 rounded-md bg-zinc-900 px-4 text-sm font-semibold text-white hover:bg-zinc-800">
              <Save size={16} aria-hidden="true" />
              保存
            </button>
          </div>
        }
      />

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
              {sourceConfigs.map((source) => (
                <tr key={source.id} className="border-t border-zinc-200">
                  <td className="px-4 py-3">
                    <input type="checkbox" defaultChecked={source.isEnabled} />
                  </td>
                  <td className="px-4 py-3 font-medium text-zinc-950">
                    {source.displayName}
                  </td>
                  <td className="px-4 py-3 text-zinc-600">{source.description}</td>
                  <td className="px-4 py-3">
                    <input
                      className="h-9 w-24 rounded-md border border-zinc-200 px-2"
                      defaultValue={source.dailyLimit}
                      type="number"
                    />
                  </td>
                  <td className="px-4 py-3">
                    <input
                      type="checkbox"
                      defaultChecked={source.participatesInRanking}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="mb-8">
        <h2 className="mb-3 text-base font-semibold text-zinc-950">关键词组</h2>
        <div className="grid gap-4 lg:grid-cols-3">
          {keywordGroups.map((group) => (
            <article
              key={group.id}
              className="rounded-md border border-zinc-200 bg-white p-4 shadow-sm"
            >
              <div className="mb-3 flex items-start justify-between gap-3">
                <div>
                  <h3 className="font-semibold text-zinc-950">{group.name}</h3>
                  <p className="mt-1 text-sm leading-5 text-zinc-500">
                    {group.description}
                  </p>
                </div>
                <input type="checkbox" defaultChecked={group.isEnabled} />
              </div>
              <label className="mb-2 block text-sm font-medium text-zinc-700">
                优先权重
                <input
                  className="mt-1 h-9 w-full rounded-md border border-zinc-200 px-2"
                  type="number"
                  step="0.1"
                  defaultValue={group.priorityWeight}
                />
              </label>
              <label className="block text-sm font-medium text-zinc-700">
                正向关键词
                <textarea
                  className="mt-1 min-h-24 w-full rounded-md border border-zinc-200 p-2 text-sm leading-5"
                  defaultValue={group.positiveKeywords.join("\n")}
                />
              </label>
            </article>
          ))}
        </div>
      </section>

      <section>
        <h2 className="mb-3 text-base font-semibold text-zinc-950">评分权重</h2>
        <div className="grid gap-3 rounded-md border border-zinc-200 bg-white p-4 sm:grid-cols-2 lg:grid-cols-6">
          {[
            ["主题", "0.30"],
            ["方法", "0.20"],
            ["来源", "0.15"],
            ["新鲜度", "0.15"],
            ["用户偏好", "0.10"],
            ["负向过滤", "0.10"],
          ].map(([label, value]) => (
            <label key={label} className="text-sm font-medium text-zinc-700">
              {label}
              <input
                className="mt-1 h-9 w-full rounded-md border border-zinc-200 px-2"
                defaultValue={value}
                type="number"
                step="0.01"
              />
            </label>
          ))}
        </div>
      </section>
    </>
  );
}
