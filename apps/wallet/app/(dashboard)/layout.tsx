import { Sidebar } from "@/components/Layout/Sidebar";
import { RightSidebar } from "@/components/Layout/RightSidebar";
import { MobileNav } from "@/components/Layout/MobileNav";

export default function DashboardLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <div className="flex min-h-screen bg-[var(--bg-primary)]">
            {/* Desktop Sidebar */}
            <div className="hidden md:block">
                <Sidebar />
            </div>

            <main className="flex-1 p-4 md:p-8 pb-24 md:pb-8 overflow-y-auto overflow-x-hidden">
                <div className="max-w-5xl mx-auto">
                    {children}
                </div>
            </main>

            <RightSidebar />

            {/* Mobile Bottom Nav */}
            <div className="md:hidden">
                <MobileNav />
            </div>
        </div>
    );
}
