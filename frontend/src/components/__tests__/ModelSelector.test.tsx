"use client";

import { render, screen } from "@testing-library/react";
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
});
