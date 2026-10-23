export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

type Method = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

async function request<T>(method: Method, path: string, body?: unknown): Promise<T> {
  const isForm = body instanceof FormData;
  const res = await fetch(`/api/v1${path}`, {
    method,
    credentials: "same-origin",
    headers: {
      // бэкенд отклоняет изменяющие запросы без этого заголовка (защита от CSRF)
      "X-Requested-With": "fetch",
      ...(body !== undefined && !isForm ? { "Content-Type": "application/json" } : {}),
    },
    body: body === undefined ? undefined : isForm ? body : JSON.stringify(body),
  });
  if (res.status === 204) return undefined as T;
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    if (res.status === 401 && path !== "/auth/login" && path !== "/auth/me") {
      window.dispatchEvent(new Event("session-expired"));
    }
    throw new ApiError(res.status, errorText(data) ?? `Ошибка ${res.status}`);
  }
  return data as T;
}

function errorText(data: unknown): string | undefined {
  if (!data || typeof data !== "object" || !("detail" in data)) return undefined;
  const detail = (data as { detail: unknown }).detail;
  if (typeof detail === "string") return detail;
  // ошибки валидации FastAPI: [{loc, msg}]
  if (Array.isArray(detail)) return detail.map((d) => `${d.loc?.slice(1).join(".")}: ${d.msg}`).join("; ");
  return undefined;
}

/** Скачивание файла с сервера (cookie сессии уходит автоматически). */
async function download(path: string, filename: string): Promise<void> {
  const res = await fetch(`/api/v1${path}`, { credentials: "same-origin" });
  if (!res.ok) throw new ApiError(res.status, errorText(await res.json().catch(() => null)) ?? `Ошибка ${res.status}`);
  const url = URL.createObjectURL(await res.blob());
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export const api = {
  get: <T>(path: string) => request<T>("GET", path),
  post: <T>(path: string, body?: unknown) => request<T>("POST", path, body ?? {}),
  put: <T>(path: string, body: unknown) => request<T>("PUT", path, body),
  patch: <T>(path: string, body: unknown) => request<T>("PATCH", path, body),
  delete: <T = void>(path: string) => request<T>("DELETE", path),
  upload: <T>(path: string, form: FormData) => request<T>("POST", path, form),
  download,
};
