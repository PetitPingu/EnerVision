import { LOGIN_ENDPOINT } from "@/config/api";
import { apiClient } from "@/lib/api/client";

type LoginResponse = {
  access_token: string;
  token_type: string;
};

export async function login(email: string, password: string): Promise<string> {
  const { data } = await apiClient.post<LoginResponse>(LOGIN_ENDPOINT, {
    email,
    password,
  });

  return data.access_token;
}
