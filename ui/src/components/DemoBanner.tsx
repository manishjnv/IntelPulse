"use client";

/**
 * Demo Mode Banner
 * 
 * Displays a prominent banner when the application is running in demo mode.
 * This indicates to reviewers that authentication has been bypassed for
 * evaluation purposes.
 */

export function DemoBanner() {
    const isDemoMode = process.env.NEXT_PUBLIC_DEMO_MODE === "true";

    if (!isDemoMode) {
        return null;
    }

    return (
        <div className="bg-blue-600 text-white px-4 py-3 text-center text-sm font-medium shadow-md">
            <div className="flex items-center justify-center gap-2">
                <span className="text-lg">🎯</span>
                <span>
                    <strong>Demo Mode Active</strong> - AWS Codethon Submission
                </span>
                <span className="hidden sm:inline">|</span>
                <span className="hidden sm:inline text-blue-100">
                    Authentication bypassed for reviewer access
                </span>
            </div>
        </div>
    );
}
