import { ADMIN_USERS_ENDPOINT } from "@/config/api";
import { apiClient } from "@/lib/api/client";
import type { AdminUser } from "@/types/user";

export async function listUsers(): Promise<AdminUser[]> {
  const { data } = await apiClient.get<AdminUser[]>(ADMIN_USERS_ENDPOINT);
  return data;
}

export async function createUser(input: {
  email: string;
  password: string;
  role: string | null;
  site_ids: string[];
}): Promise<AdminUser> {
  const { data } = await apiClient.post<AdminUser>(ADMIN_USERS_ENDPOINT, input);
  return data;
}

export async function updateUser(
  userId: string,
  input: { role?: string | null; site_ids?: string[] },
): Promise<AdminUser> {
  const { data } = await apiClient.patch<AdminUser>(
    `${ADMIN_USERS_ENDPOINT}/${userId}`,
    input,
  );
  return data;
}

export async function deleteUser(userId: string): Promise<void> {
  await apiClient.delete(`${ADMIN_USERS_ENDPOINT}/${userId}`);
}
