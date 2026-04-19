import { SideNav } from "@/components/console/SideNav";

export default function ConsoleLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen lg:flex">
      <SideNav />
      <main className="flex-1 p-6">{children}</main>
    </div>
  );
}
