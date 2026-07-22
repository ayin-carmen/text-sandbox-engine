import type { ReferenceItem } from "./api";

export function ReferenceSelect({ value, options, onChange }: { value: string; options: ReferenceItem[]; onChange: (value: string) => void }) {
  const hasCurrent = value !== "" && options.some((option) => option.id === value);
  return <select aria-label="引用选择" value={value} onChange={(event) => onChange(event.target.value)}>
    {value && !hasCurrent && <option value={value}>{value}（缺失引用）</option>}
    {options.map((option) => <option key={option.id} value={option.id}>{option.label} · {option.id}{option.valid ? "" : "（缺失引用）"}</option>)}
  </select>;
}
