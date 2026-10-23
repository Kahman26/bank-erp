import { ConfigProvider, Result } from "antd";
import ruRU from "antd/locale/ru_RU";

export default function App() {
  return (
    <ConfigProvider locale={ruRU} theme={{ token: { colorPrimary: "#1F4E79" } }}>
      <Result status="info" title="Справочник банкоматов" subTitle="Сервис разворачивается" />
    </ConfigProvider>
  );
}
