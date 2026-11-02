"use client";

import { usePathname } from "next/navigation";
import InstitutionalFooter from "@/components/InstitutionalFooter";

export default function PublicSiteFooter() {
  const pathname = usePathname();
  return pathname.startsWith("/dashboard") ? null : <InstitutionalFooter />;
}
