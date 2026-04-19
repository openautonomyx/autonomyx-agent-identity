import { MarketingPage } from "@/components/marketing/MarketingPage";
export default function Page() {
  return <MarketingPage title="Integrations" subtitle="Meet enterprise requirements without building custom governance from scratch." bullets={["OpenFGA relationship model support", "OPA policy bundle compatibility", "Keycloak realm/user lifecycle hooks", "Gateway and webhook event consumer patterns"]} />;
}
