"use client";

import {
  BookMarked,
  History,
  Radar,
  Search,
  Settings,
  Sparkles,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

type NavItem = {
  href: string;
  label: string;
  icon: LucideIcon;
};

const navItems: NavItem[] = [
  { href: "/", label: "最新推荐", icon: Sparkles },
  { href: "/settings", label: "设置", icon: Settings },
  { href: "/library", label: "文献库", icon: BookMarked },
  { href: "/feedback", label: "反馈", icon: History },
  { href: "/search", label: "搜索", icon: Search },
  { href: "/fetch-runs/1", label: "Fetch 详情", icon: Radar },
];

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="min-h-screen bg-stone-50 text-zinc-950">
      <header className="border-b border-zinc-200 bg-white">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-4 sm:px-6 lg:flex-row lg:items-center lg:justify-between lg:px-8">
          <Link href="/" className="flex items-center gap-3">
            <span className="flex size-10 items-center justify-center rounded-md bg-emerald-700 text-white">
              <Radar size={22} aria-hidden="true" />
            </span>
            <span>
              <span className="block text-base font-semibold">
                Design-AI Paper Radar
              </span>
              <span className="block text-sm text-zinc-500">
                本地优先论文检索与排序
              </span>
            </span>
          </Link>
          <nav className="flex flex-wrap gap-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const active =
                item.href === "/"
                  ? pathname === "/"
                  : pathname.startsWith(item.href.split("/[")[0]);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`inline-flex h-10 items-center gap-2 rounded-md px-3 text-sm font-medium transition ${
                    active
                      ? "bg-zinc-900 text-white"
                      : "text-zinc-600 hover:bg-zinc-100 hover:text-zinc-950"
                  }`}
                >
                  <Icon size={16} aria-hidden="true" />
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </div>
      </header>
      <main className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        {children}
      </main>
    </div>
  );
}
