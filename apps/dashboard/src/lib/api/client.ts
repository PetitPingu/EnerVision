import axios from "axios";
import { LOGIN_ENDPOINT } from "@/config/api";

export const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_BFF_URL,
  timeout: 10_000,
});

let authToken: string | null = null;
let onUnauthorized: (() => void) | null = null;

export function setAuthToken(token: string | null) {
  authToken = token;
}

/** Appelé par AuthProvider : réagit à un 401 (token absent/expiré). */
export function setUnauthorizedHandler(handler: (() => void) | null) {
  onUnauthorized = handler;
}

apiClient.interceptors.request.use((config) => {
  if (authToken) {
    config.headers.Authorization = `Bearer ${authToken}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && error.config?.url !== LOGIN_ENDPOINT) {
      onUnauthorized?.();
    }
    return Promise.reject(error);
  },
);
