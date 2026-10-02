import { describe, expect, it } from "vitest";

import { throughputLabel } from "@/lib/throughput";

describe("throughputLabel", () => {
  it("reports what each kind of model produced", () => {
    expect(throughputLabel({ tokens_per_sec: 62.5 })).toBe("62.5 tok/s");
    expect(throughputLabel({ chars_per_sec: 380 })).toBe("380 chars/s");
    expect(throughputLabel({ realtime_factor: 1.7 })).toBe("1.7x realtime");
  });

  it("says nothing when a service reports no usage", () => {
    expect(throughputLabel({})).toBeNull();
  });
});
