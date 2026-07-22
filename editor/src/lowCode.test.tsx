import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { ReferenceSelect } from "./LowCodeWidgets";

const references = [
  { id: "actor.elda", type: "actor" as const, label: "艾尔达", source: "world_state.json", valid: true },
  { id: "actor.missing", type: "actor" as const, label: "actor.missing", source: "scene.json", valid: false },
];

describe("low-code reference widgets", () => {
  afterEach(() => cleanup());

  it("renders labels and preserves a missing reference", () => {
    render(<ReferenceSelect value="actor.unknown" options={references} onChange={() => undefined} />);
    expect(screen.getByRole("option", { name: "actor.unknown（缺失引用）" })).toBeDefined();
    expect(screen.getByRole("option", { name: "艾尔达 · actor.elda" })).toBeDefined();
  });

  it("emits the selected stable id", () => {
    let selected = "";
    render(<ReferenceSelect value="" options={references} onChange={(value) => { selected = value; }} />);
    fireEvent.change(screen.getByRole("combobox", { name: "引用选择" }), { target: { value: "actor.elda" } });
    expect(selected).toBe("actor.elda");
  });
});
