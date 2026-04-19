import { MarketingPage } from "@/components/marketing/MarketingPage";
export default function Page() {
  return <MarketingPage title="Security" subtitle="Security controls designed for enterprise AI systems." bullets={["Tenant isolation and policy-scoped access", "Webhook signature verification and secret hygiene", "Audit integrity with correlation IDs and event streams", "Readiness/liveness and dependency-aware operations"]} />;
}
