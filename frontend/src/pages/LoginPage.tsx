import { LockOutlined, UserOutlined } from "@ant-design/icons";
import { Alert, Button, Form, Input, Typography } from "antd";
import { useState } from "react";

import { api } from "@/api/client";
import type { Me } from "@/api/types";
import { useAuth } from "@/auth/AuthContext";
import AuthShell from "@/components/AuthShell";

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
    <AuthShell>
      <span className="auth-form-eyebrow">Рабочее пространство</span>
      <Typography.Title level={1}>
        Вход в систему
      </Typography.Title>
      <Typography.Paragraph type="secondary">Войдите под своей учётной записью банка</Typography.Paragraph>
      {error && <Alert type="error" message={error} showIcon style={{ marginBottom: 16 }} />}
      <Form<LoginForm> size="large" layout="vertical" onFinish={onFinish} requiredMark={false}>
        <Form.Item name="login" label="Логин" rules={[{ required: true, message: "Введите логин" }]}>
          <Input prefix={<UserOutlined aria-hidden="true" />} placeholder="Введите логин" autoComplete="username" autoFocus />
        </Form.Item>
        <Form.Item name="password" label="Пароль" rules={[{ required: true, message: "Введите пароль" }]}>
          <Input.Password prefix={<LockOutlined aria-hidden="true" />} placeholder="Введите пароль" autoComplete="current-password" />
        </Form.Item>
        <Button type="primary" htmlType="submit" block loading={loading}>
          Войти
        </Button>
      </Form>
    </AuthShell>
  );
}
