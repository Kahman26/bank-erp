import { UnorderedListOutlined } from "@ant-design/icons";
import { useQuery } from "@tanstack/react-query";
import { Alert, Button, Card, Space, Spin, Typography } from "antd";
import { useMemo } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { api } from "@/api/client";
import { useReference } from "@/api/hooks";
import type { AtmModel } from "@/api/types";
import AtmMap from "@/atms/AtmMap";
import FilterPanel, { filterParams } from "@/atms/FilterPanel";
import { STATUS_COLORS } from "@/atms/status";
import type { MapPoints } from "@/atms/types";

export default function MapPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const { data: ref } = useReference();
  const query = filterParams(params).toString();
  const { data, isFetching } = useQuery({ queryKey: ["atm-map", query], queryFn: () => api.get<MapPoints>(`/atms/map?${query}`) });
  const { data: models } = useQuery({ queryKey: ["atm-models"], queryFn: () => api.get<AtmModel[]>("/atm-models") });

  const statusNames = useMemo(
    () => Object.fromEntries((ref?.dicts.atm_status ?? []).map((d) => [d.code, d.name])),
    [ref],
  );
  const present = useMemo(() => new Set((data?.points ?? []).map((p) => p[4])), [data]);

  return (
    <Card
      title="Карта банкоматов"
      extra={
        <Button icon={<UnorderedListOutlined />} onClick={() => navigate(`/atms?${query}`)}>
          Списком
        </Button>
      }
    >
      <FilterPanel models={models} />
      <Space wrap style={{ marginBottom: 8 }}>
        <Typography.Text type="secondary">
          На карте: {data?.points.length ?? "…"}
          {isFetching && <Spin size="small" style={{ marginLeft: 8 }} />}
        </Typography.Text>
        {Object.entries(statusNames)
          .filter(([code]) => present.has(code))
          .map(([code, name]) => (
            <span key={code} style={{ whiteSpace: "nowrap", fontSize: 12 }}>
              <span className="legend-dot" style={{ background: STATUS_COLORS[code] }} /> {name}
            </span>
          ))}
      </Space>
      {!!data?.without_location && (
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 8 }}
          message={`${data.without_location} банкоматов без места установки (склад, доставка, ферма, списание) на карте не показаны`}
        />
      )}
      <AtmMap points={data?.points ?? []} statusNames={statusNames} height="calc(100vh - 330px)" />
    </Card>
  );
}
