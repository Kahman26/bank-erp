import { DatabaseOutlined, EnvironmentOutlined, SafetyCertificateOutlined } from "@ant-design/icons";
import type { ReactNode } from "react";

import BrandLogo from "./BrandLogo";

export default function AuthShell({ children }: { children: ReactNode }) {
  return (
    <div className="auth-page">
      <aside className="auth-story" aria-label="О системе">
        <span className="auth-eyebrow">Справочник банкоматов</span>
        <div className="auth-story-copy">
          <h2>Вся сеть.<br />В одном пространстве.</h2>
          <p>Банкоматы, оборудование и сервис — в едином рабочем пространстве Hamkorbank.</p>
        </div>
        <div className="auth-network" aria-hidden="true">
          <div className="auth-network-orbit auth-network-orbit-outer" />
          <div className="auth-network-orbit auth-network-orbit-inner" />
          <div className="auth-network-center"><DatabaseOutlined /></div>
          <span className="auth-network-node auth-network-node-map"><EnvironmentOutlined /></span>
          <span className="auth-network-node auth-network-node-cert"><SafetyCertificateOutlined /></span>
          <span className="auth-network-label">Устройства · Размещения · Сервис</span>
        </div>
        <span className="auth-story-footer">Hamkorbank · Управление сетью</span>
      </aside>
      <main className="auth-main">
        <BrandLogo />
        <div className="auth-form">{children}</div>
        <span className="auth-footer">Внутренняя система учёта банкоматов</span>
      </main>
    </div>
  );
}
