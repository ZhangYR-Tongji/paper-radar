import { Search } from "lucide-react";

import { PageHeader } from "@/components/page-header";
import { PaperCard } from "@/components/paper-card";
import { papers } from "@/lib/mock-data";

export default function SearchPage() {
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
          />
        </label>
        <select className="h-11 rounded-md border border-zinc-200 px-3 text-sm">
          <option>全部分类</option>
          <option>Highly Relevant</option>
          <option>Worth Checking</option>
          <option>Low Priority</option>
        </select>
        <button className="h-11 rounded-md bg-zinc-900 px-4 text-sm font-semibold text-white hover:bg-zinc-800">
          搜索
        </button>
      </div>
      <div className="space-y-4">
        {papers.slice(0, 2).map((paper) => (
          <PaperCard key={paper.id} paper={paper} />
        ))}
      </div>
    </>
  );
}
