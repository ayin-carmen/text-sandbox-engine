import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { EntityForm } from "./EntityWorkspace";

const references = [
  { id: "location.west_gate", type: "location" as const, label: "西门", source: "world_state.json", valid: true },
  { id: "location.market_square", type: "location" as const, label: "集市广场", source: "world_state.json", valid: true },
  { id: "item.bread_basket", type: "item" as const, label: "面包篮", source: "scene.json", valid: true },
];

describe("world entity forms", () => {
  afterEach(() => cleanup());

  it("edits actor identity, tags, location and inventory references", () => {
    let nextDocument: Record<string, unknown> = {
      id: "actor.player",
      type: "actor",
      tags: ["player"],
      components: { profile: { name: "旅人" }, location: { current: "location.west_gate" }, inventory: { items: [] } },
    };
    const view = render(<EntityForm document={nextDocument} references={references} onChange={(document) => { nextDocument = document; }} />);

    fireEvent.change(screen.getByDisplayValue("player"), { target: { value: "player, traveler" } });
    view.rerender(<EntityForm document={nextDocument} references={references} onChange={(document) => { nextDocument = document; }} />);
    fireEvent.change(screen.getByDisplayValue("旅人"), { target: { value: "新旅人" } });
    view.rerender(<EntityForm document={nextDocument} references={references} onChange={(document) => { nextDocument = document; }} />);
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "location.market_square" } });
    view.rerender(<EntityForm document={nextDocument} references={references} onChange={(document) => { nextDocument = document; }} />);
    fireEvent.click(screen.getByRole("button", { name: "添加物品" }));

    expect(nextDocument.tags).toEqual(["player", "traveler"]);
    expect((nextDocument.components as any).profile.name).toBe("新旅人");
    expect((nextDocument.components as any).location.current).toBe("location.market_square");
    expect((nextDocument.components as any).inventory.items).toEqual(["item.bread_basket"]);
  });

  it("edits location connections without changing the stable id", () => {
    let nextDocument: Record<string, unknown> = {
      id: "location.west_gate",
      type: "location",
      tags: [],
      components: { description: { name: "西门", text: "" }, map_node: { region: "greybrook", connections: [] } },
    };
    render(<EntityForm document={nextDocument} references={references} onChange={(document) => { nextDocument = document; }} />);
    fireEvent.click(screen.getByRole("button", { name: "添加连接" }));
    expect(nextDocument.id).toBe("location.west_gate");
    expect((nextDocument.components as any).map_node.connections).toEqual(["location.market_square"]);
  });
});
