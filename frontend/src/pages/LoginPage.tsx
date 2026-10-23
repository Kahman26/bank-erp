import { LockOutlined, UserOutlined } from "@ant-design/icons";
import { Alert, Button, Card, Form, Input, Typography } from "antd";
import { useState } from "react";

import { api } from "@/api/client";
import type { Me } from "@/api/types";
import { useAuth } from "@/auth/AuthContext";

interface LoginForm {
  login: string;
  password: string;
}

export default function LoginPage() {
  const { setUser } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const onFinish = async (values: LoginForm) => {
    setLoading(true);
    setError(null);
    try {
      setUser(await api.post<Me>("/auth/login", values));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ minHeight: "100vh", display: "grid", placeItems: "center", background: "#f0f4f8", padding: 16 }}>
      <Card style={{ width: "100%", maxWidth: 380 }}>
        <Typography.Title level={3} style={{ marginTop: 0, color: "#1F4E79" }}>
          Справочник банкоматов
        </Typography.Title>
        <Typography.Paragraph type="secondary">Войдите под своей учётной записью</Typography.Paragraph>
        {error && <Alert type="error" message={error} showIcon style={{ marginBottom: 16 }} />}
        <Form<LoginForm> layout="vertical" onFinish={onFinish} requiredMark={false}>
          <Form.Item name="login" label="Логин" rules={[{ required: true, message: "Введите логин" }]}>
            <Input prefix={<UserOutlined />} autoComplete="username" autoFocus />
          </Form.Item>
          <Form.Item name="password" label="Пароль" rules={[{ required: true, message: "Введите пароль" }]}>
            <Input.Password prefix={<LockOutlined />} autoComplete="current-password" />
          </Form.Item>
          <Button type="primary" htmlType="submit" block loading={loading}>
            Войти
          </Button>
        </Form>
      </Card>
    </div>
  );
}
