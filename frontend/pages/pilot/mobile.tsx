import Head from "next/head";
import type { GetStaticProps, NextPage } from "next";
import pilotFixture from "@/data/pilot_unified_mobile_v1.json";
import {
  Bell,
  Brain,
  Bookmark,
  BriefcaseBusiness,
  Building2,
  CalendarDays,
  Camera,
  Check,
  ChevronRight,
  CircleUserRound,
  ContactRound,
  Gamepad2,
  Inbox,
  LayoutGrid,
  LockKeyhole,
  Mic,
  Mail,
  Phone,
  Download,
  ExternalLink,
  Film,
  GraduationCap,
  Paperclip,
  Plane,
  Radio,
  RefreshCw,
  Send,
  Search,
  ShieldCheck,
  ShoppingCart,
  Smartphone,
  Sparkles,
  Tv,
  Clock3,
  Pencil,
  Trash2,
  UserPlus,
} from "lucide-react";
import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import styles from "@/styles/PilotMobile.module.css";
import type { PhonePairingChallenge, PilotMobileConnection } from "@/lib/pilot/pairing";

type SpaceKind = "personal" | "workspace" | "boardroom";

type Fixture = {
  schema_version: string;
  person: { persona_id: string; display_name: string; role: string };
  device: { label: string; status: string; possession_verified: boolean };
  connection: { state: string; mother_display_name: string; route: string; trust_words: string[]; last_verified_at: string };
  spaces: Array<{ space_id: string; kind: SpaceKind; display_name: string }>;
  memberships: Array<{ space_id: string; role_id: string; scopes: string[] }>;
  leases: Array<{ space_id: string; issuer_id: string; expires_at: string }>;
  surface_manifests: Array<{
    mode: SpaceKind;
    space_id: string;
    shortcuts: string[];
    cards: string[];
  }>;
};

type PageProps = { fixture: Fixture };

const modeCopy: Record<SpaceKind, { label: string; eyebrow: string; prompt: string }> = {
  personal: {
    label: "Personal",
    eyebrow: "Your private Pilot",
    prompt: "Ask Pilot to plan, remember, find or control anything…",
  },
  workspace: {
    label: "Workspace",
    eyebrow: "Focused collaboration",
    prompt: "Ask Pilot about this assignment…",
  },
  boardroom: {
    label: "Boardroom",
    eyebrow: "Business command view",
    prompt: "Ask Pilot to brief, delegate or prepare a decision…",
  },
};

const iconForShortcut = (shortcut: string) => {
  if (["TV", "Games"].includes(shortcut)) return shortcut === "TV" ? Tv : Gamepad2;
  if (shortcut === "Learning") return GraduationCap;
  if (shortcut === "Entertainment") return Film;
  if (shortcut === "Memory") return Brain;
  if (shortcut === "Guardian") return ShieldCheck;
  if (["Board", "Sales", "Finance", "Operations", "People", "Products"].includes(shortcut)) return Building2;
  if (["Briefing", "Marketing", "Files"].includes(shortcut)) return BriefcaseBusiness;
  if (shortcut === "Calendar") return CalendarDays;
  if (shortcut === "Contacts") return ContactRound;
  if (shortcut === "Messages") return Mail;
  if (shortcut === "Shopping") return ShoppingCart;
  if (shortcut === "Pilot") return Sparkles;
  return LayoutGrid;
};

const cardContent: Record<string, { title: string; detail: string; state: string }> = {
  task: { title: "Collect dry cleaning", detail: "Prepared · not yet delegated", state: "prepared" },
  reminder: { title: "One reminder due today", detail: "Private details hidden", state: "pending" },
  message: { title: "New private message", detail: "Unlock to reveal sender and content", state: "locked" },
  receipt: { title: "Mother verified", detail: "Signed receipt available", state: "verified" },
  review: { title: "Work ready for review", detail: "No external action taken", state: "pending" },
  briefing: { title: "Morning board briefing", detail: "Sources and freshness attached", state: "verified" },
  decision: { title: "Decision needs approval", detail: "Exact scope is ready to inspect", state: "pending" },
  delegation: { title: "Delegation prepared", detail: "Recipient has not accepted", state: "prepared" },
  approval: { title: "Private approval required", detail: "Possession proof needed", state: "locked" },
};

const stateExamples = ["empty", "loading", "locked", "offline", "denied", "expired", "failed", "verified"];

const shortcutGroup = (mode: SpaceKind, shortcut: string) => {
  if (mode === "personal") {
    if (["Calendar", "Tasks", "Contacts", "Messages"].includes(shortcut)) return "Everyday";
    if (["Devices", "TV", "Games", "Learning", "Entertainment"].includes(shortcut)) return "Home & experiences";
    return "Private life";
  }
  if (mode === "workspace") return ["Briefing", "Tasks", "Pilot"].includes(shortcut) ? "Assignment" : "Resources";
  return ["Board", "Sales", "Marketing", "Finance", "Operations"].includes(shortcut) ? "Business" : "People & resources";
};

const PilotMobile: NextPage<PageProps> = ({ fixture }) => {
  const [mode, setMode] = useState<SpaceKind>("personal");
  const [activeNav, setActiveNav] = useState("Pilot");
  const [selectedShortcut, setSelectedShortcut] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [listening, setListening] = useState(false);
  const [notice, setNotice] = useState("2 private updates hidden");
  const [pairingOpen, setPairingOpen] = useState(false);
  const [pairingCode, setPairingCode] = useState("");
  const [pilotAddress, setPilotAddress] = useState("");
  const [pairingStatus, setPairingStatus] = useState("This screen is showing the product preview until you connect your Pilot.");
  const [pairingChallenge, setPairingChallenge] = useState<PhonePairingChallenge | null>(null);
  const [pairingTrustWords, setPairingTrustWords] = useState<string[]>([]);
  const [connection, setConnection] = useState<PilotMobileConnection | null>(null);
  const [liveInbox, setLiveInbox] = useState<Record<string, unknown> | null>(null);
  const [personalPilot, setPersonalPilot] = useState<Record<string, unknown> | null>(null);
  const [personalCalendar, setPersonalCalendar] = useState<Record<string, unknown> | null>(null);
  const [calendarStatus, setCalendarStatus] = useState("Open Calendar to load your private schedule.");
  const [calendarAction, setCalendarAction] = useState<"create" | "reschedule" | "cancel">("create");
  const [calendarTitle, setCalendarTitle] = useState("");
  const [calendarStart, setCalendarStart] = useState("");
  const [calendarEnd, setCalendarEnd] = useState("");
  const [calendarEventId, setCalendarEventId] = useState("");
  const [calendarLocation, setCalendarLocation] = useState("");
  const [calendarAttendees, setCalendarAttendees] = useState("");
  const [calendarTravel, setCalendarTravel] = useState("0");
  const [calendarReminder, setCalendarReminder] = useState("30");
  const [calendarNotify, setCalendarNotify] = useState(false);
  const [availabilityStart, setAvailabilityStart] = useState("");
  const [availabilityEnd, setAvailabilityEnd] = useState("");
  const [availability, setAvailability] = useState<Array<Record<string, unknown>>>([]);
  const [personalContacts, setPersonalContacts] = useState<Array<Record<string, unknown>>>([]);
  const [contactStatus, setContactStatus] = useState("Your contacts stay private on the mother brain.");
  const [contactQuery, setContactQuery] = useState("");
  const [contactResolution, setContactResolution] = useState<Record<string, unknown> | null>(null);
  const [contactId, setContactId] = useState("");
  const [contactName, setContactName] = useState("");
  const [contactEmail, setContactEmail] = useState("");
  const [contactWhatsapp, setContactWhatsapp] = useState("");
  const [contactPilotPersona, setContactPilotPersona] = useState("");
  const [contactPilotMother, setContactPilotMother] = useState("");
  const [contactPreferredRoute, setContactPreferredRoute] = useState<"pilot" | "whatsapp" | "email" | "">("");
  const [personalCommunication, setPersonalCommunication] = useState<Record<string, unknown> | null>(null);
  const [communicationStatus, setCommunicationStatus] = useState("Open Messages to load private drafts and receipts.");
  const [communicationContact, setCommunicationContact] = useState("");
  const [communicationChannel, setCommunicationChannel] = useState<"email" | "whatsapp" | "pilot">("email");
  const [communicationSubject, setCommunicationSubject] = useState("");
  const [communicationBody, setCommunicationBody] = useState("");
  const [communicationFollowUp, setCommunicationFollowUp] = useState("");
  const [preparedCall, setPreparedCall] = useState<Record<string, unknown> | null>(null);
  const [personalServices, setPersonalServices] = useState<Record<string, unknown> | null>(null);
  const [serviceStatus, setServiceStatus] = useState("Open Shopping to prepare a private action.");
  const [serviceKind, setServiceKind] = useState<"shopping" | "booking" | "maps" | "music">("shopping");
  const [servicePrimary, setServicePrimary] = useState("");
  const [serviceSecondary, setServiceSecondary] = useState("");
  const [serviceQuantity, setServiceQuantity] = useState("1");
  const [serviceDetails, setServiceDetails] = useState<Record<string, string>>({});
  const [personalLibrary, setPersonalLibrary] = useState<Record<string, unknown> | null>(null);
  const [libraryStatus, setLibraryStatus] = useState("Open Files to load saved items and private attachments.");
  const [personalDevices, setPersonalDevices] = useState<Record<string, unknown> | null>(null);
  const [deviceStatus, setDeviceStatus] = useState("Open Devices or TV to verify your local mesh.");
  const [deviceLastResult, setDeviceLastResult] = useState<Record<string, unknown> | null>(null);
  const [personalExperiences, setPersonalExperiences] = useState<Record<string, unknown> | null>(null);
  const [experienceStatus, setExperienceStatus] = useState("Open Learning, Games or Entertainment to load your private progress.");
  const [personalMemory, setPersonalMemory] = useState<Record<string, unknown> | null>(null);
  const [memoryStatus, setMemoryStatus] = useState("Open Memory to inspect what Pilot remembers about you.");
  const [memoryTarget, setMemoryTarget] = useState("");
  const [memoryKind, setMemoryKind] = useState("preference");
  const [memorySummary, setMemorySummary] = useState("");
  const [memoryScope, setMemoryScope] = useState<"private" | "household_shared">("private");
  const [personalGuardian, setPersonalGuardian] = useState<Record<string, unknown> | null>(null);
  const [guardianStatus, setGuardianStatus] = useState("Guardian uses separate emergency permissions and never silently contacts anyone.");
  const [guardianTarget, setGuardianTarget] = useState("");
  const [guardianContact, setGuardianContact] = useState("");
  const [guardianChannel, setGuardianChannel] = useState("pilot");
  const [guardianShareLocation, setGuardianShareLocation] = useState(false);
  const [guardianLocationReceipt, setGuardianLocationReceipt] = useState("");
  const [personalIntelligence, setPersonalIntelligence] = useState<Record<string, unknown> | null>(null);
  const [workspaceInvitations, setWorkspaceInvitations] = useState<Array<Record<string, unknown>>>([]);
  const [workspaceInvitationStatus, setWorkspaceInvitationStatus] = useState("Workspace invitations are private to this phone.");
  const [workspaceSummary, setWorkspaceSummary] = useState<Record<string, unknown> | null>(null);
  const [workspaceConversationDepartment, setWorkspaceConversationDepartment] = useState("boardroom");
  const [workspaceConversationDraft, setWorkspaceConversationDraft] = useState("");
  const [workspaceConversation, setWorkspaceConversation] = useState<Record<string, unknown> | null>(null);
  const [workspaceCards, setWorkspaceCards] = useState<Array<Record<string, unknown>>>([]);
  const [workspaceSignoffRole, setWorkspaceSignoffRole] = useState<"accountant" | "auditor" | "adviser" | "director">("director");
  const [workspaceSignoffs, setWorkspaceSignoffs] = useState<Array<Record<string, unknown>>>([]);
  const [workspaceCommercial, setWorkspaceCommercial] = useState<Record<string, unknown> | null>(null);
  const [workspaceCommercialStatus, setWorkspaceCommercialStatus] = useState("Open your business controls from an authorised workspace.");
  const [workspaceCommercialDepartment, setWorkspaceCommercialDepartment] = useState("sales");
  const [workspaceCommercialActions, setWorkspaceCommercialActions] = useState("100");
  const [workspaceCommercialBudget, setWorkspaceCommercialBudget] = useState("0");
  const [workspaceCommercialCapacity, setWorkspaceCommercialCapacity] = useState("100");
  const [workspaceCommercialOverage, setWorkspaceCommercialOverage] = useState(false);
  const [pilotResult, setPilotResult] = useState<Record<string, unknown> | null>(null);
  const [learningProfile, setLearningProfile] = useState("explorer_a");
  const [learningAge, setLearningAge] = useState("6-7");
  const [learningDifficulty, setLearningDifficulty] = useState("foundation");
  const [learningSubject, setLearningSubject] = useState("spanish");
  const [entertainmentTitle, setEntertainmentTitle] = useState("");
  const [entertainmentOutcome, setEntertainmentOutcome] = useState("watched");
  const [reminderTask, setReminderTask] = useState("");
  const [reminderTrigger, setReminderTrigger] = useState<"time" | "arrival" | "departure" | "journey" | "closing_time">("time");
  const [reminderAt, setReminderAt] = useState("");
  const [reminderLocation, setReminderLocation] = useState("");
  const [reminderRepeat, setReminderRepeat] = useState("none");
  const [liveState, setLiveState] = useState<"preview" | "connecting" | "live" | "reconnecting" | "offline" | "closed">("preview");
  const [liveRoute, setLiveRoute] = useState<"lan" | "direct" | "relay" | "preview">("preview");
  const [inboxQuery, setInboxQuery] = useState("");
  const [inboxKind, setInboxKind] = useState<"all" | "messages" | "tasks" | "files">("all");
  const [inboxResults, setInboxResults] = useState<Array<Record<string, unknown>> | null>(null);
  const [trustedHandoffs, setTrustedHandoffs] = useState<Record<string, unknown> | null>(null);
  const [handoffType, setHandoffType] = useState<"message" | "task" | "reminder" | "file" | "moment">("message");
  const [handoffRelationship, setHandoffRelationship] = useState("");
  const [handoffTitle, setHandoffTitle] = useState("");
  const [handoffDetail, setHandoffDetail] = useState("");
  const [handoffDue, setHandoffDue] = useState("");
  const [handoffMomentId, setHandoffMomentId] = useState("");
  const [handoffContextHash, setHandoffContextHash] = useState("");
  const [handoffProviderUrl, setHandoffProviderUrl] = useState("");
  const [handoffFile, setHandoffFile] = useState<File | null>(null);
  const [pendingTrustedTask, setPendingTrustedTask] = useState<Record<string, unknown> | null>(null);
  const [recordingFor, setRecordingFor] = useState<string | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const recordingStreamRef = useRef<MediaStream | null>(null);
  const recordingChunksRef = useRef<Blob[]>([]);
  const recordingStartedRef = useRef(0);
  const recordingPeerRef = useRef<{ recipientPersonaId: string; recipientMotherId: string; floorId: string } | null>(null);
  const recordingHeldRef = useRef(false);
  const floorRenewalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const manifest = useMemo(
    () => fixture.surface_manifests.find((item) => item.mode === mode)!,
    [fixture.surface_manifests, mode],
  );
  const space = fixture.spaces.find((item) => item.space_id === manifest.space_id)!;
  const membership = fixture.memberships.find((item) => item.space_id === space.space_id)!;
  const lease = fixture.leases.find((item) => item.space_id === space.space_id)!;
  const activeWorkspaceItem = useMemo(
    () => workspaceInvitations.find((item) => (item.invitation as Record<string, unknown> | undefined)?.state === "accepted") || null,
    [workspaceInvitations],
  );
  const sharedTVState = String(
    ((personalDevices?.shared_tv as Record<string, unknown> | undefined) || {}).state || "locked",
  );

  useEffect(() => {
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("/pilot-mobile-sw.js").catch(() => {
        // The shell remains usable online if installation is unavailable.
      });
    }
    let stopLive: (() => void) | undefined;
    import("@/lib/pilot/pairing").then(async ({ getPilotConnection, readPilotInbox, readTrustedPilotHandoffs, readPersonalPilot, readPersonalCalendar, readPersonalContacts, readPersonalCommunication, readPersonalServices, readPersonalLibrary, readPersonalDeviceMesh, readPersonalExperiences, readPersonalMemory, readPersonalGuardian, readPersonalIntelligence, readWorkspaceInvitations, watchPilotInbox }) => {
      const saved = await getPilotConnection();
      if (!saved) return;
      setConnection(saved);
      setPilotAddress(saved.endpoint);
      setPairingTrustWords(saved.trustWords);
      setPairingStatus("Connected securely to your Pilot.");
      let initialInboxRevision = 0;
      try {
        const initialInbox = await readPilotInbox(saved, setLiveRoute);
        initialInboxRevision = Number(initialInbox.revision || 0);
        setLiveInbox(initialInbox);
        try { setTrustedHandoffs(await readTrustedPilotHandoffs(saved)); } catch { /* older mothers omit this optional surface */ }
        setPersonalPilot(await readPersonalPilot(saved));
        try { setPersonalCalendar(await readPersonalCalendar(saved)); }
        catch (error) { setCalendarStatus(error instanceof Error ? error.message : "Reconnect this phone to add calendar permission."); }
        try {
          const contacts = await readPersonalContacts(saved);
          setPersonalContacts((contacts.contacts as Array<Record<string, unknown>> | undefined) || []);
        } catch (error) { setContactStatus(error instanceof Error ? error.message : "Reconnect this phone to add contact permission."); }
        try { setPersonalCommunication(await readPersonalCommunication(saved)); }
        catch (error) { setCommunicationStatus(error instanceof Error ? error.message : "Reconnect this phone to add communication permission."); }
        try { setPersonalServices(await readPersonalServices(saved)); }
        catch (error) { setServiceStatus(error instanceof Error ? error.message : "Reconnect this phone to add private service permission."); }
        try { setPersonalLibrary(await readPersonalLibrary(saved)); }
        catch (error) { setLibraryStatus(error instanceof Error ? error.message : "Reconnect this phone to add private library permission."); }
        try { setPersonalDevices(await readPersonalDeviceMesh(saved)); }
        catch (error) { setDeviceStatus(error instanceof Error ? error.message : "Reconnect this phone to add device-mesh permission."); }
        try { setPersonalExperiences(await readPersonalExperiences(saved)); }
        catch (error) { setExperienceStatus(error instanceof Error ? error.message : "Reconnect this phone to add learning and entertainment permission."); }
        try { setPersonalMemory(await readPersonalMemory(saved)); }
        catch (error) { setMemoryStatus(error instanceof Error ? error.message : "Reconnect this phone to add private memory permission."); }
        try { setPersonalGuardian(await readPersonalGuardian(saved)); }
        catch (error) { setGuardianStatus(error instanceof Error ? error.message : "Reconnect this phone to add Guardian permission."); }
        try { setPersonalIntelligence(await readPersonalIntelligence(saved)); }
        catch (error) { setNotice(error instanceof Error ? error.message : "Reconnect this phone to use AION Native."); }
        try {
          const invitations = await readWorkspaceInvitations(saved);
          setWorkspaceInvitations((invitations.invitations as Array<Record<string, unknown>> | undefined) || []);
        } catch (error) { setWorkspaceInvitationStatus(error instanceof Error ? error.message : "Reconnect this phone to review workspace invitations."); }
      } catch { setPairingStatus("Pilot found this phone, but the private connection needs renewing."); }
      stopLive = watchPilotInbox(saved, {
        onStream: setLiveInbox,
        onState: setLiveState,
        onRoute: setLiveRoute,
        initialRevision: initialInboxRevision,
      });
    }).catch(() => undefined);
    return () => stopLive?.();
  }, []);

  useEffect(() => {
    if (!connection || sharedTVState !== "you") return;
    let stopped = false;
    const provePresence = async () => {
      if (stopped || document.visibilityState !== "visible" || !navigator.onLine) return;
      try {
        const { confirmPersonalTVPresence } = await import("@/lib/pilot/pairing");
        const presence = await confirmPersonalTVPresence(connection);
        if (stopped) return;
        setPersonalDevices((current) => current ? {
          ...current,
          shared_tv: { ...((current.shared_tv as Record<string, unknown> | undefined) || {}), ...presence },
        } : current);
      } catch (error) {
        if (stopped) return;
        const message = error instanceof Error ? error.message : "Pilot could not prove this phone is still nearby.";
        if (/locked|expired|departed|does not control/i.test(message)) {
          setPersonalDevices((current) => current ? {
            ...current,
            shared_tv: { ...((current.shared_tv as Record<string, unknown> | undefined) || {}), state: "locked", expires_at: null, presence_expires_at: null },
          } : current);
          setDeviceStatus("Television workspace locked. Take control again from this trusted phone.");
        }
      }
    };
    const onVisibility = () => { if (document.visibilityState === "visible") void provePresence(); };
    void provePresence();
    const timer = window.setInterval(() => void provePresence(), 30_000);
    document.addEventListener("visibilitychange", onVisibility);
    window.addEventListener("online", provePresence);
    return () => {
      stopped = true;
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", onVisibility);
      window.removeEventListener("online", provePresence);
    };
  }, [connection, sharedTVState]);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const query = draft.trim();
    if (!query) return;
    if (!connection) {
      setNotice("Connect this phone to send private requests to your mother brain.");
      return;
    }
    setDraft("");
    setNotice("AION is routing this privately through local capability first…");
    try {
      const { askPersonalIntelligence, readPersonalIntelligence } = await import("@/lib/pilot/pairing");
      const result = await askPersonalIntelligence(connection, query);
      setPilotResult(result);
      setPersonalIntelligence(await readPersonalIntelligence(connection));
      setNotice(String(result.spoken_response || "Pilot completed the private request."));
    } catch (error) { setNotice(error instanceof Error ? error.message : "Pilot could not complete that private request."); }
  };

  const findPilot = async () => {
    setPairingStatus("Finding and verifying your Pilot…");
    try {
      const { beginPilotPairing } = await import("@/lib/pilot/pairing");
      const result = await beginPilotPairing({
        endpoint: pilotAddress,
        deviceLabel: `${fixture.person.display_name}'s phone`,
      });
      setPairingChallenge(result.challenge);
      setPairingTrustWords(result.trustWords);
      if (result.liveInboxUrl) setPairingStatus("Pilot verified. Check the words and enter the six-digit code shown locally.");
      setPairingStatus("Pilot is showing a six-digit code. Check the words match, then enter the code below.");
    } catch (error) {
      setPairingStatus(error instanceof Error ? error.message : "Pilot could not find that secure address.");
    }
  };

  const connectPilot = async () => {
    if (!pairingChallenge) return;
    setPairingStatus("Verifying this phone with your Pilot…");
    try {
      const { completePilotPairing, readPilotInbox, readTrustedPilotHandoffs, readPersonalPilot, readPersonalCalendar, readPersonalContacts, readPersonalCommunication, readPersonalServices, readPersonalLibrary, readPersonalDeviceMesh, readPersonalExperiences, readPersonalMemory, readPersonalGuardian, readPersonalIntelligence, readWorkspaceInvitations } = await import("@/lib/pilot/pairing");
      const discovery = await (await import("@/lib/pilot/pairing")).discoverPilot(pilotAddress);
      const saved = await completePilotPairing({ endpoint: pilotAddress, challenge: pairingChallenge, confirmationCode: pairingCode, trustWords: pairingTrustWords, liveInboxUrl: discovery.liveInboxUrl });
      setConnection(saved);
      setLiveInbox(await readPilotInbox(saved));
      setTrustedHandoffs(await readTrustedPilotHandoffs(saved));
      setPersonalPilot(await readPersonalPilot(saved));
      setPersonalCalendar(await readPersonalCalendar(saved));
      setCalendarStatus("Private calendar connected.");
      const contacts = await readPersonalContacts(saved);
      setPersonalContacts((contacts.contacts as Array<Record<string, unknown>> | undefined) || []);
      setContactStatus("Private contacts connected.");
      setPersonalCommunication(await readPersonalCommunication(saved));
      setCommunicationStatus("Private communication connected.");
      setPersonalServices(await readPersonalServices(saved));
      setServiceStatus("Private service actions connected.");
      setPersonalLibrary(await readPersonalLibrary(saved));
      setLibraryStatus("Private files and saved items connected.");
      setPersonalDevices(await readPersonalDeviceMesh(saved));
      setDeviceStatus("Private device mesh connected.");
      setPersonalExperiences(await readPersonalExperiences(saved));
      setExperienceStatus("Private learning, games and entertainment connected.");
      setPersonalMemory(await readPersonalMemory(saved));
      setMemoryStatus("Private memory controls connected.");
      setPersonalGuardian(await readPersonalGuardian(saved));
      setGuardianStatus("Guardian priority controls connected.");
      setPersonalIntelligence(await readPersonalIntelligence(saved));
      const invitations = await readWorkspaceInvitations(saved);
      setWorkspaceInvitations((invitations.invitations as Array<Record<string, unknown>> | undefined) || []);
      setPairingChallenge(null);
      setPairingCode("");
      setPairingStatus("Connected securely. Inbox is now showing this person's live private stream.");
    } catch (error) {
      setPairingStatus(error instanceof Error ? error.message : "Pilot could not connect this phone.");
    }
  };

  const respondToWorkspaceInvitation = async (item: Record<string, unknown>, decision: "accepted" | "declined") => {
    if (!connection) return;
    const invitation = item.invitation as Record<string, unknown>;
    setWorkspaceInvitationStatus(decision === "accepted" ? "Accepting this exact role and scope…" : "Declining this invitation…");
    try {
      const { respondWorkspaceInvitation, readWorkspaceInvitations } = await import("@/lib/pilot/pairing");
      await respondWorkspaceInvitation(connection, String(invitation.invitation_id || ""), decision);
      const refreshed = await readWorkspaceInvitations(connection);
      setWorkspaceInvitations((refreshed.invitations as Array<Record<string, unknown>> | undefined) || []);
      setWorkspaceInvitationStatus(decision === "accepted" ? "Workspace accepted. Its granted role is now available." : "Invitation declined. No workspace access was created.");
    } catch (error) { setWorkspaceInvitationStatus(error instanceof Error ? error.message : "Pilot could not update that invitation."); }
  };

  const openWorkspaceSummary = async (item: Record<string, unknown>, surface: "briefings" | "departments" | "dashboards") => {
    if (!connection) return;
    const member = item.membership as Record<string, unknown> | undefined;
    if (!member?.membership_id) { setWorkspaceInvitationStatus("Accept this workspace before opening its business summary."); return; }
    setWorkspaceInvitationStatus(`Loading the permitted ${surface} summary…`);
    try {
      const { readWorkspaceSurface } = await import("@/lib/pilot/pairing");
      const result = await readWorkspaceSurface(connection, String(member.membership_id), surface);
      setWorkspaceSummary(result);
      setWorkspaceInvitationStatus(`${surface[0].toUpperCase()}${surface.slice(1)} loaded from the workspace source of truth.`);
    } catch (error) { setWorkspaceInvitationStatus(error instanceof Error ? error.message : "Pilot could not open that workspace summary."); }
  };

  const sendWorkspaceTurn = async (item: Record<string, unknown>) => {
    if (!connection || !workspaceConversationDraft.trim()) return;
    const member = item.membership as Record<string, unknown> | undefined;
    if (!member?.membership_id) { setWorkspaceInvitationStatus("Accept this workspace before speaking to its Pilot."); return; }
    setWorkspaceInvitationStatus("Asking the permitted workspace intelligence…");
    try {
      const { sendWorkspaceConversationTurn } = await import("@/lib/pilot/pairing");
      const result = await sendWorkspaceConversationTurn(
        connection, String(member.membership_id), workspaceConversationDepartment, workspaceConversationDraft.trim(),
      );
      setWorkspaceConversation(result);
      setWorkspaceConversationDraft("");
      setWorkspaceInvitationStatus("Read-only answer returned from the workspace source of truth.");
    } catch (error) { setWorkspaceInvitationStatus(error instanceof Error ? error.message : "Pilot could not answer from that workspace."); }
  };

  const refreshWorkspaceCards = async (item: Record<string, unknown>) => {
    if (!connection) return;
    const member = item.membership as Record<string, unknown> | undefined;
    if (!member?.membership_id) return;
    try {
      const { readWorkspaceReviewCards } = await import("@/lib/pilot/pairing");
      const result = await readWorkspaceReviewCards(connection, String(member.membership_id));
      setWorkspaceCards((result.cards as Array<Record<string, unknown>> | undefined) || []);
      setWorkspaceInvitationStatus("Review cards refreshed from current workspace records.");
    } catch (error) { setWorkspaceInvitationStatus(error instanceof Error ? error.message : "Pilot could not load review cards."); }
  };

  const actOnWorkspaceCard = async (item: Record<string, unknown>, card: Record<string, unknown>, operation: "review" | "correct" | "delegate" | "approve") => {
    if (!connection) return;
    const member = item.membership as Record<string, unknown> | undefined;
    if (!member?.membership_id) return;
    const details: { correction?: string; recipient_ref?: string } = {};
    if (operation === "correct") {
      const correction = window.prompt("Describe the exact correction required")?.trim();
      if (!correction) return;
      details.correction = correction;
    }
    if (operation === "delegate") {
      const recipient = window.prompt("Enter the exact approved person reference")?.trim();
      if (!recipient) return;
      details.recipient_ref = recipient;
    }
    try {
      const { actOnWorkspaceReviewCard } = await import("@/lib/pilot/pairing");
      await actOnWorkspaceReviewCard(connection, String(member.membership_id), String(card.card_id), operation, String(card.scope_hash), details);
      await refreshWorkspaceCards(item);
      setWorkspaceInvitationStatus(operation === "approve" ? "Exact card approved. Approval did not execute an external action." : `Card ${operation} recorded.`);
    } catch (error) { setWorkspaceInvitationStatus(error instanceof Error ? error.message : "Pilot could not update that review card."); }
  };

  const refreshWorkspaceSignoffs = async (item: Record<string, unknown>) => {
    if (!connection) return;
    const member = item.membership as Record<string, unknown> | undefined;
    if (!member?.membership_id) return;
    const { readWorkspaceSignoffs } = await import("@/lib/pilot/pairing");
    const result = await readWorkspaceSignoffs(connection, String(member.membership_id));
    setWorkspaceSignoffs((result.packages as Array<Record<string, unknown>> | undefined) || []);
  };

  const prepareSignoff = async (item: Record<string, unknown>, card: Record<string, unknown>) => {
    if (!connection) return;
    const member = item.membership as Record<string, unknown> | undefined;
    if (!member?.membership_id) return;
    const statement = window.prompt(`Exact statement for the ${workspaceSignoffRole} to review`)?.trim();
    if (!statement) return;
    try {
      const { prepareWorkspaceSignoff } = await import("@/lib/pilot/pairing");
      await prepareWorkspaceSignoff(connection, String(member.membership_id), String(card.card_id), String(card.scope_hash), workspaceSignoffRole, statement);
      await refreshWorkspaceSignoffs(item);
      setWorkspaceInvitationStatus(`${workspaceSignoffRole} package prepared. Nothing was signed or executed.`);
    } catch (error) { setWorkspaceInvitationStatus(error instanceof Error ? error.message : "Pilot could not prepare the sign-off package."); }
  };

  const decideSignoff = async (item: Record<string, unknown>, signoff: Record<string, unknown>, decision: "signed" | "rejected") => {
    if (!connection) return;
    const member = item.membership as Record<string, unknown> | undefined;
    if (!member?.membership_id) return;
    const professionalReference = decision === "signed" ? window.prompt("State your professional reference or declared capacity")?.trim() : "rejected after review";
    if (!professionalReference) return;
    try {
      const { decideWorkspaceSignoff } = await import("@/lib/pilot/pairing");
      await decideWorkspaceSignoff(connection, String(member.membership_id), String(signoff.package_id), String(signoff.package_hash), decision, professionalReference);
      await refreshWorkspaceSignoffs(item);
      setWorkspaceInvitationStatus(`Package ${decision}. The signed receipt is bound to this phone and exact package hash.`);
    } catch (error) { setWorkspaceInvitationStatus(error instanceof Error ? error.message : "Pilot could not record the sign-off decision."); }
  };

  const continueWorkspaceOnDesktop = async (item: Record<string, unknown>) => {
    if (!connection) return;
    const member = item.membership as Record<string, unknown> | undefined;
    if (!member?.membership_id) return;
    try {
      const { prepareWorkspaceDesktopHandoff } = await import("@/lib/pilot/pairing");
      const result = await prepareWorkspaceDesktopHandoff(connection, String(member.membership_id), "Continue complex setup or deep work");
      const desktopPath = String(result.desktop_path || "");
      if (!desktopPath.startsWith("/aion-business?")) throw new Error("Pilot returned an invalid desktop destination.");
      window.open(`${window.location.origin}${desktopPath}`, "_blank", "noopener,noreferrer");
      setWorkspaceInvitationStatus("Desktop opened. Authenticate there; the handoff itself grants no access.");
    } catch (error) { setWorkspaceInvitationStatus(error instanceof Error ? error.message : "Pilot could not prepare the desktop handoff."); }
  };

  const refreshWorkspaceCommercial = async (item: Record<string, unknown>) => {
    if (!connection) return;
    const member = item.membership as Record<string, unknown> | undefined;
    if (!member?.membership_id) { setWorkspaceCommercialStatus("Accept an authorised workspace before opening its commercial controls."); return; }
    setWorkspaceCommercialStatus("Loading content-free usage and value evidence…");
    try {
      const { readWorkspaceCommercialDashboard } = await import("@/lib/pilot/pairing");
      const result = await readWorkspaceCommercialDashboard(connection, String(member.membership_id));
      setWorkspaceCommercial((result.dashboard as Record<string, unknown> | undefined) || null);
      setWorkspaceCommercialStatus("Current verified usage, limits and value evidence loaded.");
    } catch (error) { setWorkspaceCommercialStatus(error instanceof Error ? error.message : "Pilot could not load commercial controls."); }
  };

  const startWorkspaceTrial = async (item: Record<string, unknown>) => {
    if (!connection) return;
    const member = item.membership as Record<string, unknown> | undefined;
    if (!member?.membership_id) return;
    const actions = Number(workspaceCommercialActions), budget = Number(workspaceCommercialBudget);
    if (!Number.isInteger(actions) || actions < 1 || actions > 1_000_000 || !Number.isFinite(budget) || budget < 0) {
      setWorkspaceCommercialStatus("Enter a valid verified-action allowance and non-negative managed budget."); return;
    }
    if (!window.confirm(`Start a 30-day ${workspaceCommercialDepartment.replaceAll("_", " ")} trial with ${actions} verified actions and a EUR ${budget.toFixed(2)} managed-intelligence ceiling? No automatic renewal.`)) return;
    try {
      const { controlWorkspaceCommercialService } = await import("@/lib/pilot/pairing");
      const result = await controlWorkspaceCommercialService(connection, String(member.membership_id), {
        operation: "start_trial", department: workspaceCommercialDepartment, days: 30,
        action_limit: actions, managed_cost_limit: budget, currency: "EUR",
        offer_version: "pilot-mobile-visible-2026-09", consent_ref: `pilot-mobile-consent:${crypto.randomUUID()}`,
      });
      setWorkspaceCommercial((result.dashboard as Record<string, unknown> | undefined) || null);
      setWorkspaceCommercialStatus("Trial started with the exact displayed limits and no automatic renewal.");
    } catch (error) { setWorkspaceCommercialStatus(error instanceof Error ? error.message : "Pilot could not start that trial."); }
  };

  const cancelWorkspaceTrial = async (item: Record<string, unknown>, trialId: string) => {
    if (!connection || !window.confirm("Cancel this department service? Its safe review-only fallback will remain available.")) return;
    const member = item.membership as Record<string, unknown> | undefined;
    if (!member?.membership_id) return;
    try {
      const { controlWorkspaceCommercialService } = await import("@/lib/pilot/pairing");
      const result = await controlWorkspaceCommercialService(connection, String(member.membership_id), {
        operation: "cancel_trial", trial_id: trialId, cancellation_ref: `pilot-mobile-cancel:${crypto.randomUUID()}`,
      });
      setWorkspaceCommercial((result.dashboard as Record<string, unknown> | undefined) || null);
      setWorkspaceCommercialStatus("Cancellation recorded. Your brain, data, backup and export remain yours.");
    } catch (error) { setWorkspaceCommercialStatus(error instanceof Error ? error.message : "Pilot could not cancel that service."); }
  };

  const setWorkspaceCapacity = async (item: Record<string, unknown>) => {
    if (!connection) return;
    const member = item.membership as Record<string, unknown> | undefined;
    const limit = Number(workspaceCommercialCapacity);
    if (!member?.membership_id || !Number.isInteger(limit) || limit < 0 || limit > 1_000_000) {
      setWorkspaceCommercialStatus("Enter a monthly verified-action limit from 0 to 1,000,000."); return;
    }
    if (!window.confirm(`Set ${workspaceCommercialDepartment.replaceAll("_", " ")} to ${limit} verified actions per month${workspaceCommercialOverage ? " and explicitly allow overage" : " with overage blocked"}?`)) return;
    try {
      const { controlWorkspaceCommercialService } = await import("@/lib/pilot/pairing");
      const result = await controlWorkspaceCommercialService(connection, String(member.membership_id), {
        operation: "set_capacity", department: workspaceCommercialDepartment,
        monthly_action_limit: limit, overage_allowed: workspaceCommercialOverage,
        overage_approval_ref: workspaceCommercialOverage ? `pilot-mobile-overage:${crypto.randomUUID()}` : "",
      });
      setWorkspaceCommercial((result.dashboard as Record<string, unknown> | undefined) || null);
      setWorkspaceCommercialStatus(`Capacity updated; overage is ${workspaceCommercialOverage ? "explicitly allowed" : "blocked"}.`);
    } catch (error) { setWorkspaceCommercialStatus(error instanceof Error ? error.message : "Pilot could not update capacity."); }
  };

  const updateTask = async (item: Record<string, unknown>, event: "accepted" | "declined" | "read" | "corrected" | "cancelled" | "snoozed" | "completed") => {
    if (!connection) return;
    let details: { title?: string; until?: string } = {};
    if (event === "corrected") {
      const title = window.prompt("Correct this task", String(item.title || ""))?.trim();
      if (!title) return;
      details = { title };
    }
    if (event === "snoozed") details = { until: new Date(Date.now() + 60 * 60 * 1000).toISOString() };
    setNotice("Sending this signed task update…");
    try {
      const { actOnPilotTask, readPilotInbox } = await import("@/lib/pilot/pairing");
      await actOnPilotTask(connection, String(item.action_id), event, details);
      setLiveInbox(await readPilotInbox(connection));
      setNotice(event === "snoozed" ? "Task snoozed for one hour." : `Task ${event}.`);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Pilot could not update that task.");
    }
  };

  const searchInbox = async (event?: FormEvent) => {
    event?.preventDefault();
    if (!connection) return;
    setNotice("Searching this private Inbox…");
    try {
      const { searchPilotInbox } = await import("@/lib/pilot/pairing");
      const result = await searchPilotInbox(connection, inboxQuery, inboxKind);
      setInboxResults((result.results as Array<Record<string, unknown>> | undefined) || []);
      setNotice(`${Number(result.count || 0)} private Inbox result${Number(result.count || 0) === 1 ? "" : "s"}.`);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Pilot could not search that private Inbox.");
    }
  };

  const sendTrustedHandoff = async (event: FormEvent) => {
    event.preventDefault();
    if (!connection) return;
    const relationships = (trustedHandoffs?.relationships as Array<Record<string, unknown>> | undefined) || [];
    const relationship = relationships.find((item) => item.relationship_id === handoffRelationship);
    const recipientPersonaId = String(relationship?.peer_persona_id || "");
    const contact = personalContacts.find((item) => item.pilot_persona_id === recipientPersonaId);
    const recipientMotherId = String(contact?.pilot_mother_id || "");
    if (!relationship || !recipientMotherId) {
      setNotice("Choose a trusted Pilot contact whose mother-brain route is saved in Contacts.");
      return;
    }
    setNotice(handoffType === "task" ? "Preparing the exact task for a second approval…" : "Encrypting this handoff for the recipient's mother brain…");
    try {
      const { sendTrustedPilotHandoff, readPilotInbox } = await import("@/lib/pilot/pairing");
      const sent = await sendTrustedPilotHandoff(connection, {
        handoffType, relationshipId: handoffRelationship, recipientPersonaId, recipientMotherId,
        title: handoffTitle, body: handoffDetail, detail: handoffDetail, dueAt: handoffDue,
        file: handoffFile || undefined, momentId: handoffMomentId,
        contextHash: handoffContextHash, providerUrl: handoffProviderUrl,
      });
      if (sent.transport_state === "awaiting_private_approval") {
        setPendingTrustedTask({ ...(sent.result as Record<string, unknown>), relationship_id: handoffRelationship, recipient_persona_id: recipientPersonaId });
        setNotice("Task prepared. Review it below and approve before Pilot creates an encrypted packet.");
      } else {
        setNotice("Encrypted packet prepared for the trusted recipient. Human opening or acceptance is not yet claimed.");
        setHandoffTitle(""); setHandoffDetail(""); setHandoffDue(""); setHandoffFile(null);
      }
      setLiveInbox(await readPilotInbox(connection));
    } catch (error) { setNotice(error instanceof Error ? error.message : "Pilot could not prepare that trusted handoff."); }
  };

  const approveTrustedTask = async () => {
    if (!connection || !pendingTrustedTask) return;
    setNotice("Applying your second signed approval to this exact task…");
    try {
      const { approveTrustedPilotTask, readPilotInbox } = await import("@/lib/pilot/pairing");
      await approveTrustedPilotTask(connection, {
        relationshipId: String(pendingTrustedTask.relationship_id || ""),
        recipientPersonaId: String(pendingTrustedTask.recipient_persona_id || ""),
        actionId: String(pendingTrustedTask.action_id || ""),
        scopeHash: String(pendingTrustedTask.scope_hash || ""),
      });
      setPendingTrustedTask(null); setHandoffTitle(""); setHandoffDetail("");
      setLiveInbox(await readPilotInbox(connection));
      setNotice("Task encrypted for the recipient mother. Recipient acceptance is still required.");
    } catch (error) { setNotice(error instanceof Error ? error.message : "Pilot could not approve that task."); }
  };

  const downloadAttachment = async (attachment: Record<string, unknown>) => {
    if (!connection) return;
    setNotice("Opening this encrypted attachment…");
    try {
      const { downloadPilotAttachment } = await import("@/lib/pilot/pairing");
      const file = await downloadPilotAttachment(connection, String(attachment.attachment_id || ""));
      const bytes = file.bytes.buffer.slice(file.bytes.byteOffset, file.bytes.byteOffset + file.bytes.byteLength) as ArrayBuffer;
      const url = URL.createObjectURL(new Blob([bytes], { type: file.mediaType }));
      const link = document.createElement("a");
      link.href = url;
      link.download = file.filename;
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1_000);
      setNotice("Attachment verified and opened from your mother brain.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Pilot could not open that attachment.");
    }
  };

  const peerForItem = (item: Record<string, unknown>) => {
    const personaId = String(connection?.certificate.persona_id || "");
    const sentByMe = String(item.sender_persona_id || "") === personaId;
    return sentByMe
      ? { recipientPersonaId: String(item.recipient_persona_id || ""), recipientMotherId: String(item.recipient_mother_id || "") }
      : { recipientPersonaId: String(item.sender_persona_id || ""), recipientMotherId: String(item.sender_mother_id || "") };
  };

  const stopVoiceReply = () => {
    recordingHeldRef.current = false;
    if (recorderRef.current?.state === "recording") recorderRef.current.stop();
  };

  const startVoiceReply = async (item: Record<string, unknown>) => {
    if (!connection || recorderRef.current) return;
    recordingHeldRef.current = true;
    const peer = peerForItem(item);
    if (!peer.recipientPersonaId || !peer.recipientMotherId) {
      setNotice("Pilot cannot verify the recipient route for this older item.");
      return;
    }
    setRecordingFor(String(item.message_id || item.action_id || "reply"));
    setNotice("Securing the push-to-talk channel…");
    try {
      const { controlPilotPttFloor, sendPilotVoiceNote, readPilotInbox } = await import("@/lib/pilot/pairing");
      const floor = await controlPilotPttFloor(connection, { operation: "acquire", ...peer });
      const floorId = String(floor.floor_id || "");
      recordingPeerRef.current = { ...peer, floorId };
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
      recordingStreamRef.current = stream;
      const mediaType = MediaRecorder.isTypeSupported("audio/mp4") ? "audio/mp4" : "audio/webm";
      const recorder = new MediaRecorder(stream, { mimeType: mediaType });
      recorderRef.current = recorder;
      recordingChunksRef.current = [];
      recordingStartedRef.current = Date.now();
      recorder.ondataavailable = (event) => { if (event.data.size) recordingChunksRef.current.push(event.data); };
      recorder.onstop = async () => {
        const activePeer = recordingPeerRef.current;
        const durationMs = Date.now() - recordingStartedRef.current;
        const blob = new Blob(recordingChunksRef.current, { type: recorder.mimeType });
        recordingStreamRef.current?.getTracks().forEach((track) => track.stop());
        if (floorRenewalRef.current) clearInterval(floorRenewalRef.current);
        recorderRef.current = null;
        recordingStreamRef.current = null;
        recordingChunksRef.current = [];
        recordingPeerRef.current = null;
        setRecordingFor(null);
        try {
          if (!activePeer || !blob.size) throw new Error("No voice was recorded");
          await sendPilotVoiceNote(connection, { ...activePeer, blob, durationMs });
          setLiveInbox(await readPilotInbox(connection));
          setNotice("Encrypted voice note sent from this verified phone.");
        } catch (error) {
          if (activePeer) await controlPilotPttFloor(connection, { operation: "release", floorId: activePeer.floorId }).catch(() => undefined);
          setNotice(error instanceof Error ? error.message : "Pilot could not send that voice note.");
        }
      };
      recorder.start(250);
      floorRenewalRef.current = setInterval(() => {
        const active = recordingPeerRef.current;
        if (active) void controlPilotPttFloor(connection, { operation: "renew", floorId: active.floorId }).catch(() => stopVoiceReply());
      }, 10_000);
      setNotice("Speaking privately — release to send.");
      if (!recordingHeldRef.current) recorder.stop();
    } catch (error) {
      const active = recordingPeerRef.current;
      if (active) {
        const { controlPilotPttFloor } = await import("@/lib/pilot/pairing");
        await controlPilotPttFloor(connection, { operation: "release", floorId: active.floorId }).catch(() => undefined);
      }
      recordingStreamRef.current?.getTracks().forEach((track) => track.stop());
      recorderRef.current = null;
      recordingPeerRef.current = null;
      setRecordingFor(null);
      setNotice(error instanceof Error ? error.message : "Pilot could not access this phone's microphone.");
    }
  };

  const playVoiceNote = async (attachment: Record<string, unknown>) => {
    if (!connection) return;
    try {
      const { downloadPilotAttachment } = await import("@/lib/pilot/pairing");
      const file = await downloadPilotAttachment(connection, String(attachment.attachment_id || ""));
      const bytes = file.bytes.buffer.slice(file.bytes.byteOffset, file.bytes.byteOffset + file.bytes.byteLength) as ArrayBuffer;
      const url = URL.createObjectURL(new Blob([bytes], { type: file.mediaType }));
      const audio = new Audio(url);
      audio.onended = () => URL.revokeObjectURL(url);
      audio.onerror = () => URL.revokeObjectURL(url);
      await audio.play();
      setNotice("Playing a verified private voice note.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Pilot could not play that voice note.");
    }
  };

  const refreshPersonal = async () => {
    if (!connection) return;
    const { readPersonalPilot } = await import("@/lib/pilot/pairing");
    setPersonalPilot(await readPersonalPilot(connection));
  };

  const createReminder = async (event: FormEvent) => {
    event.preventDefault();
    if (!connection || !reminderTask) return;
    const locationPermissions = (personalPilot?.location_reminder_permissions as Array<Record<string, unknown>> | undefined) || [];
    const needsLocation = ["arrival", "departure", "journey"].includes(reminderTrigger);
    if (needsLocation && locationPermissions.length === 0) {
      setNotice("Grant location-reminder permission from this phone before using arrival, departure or journey reminders.");
      return;
    }
    try {
      const { createPersonalReminder } = await import("@/lib/pilot/pairing");
      await createPersonalReminder(connection, {
        taskId: reminderTask,
        trigger: reminderTrigger,
        at: reminderAt ? new Date(reminderAt).toISOString() : undefined,
        locationLabel: reminderLocation,
        repetition: ["time", "closing_time"].includes(reminderTrigger) ? reminderRepeat : "none",
        locationPermissionId: needsLocation ? String(locationPermissions[0]?.consent_id || "") : undefined,
      });
      await refreshPersonal();
      setNotice("Reminder scheduled privately on your mother brain.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Pilot could not schedule that reminder.");
    }
  };

  const updateReminder = async (reminderId: string, operation: "snooze" | "complete" | "cancel") => {
    if (!connection) return;
    try {
      const { updatePersonalReminder } = await import("@/lib/pilot/pairing");
      const until = operation === "snooze" ? new Date(Date.now() + 60 * 60 * 1000).toISOString() : undefined;
      await updatePersonalReminder(connection, reminderId, operation, until);
      await refreshPersonal();
      setNotice(operation === "snooze" ? "Reminder snoozed for one hour." : operation === "complete" ? "Reminder completed." : "Reminder cancelled.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Pilot could not update that reminder.");
    }
  };

  const refreshCalendar = async () => {
    if (!connection) return;
    const { readPersonalCalendar } = await import("@/lib/pilot/pairing");
    setPersonalCalendar(await readPersonalCalendar(connection));
  };

  const checkAvailability = async (event: FormEvent) => {
    event.preventDefault();
    if (!connection || !availabilityStart || !availabilityEnd) return;
    setCalendarStatus("Checking availability privately…");
    try {
      const { readPersonalAvailability } = await import("@/lib/pilot/pairing");
      const result = await readPersonalAvailability(connection, {
        start: new Date(availabilityStart).toISOString(), end: new Date(availabilityEnd).toISOString(), slotMinutes: 30,
      });
      setAvailability((result.free_slots as Array<Record<string, unknown>> | undefined) || []);
      setCalendarStatus("Availability checked without exposing event titles.");
    } catch (error) { setCalendarStatus(error instanceof Error ? error.message : "Pilot could not check availability."); }
  };

  const prepareCalendar = async (event: FormEvent) => {
    event.preventDefault();
    if (!connection) return;
    setCalendarStatus("Preparing the exact calendar change…");
    try {
      const { preparePersonalCalendarChange } = await import("@/lib/pilot/pairing");
      await preparePersonalCalendarChange(connection, {
        action: calendarAction, title: calendarTitle,
        start: calendarAction === "cancel" ? "" : new Date(calendarStart).toISOString(),
        end: calendarAction === "cancel" ? "" : new Date(calendarEnd).toISOString(),
        providerEventId: calendarEventId, location: calendarLocation,
        travelMinutes: Number(calendarTravel || 0), reminderMinutes: Number(calendarReminder || 0),
        attendees: calendarAttendees.split(",").map((item) => item.trim()).filter(Boolean),
        notifyAttendees: calendarNotify,
      });
      await refreshCalendar();
      setCalendarStatus("Prepared only. Review every detail below before approval.");
    } catch (error) { setCalendarStatus(error instanceof Error ? error.message : "Pilot could not prepare that calendar change."); }
  };

  const decideCalendar = async (proposal: Record<string, unknown>, approved: boolean) => {
    if (!connection) return;
    const conflicts = Number(proposal.conflict_count || 0);
    const acceptConflicts = conflicts > 0 && approved
      ? window.confirm(`Pilot detected ${conflicts} private calendar conflict${conflicts === 1 ? "" : "s"}. Approve anyway?`)
      : false;
    if (conflicts > 0 && approved && !acceptConflicts) return;
    try {
      const { decidePersonalCalendarChange } = await import("@/lib/pilot/pairing");
      await decidePersonalCalendarChange(connection, String(proposal.proposal_id), String(proposal.scope_hash), approved, acceptConflicts);
      await refreshCalendar();
      setCalendarStatus(approved ? "Exact change approved. Nothing is sent until you press Execute." : "Calendar change rejected.");
    } catch (error) { setCalendarStatus(error instanceof Error ? error.message : "Pilot could not record that decision."); }
  };

  const executeCalendar = async (proposal: Record<string, unknown>) => {
    if (!connection) return;
    setCalendarStatus("Sending the approved change to your calendar provider…");
    try {
      const { executePersonalCalendarChange } = await import("@/lib/pilot/pairing");
      const receipt = await executePersonalCalendarChange(connection, String(proposal.proposal_id), String(proposal.scope_hash));
      await refreshCalendar();
      setCalendarStatus(Boolean(receipt.verified) ? "Calendar provider verified the change." : "Pilot could not verify the provider result.");
    } catch (error) { setCalendarStatus(error instanceof Error ? error.message : "Pilot could not execute that calendar change."); }
  };

  const refreshContacts = async (query = contactQuery) => {
    if (!connection) return;
    const { readPersonalContacts } = await import("@/lib/pilot/pairing");
    const result = await readPersonalContacts(connection, query);
    setPersonalContacts((result.contacts as Array<Record<string, unknown>> | undefined) || []);
  };

  const clearContactForm = () => {
    setContactId(""); setContactName(""); setContactEmail(""); setContactWhatsapp("");
    setContactPilotPersona(""); setContactPilotMother(""); setContactPreferredRoute("");
  };

  const editContact = (contact: Record<string, unknown>) => {
    setContactId(String(contact.contact_id || "")); setContactName(String(contact.display_name || ""));
    setContactEmail(String(contact.email || "")); setContactWhatsapp(String(contact.whatsapp || ""));
    setContactPilotPersona(String(contact.pilot_persona_id || "")); setContactPilotMother(String(contact.pilot_mother_id || ""));
    setContactPreferredRoute(String(contact.preferred_route || "") as typeof contactPreferredRoute);
    setContactStatus(`Editing ${String(contact.display_name || "this contact")}. Nothing changes until you save.`);
  };

  const saveContact = async (event: FormEvent) => {
    event.preventDefault();
    if (!connection) return;
    setContactStatus("Saving this contact privately…");
    try {
      const { savePersonalContact } = await import("@/lib/pilot/pairing");
      await savePersonalContact(connection, {
        contactId, displayName: contactName, email: contactEmail, whatsapp: contactWhatsapp,
        pilotPersonaId: contactPilotPersona, pilotMotherId: contactPilotMother,
        preferredRoute: contactPreferredRoute,
      });
      clearContactForm(); await refreshContacts(""); setContactQuery("");
      setContactStatus("Contact saved on your mother brain. No message was sent.");
    } catch (error) { setContactStatus(error instanceof Error ? error.message : "Pilot could not save that contact."); }
  };

  const removeContact = async (contact: Record<string, unknown>) => {
    if (!connection || !window.confirm(`Remove ${String(contact.display_name || "this contact")} from your private contacts?`)) return;
    try {
      const { removePersonalContact } = await import("@/lib/pilot/pairing");
      await removePersonalContact(connection, String(contact.contact_id || ""));
      await refreshContacts(); setContactResolution(null);
      setContactStatus("Contact removed. Historical receipts and tasks were preserved.");
    } catch (error) { setContactStatus(error instanceof Error ? error.message : "Pilot could not remove that contact."); }
  };

  const resolveContact = async (event: FormEvent) => {
    event.preventDefault();
    if (!connection || !contactQuery.trim()) return;
    setContactStatus("Resolving that name inside your private contacts…");
    try {
      const { resolvePersonalContact } = await import("@/lib/pilot/pairing");
      const result = await resolvePersonalContact(connection, contactQuery);
      setContactResolution(result);
      setContactStatus(result.status === "resolved" ? "One exact recipient is ready for private confirmation." : result.status === "ambiguous" ? "More than one contact sounds like that. Choose privately below." : "No matching private contact was found.");
    } catch (error) { setContactStatus(error instanceof Error ? error.message : "Pilot could not resolve that contact."); }
  };

  const importPhoneContact = async () => {
    type ContactPicker = { select: (properties: string[], options: { multiple: boolean }) => Promise<Array<{ name?: string[]; email?: string[]; tel?: string[] }>> };
    const picker = (navigator as Navigator & { contacts?: ContactPicker }).contacts;
    if (!picker) { setContactStatus("This browser does not offer private contact selection. Enter the contact below instead."); return; }
    try {
      const chosen = (await picker.select(["name", "email", "tel"], { multiple: false }))[0];
      if (!chosen) return;
      setContactName(chosen.name?.[0] || ""); setContactEmail(chosen.email?.[0] || "");
      setContactWhatsapp(chosen.tel?.[0] || ""); setContactPreferredRoute(chosen.email?.[0] ? "email" : chosen.tel?.[0] ? "whatsapp" : "");
      setContactStatus("Contact copied into the form. Review it before saving to Pilot.");
    } catch { setContactStatus("Phone contact selection was cancelled. Nothing was imported."); }
  };

  const refreshCommunication = async () => {
    if (!connection) return;
    const { readPersonalCommunication } = await import("@/lib/pilot/pairing");
    setPersonalCommunication(await readPersonalCommunication(connection));
  };

  const prepareCommunication = async (event: FormEvent) => {
    event.preventDefault();
    if (!connection) return;
    setCommunicationStatus("Preparing the exact recipient and content locally…");
    try {
      const { preparePersonalCommunication } = await import("@/lib/pilot/pairing");
      await preparePersonalCommunication(connection, {
        contactId: communicationContact, channel: communicationChannel,
        subject: communicationSubject, body: communicationBody,
      });
      setCommunicationSubject(""); setCommunicationBody("");
      await refreshCommunication();
      setCommunicationStatus("Draft prepared only. Review the exact recipient and content before approval.");
    } catch (error) { setCommunicationStatus(error instanceof Error ? error.message : "Pilot could not prepare that communication."); }
  };

  const decideCommunication = async (item: Record<string, unknown>, approved: boolean) => {
    if (!connection) return;
    try {
      const { decidePersonalCommunication } = await import("@/lib/pilot/pairing");
      await decidePersonalCommunication(connection, String(item.draft_id), String(item.content_hash), approved);
      await refreshCommunication();
      setCommunicationStatus(approved ? "Exact message approved. It has not been sent; press Send approved message to continue." : "Draft rejected. Nothing was sent.");
    } catch (error) { setCommunicationStatus(error instanceof Error ? error.message : "Pilot could not record that decision."); }
  };

  const executeCommunication = async (item: Record<string, unknown>) => {
    if (!connection) return;
    setCommunicationStatus("Asking the authorized provider to deliver the approved message…");
    try {
      const { executePersonalCommunication } = await import("@/lib/pilot/pairing");
      const receipt = await executePersonalCommunication(connection, String(item.draft_id), String(item.content_hash));
      await refreshCommunication();
      setCommunicationStatus(Boolean(receipt.verified) ? "Delivery verified by the provider. The receipt is shown below." : "Pilot did not receive a verified delivery receipt.");
    } catch (error) { setCommunicationStatus(error instanceof Error ? error.message : "Pilot could not verify delivery."); }
  };

  const convertCommunication = async (messageId: string, target: "task" | "reminder" | "calendar") => {
    if (!connection) return;
    try {
      const { convertReceivedCommunication } = await import("@/lib/pilot/pairing");
      await convertReceivedCommunication(connection, messageId, target);
      await refreshPersonal();
      setCommunicationStatus(target === "task" ? "A private task was created from the received summary." : target === "reminder" ? "A reminder proposal is ready for a private time." : "A calendar proposal was prepared and still needs private dates.");
    } catch (error) { setCommunicationStatus(error instanceof Error ? error.message : "Pilot could not prepare that follow-through."); }
  };

  const createInvite = async (draftId: string) => {
    if (!connection) return;
    try {
      const { createCommunicationInvitation } = await import("@/lib/pilot/pairing");
      const invitation = await createCommunicationInvitation(connection, draftId);
      const shared = typeof navigator.share === "function";
      if (shared) await navigator.share({ title: "Pilot request", text: String(invitation.request_summary || "A Pilot request is waiting for you."), url: String(invitation.url || "") });
      else await navigator.clipboard.writeText(String(invitation.url || ""));
      await refreshCommunication();
      setCommunicationStatus(shared ? "The exact request invitation is ready to share." : "Invitation link copied. It reveals only this exact request.");
    } catch (error) { setCommunicationStatus(error instanceof Error ? error.message : "Pilot could not create that invitation."); }
  };

  const protectContact = async (contactId: string, operation: "block" | "report") => {
    if (!connection) return;
    try {
      const { protectCommunicationContact } = await import("@/lib/pilot/pairing");
      await protectCommunicationContact(connection, contactId, operation);
      await refreshCommunication();
      setCommunicationStatus(operation === "block" ? "Contact blocked for this private identity." : "Safety report recorded locally; no provider report was claimed.");
    } catch (error) { setCommunicationStatus(error instanceof Error ? error.message : "Pilot could not apply that protection."); }
  };

  const scheduleMessageFollowUp = async (draftId: string) => {
    if (!connection || !communicationFollowUp) return;
    try {
      const { scheduleCommunicationFollowUp } = await import("@/lib/pilot/pairing");
      await scheduleCommunicationFollowUp(connection, draftId, new Date(communicationFollowUp).toISOString());
      await refreshCommunication(); setCommunicationFollowUp("");
      setCommunicationStatus("Follow-up scheduled only if no verified reply is received.");
    } catch (error) { setCommunicationStatus(error instanceof Error ? error.message : "Pilot could not schedule that follow-up."); }
  };

  const prepareCall = async () => {
    if (!connection || !communicationContact) return;
    try {
      const { prepareCommunicationCall } = await import("@/lib/pilot/pairing");
      setPreparedCall(await prepareCommunicationCall(connection, communicationContact));
      setCommunicationStatus("Call prepared. Only your explicit phone tap can place it.");
    } catch (error) { setCommunicationStatus(error instanceof Error ? error.message : "Pilot could not prepare that call."); }
  };

  const refreshServices = async () => {
    if (!connection) return;
    const { readPersonalServices } = await import("@/lib/pilot/pairing");
    setPersonalServices(await readPersonalServices(connection));
  };

  const prepareServiceAction = async (event: FormEvent) => {
    event.preventDefault();
    if (!connection) return;
    const parameters: Record<string, unknown> = serviceKind === "shopping"
      ? { item: servicePrimary.trim(), quantity: Number(serviceQuantity), requirements: serviceSecondary.trim() }
      : serviceKind === "booking"
        ? { what: servicePrimary.trim(), date: serviceSecondary }
        : serviceKind === "maps"
          ? { destination: servicePrimary.trim(), preference: serviceSecondary.trim() }
          : { request: servicePrimary.trim(), context: serviceSecondary.trim() };
    setServiceStatus("Preparing the exact action. Nothing will be purchased, booked or changed yet…");
    try {
      const { preparePersonalServiceAction } = await import("@/lib/pilot/pairing");
      await preparePersonalServiceAction(connection, serviceKind, serviceKind === "shopping" ? "prepare_purchase" : serviceKind === "booking" ? "prepare_booking" : serviceKind === "maps" ? "prepare_route" : "prepare_playback", parameters);
      setServicePrimary(""); setServiceSecondary(""); setServiceQuantity("1");
      await refreshServices();
      setServiceStatus("Proposal prepared only. Review its exact details below before approval.");
    } catch (error) { setServiceStatus(error instanceof Error ? error.message : "Pilot could not prepare that service action."); }
  };

  const completeServiceDetails = async (proposal: Record<string, unknown>) => {
    if (!connection) return;
    const missing = (proposal.missing_fields as string[] | undefined) || [];
    const details = Object.fromEntries(missing.map((field) => [field, serviceDetails[`${String(proposal.proposal_id)}:${field}`] || ""]));
    try {
      const { updatePersonalServiceDetails } = await import("@/lib/pilot/pairing");
      await updatePersonalServiceDetails(connection, String(proposal.proposal_id), details);
      await refreshServices();
      setServiceStatus("Private details saved. Review the complete proposal before approval.");
    } catch (error) { setServiceStatus(error instanceof Error ? error.message : "Pilot could not save those details."); }
  };

  const decideServiceAction = async (proposal: Record<string, unknown>, approved: boolean) => {
    if (!connection) return;
    try {
      const { decidePersonalServiceAction } = await import("@/lib/pilot/pairing");
      await decidePersonalServiceAction(connection, String(proposal.proposal_id), String(proposal.parameters_hash), approved);
      await refreshServices();
      setServiceStatus(approved ? "Exact action approved. Nothing has executed; press Execute to continue." : "Proposal rejected. Nothing changed.");
    } catch (error) { setServiceStatus(error instanceof Error ? error.message : "Pilot could not record that decision."); }
  };

  const executeServiceAction = async (proposal: Record<string, unknown>) => {
    if (!connection) return;
    setServiceStatus("Sending the approved action through your authorized service…");
    try {
      const { executePersonalServiceAction } = await import("@/lib/pilot/pairing");
      const receipt = await executePersonalServiceAction(connection, String(proposal.proposal_id), String(proposal.parameters_hash));
      await refreshServices();
      setServiceStatus(Boolean(receipt.verified) ? "The provider verified the result. A receipt is shown below." : "Pilot did not receive a verified result.");
    } catch (error) { setServiceStatus(error instanceof Error ? error.message : "The service is not connected or could not verify the result."); }
  };

  const refreshLibrary = async () => {
    if (!connection) return;
    const { readPersonalLibrary } = await import("@/lib/pilot/pairing");
    setPersonalLibrary(await readPersonalLibrary(connection));
  };

  const claimLibraryItem = async (saveId: string) => {
    if (!connection) return;
    setLibraryStatus("Saving this shared-screen item to your private library…");
    try {
      const { claimPersonalLibraryItem } = await import("@/lib/pilot/pairing");
      await claimPersonalLibraryItem(connection, saveId);
      await refreshLibrary();
      setLibraryStatus("Saved privately to this person. No external action was taken.");
    } catch (error) { setLibraryStatus(error instanceof Error ? error.message : "Pilot could not save that item."); }
  };

  const continueLibraryItem = async (saveId: string, action: "research" | "shortlist" | "task" | "shopping" | "trip" | "playlist" | "learning") => {
    if (!connection) return;
    setLibraryStatus(action === "research" ? "Researching with AION and bounded evidence…" : "Preparing a separate private continuation…");
    try {
      const { continuePersonalLibraryItem } = await import("@/lib/pilot/pairing");
      await continuePersonalLibraryItem(connection, saveId, action);
      await refreshLibrary();
      setLibraryStatus(["shopping", "trip", "playlist"].includes(action)
        ? "A separate proposal is ready. It still requires private review and approval."
        : "Private continuation prepared. Nothing was sent, bought or booked.");
    } catch (error) { setLibraryStatus(error instanceof Error ? error.message : "Pilot could not continue that item."); }
  };

  const removeLibraryItem = async (item: Record<string, unknown>) => {
    if (!connection || !window.confirm(`Remove ${String(item.title || "this item")} from your private library?`)) return;
    try {
      const { deletePersonalLibraryItem } = await import("@/lib/pilot/pairing");
      await deletePersonalLibraryItem(connection, String(item.save_id || ""));
      await refreshLibrary();
      setLibraryStatus("Saved item removed. Existing audit and approval records were preserved.");
    } catch (error) { setLibraryStatus(error instanceof Error ? error.message : "Pilot could not remove that item."); }
  };

  const refreshDeviceMesh = async () => {
    if (!connection) return;
    const { readPersonalDeviceMesh } = await import("@/lib/pilot/pairing");
    setPersonalDevices(await readPersonalDeviceMesh(connection));
  };

  const discoverDevices = async () => {
    if (!connection) return;
    setDeviceStatus("Listening briefly for local device advertisements…");
    try {
      const { discoverPersonalDevices } = await import("@/lib/pilot/pairing");
      setPersonalDevices(await discoverPersonalDevices(connection));
      setDeviceStatus("Discovery complete. Newly seen devices remain observed only—not enrolled or controllable.");
    } catch (error) { setDeviceStatus(error instanceof Error ? error.message : "Pilot could not complete safe discovery."); }
  };

  const changeTVSession = async (operation: "acquire" | "release") => {
    if (!connection) return;
    setDeviceStatus(operation === "acquire" ? "Proving this trusted phone and acquiring the shared screen…" : "Locking the shared television workspace…");
    try {
      const { changePersonalTVSession } = await import("@/lib/pilot/pairing");
      await changePersonalTVSession(connection, operation);
      await refreshDeviceMesh();
      setDeviceStatus(operation === "acquire" ? "You control the shared screen for five minutes of inactivity." : "Television workspace locked. Private tiles are hidden.");
    } catch (error) { setDeviceStatus(error instanceof Error ? error.message : "Pilot could not change the television session."); }
  };

  const sendTVCommand = async (command: string) => {
    if (!connection) return;
    setDeviceStatus(command === "observe" ? "Reading the paired television state…" : `Sending ${command.replaceAll("_", " ")} through the governed TV adapter…`);
    try {
      const { controlPersonalTV } = await import("@/lib/pilot/pairing");
      const result = await controlPersonalTV(connection, command);
      setDeviceLastResult(result);
      await refreshDeviceMesh();
      const receipt = (result.receipt as Record<string, unknown> | undefined) || {};
      setDeviceStatus(Boolean(receipt.verified) ? String(result.spoken_response || "Television verified the result.") : "Command delivered; use Refresh TV state or Visual Observer for outcome verification.");
    } catch (error) { setDeviceStatus(error instanceof Error ? error.message : "Pilot could not control the television."); }
  };

  const presentOnTV = async (args: {
    operation: "present" | "dismiss";
    contentKind?: "document" | "dashboard" | "briefing";
    contentId?: string;
    title?: string;
    authorityDomain?: "personal" | "workspace" | "boardroom";
    membershipId?: string;
  }) => {
    if (!connection) return;
    setDeviceStatus(args.operation === "dismiss" ? "Closing private television presentation…" : "Presenting this exact authorized view on the television…");
    try {
      const { controlPersonalTVPresentation } = await import("@/lib/pilot/pairing");
      await controlPersonalTVPresentation(connection, args);
      setDeviceStatus(args.operation === "dismiss" ? "Private television presentation closed." : "Presented on the television. It will close automatically when authority expires.");
    } catch (error) { setDeviceStatus(error instanceof Error ? error.message : "Pilot could not change the private television presentation."); }
  };

  const sendIotPreset = async (preset: string) => {
    if (!connection) return;
    if (!window.confirm(`Send the learned ${preset.replaceAll("_", " ")} infrared preset? Infrared cannot prove the appliance changed state.`)) return;
    setDeviceStatus(`Sending ${preset.replaceAll("_", " ")} through the local infrared gateway…`);
    try {
      const { controlPersonalIotPreset } = await import("@/lib/pilot/pairing");
      const result = await controlPersonalIotPreset(connection, preset);
      setDeviceLastResult(result);
      await refreshDeviceMesh();
      setDeviceStatus(Boolean(result.transport_delivered) ? "Infrared transport delivered. Check the appliance because its state is not independently verified." : "The infrared gateway did not verify delivery.");
    } catch (error) { setDeviceStatus(error instanceof Error ? error.message : "Pilot could not send that IoT preset."); }
  };

  const refreshExperiences = async () => {
    if (!connection) return;
    const { readPersonalExperiences } = await import("@/lib/pilot/pairing");
    setPersonalExperiences(await readPersonalExperiences(connection));
  };

  const runExperience = async (
    operation:
      | "learning_start" | "learning_answer" | "learning_next" | "learning_repeat"
      | "games_open" | "games_continue"
      | "entertainment_continue_prepare" | "entertainment_continue_confirm" | "entertainment_continue_execute"
      | "entertainment_remember" | "entertainment_watchlist_add",
    args: Record<string, unknown> = {},
  ) => {
    if (!connection) return;
    setExperienceStatus("Pilot is applying that action through the existing governed experience…");
    try {
      const { controlPersonalExperience } = await import("@/lib/pilot/pairing");
      const result = await controlPersonalExperience(connection, operation, args);
      await refreshExperiences();
      setExperienceStatus(String(result.spoken_response || "Experience updated."));
    } catch (error) {
      setExperienceStatus(error instanceof Error ? error.message : "Pilot could not complete that experience action.");
    }
  };

  const refreshMemory = async (targetPersonaId = memoryTarget) => {
    if (!connection) return;
    const { readPersonalMemory } = await import("@/lib/pilot/pairing");
    setPersonalMemory(await readPersonalMemory(connection, targetPersonaId || undefined));
  };

  const addMemory = async (event: FormEvent) => {
    event.preventDefault();
    if (!connection || !memorySummary.trim()) return;
    if (memoryScope === "household_shared" && !window.confirm("Share this memory with household experiences? You can change it back to private later.")) return;
    setMemoryStatus("Saving this explicit memory to your mother brain…");
    try {
      const { createPersonalMemory } = await import("@/lib/pilot/pairing");
      await createPersonalMemory(connection, { targetPersonaId: memoryTarget || undefined, kind: memoryKind, summary: memorySummary.trim(), scope: memoryScope });
      setMemorySummary("");
      await refreshMemory();
      setMemoryStatus("Memory saved with the scope you selected.");
    } catch (error) { setMemoryStatus(error instanceof Error ? error.message : "Pilot could not save that memory."); }
  };

  const correctMemory = async (item: Record<string, unknown>) => {
    if (!connection) return;
    const summary = window.prompt("Correct what Pilot should remember", String(item.summary || ""))?.trim();
    if (!summary) return;
    try {
      const { updatePersonalMemory } = await import("@/lib/pilot/pairing");
      await updatePersonalMemory(connection, { targetPersonaId: memoryTarget || undefined, memoryId: String(item.memory_id || ""), summary, scope: String(item.scope) === "household_shared" ? "household_shared" : "private" });
      await refreshMemory();
      setMemoryStatus("Memory corrected. The correction time and new integrity hash were recorded.");
    } catch (error) { setMemoryStatus(error instanceof Error ? error.message : "Pilot could not correct that memory."); }
  };

  const changeMemoryScope = async (item: Record<string, unknown>) => {
    if (!connection) return;
    const nextScope = String(item.scope) === "private" ? "household_shared" : "private";
    if (nextScope === "household_shared" && !window.confirm("Make this memory available to household-shared experiences?")) return;
    try {
      const { updatePersonalMemory } = await import("@/lib/pilot/pairing");
      await updatePersonalMemory(connection, { targetPersonaId: memoryTarget || undefined, memoryId: String(item.memory_id || ""), summary: String(item.summary || ""), scope: nextScope });
      await refreshMemory();
      setMemoryStatus(`Memory is now ${nextScope === "private" ? "private" : "household shared"}.`);
    } catch (error) { setMemoryStatus(error instanceof Error ? error.message : "Pilot could not change that scope."); }
  };

  const removeMemory = async (item: Record<string, unknown>) => {
    if (!connection || !window.confirm("Permanently delete this memory? This cannot be undone.")) return;
    try {
      const { deletePersonalMemory } = await import("@/lib/pilot/pairing");
      await deletePersonalMemory(connection, { targetPersonaId: memoryTarget || undefined, memoryId: String(item.memory_id || "") });
      await refreshMemory();
      setMemoryStatus("Memory permanently deleted. The audit operation remains, but its content is gone.");
    } catch (error) { setMemoryStatus(error instanceof Error ? error.message : "Pilot could not delete that memory."); }
  };

  const downloadMemoryExport = async () => {
    if (!connection) return;
    try {
      const { exportPersonalMemory } = await import("@/lib/pilot/pairing");
      const result = await exportPersonalMemory(connection, memoryTarget || undefined);
      const url = URL.createObjectURL(new Blob([JSON.stringify(result.export || {}, null, 2)], { type: "application/json" }));
      const link = document.createElement("a");
      link.href = url;
      link.download = `pilot-memory-${String(result.persona_id || "private")}.json`;
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1_000);
      setMemoryStatus("Private export downloaded. Recovery secrets and device public keys were excluded.");
    } catch (error) { setMemoryStatus(error instanceof Error ? error.message : "Pilot could not export that memory."); }
  };

  const refreshGuardian = async (targetPersonaId = guardianTarget) => {
    if (!connection) return;
    const { readPersonalGuardian } = await import("@/lib/pilot/pairing");
    setPersonalGuardian(await readPersonalGuardian(connection, targetPersonaId || undefined));
  };

  const saveGuardianContact = async () => {
    if (!connection || !guardianContact) return setGuardianStatus("Choose a trusted contact first.");
    if (!window.confirm("Give this contact separate Guardian interruption permission? This does not grant ordinary contact or account access.")) return;
    try {
      const { configurePersonalGuardian } = await import("@/lib/pilot/pairing");
      await configurePersonalGuardian(connection, { targetPersonaId: guardianTarget || undefined, contactId: guardianContact, channel: guardianChannel, shareLocation: guardianShareLocation, locationPermissionReceipt: guardianLocationReceipt });
      await refreshGuardian();
      setGuardianStatus("Separate Guardian contact permission saved.");
    } catch (error) { setGuardianStatus(error instanceof Error ? error.message : "Pilot could not save that emergency permission."); }
  };

  const runGuardian = async (operation: "request" | "confirm" | "cancel", incidentId = "") => {
    if (!connection) return;
    if (operation === "confirm" && !window.confirm("Send this urgent alert now to the exact authorized Guardian contacts?")) return;
    try {
      const { controlPersonalGuardian } = await import("@/lib/pilot/pairing");
      const result = await controlPersonalGuardian(connection, { targetPersonaId: guardianTarget || undefined, operation, incidentId, trigger: "Explicit help request from trusted phone" });
      await refreshGuardian();
      if (operation === "request") setGuardianStatus("No alert has been sent. Use the large confirmation below or cancel as a false alarm.");
      else if (Boolean(result.delivery_verified)) setGuardianStatus("A trusted-contact provider verified delivery. Pilot has not contacted an ambulance.");
      else if (Boolean(result.fallback_required)) setGuardianStatus("No provider verified delivery. Use the visible fallback and call local emergency services directly if needed.");
      else setGuardianStatus(operation === "cancel" ? "Guardian request cancelled as a false alarm." : "Guardian state updated.");
    } catch (error) { setGuardianStatus(error instanceof Error ? error.message : "Pilot could not complete that Guardian action."); }
  };

  const changeIntelligenceMode = async (nextMode: "native" | "gemini" | "boost") => {
    if (!connection) return;
    if (nextMode !== "native" && !window.confirm(`${nextMode === "gemini" ? "AION + Gemini" : "Pilot Boost"} may send only permitted context to a connected external provider. Continue?`)) return;
    try {
      const { configurePersonalIntelligence } = await import("@/lib/pilot/pairing");
      setPersonalIntelligence(await configurePersonalIntelligence(connection, nextMode));
      setNotice(`Maximum intelligence route set to ${nextMode === "native" ? "AION Native" : nextMode === "gemini" ? "AION + Gemini" : "Pilot Boost"}. Local capability remains first.`);
    } catch (error) { setNotice(error instanceof Error ? error.message : "Pilot could not change that intelligence route."); }
  };

  const openShortcut = (shortcut: string | null) => {
    setActiveNav("Pilot");
    setSelectedShortcut(shortcut);
    if (!shortcut) return setNotice(`${modeCopy[mode].label} overview restored`);
    setNotice(`${shortcut} is ready in ${space.display_name}`);
    if (shortcut === "Calendar" && connection) void refreshCalendar().catch((error) => setCalendarStatus(error instanceof Error ? error.message : "Reconnect this phone to add calendar permission."));
    if (shortcut === "Contacts" && connection) void refreshContacts("").catch((error) => setContactStatus(error instanceof Error ? error.message : "Reconnect this phone to add contact permission."));
    if (shortcut === "Messages" && connection) {
      void refreshContacts("").catch(() => undefined);
      void refreshCommunication().catch((error) => setCommunicationStatus(error instanceof Error ? error.message : "Reconnect this phone to add communication permission."));
    }
    if (shortcut === "Shopping" && connection) void refreshServices().catch((error) => setServiceStatus(error instanceof Error ? error.message : "Reconnect this phone to add private service permission."));
    if (shortcut === "Files" && connection) void refreshLibrary().catch((error) => setLibraryStatus(error instanceof Error ? error.message : "Reconnect this phone to add private library permission."));
    if (["Devices", "TV"].includes(shortcut) && connection) void refreshDeviceMesh().catch((error) => setDeviceStatus(error instanceof Error ? error.message : "Reconnect this phone to add device-mesh permission."));
    if (["Learning", "Games", "Entertainment"].includes(shortcut) && connection) void refreshExperiences().catch((error) => setExperienceStatus(error instanceof Error ? error.message : "Reconnect this phone to add experience permission."));
    if (shortcut === "Memory" && connection) void refreshMemory().catch((error) => setMemoryStatus(error instanceof Error ? error.message : "Reconnect this phone to add private memory permission."));
    if (shortcut === "Guardian" && connection) void refreshGuardian().catch((error) => setGuardianStatus(error instanceof Error ? error.message : "Reconnect this phone to add Guardian permission."));
  };

  return (
    <>
      <Head>
        <title>Pilot · Your intelligence</title>
        <meta name="theme-color" content="#f5f8ff" />
        <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
        <link rel="manifest" href="/pilot-mobile.webmanifest" />
      </Head>
      <div className={`${styles.viewport} ${styles[mode]}`}>
        <main className={styles.shell} aria-label="Pilot unified mobile app">
          <header className={styles.header}>
            <div className={styles.brandMark} aria-label="Pilot">
              <Plane size={25} strokeWidth={2.5} />
            </div>
            <div className={styles.brandCopy}>
              <strong>Pilot</strong>
              <span><i /> Connected to {lease.issuer_id.replaceAll("_", " ")}</span>
            </div>
            <button className={styles.iconButton} aria-label="Private notifications" onClick={() => setNotice("Protected details stay hidden until you unlock them") }>
              <Bell size={21} />
              <b>2</b>
            </button>
            <button className={styles.avatar} aria-label={`Signed in as ${fixture.person.display_name}`}>
              {fixture.person.display_name.split(" ").map((word) => word[0]).join("").slice(0, 2)}
            </button>
          </header>

          <section className={styles.identityStrip} aria-label="Active identity and authority">
            <div>
              <span>{fixture.person.display_name}</span>
              <strong>{space.display_name}</strong>
            </div>
            <div className={styles.authority}>
              <LockKeyhole size={14} /> {membership.role_id.replace("role_", "").replaceAll("_", " ")}
            </div>
          </section>

          <nav className={styles.modeSwitcher} aria-label="Choose your Pilot space">
            {fixture.surface_manifests.map((item) => (
              <button
                key={item.mode}
                className={mode === item.mode ? styles.modeActive : ""}
                onClick={() => { setMode(item.mode); setActiveNav("Pilot"); setSelectedShortcut(null); }}
                aria-pressed={mode === item.mode}
              >
                {item.mode === "personal" && <CircleUserRound size={17} />}
                {item.mode === "workspace" && <BriefcaseBusiness size={17} />}
                {item.mode === "boardroom" && <Building2 size={17} />}
                {modeCopy[item.mode].label}
              </button>
            ))}
          </nav>

          <section className={styles.hero}>
            <p>{modeCopy[mode].eyebrow}</p>
            <h1>{mode === "personal" ? "Good afternoon." : space.display_name}</h1>
            <span>{mode === "personal" ? "What can I take care of?" : "Review what matters, then ask Pilot to act."}</span>
          </section>

          {activeNav === "Pilot" && <section className={styles.contextTools} aria-label={`${modeCopy[mode].label} grouped tools`}>
            <label className={styles.contextPicker}>
              <span>Open a {modeCopy[mode].label.toLowerCase()} tool</span>
              <select value={selectedShortcut || ""} onChange={(event) => openShortcut(event.target.value || null)}>
                <option value="">Overview</option>
                {[...new Set(manifest.shortcuts.map((shortcut) => shortcutGroup(mode, shortcut)))].map((group) => (
                  <optgroup key={group} label={group}>
                    {manifest.shortcuts.filter((shortcut) => shortcutGroup(mode, shortcut) === group).map((shortcut) => <option key={shortcut} value={shortcut}>{shortcut}</option>)}
                  </optgroup>
                ))}
              </select>
            </label>
            <div className={styles.shortcuts} aria-label="Quick controls">
            {manifest.shortcuts.filter((shortcut) => mode !== "personal" || ["TV", "Tasks", "Calendar", "Devices"].includes(shortcut)).slice(0, 4).map((shortcut) => {
              const ShortcutIcon = iconForShortcut(shortcut);
              return (
                <button
                  key={shortcut}
                  className={selectedShortcut === shortcut ? styles.shortcutActive : ""}
                  onClick={() => openShortcut(shortcut)}
                >
                  <span><ShortcutIcon size={20} /></span>
                  {shortcut}
                </button>
              );
            })}
            </div>
          </section>}

          {activeNav === "Pilot" && mode === "personal" && connection && <section className={styles.intelligenceRail} aria-label="Pilot intelligence route">
            <div><Sparkles size={15} /><span><b>{String(personalIntelligence?.label || "AION Native")}</b> · local capability first</span></div>
            <div>{(["native", "gemini", "boost"] as const).map((item) => <button key={item} className={String(personalIntelligence?.mode || "native") === item ? styles.intelligenceActive : ""} onClick={() => void changeIntelligenceMode(item)}>{item === "native" ? "Native" : item === "gemini" ? "Gemini" : "Boost"}</button>)}</div>
          </section>}

          {activeNav === "Pilot" && mode === "boardroom" && connection && activeWorkspaceItem && (() => {
            const trials = (workspaceCommercial?.trials as Array<Record<string, unknown>> | undefined) || [];
            const value = (workspaceCommercial?.value as Record<string, unknown> | undefined) || {};
            return <section className={styles.commercialPanel} aria-label="Departments, usage and value">
              <header><div><small>CUSTOMER CONTROL</small><strong>Departments, usage and value</strong></div><button onClick={() => void refreshWorkspaceCommercial(activeWorkspaceItem)}>Refresh</button></header>
              <p>{String(workspaceCommercial?.ownership_message || "Your brain, memory, local models, backup and export remain yours.")}</p>
              <div className={styles.commercialSummary}><span><b>{Number(value.verified_actions || 0)}</b> verified actions</span><span><b>{trials.filter((item) => ["active", "paid_active", "review_only"].includes(String(item.state))).length}</b> active departments</span></div>
              {trials.map((trial) => <article key={String(trial.trial_id)}><div><strong>{String(trial.department || "department").replaceAll("_", " ")}</strong><span>{String(trial.state)} · {Number(trial.verified_actions || 0)}/{Number(trial.action_limit || 0)} actions · {Number(trial.managed_cost || 0).toFixed(2)}/{Number(trial.managed_cost_limit || 0).toFixed(2)} {String(trial.currency || "")}</span></div>{!["cancelled", "expired"].includes(String(trial.state)) && <button onClick={() => void cancelWorkspaceTrial(activeWorkspaceItem, String(trial.trial_id))}>Cancel</button>}</article>)}
              <div className={styles.commercialForm}><select aria-label="Department trial" value={workspaceCommercialDepartment} onChange={(event) => setWorkspaceCommercialDepartment(event.target.value)}><option value="sales">Sales</option><option value="marketing">Marketing</option><option value="customer_support">Customer support</option><option value="finance_monitoring">Finance monitoring</option><option value="operations">Operations</option><option value="website_lead_response">Website lead response</option></select><input aria-label="Verified-action allowance" type="number" min="1" max="1000000" value={workspaceCommercialActions} onChange={(event) => setWorkspaceCommercialActions(event.target.value)}/><input aria-label="Managed intelligence budget in EUR" type="number" min="0" step="0.01" value={workspaceCommercialBudget} onChange={(event) => setWorkspaceCommercialBudget(event.target.value)}/><button onClick={() => void startWorkspaceTrial(activeWorkspaceItem)}>Start 30-day trial</button><input aria-label="Monthly verified-action capacity" type="number" min="0" max="1000000" value={workspaceCommercialCapacity} onChange={(event) => setWorkspaceCommercialCapacity(event.target.value)}/><label className={styles.commercialOverage}><input type="checkbox" checked={workspaceCommercialOverage} onChange={(event) => setWorkspaceCommercialOverage(event.target.checked)}/> Allow overage</label><button onClick={() => void setWorkspaceCapacity(activeWorkspaceItem)}>Set monthly capacity</button></div>
              <small>{workspaceCommercialStatus} No automatic renewal.</small>
            </section>;
          })()}

          <section className={styles.feed} aria-live="polite">
            <div className={styles.sectionTitle}>
              <div>
                <p>{selectedShortcut && activeNav === "Pilot" ? `${modeCopy[mode].label} tool` : "Right now"}</p>
                <h2>{activeNav === "Pilot" ? selectedShortcut || "Pilot stream" : activeNav}</h2>
              </div>
              {selectedShortcut && activeNav === "Pilot" ? (
                <button onClick={() => openShortcut(null)}>Close tool</button>
              ) : (
                <button onClick={() => setNotice("Everything in this section is now shown")}>See all <ChevronRight size={15} /></button>
              )}
            </div>

            {activeNav === "Pilot" && pilotResult && <article className={styles.pilotResult}><small>{String(pilotResult.display_label || "AION Local")}</small><strong>Pilot</strong><p>{String(pilotResult.spoken_response || "")}</p>{pilotResult.receipt ? <span>Execution receipt attached</span> : <span>No external action claimed</span>}</article>}

            {activeNav === "Spaces" && connection && (
              <section className={styles.workspaceInvitations} aria-label="Private workspace invitations">
                <div><BriefcaseBusiness size={18} /><strong>Workspace invitations</strong><span>private phone review</span></div>
                {workspaceInvitations.length === 0 && <p>No pending workspace invitations.</p>}
                {workspaceInvitations.map((item) => {
                  const invitation = item.invitation as Record<string, unknown>;
                  const organization = item.organization as Record<string, unknown>;
                  const constraints = item.constraints as Record<string, unknown>;
                  const pending = invitation.state === "pending";
                  return <article key={String(invitation.invitation_id)}>
                    <small>{String(organization.display_name || "Workspace")}</small>
                    <h3>{String(invitation.role_id || "Member").replace("role_", "").replaceAll("_", " ")}</h3>
                    <p>Invited by {String(invitation.inviter_persona_id || "an authorized member")}</p>
                    <dl><dt>Permissions</dt><dd>{((invitation.requested_scopes as string[]) || []).join(", ") || "None"}</dd><dt>Constraints</dt><dd>{Object.keys(constraints || {}).length ? JSON.stringify(constraints) : "No additional constraints"}</dd><dt>Expires</dt><dd>{new Date(String(invitation.expires_at)).toLocaleString()}</dd></dl>
                    {pending && <div><button onClick={() => void respondToWorkspaceInvitation(item, "declined")}>Decline</button><button className={styles.primaryAction} onClick={() => void respondToWorkspaceInvitation(item, "accepted")}>Accept exact access</button></div>}
                    {!pending && <><b>{String(invitation.state)}</b>{invitation.state === "accepted" && <><div><button onClick={() => void openWorkspaceSummary(item, "briefings")}>Briefing</button><button onClick={() => void openWorkspaceSummary(item, "departments")}>Departments</button><button onClick={() => void openWorkspaceSummary(item, "dashboards")}>Dashboard</button><button onClick={() => void refreshWorkspaceCards(item)}>Review cards</button><button onClick={() => void refreshWorkspaceSignoffs(item)}>Sign-offs</button></div><form className={styles.workspaceConversation} onSubmit={(event) => { event.preventDefault(); void sendWorkspaceTurn(item); }}><label>Talk to workspace Pilot<select value={workspaceConversationDepartment} onChange={(event) => setWorkspaceConversationDepartment(event.target.value)}><option value="boardroom">Boardroom</option><option value="sales">Sales</option><option value="marketing">Marketing</option><option value="finance">Finance</option><option value="operations">Operations</option><option value="support">Support</option><option value="people">People</option></select></label><textarea value={workspaceConversationDraft} onChange={(event) => setWorkspaceConversationDraft(event.target.value)} maxLength={2000} placeholder="Ask about this workspace…"/><button className={styles.primaryAction} type="submit">Ask Pilot</button></form><label className={styles.signoffRole}>Prepare professional sign-off<select value={workspaceSignoffRole} onChange={(event) => setWorkspaceSignoffRole(event.target.value as typeof workspaceSignoffRole)}><option value="accountant">Accountant</option><option value="auditor">Auditor</option><option value="adviser">Adviser</option><option value="director">Director</option></select></label>{workspaceCards.map((card) => <section className={styles.workspaceCard} key={String(card.card_id)}><small>{String(card.department_id)} · {String(card.state)}</small><strong>{String(card.title)}</strong><span>{String(card.source_status)}</span><div><button onClick={() => void actOnWorkspaceCard(item, card, "review")}>Reviewed</button><button onClick={() => void actOnWorkspaceCard(item, card, "correct")}>Correct</button><button onClick={() => void actOnWorkspaceCard(item, card, "delegate")}>Delegate</button><button className={styles.primaryAction} onClick={() => void actOnWorkspaceCard(item, card, "approve")}>Approve exact card</button><button onClick={() => void prepareSignoff(item, card)}>Prepare sign-off</button></div></section>)}{workspaceSignoffs.map((signoff) => <section className={styles.workspaceCard} key={String(signoff.package_id)}><small>{String(signoff.signatory_role)} · {String(signoff.status)}</small><strong>{String(signoff.title)}</strong><span>{String(signoff.statement)}</span>{signoff.status === "awaiting_signoff" && <div><button onClick={() => void decideSignoff(item, signoff, "rejected")}>Reject</button><button className={styles.primaryAction} onClick={() => void decideSignoff(item, signoff, "signed")}>Sign exact package</button></div>}</section>)}</>}</>}
                  </article>;
                })}
                {workspaceSummary && <article className={styles.workspaceSummary}>
                  <small>{String(workspaceSummary.surface || "Workspace summary")}</small>
                  <h3>{String((workspaceSummary.space as Record<string, unknown> | undefined)?.display_name || "Business update")}</h3>
                  <pre>{JSON.stringify(workspaceSummary.data || {}, null, 2)}</pre>
                  <span>Source: {String(workspaceSummary.source_of_truth || "workspace provider")} · revision {String(workspaceSummary.provider_revision || "current")}</span>
                  {["briefings", "dashboards"].includes(String(workspaceSummary.surface || "")) && <button className={styles.primaryAction} onClick={() => void presentOnTV({
                    operation: "present",
                    contentKind: String(workspaceSummary.surface) === "dashboards" ? "dashboard" : "briefing",
                    contentId: `${String((workspaceSummary.space as Record<string, unknown> | undefined)?.space_id || "workspace")}/${String(workspaceSummary.surface || "briefing")}`,
                    title: String((workspaceSummary.space as Record<string, unknown> | undefined)?.display_name || "Workspace"),
                    authorityDomain: String((workspaceSummary.space as Record<string, unknown> | undefined)?.kind || "workspace") === "boardroom" ? "boardroom" : "workspace",
                    membershipId: String(workspaceSummary.membership_id || ""),
                  })}>Present this on TV</button>}
                </article>}
                {workspaceConversation && <article className={styles.workspaceSummary}>
                  <small>{String(workspaceConversation.department_id || "Workspace Pilot")}</small>
                  <h3>Pilot answer</h3>
                  <p>{String((((workspaceConversation.conversation as Record<string, unknown> | undefined)?.turn as Record<string, unknown> | undefined)?.content) || "No answer returned.")}</p>
                  <span>{String(((workspaceConversation.conversation as Record<string, unknown> | undefined)?.reliability) || "unknown reliability")} · no external action claimed</span>
                </article>}
                {activeWorkspaceItem && <button className={styles.secondaryAction} onClick={() => void continueWorkspaceOnDesktop(activeWorkspaceItem)}>
                  <ExternalLink size={16} /> Continue on desktop
                </button>}
                <p>{workspaceInvitationStatus}</p>
              </section>
            )}

            {activeNav === "Me" && (
              <section className={styles.connectionPanel} aria-label="Phone and Pilot connection">
                <div className={styles.connectionHeading}>
                  <span><ShieldCheck size={20} /></span>
                  <div><small>YOUR PILOT</small><h3>{fixture.connection.mother_display_name}</h3></div>
                  <i>Connected</i>
                </div>
                <p><Smartphone size={16} /> {fixture.device.label} · trusted possession</p>
                <p><Radio size={16} /> Direct private connection while you are at home</p>
                <div className={styles.trustWords} aria-label="Mother verification words">
                  {fixture.connection.trust_words.map((word) => <span key={word}>{word}</span>)}
                </div>
              <button className={styles.secondaryAction} onClick={() => setPairingOpen(!pairingOpen)}>
                  <RefreshCw size={17} /> {pairingOpen ? "Close connection setup" : "Connect another Pilot"}
                </button>
                {pairingOpen && (
                  <div className={styles.pairingBox}>
                    <strong>Connect this phone</strong>
                    <p>Enter the secure address shown by the Pilot you own. Pilot will show six digits locally; the code is never sent to this page.</p>
                    <input
                      className={styles.addressInput}
                      value={pilotAddress}
                      onChange={(event) => setPilotAddress(event.target.value)}
                      inputMode="url"
                      autoCapitalize="none"
                      placeholder="https://pilot-home.local:8770"
                      aria-label="Secure Pilot address"
                    />
                    <button disabled={!pilotAddress || Boolean(pairingChallenge)} onClick={() => void findPilot()}>Find my Pilot</button>
                    {pairingTrustWords.length > 0 && <div className={styles.trustWords}>{pairingTrustWords.map((word) => <span key={word}>{word}</span>)}</div>}
                    <input
                      value={pairingCode}
                      onChange={(event) => setPairingCode(event.target.value.replace(/\D/g, "").slice(0, 6))}
                      inputMode="numeric"
                      autoComplete="one-time-code"
                      placeholder="6-digit code"
                      aria-label="Six-digit Pilot pairing code"
                      disabled={!pairingChallenge}
                    />
                    <button
                      disabled={!pairingChallenge || pairingCode.length !== 6}
                      onClick={() => void connectPilot()}
                    >Connect securely</button>
                    <small>{pairingStatus}</small>
                  </div>
                )}
              </section>
            )}

            <article className={styles.primaryCard}>
              <div className={styles.cardIcon}><Sparkles size={20} /></div>
              <div>
                <small>{mode === "boardroom" ? "BRIEFING · VERIFIED" : "PILOT · READY"}</small>
                <h3>{mode === "personal" ? "Your day is clear until 16:30" : mode === "workspace" ? "Three items need your review" : "Two decisions await approval"}</h3>
                <p>{mode === "personal" ? "One household task is due today. Nothing has been sent or changed." : "Private details remain on the mother brain until you open them."}</p>
              </div>
              <button aria-label="Open item"><ChevronRight /></button>
            </article>

            {activeNav === "Pilot" && mode === "personal" && selectedShortcut === "Calendar" && connection && (
              <section className={`${styles.liveInbox} ${styles.calendarPanel}`} aria-label="Private calendar">
                <div><CalendarDays size={17} /><strong>Your private calendar</strong><span>phone only</span></div>
                {(() => {
                  const provider = (personalCalendar?.provider as Record<string, unknown> | undefined) || {};
                  return <p>{provider.google_calendar_connected ? "Google Calendar is connected to this person." : "No external calendar is connected. You can prepare and review changes; execution stays safely blocked."}</p>;
                })()}
                <form className={styles.calendarForm} onSubmit={(event) => void checkAvailability(event)}>
                  <strong>Find a free time</strong>
                  <input type="datetime-local" value={availabilityStart} onChange={(event) => setAvailabilityStart(event.target.value)} aria-label="Availability starts" required />
                  <input type="datetime-local" value={availabilityEnd} onChange={(event) => setAvailabilityEnd(event.target.value)} aria-label="Availability ends" required />
                  <button type="submit"><Clock3 size={15} /> Check privately</button>
                  {availability.length > 0 && <div className={styles.freeSlots}>{availability.slice(0, 6).map((slot) => <span key={String(slot.start)}>{new Date(String(slot.start)).toLocaleString([], { weekday: "short", hour: "2-digit", minute: "2-digit" })}</span>)}</div>}
                </form>
                <form className={styles.calendarForm} onSubmit={(event) => void prepareCalendar(event)}>
                  <strong>Prepare a calendar change</strong>
                  <select value={calendarAction} onChange={(event) => setCalendarAction(event.target.value as typeof calendarAction)} aria-label="Calendar action">
                    <option value="create">Create event</option><option value="reschedule">Reschedule event</option><option value="cancel">Cancel event</option>
                  </select>
                  <input value={calendarTitle} onChange={(event) => setCalendarTitle(event.target.value)} placeholder="Event title" aria-label="Event title" required />
                  {calendarAction !== "create" && <input value={calendarEventId} onChange={(event) => setCalendarEventId(event.target.value)} placeholder="Exact calendar event ID" aria-label="Calendar event ID" required />}
                  {calendarAction !== "cancel" && <>
                    <input type="datetime-local" value={calendarStart} onChange={(event) => setCalendarStart(event.target.value)} aria-label="Event starts" required />
                    <input type="datetime-local" value={calendarEnd} onChange={(event) => setCalendarEnd(event.target.value)} aria-label="Event ends" required />
                    <input value={calendarLocation} onChange={(event) => setCalendarLocation(event.target.value)} placeholder="Location (optional)" aria-label="Event location" />
                    <input value={calendarAttendees} onChange={(event) => setCalendarAttendees(event.target.value)} placeholder="Attendee emails, separated by commas" aria-label="Event attendees" inputMode="email" />
                    <div className={styles.calendarNumbers}>
                      <label>Travel<input type="number" min="0" max="1440" value={calendarTravel} onChange={(event) => setCalendarTravel(event.target.value)} aria-label="Travel minutes" /></label>
                      <label>Reminder<input type="number" min="0" max="10080" value={calendarReminder} onChange={(event) => setCalendarReminder(event.target.value)} aria-label="Reminder minutes" /></label>
                    </div>
                    <label className={styles.checkRow}><input type="checkbox" checked={calendarNotify} onChange={(event) => setCalendarNotify(event.target.checked)} /> Notify attendees after approval</label>
                  </>}
                  <button type="submit">Prepare—do not send</button>
                </form>
                {((personalCalendar?.proposals as Array<Record<string, unknown>> | undefined) || []).slice(-5).reverse().map((proposal) => {
                  const scope = (proposal.scope as Record<string, unknown> | undefined) || {};
                  const status = String(proposal.status || "awaiting_private_approval");
                  return <article className={styles.calendarProposal} key={String(proposal.proposal_id)}>
                    <small>{String(proposal.action || "change")} · {status.replaceAll("_", " ")}</small>
                    <strong>{String(scope.title || "Calendar change")}</strong>
                    <span>Calendar: {String(scope.calendar_id || "primary")}</span>
                    {Boolean(scope.start) && <span>{new Date(String(scope.start)).toLocaleString()} → {new Date(String(scope.end)).toLocaleString()}</span>}
                    {Boolean(scope.location) && <span>Location: {String(scope.location)}</span>}
                    {Array.isArray(scope.attendees) && scope.attendees.length > 0 && <span>Attendees: {scope.attendees.map(String).join(", ")}</span>}
                    <span>Travel {Number(scope.travel_minutes || 0)} min · reminder {Number(scope.reminder_minutes || 0)} min</span>
                    {Number(proposal.conflict_count || 0) > 0 && <b>{Number(proposal.conflict_count)} private conflict detected; titles remain hidden.</b>}
                    {["awaiting_private_approval", "awaiting_conflict_confirmation"].includes(status) && <div className={styles.taskActions}><button className={styles.acceptTask} onClick={() => void decideCalendar(proposal, true)}>Approve exact change</button><button onClick={() => void decideCalendar(proposal, false)}>Reject</button></div>}
                    {status === "approved_pending_adapter" && <div className={styles.taskActions}><button className={styles.acceptTask} onClick={() => void executeCalendar(proposal)}>Execute approved change</button></div>}
                    {status === "executed" && <i className={`${styles.state} ${styles.state_verified}`}>provider verified</i>}
                  </article>;
                })}
                <p className={styles.calendarStatus}>{calendarStatus}</p>
              </section>
            )}

            {activeNav === "Pilot" && mode === "personal" && selectedShortcut === "Contacts" && connection && (
              <section className={`${styles.liveInbox} ${styles.contactsPanel}`} aria-label="Private contacts">
                <div><ContactRound size={17} /><strong>Your private contacts</strong><span>phone only</span></div>
                <form className={styles.contactSearch} onSubmit={(event) => void resolveContact(event)}>
                  <label><Search size={16} /><input value={contactQuery} onChange={(event) => { setContactQuery(event.target.value); setContactResolution(null); }} placeholder="Type or say a contact name" aria-label="Resolve a private contact" required /></label>
                  <button type="submit">Resolve</button>
                </form>
                {contactResolution && <div className={styles.resolutionCard}>
                  <strong>{contactResolution.status === "resolved" ? String((contactResolution.contact as Record<string, unknown>)?.display_name || "Contact resolved") : contactResolution.status === "ambiguous" ? "Choose one contact" : "No contact found"}</strong>
                  {contactResolution.status === "resolved" && <>
                    <span>Route: {String(contactResolution.selected_route || "private")}</span>
                    <small>{String(contactResolution.recipient_reference || "")}</small>
                    <i>Resolved only—nothing has been sent.</i>
                  </>}
                  {contactResolution.status === "ambiguous" && ((contactResolution.candidates as Array<Record<string, unknown>> | undefined) || []).map((candidate) => <button key={String(candidate.contact_id)} onClick={() => { setContactQuery(String(candidate.display_name || "")); setContactResolution(null); }}>{String(candidate.display_name)}</button>)}
                </div>}
                <div className={styles.contactList}>
                  {personalContacts.map((contact) => <article key={String(contact.contact_id)}>
                    <small>{((contact.available_routes as string[] | undefined) || []).join(" · ") || "no route"}</small>
                    <strong>{String(contact.display_name || "Private contact")}</strong>
                    <span>{String(contact.email || contact.whatsapp || contact.pilot_persona_id || "Private route")}</span>
                    <div className={styles.taskActions}><button onClick={() => editContact(contact)}><Pencil size={13} /> Edit</button><button onClick={() => void removeContact(contact)}><Trash2 size={13} /> Remove</button></div>
                  </article>)}
                  {personalContacts.length === 0 && <p>No private contacts match.</p>}
                </div>
                <form className={styles.contactForm} onSubmit={(event) => void saveContact(event)}>
                  <strong>{contactId ? "Edit contact" : "Add a contact"}</strong>
                  <button type="button" className={styles.importContact} onClick={() => void importPhoneContact()}><UserPlus size={15} /> Choose from phone when supported</button>
                  <input value={contactName} onChange={(event) => setContactName(event.target.value)} placeholder="Name" aria-label="Contact name" required />
                  <input value={contactEmail} onChange={(event) => setContactEmail(event.target.value)} placeholder="Email (optional)" aria-label="Contact email" inputMode="email" />
                  <input value={contactWhatsapp} onChange={(event) => setContactWhatsapp(event.target.value)} placeholder="WhatsApp with country code (optional)" aria-label="Contact WhatsApp number" inputMode="tel" />
                  <details><summary>Pilot-to-Pilot route</summary>
                    <input value={contactPilotPersona} onChange={(event) => setContactPilotPersona(event.target.value)} placeholder="Pilot person ID" aria-label="Contact Pilot person ID" />
                    <input value={contactPilotMother} onChange={(event) => setContactPilotMother(event.target.value)} placeholder="Pilot mother ID" aria-label="Contact Pilot mother ID" />
                  </details>
                  <select value={contactPreferredRoute} onChange={(event) => setContactPreferredRoute(event.target.value as typeof contactPreferredRoute)} aria-label="Preferred contact route">
                    <option value="">Choose best available route</option><option value="pilot">Pilot-to-Pilot</option><option value="whatsapp">WhatsApp</option><option value="email">Email</option>
                  </select>
                  <button type="submit">{contactId ? "Save changes" : "Save private contact"}</button>
                  {contactId && <button type="button" className={styles.cancelEdit} onClick={clearContactForm}>Cancel editing</button>}
                </form>
                <p className={styles.contactStatus}>{contactStatus}</p>
              </section>
            )}

            {activeNav === "Pilot" && mode === "personal" && selectedShortcut === "Messages" && connection && (
              <section className={`${styles.liveInbox} ${styles.communicationPanel}`} aria-label="Private email and messaging">
                <div><Mail size={17} /><strong>Email &amp; messages</strong><span>approval gated</span></div>
                {(() => {
                  const providers = (personalCommunication?.providers as Record<string, unknown> | undefined) || {};
                  return <p>{providers.email_send_connected ? "Your authorized email sender is connected." : "No email sender is connected. Drafting and approval work, but delivery remains blocked."} WhatsApp delivery also requires an officially authorized adapter.</p>;
                })()}
                <form className={styles.communicationForm} onSubmit={(event) => void prepareCommunication(event)}>
                  <strong>Prepare—do not send</strong>
                  <select value={communicationContact} onChange={(event) => setCommunicationContact(event.target.value)} aria-label="Message recipient" required>
                    <option value="">Choose a private contact</option>
                    {personalContacts.map((contact) => <option key={String(contact.contact_id)} value={String(contact.contact_id)}>{String(contact.display_name)}</option>)}
                  </select>
                  <select value={communicationChannel} onChange={(event) => setCommunicationChannel(event.target.value as typeof communicationChannel)} aria-label="Message route">
                    <option value="email">Email</option><option value="whatsapp">WhatsApp handoff</option><option value="pilot">Pilot-to-Pilot</option>
                  </select>
                  {communicationChannel === "email" && <input value={communicationSubject} onChange={(event) => setCommunicationSubject(event.target.value)} placeholder="Subject (optional)" aria-label="Email subject" />}
                  <textarea value={communicationBody} onChange={(event) => setCommunicationBody(event.target.value)} placeholder="Write the exact message" aria-label="Exact message content" maxLength={20000} required />
                  <button type="submit">Prepare exact draft</button>
                  <button type="button" className={styles.cancelEdit} onClick={() => void prepareCall()}><Phone size={14} /> Prepare a call instead</button>
                </form>
                {preparedCall && <article className={styles.callPreparation}>
                  <small>call · prepared, not placed</small>
                  <strong>{String(preparedCall.recipient_name || "Contact")}</strong>
                  <span>Your phone must place this call.</span>
                  <a href={`tel:${String(preparedCall.phone_reference || "")}`}>Tap to call</a>
                </article>}
                <div className={styles.communicationList}>
                  {((personalCommunication?.drafts as Array<Record<string, unknown>> | undefined) || []).slice(-8).reverse().map((item) => {
                    const status = String(item.status || "awaiting_private_approval");
                    return <article key={String(item.draft_id)}>
                      <small>{String(item.channel || "message")} · {status.replaceAll("_", " ")}</small>
                      <strong>To {String(item.recipient_name || "private contact")}</strong>
                      <span>{String(item.recipient || "")}</span>
                      {Boolean(item.subject) && <b>{String(item.subject)}</b>}
                      <p>{String(item.body || "")}</p>
                      {((item.attachments as Array<Record<string, unknown>> | undefined) || []).map((attachment) => <span key={String(attachment.attachment_id)}>Attachment: {String(attachment.name)} · {Number(attachment.size || 0).toLocaleString()} bytes · verified hash {String(attachment.sha256 || "").slice(0, 12)}…</span>)}
                      {status === "guardian_approval_required" && <i className={`${styles.state} ${styles.state_locked}`}>guardian decision required</i>}
                      {status === "awaiting_private_approval" && <div className={styles.taskActions}><button className={styles.acceptTask} onClick={() => void decideCommunication(item, true)}>Approve exact message</button><button onClick={() => void decideCommunication(item, false)}>Reject</button></div>}
                      {status === "approved_pending_adapter" && <div className={styles.taskActions}><button className={styles.acceptTask} onClick={() => void executeCommunication(item)}>Send approved message</button></div>}
                      {["provider_accepted", "delivered"].includes(status) && <><div className={styles.followUpRow}><input type="datetime-local" value={communicationFollowUp} onChange={(event) => setCommunicationFollowUp(event.target.value)} aria-label="Follow up if no reply by" /><button onClick={() => void scheduleMessageFollowUp(String(item.draft_id))}>Remind if no reply</button></div><div className={styles.taskActions}><button onClick={() => void createInvite(String(item.draft_id))}>Share useful invite</button><button onClick={() => void protectContact(String(item.contact_id), "block")}>Block</button><button onClick={() => void protectContact(String(item.contact_id), "report")}>Report</button></div></>}
                    </article>;
                  })}
                </div>
                {((personalCommunication?.received as Array<Record<string, unknown>> | undefined) || []).length > 0 && <h3>Received summaries</h3>}
                {((personalCommunication?.received as Array<Record<string, unknown>> | undefined) || []).slice(-5).reverse().map((item) => <article key={String(item.message_id)}>
                  <small>received · {String(item.source || "provider evidence")}</small>
                  <strong>{String(item.sender_name || "Sender")}</strong>
                  <p>{String(item.summary || "")}</p>
                  <span>{new Date(String(item.received_at)).toLocaleString()}</span>
                  <div className={styles.taskActions}><button onClick={() => void convertCommunication(String(item.message_id), "task")}>Make task</button><button onClick={() => void convertCommunication(String(item.message_id), "reminder")}>Prepare reminder</button><button onClick={() => void convertCommunication(String(item.message_id), "calendar")}>Prepare calendar item</button></div>
                </article>)}
                {((personalCommunication?.receipts as Array<Record<string, unknown>> | undefined) || []).length > 0 && <h3>Verified delivery receipts</h3>}
                {((personalCommunication?.receipts as Array<Record<string, unknown>> | undefined) || []).slice(-5).reverse().map((receipt) => <article key={String(receipt.receipt_id)}>
                  <small>{String(receipt.channel || "provider")} · {String(receipt.provider_state || "provider accepted").replaceAll("_", " ")}</small>
                  <strong>{receipt.provider_state === "delivered" ? "Provider delivery event recorded" : "Provider accepted the send request"}</strong>
                  <span>{String(receipt.provider_message_id || "")}</span>
                  <i className={`${styles.state} ${styles.state_verified}`}>{receipt.provider_state === "delivered" ? "delivery event verified; human reading unknown" : "not proof of delivery or reading"}</i>
                </article>)}
                <p className={styles.communicationStatus}>{communicationStatus}</p>
              </section>
            )}

            {activeNav === "Pilot" && mode === "personal" && selectedShortcut === "Devices" && connection && (
              <section className={`${styles.liveInbox} ${styles.communicationPanel} ${styles.devicePanel}`} aria-label="Private device mesh and IoT controls">
                <div><Radio size={17} /><strong>Devices &amp; IoT</strong><span>local mesh</span></div>
                <p>Pilot shows evidenced devices without exposing local addresses or cryptographic keys. Discovery observes advertisements only; it never enrolls a device or grants control.</p>
                <button className={styles.devicePrimary} onClick={() => void discoverDevices()}><RefreshCw size={15} /> Discover nearby devices</button>
                <div className={styles.deviceSummary}>
                  <span><b>{Number(personalDevices?.node_count || 0)}</b> visible nodes</span>
                  <span><b>{((personalDevices?.nodes as Array<Record<string, unknown>> | undefined) || []).filter((node) => node.enrollment === "enrolled").length}</b> enrolled</span>
                  <span><b>{((personalDevices?.rooms as Array<Record<string, unknown>> | undefined) || []).length}</b> TV rooms</span>
                </div>
                <div className={styles.deviceGrid}>{((personalDevices?.nodes as Array<Record<string, unknown>> | undefined) || []).map((node) => {
                  const capabilities = (node.capabilities as Array<Record<string, unknown>> | undefined) || [];
                  return <article key={String(node.node_id)}>
                    <small>{String(node.role || "observer")} · {String(node.enrollment || "discovered")}</small>
                    <strong>{String(node.name || "Unknown device")}</strong>
                    <span>{String(node.device_class || "unknown")} · {String(node.platform || "unknown")}</span>
                    <span>{((node.transports as string[] | undefined) || []).join(", ") || "transport not evidenced"}</span>
                    <i className={`${styles.state} ${node.enrollment === "enrolled" ? styles.state_verified : styles.state_pending}`}>{node.enrollment === "enrolled" ? `${capabilities.length} signed capabilities` : "observation only"}</i>
                  </article>;
                })}</div>
                {(() => {
                  const climate = (personalDevices?.climate as Record<string, unknown> | undefined) || {};
                  const presets = (climate.learned_presets as string[] | undefined) || [];
                  return <section className={styles.climateCard}>
                    <strong>Local infrared climate</strong>
                    <span>{climate.connected ? "Gateway connected" : "No AION-compatible infrared gateway detected"}</span>
                    {presets.length > 0 && <div className={styles.libraryActions}>{presets.map((preset) => <button key={preset} onClick={() => void sendIotPreset(preset)}>{preset.replaceAll("_", " ")}</button>)}</div>}
                    <small>Infrared proves transport delivery only. It cannot prove the air conditioner changed state.</small>
                  </section>;
                })()}
                <p className={styles.communicationStatus}>{deviceStatus}</p>
              </section>
            )}

            {activeNav === "Pilot" && mode === "personal" && selectedShortcut === "TV" && connection && (
              <section className={`${styles.liveInbox} ${styles.communicationPanel} ${styles.devicePanel}`} aria-label="Private television status and controls">
                <div><Tv size={17} /><strong>Television</strong><span>verified control</span></div>
                {(() => {
                  const tvConnection = (personalDevices?.tv_connection as Record<string, unknown> | undefined) || {};
                  const sharedTV = (personalDevices?.shared_tv as Record<string, unknown> | undefined) || {};
                  const primary = ((personalDevices?.nodes as Array<Record<string, unknown>> | undefined) || []).find((node) => node.is_primary_tv);
                  const state = String(sharedTV.state || "locked");
                  return <>
                    <article className={styles.tvStatusCard}>
                      <small>{String(tvConnection.status || "not verified").replaceAll("_", " ")}</small>
                      <strong>{String(primary?.name || "No paired television")}</strong>
                      <p>{String(tvConnection.message || "Refresh to verify the television.")}</p>
                      <span>{state === "you" ? "You currently control the shared screen. It locks after five minutes without an action or a nearby trusted-phone signal." : state === "another_person" ? "Another household member currently controls this screen." : "Private workspace is locked."}</span>
                    </article>
                    <div className={styles.tvSessionActions}>
                      {state !== "you" && <button disabled={state === "another_person"} onClick={() => void changeTVSession("acquire")}><ShieldCheck size={15} /> Take control</button>}
                      {state === "you" && <button onClick={() => void changeTVSession("release")}><LockKeyhole size={15} /> Lock TV workspace</button>}
                      <button onClick={() => void sendTVCommand("observe")}><RefreshCw size={15} /> Refresh TV state</button>
                    </div>
                    {state === "you" && <>
                      <div className={styles.tvDpad} aria-label="Television directional controls">
                        <button className={styles.tvUp} aria-label="Up" onClick={() => void sendTVCommand("up")}>▲</button>
                        <button className={styles.tvLeft} aria-label="Left" onClick={() => void sendTVCommand("left")}>◀</button>
                        <button className={styles.tvOk} aria-label="OK" onClick={() => void sendTVCommand("enter")}>OK</button>
                        <button className={styles.tvRight} aria-label="Right" onClick={() => void sendTVCommand("right")}>▶</button>
                        <button className={styles.tvDown} aria-label="Down" onClick={() => void sendTVCommand("down")}>▼</button>
                      </div>
                      <div className={styles.tvControls}>{[
                        ["back", "Back"], ["home", "Home"], ["volume_down", "Volume −"], ["volume_up", "Volume +"],
                        ["play", "Play"], ["pause", "Pause"], ["mute", "Mute"], ["unmute", "Unmute"],
                      ].map(([command, label]) => <button key={command} onClick={() => void sendTVCommand(command)}>{label}</button>)}</div>
                      <h3>Open on television</h3>
                      <div className={styles.tvApps}>{[
                        ["aion", "Pilot Home"], ["netflix", "Netflix"], ["youtube", "YouTube"], ["games", "Games"], ["god_view", "God View"],
                      ].map(([command, label]) => <button key={command} onClick={() => void sendTVCommand(command)}>{label}</button>)}</div>
                      <h3>Present privately</h3>
                      <div className={styles.tvApps}>
                        <button onClick={() => void presentOnTV({ operation: "present", contentKind: "briefing", contentId: "personal/today", title: "My Pilot briefing", authorityDomain: "personal" })}>My briefing</button>
                        <button onClick={() => void presentOnTV({ operation: "dismiss" })}>Close presentation</button>
                      </div>
                    </>}
                  </>;
                })()}
                {deviceLastResult && <div className={styles.deviceReceipt}><Check size={15} /><span>{String(deviceLastResult.spoken_response || "Latest command recorded")}</span><small>{Boolean((deviceLastResult.receipt as Record<string, unknown> | undefined)?.verified) ? "device verified" : "verification still required"}</small></div>}
                <p className={styles.communicationStatus}>{deviceStatus}</p>
              </section>
            )}

            {activeNav === "Pilot" && mode === "personal" && selectedShortcut === "Memory" && connection && (
              <section className={`${styles.liveInbox} ${styles.experiencePanel} ${styles.memoryPanel}`} aria-label="Private memory controls">
                <div><Brain size={17} /><strong>Memory</strong><span>you control it</span></div>
                <p>Inspect, correct, move between private and household scope, export, or permanently delete what Pilot remembers. Another adult&apos;s memory is never available here.</p>
                <label className={styles.memoryTarget}>Memory owner
                  <select value={memoryTarget} onChange={(event) => { const value = event.target.value; setMemoryTarget(value); void refreshMemory(value).catch((error) => setMemoryStatus(error instanceof Error ? error.message : "Pilot could not open that memory.")); }}>
                    <option value="">Me</option>
                    {((personalPilot?.guardian_controlled_children as Array<Record<string, unknown>> | undefined) || []).map((child) => <option key={String(child.persona_id)} value={String(child.persona_id)}>{String(child.display_name)} · guardian managed</option>)}
                  </select>
                </label>
                <form className={styles.memoryForm} onSubmit={addMemory}>
                  <strong>Add something explicitly</strong>
                  <div><select value={memoryKind} onChange={(event) => setMemoryKind(event.target.value)} aria-label="Memory kind"><option value="preference">Preference</option><option value="fact">Personal fact</option><option value="goal">Goal</option><option value="correction">Correction</option></select><select value={memoryScope} onChange={(event) => setMemoryScope(event.target.value as "private" | "household_shared")} aria-label="Memory scope"><option value="private">Private</option><option value="household_shared">Household shared</option></select></div>
                  <textarea value={memorySummary} onChange={(event) => setMemorySummary(event.target.value)} placeholder="What should Pilot remember?" maxLength={500} required />
                  <button type="submit">Save with this scope</button>
                </form>
                <div className={styles.memoryToolbar}><span><b>{Number(personalMemory?.memory_count || 0)}</b> memories for {String(personalMemory?.display_name || "you")}</span><button onClick={() => void downloadMemoryExport()}><Download size={14} /> Export JSON</button></div>
                <div className={styles.memoryList}>{((personalMemory?.memories as Array<Record<string, unknown>> | undefined) || []).slice().reverse().map((item) => <article key={String(item.memory_id)}>
                  <small>{String(item.kind || "memory").replaceAll("_", " ")} · {String(item.scope || "private").replaceAll("_", " ")}</small>
                  <strong>{String(item.summary || "")}</strong>
                  <span>{item.corrected_at ? `Corrected ${new Date(String(item.corrected_at)).toLocaleString()}` : `Added ${new Date(String(item.created_at)).toLocaleString()}`}</span>
                  <div className={styles.memoryActions}><button onClick={() => void correctMemory(item)}><Pencil size={13} /> Correct</button><button onClick={() => void changeMemoryScope(item)}>{String(item.scope) === "private" ? "Share with household" : "Make private"}</button><button className={styles.memoryDelete} onClick={() => void removeMemory(item)}><Trash2 size={13} /> Delete</button></div>
                </article>)}</div>
                {Number(personalMemory?.memory_count || 0) === 0 && <p>Pilot has no explicit memories for this person yet.</p>}
                <p className={styles.communicationStatus}>{memoryStatus}</p>
              </section>
            )}

            {activeNav === "Pilot" && mode === "personal" && selectedShortcut === "Guardian" && connection && (
              <section className={`${styles.liveInbox} ${styles.guardianPanel}`} aria-label="Pilot Guardian priority help">
                <div><ShieldCheck size={18} /><strong>Pilot Guardian</strong><span>priority help</span></div>
                <p>Guardian can alert only contacts you authorize here. It does not diagnose a fall and cannot claim an ambulance or emergency service was dispatched.</p>
                <label>Protected person<select value={guardianTarget} onChange={(event) => { const value = event.target.value; setGuardianTarget(value); void refreshGuardian(value).catch((error) => setGuardianStatus(error instanceof Error ? error.message : "Pilot could not open Guardian.")); }}><option value="">Me</option>{((personalPilot?.guardian_controlled_children as Array<Record<string, unknown>> | undefined) || []).map((child) => <option key={String(child.persona_id)} value={String(child.persona_id)}>{String(child.display_name)} · guardian managed</option>)}</select></label>
                <div className={styles.guardianPermission}>
                  <strong>Separate emergency contact permission</strong>
                  <select value={guardianContact} onChange={(event) => setGuardianContact(event.target.value)}><option value="">Choose a private contact</option>{personalContacts.map((contact) => <option key={String(contact.contact_id)} value={String(contact.contact_id)}>{String(contact.display_name)}</option>)}</select>
                  <select value={guardianChannel} onChange={(event) => setGuardianChannel(event.target.value)}><option value="pilot">Pilot-to-Pilot</option><option value="whatsapp">WhatsApp provider</option><option value="email">Email provider</option><option value="sms">SMS provider</option><option value="voice_call">Authorized call surface</option></select>
                  <label className={styles.guardianCheck}><input type="checkbox" checked={guardianShareLocation} onChange={(event) => setGuardianShareLocation(event.target.checked)} /> Share authorized location only during this alert</label>
                  {guardianShareLocation && <input value={guardianLocationReceipt} onChange={(event) => setGuardianLocationReceipt(event.target.value)} placeholder="Location permission receipt" />}
                  <button onClick={() => void saveGuardianContact()}>Save separate Guardian permission</button>
                </div>
                <button className={styles.guardianHelp} onClick={() => void runGuardian("request")}>I NEED HELP</button>
                {(() => {
                  const incident = (personalGuardian?.latest_incident as Record<string, unknown> | null | undefined) || null;
                  if (!incident) return <p>No active Guardian request.</p>;
                  const status = String(incident.status || "");
                  return <article className={styles.guardianIncident}><small>{status.replaceAll("_", " ")}</small><strong>{String(incident.trigger || "Priority help request")}</strong><span>{Number(incident.trusted_contact_count || 0)} authorized contact route(s)</span>{status === "awaiting_large_confirmation" && <><button className={styles.guardianConfirm} onClick={() => void runGuardian("confirm", String(incident.incident_id || ""))}>CONFIRM AND ALERT TRUSTED CONTACTS</button><button onClick={() => void runGuardian("cancel", String(incident.incident_id || ""))}>False alarm — cancel</button></>}{status === "connectivity_fallback_required" && <b>No delivery was verified. Call local emergency services directly.</b>}</article>;
                })()}
                <p className={styles.guardianWarning}>Emergency-service dispatch: <b>not connected</b>. In immediate danger, call your local emergency number.</p>
                <p className={styles.communicationStatus}>{guardianStatus}</p>
              </section>
            )}

            {activeNav === "Pilot" && mode === "personal" && selectedShortcut === "Learning" && connection && (
              <section className={`${styles.liveInbox} ${styles.experiencePanel}`} aria-label="Private learning centre">
                <div><GraduationCap size={17} /><strong>Learning Centre</strong><span>AION local</span></div>
                <p>Adaptive, child-safe practice runs without paid AI, advertising, open chat or external links.</p>
                <div className={styles.experienceSelectors}>
                  <select value={learningProfile} onChange={(event) => setLearningProfile(event.target.value)} aria-label="Learner"><option value="explorer_a">Explorer A</option><option value="explorer_b">Explorer B</option></select>
                  <select value={learningSubject} onChange={(event) => setLearningSubject(event.target.value)} aria-label="Subject"><option value="spanish">Spanish</option><option value="mathematics">Mathematics</option><option value="science">Science</option></select>
                  <select value={learningAge} onChange={(event) => setLearningAge(event.target.value)} aria-label="Age band"><option value="6-7">Age 6–7</option><option value="8-9">Age 8–9</option><option value="10-12">Age 10–12</option></select>
                  <select value={learningDifficulty} onChange={(event) => setLearningDifficulty(event.target.value)} aria-label="Difficulty"><option value="foundation">Foundation</option><option value="developing">Developing</option><option value="challenge">Challenge</option></select>
                </div>
                <button className={styles.experiencePrimary} onClick={() => void runExperience("learning_start", { profile_id: learningProfile, subject: learningSubject, age_band: learningAge, difficulty: learningDifficulty })}>Start a 50-question session</button>
                {(() => {
                  const learning = (personalExperiences?.learning as Record<string, unknown> | undefined) || {};
                  const session = (learning.session as Record<string, unknown> | undefined) || null;
                  const profile = session ? (((learning.profiles as Record<string, Record<string, unknown>> | undefined) || {})[String(session.profile_id)] || {}) : {};
                  if (!session) return <p>No learning session is active.</p>;
                  const choices = (session.choices as Array<Record<string, unknown>> | undefined) || [];
                  return <article className={styles.learningCard}>
                    <small>{String(session.category || session.subject || "Learning")} · {Number(session.round_number || 0)}/{Number(session.lesson_total || 50)}</small>
                    {Boolean(session.illustration_uri) && <img src={String(session.illustration_uri)} alt={String(session.visual_alt || "Learning illustration")} />}
                    <strong>{String(session.prompt || "Challenge ready")}</strong>
                    <p>{String(session.instruction || "Choose an answer.")}</p>
                    <div className={styles.learningProgress}><span><b>{Number(session.correct_in_session || 0)}</b> correct</span><span><b>{Number(profile.stars || 0)}</b> stars</span><span><b>{Number(profile.streak || 0)}</b> streak</span></div>
                    {String(session.phase) === "question" && <div className={styles.learningChoices}>{choices.map((choice) => <button key={String(choice.index)} onClick={() => void runExperience("learning_answer", { choice_index: Number(choice.index) })}>{String(choice.text)}</button>)}</div>}
                    {String(session.phase) === "feedback" && <div className={`${styles.learningFeedback} ${session.was_correct ? styles.learningCorrect : styles.learningIncorrect}`}>{String(session.feedback || "Answer checked.")}</div>}
                    <div className={styles.libraryActions}><button onClick={() => void runExperience("learning_repeat")}>Repeat</button>{String(session.phase) === "feedback" && <button onClick={() => void runExperience("learning_next")}>Next challenge</button>}</div>
                  </article>;
                })()}
                <p className={styles.communicationStatus}>{experienceStatus}</p>
              </section>
            )}

            {activeNav === "Pilot" && mode === "personal" && selectedShortcut === "Games" && connection && (
              <section className={`${styles.liveInbox} ${styles.experiencePanel}`} aria-label="Private games continuation">
                <div><Gamepad2 size={17} /><strong>Games</strong><span>provider governed</span></div>
                <p>Open GeForce NOW or prepare your last verified game. Provider sign-in remains with NVIDIA and opening the site is never described as playing.</p>
                <div className={styles.experienceActions}><button onClick={() => void runExperience("games_open")}><Gamepad2 size={15} /> Open GeForce NOW on TV</button><button onClick={() => void runExperience("games_continue")}><RefreshCw size={15} /> Continue last verified game</button></div>
                {(() => {
                  const games = (personalExperiences?.games as Record<string, unknown> | undefined) || {};
                  const latest = (games.latest_session as Record<string, unknown> | undefined) || null;
                  const controllers = (games.controllers as Array<Record<string, unknown>> | undefined) || [];
                  const shortcuts = (games.shortcuts as Array<Record<string, unknown>> | undefined) || [];
                  return <>
                    <article><small>{latest ? String(latest.state || "prepared").replaceAll("_", " ") : "no session"}</small><strong>{latest ? String(latest.title || latest.query || latest.provider_name || "GeForce NOW") : "No private game continuation yet"}</strong><span>{latest?.playing_verified ? "Playing verified" : "Playing not verified"}</span></article>
                    <div className={styles.learningProgress}><span><b>{controllers.filter((item) => item.gameplay_ready).length}</b> ready controllers</span><span><b>{shortcuts.length}</b> saved games</span><span><b>{latest?.stream_ready_verified ? 1 : 0}</b> streams ready</span></div>
                  </>;
                })()}
                <p className={styles.communicationStatus}>{experienceStatus}</p>
              </section>
            )}

            {activeNav === "Pilot" && mode === "personal" && selectedShortcut === "Entertainment" && connection && (
              <section className={`${styles.liveInbox} ${styles.experiencePanel}`} aria-label="Private entertainment continuation">
                <div><Film size={17} /><strong>Entertainment</strong><span>private history</span></div>
                <p>Continue a previously verified provider title or manage your private watch memory. Entitlement and playback remain separate verified states.</p>
                {(() => {
                  const entertainment = (personalExperiences?.entertainment as Record<string, unknown> | undefined) || {};
                  const executionSnapshot = (entertainment.execution as Record<string, unknown> | undefined) || {};
                  const latest = (executionSnapshot.latest as Record<string, unknown> | undefined) || null;
                  const personalization = (entertainment.personalization as Record<string, unknown> | undefined) || {};
                  const watchlist = (personalization.watchlists as Array<Record<string, unknown>> | undefined) || [];
                  const history = (personalization.private_history as Array<Record<string, unknown>> | undefined) || [];
                  return <>
                    <div className={styles.experienceActions}><button onClick={() => void runExperience("entertainment_continue_prepare")}><RefreshCw size={15} /> Prepare continue watching</button></div>
                    {latest && <article className={styles.entertainmentRoute}><small>{String(latest.provider || "provider")} · {String(latest.status || "prepared").replaceAll("_", " ")}</small><strong>{String(latest.title || "Entertainment route")}</strong><span>Entitlement: {String(latest.entitlement || "unknown")}</span><span>Provider open: {latest.provider_open_verified ? "verified" : "not verified"} · playback: {latest.playback_verified ? "verified" : "not verified"}</span>{latest.status === "awaiting_private_confirmation" && <button onClick={() => void runExperience("entertainment_continue_confirm", { execution_id: latest.execution_id })}>Approve exact provider route</button>}{latest.status === "approved_for_device_attempt" && <button onClick={() => void runExperience("entertainment_continue_execute", { execution_id: latest.execution_id })}>Open approved route on TV</button>}</article>}
                    <form className={styles.entertainmentForm} onSubmit={(event) => { event.preventDefault(); void runExperience("entertainment_remember", { title: entertainmentTitle, outcome: entertainmentOutcome }); setEntertainmentTitle(""); }}><strong>Remember privately</strong><input value={entertainmentTitle} onChange={(event) => setEntertainmentTitle(event.target.value)} placeholder="Film or series title" required /><select value={entertainmentOutcome} onChange={(event) => setEntertainmentOutcome(event.target.value)}><option value="watched">Watched</option><option value="liked">Liked</option><option value="disliked">Disliked</option><option value="avoid">Do not recommend</option></select><button type="submit">Save private preference</button></form>
                    <div className={styles.learningProgress}><span><b>{watchlist.length}</b> watchlist</span><span><b>{history.length}</b> remembered</span><span><b>{executionSnapshot.count ? Number(executionSnapshot.count) : 0}</b> routes</span></div>
                  </>;
                })()}
                <p className={styles.communicationStatus}>{experienceStatus}</p>
              </section>
            )}

            {activeNav === "Pilot" && mode === "personal" && selectedShortcut === "Files" && connection && (
              <section className={`${styles.liveInbox} ${styles.communicationPanel} ${styles.libraryPanel}`} aria-label="Private files, saved items and continuations">
                <div><Bookmark size={17} /><strong>Files &amp; saved items</strong><span>private</span></div>
                <p>Open encrypted files, claim something saved from the television, or continue it on this phone. Research never inherits permission to buy, book, send, or change an account.</p>
                {(() => {
                  const messages = (liveInbox?.messages as Array<Record<string, unknown>> | undefined) || [];
                  const attachments: Array<Record<string, unknown>> = messages.flatMap((message) => ((message.attachments as Array<Record<string, unknown>> | undefined) || []).map((attachment) => ({ ...attachment, message_id: message.message_id }) as Record<string, unknown>));
                  return <>
                    <h3>Private files</h3>
                    {attachments.length === 0 && <p>No encrypted files have been shared with this person yet.</p>}
                    <div className={styles.libraryGrid}>{attachments.slice(-12).reverse().map((attachment) => <article key={String(attachment.attachment_id)}>
                      <small>{String(attachment.media_type || "file")} · encrypted</small>
                      <strong>{String(attachment.filename || "Private file")}</strong>
                      <span>{Number(attachment.size_bytes || 0).toLocaleString()} bytes</span>
                      <button className={styles.libraryPrimary} onClick={() => void downloadAttachment(attachment)}><Download size={14} /> Open verified file</button>
                    </article>)}</div>
                  </>;
                })()}
                {(() => {
                  const pending = personalLibrary?.pending as Record<string, unknown> | null | undefined;
                  if (!pending || pending.status !== "awaiting_private_claim") return null;
                  return <><h3>Waiting from the television</h3><article className={styles.libraryPending}>
                    <small>{String(pending.category || "item")} · claim expires</small>
                    <strong>{String(pending.title || "Saved from television")}</strong>
                    <p>{String(pending.detail || "Review this item privately before saving it.")}</p>
                    <span>{new Date(String(pending.expires_at)).toLocaleString()}</span>
                    <button className={styles.libraryPrimary} onClick={() => void claimLibraryItem(String(pending.save_id || ""))}><Bookmark size={14} /> Save to me</button>
                  </article></>;
                })()}
                <h3>My saved items</h3>
                {((personalLibrary?.saved as Array<Record<string, unknown>> | undefined) || []).length === 0 && <p>Your private saved-item library is clear.</p>}
                <div className={styles.libraryGrid}>{((personalLibrary?.saved as Array<Record<string, unknown>> | undefined) || []).slice(-20).reverse().map((item) => {
                  const category = String(item.category || "idea");
                  const actions: Array<["research" | "shortlist" | "task" | "shopping" | "trip" | "playlist" | "learning", string]> = [
                    ["research", "Research"], ["shortlist", "Shortlist"], ["task", "Make task"], ["learning", "Learn"],
                  ];
                  if (category === "product") actions.push(["shopping", "Prepare shopping"]);
                  if (category === "destination") actions.push(["trip", "Plan trip"]);
                  if (category === "music") actions.push(["playlist", "Prepare playlist"]);
                  return <article key={String(item.save_id)}>
                    <small>{category} · {Math.round(Number(item.confidence || 0) * 100)}% source confidence</small>
                    <strong>{String(item.title || "Saved item")}</strong>
                    <p>{String(item.detail || "")}</p>
                    <div className={styles.libraryActions}>{actions.map(([action, label]) => <button key={action} onClick={() => void continueLibraryItem(String(item.save_id || ""), action)}>{label}</button>)}</div>
                    <button className={styles.libraryDelete} onClick={() => void removeLibraryItem(item)}><Trash2 size={13} /> Remove</button>
                  </article>;
                })}</div>
                {((personalLibrary?.followthrough as Array<Record<string, unknown>> | undefined) || []).length > 0 && <h3>Prepared continuations</h3>}
                <div className={styles.libraryGrid}>{((personalLibrary?.followthrough as Array<Record<string, unknown>> | undefined) || []).slice(-12).reverse().map((item) => {
                  const scope = (item.exact_scope as Record<string, unknown> | undefined) || {};
                  const proposal = (item.service_proposal as Record<string, unknown> | undefined) || null;
                  return <article key={String(item.followthrough_id)}>
                    <small>{String(item.kind || "continuation")} · {String(item.status || "prepared").replaceAll("_", " ")}</small>
                    <strong>{String(item.title || "Saved-item continuation")}</strong>
                    {Boolean(item.answer) && <p>{String(item.answer)}</p>}
                    {Object.entries(scope).slice(0, 6).map(([key, value]) => <span key={key}>{key.replaceAll("_", " ")}: {Array.isArray(value) ? value.join(", ") : String(value)}</span>)}
                    {((item.items as Array<Record<string, unknown>> | undefined) || []).map((evidence) => Boolean(evidence.url) && <a key={String(evidence.url)} href={String(evidence.url)} target="_blank" rel="noreferrer"><ExternalLink size={13} /> {String(evidence.title || "Open evidence on phone")}</a>)}
                    {proposal && <div className={styles.libraryBoundary}><LockKeyhole size={13} /> Separate {String(proposal.service || "service")} proposal · {String(proposal.status || "awaiting approval").replaceAll("_", " ")}</div>}
                  </article>;
                })}</div>
                <p className={styles.communicationStatus}>{libraryStatus}</p>
              </section>
            )}

            {activeNav === "Pilot" && mode === "personal" && selectedShortcut === "Shopping" && connection && (
              <section className={`${styles.liveInbox} ${styles.communicationPanel}`} aria-label="Private shopping, booking and service actions">
                <div><ShoppingCart size={17} /><strong>Shopping &amp; services</strong><span>approval gated</span></div>
                <p>Prepare a purchase, booking, route or music request. Pilot never stores card details and cannot execute until this person approves the unchanged proposal.</p>
                <form className={styles.communicationForm} onSubmit={(event) => void prepareServiceAction(event)}>
                  <strong>Prepare—do not execute</strong>
                  <select value={serviceKind} onChange={(event) => { setServiceKind(event.target.value as typeof serviceKind); setServicePrimary(""); setServiceSecondary(""); }} aria-label="Service action type">
                    <option value="shopping">Shopping</option><option value="booking">Booking</option><option value="maps">Route</option><option value="music">Music</option>
                  </select>
                  <input value={servicePrimary} onChange={(event) => setServicePrimary(event.target.value)} placeholder={serviceKind === "shopping" ? "What do you want to find?" : serviceKind === "booking" ? "What do you want to book?" : serviceKind === "maps" ? "Destination" : "What do you want to hear?"} aria-label="Service request" required />
                  {serviceKind === "shopping" && <><input type="number" min="1" max="999" value={serviceQuantity} onChange={(event) => setServiceQuantity(event.target.value)} aria-label="Quantity" required /><input value={serviceSecondary} onChange={(event) => setServiceSecondary(event.target.value)} placeholder="Requirements or budget (optional, never card details)" aria-label="Shopping requirements" /></>}
                  {serviceKind === "booking" && <input type="datetime-local" value={serviceSecondary} onChange={(event) => setServiceSecondary(event.target.value)} aria-label="Booking date and time" required />}
                  {serviceKind === "maps" && <input value={serviceSecondary} onChange={(event) => setServiceSecondary(event.target.value)} placeholder="Route preference (optional)" aria-label="Route preference" />}
                  {serviceKind === "music" && <input value={serviceSecondary} onChange={(event) => setServiceSecondary(event.target.value)} placeholder="Room or playlist context (optional)" aria-label="Music context" />}
                  <button type="submit">Prepare exact proposal</button>
                </form>
                {((personalServices?.proposals as Array<Record<string, unknown>> | undefined) || []).slice(-8).reverse().map((proposal) => {
                  const status = String(proposal.status || "needs_details");
                  const parameters = (proposal.parameters as Record<string, unknown> | undefined) || {};
                  const missing = (proposal.missing_fields as string[] | undefined) || [];
                  return <article key={String(proposal.proposal_id)}>
                    <small>{String(proposal.service || "service")} · {status.replaceAll("_", " ")}</small>
                    <strong>{String(parameters.item || parameters.what || parameters.destination || parameters.request || proposal.action || "Private service action")}</strong>
                    {Object.entries(parameters).filter(([, value]) => value !== "" && value !== null).map(([key, value]) => <span key={key}>{key.replaceAll("_", " ")}: {String(value)}</span>)}
                    {status === "needs_details" && <div className={styles.serviceDetails}>
                      {missing.map((field) => <input key={field} value={serviceDetails[`${String(proposal.proposal_id)}:${field}`] || ""} onChange={(event) => setServiceDetails((current) => ({ ...current, [`${String(proposal.proposal_id)}:${field}`]: event.target.value }))} placeholder={field.replaceAll("_", " ")} aria-label={`Missing ${field}`} />)}
                      <button onClick={() => void completeServiceDetails(proposal)}>Save private details</button>
                    </div>}
                    {status === "awaiting_private_approval" && <div className={styles.taskActions}><button className={styles.acceptTask} onClick={() => void decideServiceAction(proposal, true)}>Approve exact proposal</button><button onClick={() => void decideServiceAction(proposal, false)}>Reject</button></div>}
                    {status === "approved_pending_adapter" && <div className={styles.taskActions}><button className={styles.acceptTask} onClick={() => void executeServiceAction(proposal)}>Execute approved action</button></div>}
                    {status === "executed" && <i className={`${styles.state} ${styles.state_verified}`}>verified</i>}
                  </article>;
                })}
                {((personalServices?.receipts as Array<Record<string, unknown>> | undefined) || []).length > 0 && <h3>Verified service receipts</h3>}
                {((personalServices?.receipts as Array<Record<string, unknown>> | undefined) || []).slice(-5).reverse().map((receipt) => <article key={String(receipt.receipt_id)}><small>{String(receipt.service)} · verified</small><strong>Provider result recorded</strong><span>{String(receipt.external_reference || "Verified without exposing provider data")}</span></article>)}
                <p className={styles.communicationStatus}>{serviceStatus}</p>
              </section>
            )}

            {activeNav === "Pilot" && mode === "personal" && !["Calendar", "Contacts", "Messages", "Shopping", "Files", "Devices", "TV", "Learning", "Games", "Entertainment", "Memory", "Guardian"].includes(selectedShortcut || "") && connection && personalPilot && (() => {
              const summary = (personalPilot.summary as Record<string, unknown> | undefined) || {};
              const tasks = (personalPilot.tasks as Array<Record<string, unknown>> | undefined) || [];
              const reminders = (personalPilot.reminders as Array<Record<string, unknown>> | undefined) || [];
              const children = (personalPilot.guardian_controlled_children as Array<Record<string, unknown>> | undefined) || [];
              return <section className={styles.liveInbox} aria-label="Live Personal Pilot">
                <div><ShieldCheck size={17} /><strong>Your Personal Pilot</strong><span>private</span></div>
                <div className={styles.personalSummary}>
                  <span><b>{Number(summary.open_tasks || 0)}</b> open tasks</span>
                  <span><b>{Number(summary.due_reminders || 0)}</b> reminders due</span>
                  <span><b>{Number(summary.contacts || 0)}</b> contacts</span>
                </div>
                {tasks.slice(-3).reverse().map((task) => <article key={String(task.task_id)}>
                  <small>task · {String(task.status || "open").replaceAll("_", " ")}</small>
                  <strong>{String(task.title || "Private task")}</strong>
                </article>)}
                <form className={styles.reminderForm} onSubmit={(event) => void createReminder(event)}>
                  <strong>Add a reminder</strong>
                  <select value={reminderTask} onChange={(event) => setReminderTask(event.target.value)} aria-label="Task to remind me about" required>
                    <option value="">Choose a task</option>
                    {tasks.filter((task) => !["completed", "cancelled", "declined"].includes(String(task.status))).map((task) => <option key={String(task.task_id)} value={String(task.task_id)}>{String(task.title)}</option>)}
                  </select>
                  <select value={reminderTrigger} onChange={(event) => setReminderTrigger(event.target.value as typeof reminderTrigger)} aria-label="Reminder trigger">
                    <option value="time">At a time</option><option value="arrival">When I arrive</option><option value="departure">When I leave</option><option value="journey">During a journey</option><option value="closing_time">Before closing time</option>
                  </select>
                  {["time", "journey", "closing_time"].includes(reminderTrigger) && <input type="datetime-local" value={reminderAt} onChange={(event) => setReminderAt(event.target.value)} aria-label="Reminder time" required />}
                  {["arrival", "departure", "journey"].includes(reminderTrigger) && <input value={reminderLocation} onChange={(event) => setReminderLocation(event.target.value)} placeholder="Location label" aria-label="Reminder location" required />}
                  {["time", "closing_time"].includes(reminderTrigger) && <select value={reminderRepeat} onChange={(event) => setReminderRepeat(event.target.value)} aria-label="Repeat reminder"><option value="none">Once</option><option value="daily">Every day</option><option value="weekly">Every week</option><option value="weekdays">Weekdays</option></select>}
                  <button type="submit">Schedule reminder</button>
                </form>
                {reminders.slice(-5).reverse().map((reminder) => <article key={String(reminder.reminder_id)}>
                  <small>{String(reminder.trigger || "time").replaceAll("_", " ")} reminder</small>
                  <strong>{String(tasks.find((task) => task.task_id === reminder.task_id)?.title || "Private reminder")}</strong>
                  <span>{String(reminder.status || "scheduled")}</span>
                  {!['completed', 'cancelled'].includes(String(reminder.status)) && <div className={styles.taskActions}><button onClick={() => void updateReminder(String(reminder.reminder_id), "snooze")}>Snooze</button><button onClick={() => void updateReminder(String(reminder.reminder_id), "complete")}>Done</button><button onClick={() => void updateReminder(String(reminder.reminder_id), "cancel")}>Cancel</button></div>}
                </article>)}
                {children.length > 0 && <p>Guardian profiles: {children.map((child) => String(child.display_name)).join(", ")}</p>}
              </section>;
            })()}

            {activeNav === "Inbox" && connection && liveInbox && (
              <section className={styles.liveInbox} aria-label="Live private Inbox">
                <div><Radio size={17} /><strong>Live from your Pilot</strong><span>{liveState === "live" ? `${liveRoute} · live` : liveState}</span></div>
                <details className={styles.handoffComposer}>
                  <summary><Send size={15} /> Send to a trusted Pilot</summary>
                  <form className={styles.communicationForm} onSubmit={(event) => void sendTrustedHandoff(event)}>
                    <select value={handoffRelationship} onChange={(event) => setHandoffRelationship(event.target.value)} aria-label="Trusted Pilot recipient" required>
                      <option value="">Choose a trusted relationship</option>
                      {((trustedHandoffs?.relationships as Array<Record<string, unknown>> | undefined) || []).map((relationship) => {
                        const peer = String(relationship.peer_persona_id || "");
                        const contact = personalContacts.find((item) => item.pilot_persona_id === peer);
                        return <option key={String(relationship.relationship_id)} value={String(relationship.relationship_id)}>{String(contact?.display_name || peer)} · {String(relationship.scope || "contact")}</option>;
                      })}
                    </select>
                    <select value={handoffType} onChange={(event) => setHandoffType(event.target.value as typeof handoffType)} aria-label="Handoff type">
                      <option value="message">Message</option><option value="task">Task</option><option value="reminder">Reminder</option><option value="file">File</option><option value="moment">Moment</option>
                    </select>
                    {["task", "reminder", "moment"].includes(handoffType) && <input value={handoffTitle} onChange={(event) => setHandoffTitle(event.target.value)} placeholder={handoffType === "moment" ? "Moment title" : "What needs doing?"} aria-label="Handoff title" required />}
                    {["message", "reminder", "moment"].includes(handoffType) && <textarea value={handoffDetail} onChange={(event) => setHandoffDetail(event.target.value)} placeholder={handoffType === "message" ? "Write the exact private message" : "Optional context"} aria-label="Handoff detail" required={handoffType === "message"} />}
                    {handoffType === "reminder" && <input type="datetime-local" value={handoffDue} onChange={(event) => setHandoffDue(event.target.value)} aria-label="Reminder due time" required />}
                    {handoffType === "file" && <input type="file" onChange={(event) => setHandoffFile(event.target.files?.[0] || null)} aria-label="Private file" required />}
                    {handoffType === "moment" && <>
                      <input value={handoffMomentId} onChange={(event) => setHandoffMomentId(event.target.value)} placeholder="Prepared Moment ID" aria-label="Prepared Moment ID" required />
                      <input value={handoffContextHash} onChange={(event) => setHandoffContextHash(event.target.value)} placeholder="Verified context hash" aria-label="Moment context hash" required />
                      <input value={handoffProviderUrl} onChange={(event) => setHandoffProviderUrl(event.target.value)} placeholder="Official HTTPS link (optional)" aria-label="Official Moment provider link" inputMode="url" />
                      <small>Pilot sends a signed context card and official link—never protected programme audio or video.</small>
                    </>}
                    <button type="submit">{handoffType === "task" ? "Prepare task" : `Encrypt ${handoffType}`}</button>
                  </form>
                  {((trustedHandoffs?.relationships as unknown[] | undefined)?.length || 0) === 0 && <p>No active Pilot relationship is available. Accept a useful invitation and save that person's Pilot route first.</p>}
                  {pendingTrustedTask && <article className={styles.structuredCard}>
                    <small>task · awaiting your second signed approval</small>
                    <strong>{String(pendingTrustedTask.title || "Private task")}</strong>
                    <button className={styles.acceptTask} onClick={() => void approveTrustedTask()}>Approve exact task</button>
                  </article>}
                </details>
                <form className={styles.inboxSearch} onSubmit={(event) => void searchInbox(event)}>
                  <label><Search size={16} /><input value={inboxQuery} onChange={(event) => setInboxQuery(event.target.value)} placeholder="Search messages, tasks and files" aria-label="Search private Inbox" /></label>
                  <button type="submit">Search</button>
                </form>
                <div className={styles.inboxFilters} aria-label="Inbox filters">
                  {(["all", "messages", "tasks", "files"] as const).map((kind) => <button key={kind} className={inboxKind === kind ? styles.filterActive : ""} onClick={() => { setInboxKind(kind); setInboxResults(null); }}>{kind}</button>)}
                </div>
                {(inboxResults || [...((liveInbox.messages as Array<Record<string, unknown>> | undefined) || []), ...((liveInbox.actions as Array<Record<string, unknown>> | undefined) || [])].slice(-20).reverse()).map((item, index) => {
                  const personaId = String(connection.certificate.persona_id || "");
                  const isTask = Boolean(item.action_id);
                  const attachments = (item.attachments as Array<Record<string, unknown>> | undefined) || [];
                  const structuredCard = (item.card as Record<string, unknown> | undefined) || null;
                  const isSender = item.owner_persona_id === personaId;
                  const isRecipient = item.recipient_persona_id === personaId;
                  const status = String(item.status || "received");
                  return (
                    <article key={String(item.message_id || item.action_id || index)}>
                      <small>{String(item.kind || "message").replaceAll("_", " ")}</small>
                      <strong>{String(structuredCard?.title || item.body || item.title || "Private item")}</strong>
                      <span>{status.replaceAll("_", " ")}</span>
                      {structuredCard && <div className={styles.structuredCard}>
                        <b>{String(structuredCard.card_type || "item").replaceAll("_", " ")}</b>
                        {Boolean(structuredCard.detail) && <p>{String(structuredCard.detail)}</p>}
                        <small>{String(structuredCard.due_at || structuredCard.starts_at || "Ready to review")}</small>
                      </div>}
                      {attachments.map((attachment) => {
                        const isVoice = String(attachment.media_type || "").startsWith("audio/");
                        return <button className={styles.attachmentButton} key={String(attachment.attachment_id)} onClick={() => void (isVoice ? playVoiceNote(attachment) : downloadAttachment(attachment))}><Paperclip size={14} /><span>{isVoice ? `Voice note · ${Math.max(1, Math.round(Number(attachment.duration_ms || 0) / 1000))}s` : String(attachment.filename || "Attachment")}</span>{isVoice ? <Mic size={14} /> : <Download size={14} />}</button>;
                      })}
                      {isTask && <div className={styles.taskActions}>
                        {isRecipient && status === "awaiting_recipient_acceptance" && <>
                          {!item.read_at && <button onClick={() => void updateTask(item, "read")}>Mark read</button>}
                          <button className={styles.acceptTask} onClick={() => void updateTask(item, "accepted")}>Accept</button>
                          <button onClick={() => void updateTask(item, "declined")}>Decline</button>
                        </>}
                        {isRecipient && ["accepted", "snoozed"].includes(status) && <>
                          <button className={styles.acceptTask} onClick={() => void updateTask(item, "completed")}>Complete</button>
                          <button onClick={() => void updateTask(item, "snoozed")}>Snooze 1 hour</button>
                        </>}
                        {isSender && !["completed", "cancelled", "declined", "expired", "failed"].includes(status) && <>
                          <button onClick={() => void updateTask(item, "corrected")}>Correct</button>
                          <button onClick={() => void updateTask(item, "cancelled")}>Cancel</button>
                        </>}
                      </div>}
                      {!isTask && Boolean(item.sender_mother_id) && Boolean(item.recipient_mother_id) && <button
                        className={`${styles.voiceReply} ${recordingFor === String(item.message_id) ? styles.voiceReplyActive : ""}`}
                        onPointerDown={(event) => { event.preventDefault(); void startVoiceReply(item); }}
                        onPointerUp={(event) => { event.preventDefault(); stopVoiceReply(); }}
                        onPointerCancel={stopVoiceReply}
                        onPointerLeave={() => { if (recordingFor === String(item.message_id)) stopVoiceReply(); }}
                      ><Mic size={14} />{recordingFor === String(item.message_id) ? "Release to send" : "Hold to reply"}</button>}
                    </article>
                  );
                })}
                {inboxResults?.length === 0 && <p>No private items match that search.</p>}
                {((liveInbox.messages as unknown[] | undefined)?.length || 0) + ((liveInbox.actions as unknown[] | undefined)?.length || 0) === 0 && <p>Your private Inbox is connected and clear.</p>}
              </section>
            )}

            {activeNav === "Inbox" && !connection && (
              <section className={styles.previewBanner}><LockKeyhole size={17} /><span>Connect this phone under <strong>Me</strong> to replace preview cards with your live private Inbox.</span></section>
            )}

            {((activeNav === "Pilot" && !selectedShortcut) || activeNav === "Actions") && <div className={styles.cardGrid}>
              {manifest.cards.map((cardType) => {
                const card = cardContent[cardType] || { title: `${cardType} ready`, detail: "Open to review", state: "pending" };
                return (
                  <article className={styles.smallCard} key={cardType}>
                    <div><Radio size={17} /><span>{cardType}</span><i className={`${styles.state} ${styles[`state_${card.state}`]}`}>{card.state}</i></div>
                    <strong>{card.title}</strong>
                    <small>{cardType === "receipt" ? `${fixture.device.label} · ${fixture.device.status}` : card.detail}</small>
                  </article>
                );
              })}
            </div>}

            {activeNav === "Actions" && (
              <div className={styles.stateGallery} aria-label="Action state examples">
                <strong>Action states</strong>
                <div>{stateExamples.map((state) => <span className={`${styles.state} ${styles[`state_${state}`]}`} key={state}>{state}</span>)}</div>
              </div>
            )}

            <div className={styles.privacyNotice}>
              <LockKeyhole size={15} />
              <span>{notice}</span>
            </div>
          </section>

          <div className={styles.composerDock}>
            <form className={styles.composer} onSubmit={submit}>
              <button type="button" aria-label="Attach camera evidence"><Camera size={20} /></button>
              <input value={draft} onChange={(event) => setDraft(event.target.value)} placeholder={modeCopy[mode].prompt} aria-label="Ask Pilot" />
              {draft ? (
                <button type="submit" className={styles.send} aria-label="Send to Pilot"><Send size={19} /></button>
              ) : (
                <button
                  type="button"
                  className={listening ? styles.listening : styles.mic}
                  aria-label="Hold to speak to Pilot"
                  onPointerDown={() => setListening(true)}
                  onPointerUp={() => setListening(false)}
                  onPointerLeave={() => setListening(false)}
                ><Mic size={20} /></button>
              )}
            </form>
            <nav className={styles.bottomNav} aria-label="Primary navigation">
              {[
                ["Pilot", Sparkles],
                ["Inbox", Inbox],
                ["Actions", Check],
                ["Spaces", LayoutGrid],
                ["Me", CircleUserRound],
              ].map(([label, Icon]) => (
                <button key={label as string} className={activeNav === label ? styles.navActive : ""} onClick={() => { setActiveNav(label as string); if (label !== "Pilot") setSelectedShortcut(null); }}>
                  <Icon size={20} /><span>{label as string}</span>
                </button>
              ))}
            </nav>
          </div>
        </main>
      </div>
    </>
  );
};

export const getStaticProps: GetStaticProps<PageProps> = async () => {
  return { props: { fixture: pilotFixture as Fixture } };
};

export default PilotMobile;
