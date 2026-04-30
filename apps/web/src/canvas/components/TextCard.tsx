import type { TextCardData } from "@pair-cooking/types";

interface Props {
  data: TextCardData;
  focused?: boolean;
}

// Supports **bold** and _italic_ inline markdown
function renderInline(text: string): React.ReactNode[] {
  const parts = text.split(/(\*\*[^*]+\*\*|_[^_]+_)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith("_") && part.endsWith("_")) {
      return <em key={i}>{part.slice(1, -1)}</em>;
    }
    return part;
  });
}

export function TextCard({ data, focused }: Props) {
  return (
    <div className={`card comp-medium${focused ? " elevated" : ""}`}>
      <p className="text-primary size-md">{renderInline(data.body)}</p>
    </div>
  );
}
