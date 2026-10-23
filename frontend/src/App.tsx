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
import AuditPage from "@/pages/AuditPage";
import AtmsPage from "@/pages/AtmsPage";
import CertificatesPage from "@/pages/CertificatesPage";
import ForcePasswordPage from "@/pages/ForcePasswordPage";
import ImportPage from "@/pages/ImportPage";
import LoginPage from "@/pages/LoginPage";
import MapPage from "@/pages/MapPage";
import ModelsPage from "@/pages/ModelsPage";
import ReferencePage from "@/pages/ReferencePage";
import ReportsPage from "@/pages/ReportsPage";
import UsersPage from "@/pages/UsersPage";

dayjs.locale("ru");

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: (count, err) => count < 2 && (err as { status?: number }).status !== 401 } },
});

function RequireAuth() {
  const { user } = useAuth();
  if (!user) return <LoginPage />;
  return user.must_change_password ? <ForcePasswordPage /> : <Outlet />;
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
          { path: "certificates", element: <CertificatesPage /> },
          { path: "reports", element: <ReportsPage /> },
          {
            element: <RequirePerm perm="manage_reference" />,
            children: [
              { path: "reference", element: <ReferencePage /> },
              { path: "import", element: <ImportPage /> },
            ],
          },
          { element: <RequirePerm perm="manage_users" />, children: [{ path: "users", element: <UsersPage /> }] },
          { element: <RequirePerm perm="superadmin" />, children: [{ path: "audit", element: <AuditPage /> }] },
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
