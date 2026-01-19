"use client";

import { useEffect, useMemo, useState } from "react";

import { useApp } from "@/contexts/AppContext";
import { apiClient } from "@/lib/api";
import { OrganizedModels, ProviderModels } from "@/types";

const emptyProvider: ProviderModels = { recommended: [], additional: [] };

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

  useEffect(() => {
    const storedOpenai = localStorage.getItem("openai_api_key") || "";
    const storedDeepinfra = localStorage.getItem("deepinfra_api_key") || "";
    const storedGemini = localStorage.getItem("gemini_api_key") || "";
    setOpenaiApiKey(storedOpenai);
    setDeepinfraApiKey(storedDeepinfra);
    setGeminiApiKey(storedGemini);
    loadModels(storedOpenai, storedDeepinfra, storedGemini);
  }, []);

  const loadModels = async (
    openaiKey = openaiApiKey,
    deepinfraKey = deepinfraApiKey,
    geminiKey = geminiApiKey
  ) => {
    setLoading(true);
    try {
      const organized = await apiClient.fetchOrganizedModels({
        openaiApiKey: openaiKey,
        deepinfraApiKey: deepinfraKey,
        geminiApiKey: geminiKey,
      });
      setOrganizedModels(organized.organized);

      const allModels = [
        ...organized.organized.openai.recommended,
        ...organized.organized.openai.additional,
        ...organized.organized.deepinfra.recommended,
        ...organized.organized.deepinfra.additional,
        ...organized.organized.gemini.recommended,
        ...organized.organized.gemini.additional,
      ];

      setAvailableModels(allModels);
      if (!state.selectedModel) {
        setSelectedModel(organized.default || allModels[0]?.id || "");
      }
    } catch (error) {
      console.error("Error loading models:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyChange = (
    value: string,
    type: "openai" | "deepinfra" | "gemini"
  ) => {
    if (type === "openai") {
      setOpenaiApiKey(value);
      localStorage.setItem("openai_api_key", value);
    } else if (type === "deepinfra") {
      setDeepinfraApiKey(value);
      localStorage.setItem("deepinfra_api_key", value);
    } else {
      setGeminiApiKey(value);
      localStorage.setItem("gemini_api_key", value);
    }
    if (value.length > 10) {
      loadModels(
        type === "openai" ? value : openaiApiKey,
        type === "deepinfra" ? value : deepinfraApiKey,
        type === "gemini" ? value : geminiApiKey
      );
    }
  };

  const selectedModelLabel = useMemo(() => {
    const model = state.availableModels.find(
      (item) => item.id === state.selectedModel
    );
    return model ? `${model.name} (${model.provider})` : "Model wählen";
  }, [state.availableModels, state.selectedModel]);

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((prev) => !prev)}
        className="flex items-center gap-2 rounded-full border border-white/30 bg-white/10 px-4 py-2 text-sm font-semibold text-white backdrop-blur-md transition hover:bg-white/20"
      >
        <span className="text-lg">🤖</span>
        <span className="hidden sm:inline">{selectedModelLabel}</span>
        <span className="sm:hidden">Modell</span>
      </button>

      {open && (
        <div className="absolute right-0 mt-3 w-[320px] rounded-2xl border border-white/30 bg-white/95 p-4 text-slate-800 shadow-2xl backdrop-blur">
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
                  <optgroup label="Empfohlen - OpenAI">
                    {organizedModels.openai.recommended.map((model) => (
                      <option key={model.id} value={model.id}>
                        {model.name}
                      </option>
                    ))}
                  </optgroup>
                  <optgroup label="Empfohlen - DeepInfra">
                    {organizedModels.deepinfra.recommended.map((model) => (
                      <option key={model.id} value={model.id}>
                        {model.name}
                      </option>
                    ))}
                  </optgroup>
                  <optgroup label="Empfohlen - Gemini">
                    {organizedModels.gemini.recommended.map((model) => (
                      <option key={model.id} value={model.id}>
                        {model.name}
                      </option>
                    ))}
                  </optgroup>
                  <optgroup label="Weitere - OpenAI">
                    {organizedModels.openai.additional.map((model) => (
                      <option key={model.id} value={model.id}>
                        {model.name}
                      </option>
                    ))}
                  </optgroup>
                  <optgroup label="Weitere - DeepInfra">
                    {organizedModels.deepinfra.additional.map((model) => (
                      <option key={model.id} value={model.id}>
                        {model.name}
                      </option>
                    ))}
                  </optgroup>
                  <optgroup label="Weitere - Gemini">
                    {organizedModels.gemini.additional.map((model) => (
                      <option key={model.id} value={model.id}>
                        {model.name}
                      </option>
                    ))}
                  </optgroup>
                </select>
              </div>

              <div className="space-y-3">
                <div>
                  <label className="text-xs font-semibold text-slate-500">OpenAI API Key</label>
                  <input
                    type="password"
                    value={openaiApiKey}
                    onChange={(event) =>
                      handleKeyChange(event.target.value, "openai")
                    }
                    placeholder="sk-..."
                    className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm"
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-500">DeepInfra API Key</label>
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
                  <label className="text-xs font-semibold text-slate-500">Gemini API Key</label>
                  <input
                    type="password"
                    value={geminiApiKey}
                    onChange={(event) =>
                      handleKeyChange(event.target.value, "gemini")
                    }
                    placeholder="AIza..."
                    className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm"
                  />
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
