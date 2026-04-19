import { PlaceholderPage } from "@/components/console/PlaceholderPage";
export default function Page() {
  return <PlaceholderPage title="Policy Console" subtitle="Manage OPA and OpenFGA-backed policies, assignments, and evaluation outcomes." items={["Policy list with status and revision", "Assignment to agents, groups, tenants", "Allow/deny examples and rationale", "Simulation panel placeholder for what-if evaluations"]} />;
}
