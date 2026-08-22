import { afterEach, describe, expect, it } from "vitest";
import { parseAMAConfig } from "../config.ts";

const originalApiKey = process.env.AMA_TEST_API_KEY;

afterEach(() => {
  if (originalApiKey === undefined) {
    delete process.env.AMA_TEST_API_KEY;
  } else {
    process.env.AMA_TEST_API_KEY = originalApiKey;
  }
});

describe("parseAMAConfig", () => {
  it("applies stable defaults", () => {
    const config = parseAMAConfig({
      llmApiKey: "test-key",
      llmBaseUrl: "https://example.com/v1/chat/completions",
      embeddingApiUrl: "https://example.com/v1/embeddings",
    });

    expect(config.needsSetup).toBe(false);
    expect(config.modelMemory).toBe("gpt-4o-mini");
    expect(config.sidecarPort).toBe(8321);
    expect(config.dataDir).toBe("./ama-data");
  });

  it("resolves environment placeholders without exposing the value", () => {
    process.env.AMA_TEST_API_KEY = "resolved-secret";
    const config = parseAMAConfig({
      llmApiKey: "${AMA_TEST_API_KEY}",
      llmBaseUrl: "https://example.com/v1/chat/completions",
      embeddingApiUrl: "https://example.com/v1/embeddings",
    });

    expect(config.llmApiKey).toBe("resolved-secret");
    expect(config.needsSetup).toBe(false);
  });

  it("marks incomplete configuration as needing setup", () => {
    expect(parseAMAConfig({}).needsSetup).toBe(true);
  });
});
