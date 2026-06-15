import { PageHeader } from "@/components/page-header";
import { PaperCard } from "@/components/paper-card";
import { papers } from "@/lib/mock-data";

export default function LibraryPage() {
  const libraryPapers = papers.filter((paper) => paper.isSaved || paper.isCore);

  return (
    <>
      <PageHeader
        title="文献库"
        description="保存、已读、核心和忽略状态会汇总到这里。"
      />
      <div className="mb-4 flex flex-wrap gap-2">
        {["全部", "已保存", "核心", "已读", "未读"].map((filter, index) => (
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
        {libraryPapers.map((paper) => (
          <PaperCard key={paper.id} paper={paper} />
        ))}
      </div>
    </>
  );
}
