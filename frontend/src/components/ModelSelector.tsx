"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";

import { useApp } from "@/contexts/AppContext";
import { apiClient } from "@/lib/api";
import { logClientError } from "@/lib/errorFeedback";
import { useAnchoredPopoverPosition } from "@/lib/useAnchoredPopoverPosition";
import { Model, OrganizedModels, ProviderModels } from "@/types";

const emptyProvider: ProviderModels = { recommended: [], additional: [] };
const isLikelyValidApiKey = (value: string) => value.trim().length > 10;
const modelMenuWidth = 340;
const recommendedModelsCheckedAt = "02.07.2026";
const recommendedModelPriceLabels: Record<string, string> = {
  "gpt-5.4": "$2.50 in / $15 out",
  "gpt-5.4-mini": "$0.75 in / $4.50 out",
  "gemini-3.1-pro-preview": "≤200k $2/$12 · >200k $4/$18",
  "gemini-3.5-flash": "$1.50 in / $9 out",
  "gemini-3-flash-preview": "$0.50 in / $3 out",
  "anthropic/claude-sonnet-4-6": "$3 in / $15 out",
  "deepseek-ai/DeepSeek-V3.2": "$0.26 in / $0.38 out",
};
const flattenModels = (organized: OrganizedModels) => [
  ...organized.openai.recommended,
  ...organized.openai.additional,
  ...organized.deepinfra.recommended,
  ...organized.deepinfra.additional,
  ...organized.gemini.recommended,
  ...organized.gemini.additional,
];
const compactModelName = (value: string) =>
  value
    .replace(/^.+\//, "")
    .replace(/^gemini-/i, "g-")
    .replace(/^deep-research-/i, "dr-");
const recommendationGroupLabel = (provider: string) =>
  `Empfohlen - ${provider} (Stand ${recommendedModelsCheckedAt})`;
const modelOptionLabel = (model: Model, recommended = false) => {
  const priceLabel = recommended ? recommendedModelPriceLabels[model.id] : undefined;
  if (!priceLabel) {
    return model.name;
  }
  return `${model.id} · ${priceLabel}`;
};

const buildSelectedModelLabels = (
  selectedModel: string,
  organizedModels: OrganizedModels,
  availableModels: Model[]
) => {
  if (!selectedModel) {
    return {
      button: "Modell wählen",
      full: "Modell wählen",
    };
  }
  const knownModels = flattenModels(organizedModels);
  const model =
    knownModels.find((item) => item.id === selectedModel) ||
    availableModels.find((item) => item.id === selectedModel);
  if (!model) {
    return {
      button: compactModelName(selectedModel),
      full: selectedModel,
    };
  }
  return {
    button: compactModelName(model.name),
    full: `${model.name} (${model.provider})`,
  };
};

export default function ModelSelector() {
  const { state, setAvailableModels, setSelectedModel } = useApp();
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [openaiApiKey, setOpenaiApiKey] = useState("");
  const [deepinfraApiKey, setDeepinfraApiKey] = useState("");
  const [geminiApiKey, setGeminiApiKey] = useState("");
  const [organizedModels, setOrganizedModels] = useState<OrganizedModels>({
    openai: emptyProvider,
    deepinfra: emptyProvider,
    gemini: emptyProvider,
  });
  const triggerRef = useRef<HTMLDivElement | null>(null);
  const menuRef = useRef<HTMLDivElement | null>(null);
  const [isMounted, setIsMounted] = useState(false);
  const modelsLoadedRef = useRef(false);
  const { position: menuPos } = useAnchoredPopoverPosition({
    open,
    triggerRef,
    width: modelMenuWidth,
    align: "right",
    offset: 12,
    padding: 12,
  });

  useEffect(() => {
    setIsMounted(true);
  }, []);

  const loadModels = useCallback(async (
    openaiKey: string,
    deepinfraKey: string,
    geminiKey: string
  ) => {
    setLoading(true);
    try {
      const organized = await apiClient.fetchOrganizedModels({
        openaiApiKey: isLikelyValidApiKey(openaiKey)
          ? openaiKey.trim()
          : undefined,
        deepinfraApiKey: isLikelyValidApiKey(deepinfraKey)
          ? deepinfraKey.trim()
          : undefined,
        geminiApiKey: isLikelyValidApiKey(geminiKey)
          ? geminiKey.trim()
          : undefined,
      });
      setOrganizedModels(organized.organized);
    } catch (error) {
      logClientError("ModelSelector.loadModels", error);
    } finally {
      modelsLoadedRef.current = true;
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const storedOpenai = localStorage.getItem("openai_api_key") || "";
    const storedDeepinfra = localStorage.getItem("deepinfra_api_key") || "";
    const storedGemini = localStorage.getItem("gemini_api_key") || "";
    setOpenaiApiKey(storedOpenai);
    setDeepinfraApiKey(storedDeepinfra);
    setGeminiApiKey(storedGemini);
    loadModels(storedOpenai, storedDeepinfra, storedGemini);
  }, [loadModels]);

  const visibleOrganizedModels = useMemo<OrganizedModels>(() => {
    const hasOpenAiKey = isLikelyValidApiKey(openaiApiKey);
    const hasDeepinfraKey = isLikelyValidApiKey(deepinfraApiKey);
    const hasGeminiKey = isLikelyValidApiKey(geminiApiKey);
    return {
      openai: hasOpenAiKey ? organizedModels.openai : emptyProvider,
      deepinfra: hasDeepinfraKey ? organizedModels.deepinfra : emptyProvider,
      gemini: hasGeminiKey ? organizedModels.gemini : emptyProvider,
    };
  }, [organizedModels, openaiApiKey, deepinfraApiKey, geminiApiKey]);

  useEffect(() => {
    const allModels = flattenModels(visibleOrganizedModels);
    setAvailableModels(allModels);
    if (!modelsLoadedRef.current) {
      return;
    }
    const hasSelection = allModels.some((model) => model.id === state.selectedModel);
    if (!hasSelection && state.selectedModel) {
      setSelectedModel("");
    }
  }, [
    visibleOrganizedModels,
    state.selectedModel,
    setAvailableModels,
    setSelectedModel,
  ]);

  const handleKeyChange = (
    value: string,
    type: "openai" | "deepinfra" | "gemini"
  ) => {
    const normalized = value.trim();
    if (type === "openai") {
      setOpenaiApiKey(value);
      if (normalized) {
        localStorage.setItem("openai_api_key", value);
      } else {
        localStorage.removeItem("openai_api_key");
      }
    } else if (type === "deepinfra") {
      setDeepinfraApiKey(value);
      if (normalized) {
        localStorage.setItem("deepinfra_api_key", value);
      } else {
        localStorage.removeItem("deepinfra_api_key");
      }
    } else {
      setGeminiApiKey(value);
      if (normalized) {
        localStorage.setItem("gemini_api_key", value);
      } else {
        localStorage.removeItem("gemini_api_key");
      }
    }
    if (isLikelyValidApiKey(value) || normalized.length === 0) {
      loadModels(
        type === "openai" ? value : openaiApiKey,
        type === "deepinfra" ? value : deepinfraApiKey,
        type === "gemini" ? value : geminiApiKey
      );
    }
  };

  const selectedModelLabels = useMemo(() => {
    return buildSelectedModelLabels(
      state.selectedModel,
      organizedModels,
      state.availableModels
    );
  }, [organizedModels, state.availableModels, state.selectedModel]);

  useEffect(() => {
    if (!open) {
      return;
    }
    const handlePointerDown = (event: PointerEvent) => {
      const target = event.target as Node;
      if (menuRef.current?.contains(target) || triggerRef.current?.contains(target)) {
        return;
      }
      setOpen(false);
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
      }
    };
    document.addEventListener("pointerdown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open]);

  const menuContent = (
    <div
      ref={menuRef}
      data-testid="model-selector-modal"
      className="fixed z-[70] rounded-2xl border border-slate-200 bg-white p-4 text-slate-800 shadow-2xl"
      style={{ top: menuPos.top, left: menuPos.left, width: modelMenuWidth }}
    >
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">LLM-Auswahl</h3>
        <button
          onClick={() => setOpen(false)}
          className="flex h-7 w-7 items-center justify-center rounded-full text-sm font-semibold text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
          aria-label="LLM-Dialog schließen"
        >
          ×
        </button>
      </div>

      {loading ? (
        <p className="mt-4 text-sm text-slate-500">Modelle werden geladen...</p>
      ) : (
        <div className="mt-4 space-y-4">
          <div>
            <label
              htmlFor="model-selector-select"
              className="text-xs font-semibold text-slate-500"
            >
              Modell
            </label>
            <select
              id="model-selector-select"
              value={state.selectedModel}
              onChange={(event) => setSelectedModel(event.target.value)}
              className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm"
            >
              <option value="">Modell auswählen</option>
              <optgroup label={recommendationGroupLabel("OpenAI")}>
                {visibleOrganizedModels.openai.recommended.map((model) => (
                  <option key={model.id} value={model.id}>
                    {modelOptionLabel(model, true)}
                  </option>
                ))}
              </optgroup>
              <optgroup label={recommendationGroupLabel("DeepInfra")}>
                {visibleOrganizedModels.deepinfra.recommended.map((model) => (
                  <option key={model.id} value={model.id}>
                    {modelOptionLabel(model, true)}
                  </option>
                ))}
              </optgroup>
              <optgroup label={recommendationGroupLabel("Gemini")}>
                {visibleOrganizedModels.gemini.recommended.map((model) => (
                  <option key={model.id} value={model.id}>
                    {modelOptionLabel(model, true)}
                  </option>
                ))}
              </optgroup>
              <optgroup label="Weitere - OpenAI">
                {visibleOrganizedModels.openai.additional.map((model) => (
                  <option key={model.id} value={model.id}>
                    {model.name}
                  </option>
                ))}
              </optgroup>
              <optgroup label="Weitere - DeepInfra">
                {visibleOrganizedModels.deepinfra.additional.map((model) => (
                  <option key={model.id} value={model.id}>
                    {model.name}
                  </option>
                ))}
              </optgroup>
              <optgroup label="Weitere - Gemini">
                {visibleOrganizedModels.gemini.additional.map((model) => (
                  <option key={model.id} value={model.id}>
                    {model.name}
                  </option>
                ))}
              </optgroup>
            </select>
            {flattenModels(visibleOrganizedModels).length === 0 ? (
              <p className="mt-2 text-[11px] leading-4 text-slate-500">
                Kein Modell verfügbar. Bitte einen gültigen API-Schlüssel
                eintragen oder prüfen.
              </p>
            ) : null}
            <p className="mt-2 text-[11px] leading-4 text-slate-500">
              Dieses Modell wird für zukünftige Prompts verwendet. Bereits
              berechnete Schritte ändern sich dadurch nicht.
            </p>
          </div>

          <div className="space-y-3 border-t border-slate-100 pt-4">
            <div>
              <div className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                API-Schlüssel
              </div>
              <p className="mt-1 text-[11px] leading-4 text-slate-500">
                Für Deep Research wird ein Gemini API Key benötigt.
              </p>
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-500">
                OpenAI API Key
              </label>
              <input
                type="password"
                value={openaiApiKey}
                onChange={(event) => handleKeyChange(event.target.value, "openai")}
                placeholder="sk-..."
                className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-500">
                DeepInfra API Key
              </label>
              <input
                type="password"
                value={deepinfraApiKey}
                onChange={(event) =>
                  handleKeyChange(event.target.value, "deepinfra")
                }
                placeholder="di-..."
                className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-500">
                Gemini API Key
              </label>
              <input
                type="password"
                value={geminiApiKey}
                onChange={(event) => handleKeyChange(event.target.value, "gemini")}
                placeholder="AIza..."
                className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm"
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );

  return (
    <div ref={triggerRef} className="relative">
      <div
        className="flex h-10 items-stretch overflow-hidden rounded-xl border border-white/30 bg-white/10 text-sm font-semibold text-white shadow-sm backdrop-blur-md"
        title={selectedModelLabels.full}
      >
        <div className="flex items-center gap-2 px-3 py-2">
          <svg
            aria-hidden="true"
            viewBox="0 0 24 24"
            className="h-6 w-6 shrink-0"
          >
            <path
              d="M11.5 3.5 13.2 8.8 18.5 10.5 13.2 12.2 11.5 17.5 9.8 12.2 4.5 10.5 9.8 8.8 11.5 3.5Z"
              fill="none"
              stroke="currentColor"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="1.7"
            />
            <path
              d="M18.5 3.5v4"
              fill="none"
              stroke="currentColor"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="1.7"
            />
            <path
              d="M20.5 5.5h-4"
              fill="none"
              stroke="currentColor"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="1.7"
            />
          </svg>
          <span>LLM:</span>
          <span className="hidden max-w-32 overflow-hidden text-left leading-tight text-ellipsis [-webkit-box-orient:vertical] [-webkit-line-clamp:2] sm:[display:-webkit-box]">
            {selectedModelLabels.button}
          </span>
          <span className="sm:hidden">Modell</span>
        </div>
        <button
          type="button"
          onClick={() => setOpen((prev) => !prev)}
          title="LLM-Auswahl"
          aria-label={open ? "LLM-Auswahl schließen" : "LLM-Auswahl öffnen"}
          aria-expanded={open}
          className="h-full border-l border-white/20 px-3 py-2 transition hover:bg-white/10"
        >
          {open ? "⌃" : "⌄"}
        </button>
      </div>
      {open && isMounted ? createPortal(menuContent, document.body) : null}
    </div>
  );
}
