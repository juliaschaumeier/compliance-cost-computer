import { buildLlmRequestOptions } from "@/lib/api";

describe("buildLlmRequestOptions", () => {
  it("builds model/provider and reads API keys from provided storage", () => {
    const storage = {
      getItem: (key: string) => {
        if (key === "openai_api_key") return "sk-test";
        if (key === "deepinfra_api_key") return "di-test";
        if (key === "gemini_api_key") return "gm-test";
        return null;
      },
    };

    const result = buildLlmRequestOptions({
      selectedModel: "gpt-5",
      availableModels: [{ id: "gpt-5", name: "GPT-5", provider: "OpenAI" }],
      storage,
    });

    expect(result).toEqual({
      model: "gpt-5",
      provider: "openai",
      keys: {
        openaiApiKey: "sk-test",
        deepinfraApiKey: "di-test",
        geminiApiKey: "gm-test",
      },
    });
  });

  it("returns undefined model/provider when no selected model is set", () => {
    const result = buildLlmRequestOptions({
      selectedModel: "",
      availableModels: [{ id: "gpt-5", name: "GPT-5", provider: "OpenAI" }],
      storage: { getItem: () => null },
    });

    expect(result).toEqual({
      model: undefined,
      provider: undefined,
      keys: {
        openaiApiKey: undefined,
        deepinfraApiKey: undefined,
        geminiApiKey: undefined,
      },
    });
  });

  it("routes DeepInfra Claude models with the DeepInfra provider", () => {
    const result = buildLlmRequestOptions({
      selectedModel: "anthropic/claude-sonnet-4-6",
      availableModels: [
        {
          id: "anthropic/claude-sonnet-4-6",
          name: "Claude Sonnet 4 6",
          provider: "DeepInfra",
        },
      ],
      storage: { getItem: () => null },
    });

    expect(result.provider).toBe("deepinfra");
  });
});
