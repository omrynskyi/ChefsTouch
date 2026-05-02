import { describe, expect, it, afterEach } from "vitest";
import { render, cleanup } from "@testing-library/react";

afterEach(() => cleanup());
import { IngredientList } from "./IngredientList";

const items = [
  { name: "Pasta", qty: "200g" },
  { name: "Salt", qty: "1 tsp" },
  { name: "Olive oil", qty: "2 tbsp" },
];

describe("IngredientList", () => {
  it("renders all ingredient names", () => {
    const { getByText } = render(<IngredientList data={{ items }} />);
    expect(getByText("Pasta")).toBeTruthy();
    expect(getByText("Salt")).toBeTruthy();
    expect(getByText("Olive oil")).toBeTruthy();
  });

  it("renders all ingredient quantities", () => {
    const { getByText } = render(<IngredientList data={{ items }} />);
    expect(getByText("200g")).toBeTruthy();
    expect(getByText("1 tsp")).toBeTruthy();
    expect(getByText("2 tbsp")).toBeTruthy();
  });

  it("applies elevated class when focused", () => {
    const { container } = render(<IngredientList data={{ items }} focused />);
    expect(container.querySelector(".elevated")).not.toBeNull();
  });

  it("does not apply elevated class when not focused", () => {
    const { container } = render(<IngredientList data={{ items }} />);
    expect(container.querySelector(".elevated")).toBeNull();
  });

  it("renders empty list without crashing", () => {
    const { container } = render(<IngredientList data={{ items: [] }} />);
    expect(container.querySelector(".ingredient-list")).not.toBeNull();
    expect(container.querySelectorAll(".ingredient-row")).toHaveLength(0);
  });

  it("uses list semantics", () => {
    const { container } = render(<IngredientList data={{ items }} />);
    expect(container.querySelector("ul")).not.toBeNull();
    expect(container.querySelectorAll("li")).toHaveLength(3);
  });
});
