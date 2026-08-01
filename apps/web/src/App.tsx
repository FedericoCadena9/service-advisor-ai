import {
  Activity,
  CalendarDays,
  CarFront,
  ChevronRight,
  ClipboardCheck,
  FileText,
  LayoutDashboard,
  Settings,
  ShieldCheck,
  Wrench,
} from "lucide-react";
import { type FormEvent, useCallback, useEffect, useState } from "react";

import { askContextualChat } from "./api/chat";
import { saveCheckin } from "./api/checkins";
import type { AdvisorContext } from "./api/advisor-context";
import { fetchQualityDashboard } from "./api/dashboard";
import { enterDemoWorkspace } from "./api/demo-session";
import type {
  CreateDemoSessionRequest,
  VehicleSearchResponse,
  WorkspaceResponse,
} from "./api/generated/types.gen";
import { fetchHealth } from "./api/health";
import {
  advanceMessage,
  previewSms,
  reserveAppointment,
  sendSms,
} from "./api/messaging";
import { decideQuoteReview, openQuoteReview } from "./api/quote-reviews";
import { draftQuote } from "./api/quotes";
import { fetchRecommendation } from "./api/recommendations";
import {
  decideAdvisorRun,
  fetchAdvisorRunEvents,
  startAdvisorRun,
} from "./api/advisor-run";
import { askServiceQuestion } from "./api/service-questions";
import { searchDemoVehicles } from "./api/vehicles";
import { confirmTranscript, recordVoiceNote } from "./api/voice";
import { QualityDashboard } from "./components/advisor/QualityDashboard";
import { RecommendationConsole } from "./components/advisor/RecommendationConsole";
import { VoiceCheckinPanel } from "./components/advisor/VoiceCheckinPanel";

type HealthState = "loading" | "waking" | "healthy" | "unavailable";

const COLD_START_RETRY_MS = 400;
const DEMO_VEHICLE_ID = "honda-civic-2019-lx";
const roles = [
  {
    value: "advisor",
    label: "Advisor",
    description:
      "Check in vehicles, prepare grounded recommendations, and open quotes.",
    icon: CarFront,
  },
  {
    value: "manager",
    label: "Manager",
    description: "Review escalations, outcomes, and quality metrics.",
    icon: ShieldCheck,
  },
  {
    value: "admin",
    label: "Admin",
    description: "See the entire operating picture and evaluation health.",
    icon: Activity,
  },
] as const;

export default function App() {
  const [state, setState] = useState<HealthState>("loading");
  const [workspace, setWorkspace] = useState<WorkspaceResponse | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [vehicles, setVehicles] = useState<VehicleSearchResponse[]>([]);
  const [checkinMileage, setCheckinMileage] = useState("");
  const [useProfile, setUseProfile] = useState<"normal" | "severe">("normal");
  const [severeUseFactors, setSevereUseFactors] = useState("");
  const [concern, setConcern] = useState("");
  const [appointmentWindow, setAppointmentWindow] = useState("");
  const [messageConsent, setMessageConsent] = useState(false);
  const [checkinSaved, setCheckinSaved] = useState(false);
  const [recommendation, setRecommendation] =
    useState<import("./api/generated/types.gen").RecommendationResponse>();
  const [advisorRunId, setAdvisorRunId] = useState<string | null>(null);
  const [traceId, setTraceId] = useState<string | null>(null);
  const [vehicleId, setVehicleId] = useState(DEMO_VEHICLE_ID);
  const [voiceNoteId, setVoiceNoteId] = useState<string | null>(null);
  const [sessionError, setSessionError] = useState<string | null>(null);
  const requireToken = useCallback(() => {
    if (!token) throw new Error("Session required");
    return token;
  }, [token]);
  const advisorContext = useCallback(
    (): AdvisorContext => ({
      vehicleId,
      currentMileageKm: Number(checkinMileage) || 0,
      traceId,
    }),
    [vehicleId, checkinMileage, traceId],
  );
  const loadDashboard = useCallback(
    async () => fetchQualityDashboard(requireToken()),
    [requireToken],
  );

  useEffect(() => {
    let cancelled = false;
    async function probeHealth() {
      try {
        await fetchHealth();
        if (!cancelled) setState("healthy");
      } catch {
        if (cancelled) return;
        setState("waking");
        await new Promise((resolve) =>
          setTimeout(resolve, COLD_START_RETRY_MS),
        );
        if (cancelled) return;
        try {
          await fetchHealth();
          if (!cancelled) setState("healthy");
        } catch {
          if (!cancelled) setState("unavailable");
        }
      }
    }
    void probeHealth();
    return () => {
      cancelled = true;
    };
  }, []);

  const message = {
    healthy: "Demo environment healthy",
    unavailable: "Demo environment unavailable",
    waking: "Waking the demo environment after scale to zero",
    loading: "Checking demo environment",
  }[state];
  async function chooseRole(role: CreateDemoSessionRequest["role"]) {
    setSessionError(null);
    try {
      const session = await enterDemoWorkspace(role);
      setToken(session.token);
      setWorkspace(session.workspace);
    } catch {
      setSessionError("Demo session unavailable");
    }
  }
  async function searchVehicles(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token || !query.trim()) return;
    try {
      setVehicles(await searchDemoVehicles(token, query));
    } catch {
      setSessionError("Vehicle search unavailable");
    }
  }
  async function submitCheckin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) return;
    try {
      await saveCheckin(token, {
        current_mileage_km: Number(checkinMileage),
        checked_in_on: new Date().toISOString().slice(0, 10),
        use_profile: useProfile,
        severe_use_factors: severeUseFactors
          .split(",")
          .map((factor) => factor.trim())
          .filter(Boolean),
        concern,
        appointment_window: appointmentWindow,
        message_consent: messageConsent,
        voice_note_id: voiceNoteId,
      });
      setCheckinSaved(true);
      setRecommendation(await fetchRecommendation(token, advisorContext()));
    } catch {
      setSessionError("Check-in could not be saved");
    }
  }

  return (
    <main className="flex min-h-screen bg-[#f7f7fb]">
      <aside className="hidden w-60 shrink-0 border-r border-border bg-card px-4 py-6 lg:flex lg:flex-col">
        <div className="flex items-center gap-2 px-2 text-lg font-bold tracking-tight text-foreground">
          <span className="grid size-8 place-items-center rounded-lg bg-primary text-sm text-primary-foreground">
            SA
          </span>
          service.ai
        </div>
        <nav
          aria-label="Primary navigation"
          className="mt-10 space-y-1 text-sm"
        >
          <a
            className="flex items-center gap-3 rounded-lg bg-primary/10 px-3 py-2.5 font-medium text-primary"
            href="#workspace"
          >
            <LayoutDashboard className="size-4" /> Advisor workspace
          </a>
          <a
            className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-muted-foreground hover:bg-muted"
            href="#checkin"
          >
            <CarFront className="size-4" /> Vehicle check-in
          </a>
          <a
            className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-muted-foreground hover:bg-muted"
            href="#recommendation"
          >
            <FileText className="size-4" /> Recommendations
          </a>
          <a
            className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-muted-foreground hover:bg-muted"
            href="#schedule"
          >
            <CalendarDays className="size-4" /> Appointments
          </a>
        </nav>
        <div className="mt-auto border-t border-border pt-4">
          <a
            className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-muted-foreground hover:bg-muted"
            href="#settings"
          >
            <Settings className="size-4" /> Settings
          </a>
          <p className="mt-4 px-3 text-xs leading-5 text-muted-foreground">
            Demo workspace
            <br />
            All records are synthetic.
          </p>
        </div>
      </aside>
      <div className="min-w-0 flex-1 px-4 py-5 sm:px-8 lg:px-10">
        <header className="mb-7 flex flex-col gap-5 border-b border-border pb-5 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <div className="grid size-10 place-items-center rounded-xl bg-primary text-primary-foreground shadow-sm">
              <Wrench className="size-5" />
            </div>
            <div>
              <h1 className="text-lg font-semibold tracking-tight">
                Service Advisor <span className="text-primary">AI</span>
              </h1>
              <p className="text-xs text-muted-foreground">
                Service operations workspace
              </p>
            </div>
          </div>
          <p
            role="status"
            className="flex items-center gap-2 self-start rounded-full border border-border bg-card px-3 py-1.5 text-xs text-muted-foreground sm:self-auto"
          >
            <span
              className={`size-1.5 rounded-full ${state === "healthy" ? "bg-emerald-400" : state === "unavailable" ? "bg-red-400" : "animate-pulse bg-primary"}`}
            />
            {message}
          </p>
        </header>
        {state === "healthy" && !workspace && (
          <section
            aria-labelledby="role-selection-heading"
            className="mx-auto grid min-h-[70vh] max-w-5xl items-center gap-10 py-8 lg:grid-cols-[1.05fr_1fr]"
          >
            <div className="max-w-xl">
              <p className="mb-4 text-xs font-semibold uppercase tracking-[0.24em] text-primary">
                Independent shop · Mexico
              </p>
              <h2
                id="role-selection-heading"
                className="text-4xl font-semibold tracking-[-0.045em] text-balance sm:text-5xl"
              >
                Make the next service call with evidence in hand.
              </h2>
              <p className="mt-5 max-w-lg text-base leading-7 text-muted-foreground">
                Every recommendation is anchored to a reviewed manual. Quotes
                move through clear human approval boundaries before a customer
                ever sees a message.
              </p>
              <div className="mt-8 flex flex-wrap gap-x-6 gap-y-3 text-sm text-muted-foreground">
                <span className="flex items-center gap-2">
                  <ShieldCheck className="size-4 text-primary" /> Reviewed
                  citations
                </span>
                <span className="flex items-center gap-2">
                  <ClipboardCheck className="size-4 text-primary" /> Human
                  approval
                </span>
              </div>
            </div>
            <div className="grid gap-3">
              {roles.map(({ value, label, description, icon: Icon }) => (
                <button
                  key={value}
                  type="button"
                  aria-label={`Enter as ${label}`}
                  onClick={() => void chooseRole(value)}
                  className="group flex items-center gap-4 rounded-xl border border-border bg-card p-5 text-left shadow-sm transition hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                >
                  <span className="grid size-11 shrink-0 place-items-center rounded-xl bg-primary/10 text-primary">
                    <Icon className="size-5" />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block text-base font-semibold">
                      Enter as {label}
                    </span>
                    <span className="mt-1 block text-sm leading-5 text-muted-foreground">
                      {description}
                    </span>
                  </span>
                  <ChevronRight className="size-5 text-muted-foreground transition group-hover:translate-x-1 group-hover:text-primary" />
                </button>
              ))}
            </div>
          </section>
        )}
        {workspace && (
          <section
            id="workspace"
            aria-labelledby="workspace-heading"
            className="mx-auto max-w-6xl space-y-5"
          >
            <div className="flex flex-col gap-3 rounded-xl border border-border bg-card px-5 py-4 shadow-sm sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary">
                  Live demo workspace
                </p>
                <h2
                  id="workspace-heading"
                  className="mt-1 text-xl font-semibold"
                >
                  Protected demo workspace
                </h2>
              </div>
              <div className="flex gap-2 text-xs">
                <span className="rounded-full bg-primary/15 px-3 py-1.5 font-medium capitalize text-primary">
                  Role: {workspace.role}
                </span>
                <span className="rounded-full bg-muted px-3 py-1.5 text-muted-foreground">
                  Shop: {workspace.shop_id}
                </span>
              </div>
            </div>
            <form
              onSubmit={searchVehicles}
              role="search"
              className="flex flex-col gap-3 rounded-xl border border-border bg-card p-4 shadow-sm sm:flex-row sm:items-end"
            >
              <div className="flex-1">
                <label
                  htmlFor="vehicle-search"
                  className="mb-1.5 block text-sm font-medium"
                >
                  Search demo vehicle
                </label>
                <input
                  id="vehicle-search"
                  name="vehicle-search"
                  type="search"
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                />
              </div>
              <button
                type="submit"
                className="rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground transition hover:brightness-110"
              >
                Search
              </button>
            </form>
            <ul
              aria-label="Vehicle search results"
              className="grid gap-2 sm:grid-cols-2"
            >
              {vehicles.map((vehicle) => (
                <li key={vehicle.id}>
                  <button
                    type="button"
                    onClick={() => setVehicleId(vehicle.id)}
                    className={`w-full rounded-lg border p-3 text-left text-sm transition ${vehicleId === vehicle.id ? "border-primary bg-primary/10 text-primary" : "border-border bg-card hover:border-primary/40 hover:bg-muted/50"}`}
                  >{`${vehicle.vehicle_label} — Demo data`}</button>
                </li>
              ))}
            </ul>
            <form
              onSubmit={submitCheckin}
              aria-labelledby="checkin-heading"
              id="checkin"
              className="grid gap-6 rounded-xl border border-border bg-card p-5 shadow-sm lg:grid-cols-[1.15fr_0.85fr] lg:p-6"
            >
              <div className="space-y-5">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary">
                    01 · Intake
                  </p>
                  <h3
                    id="checkin-heading"
                    className="mt-1 text-xl font-semibold"
                  >
                    Vehicle check-in
                  </h3>
                  <p className="mt-1 text-sm text-muted-foreground">
                    Capture the operating context before any recommendation is
                    generated.
                  </p>
                </div>
                <div className="grid gap-4 sm:grid-cols-2">
                  <div>
                    <label
                      htmlFor="current-mileage"
                      className="mb-1.5 block text-sm font-medium"
                    >
                      Current mileage (km)
                    </label>
                    <input
                      id="current-mileage"
                      type="number"
                      min="42500"
                      required
                      value={checkinMileage}
                      onChange={(event) =>
                        setCheckinMileage(event.target.value)
                      }
                    />
                  </div>
                  <div>
                    <label
                      htmlFor="use-profile"
                      className="mb-1.5 block text-sm font-medium"
                    >
                      Use profile
                    </label>
                    <select
                      id="use-profile"
                      value={useProfile}
                      onChange={(event) =>
                        setUseProfile(event.target.value as "normal" | "severe")
                      }
                    >
                      <option value="normal">Normal use</option>
                      <option value="severe">Severe use</option>
                    </select>
                  </div>
                </div>
                <div>
                  <label
                    htmlFor="severe-use-factors"
                    className="mb-1.5 block text-sm font-medium"
                  >
                    Severe use factors
                  </label>
                  <input
                    id="severe-use-factors"
                    value={severeUseFactors}
                    onChange={(event) =>
                      setSevereUseFactors(event.target.value)
                    }
                  />
                </div>
                <div>
                  <label
                    htmlFor="concern"
                    className="mb-1.5 block text-sm font-medium"
                  >
                    Written concern
                  </label>
                  <textarea
                    id="concern"
                    required
                    value={concern}
                    onChange={(event) => setConcern(event.target.value)}
                  />
                </div>
                <div>
                  <label
                    htmlFor="appointment-window"
                    className="mb-1.5 block text-sm font-medium"
                  >
                    Desired appointment window
                  </label>
                  <input
                    id="appointment-window"
                    required
                    value={appointmentWindow}
                    onChange={(event) =>
                      setAppointmentWindow(event.target.value)
                    }
                  />
                </div>
                <label className="flex cursor-pointer items-center gap-3 rounded-lg border border-border bg-muted/40 p-3 text-sm">
                  <input
                    id="message-consent"
                    type="checkbox"
                    checked={messageConsent}
                    onChange={(event) =>
                      setMessageConsent(event.target.checked)
                    }
                    className="size-4 accent-[oklch(0.76_0.16_64)]"
                  />
                  Consent to prepare a message
                </label>
                <button
                  type="submit"
                  className="w-full rounded-lg bg-primary px-4 py-3 text-sm font-semibold text-primary-foreground transition hover:brightness-110"
                >
                  Confirm check-in
                </button>
              </div>
              <aside className="rounded-xl border border-primary/15 bg-primary/5 p-4 lg:p-5">
                <p className="mb-4 text-xs font-semibold uppercase tracking-[0.18em] text-primary">
                  Optional context
                </p>
                <VoiceCheckinPanel
                  onRecord={async (note) =>
                    recordVoiceNote(requireToken(), note)
                  }
                  onConfirm={async (noteId, transcript) =>
                    confirmTranscript(requireToken(), noteId, transcript)
                  }
                  onConfirmed={setVoiceNoteId}
                />
              </aside>
            </form>
            {checkinSaved && (
              <p
                role="status"
                className="rounded-lg border border-emerald-400/25 bg-emerald-400/10 px-4 py-3 text-sm text-emerald-200"
              >
                Check-in confirmed
              </p>
            )}
            <div id="recommendation">
              <RecommendationConsole
                recommendation={recommendation}
                onStartRun={async () => {
                  const activeToken = requireToken();
                  const run = await startAdvisorRun(activeToken);
                  setAdvisorRunId(run.id);
                  setTraceId(run.trace_id);
                  return {
                    id: run.id,
                    events: await fetchAdvisorRunEvents(activeToken, run.id),
                  };
                }}
                onApproveRun={async () => {
                  const activeToken = requireToken();
                  if (!advisorRunId) throw new Error("Run required");
                  await decideAdvisorRun(activeToken, advisorRunId);
                }}
                onAsk={async (question) =>
                  (
                    await askContextualChat(
                      requireToken(),
                      question,
                      advisorContext(),
                    )
                  ).text
                }
                onDraftQuote={async (serviceCodes) =>
                  draftQuote(requireToken(), serviceCodes, advisorContext())
                }
                onOpenReview={async (serviceCodes) =>
                  openQuoteReview(
                    requireToken(),
                    serviceCodes,
                    advisorContext(),
                  )
                }
                onDecideReview={async (reviewId, decision, reason) =>
                  decideQuoteReview(requireToken(), reviewId, decision, {
                    idempotencyKey: reviewId,
                    reason,
                    context: advisorContext(),
                  })
                }
                onAskData={async (question) =>
                  askServiceQuestion(requireToken(), question)
                }
                timeline={{
                  onReserve: async (quoteId) =>
                    reserveAppointment(requireToken(), quoteId),
                  onPreview: async (quoteId) =>
                    previewSms(requireToken(), quoteId),
                  onSend: async (quoteId, text) =>
                    sendSms(requireToken(), quoteId, text),
                  onAdvance: async (deliveryId) =>
                    advanceMessage(requireToken(), deliveryId),
                }}
              />
            </div>
            {(workspace.role === "manager" || workspace.role === "admin") && (
              <QualityDashboard onLoad={loadDashboard} />
            )}
          </section>
        )}
        {sessionError && (
          <p
            role="alert"
            className="fixed right-5 bottom-5 rounded-lg border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive shadow-xl"
          >
            {sessionError}
          </p>
        )}
      </div>
    </main>
  );
}
