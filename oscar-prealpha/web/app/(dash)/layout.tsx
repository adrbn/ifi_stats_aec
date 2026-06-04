import { NavRail } from "@/components/NavRail";
import { TopBar } from "@/components/TopBar";
import { AssistantModal } from "@/components/AssistantModal";

export default function DashLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen">
      <NavRail />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar />
        <main className="mx-auto w-full max-w-[1280px] flex-1 px-6 py-6">{children}</main>
      </div>
      <AssistantModal />
    </div>
  );
}
