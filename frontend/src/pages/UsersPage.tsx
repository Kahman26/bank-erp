import { PlusOutlined } from "@ant-design/icons";
import { useQuery } from "@tanstack/react-query";
import { Button, Card, Form, Input, Modal, Popconfirm, Select, Space, Switch, Table, Tag, Tooltip, Typography } from "antd";
import dayjs from "dayjs";
import { useState } from "react";

import { api } from "@/api/client";
import { useApiMutation } from "@/api/hooks";
import type { RoleCode, UserRow } from "@/api/types";
import { useAuth } from "@/auth/AuthContext";

const USERS_KEY = ["users"];

interface UserForm {
  login: string;
  full_name: string;
  department?: string;
  role: RoleCode;
  password?: string;
}

export default function UsersPage() {
  const { user: me, can } = useAuth();
  const { data: users = [], isLoading } = useQuery({ queryKey: USERS_KEY, queryFn: () => api.get<UserRow[]>("/users") });
  const { data: roles = [] } = useQuery({
    queryKey: ["roles"],
    queryFn: () => api.get<{ value: RoleCode; label: string }[]>("/users/roles"),
  });
  const [editing, setEditing] = useState<UserRow | "new" | null>(null);
  const [resetFor, setResetFor] = useState<UserRow | null>(null);
  const [search, setSearch] = useState("");
  const [form] = Form.useForm<UserForm>();
  const [pwdForm] = Form.useForm<{ password: string }>();

  const roleLabel = Object.fromEntries(roles.map((r) => [r.value, r.label]));
  const roleOptions = roles
    .filter((r) => r.value !== "superadmin" || can("superadmin"))
    .map((r) => ({ value: r.value, label: r.label }));

  const save = useApiMutation(
    (v: UserForm) =>
      editing === "new"
        ? api.post("/users", v)
        : api.patch(`/users/${(editing as UserRow).id}`, { full_name: v.full_name, department: v.department, role: v.role }),
    { success: "Сохранено", invalidate: [USERS_KEY] },
  );
  const terminate = useApiMutation((u: UserRow) => api.post(`/users/${u.id}/terminate-sessions`), {
    success: "Сеансы завершены — пользователю нужно войти заново",
    invalidate: [USERS_KEY],
  });
  const toggle = useApiMutation((u: UserRow) => api.patch(`/users/${u.id}`, { is_active: !u.is_active }), {
    invalidate: [USERS_KEY],
  });
  const reset = useApiMutation((v: { id: number; password: string }) => api.post(`/users/${v.id}/reset-password`, v), {
    success: "Пароль сброшен, сессии пользователя закрыты",
    invalidate: [USERS_KEY],
  });

  const open = (u: UserRow | "new") => {
    setEditing(u);
    form.setFieldsValue(u === "new" ? { role: "viewer" } : { ...u, department: u.department ?? undefined });
  };

  const submit = async () => {
    const values = await form.validateFields().catch(() => null);
    if (!values) return;
    await save.mutateAsync(values);
    setEditing(null);
  };

  const submitReset = async () => {
    const values = await pwdForm.validateFields().catch(() => null);
    if (!values) return;
    const { password } = values;
    await reset.mutateAsync({ id: resetFor!.id, password });
    setResetFor(null);
  };

  const editable = (u: UserRow) => u.role !== "superadmin" || can("superadmin");

  return (
    <Card
      title="Пользователи"
      extra={
        <Button type="primary" icon={<PlusOutlined />} onClick={() => open("new")}>
          Добавить
        </Button>
      }
    >
      <Input.Search
        allowClear
        placeholder="ФИО, логин или подразделение"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        style={{ maxWidth: 360, marginBottom: 12 }}
      />
      <Table<UserRow>
        rowKey="id"
        loading={isLoading}
        dataSource={users.filter((u) =>
          [u.full_name, u.login, u.department ?? ""].some((x) => x.toLowerCase().includes(search.trim().toLowerCase())),
        )}
        pagination={false}
        scroll={{ x: 900 }}
        columns={[
          { title: "ФИО", dataIndex: "full_name" },
          { title: "Логин", dataIndex: "login" },
          { title: "Подразделение", dataIndex: "department" },
          { title: "Роль", dataIndex: "role", render: (r: RoleCode) => roleLabel[r] ?? r },
          {
            title: "Статус",
            render: (_, u) =>
              !u.is_active ? (
                <Tag>Заблокирован</Tag>
              ) : u.locked_until && dayjs(u.locked_until).isAfter(dayjs()) ? (
                <Tag color="orange">Вход приостановлен</Tag>
              ) : (
                <Tag color="green">Активен</Tag>
              ),
          },
          {
            title: "Сеансы",
            dataIndex: "active_sessions",
            align: "right",
            render: (n: number, u) => (
              <Space size={4}>
                {n}
                {u.must_change_password && (
                  <Tooltip title="Вошёл с временным паролем или ещё не входил — при входе сменит пароль">
                    <Tag color="gold">временный пароль</Tag>
                  </Tooltip>
                )}
              </Space>
            ),
          },
          {
            title: "Последний вход",
            dataIndex: "last_login_at",
            render: (v: string | null) => (v ? dayjs(v).format("DD.MM.YYYY HH:mm") : "—"),
          },
          {
            title: "",
            render: (_, u) =>
              editable(u) && (
                <Space>
                  <Button size="small" onClick={() => open(u)}>
                    Изменить
                  </Button>
                  <Button
                    size="small"
                    onClick={() => {
                      pwdForm.resetFields();
                      setResetFor(u);
                    }}
                  >
                    Сбросить пароль
                  </Button>
                  {u.id !== me?.id && u.active_sessions > 0 && (
                    <Popconfirm
                      title="Завершить все сеансы?"
                      description="Пользователя выбросит из системы на всех устройствах"
                      okText="Завершить"
                      cancelText="Отмена"
                      onConfirm={() => terminate.mutate(u)}
                    >
                      <Button size="small">Завершить сеансы</Button>
                    </Popconfirm>
                  )}
                  {u.id !== me?.id && (
                    <Switch
                      size="small"
                      checked={u.is_active}
                      onChange={() => toggle.mutate(u)}
                      checkedChildren="вкл"
                      unCheckedChildren="выкл"
                    />
                  )}
                </Space>
              ),
          },
        ]}
      />

      <Modal
        title={editing === "new" ? "Новый пользователь" : "Пользователь"}
        open={editing !== null}
        onOk={submit}
        onCancel={() => setEditing(null)}
        confirmLoading={save.isPending}
        okText="Сохранить"
        destroyOnClose
      >
        <Form form={form} layout="vertical" preserve={false}>
          <Form.Item
            name="login"
            label="Логин"
            rules={[{ required: true, pattern: /^[A-Za-z0-9._-]{3,64}$/, message: "Латиница, цифры, . _ -; от 3 символов" }]}
          >
            <Input disabled={editing !== "new"} autoComplete="off" />
          </Form.Item>
          <Form.Item name="full_name" label="ФИО" rules={[{ required: true, min: 2 }]}>
            <Input />
          </Form.Item>
          <Form.Item name="department" label="Подразделение">
            <Input />
          </Form.Item>
          <Form.Item name="role" label="Роль" rules={[{ required: true }]}>
            <Select options={roleOptions} disabled={editing !== "new" && (editing as UserRow)?.id === me?.id} />
          </Form.Item>
          {editing === "new" && (
            <Form.Item
              name="password"
              label="Временный пароль"
              extra="Не короче 8 символов, буквы и цифры. Сообщите его сотруднику: при первом входе система попросит сменить пароль."
              rules={[{ required: true, min: 8 }]}
            >
              <Input.Password autoComplete="new-password" />
            </Form.Item>
          )}
        </Form>
      </Modal>

      <Modal
        title="Сброс пароля"
        open={resetFor !== null}
        onOk={submitReset}
        onCancel={() => setResetFor(null)}
        okText="Сбросить"
        destroyOnClose
      >
        <Typography.Paragraph>
          Новый пароль для <b>{resetFor?.full_name}</b>. Все сессии пользователя будут закрыты.
        </Typography.Paragraph>
        <Form form={pwdForm} layout="vertical" preserve={false}>
          <Form.Item name="password" label="Новый пароль" rules={[{ required: true, min: 8 }]}>
            <Input.Password autoComplete="new-password" />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
}
