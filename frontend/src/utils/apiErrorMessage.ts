import axios from 'axios';

type ApiErrorDetail = string | Array<{ msg?: unknown }> | null | undefined;

export const apiErrorMessage = (error: unknown, fallback: string): string => {
  if (!axios.isAxiosError<{ detail?: ApiErrorDetail }>(error)) return fallback;

  const detail = error.response?.data?.detail;
  if (typeof detail === 'string' && detail.trim()) return detail;
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => item?.msg)
      .filter((message): message is string => typeof message === 'string' && Boolean(message.trim()));
    if (messages.length) return messages.join('; ');
  }
  return fallback;
};
