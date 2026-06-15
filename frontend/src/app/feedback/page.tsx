import { PageHeader } from "@/components/page-header";
import { feedbackHistory } from "@/lib/mock-data";

export default function FeedbackPage() {
  return (
    <>
      <PageHeader
        title="反馈历史"
        description="用户评分和标签会用于后续偏好权重更新。"
      />
      <div className="overflow-hidden rounded-md border border-zinc-200 bg-white">
        <table className="w-full min-w-[760px] border-collapse text-sm">
          <thead className="bg-zinc-50 text-left text-zinc-600">
            <tr>
              <th className="px-4 py-3 font-medium">评分</th>
              <th className="px-4 py-3 font-medium">论文</th>
              <th className="px-4 py-3 font-medium">标签</th>
              <th className="px-4 py-3 font-medium">备注</th>
              <th className="px-4 py-3 font-medium">更新时间</th>
            </tr>
          </thead>
          <tbody>
            {feedbackHistory.map((item) => (
              <tr key={item.id} className="border-t border-zinc-200">
                <td className="px-4 py-3 font-semibold">{item.rating}</td>
                <td className="px-4 py-3 text-zinc-950">{item.paperTitle}</td>
                <td className="px-4 py-3">
                  <div className="flex flex-wrap gap-1">
                    {item.tags.map((tag) => (
                      <span
                        key={tag}
                        className="rounded-md bg-indigo-50 px-2 py-1 text-xs font-medium text-indigo-800"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                </td>
                <td className="px-4 py-3 text-zinc-600">{item.note}</td>
                <td className="px-4 py-3 text-zinc-500">{item.updatedAt}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
