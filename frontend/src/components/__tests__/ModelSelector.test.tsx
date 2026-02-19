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
    await user.click(screen.getByRole("button", { name: /GPT-5/i }));

    const modal = await screen.findByTestId("model-selector-modal");
    expect(modal.className).toContain("fixed");
    expect(modal.className).toContain("z-[70]");

    await user.click(screen.getByRole("button", { name: /Schließen/i }));
    expect(screen.queryByText("LLM-Auswahl")).not.toBeInTheDocument();
  });

  it("removes cleared API keys and only shows models for valid keys", async () => {
    mockUseApp.mockReturnValue({
      state: {
        selectedModel: "",
        availableModels: [],
      },
      setAvailableModels: jest.fn(),
      setSelectedModel: jest.fn(),
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
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: /modell/i }));
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
});
