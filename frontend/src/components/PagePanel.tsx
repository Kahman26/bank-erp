import { Card } from "antd";
import type { ReactNode } from "react";

interface HeadingProps {
  title: string;
  description?: string;
  extra?: ReactNode;
}

export function PageHeading({ title, description, extra }: HeadingProps) {
  return (
    <div className="page-heading">
      <div className="page-heading-copy">
        <h1>{title}</h1>
        {description && <p>{description}</p>}
      </div>
      {extra && <div className="page-heading-actions">{extra}</div>}
    </div>
  );
}

export default function PagePanel({ children, ...heading }: HeadingProps & { children: ReactNode }) {
  return (
    <section className="page-section">
      <PageHeading {...heading} />
      <Card className="workspace-card">{children}</Card>
    </section>
  );
}
