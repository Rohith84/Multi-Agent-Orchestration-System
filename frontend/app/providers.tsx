/**
 * React Query provider wrapper.
 *
 * Must be a client component since QueryClientProvider uses React context.
 * Separated from layout.tsx to keep the layout as a server component.
 */

"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";

interface ProvidersProps {
  children: ReactNode;
}

export function Providers({ children }: ProvidersProps) {
  // Create QueryClient inside state to prevent re-creation on every render
  // and to avoid sharing state between server/client
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            // Don't refetch on window focus in development
            refetchOnWindowFocus: process.env.NODE_ENV === "production",
            // Retry once on failure
            retry: 1,
            // Data is considered fresh for 5 seconds
            staleTime: 5000,
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}
