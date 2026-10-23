import { Card, Result } from "antd";

export default function PlaceholderPage({ title, stage }: { title: string; stage: string }) {
  return (
    <Card title={title}>
      <Result status="info" title="Раздел в разработке" subTitle={`Появится на этапе: ${stage}`} />
    </Card>
  );
}
