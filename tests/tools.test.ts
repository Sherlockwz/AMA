import { describe, expect, it } from "vitest";
import { createRetrievalPreview } from "../tools/index.ts";

describe("createRetrievalPreview", () => {
  it("formats multi-granularity retrievals", () => {
    const preview = createRetrievalPreview({
      text_match_results: [{ content: "raw memory" }],
      fact_match_results: [{ content: "structured fact" }],
      episodes_results: [{ content: "episode summary" }],
    });

    expect(preview).toContain("Text:");
    expect(preview).toContain("structured fact");
    expect(preview).toContain("episode summary");
  });

  it("handles empty retrievals", () => {
    expect(createRetrievalPreview([])).toBe("No retrieval results.");
  });
});
