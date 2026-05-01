import type { IngredientListData } from "@pair-cooking/types";

interface Props {
  data: IngredientListData;
  focused?: boolean;
}

export function IngredientList({ data, focused }: Props) {
  return (
    <div className={`card comp-full${focused ? " elevated" : ""}`}>
      <ul className="ingredient-list" style={{ listStyle: "none", padding: 0, margin: 0 }}>
        {data.items.map((item, i) => (
          <li key={i} className="ingredient-row">
            <span className="ingredient-name">{item.name}</span>
            <span className="ingredient-qty">{item.qty}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
