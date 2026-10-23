import { App, Form, Input, Modal } from "antd";

import { api } from "@/api/client";

interface Values {
  old_password: string;
  new_password: string;
  confirm: string;
}

export default function ChangePasswordModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [form] = Form.useForm<Values>();
  const { message } = App.useApp();

  const submit = async () => {
    const values = await form.validateFields().catch(() => null);
    if (!values) return;
    const { old_password, new_password } = values;
    try {
      await api.post("/auth/change-password", { old_password, new_password });
      message.success("Пароль изменён");
      form.resetFields();
      onClose();
    } catch (e) {
      message.error((e as Error).message);
    }
  };

  return (
    <Modal title="Смена пароля" open={open} onOk={submit} onCancel={onClose} okText="Сменить" destroyOnClose>
      <Form form={form} layout="vertical" preserve={false}>
        <Form.Item name="old_password" label="Текущий пароль" rules={[{ required: true }]}>
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
      </Form>
    </Modal>
  );
}
