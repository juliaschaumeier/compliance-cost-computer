"use client";

import { useCallback, useState } from "react";

import { logClientError } from "@/lib/errorFeedback";

type UseEaReviewSaveOptions = {
  logLabel: string;
  logContext?: Record<string, unknown>;
};

export function useEaReviewSave({ logLabel, logContext }: UseEaReviewSaveOptions) {
  const [reviewMode, setReviewMode] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [status, setStatus] = useState<string | null>(null);

  const runSave = useCallback(
    async (
      saveFn: () => Promise<void>,
      options: { successMessage: string; errorMessage: string }
    ) => {
      setIsSaving(true);
      setStatus(null);
      try {
        await saveFn();
        setStatus(options.successMessage);
      } catch (error) {
        logClientError(logLabel, error, logContext);
        setStatus(options.errorMessage);
        throw error;
      } finally {
        setIsSaving(false);
      }
    },
    [logContext, logLabel]
  );

  return {
    reviewMode,
    setReviewMode,
    isSaving,
    status,
    setStatus,
    runSave,
  };
}
