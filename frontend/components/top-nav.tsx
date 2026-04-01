"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/generate", label: "Image" },
  { href: "/video", label: "Video" },
  { href: "/chat", label: "Chat" },
  { href: "/studio", label: "Studio" },
  { href: "/history", label: "History" },
];

export function TopNav() {
  const pathname = usePathname();

  return (
    <nav className="flex gap-2 text-sm text-muted-foreground">
      {navItems.map((item) => {
        const active = pathname.startsWith(item.href);
        return (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              "rounded-full px-3 py-1.5 transition-colors",
              active ? "bg-accent text-foreground" : "hover:text-foreground"
            )}
          >
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
