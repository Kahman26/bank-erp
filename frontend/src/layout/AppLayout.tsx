import {
  AppstoreOutlined,
  BarChartOutlined,
  BookOutlined,
  CloudUploadOutlined,
  DatabaseOutlined,
  EnvironmentOutlined,
  HistoryOutlined,
  KeyOutlined,
  LogoutOutlined,
  MenuOutlined,
  SafetyCertificateOutlined,
  TeamOutlined,
  UserOutlined,
} from "@ant-design/icons";
import { Button, Drawer, Dropdown, Grid, Layout, Menu, Tag, Tooltip, Typography, type MenuProps } from "antd";
import { useState } from "react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";

import { useIsDemo } from "@/api/hooks";
import type { Permission } from "@/api/types";
import { useAuth } from "@/auth/AuthContext";
import ChangePasswordModal from "@/components/ChangePasswordModal";

const ITEMS: { key: string; label: string; icon: React.ReactNode; perm: Permission }[] = [
  { key: "/atms", label: "Банкоматы", icon: <DatabaseOutlined />, perm: "view" },
  { key: "/map", label: "Карта", icon: <EnvironmentOutlined />, perm: "view" },
  { key: "/models", label: "Модели", icon: <AppstoreOutlined />, perm: "view" },
  { key: "/certificates", label: "Сертификаты", icon: <SafetyCertificateOutlined />, perm: "view" },
  { key: "/reports", label: "Отчёты", icon: <BarChartOutlined />, perm: "view" },
  { key: "/import", label: "Загрузка данных", icon: <CloudUploadOutlined />, perm: "manage_reference" },
  { key: "/reference", label: "Справочники", icon: <BookOutlined />, perm: "manage_reference" },
  { key: "/users", label: "Пользователи", icon: <TeamOutlined />, perm: "manage_users" },
  { key: "/audit", label: "Журнал изменений", icon: <HistoryOutlined />, perm: "superadmin" },
];

export default function AppLayout() {
  const { user, can, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const screens = Grid.useBreakpoint();
  const [pwdOpen, setPwdOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const demo = useIsDemo();
  // до первого замера useBreakpoint пуст — считаем экран широким, чтобы не мигало
  const mobile = screens.lg === false;

  const selected = ITEMS.find((i) => location.pathname.startsWith(i.key))?.key;
  const userMenu: MenuProps["items"] = [
    { key: "pwd", icon: <KeyOutlined />, label: "Сменить пароль", onClick: () => setPwdOpen(true) },
    { key: "logout", icon: <LogoutOutlined />, label: "Выйти", onClick: logout },
  ];
  const title = (
    <div style={{ color: "#fff", padding: "18px 20px", fontWeight: 600, fontSize: 15, lineHeight: 1.3 }}>
      Справочник банкоматов
    </div>
  );
  const menu = (
    <Menu
      theme="dark"
      mode="inline"
      selectedKeys={selected ? [selected] : []}
      items={ITEMS.filter((i) => can(i.perm)).map(({ key, label, icon }) => ({ key, label, icon }))}
      onClick={({ key }) => {
        navigate(key);
        setMenuOpen(false);
      }}
    />
  );

  return (
    <Layout style={{ minHeight: "100vh" }}>
      {!mobile && (
        <Layout.Sider width={220} theme="dark" style={{ position: "sticky", top: 0, height: "100vh", overflow: "auto" }}>
          {title}
          {menu}
        </Layout.Sider>
      )}
      <Layout style={{ minWidth: 0 }}>
        <Layout.Header
          style={{
            background: "#fff",
            padding: "0 12px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            borderBottom: "1px solid #f0f0f0",
            position: "sticky",
            top: 0,
            zIndex: 10,
          }}
        >
          {mobile ? (
            <Button type="text" icon={<MenuOutlined />} onClick={() => setMenuOpen(true)} aria-label="Меню">
              Банкоматы
            </Button>
          ) : (
            <span />
          )}
          <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
            {demo && (
              <Tooltip title="Демо-стенд: банкоматы, адреса, ремонты и сертификаты вымышленные">
                <Tag color="gold" style={{ marginInlineEnd: 0 }}>
                  демо-данные
                </Tag>
              </Tooltip>
            )}
            <Dropdown menu={{ items: userMenu }} trigger={["click"]}>
            <Button type="text" icon={<UserOutlined />}>
              {screens.sm ? (
                <span>
                  {user?.full_name} <Typography.Text type="secondary">· {user?.role_label}</Typography.Text>
                </span>
              ) : null}
            </Button>
          </Dropdown>
          </span>
        </Layout.Header>
        <Layout.Content style={{ padding: screens.md ? 24 : 8, minWidth: 0 }}>
          <Outlet />
        </Layout.Content>
      </Layout>
      <Drawer
        placement="left"
        open={mobile && menuOpen}
        onClose={() => setMenuOpen(false)}
        width={260}
        closable={false}
        styles={{ body: { padding: 0, background: "#001529" }, header: { display: "none" } }}
      >
        {title}
        {menu}
      </Drawer>
      <ChangePasswordModal open={pwdOpen} onClose={() => setPwdOpen(false)} />
    </Layout>
  );
}
