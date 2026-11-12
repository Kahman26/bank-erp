import {
  AppstoreOutlined,
  BarChartOutlined,
  BookOutlined,
  CloudUploadOutlined,
  DatabaseOutlined,
  DownOutlined,
  EnvironmentOutlined,
  HistoryOutlined,
  KeyOutlined,
  LogoutOutlined,
  MenuOutlined,
  SafetyCertificateOutlined,
  TeamOutlined,
} from "@ant-design/icons";
import { Avatar, Button, Drawer, Dropdown, Grid, Layout, Menu, type MenuProps } from "antd";
import { useState } from "react";
import { Link, Outlet, useLocation, useNavigate } from "react-router-dom";

import type { Permission } from "@/api/types";
import { useAuth } from "@/auth/AuthContext";
import BrandLogo from "@/components/BrandLogo";
import ChangePasswordModal from "@/components/ChangePasswordModal";

const ITEMS: { key: string; label: string; icon: React.ReactNode; perm: Permission; group: "network" | "admin" }[] = [
  { key: "/atms", label: "Банкоматы", icon: <DatabaseOutlined />, perm: "view", group: "network" },
  { key: "/map", label: "Карта", icon: <EnvironmentOutlined />, perm: "view", group: "network" },
  { key: "/models", label: "Модели", icon: <AppstoreOutlined />, perm: "view", group: "network" },
  { key: "/certificates", label: "Сертификаты", icon: <SafetyCertificateOutlined />, perm: "view", group: "network" },
  { key: "/reports", label: "Отчёты", icon: <BarChartOutlined />, perm: "view", group: "network" },
  { key: "/import", label: "Загрузка данных", icon: <CloudUploadOutlined />, perm: "manage_reference", group: "admin" },
  { key: "/reference", label: "Справочники", icon: <BookOutlined />, perm: "manage_reference", group: "admin" },
  { key: "/users", label: "Пользователи", icon: <TeamOutlined />, perm: "manage_users", group: "admin" },
  { key: "/audit", label: "Журнал изменений", icon: <HistoryOutlined />, perm: "superadmin", group: "admin" },
];

export default function AppLayout() {
  const { user, can, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const screens = Grid.useBreakpoint();
  const [pwdOpen, setPwdOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const mobile = screens.lg === false;
  const active = ITEMS.find((i) => location.pathname.startsWith(i.key));
  const initials = user?.full_name.trim().split(/\s+/).slice(0, 2).map((s) => s[0]).join("").toUpperCase();

  const userMenu: MenuProps["items"] = [
    { key: "pwd", icon: <KeyOutlined />, label: "Сменить пароль", onClick: () => setPwdOpen(true) },
    { type: "divider" },
    { key: "logout", icon: <LogoutOutlined />, label: "Выйти", onClick: logout },
  ];
  const items: MenuProps["items"] = [
    { key: "network", type: "group", label: "Сеть банкоматов", children: ITEMS.filter((i) => i.group === "network" && can(i.perm)).map(({ key, label, icon }) => ({ key, label, icon })) },
    ...(ITEMS.some((i) => i.group === "admin" && can(i.perm))
      ? [{ key: "admin", type: "group" as const, label: "Управление", children: ITEMS.filter((i) => i.group === "admin" && can(i.perm)).map(({ key, label, icon }) => ({ key, label, icon })) }]
      : []),
  ];
  const sidebar = (
    <div className="sidebar-inner">
      <Link to="/atms" className="sidebar-brand" onClick={() => setMenuOpen(false)} aria-label="Hamkorbank — банкоматы">
        <BrandLogo />
        <span>Справочник банкоматов</span>
      </Link>
      <nav aria-label="Основная навигация" className="sidebar-nav">
        <Menu
          mode="inline"
          selectedKeys={active ? [active.key] : []}
          items={items}
          onClick={({ key }) => {
            navigate(key);
            setMenuOpen(false);
          }}
        />
      </nav>
      <div className="sidebar-footer">
        <img src="/brand/hamkorbank-mark.svg" width={24} height={24} alt="" />
        <div><strong>Hamkorbank</strong><span>Рабочее пространство</span></div>
      </div>
    </div>
  );

  return (
    <Layout className="app-shell">
      <a className="skip-link" href="#main-content">К содержимому</a>
      {!mobile && <Layout.Sider width={252} theme="light" className="app-sidebar">{sidebar}</Layout.Sider>}
      <Layout className="app-workspace">
        <Layout.Header className="app-header">
          <div className="header-location">
            {mobile && (
              <Button type="text" className="menu-toggle" icon={<MenuOutlined />} onClick={() => setMenuOpen(true)} aria-label="Открыть меню" aria-expanded={menuOpen} />
            )}
            <div className="header-breadcrumb"><span>Hamkorbank</span><span className="breadcrumb-divider" aria-hidden="true">/</span><span>{active?.label ?? "Банкоматы"}</span></div>
          </div>
          <div className="header-account">
            <Dropdown menu={{ items: userMenu }} trigger={["click"]}>
              <Button type="text" className="account-button" aria-label={"Меню пользователя: " + user?.full_name}>
                <Avatar size={36}>{initials}</Avatar>
                <span className="account-info"><strong>{user?.full_name}</strong><span>{user?.role_label}</span></span>
                <DownOutlined className="account-chevron" />
              </Button>
            </Dropdown>
          </div>
        </Layout.Header>
        <Layout.Content id="main-content" tabIndex={-1} className="app-content"><Outlet /></Layout.Content>
      </Layout>
      <Drawer
        title="Меню Hamkorbank"
        aria-label="Меню Hamkorbank"
        placement="left"
        open={mobile && menuOpen}
        onClose={() => setMenuOpen(false)}
        width={Math.min(292, typeof window === "undefined" ? 292 : window.innerWidth - 32)}
        className="navigation-drawer"
        styles={{ body: { padding: 0 }, header: { padding: "12px 20px" } }}
      >
        {sidebar}
      </Drawer>
      <ChangePasswordModal open={pwdOpen} onClose={() => setPwdOpen(false)} />
    </Layout>
  );
}
