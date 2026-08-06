import { redirect } from "next/navigation";

/**
 * This route previously hosted a 6-step wizard (app/create-copilot/
 * components/, store/) that never called the real backend -- its
 * knowledge-source options were hardcoded and its "success" step was a
 * pure setInterval animation. Rather than delete that code outright,
 * this route is redirected to the real, fully wired Copilot Management
 * page (/copilots), which has an equivalent Create Copilot flow backed
 * by the actual API. See the codebase audit notes for details.
 */
export default function CreateCopilotRedirect() {
  redirect("/copilots");
}
