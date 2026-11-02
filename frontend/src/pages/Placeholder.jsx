import { PageHeader } from "../components/ui.jsx";

export default function Placeholder({ title, note }) {
  return (
    <div>
      <PageHeader title={title} />
      <div className="rounded-xl border border-dashed border-line bg-surface p-8 text-muted">{note}</div>
    </div>
  );
}
