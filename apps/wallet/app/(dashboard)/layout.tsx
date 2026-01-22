import { Sidebar } from "@/components/Layout/Sidebar";
import { RightSidebar } from "@/components/Layout/RightSidebar";

export default function DashboardLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <div className="flex min-h-screen bg-[var(--bg-primary)]">
            <Sidebar />
            <main className="flex-1 p-8 overflow-y-auto">
                <div className="max-w-5xl mx-auto">
                    {children}
                </div>
            </main>
            <RightSidebar />
        </div>
    );
}
