import { Alert, Button, Card, Form, Input, Typography } from "antd";
import { useState } from "react";

import { api } from "@/api/client";
import { useAuth } from "@/auth/AuthContext";

interface Values {
  old_password: string;
  new_password: string;
  confirm: string;
}

/** Первый вход с временным паролем от администратора: дальше без смены пароля не пускаем. */
export default function ForcePasswordPage() {
  const { user, setUser, logout } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const onFinish = async (v: Values) => {
    setBusy(true);
    setError(null);
    try {
      await api.post("/auth/change-password", { old_password: v.old_password, new_password: v.new_password });
      if (user) setUser({ ...user, must_change_password: false });
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div style={{ minHeight: "100vh", display: "grid", placeItems: "center", background: "#f0f4f8", padding: 16 }}>
      <Card style={{ width: "100%", maxWidth: 420 }}>
        <Typography.Title level={4} style={{ marginTop: 0 }}>
          Смените временный пароль
        </Typography.Title>
        <Typography.Paragraph type="secondary">
          {user?.full_name}, пароль выдал администратор. Придумайте свой — его будете знать только вы.
        </Typography.Paragraph>
        {error && <Alert type="error" showIcon message={error} style={{ marginBottom: 16 }} />}
        <Form<Values> layout="vertical" onFinish={onFinish} requiredMark={false}>
          <Form.Item name="old_password" label="Временный пароль" rules={[{ required: true }]}>
            <Input.Password autoComplete="current-password" />
          </Form.Item>
          <Form.Item
            name="new_password"
            label="Новый пароль"
            extra="Не короче 8 символов, буквы и цифры"
            rules={[{ required: true, min: 8, message: "Не короче 8 символов" }]}
          >
            <Input.Password autoComplete="new-password" />
          </Form.Item>
          <Form.Item
            name="confirm"
            label="Повторите пароль"
            dependencies={["new_password"]}
            rules={[
              { required: true },
              ({ getFieldValue }) => ({
                validator: (_, v) =>
                  v === getFieldValue("new_password") ? Promise.resolve() : Promise.reject(new Error("Пароли не совпадают")),
              }),
            ]}
          >
            <Input.Password autoComplete="new-password" />
          </Form.Item>
          <Button type="primary" htmlType="submit" block loading={busy}>
            Сохранить и продолжить
          </Button>
          <Button type="link" block onClick={logout} style={{ marginTop: 8 }}>
            Выйти
          </Button>
        </Form>
      </Card>
    </div>
  );
}
