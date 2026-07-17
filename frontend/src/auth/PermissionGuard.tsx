import type { PropsWithChildren, ReactNode } from "react";
import { useAuth } from "./AuthContext";

export function PermissionGuard({
  permission,
  all = [],
  fallback = null,
  children,
}: PropsWithChildren<{
  permission?: string;
  all?: string[];
  fallback?: ReactNode;
}>) {
  const { hasPermission, hasAllPermissions } = useAuth();
  const visible = permission ? hasPermission(permission) : hasAllPermissions(all);
  return visible ? <>{children}</> : <>{fallback}</>;
}
