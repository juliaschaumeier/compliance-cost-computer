describe("isLlmConsoleEnabled", () => {
  const originalNodeEnv = process.env.NODE_ENV;
  const originalExplicit = process.env.NEXT_PUBLIC_ENABLE_LLM_CONSOLE;

  afterEach(() => {
    process.env.NODE_ENV = originalNodeEnv;
    if (typeof originalExplicit === "string") {
      process.env.NEXT_PUBLIC_ENABLE_LLM_CONSOLE = originalExplicit;
    } else {
      delete process.env.NEXT_PUBLIC_ENABLE_LLM_CONSOLE;
    }
    jest.resetModules();
  });

  it("defaults to enabled without explicit flag", async () => {
    delete process.env.NEXT_PUBLIC_ENABLE_LLM_CONSOLE;
    const { isLlmConsoleEnabled } = await import("@/lib/llmConsoleConfig");
    expect(isLlmConsoleEnabled()).toBe(true);
  });

  it("still defaults to enabled even in production runtime", async () => {
    process.env.NODE_ENV = "production";
    delete process.env.NEXT_PUBLIC_ENABLE_LLM_CONSOLE;
    const { isLlmConsoleEnabled } = await import("@/lib/llmConsoleConfig");
    expect(isLlmConsoleEnabled()).toBe(true);
  });

  it("respects explicit disable override", async () => {
    process.env.NODE_ENV = "production";
    process.env.NEXT_PUBLIC_ENABLE_LLM_CONSOLE = "false";
    const { isLlmConsoleEnabled } = await import("@/lib/llmConsoleConfig");
    expect(isLlmConsoleEnabled()).toBe(false);
  });

  it("respects explicit enable/disable override", async () => {
    process.env.NODE_ENV = "production";
    process.env.NEXT_PUBLIC_ENABLE_LLM_CONSOLE = "true";
    let llmConfig = await import("@/lib/llmConsoleConfig");
    expect(llmConfig.isLlmConsoleEnabled()).toBe(true);

    jest.resetModules();
    process.env.NEXT_PUBLIC_ENABLE_LLM_CONSOLE = "0";
    llmConfig = await import("@/lib/llmConsoleConfig");
    expect(llmConfig.isLlmConsoleEnabled()).toBe(false);
  });
});
