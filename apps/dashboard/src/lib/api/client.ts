import axios from "axios";

export const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_BFF_URL,
  timeout: 10_000,
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => Promise.reject(error),
);
