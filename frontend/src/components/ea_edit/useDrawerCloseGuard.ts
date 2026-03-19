"use client";

import { useEffect, useMemo, useState } from "react";

type TabInfo = { title: string };

type UseDrawerCloseGuardArgs<TTab extends string> = {
  open: boolean;
  sessionKey: string;
  tabs: Record<TTab, TabInfo>;
  onClose: () => void;
  onActivateTab: (tab: TTab) => void;
};

type UseDrawerCloseGuardResult<TTab extends string> = {
  hasUnsavedChanges: boolean;
  closeConfirmOpen: boolean;
  closeGuardHint: string | null;
  dirtyTabs: TTab[];
  markTabDirty: (tab: TTab, dirty: boolean) => void;
  requestClose: () => void;
  continueEditing: () => void;
  discardAndClose: () => void;
  leadToSave: () => void;
};

export function useDrawerCloseGuard<TTab extends string>({
  open,
  sessionKey,
  tabs,
  onClose,
  onActivateTab,
}: UseDrawerCloseGuardArgs<TTab>): UseDrawerCloseGuardResult<TTab> {
  const emptyUnsavedByTab = useMemo(() => {
    const entries = (Object.keys(tabs) as TTab[]).map((tab) => [tab, false]);
    return Object.fromEntries(entries) as Record<TTab, boolean>;
  }, [tabs]);

  const [unsavedByTab, setUnsavedByTab] =
    useState<Record<TTab, boolean>>(emptyUnsavedByTab);
  const [closeConfirmOpen, setCloseConfirmOpen] = useState(false);
  const [closeGuardHint, setCloseGuardHint] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      return;
    }
    setCloseConfirmOpen(false);
    setCloseGuardHint(null);
    setUnsavedByTab(emptyUnsavedByTab);
  }, [open, emptyUnsavedByTab]);

  useEffect(() => {
    setCloseConfirmOpen(false);
    setCloseGuardHint(null);
    setUnsavedByTab(emptyUnsavedByTab);
  }, [sessionKey, emptyUnsavedByTab]);

  const dirtyTabs = useMemo(
    () => (Object.keys(unsavedByTab) as TTab[]).filter((tab) => unsavedByTab[tab]),
    [unsavedByTab]
  );
  const hasUnsavedChanges = dirtyTabs.length > 0;

  useEffect(() => {
    if (!closeGuardHint) {
      return;
    }
    if (dirtyTabs.length === 0) {
      setCloseGuardHint(null);
      return;
    }
    setCloseGuardHint(
      `Bitte zuerst prüfen und speichern in: ${dirtyTabs
        .map((tab) => tabs[tab].title)
        .join(", ")}.`
    );
  }, [closeGuardHint, dirtyTabs, tabs]);

  const markTabDirty = (tab: TTab, dirty: boolean) => {
    setUnsavedByTab((prev) => {
      if (prev[tab] === dirty) {
        return prev;
      }
      return { ...prev, [tab]: dirty };
    });
  };

  const requestClose = () => {
    if (!hasUnsavedChanges) {
      onClose();
      return;
    }
    setCloseGuardHint(null);
    setCloseConfirmOpen(true);
  };

  const continueEditing = () => {
    setCloseConfirmOpen(false);
  };

  const discardAndClose = () => {
    setCloseConfirmOpen(false);
    setCloseGuardHint(null);
    onClose();
  };

  const leadToSave = () => {
    if (dirtyTabs.length === 0) {
      onClose();
      return;
    }
    const firstDirtyTab = dirtyTabs[0];
    onActivateTab(firstDirtyTab);
    setCloseGuardHint(
      `Bitte zuerst prüfen und speichern in: ${dirtyTabs
        .map((tab) => tabs[tab].title)
        .join(", ")}.`
    );
    setCloseConfirmOpen(false);
  };

  return {
    hasUnsavedChanges,
    closeConfirmOpen,
    closeGuardHint,
    dirtyTabs,
    markTabDirty,
    requestClose,
    continueEditing,
    discardAndClose,
    leadToSave,
  };
}
