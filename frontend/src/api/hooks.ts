import { useMutation, useQuery, useQueryClient, type QueryKey } from "@tanstack/react-query";
import { App } from "antd";

import { api } from "./client";
import type { ReferenceBundle } from "./types";

export const REFERENCE_KEY = ["reference"];

/** Демо-стенд с вымышленными данными — показываем пометку, чтобы никто не принял данные за настоящие. */
export function useIsDemo(): boolean {
  const { data } = useQuery({ queryKey: ["meta"], queryFn: () => api.get<{ demo: boolean }>("/meta"), staleTime: Infinity });
  return !!data?.demo;
}

export function useReference() {
  return useQuery({ queryKey: REFERENCE_KEY, queryFn: () => api.get<ReferenceBundle>("/reference"), staleTime: 60_000 });
}

/** Мутация с сообщением об успехе/ошибке и обновлением связанных запросов. */
export function useApiMutation<TVars, TResult = unknown>(
  fn: (vars: TVars) => Promise<TResult>,
  opts: { success?: string; invalidate?: QueryKey[] } = {},
) {
  const qc = useQueryClient();
  const { message } = App.useApp();
  return useMutation({
    mutationFn: fn,
    onSuccess: () => {
      if (opts.success) message.success(opts.success);
      opts.invalidate?.forEach((key) => qc.invalidateQueries({ queryKey: key }));
    },
    onError: (e: Error) => message.error(e.message),
  });
}
