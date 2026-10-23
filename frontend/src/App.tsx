import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { App as AntApp, ConfigProvider } from "antd";
import ruRU from "antd/locale/ru_RU";
import dayjs from "dayjs";
import "dayjs/locale/ru";
import { createBrowserRouter, Navigate, Outlet, RouterProvider } from "react-router-dom";

import type { Permission } from "@/api/types";
import { AuthProvider, useAuth } from "@/auth/AuthContext";
import AppLayout from "@/layout/AppLayout";
import AtmCardPage from "@/pages/AtmCardPage";
import AtmsPage from "@/pages/AtmsPage";
import LoginPage from "@/pages/LoginPage";
import MapPage from "@/pages/MapPage";
import ModelsPage from "@/pages/ModelsPage";
import PlaceholderPage from "@/pages/PlaceholderPage";
import ReferencePage from "@/pages/ReferencePage";
import UsersPage from "@/pages/UsersPage";

dayjs.locale("ru");

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: (count, err) => count < 2 && (err as { status?: number }).status !== 401 } },
});

function RequireAuth() {
  const { user } = useAuth();
  return user ? <Outlet /> : <LoginPage />;
}

function RequirePerm({ perm }: { perm: Permission }) {
  const { can } = useAuth();
  return can(perm) ? <Outlet /> : <Navigate to="/atms" replace />;
}

const router = createBrowserRouter([
  {
    element: <RequireAuth />,
    children: [
      {
        element: <AppLayout />,
        children: [
          { index: true, element: <Navigate to="/atms" replace /> },
          { path: "atms", element: <AtmsPage /> },
          { path: "atms/:id", element: <AtmCardPage /> },
          { path: "map", element: <MapPage /> },
          { path: "models", element: <ModelsPage /> },
          { path: "certificates", element: <PlaceholderPage title="Сертификаты" stage="6 — сертификаты и гарантии" /> },
          { path: "reports", element: <PlaceholderPage title="Отчёты" stage="7 — выгрузки и отчёты" /> },
          { element: <RequirePerm perm="manage_reference" />, children: [{ path: "reference", element: <ReferencePage /> }] },
          { element: <RequirePerm perm="manage_users" />, children: [{ path: "users", element: <UsersPage /> }] },
          { path: "*", element: <Navigate to="/atms" replace /> },
        ],
      },
    ],
  },
]);

export default function App() {
  return (
    <ConfigProvider locale={ruRU} theme={{ token: { colorPrimary: "#1F4E79", borderRadius: 6 } }}>
      <AntApp>
        <QueryClientProvider client={queryClient}>
          <AuthProvider>
            <RouterProvider router={router} />
          </AuthProvider>
        </QueryClientProvider>
      </AntApp>
    </ConfigProvider>
  );
}
