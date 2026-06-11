"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";

import { useApp } from "@/contexts/AppContext";
import { apiClient } from "@/lib/api";
import { logClientError } from "@/lib/errorFeedback";
import { Model, OrganizedModels, ProviderModels } from "@/types";

const emptyProvider: ProviderModels = { recommended: [], additional: [] };
const isLikelyValidApiKey = (value: string) => value.trim().length > 10;
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

const buildSelectedModelLabels = (
  selectedModel: string,
  organizedModels: OrganizedModels,
  availableModels: Model[]
) => {
  if (!selectedModel) {
    return {
      button: "LLM",
      full: "Modell wählen",
    };
  }
  const knownModels = flattenModels(organizedModels);
  const model =
    knownModels.find((item) => item.id === selectedModel) ||
    availableModels.find((item) => item.id === selectedModel);
  if (!model) {
    return {
      button: `LLM: ${compactModelName(selectedModel)}`,
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
  const [menuPos, setMenuPos] = useState<{ top: number; left: number }>({
    top: 72,
    left: 16,
  });
  const [isMounted, setIsMounted] = useState(false);
  const modelsLoadedRef = useRef(false);

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
    const updatePosition = () => {
      const rect = triggerRef.current?.getBoundingClientRect();
      if (!rect) {
        return;
      }
      const width = 320;
      const padding = 12;
      const left = Math.min(
        Math.max(padding, rect.right - width),
        window.innerWidth - width - padding
      );
      setMenuPos({
        top: rect.bottom + 12,
        left,
      });
    };
    updatePosition();
    window.addEventListener("resize", updatePosition);
    window.addEventListener("scroll", updatePosition, true);
    return () => {
      window.removeEventListener("resize", updatePosition);
      window.removeEventListener("scroll", updatePosition, true);
    };
  }, [open]);

  const menuContent = (
    <div
      data-testid="model-selector-modal"
      className="fixed z-[70] w-[320px] rounded-2xl border border-white/30 bg-white/95 p-4 text-slate-800 shadow-2xl backdrop-blur"
      style={{ top: menuPos.top, left: menuPos.left }}
    >
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">LLM-Auswahl</h3>
        <button
          onClick={() => setOpen(false)}
          className="rounded-full border border-slate-200 px-2 py-1 text-xs"
        >
          Schließen
        </button>
      </div>

      {loading ? (
        <p className="mt-4 text-sm text-slate-500">Modelle werden geladen...</p>
      ) : (
        <div className="mt-4 space-y-4">
          <div>
            <label className="text-xs font-semibold text-slate-500">Modell</label>
            <select
              value={state.selectedModel}
              onChange={(event) => setSelectedModel(event.target.value)}
              className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm"
            >
              <option value="">Modell auswählen</option>
              <optgroup label="Empfohlen - OpenAI">
                {visibleOrganizedModels.openai.recommended.map((model) => (
                  <option key={model.id} value={model.id}>
                    {model.name}
                  </option>
                ))}
              </optgroup>
              <optgroup label="Empfohlen - DeepInfra">
                {visibleOrganizedModels.deepinfra.recommended.map((model) => (
                  <option key={model.id} value={model.id}>
                    {model.name}
                  </option>
                ))}
              </optgroup>
              <optgroup label="Empfohlen - Gemini">
                {visibleOrganizedModels.gemini.recommended.map((model) => (
                  <option key={model.id} value={model.id}>
                    {model.name}
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
          </div>

          <div className="space-y-3">
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
      <button
        onClick={() => setOpen((prev) => !prev)}
        className="flex items-center gap-2 rounded-full border border-white/30 bg-white/10 px-3 py-2 text-sm font-semibold text-white backdrop-blur-md transition hover:bg-white/20"
        title={selectedModelLabels.full}
        aria-label={`LLM-Auswahl öffnen: ${selectedModelLabels.full}`}
      >
        <span className="text-lg">🤖</span>
        <span className="hidden max-w-32 overflow-hidden text-left leading-tight text-ellipsis [-webkit-box-orient:vertical] [-webkit-line-clamp:2] sm:[display:-webkit-box]">
          {selectedModelLabels.button}
        </span>
        <span className="sm:hidden">Modell</span>
      </button>
      {open && isMounted ? createPortal(menuContent, document.body) : null}
    </div>
  );
}
