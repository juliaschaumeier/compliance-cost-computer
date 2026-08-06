"use client";

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import ModelSelector from "@/components/ModelSelector";
import { apiClient } from "@/lib/api";
import { useApp } from "@/contexts/AppContext";

jest.mock("@/lib/api", () => ({
  apiClient: {
    fetchOrganizedModels: jest.fn(),
  },
}));

jest.mock("@/contexts/AppContext", () => ({
  useApp: jest.fn(),
}));

const mockUseApp = useApp as jest.Mock;
const mockFetchModels = apiClient.fetchOrganizedModels as jest.Mock;

describe("ModelSelector", () => {
  beforeEach(() => {
    mockFetchModels.mockReset();
    localStorage.clear();
  });

  it("renders the chooser in a portal and allows closing", async () => {
    mockUseApp.mockReturnValue({
      state: {
        selectedModel: "gpt-5",
        availableModels: [{ id: "gpt-5", name: "GPT-5", provider: "OpenAI" }],
      },
      setAvailableModels: jest.fn(),
      setSelectedModel: jest.fn(),
    });
    mockFetchModels.mockResolvedValue({
      organized: {
        openai: { recommended: [], additional: [] },
        deepinfra: { recommended: [], additional: [] },
        gemini: { recommended: [], additional: [] },
      },
      default: "gpt-5",
    });

    render(<ModelSelector />);

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /llm-auswahl öffnen/i }));

    const modal = await screen.findByTestId("model-selector-modal");
    expect(modal.className).toContain("fixed");
    expect(modal.className).toContain("z-[70]");

    await user.click(
      screen.getByRole("button", { name: "LLM-Dialog schließen" })
    );
    expect(screen.queryByText("LLM-Auswahl")).not.toBeInTheDocument();
  });

  it("stores cleared API keys and uses backend-returned model availability", async () => {
    mockUseApp.mockReturnValue({
      state: {
        selectedModel: "",
        availableModels: [],
      },
      setAvailableModels: jest.fn(),
      setSelectedModel: jest.fn(),
    });
    mockFetchModels.mockImplementation((keys) => {
      const openaiModels = keys.openaiApiKey
        ? {
            recommended: [{ id: "gpt-5", name: "GPT-5", provider: "OpenAI" }],
            additional: [],
          }
        : { recommended: [], additional: [] };
      return Promise.resolve({
        organized: {
          openai: openaiModels,
          deepinfra: { recommended: [], additional: [] },
          gemini: { recommended: [], additional: [] },
        },
        default: "gpt-5",
      });
    });

    render(<ModelSelector />);
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: /llm-auswahl öffnen/i }));
    await screen.findByTestId("model-selector-modal");

    expect(screen.queryByRole("option", { name: "GPT-5" })).not.toBeInTheDocument();

    const openAiInput = screen.getByPlaceholderText("sk-...");
    await user.type(openAiInput, "sk-very-valid-test-key");
    await waitFor(() =>
      expect(
        screen.getByRole("option", {
          name: "GPT-5",
        })
      ).toBeInTheDocument()
    );
    const storedKey = localStorage.getItem("openai_api_key");
    expect(storedKey).toMatch(/^sk-/);
    expect(storedKey && storedKey.length).toBeGreaterThan(10);

    const refreshedOpenAiInput = screen.getByPlaceholderText("sk-...");
    await user.click(refreshedOpenAiInput);
    await user.clear(refreshedOpenAiInput);
    await waitFor(() =>
      expect(screen.queryByRole("option", { name: "GPT-5" })).not.toBeInTheDocument()
    );
    expect(localStorage.getItem("openai_api_key")).toBeNull();
  });

  it("shows models supplied by backend env keys when no browser key is stored", async () => {
    const setAvailableModels = jest.fn();
    mockUseApp.mockReturnValue({
      state: {
        selectedModel: "",
        availableModels: [],
      },
      setAvailableModels,
      setSelectedModel: jest.fn(),
    });
    mockFetchModels.mockResolvedValue({
      organized: {
        openai: { recommended: [], additional: [] },
        deepinfra: { recommended: [], additional: [] },
        gemini: {
          recommended: [
            {
              id: "gemini-3.5-flash",
              name: "Gemini 3.5 flash",
              provider: "Gemini",
            },
          ],
          additional: [],
        },
      },
      default: "gemini-3.5-flash",
    });

    render(<ModelSelector />);

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /llm-auswahl öffnen/i }));

    expect(
      await screen.findByRole("option", {
        name: "gemini-3.5-flash · $1.50 in / $9 out",
      })
    ).toBeInTheDocument();
    expect(setAvailableModels).toHaveBeenCalledWith([
      {
        id: "gemini-3.5-flash",
        name: "Gemini 3.5 flash",
        provider: "Gemini",
      },
    ]);
  });

  it("keeps selected model label visible after loading models", async () => {
    const setAvailableModels = jest.fn();
    const setSelectedModel = jest.fn();
    localStorage.setItem("openai_api_key", "sk-very-valid-test-key");
    mockUseApp.mockReturnValue({
      state: {
        selectedModel: "gpt-5",
        availableModels: [],
      },
      setAvailableModels,
      setSelectedModel,
    });
    mockFetchModels.mockResolvedValue({
      organized: {
        openai: {
          recommended: [{ id: "gpt-5", name: "GPT-5", provider: "OpenAI" }],
          additional: [],
        },
        deepinfra: { recommended: [], additional: [] },
        gemini: { recommended: [], additional: [] },
      },
      default: "gpt-5",
    });

    render(<ModelSelector />);

    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: /llm-auswahl öffnen/i })
      ).toBeInTheDocument()
    );
    const visibleLabel = screen.getByText("GPT-5");
    expect(visibleLabel).toBeInTheDocument();
    expect(visibleLabel).toHaveClass("sm:[display:-webkit-box]");
    expect(visibleLabel).not.toHaveClass("sm:inline-block");
    expect(setSelectedModel).not.toHaveBeenCalledWith("");
    expect(setAvailableModels).toHaveBeenCalled();
  });

  it("shows dated recommendation groups with price guidance on recommended models", async () => {
    localStorage.setItem("openai_api_key", "sk-very-valid-test-key");
    localStorage.setItem("deepinfra_api_key", "di-very-valid-test-key");
    localStorage.setItem("gemini_api_key", "AIza-very-valid-test-key");
    const setSelectedModel = jest.fn();
    mockUseApp.mockReturnValue({
      state: {
        selectedModel: "",
        availableModels: [],
      },
      setAvailableModels: jest.fn(),
      setSelectedModel,
    });
    mockFetchModels.mockResolvedValue({
      organized: {
        openai: {
          recommended: [{ id: "gpt-5.4", name: "GPT 5.4", provider: "OpenAI" }],
          additional: [],
        },
        deepinfra: {
          recommended: [
            {
              id: "deepseek-ai/DeepSeek-V3.2",
              name: "DeepSeek V3.2",
              provider: "DeepInfra",
            },
          ],
          additional: [],
        },
        gemini: {
          recommended: [
            {
              id: "gemini-3.5-flash",
              name: "Gemini 3.5 flash",
              provider: "Gemini",
            },
          ],
          additional: [],
        },
      },
      default: "gpt-5.4",
    });

    render(<ModelSelector />);

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /llm-auswahl öffnen/i }));

    expect(
      await screen.findByRole("option", {
        name: "gpt-5.4 · $2.50 in / $15 out",
      })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("option", {
        name: "deepseek-ai/DeepSeek-V3.2 · $0.26 in / $0.38 out",
      })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("option", {
        name: "gemini-3.5-flash · $1.50 in / $9 out",
      })
    ).toBeInTheDocument();
    expect(
      document.querySelector('optgroup[label="Empfohlen - OpenAI (Stand 02.07.2026)"]')
    ).toBeInTheDocument();
    expect(
      document.querySelector('optgroup[label="Empfohlen - DeepInfra (Stand 02.07.2026)"]')
    ).toBeInTheDocument();
    expect(
      document.querySelector('optgroup[label="Empfohlen - Gemini (Stand 02.07.2026)"]')
    ).toBeInTheDocument();

    await user.selectOptions(
      screen.getByLabelText("Modell"),
      "gemini-3.5-flash"
    );
    expect(setSelectedModel).toHaveBeenCalledWith("gemini-3.5-flash");
  });

  it("only opens from the chevron control in the header split button", async () => {
    mockUseApp.mockReturnValue({
      state: {
        selectedModel: "gpt-5",
        availableModels: [{ id: "gpt-5", name: "GPT-5", provider: "OpenAI" }],
      },
      setAvailableModels: jest.fn(),
      setSelectedModel: jest.fn(),
    });
    mockFetchModels.mockResolvedValue({
      organized: {
        openai: { recommended: [], additional: [] },
        deepinfra: { recommended: [], additional: [] },
        gemini: { recommended: [], additional: [] },
      },
      default: "gpt-5",
    });

    render(<ModelSelector />);

    const user = userEvent.setup();
    await user.click(screen.getByText("LLM:"));
    expect(screen.queryByTestId("model-selector-modal")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /llm-auswahl öffnen/i }));
    expect(await screen.findByTestId("model-selector-modal")).toBeInTheDocument();
  });
});
