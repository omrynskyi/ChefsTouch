import type { CanvasComponent, RecipeGridData, RecipeOptionData } from "@pair-cooking/types";
import { RecipeOption } from "./RecipeOption";

interface Props {
  data: RecipeGridData;
  focused?: boolean;
  children: CanvasComponent<"recipe-option">[];
}

export function RecipeGrid({ focused, children }: Props) {
  return (
    <div
      className={`recipe-grid comp-wide${focused ? " elevated" : ""}`}
    >
      {children.map((child) => (
        <RecipeOption
          key={child.id}
          data={child.data as RecipeOptionData}
          focused={child.focused}
        />
      ))}
    </div>
  );
}
