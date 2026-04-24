import React, { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import Navbar from "../components/Navbar";
import {
  fetchDeals,
  fetchDealTemplates,
  createDealTemplate,
  fetchDealApprovals,
  requestDealApproval,
  decideDealApproval,
  fetchNegotiations,
  createNegotiationEntry,
  fetchDealMilestones,
  createDealMilestone,
  updateMilestoneAction,
  fetchEscrowState,
  fetchDealDisputes,
  openDealDispute,
  resolveDealDispute,
  createWorkspace,
  fetchWorkspaces,
  fetchWorkspace,
  inviteWorkspaceMember,
  addWorkspaceResource,
  fetchWorkspaceResources,
  generateMyNudges,
  fetchMyNudges,
  updateNudgeState,
  fetchROIReport,
  fetchCampaignOutcomes,
  fetchMonthlyExecutiveReport,
  fetchReportSnapshots,
  fetchIntegrations,
  connectIntegration,
  disconnectIntegration,
  syncIntegration,
  fetchIntegrationEvents,
  sendIntegrationTestAlert,
  exportCampaignOutcomesCsvUrl,
  exportSheetsCsvUrl,
  exportCalendarIcsUrl,
  fetchOpsMetrics,
  fetchOpsAuditEvents,
  fetchOpsPlanDistribution,
  fetchPendingKycSubmissions,
  reviewKycSubmission,
} from "../services/api";
import { formatCurrency } from "../utils/formatCurrency";
import "./ScaleOpsPage.css";

const BASE_TABS = [
  { id: "proposal", label: "Proposal Tools" },
  { id: "revenue", label: "Revenue Confidence" },
  { id: "collab", label: "Team Collaboration" },
  { id: "retention", label: "Retention Engine" },
  { id: "reports", label: "Reporting" },
  { id: "integrations", label: "Integrations" },
];

const INTEGRATION_PROVIDERS = ["hubspot", "sheets", "slack", "email", "calendar"];

const ScaleOpsPage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const currentUser = useMemo(() => JSON.parse(localStorage.getItem("currentUser") || "{}"), []);
  const isAdmin = String(currentUser.role || "").toLowerCase() === "admin";
  const tabs = useMemo(
    () => (isAdmin ? [...BASE_TABS, { id: "admin", label: "Admin Ops" }] : BASE_TABS),
    [isAdmin]
  );
  const allowedTabIds = useMemo(() => tabs.map((tab) => tab.id), [tabs]);
  const [activeTab, setActiveTab] = useState("proposal");
  const [loading, setLoading] = useState(false);

  const [deals, setDeals] = useState([]);
  const [selectedDealId, setSelectedDealId] = useState("");

  const [templates, setTemplates] = useState([]);
  const [approvals, setApprovals] = useState([]);
  const [negotiations, setNegotiations] = useState([]);

  const [milestones, setMilestones] = useState([]);
  const [escrow, setEscrow] = useState(null);
  const [disputes, setDisputes] = useState([]);

  const [workspaces, setWorkspaces] = useState([]);
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState("");
  const [workspaceDetail, setWorkspaceDetail] = useState(null);
  const [workspaceResources, setWorkspaceResources] = useState([]);

  const [nudges, setNudges] = useState([]);

  const [roi, setRoi] = useState(null);
  const [outcomes, setOutcomes] = useState([]);
  const [monthlyReport, setMonthlyReport] = useState(null);
  const [snapshots, setSnapshots] = useState([]);

  const [connections, setConnections] = useState([]);
  const [integrationEvents, setIntegrationEvents] = useState([]);
  const [selectedProvider, setSelectedProvider] = useState("hubspot");
  const [opsMetrics, setOpsMetrics] = useState(null);
  const [planDistribution, setPlanDistribution] = useState(null);
  const [auditEvents, setAuditEvents] = useState([]);
  const [auditActionFilter, setAuditActionFilter] = useState("");
  const [pendingKyc, setPendingKyc] = useState([]);
  const [adminLoading, setAdminLoading] = useState(false);
  const [kycReviewDrafts, setKycReviewDrafts] = useState({});

  const [templateForm, setTemplateForm] = useState({ name: "", description: "", deal_type: "sponsorship" });
  const [approvalForm, setApprovalForm] = useState({ approver_role: "manager", approver_user_id: "" });
  const [negotiationForm, setNegotiationForm] = useState({ change_type: "comment", message: "" });
  const [milestoneForm, setMilestoneForm] = useState({ title: "", amount: "", due_date: "" });
  const [disputeForm, setDisputeForm] = useState({ reason: "", details: "" });
  const [resolveForm, setResolveForm] = useState({ decision: "under_review", resolution_note: "", settlement_amount: "" });
  const [workspaceForm, setWorkspaceForm] = useState({ name: "" });
  const [memberInviteForm, setMemberInviteForm] = useState({ user_id: "", role: "viewer" });
  const [resourceForm, setResourceForm] = useState({ resource_type: "deal", resource_id: "" });
  const [integrationSyncPayload, setIntegrationSyncPayload] = useState("{}");

  const selectedDeal = useMemo(
    () => deals.find((d) => Number(d.id) === Number(selectedDealId)) || null,
    [deals, selectedDealId]
  );

  const selectedWorkspace = useMemo(
    () => workspaces.find((w) => Number(w.id) === Number(selectedWorkspaceId)) || null,
    [workspaces, selectedWorkspaceId]
  );

  const loadBaseData = async () => {
    setLoading(true);
    try {
      const [dealsResp, templatesResp, workspacesResp, nudgesResp, connResp] = await Promise.all([
        fetchDeals(),
        fetchDealTemplates(),
        fetchWorkspaces(),
        fetchMyNudges(),
        fetchIntegrations(),
      ]);

      const allDeals = dealsResp.data || [];
      setDeals(allDeals);
      if (!selectedDealId && allDeals.length > 0) {
        setSelectedDealId(String(allDeals[0].id));
      }
      setTemplates(templatesResp.data || []);

      const ws = workspacesResp.data || [];
      setWorkspaces(ws);
      if (!selectedWorkspaceId && ws.length > 0) {
        setSelectedWorkspaceId(String(ws[0].id));
      }

      setNudges(nudgesResp.data || []);
      setConnections(connResp.data || []);
    } catch {
      toast.error("Unable to load scale operations data");
    } finally {
      setLoading(false);
    }
  };

  const loadDealArtifacts = async (dealId) => {
    if (!dealId) return;
    try {
      const [approvalsResp, negotiationResp, milestonesResp, escrowResp, disputeResp] = await Promise.all([
        fetchDealApprovals(dealId),
        fetchNegotiations(dealId),
        fetchDealMilestones(dealId),
        fetchEscrowState(dealId),
        fetchDealDisputes(dealId),
      ]);
      setApprovals(approvalsResp.data || []);
      setNegotiations(negotiationResp.data || []);
      setMilestones(milestonesResp.data || []);
      setEscrow(escrowResp.data || null);
      setDisputes(disputeResp.data || []);
    } catch {
      setApprovals([]);
      setNegotiations([]);
      setMilestones([]);
      setEscrow(null);
      setDisputes([]);
    }
  };

  const loadWorkspaceArtifacts = async (workspaceId) => {
    if (!workspaceId) return;
    try {
      const [wsResp, resourcesResp] = await Promise.all([fetchWorkspace(workspaceId), fetchWorkspaceResources(workspaceId)]);
      setWorkspaceDetail(wsResp.data || null);
      setWorkspaceResources(resourcesResp.data || []);
    } catch {
      setWorkspaceDetail(null);
      setWorkspaceResources([]);
    }
  };

  const loadReports = async () => {
    try {
      const [roiResp, outcomesResp, monthlyResp, snapshotsResp] = await Promise.all([
        fetchROIReport(30),
        fetchCampaignOutcomes(),
        fetchMonthlyExecutiveReport(),
        fetchReportSnapshots(),
      ]);
      setRoi(roiResp.data || null);
      setOutcomes(outcomesResp.data || []);
      setMonthlyReport(monthlyResp.data || null);
      setSnapshots(snapshotsResp.data || []);
    } catch {
      toast.error("Unable to load reports");
    }
  };

  const loadProviderEvents = async (provider) => {
    try {
      const resp = await fetchIntegrationEvents(provider);
      setIntegrationEvents(resp.data || []);
    } catch {
      setIntegrationEvents([]);
    }
  };

  const loadAdminData = async (actionFilter = "") => {
    if (!isAdmin) return;
    setAdminLoading(true);
    try {
      const [metricsResp, planResp, auditResp, pendingResp] = await Promise.all([
        fetchOpsMetrics(),
        fetchOpsPlanDistribution(),
        fetchOpsAuditEvents({
          limit: 50,
          ...(actionFilter.trim() ? { action: actionFilter.trim() } : {}),
        }),
        fetchPendingKycSubmissions(),
      ]);
      setOpsMetrics(metricsResp.data || null);
      setPlanDistribution(planResp.data || null);
      setAuditEvents(auditResp.data || []);
      setPendingKyc(pendingResp.data || []);
    } catch {
      toast.error("Unable to load admin operations data");
      setOpsMetrics(null);
      setPlanDistribution(null);
      setAuditEvents([]);
      setPendingKyc([]);
    } finally {
      setAdminLoading(false);
    }
  };

  useEffect(() => {
    loadBaseData();
  }, []);

  useEffect(() => {
    const requestedTab = String(new URLSearchParams(location.search).get("tab") || "").toLowerCase();
    if (!requestedTab) return;
    if (allowedTabIds.includes(requestedTab)) {
      setActiveTab(requestedTab);
    }
  }, [location.search, allowedTabIds]);

  useEffect(() => {
    if (selectedDealId) {
      loadDealArtifacts(selectedDealId);
    }
  }, [selectedDealId]);

  useEffect(() => {
    if (selectedWorkspaceId) {
      loadWorkspaceArtifacts(selectedWorkspaceId);
    }
  }, [selectedWorkspaceId]);

  useEffect(() => {
    if (activeTab === "reports") {
      loadReports();
    }
    if (activeTab === "integrations") {
      loadProviderEvents(selectedProvider);
    }
    if (activeTab === "admin" && isAdmin) {
      loadAdminData(auditActionFilter);
    }
  }, [activeTab, selectedProvider, isAdmin]);

  useEffect(() => {
    if (activeTab === "admin" && !isAdmin) {
      setActiveTab("proposal");
      toast.error("Admin access required");
    }
  }, [activeTab, isAdmin]);

  const handleCreateTemplate = async (e) => {
    e.preventDefault();
    try {
      await createDealTemplate(templateForm);
      setTemplateForm({ name: "", description: "", deal_type: "sponsorship" });
      const resp = await fetchDealTemplates();
      setTemplates(resp.data || []);
      toast.success("Template created");
    } catch {
      toast.error("Template creation failed");
    }
  };

  const handleRequestApproval = async (e) => {
    e.preventDefault();
    if (!selectedDealId) return;
    try {
      await requestDealApproval(selectedDealId, {
        approver_role: approvalForm.approver_role,
        approver_user_id: approvalForm.approver_user_id ? Number(approvalForm.approver_user_id) : null,
      });
      setApprovalForm({ approver_role: "manager", approver_user_id: "" });
      loadDealArtifacts(selectedDealId);
      toast.success("Approval requested");
    } catch {
      toast.error("Failed to request approval");
    }
  };

  const handleApprovalDecision = async (approvalId, decision) => {
    try {
      await decideDealApproval(approvalId, { decision });
      loadDealArtifacts(selectedDealId);
      toast.success(`Approval ${decision}`);
    } catch {
      toast.error("Unable to update approval");
    }
  };

  const handleAddNegotiation = async (e) => {
    e.preventDefault();
    if (!selectedDealId) return;
    if (!negotiationForm.message.trim()) {
      toast.error("Write a negotiation note");
      return;
    }
    try {
      await createNegotiationEntry(selectedDealId, negotiationForm);
      setNegotiationForm({ change_type: "comment", message: "" });
      loadDealArtifacts(selectedDealId);
      toast.success("Negotiation saved");
    } catch {
      toast.error("Unable to save negotiation");
    }
  };

  const handleAddMilestone = async (e) => {
    e.preventDefault();
    if (!selectedDealId) return;
    try {
      await createDealMilestone(selectedDealId, {
        title: milestoneForm.title,
        amount: Number(milestoneForm.amount || 0),
        due_date: milestoneForm.due_date || null,
      });
      setMilestoneForm({ title: "", amount: "", due_date: "" });
      loadDealArtifacts(selectedDealId);
      toast.success("Milestone added");
    } catch {
      toast.error("Unable to add milestone");
    }
  };

  const handleMilestoneAction = async (milestoneId, action) => {
    try {
      await updateMilestoneAction(milestoneId, action);
      loadDealArtifacts(selectedDealId);
      toast.success(`Milestone ${action}`);
    } catch {
      toast.error("Milestone action failed");
    }
  };

  const handleOpenDispute = async (e) => {
    e.preventDefault();
    if (!selectedDealId) return;
    try {
      await openDealDispute(selectedDealId, disputeForm);
      setDisputeForm({ reason: "", details: "" });
      loadDealArtifacts(selectedDealId);
      toast.success("Dispute opened");
    } catch {
      toast.error("Unable to open dispute");
    }
  };

  const handleResolveDispute = async (disputeId) => {
    try {
      await resolveDealDispute(disputeId, {
        decision: resolveForm.decision,
        resolution_note: resolveForm.resolution_note || null,
        settlement_amount: resolveForm.settlement_amount ? Number(resolveForm.settlement_amount) : null,
      });
      loadDealArtifacts(selectedDealId);
      toast.success("Dispute updated");
    } catch {
      toast.error("Unable to update dispute");
    }
  };

  const handleCreateWorkspace = async (e) => {
    e.preventDefault();
    if (!workspaceForm.name.trim()) return;
    try {
      await createWorkspace({ name: workspaceForm.name.trim() });
      setWorkspaceForm({ name: "" });
      const resp = await fetchWorkspaces();
      const next = resp.data || [];
      setWorkspaces(next);
      if (next.length > 0) setSelectedWorkspaceId(String(next[0].id));
      toast.success("Workspace created");
    } catch {
      toast.error("Unable to create workspace");
    }
  };

  const handleInviteMember = async (e) => {
    e.preventDefault();
    if (!selectedWorkspaceId) return;
    try {
      await inviteWorkspaceMember(selectedWorkspaceId, {
        user_id: Number(memberInviteForm.user_id),
        role: memberInviteForm.role,
      });
      setMemberInviteForm({ user_id: "", role: "viewer" });
      loadWorkspaceArtifacts(selectedWorkspaceId);
      toast.success("Member invited");
    } catch {
      toast.error("Unable to invite member");
    }
  };

  const handleAddResource = async (e) => {
    e.preventDefault();
    if (!selectedWorkspaceId) return;
    try {
      await addWorkspaceResource(selectedWorkspaceId, {
        resource_type: resourceForm.resource_type,
        resource_id: Number(resourceForm.resource_id),
      });
      setResourceForm({ resource_type: "deal", resource_id: "" });
      loadWorkspaceArtifacts(selectedWorkspaceId);
      toast.success("Resource linked");
    } catch {
      toast.error("Unable to add resource");
    }
  };

  const handleGenerateNudges = async () => {
    try {
      await generateMyNudges();
      const resp = await fetchMyNudges();
      setNudges(resp.data || []);
      toast.success("Nudges refreshed");
    } catch {
      toast.error("Unable to generate nudges");
    }
  };

  const handleNudgeState = async (nudgeId, state) => {
    try {
      await updateNudgeState(nudgeId, state);
      const resp = await fetchMyNudges();
      setNudges(resp.data || []);
    } catch {
      toast.error("Unable to update nudge");
    }
  };

  const handleConnectProvider = async (provider) => {
    try {
      await connectIntegration(provider, {});
      const resp = await fetchIntegrations();
      setConnections(resp.data || []);
      toast.success(`${provider} connected`);
    } catch {
      toast.error(`Failed to connect ${provider}`);
    }
  };

  const handleDisconnectProvider = async (provider) => {
    try {
      await disconnectIntegration(provider);
      const resp = await fetchIntegrations();
      setConnections(resp.data || []);
      toast.success(`${provider} disconnected`);
    } catch {
      toast.error(`Failed to disconnect ${provider}`);
    }
  };

  const handleSyncProvider = async () => {
    try {
      const parsed = JSON.parse(integrationSyncPayload || "{}");
      await syncIntegration(selectedProvider, "manual_sync", parsed);
      loadProviderEvents(selectedProvider);
      const connResp = await fetchIntegrations();
      setConnections(connResp.data || []);
      toast.success(`${selectedProvider} sync complete`);
    } catch {
      toast.error("Sync payload must be valid JSON");
    }
  };

  const handleSendTestAlert = async (provider) => {
    try {
      await sendIntegrationTestAlert(provider, { message: "Lifecycle alert test from Scale Ops Hub" });
      loadProviderEvents(provider);
      toast.success("Test alert sent");
    } catch {
      toast.error("Test alert failed");
    }
  };

  const handleRefreshAdmin = async () => {
    await loadAdminData(auditActionFilter);
  };

  const handleKycDraftChange = (submissionId, field, value) => {
    setKycReviewDrafts((prev) => ({
      ...prev,
      [submissionId]: {
        ...(prev[submissionId] || {}),
        [field]: value,
      },
    }));
  };

  const handleReviewKyc = async (submissionId, decision) => {
    const draft = kycReviewDrafts[submissionId] || {};
    const rawRiskScore = String(draft.riskScore || "").trim();
    const rawFlags = String(draft.riskFlags || "").trim();
    const reviewNote = String(draft.reviewNote || "").trim();

    try {
      await reviewKycSubmission(submissionId, {
        decision,
        review_note: reviewNote || null,
        risk_score: rawRiskScore ? Number(rawRiskScore) : null,
        risk_flags: rawFlags
          ? rawFlags.split(",").map((f) => f.trim()).filter(Boolean)
          : null,
      });
      toast.success(`KYC ${decision}`);
      await loadAdminData(auditActionFilter);
    } catch (err) {
      const msg = err?.response?.data?.message || err?.response?.data?.detail || "KYC review failed";
      toast.error(msg);
    }
  };

  return (
    <div>
      <Navbar role={currentUser.role || "sponsor"} />
      <main className="scale-ops-page">
        <header className="scale-ops-header">
          <div>
            <h1>Scale Operations Hub</h1>
            <p>Feature set 4-10 in one command center for proposal quality, revenue confidence, and growth operations.</p>
          </div>
          <div className="scale-ops-header-actions">
            <button type="button" className="ghost-btn" onClick={() => navigate(-1)}>Back</button>
            <button type="button" onClick={loadBaseData} disabled={loading}>
              {loading ? "Refreshing..." : "Refresh Data"}
            </button>
          </div>
        </header>

        <div className="scale-ops-tab-row">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              type="button"
              className={activeTab === tab.id ? "active" : ""}
              onClick={() => setActiveTab(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <section className="scale-ops-card">
          <label className="field-label">Selected Deal</label>
          <select value={selectedDealId} onChange={(e) => setSelectedDealId(e.target.value)}>
            <option value="">Select a deal</option>
            {deals.map((deal) => (
              <option key={deal.id} value={deal.id}>
                #{deal.id} - {deal.deal_type} - {deal.status}
              </option>
            ))}
          </select>
          {selectedDeal && (
            <p className="muted-line">
              Participants: Sponsor {selectedDeal.sponsor_id || "-"}, Organizer {selectedDeal.organizer_id || "-"},
              Influencer {selectedDeal.influencer_id || "-"}
            </p>
          )}
        </section>

        {activeTab === "proposal" && (
          <section className="scale-ops-grid two">
            <article className="scale-ops-card">
              <h3>Reusable Deal Templates</h3>
              <form onSubmit={handleCreateTemplate} className="form-grid">
                <input
                  placeholder="Template name"
                  value={templateForm.name}
                  onChange={(e) => setTemplateForm((p) => ({ ...p, name: e.target.value }))}
                  required
                />
                <select
                  value={templateForm.deal_type}
                  onChange={(e) => setTemplateForm((p) => ({ ...p, deal_type: e.target.value }))}
                >
                  <option value="sponsorship">sponsorship</option>
                  <option value="promotion">promotion</option>
                </select>
                <textarea
                  placeholder="Template notes / terms"
                  value={templateForm.description}
                  onChange={(e) => setTemplateForm((p) => ({ ...p, description: e.target.value }))}
                />
                <button type="submit">Save Template</button>
              </form>
              <div className="list-block">
                {templates.map((tpl) => (
                  <div key={tpl.id} className="line-item">
                    <div>
                      <strong>{tpl.name}</strong>
                      <p>{tpl.deal_type} {tpl.is_default ? "(default)" : ""}</p>
                    </div>
                  </div>
                ))}
                {templates.length === 0 && <p className="muted-line">No templates yet.</p>}
              </div>
            </article>

            <article className="scale-ops-card">
              <h3>Approval Flow</h3>
              <form onSubmit={handleRequestApproval} className="form-grid">
                <select
                  value={approvalForm.approver_role}
                  onChange={(e) => setApprovalForm((p) => ({ ...p, approver_role: e.target.value }))}
                >
                  <option value="owner">owner</option>
                  <option value="manager">manager</option>
                  <option value="finance">finance</option>
                  <option value="viewer">viewer</option>
                </select>
                <input
                  type="number"
                  placeholder="Approver user id (optional)"
                  value={approvalForm.approver_user_id}
                  onChange={(e) => setApprovalForm((p) => ({ ...p, approver_user_id: e.target.value }))}
                />
                <button type="submit" disabled={!selectedDealId}>Request Approval</button>
              </form>
              <div className="list-block">
                {approvals.map((approval) => (
                  <div key={approval.id} className="line-item">
                    <div>
                      <strong>{approval.approver_role}</strong>
                      <p>Status: {approval.status}</p>
                    </div>
                    {approval.status === "pending" && (
                      <div className="inline-actions">
                        <button type="button" onClick={() => handleApprovalDecision(approval.id, "approved")}>Approve</button>
                        <button type="button" className="danger" onClick={() => handleApprovalDecision(approval.id, "rejected")}>Reject</button>
                      </div>
                    )}
                  </div>
                ))}
                {approvals.length === 0 && <p className="muted-line">No approval requests yet.</p>}
              </div>
            </article>

            <article className="scale-ops-card full">
              <h3>Negotiation History</h3>
              <form onSubmit={handleAddNegotiation} className="form-grid inline">
                <select
                  value={negotiationForm.change_type}
                  onChange={(e) => setNegotiationForm((p) => ({ ...p, change_type: e.target.value }))}
                >
                  <option value="comment">comment</option>
                  <option value="counter_offer">counter_offer</option>
                  <option value="term_update">term_update</option>
                </select>
                <input
                  placeholder="Write negotiation note"
                  value={negotiationForm.message}
                  onChange={(e) => setNegotiationForm((p) => ({ ...p, message: e.target.value }))}
                />
                <button type="submit" disabled={!selectedDealId}>Add Entry</button>
              </form>
              <div className="list-block">
                {negotiations.map((entry) => (
                  <div key={entry.id} className="line-item">
                    <div>
                      <strong>{entry.change_type}</strong>
                      <p>{entry.message || "No message"}</p>
                    </div>
                    <span>{new Date(entry.created_at).toLocaleString()}</span>
                  </div>
                ))}
                {negotiations.length === 0 && <p className="muted-line">No negotiation entries yet.</p>}
              </div>
            </article>
          </section>
        )}

        {activeTab === "revenue" && (
          <section className="scale-ops-grid two">
            <article className="scale-ops-card">
              <h3>Escrow and Milestones</h3>
              <div className="metric-grid">
                <div>
                  <small>Escrow State</small>
                  <strong>{escrow?.escrow_state || "-"}</strong>
                </div>
                <div>
                  <small>Planned</small>
                  <strong>{formatCurrency(Number(escrow?.planned_total || 0), escrow?.currency || "INR")}</strong>
                </div>
                <div>
                  <small>Released</small>
                  <strong>{formatCurrency(Number(escrow?.released_total || 0), escrow?.currency || "INR")}</strong>
                </div>
              </div>
              <form onSubmit={handleAddMilestone} className="form-grid">
                <input
                  placeholder="Milestone title"
                  value={milestoneForm.title}
                  onChange={(e) => setMilestoneForm((p) => ({ ...p, title: e.target.value }))}
                  required
                />
                <input
                  type="number"
                  step="0.01"
                  placeholder="Amount"
                  value={milestoneForm.amount}
                  onChange={(e) => setMilestoneForm((p) => ({ ...p, amount: e.target.value }))}
                  required
                />
                <input
                  type="date"
                  value={milestoneForm.due_date}
                  onChange={(e) => setMilestoneForm((p) => ({ ...p, due_date: e.target.value }))}
                />
                <button type="submit" disabled={!selectedDealId}>Add Milestone</button>
              </form>
              <div className="list-block">
                {milestones.map((ms) => (
                  <div key={ms.id} className="line-item">
                    <div>
                      <strong>{ms.sequence_no}. {ms.title}</strong>
                      <p>{formatCurrency(Number(ms.amount || 0))} - {ms.status}</p>
                    </div>
                    <div className="inline-actions">
                      <button type="button" onClick={() => handleMilestoneAction(ms.id, "fund")}>Fund</button>
                      <button type="button" onClick={() => handleMilestoneAction(ms.id, "release")}>Release</button>
                      <button type="button" className="danger" onClick={() => handleMilestoneAction(ms.id, "mark_disputed")}>Dispute</button>
                    </div>
                  </div>
                ))}
                {milestones.length === 0 && <p className="muted-line">No milestones yet.</p>}
              </div>
            </article>

            <article className="scale-ops-card">
              <h3>Dispute Workflow</h3>
              <form onSubmit={handleOpenDispute} className="form-grid">
                <input
                  placeholder="Dispute reason"
                  value={disputeForm.reason}
                  onChange={(e) => setDisputeForm((p) => ({ ...p, reason: e.target.value }))}
                  required
                />
                <textarea
                  placeholder="Dispute details"
                  value={disputeForm.details}
                  onChange={(e) => setDisputeForm((p) => ({ ...p, details: e.target.value }))}
                />
                <button type="submit" disabled={!selectedDealId}>Open Dispute</button>
              </form>

              <div className="form-grid inline">
                <select
                  value={resolveForm.decision}
                  onChange={(e) => setResolveForm((p) => ({ ...p, decision: e.target.value }))}
                >
                  <option value="under_review">under_review</option>
                  <option value="resolved">resolved</option>
                  <option value="rejected">rejected</option>
                </select>
                <input
                  placeholder="Resolution note"
                  value={resolveForm.resolution_note}
                  onChange={(e) => setResolveForm((p) => ({ ...p, resolution_note: e.target.value }))}
                />
                <input
                  type="number"
                  step="0.01"
                  placeholder="Settlement amount (optional)"
                  value={resolveForm.settlement_amount}
                  onChange={(e) => setResolveForm((p) => ({ ...p, settlement_amount: e.target.value }))}
                />
              </div>

              <div className="list-block">
                {disputes.map((d) => (
                  <div key={d.id} className="line-item">
                    <div>
                      <strong>{d.reason}</strong>
                      <p>Status: {d.status}</p>
                    </div>
                    <button type="button" onClick={() => handleResolveDispute(d.id)}>Update</button>
                  </div>
                ))}
                {disputes.length === 0 && <p className="muted-line">No disputes on this deal.</p>}
              </div>
            </article>
          </section>
        )}

        {activeTab === "collab" && (
          <section className="scale-ops-grid two">
            <article className="scale-ops-card">
              <h3>Workspaces</h3>
              <form onSubmit={handleCreateWorkspace} className="form-grid inline">
                <input
                  placeholder="Workspace name"
                  value={workspaceForm.name}
                  onChange={(e) => setWorkspaceForm({ name: e.target.value })}
                  required
                />
                <button type="submit">Create Workspace</button>
              </form>
              <label className="field-label">Select Workspace</label>
              <select value={selectedWorkspaceId} onChange={(e) => setSelectedWorkspaceId(e.target.value)}>
                <option value="">Select workspace</option>
                {workspaces.map((ws) => (
                  <option key={ws.id} value={ws.id}>
                    {ws.name} (owner #{ws.owner_user_id})
                  </option>
                ))}
              </select>
              <div className="list-block">
                {workspaceDetail?.members?.map((member) => (
                  <div key={member.id} className="line-item">
                    <div>
                      <strong>User #{member.user_id}</strong>
                      <p>{member.role} - {member.status}</p>
                    </div>
                  </div>
                ))}
                {!workspaceDetail?.members?.length && <p className="muted-line">No members yet.</p>}
              </div>
            </article>

            <article className="scale-ops-card">
              <h3>Invite and Resource Linking</h3>
              <form onSubmit={handleInviteMember} className="form-grid">
                <input
                  type="number"
                  placeholder="User id"
                  value={memberInviteForm.user_id}
                  onChange={(e) => setMemberInviteForm((p) => ({ ...p, user_id: e.target.value }))}
                  required
                />
                <select
                  value={memberInviteForm.role}
                  onChange={(e) => setMemberInviteForm((p) => ({ ...p, role: e.target.value }))}
                >
                  <option value="viewer">viewer</option>
                  <option value="manager">manager</option>
                  <option value="finance">finance</option>
                  <option value="owner">owner</option>
                </select>
                <button type="submit" disabled={!selectedWorkspaceId}>Invite Member</button>
              </form>

              <form onSubmit={handleAddResource} className="form-grid">
                <select
                  value={resourceForm.resource_type}
                  onChange={(e) => setResourceForm((p) => ({ ...p, resource_type: e.target.value }))}
                >
                  <option value="deal">deal</option>
                  <option value="event">event</option>
                  <option value="campaign">campaign</option>
                  <option value="template">template</option>
                  <option value="report">report</option>
                </select>
                <input
                  type="number"
                  placeholder="Resource id"
                  value={resourceForm.resource_id}
                  onChange={(e) => setResourceForm((p) => ({ ...p, resource_id: e.target.value }))}
                  required
                />
                <button type="submit" disabled={!selectedWorkspaceId}>Add Resource</button>
              </form>

              <div className="list-block">
                {workspaceResources.map((resource) => (
                  <div key={resource.id} className="line-item">
                    <strong>{resource.resource_type} #{resource.resource_id}</strong>
                  </div>
                ))}
                {!workspaceResources.length && <p className="muted-line">No resources linked.</p>}
              </div>
            </article>
          </section>
        )}

        {activeTab === "retention" && (
          <section className="scale-ops-card">
            <div className="heading-row">
              <h3>Lifecycle Nudges</h3>
              <button type="button" onClick={handleGenerateNudges}>Generate Nudges</button>
            </div>
            <div className="list-block">
              {nudges.map((nudge) => (
                <div key={nudge.id} className="line-item">
                  <div>
                    <strong>{nudge.title}</strong>
                    <p>{nudge.message}</p>
                    <small>{nudge.nudge_type} - {nudge.state}</small>
                  </div>
                  <div className="inline-actions">
                    {nudge.state !== "done" && (
                      <button type="button" onClick={() => handleNudgeState(nudge.id, "done")}>Mark Done</button>
                    )}
                    {nudge.state !== "dismissed" && (
                      <button type="button" className="ghost-btn" onClick={() => handleNudgeState(nudge.id, "dismissed")}>Dismiss</button>
                    )}
                  </div>
                </div>
              ))}
              {nudges.length === 0 && <p className="muted-line">No nudges found. Generate from the button above.</p>}
            </div>
          </section>
        )}

        {activeTab === "reports" && (
          <section className="scale-ops-grid two">
            <article className="scale-ops-card">
              <h3>ROI Dashboard</h3>
              {roi ? (
                <div className="metric-grid">
                  <div><small>Total Deals</small><strong>{roi.total_deals}</strong></div>
                  <div><small>Closed Deals</small><strong>{roi.closed_deals}</strong></div>
                  <div><small>Conversion</small><strong>{roi.conversion_rate}%</strong></div>
                  <div><small>Total Value</small><strong>{formatCurrency(Number(roi.total_value || 0))}</strong></div>
                </div>
              ) : (
                <p className="muted-line">ROI unavailable.</p>
              )}
              <div className="inline-actions">
                <button type="button" onClick={loadReports}>Refresh Reports</button>
                <button type="button" onClick={() => window.open(exportCampaignOutcomesCsvUrl(), "_blank")}>Export Outcomes CSV</button>
              </div>
            </article>

            <article className="scale-ops-card">
              <h3>Monthly Executive Report</h3>
              {monthlyReport ? (
                <>
                  <p className="muted-line">Month: {monthlyReport.month} | Role: {monthlyReport.role}</p>
                  <div className="list-block">
                    {Object.entries(monthlyReport.kpis || {}).map(([k, v]) => (
                      <div key={k} className="line-item"><strong>{k}</strong><span>{String(v)}</span></div>
                    ))}
                  </div>
                  <div className="stacked-note">
                    <strong>Highlights</strong>
                    <ul>
                      {(monthlyReport.highlights || []).map((h, i) => <li key={i}>{h}</li>)}
                    </ul>
                  </div>
                  <div className="stacked-note">
                    <strong>Risks</strong>
                    <ul>
                      {(monthlyReport.risks || []).map((r, i) => <li key={i}>{r}</li>)}
                    </ul>
                  </div>
                </>
              ) : (
                <p className="muted-line">No executive report yet.</p>
              )}
            </article>

            <article className="scale-ops-card full">
              <h3>Campaign Outcomes and Report Snapshots</h3>
              <div className="list-block">
                {outcomes.map((row) => (
                  <div key={row.id} className="line-item">
                    <div>
                      <strong>{row.title}</strong>
                      <p>{row.status} | {row.linked_deals} linked deals</p>
                    </div>
                    <span>{row.conversion_rate}%</span>
                  </div>
                ))}
                {outcomes.length === 0 && <p className="muted-line">No outcome rows found.</p>}
              </div>
              <h4>Snapshots</h4>
              <div className="list-block">
                {snapshots.map((s) => (
                  <div key={s.id} className="line-item">
                    <strong>{s.report_type}</strong>
                    <span>{s.period_key}</span>
                  </div>
                ))}
                {snapshots.length === 0 && <p className="muted-line">No snapshots yet.</p>}
              </div>
            </article>
          </section>
        )}

        {activeTab === "admin" && isAdmin && (
          <section className="scale-ops-grid two">
            <article className="scale-ops-card">
              <div className="heading-row">
                <h3>Platform Metrics</h3>
                <button type="button" onClick={handleRefreshAdmin} disabled={adminLoading}>
                  {adminLoading ? "Refreshing..." : "Refresh"}
                </button>
              </div>
              {opsMetrics ? (
                <pre className="json-block">{JSON.stringify(opsMetrics, null, 2)}</pre>
              ) : (
                <p className="muted-line">No metrics payload available.</p>
              )}
            </article>

            <article className="scale-ops-card">
              <h3>Plan Distribution</h3>
              {planDistribution ? (
                <>
                  <div className="metric-grid">
                    <div><small>Total Users</small><strong>{planDistribution.total_users ?? 0}</strong></div>
                    <div><small>Paid Users</small><strong>{planDistribution.paid_users ?? 0}</strong></div>
                    <div><small>Estimated MRR</small><strong>{formatCurrency(Number(planDistribution.estimated_mrr_inr || 0), "INR")}</strong></div>
                    <div><small>Free Users</small><strong>{planDistribution.distribution?.free ?? 0}</strong></div>
                  </div>
                  <div className="list-block">
                    {Object.entries(planDistribution.distribution || {}).map(([tier, count]) => (
                      <div key={tier} className="line-item">
                        <strong>{tier}</strong>
                        <span>{String(count)}</span>
                      </div>
                    ))}
                  </div>
                </>
              ) : (
                <p className="muted-line">No plan distribution loaded yet.</p>
              )}
            </article>

            <article className="scale-ops-card full">
              <h3>Audit Events</h3>
              <div className="form-grid inline admin-inline-grid">
                <input
                  placeholder="Filter by action (optional)"
                  value={auditActionFilter}
                  onChange={(e) => setAuditActionFilter(e.target.value)}
                />
                <button type="button" onClick={() => loadAdminData(auditActionFilter)} disabled={adminLoading}>
                  Apply Filter
                </button>
                <button
                  type="button"
                  className="ghost-btn"
                  onClick={() => {
                    setAuditActionFilter("");
                    loadAdminData("");
                  }}
                  disabled={adminLoading}
                >
                  Clear
                </button>
              </div>
              <div className="list-block">
                {auditEvents.map((evt) => (
                  <div key={evt.id} className="line-item">
                    <div>
                      <strong>{evt.action}</strong>
                      <p>
                        Actor #{evt.actor_user_id ?? "-"} | {evt.target_type || "-"} #{evt.target_id ?? "-"}
                      </p>
                    </div>
                    <span>{new Date(evt.created_at).toLocaleString()}</span>
                  </div>
                ))}
                {auditEvents.length === 0 && <p className="muted-line">No audit events found for this filter.</p>}
              </div>
            </article>

            <article className="scale-ops-card full">
              <h3>Pending KYC Reviews</h3>
              <div className="list-block">
                {pendingKyc.map((submission) => {
                  const draft = kycReviewDrafts[submission.id] || {};
                  return (
                    <div key={submission.id} className="line-item kyc-review-row">
                      <div>
                        <strong>Submission #{submission.id} | User #{submission.user_id}</strong>
                        <p>
                          {submission.document_type} | {submission.document_number_masked || "masked id unavailable"}
                        </p>
                        <p>Status: {submission.status}</p>
                        {submission.document_url && (
                          <p>
                            <a
                              href={submission.document_url}
                              target="_blank"
                              rel="noreferrer"
                              className="inline-link"
                            >
                              Open Document
                            </a>
                          </p>
                        )}
                      </div>
                      <div className="kyc-review-form">
                        <input
                          placeholder="Review note"
                          value={draft.reviewNote || ""}
                          onChange={(e) => handleKycDraftChange(submission.id, "reviewNote", e.target.value)}
                        />
                        <input
                          type="number"
                          min="0"
                          max="100"
                          placeholder="Risk score (0-100)"
                          value={draft.riskScore || ""}
                          onChange={(e) => handleKycDraftChange(submission.id, "riskScore", e.target.value)}
                        />
                        <input
                          placeholder="Risk flags (comma separated)"
                          value={draft.riskFlags || ""}
                          onChange={(e) => handleKycDraftChange(submission.id, "riskFlags", e.target.value)}
                        />
                        <div className="inline-actions">
                          <button type="button" onClick={() => handleReviewKyc(submission.id, "approved")}>
                            Approve
                          </button>
                          <button
                            type="button"
                            className="danger"
                            onClick={() => handleReviewKyc(submission.id, "rejected")}
                          >
                            Reject
                          </button>
                        </div>
                      </div>
                    </div>
                  );
                })}
                {pendingKyc.length === 0 && <p className="muted-line">No pending KYC submissions.</p>}
              </div>
            </article>
          </section>
        )}

        {activeTab === "integrations" && (
          <section className="scale-ops-grid two">
            <article className="scale-ops-card">
              <h3>Provider Connections</h3>
              <label className="field-label">Provider</label>
              <select value={selectedProvider} onChange={(e) => setSelectedProvider(e.target.value)}>
                {INTEGRATION_PROVIDERS.map((provider) => (
                  <option key={provider} value={provider}>{provider}</option>
                ))}
              </select>

              <div className="provider-grid">
                {INTEGRATION_PROVIDERS.map((provider) => {
                  const active = connections.find((c) => c.provider === provider && c.status === "connected");
                  return (
                    <div key={provider} className="line-item">
                      <strong>{provider}</strong>
                      <div className="inline-actions">
                        {active ? (
                          <button type="button" className="danger" onClick={() => handleDisconnectProvider(provider)}>Disconnect</button>
                        ) : (
                          <button type="button" onClick={() => handleConnectProvider(provider)}>Connect</button>
                        )}
                        {(provider === "slack" || provider === "email") && (
                          <button type="button" className="ghost-btn" onClick={() => handleSendTestAlert(provider)}>Test Alert</button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>

              <div className="form-grid">
                <label className="field-label">Sync Payload (JSON)</label>
                <textarea value={integrationSyncPayload} onChange={(e) => setIntegrationSyncPayload(e.target.value)} rows={4} />
                <button type="button" onClick={handleSyncProvider}>Run Sync</button>
              </div>
            </article>

            <article className="scale-ops-card">
              <h3>Integration Events</h3>
              <div className="inline-actions">
                <button type="button" onClick={() => loadProviderEvents(selectedProvider)}>Refresh Events</button>
                <button type="button" onClick={() => window.open(exportSheetsCsvUrl(), "_blank")}>Sheets Export</button>
                <button type="button" onClick={() => window.open(exportCalendarIcsUrl(), "_blank")}>Calendar Export</button>
              </div>
              <div className="list-block">
                {integrationEvents.map((evt) => (
                  <div key={evt.id} className="line-item">
                    <div>
                      <strong>{evt.event_type}</strong>
                      <p>{evt.status}</p>
                    </div>
                    <span>{new Date(evt.created_at).toLocaleString()}</span>
                  </div>
                ))}
                {integrationEvents.length === 0 && <p className="muted-line">No events for this provider yet.</p>}
              </div>
            </article>
          </section>
        )}
      </main>
    </div>
  );
};

export default ScaleOpsPage;
