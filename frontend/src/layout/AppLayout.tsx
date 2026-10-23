import {
  AppstoreOutlined,
  BarChartOutlined,
  BookOutlined,
  DatabaseOutlined,
  EnvironmentOutlined,
  KeyOutlined,
  LogoutOutlined,
  SafetyCertificateOutlined,
  TeamOutlined,
  UserOutlined,
} from "@ant-design/icons";
import { Button, Dropdown, Grid, Layout, Menu, Typography, type MenuProps } from "antd";
import { useState } from "react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";

import type { Permission } from "@/api/types";
import { useAuth } from "@/auth/AuthContext";
import ChangePasswordModal from "@/components/ChangePasswordModal";

const ITEMS: { key: string; label: string; icon: React.ReactNode; perm: Permission }[] = [
  { key: "/atms", label: "Банкоматы", icon: <DatabaseOutlined />, perm: "view" },
  { key: "/map", label: "Карта", icon: <EnvironmentOutlined />, perm: "view" },
  { key: "/models", label: "Модели", icon: <AppstoreOutlined />, perm: "view" },
  { key: "/certificates", label: "Сертификаты", icon: <SafetyCertificateOutlined />, perm: "view" },
  { key: "/reports", label: "Отчёты", icon: <BarChartOutlined />, perm: "view" },
  { key: "/reference", label: "Справочники", icon: <BookOutlined />, perm: "manage_reference" },
  { key: "/users", label: "Пользователи", icon: <TeamOutlined />, perm: "manage_users" },
];

export default function AppLayout() {
  const { user, can, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const screens = Grid.useBreakpoint();
  const [pwdOpen, setPwdOpen] = useState(false);

  const selected = ITEMS.find((i) => location.pathname.startsWith(i.key))?.key;
  const userMenu: MenuProps["items"] = [
    { key: "pwd", icon: <KeyOutlined />, label: "Сменить пароль", onClick: () => setPwdOpen(true) },
    { key: "logout", icon: <LogoutOutlined />, label: "Выйти", onClick: logout },
  ];

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Layout.Sider breakpoint="lg" collapsedWidth={0} width={220} theme="dark">
        <div style={{ color: "#fff", padding: "18px 20px", fontWeight: 600, fontSize: 15, lineHeight: 1.3 }}>
          Справочник банкоматов
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={selected ? [selected] : []}
          items={ITEMS.filter((i) => can(i.perm)).map(({ key, label, icon }) => ({ key, label, icon }))}
          onClick={({ key }) => navigate(key)}
        />
      </Layout.Sider>
      <Layout>
        <Layout.Header
          style={{
            background: "#fff",
            padding: "0 16px",
            display: "flex",
            justifyContent: "flex-end",
            alignItems: "center",
            borderBottom: "1px solid #f0f0f0",
          }}
        >
          <Dropdown menu={{ items: userMenu }} trigger={["click"]}>
            <Button type="text" icon={<UserOutlined />}>
              {screens.sm ? (
                <span>
                  {user?.full_name} <Typography.Text type="secondary">· {user?.role_label}</Typography.Text>
                </span>
              ) : null}
            </Button>
          </Dropdown>
        </Layout.Header>
        <Layout.Content style={{ padding: screens.md ? 24 : 12 }}>
          <Outlet />
        </Layout.Content>
      </Layout>
      <ChangePasswordModal open={pwdOpen} onClose={() => setPwdOpen(false)} />
    </Layout>
  );
}
