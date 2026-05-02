import { AnimatePresence, motion } from "framer-motion";
import type { CanvasComponent, RecipeGridData, RecipeOptionData } from "@pair-cooking/types";
import { RecipeOption } from "./RecipeOption";

const CHILD_TRANSITION = { duration: 0.18, ease: [0.25, 0.1, 0.25, 1] as const };

interface Props {
  data: RecipeGridData;
  focused?: boolean;
  children: CanvasComponent<"recipe-option">[];
}

export function RecipeGrid({ focused, children }: Props) {
  return (
    <div className={`recipe-grid comp-wide${focused ? " elevated" : ""}`}>
      <AnimatePresence>
        {children.map((child) => (
          <motion.div
            key={child.id}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={CHILD_TRANSITION}
          >
            <RecipeOption
              data={child.data as RecipeOptionData}
              focused={child.focused}
            />
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
