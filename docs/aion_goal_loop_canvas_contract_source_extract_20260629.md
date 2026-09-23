# AION Goal Loop Canvas — Contract Source Extract

Purpose: extract exact existing graph, node, glyph compile, goal engine, Pilot and persistence functions before adding Goal Loop contract.


## function getAionWorkflowDraftState

18901:   }
18902: 
18903:   graph.updated_at = new Date().toISOString();
18904:   graph.dirty = true;
18905: 
18906:   return graph;
18907: }
18908: 
18909: function getAionWorkflowDraftState() {
18910:   /*
18911:    * CLEAN TAB GRAPH RESOLVER
18912:    *
18913:    * Main workflow and glyph workflow tabs must never share graph objects.
18914:    * The renderer calls this function, so this is the single source of truth.
18915:    */
18916:   const activeTab = String(window.__aionActiveWorkflowTab || "").toLowerCase();
18917:   const activeGlyphCode = String(
18918:     window.__aionActiveGlyphWorkflowTabCode ||
18919:     window.__aionActiveGlyphWorkflowCode ||
18920:     ""
18921:   ).trim();
18922: 
18923:   if (activeTab === "glyph" && activeGlyphCode && activeGlyphCode.toLowerCase() !== "main") {
18924:     const store =
18925:       window.__aionOpenedGlyphWorkflowGraphsByCode &&
18926:       typeof window.__aionOpenedGlyphWorkflowGraphsByCode === "object"
18927:         ? window.__aionOpenedGlyphWorkflowGraphsByCode
18928:         : {};
18929: 
18930:     const glyphGraph =
18931:       store[activeGlyphCode] ||
18932:       store[activeGlyphCode.toUpperCase()] ||
18933:       store[activeGlyphCode.toLowerCase()] ||
18934:       window.__aionOpenedGlyphWorkflowGraph;
18935: 
18936:     if (glyphGraph && typeof glyphGraph === "object") {
18937:       glyphGraph.glyph_code = glyphGraph.glyph_code || activeGlyphCode;
18938:       window.__aionOpenedGlyphWorkflowGraph = glyphGraph;
18939:       window.__aionWorkflowGraph = glyphGraph;
18940:       return stripAionWorkflowSyntheticChooseNode(glyphGraph);
18941:     }
18942:   }
18943: 
18944:   if (
18945:     window.__aionWorkflowMainGraph &&
18946:     typeof window.__aionWorkflowMainGraph === "object"
18947:   ) {
18948:     window.__aionWorkflowGraph = window.__aionWorkflowMainGraph;
18949:     return stripAionWorkflowSyntheticChooseNode(window.__aionWorkflowMainGraph);
18950:   }
18951: 
18952:   if (window.__aionWorkflowGraph && typeof window.__aionWorkflowGraph === "object") {
18953:     window.__aionWorkflowMainGraph = window.__aionWorkflowGraph;
18954:     return stripAionWorkflowSyntheticChooseNode(window.__aionWorkflowGraph);
18955:   }
18956: 
18957:   try {
18958:     const raw = localStorage.getItem(AION_WORKFLOW_DRAFT_STORAGE_KEY);
18959:     if (raw) {
18960:       const parsed = JSON.parse(raw);
18961:       window.__aionWorkflowMainGraph = stripAionWorkflowSyntheticChooseNode({
18962:         ...getDefaultAionWorkflowDraftState(),
18963:         ...parsed,
18964:         nodes: Array.isArray(parsed.nodes) ? parsed.nodes : [],
18965:         edges: Array.isArray(parsed.edges) ? parsed.edges : [],
18966:       });
18967:       window.__aionWorkflowGraph = window.__aionWorkflowMainGraph;
18968:       return window.__aionWorkflowMainGraph;
18969:     }
18970:   } catch (error) {
18971:     console.warn("[workflow] failed to load draft", error);
18972:   }
18973: 
18974:   window.__aionWorkflowMainGraph = getDefaultAionWorkflowDraftState();
18975:   window.__aionWorkflowGraph = window.__aionWorkflowMainGraph;
18976:   return window.__aionWorkflowMainGraph;
18977: }
18978: 
18979: 
18980: function buildAionWorkflowSavePayload(graph) {
18981:   const safeGraph = graph || getAionWorkflowDraftState();
18982:   const compiledGlyph =
18983:     safeGraph.compiled_glyph || compileAionWorkflowGraphToGlyph(safeGraph);
18984: 
18985:   const nodes = Array.isArray(safeGraph.nodes) ? safeGraph.nodes : [];
18986:   const edges = Array.isArray(safeGraph.edges) ? safeGraph.edges : [];
18987: 
18988:   return {
18989:     schema_version: "aion.workflow_save.v1",
18990:     storage_scope: "business_container",
18991:     business_container:
18992:       compiledGlyph?.workflow?.business_container ||
18993:       safeGraph.business_container ||
18994:       "costa-conexion",
18995:     workflow_id: safeGraph.workflow_id || window.__aionCreateUniqueWorkflowId?.() || "workflow_draft",
18996:     name: safeGraph.name || "Untitled workflow 1",
18997:     status: safeGraph.status || "draft",
18998:     canvas_layout: {
18999:       schema_version: "aion.workflow_canvas_layout.v1",
19000:       coordinate_space: "absolute_canvas_px",
19001:       nodes: nodes.map((node) => ({
19002:         node_id: node.id,
19003:         x: Number(node.x || 0),
19004:         y: Number(node.y || 0),
19005:       })),
19006:       edges: edges.map((edge) => ({
19007:         from: edge.from,
19008:         to: edge.to,
19009:         condition: edge.condition || "success",
19010:       })),
19011:     },
19012:     graph: {
19013:       nodes,
19014:       edges,
19015:     },
19016:     compiled_glyph: compiledGlyph,
19017:     saved_at: new Date().toISOString(),
19018:   };
19019: }
19020: 
19021: function getAionWorkflowPendingNodeConfig(nodeId) {
19022:   window.__aionWorkflowPendingNodeConfig = window.__aionWorkflowPendingNodeConfig || {};
19023:   return window.__aionWorkflowPendingNodeConfig[nodeId] || {};
19024: }
19025: 
19026: function setAionWorkflowPendingNodeConfig(nodeId, key, value) {
19027:   if (!nodeId || !key) return;
19028: 
19029:   window.__aionWorkflowPendingNodeConfig = window.__aionWorkflowPendingNodeConfig || {};
19030:   window.__aionWorkflowPendingNodeConfig[nodeId] = {
19031:     ...(window.__aionWorkflowPendingNodeConfig[nodeId] || {}),
19032:     [key]: value,
19033:   };
19034: }
19035: 
19036: function applyAionWorkflowPendingNodeConfig(nodeId) {
19037:   if (!nodeId) return null;
19038: 
19039:   const graph = getAionWorkflowDraftState();
19040:   const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
19041:   const pending = getAionWorkflowPendingNodeConfig(nodeId);
19042:   const node = nodes.find((item) => item.id === nodeId);
19043: 
19044:   if (!node) return null;
19045: 
19046:   const config = {
19047:     ...(node.config || {}),
19048:     ...pending,
19049:   };

## function normaliseAionWorkflowNodeToGlyphStep

18567:     desktopStore?.state?.business_container;
18568: 
18569:   return String(fromWindow || fromState || "costa_conexion")
18570:     .trim()
18571:     .replace(/[^a-zA-Z0-9_-]/g, "_")
18572:     || "costa_conexion";
18573: }
18574: 
18575: function normaliseAionWorkflowNodeToGlyphStep(node, index = 0) {
18576:   const title = String(node?.title || "").toLowerCase();
18577:   const type = String(node?.type || "").toLowerCase();
18578:   const id = String(node?.id || `node_${index}`);
18579: 
18580:   let op = AION_WORKFLOW_OPS.ACTION;
18581: 
18582:   if (
18583:     type.includes("trigger") ||
18584:     title.includes("trigger") ||
18585:     title.includes("gmail new email") ||
18586:     title.includes("schedule") ||
18587:     title.includes("webhook")
18588:   ) {
18589:     op = AION_WORKFLOW_OPS.TRIGGER;
18590:   } else if (
18591:     title.includes("extract") ||
18592:     title.includes("pattern") ||
18593:     title.includes("replace") ||
18594:     title.includes("html") ||
18595:     title.includes("variable") ||
18596:     title.includes("compose string") ||
18597:     title.includes("sleep") ||
18598:     title.includes("delay") ||
18599:     type.includes("parser") ||
18600:     type.includes("tools")
18601:   ) {
18602:     op = AION_WORKFLOW_OPS.EXTRACT;
18603:   } else if (
18604:     title.includes("classify") ||
18605:     title.includes("router") ||
18606:     title.includes("route")
18607:   ) {
18608:     op = AION_WORKFLOW_OPS.CLASSIFY;
18609:   } else if (
18610:     title.includes("approval") ||
18611:     type.includes("gate")
18612:   ) {
18613:     op = AION_WORKFLOW_OPS.APPROVAL;
18614:   } else if (
18615:     title.includes("wait") ||
18616:     title.includes("delay") ||
18617:     title.includes("schedule")
18618:   ) {
18619:     op = AION_WORKFLOW_OPS.WAIT;
18620:   } else if (
18621:     title.includes("if") ||
18622:     title.includes("else") ||
18623:     title.includes("fork")
18624:   ) {
18625:     op = AION_WORKFLOW_OPS.ROUTE;
18626:   }
18627: 
18628:   return {
18629:     op,
18630:     node_id: id,
18631:     ref: id,
18632:     title: String(node?.title || "Untitled step"),
18633:     node_type: String(node?.type || "Action"),
18634:     status: String(node?.status || "draft"),
18635:     meta: String(node?.meta || ""),
18636:     position: {
18637:       x: Number(node?.x || 0),
18638:       y: Number(node?.y || 0),
18639:     },
18640:     config: node?.config && typeof node.config === "object" ? node.config : {},
18641:   };
18642: }
18643: 
18644: function isAionWorkflowSyntheticChooseNode(node) {
18645:   if (!node) return false;
18646: 
18647:   const id = String(node.id || "");
18648:   const title = String(node.title || node.label || "").trim().toLowerCase();
18649:   const actionId = String(node.action_id || node.action || node.config?.action_id || "").trim().toLowerCase();
18650: 
18651:   return (
18652:     id === "node_choose_start" ||
18653:     (
18654:       title === "choose" &&
18655:       (!actionId || actionId === "generic.step")
18656:     )
18657:   );
18658: }
18659: 
18660: function orderAionWorkflowNodesForGlyph(graph) {
18661:   const nodes = Array.isArray(graph?.nodes)
18662:     ? graph.nodes.filter((node) => !isAionWorkflowSyntheticChooseNode(node))
18663:     : [];
18664: 
18665:   const syntheticChooseIds = new Set(
18666:     Array.isArray(graph?.nodes)
18667:       ? graph.nodes
18668:           .filter((node) => isAionWorkflowSyntheticChooseNode(node))
18669:           .map((node) => String(node.id))
18670:       : [],
18671:   );
18672: 
18673:   const edges = Array.isArray(graph?.edges)
18674:     ? graph.edges.filter((edge) => !syntheticChooseIds.has(String(edge?.from || "")))
18675:     : [];
18676: 
18677:   if (!nodes.length) return [];
18678: 
18679:   const nodeById = new Map(nodes.map((node) => [String(node.id), node]));
18680:   const incoming = new Map(nodes.map((node) => [String(node.id), 0]));
18681:   const outgoing = new Map(nodes.map((node) => [String(node.id), []]));
18682: 
18683:   for (const edge of edges) {
18684:     const from = String(edge?.from || "");
18685:     const to = String(edge?.to || "");
18686:     if (!nodeById.has(from) || !nodeById.has(to)) continue;
18687:     incoming.set(to, (incoming.get(to) || 0) + 1);
18688:     outgoing.get(from)?.push(to);
18689:   }
18690: 
18691:   const queue = nodes
18692:     .filter((node) => (incoming.get(String(node.id)) || 0) === 0)
18693:     .sort((a, b) => Number(a.x || 0) - Number(b.x || 0));
18694: 
18695:   const ordered = [];
18696:   const seen = new Set();
18697: 
18698:   while (queue.length) {
18699:     const node = queue.shift();
18700:     const id = String(node.id);
18701:     if (seen.has(id)) continue;
18702: 
18703:     seen.add(id);
18704:     ordered.push(node);
18705: 
18706:     const nextIds = (outgoing.get(id) || [])
18707:       .filter((nextId) => !seen.has(nextId))
18708:       .sort((a, b) => Number(nodeById.get(a)?.x || 0) - Number(nodeById.get(b)?.x || 0));
18709: 
18710:     for (const nextId of nextIds) {
18711:       const nextIncoming = Math.max(0, (incoming.get(nextId) || 0) - 1);
18712:       incoming.set(nextId, nextIncoming);
18713:       if (nextIncoming === 0 && nodeById.has(nextId)) {
18714:         queue.push(nodeById.get(nextId));
18715:       }

## function orderAionWorkflowNodesForGlyph

18652:     id === "node_choose_start" ||
18653:     (
18654:       title === "choose" &&
18655:       (!actionId || actionId === "generic.step")
18656:     )
18657:   );
18658: }
18659: 
18660: function orderAionWorkflowNodesForGlyph(graph) {
18661:   const nodes = Array.isArray(graph?.nodes)
18662:     ? graph.nodes.filter((node) => !isAionWorkflowSyntheticChooseNode(node))
18663:     : [];
18664: 
18665:   const syntheticChooseIds = new Set(
18666:     Array.isArray(graph?.nodes)
18667:       ? graph.nodes
18668:           .filter((node) => isAionWorkflowSyntheticChooseNode(node))
18669:           .map((node) => String(node.id))
18670:       : [],
18671:   );
18672: 
18673:   const edges = Array.isArray(graph?.edges)
18674:     ? graph.edges.filter((edge) => !syntheticChooseIds.has(String(edge?.from || "")))
18675:     : [];
18676: 
18677:   if (!nodes.length) return [];
18678: 
18679:   const nodeById = new Map(nodes.map((node) => [String(node.id), node]));
18680:   const incoming = new Map(nodes.map((node) => [String(node.id), 0]));
18681:   const outgoing = new Map(nodes.map((node) => [String(node.id), []]));
18682: 
18683:   for (const edge of edges) {
18684:     const from = String(edge?.from || "");
18685:     const to = String(edge?.to || "");
18686:     if (!nodeById.has(from) || !nodeById.has(to)) continue;
18687:     incoming.set(to, (incoming.get(to) || 0) + 1);
18688:     outgoing.get(from)?.push(to);
18689:   }
18690: 
18691:   const queue = nodes
18692:     .filter((node) => (incoming.get(String(node.id)) || 0) === 0)
18693:     .sort((a, b) => Number(a.x || 0) - Number(b.x || 0));
18694: 
18695:   const ordered = [];
18696:   const seen = new Set();
18697: 
18698:   while (queue.length) {
18699:     const node = queue.shift();
18700:     const id = String(node.id);
18701:     if (seen.has(id)) continue;
18702: 
18703:     seen.add(id);
18704:     ordered.push(node);
18705: 
18706:     const nextIds = (outgoing.get(id) || [])
18707:       .filter((nextId) => !seen.has(nextId))
18708:       .sort((a, b) => Number(nodeById.get(a)?.x || 0) - Number(nodeById.get(b)?.x || 0));
18709: 
18710:     for (const nextId of nextIds) {
18711:       const nextIncoming = Math.max(0, (incoming.get(nextId) || 0) - 1);
18712:       incoming.set(nextId, nextIncoming);
18713:       if (nextIncoming === 0 && nodeById.has(nextId)) {
18714:         queue.push(nodeById.get(nextId));
18715:       }
18716:     }
18717:   }
18718: 
18719:   const remaining = nodes
18720:     .filter((node) => !seen.has(String(node.id)))
18721:     .sort((a, b) => Number(a.x || 0) - Number(b.x || 0));
18722: 
18723:   return [...ordered, ...remaining];
18724: }
18725: 
18726: function collectAionWorkflowRequiredConnectors(graph) {
18727:   const nodes = Array.isArray(graph?.nodes) ? graph.nodes : [];
18728: 
18729:   return Array.from(
18730:     new Set(
18731:       nodes
18732:         .map((node) => {
18733:           const config = node?.config && typeof node.config === "object" ? node.config : {};
18734:           return String(config.connector || node.connector || config.app || "").trim();
18735:         })
18736:         .filter(Boolean)
18737:         .filter((connector) => !["logic", "tools", "tool", "flow"].includes(connector.toLowerCase())),
18738:     ),
18739:   );
18740: }
18741: 
18742: function collectAionWorkflowBoardroomEvents(graph) {
18743:   const nodes = Array.isArray(graph?.nodes) ? graph.nodes : [];
18744: 
18745:   return Array.from(
18746:     new Set(
18747:       nodes.flatMap((node) => {
18748:         const config = node?.config && typeof node.config === "object" ? node.config : {};
18749:         const declared =
18750:           config.boardroom_events ||
18751:           config.boardroom_event ||
18752:           config.events ||
18753:           node.boardroom_events ||
18754:           [];
18755: 
18756:         if (Array.isArray(declared)) return declared;
18757:         if (typeof declared === "string") {
18758:           return declared
18759:             .split(",")
18760:             .map((item) => item.trim())
18761:             .filter(Boolean);
18762:         }
18763: 
18764:         return [];
18765:       }),
18766:     ),
18767:   );
18768: }
18769: 
18770: function inferAionWorkflowRiskTier(graph) {
18771:   const nodes = Array.isArray(graph?.nodes) ? graph.nodes : [];
18772:   const hasExternalWrite = nodes.some((node) => {
18773:     const config = node?.config && typeof node.config === "object" ? node.config : {};
18774:     const action = String(config.action_id || config.module_id || node?.action_id || "").toLowerCase();
18775: 
18776:     return (
18777:       config.external_write === true ||
18778:       config.requires_approval === true ||
18779:       action.includes("send") ||
18780:       action.includes("publish") ||
18781:       action.includes("create_draft") ||
18782:       action.includes("post_social")
18783:     );
18784:   });
18785: 
18786:   return hasExternalWrite ? "medium" : "low";
18787: }
18788: 
18789: function compileAionWorkflowGraphToGlyph(graph) {
18790:   const safeGraph = graph && typeof graph === "object" ? graph : {};
18791:   const orderedNodes = orderAionWorkflowNodesForGlyph(safeGraph);
18792:   const steps = orderedNodes.map((node, index) =>
18793:     normaliseAionWorkflowNodeToGlyphStep(node, index),
18794:   );
18795: 
18796:   const syntheticChooseIds = new Set(
18797:     Array.isArray(safeGraph.nodes)
18798:       ? safeGraph.nodes
18799:           .filter((node) => isAionWorkflowSyntheticChooseNode(node))
18800:           .map((node) => String(node.id))

## function compileAionWorkflowGraphToGlyph

18781:       action.includes("create_draft") ||
18782:       action.includes("post_social")
18783:     );
18784:   });
18785: 
18786:   return hasExternalWrite ? "medium" : "low";
18787: }
18788: 
18789: function compileAionWorkflowGraphToGlyph(graph) {
18790:   const safeGraph = graph && typeof graph === "object" ? graph : {};
18791:   const orderedNodes = orderAionWorkflowNodesForGlyph(safeGraph);
18792:   const steps = orderedNodes.map((node, index) =>
18793:     normaliseAionWorkflowNodeToGlyphStep(node, index),
18794:   );
18795: 
18796:   const syntheticChooseIds = new Set(
18797:     Array.isArray(safeGraph.nodes)
18798:       ? safeGraph.nodes
18799:           .filter((node) => isAionWorkflowSyntheticChooseNode(node))
18800:           .map((node) => String(node.id))
18801:       : [],
18802:   );
18803: 
18804:   const edges = Array.isArray(safeGraph.edges)
18805:     ? safeGraph.edges
18806:         .filter((edge) => !syntheticChooseIds.has(String(edge?.from || "")))
18807:         .filter((edge) => !syntheticChooseIds.has(String(edge?.to || "")))
18808:         .map((edge) => ({
18809:           from: String(edge?.from || ""),
18810:           to: String(edge?.to || ""),
18811:           condition: String(edge?.condition || "success"),
18812:         }))
18813:     : [];
18814: 
18815:   const approvalPolicy = {
18816:     dry_run_first: true,
18817:     approval_before_external_write: true,
18818:     raw_glyph_execution: false,
18819:     raw_glyphs_are_ui_decoration_only: true,
18820:   };
18821: 
18822:   return {
18823:     schema_version: AION_WORKFLOW_GLYPH_SCHEMA_VERSION,
18824:     namespace: AION_WORKFLOW_GLYPH_NAMESPACE,
18825:     glyph_type: "workflow_capsule",
18826:     callable: true,
18827:     op: AION_WORKFLOW_OPS.SEQUENCE,
18828:     workflow: {
18829:       workflow_id: String(safeGraph.workflow_id || window.__aionCreateUniqueWorkflowId?.() || "workflow_draft"),
18830:       name: String(safeGraph.name || "Untitled workflow 1"),
18831:       business_container: String(
18832:         safeGraph.business_container || getAionWorkflowBusinessContainerId(),
18833:       ),
18834:       status: String(safeGraph.status || "draft"),
18835:     },
18836:     inputs_schema:
18837:       safeGraph.inputs_schema && typeof safeGraph.inputs_schema === "object"
18838:         ? safeGraph.inputs_schema
18839:         : {},
18840:     outputs_schema:
18841:       safeGraph.outputs_schema && typeof safeGraph.outputs_schema === "object"
18842:         ? safeGraph.outputs_schema
18843:         : {},
18844:     required_connectors: collectAionWorkflowRequiredConnectors(safeGraph),
18845:     approval_policy: approvalPolicy,
18846:     risk_tier: String(safeGraph.risk_tier || inferAionWorkflowRiskTier(safeGraph) || "low"),
18847:     boardroom_events: collectAionWorkflowBoardroomEvents(safeGraph),
18848:     policy: approvalPolicy,
18849:     steps,
18850:     flow_links: edges,
18851:     compiled_at: new Date().toISOString(),
18852:   };
18853: }
18854: 
18855: function compileAndAttachAionWorkflowGlyph(graph) {
18856:   const target = graph || getAionWorkflowDraftState();
18857:   target.business_container = target.business_container || getAionWorkflowBusinessContainerId();
18858:   target.compiled_glyph = compileAionWorkflowGraphToGlyph(target);
18859:   target.compiled_glyph_hash_hint = `${target.compiled_glyph.schema_version}:${target.workflow_id || window.__aionCreateUniqueWorkflowId?.() || "workflow_draft"}:${target.compiled_glyph.steps.length}:${target.compiled_glyph.flow_links.length}`;
18860:   return target.compiled_glyph;
18861: }
18862: 
18863: 
18864: function getDefaultAionWorkflowDraftState() {
18865:   return {
18866:     workflow_id: createAionWorkflowId(),
18867:     name: "Untitled workflow 1",
18868:     status: "draft",
18869:     nodes: [],
18870:     edges: [],
18871:     updated_at: new Date().toISOString(),
18872:   };
18873: }
18874: 
18875: function stripAionWorkflowSyntheticChooseNode(graph) {
18876:   if (!graph || typeof graph !== "object") return graph;
18877: 
18878:   const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
18879:   const syntheticIds = new Set(
18880:     nodes
18881:       .filter((node) =>
18882:         typeof isAionWorkflowSyntheticChooseNode === "function" &&
18883:         isAionWorkflowSyntheticChooseNode(node)
18884:       )
18885:       .map((node) => String(node.id)),
18886:   );
18887: 
18888:   if (!syntheticIds.size) return graph;
18889: 
18890:   graph.nodes = nodes.filter((node) => !syntheticIds.has(String(node.id)));
18891:   graph.edges = Array.isArray(graph.edges)
18892:     ? graph.edges.filter(
18893:         (edge) =>
18894:           !syntheticIds.has(String(edge?.from || "")) &&
18895:           !syntheticIds.has(String(edge?.to || "")),
18896:       )
18897:     : [];
18898: 
18899:   if (syntheticIds.has(String(window.__aionWorkflowSelectedNodeId || ""))) {
18900:     window.__aionWorkflowSelectedNodeId = graph.nodes[0]?.id || null;
18901:   }
18902: 
18903:   graph.updated_at = new Date().toISOString();
18904:   graph.dirty = true;
18905: 
18906:   return graph;
18907: }
18908: 
18909: function getAionWorkflowDraftState() {
18910:   /*
18911:    * CLEAN TAB GRAPH RESOLVER
18912:    *
18913:    * Main workflow and glyph workflow tabs must never share graph objects.
18914:    * The renderer calls this function, so this is the single source of truth.
18915:    */
18916:   const activeTab = String(window.__aionActiveWorkflowTab || "").toLowerCase();
18917:   const activeGlyphCode = String(
18918:     window.__aionActiveGlyphWorkflowTabCode ||
18919:     window.__aionActiveGlyphWorkflowCode ||
18920:     ""
18921:   ).trim();
18922: 
18923:   if (activeTab === "glyph" && activeGlyphCode && activeGlyphCode.toLowerCase() !== "main") {
18924:     const store =
18925:       window.__aionOpenedGlyphWorkflowGraphsByCode &&
18926:       typeof window.__aionOpenedGlyphWorkflowGraphsByCode === "object"
18927:         ? window.__aionOpenedGlyphWorkflowGraphsByCode
18928:         : {};
18929: 

## function compileAndAttachAionWorkflowGlyph

18847:     boardroom_events: collectAionWorkflowBoardroomEvents(safeGraph),
18848:     policy: approvalPolicy,
18849:     steps,
18850:     flow_links: edges,
18851:     compiled_at: new Date().toISOString(),
18852:   };
18853: }
18854: 
18855: function compileAndAttachAionWorkflowGlyph(graph) {
18856:   const target = graph || getAionWorkflowDraftState();
18857:   target.business_container = target.business_container || getAionWorkflowBusinessContainerId();
18858:   target.compiled_glyph = compileAionWorkflowGraphToGlyph(target);
18859:   target.compiled_glyph_hash_hint = `${target.compiled_glyph.schema_version}:${target.workflow_id || window.__aionCreateUniqueWorkflowId?.() || "workflow_draft"}:${target.compiled_glyph.steps.length}:${target.compiled_glyph.flow_links.length}`;
18860:   return target.compiled_glyph;
18861: }
18862: 
18863: 
18864: function getDefaultAionWorkflowDraftState() {
18865:   return {
18866:     workflow_id: createAionWorkflowId(),
18867:     name: "Untitled workflow 1",
18868:     status: "draft",
18869:     nodes: [],
18870:     edges: [],
18871:     updated_at: new Date().toISOString(),
18872:   };
18873: }
18874: 
18875: function stripAionWorkflowSyntheticChooseNode(graph) {
18876:   if (!graph || typeof graph !== "object") return graph;
18877: 
18878:   const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
18879:   const syntheticIds = new Set(
18880:     nodes
18881:       .filter((node) =>
18882:         typeof isAionWorkflowSyntheticChooseNode === "function" &&
18883:         isAionWorkflowSyntheticChooseNode(node)
18884:       )
18885:       .map((node) => String(node.id)),
18886:   );
18887: 
18888:   if (!syntheticIds.size) return graph;
18889: 
18890:   graph.nodes = nodes.filter((node) => !syntheticIds.has(String(node.id)));
18891:   graph.edges = Array.isArray(graph.edges)
18892:     ? graph.edges.filter(
18893:         (edge) =>
18894:           !syntheticIds.has(String(edge?.from || "")) &&
18895:           !syntheticIds.has(String(edge?.to || "")),
18896:       )
18897:     : [];
18898: 
18899:   if (syntheticIds.has(String(window.__aionWorkflowSelectedNodeId || ""))) {
18900:     window.__aionWorkflowSelectedNodeId = graph.nodes[0]?.id || null;
18901:   }
18902: 
18903:   graph.updated_at = new Date().toISOString();
18904:   graph.dirty = true;
18905: 
18906:   return graph;
18907: }
18908: 
18909: function getAionWorkflowDraftState() {
18910:   /*
18911:    * CLEAN TAB GRAPH RESOLVER
18912:    *
18913:    * Main workflow and glyph workflow tabs must never share graph objects.
18914:    * The renderer calls this function, so this is the single source of truth.
18915:    */
18916:   const activeTab = String(window.__aionActiveWorkflowTab || "").toLowerCase();
18917:   const activeGlyphCode = String(
18918:     window.__aionActiveGlyphWorkflowTabCode ||
18919:     window.__aionActiveGlyphWorkflowCode ||
18920:     ""
18921:   ).trim();
18922: 
18923:   if (activeTab === "glyph" && activeGlyphCode && activeGlyphCode.toLowerCase() !== "main") {
18924:     const store =
18925:       window.__aionOpenedGlyphWorkflowGraphsByCode &&
18926:       typeof window.__aionOpenedGlyphWorkflowGraphsByCode === "object"
18927:         ? window.__aionOpenedGlyphWorkflowGraphsByCode
18928:         : {};
18929: 
18930:     const glyphGraph =
18931:       store[activeGlyphCode] ||
18932:       store[activeGlyphCode.toUpperCase()] ||
18933:       store[activeGlyphCode.toLowerCase()] ||
18934:       window.__aionOpenedGlyphWorkflowGraph;
18935: 
18936:     if (glyphGraph && typeof glyphGraph === "object") {
18937:       glyphGraph.glyph_code = glyphGraph.glyph_code || activeGlyphCode;
18938:       window.__aionOpenedGlyphWorkflowGraph = glyphGraph;
18939:       window.__aionWorkflowGraph = glyphGraph;
18940:       return stripAionWorkflowSyntheticChooseNode(glyphGraph);
18941:     }
18942:   }
18943: 
18944:   if (
18945:     window.__aionWorkflowMainGraph &&
18946:     typeof window.__aionWorkflowMainGraph === "object"
18947:   ) {
18948:     window.__aionWorkflowGraph = window.__aionWorkflowMainGraph;
18949:     return stripAionWorkflowSyntheticChooseNode(window.__aionWorkflowMainGraph);
18950:   }
18951: 
18952:   if (window.__aionWorkflowGraph && typeof window.__aionWorkflowGraph === "object") {
18953:     window.__aionWorkflowMainGraph = window.__aionWorkflowGraph;
18954:     return stripAionWorkflowSyntheticChooseNode(window.__aionWorkflowGraph);
18955:   }
18956: 
18957:   try {
18958:     const raw = localStorage.getItem(AION_WORKFLOW_DRAFT_STORAGE_KEY);
18959:     if (raw) {
18960:       const parsed = JSON.parse(raw);
18961:       window.__aionWorkflowMainGraph = stripAionWorkflowSyntheticChooseNode({
18962:         ...getDefaultAionWorkflowDraftState(),
18963:         ...parsed,
18964:         nodes: Array.isArray(parsed.nodes) ? parsed.nodes : [],
18965:         edges: Array.isArray(parsed.edges) ? parsed.edges : [],
18966:       });
18967:       window.__aionWorkflowGraph = window.__aionWorkflowMainGraph;
18968:       return window.__aionWorkflowMainGraph;
18969:     }
18970:   } catch (error) {
18971:     console.warn("[workflow] failed to load draft", error);
18972:   }
18973: 
18974:   window.__aionWorkflowMainGraph = getDefaultAionWorkflowDraftState();
18975:   window.__aionWorkflowGraph = window.__aionWorkflowMainGraph;
18976:   return window.__aionWorkflowMainGraph;
18977: }
18978: 
18979: 
18980: function buildAionWorkflowSavePayload(graph) {
18981:   const safeGraph = graph || getAionWorkflowDraftState();
18982:   const compiledGlyph =
18983:     safeGraph.compiled_glyph || compileAionWorkflowGraphToGlyph(safeGraph);
18984: 
18985:   const nodes = Array.isArray(safeGraph.nodes) ? safeGraph.nodes : [];
18986:   const edges = Array.isArray(safeGraph.edges) ? safeGraph.edges : [];
18987: 
18988:   return {
18989:     schema_version: "aion.workflow_save.v1",
18990:     storage_scope: "business_container",
18991:     business_container:
18992:       compiledGlyph?.workflow?.business_container ||
18993:       safeGraph.business_container ||
18994:       "costa-conexion",
18995:     workflow_id: safeGraph.workflow_id || window.__aionCreateUniqueWorkflowId?.() || "workflow_draft",

## function buildAionWorkflowCanvasCapsulePayload

19925:     .trim()
19926:     .toLowerCase()
19927:     .replace(/[^a-z0-9_.-]+/g, ".")
19928:     .replace(/^\.+|\.+$/g, "");
19929: 
19930:   return raw || fallback;
19931: }
19932: 
19933: function buildAionWorkflowCanvasCapsulePayload(graph) {
19934:   const safeGraph = graph || getAionWorkflowDraftState();
19935:   const nodes = Array.isArray(safeGraph.nodes) ? safeGraph.nodes : [];
19936:   const edges = Array.isArray(safeGraph.edges) ? safeGraph.edges : [];
19937: 
19938:   const workflowSlug = slugifyAionWorkflowPart(
19939:     safeGraph.workflow_id || safeGraph.name || "canvas.workflow",
19940:     "canvas.workflow",
19941:   );
19942: 
19943:   const canonicalKey =
19944:     String(safeGraph.canonical_key || "").trim() ||
19945:     `workflow:${workflowSlug}.v1`;
19946: 
19947:   const displayGlyph =
19948:     String(safeGraph.display_glyph || "").trim() ||
19949:     `WG-${workflowSlug.toUpperCase().replace(/[^A-Z0-9]+/g, "-").slice(0, 28)}`;
19950: 
19951:   const canvasNodes = nodes.map((node, index) => {
19952:     const stepId = slugifyAionWorkflowPart(
19953:       node.step_id || node.id || `step_${index + 1}`,
19954:       `step_${index + 1}`,
19955:     ).replace(/\./g, "_");
19956: 
19957:     const config = node.config && typeof node.config === "object" ? node.config : {};
19958:     const connector = config.connector || node.connector || "";
19959: 
19960:     const requires = Array.isArray(config.requires)
19961:       ? config.requires
19962:       : connector === "gmail"
19963:         ? ["vault.gmail.credentials"]
19964:         : [];
19965: 
19966:     return {
19967:       id: String(node.id || stepId),
19968:       type: String(node.type || "task"),
19969:       position: {
19970:         x: Number(node.x || 0),
19971:         y: Number(node.y || 0),
19972:       },
19973:       data: {
19974:         step_id: stepId,
19975:         kind: String(config.kind || node.kind || node.type || "task"),
19976:         label: String(node.title || config.label || stepId),
19977:         output_ref: String(config.output_ref || `${stepId}.output`),
19978:         ...(connector ? { connector: String(connector) } : {}),
19979:         ...(requires.length ? { requires } : {}),
19980:         ...(config.external_write === true ? { external_write: true } : {}),
19981:         ...(config.requires_approval === true ? { requires_approval: true } : {}),
19982:         ...(config.guard && typeof config.guard === "object" ? { guard: config.guard } : {}),
19983:         ...(config.approval && typeof config.approval === "object" ? { approval: config.approval } : {}),
19984:       },
19985:     };
19986:   });
19987: 
19988:   const canvasEdges = edges.map((edge, index) => ({
19989:     id: String(edge.id || `edge_${index + 1}`),
19990:     source: String(edge.source || edge.from || ""),
19991:     target: String(edge.target || edge.to || ""),
19992:     condition: String(edge.condition || "success"),
19993:   }));
19994: 
19995:   return {
19996:     canonical_key: canonicalKey,
19997:     display_name: String(safeGraph.name || "Untitled workflow"),
19998:     meaning: String(
19999:       safeGraph.meaning ||
20000:       "Canvas-built workflow capsule generated from the Aion desktop workflow canvas.",
20001:     ),
20002:     display_glyph: displayGlyph,
20003:     tags: ["canvas", "desktop", "workflow"],
20004:     allowed_use_cases: ["Compile and save a visual workflow canvas as a Workflow Capsule."],
20005:     vault_requirements: Array.from(
20006:       new Set(
20007:         canvasNodes.flatMap((node) =>
20008:           Array.isArray(node.data?.requires) ? node.data.requires : [],
20009:         ),
20010:       ),
20011:     ),
20012:     policy: {
20013:       dry_run_first: true,
20014:       approval_before_external_write: true,
20015:       external_writes_allowed: false,
20016:       allow_autonomous_execution: false,
20017:     },
20018:     nodes: canvasNodes,
20019:     edges: canvasEdges,
20020:   };
20021: }
20022: 
20023: async function saveAionWorkflowCanvasAsCapsule(graph) {
20024:   const safeGraph = graph || getAionWorkflowDraftState();
20025:   const apiBase =
20026:     state.apiBase ||
20027:     state.desktopApiBase ||
20028:     window.AION_API_BASE ||
20029:     "http://127.0.0.1:8080";
20030: 
20031:   const canvas = buildAionWorkflowCanvasCapsulePayload(safeGraph);
20032: 
20033:   const response = await fetch(`${apiBase}/api/workflow-capsules/canvas/compile-save`, {
20034:     method: "POST",
20035:     headers: { "Content-Type": "application/json" },
20036:     body: JSON.stringify({
20037:       canvas,
20038:       scope: "workspace",
20039:       workspace_id: state.workspaceId || safeGraph.business_container || "default_workspace",
20040:       overwrite: true,
20041:       rebuild_registry: true,
20042:     }),
20043:   });
20044: 
20045:   if (!response.ok) {
20046:     throw new Error(`Canvas capsule save failed: HTTP ${response.status}`);
20047:   }
20048: 
20049:   const result = await response.json();
20050:   if (!result?.ok) {
20051:     const reason = Array.isArray(result?.errors)
20052:       ? result.errors.join(", ")
20053:       : result?.error || "Canvas capsule save failed";
20054:     throw new Error(reason);
20055:   }
20056: 
20057:   safeGraph.canonical_key = result.canonical_key || canvas.canonical_key;
20058:   safeGraph.display_glyph = result.display_glyph || canvas.display_glyph;
20059:   safeGraph.capsule_saved_at = new Date().toISOString();
20060:   safeGraph.capsule_path = result.path || "";
20061:   safeGraph.capsule_checksum = result.checksum || "";
20062:   safeGraph.dirty = false;
20063: 
20064:   window.__aionWorkflowGraph = safeGraph;
20065:   persistAionWorkflowDraftState();
20066: 
20067:   return result;
20068: }
20069: 
20070: function renderAionWorkflowGlyphDebugExecutionPanel() {
20071:   if (window.__aionWorkflowGlyphDebugOpen !== true) return "";
20072: 
20073:   const graph = getAionWorkflowDraftState();

## function saveAionWorkflowCanvasAsCapsule

20015:       external_writes_allowed: false,
20016:       allow_autonomous_execution: false,
20017:     },
20018:     nodes: canvasNodes,
20019:     edges: canvasEdges,
20020:   };
20021: }
20022: 
20023: async function saveAionWorkflowCanvasAsCapsule(graph) {
20024:   const safeGraph = graph || getAionWorkflowDraftState();
20025:   const apiBase =
20026:     state.apiBase ||
20027:     state.desktopApiBase ||
20028:     window.AION_API_BASE ||
20029:     "http://127.0.0.1:8080";
20030: 
20031:   const canvas = buildAionWorkflowCanvasCapsulePayload(safeGraph);
20032: 
20033:   const response = await fetch(`${apiBase}/api/workflow-capsules/canvas/compile-save`, {
20034:     method: "POST",
20035:     headers: { "Content-Type": "application/json" },
20036:     body: JSON.stringify({
20037:       canvas,
20038:       scope: "workspace",
20039:       workspace_id: state.workspaceId || safeGraph.business_container || "default_workspace",
20040:       overwrite: true,
20041:       rebuild_registry: true,
20042:     }),
20043:   });
20044: 
20045:   if (!response.ok) {
20046:     throw new Error(`Canvas capsule save failed: HTTP ${response.status}`);
20047:   }
20048: 
20049:   const result = await response.json();
20050:   if (!result?.ok) {
20051:     const reason = Array.isArray(result?.errors)
20052:       ? result.errors.join(", ")
20053:       : result?.error || "Canvas capsule save failed";
20054:     throw new Error(reason);
20055:   }
20056: 
20057:   safeGraph.canonical_key = result.canonical_key || canvas.canonical_key;
20058:   safeGraph.display_glyph = result.display_glyph || canvas.display_glyph;
20059:   safeGraph.capsule_saved_at = new Date().toISOString();
20060:   safeGraph.capsule_path = result.path || "";
20061:   safeGraph.capsule_checksum = result.checksum || "";
20062:   safeGraph.dirty = false;
20063: 
20064:   window.__aionWorkflowGraph = safeGraph;
20065:   persistAionWorkflowDraftState();
20066: 
20067:   return result;
20068: }
20069: 
20070: function renderAionWorkflowGlyphDebugExecutionPanel() {
20071:   if (window.__aionWorkflowGlyphDebugOpen !== true) return "";
20072: 
20073:   const graph = getAionWorkflowDraftState();
20074:   const compiled = graph?.compiled_glyph || compileAionWorkflowGraphToGlyph(graph);
20075:   const stepCount = Array.isArray(compiled?.steps) ? compiled.steps.length : 0;
20076:   const linkCount = Array.isArray(compiled?.flow_links) ? compiled.flow_links.length : 0;
20077: 
20078:   return `
20079:     <div class="aion-workflow-glyph-debug-panel" data-aion-glyph-debug-panel="true">
20080:       <button
20081:         class="aion-dry-run-floating-close"
20082:         type="button"
20083:         data-aion-glyph-debug-close="true"
20084:         title="Close compiled glyph"
20085:       >
20086:         ×
20087:       </button>
20088: 
20089:       <div class="aion-workflow-glyph-debug-head">
20090:         <strong>⌁ Compiled Glyph developer/debug</strong>
20091:         <span>${escapeHtml(String(stepCount))} steps · ${escapeHtml(String(linkCount))} links</span>
20092:       </div>
20093: 
20094:       <pre>${escapeHtml(JSON.stringify(compiled, null, 2))}</pre>
20095:     </div>
20096:   `;
20097: }
20098: 
20099: 
20100: 
20101: 
20102: function getWorkflowArchitectProviderCopy(provider) {
20103:   const key = String(provider || "mock");
20104: 
20105:   if (key === "local_gemma") {
20106:     return "Uses local Ollama/Gemma if available. Still dry-run only.";
20107:   }
20108: 
20109:   if (key === "openai") {
20110:     return "Uses OpenAI provider adapter. Still dry-run only.";
20111:   }
20112: 
20113:   if (key === "claude" || key === "gemini" || key === "grok") {
20114:     return "Provider is visible for future routing but currently fail-closed.";
20115:   }
20116: 
20117:   return "Uses deterministic local mock generation. Safe for testing.";
20118: }
20119: 
20120: function getWorkflowArchitectResultErrors(result) {
20121:   const value =
20122:     result?.errors ||
20123:     result?.review?.errors ||
20124:     result?.validation_errors ||
20125:     result?.review?.validation_errors ||
20126:     [];
20127: 
20128:   if (Array.isArray(value)) {
20129:     return value.map((item) => String(item)).filter(Boolean);
20130:   }
20131: 
20132:   return value ? [String(value)] : [];
20133: }
20134: 
20135: function getWorkflowArchitectResultWarnings(result) {
20136:   const value =
20137:     result?.warnings ||
20138:     result?.review?.warnings ||
20139:     result?.validation_warnings ||
20140:     result?.review?.validation_warnings ||
20141:     [];
20142: 
20143:   if (Array.isArray(value)) {
20144:     return value.map((item) => String(item)).filter(Boolean);
20145:   }
20146: 
20147:   return value ? [String(value)] : [];
20148: }
20149: 
20150: 
20151: 
20152: /* ============================================================
20153:    AI Architect Canvas Node Builder
20154:    Separate AI build canvas, not the main workflow canvas.
20155:    ============================================================ */
20156: 
20157: function getAionArchitectCanvasState() {
20158:   const current = window.__aionArchitectCanvasState || {};
20159: 
20160:   if (!Array.isArray(current.steps) || current.steps.length === 0) {
20161:     current.steps = [
20162:       {
20163:         id: "ai_arch_step_1",

## function renderAionWorkflowCanvasPanel

23559:         aria-label="Clear staged glyph nodes"
23560:       >
23561:         Clear staged glyphs
23562:       </button>
23563: </div>
23564:   `;
23565: }
23566: 
23567: function renderAionWorkflowCanvasPanel({ workflows = [], loading = false } = {}) {
23568:   if (window.__aionWorkflowArchitectCanvasMode === true) {
23569:     return renderAionArchitectCanvasMode();
23570:   }
23571: 
23572:   maybeLoadAionWorkflowFromBusinessContainerOnce();
23573:   const graph = getAionWorkflowDraftState();
23574:   window["__aionWorkflowGraph"] = graph;
23575:   compileAndAttachAionWorkflowGlyph(graph);
23576: 
23577:   const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
23578:   const edges = Array.isArray(graph.edges) ? graph.edges : [];
23579: 
23580:   const selectedNodeId = window.__aionWorkflowSelectedNodeId || null;
23581:   const selectedNode =
23582:     nodes.find((node) => node.id === selectedNodeId) ||
23583:     nodes[nodes.length - 1] ||
23584:     nodes[0] ||
23585:     null;
23586: 
23587:   const firstStepPickerHtml = `
23588:     <div class="aion-first-step-picker">
23589:       <div class="aion-inspector-head">
23590:         <div>
23591:           <div class="eyebrow">Start workflow</div>
23592:           <h3>What starts this workflow?</h3>
23593:           <p>Choose a trigger, app event, browser skill, or AI starter.</p>
23594:         </div>
23595:       </div>
23596: 
23597:       <div class="aion-workflow-search">⌕ Search triggers, apps, or modules...</div>
23598: 
23599:       <div class="aion-picker-section">
23600:         <div class="aion-picker-section-title">Recommended</div>
23601: 
23602:         <button class="aion-picker-row" data-aion-workflow-create-trigger="manual" type="button">
23603:           <span class="aion-picker-icon">◎</span>
23604:           <span>
23605:             <strong>Trigger manually</strong>
23606:             <small>Start the workflow when the user clicks Run once.</small>
23607:           </span>
23608:           <em>Active</em>
23609:         </button>
23610: 
23611:         <button class="aion-picker-row" data-aion-workflow-create-trigger="gmail_new_email" type="button">
23612:           <span class="aion-picker-icon">✉</span>
23613:           <span>
23614:             <strong>Gmail new email</strong>
23615:             <small>Start when a new Gmail email arrives. Connection required later.</small>
23616:           </span>
23617:           <em>Mock</em>
23618:         </button>
23619: 
23620:         <button class="aion-picker-row" data-aion-workflow-create-trigger="schedule" type="button">
23621:           <span class="aion-picker-icon">◷</span>
23622:           <span>
23623:             <strong>Schedule</strong>
23624:             <small>Run every hour, day, week, or custom interval.</small>
23625:           </span>
23626:           <em>Draft</em>
23627:         </button>
23628: 
23629:         <button class="aion-picker-row" data-aion-workflow-create-trigger="webhook" type="button">
23630:           <span class="aion-picker-icon">⑂</span>
23631:           <span>
23632:             <strong>Webhook / API call</strong>
23633:             <small>Start when another system sends Aion an HTTP request.</small>
23634:           </span>
23635:           <em>Draft</em>
23636:         </button>
23637:       </div>
23638: 
23639:       <div class="aion-picker-section">
23640:         <div class="aion-picker-section-title">Apps</div>
23641: 
23642:         <button class="aion-picker-row" data-aion-workflow-create-trigger="gmail_new_email" type="button">
23643:           <span class="aion-picker-icon">G</span>
23644:           <span>
23645:             <strong>Gmail</strong>
23646:             <small>Watch emails, read messages, draft replies, send after approval.</small>
23647:           </span>
23648:           <em>Mock</em>
23649:         </button>
23650: 
23651:         <button class="aion-picker-row" data-aion-workflow-create-trigger="xero_event" type="button">
23652:           <span class="aion-picker-icon">X</span>
23653:           <span>
23654:             <strong>Xero</strong>
23655:             <small>Invoices, contacts, PDFs, quote and payment events.</small>
23656:           </span>
23657:           <em>Soon</em>
23658:         </button>
23659: 
23660:         <button class="aion-picker-row" data-aion-workflow-create-trigger="crm_event" type="button">
23661:           <span class="aion-picker-icon">C</span>
23662:           <span>
23663:             <strong>CRM / CostaConnect</strong>
23664:             <small>New leads, profile claims, ad orders, customer updates.</small>
23665:           </span>
23666:           <em>Soon</em>
23667:         </button>
23668: 
23669:         <button class="aion-picker-row" data-aion-workflow-create-trigger="http_event" type="button">
23670:           <span class="aion-picker-icon">⌁</span>
23671:           <span>
23672:             <strong>HTTP Request</strong>
23673:             <small>Use API/MCP-first automation for external systems.</small>
23674:           </span>
23675:           <em>Soon</em>
23676:         </button>
23677:       </div>
23678: 
23679:       <div class="aion-picker-section">
23680:         <div class="aion-picker-section-title">AI / Aion</div>
23681: 
23682:         <button class="aion-picker-row" data-aion-workflow-create-trigger="chat" type="button">
23683:           <span class="aion-picker-icon">☏</span>
23684:           <span>
23685:             <strong>Chat message</strong>
23686:             <small>Start when a user, customer, or operator sends a message.</small>
23687:           </span>
23688:           <em>Draft</em>
23689:         </button>
23690: 
23691:         <button class="aion-picker-row" data-aion-workflow-build-with-ai="true" type="button">
23692:           <span class="aion-picker-icon">✦</span>
23693:           <span>
23694:             <strong>Build with AI</strong>
23695:             <small>Describe the backend automation and Aion drafts a workflow.</small>
23696:           </span>
23697:           <em>Soon</em>
23698:         </button>
23699: 
23700:         <button class="aion-picker-row" data-aion-workflow-create-trigger="evaluation" type="button">
23701:           <span class="aion-picker-icon">✓</span>
23702:           <span>
23703:             <strong>Evaluation run</strong>
23704:             <small>Run a test dataset through the workflow before publishing.</small>
23705:           </span>
23706:           <em>Draft</em>
23707:         </button>

## function renderAionArchitectNodeCanvas

20262:           <span>${escapeHtml(action.connector || "app")} · ${escapeHtml(action.category || action.kind || "action")}</span>
20263:           ${action.locked ? `<em>Locked</em>` : ""}
20264:         </button>
20265:       `).join("")}
20266:     </div>
20267:   `;
20268: }
20269: 
20270: function renderAionArchitectNodeCanvas() {
20271:   const canvas = getAionArchitectCanvasState();
20272:   const steps = Array.isArray(canvas.steps) ? canvas.steps : [];
20273:   const selectedId = canvas.selectedStepId;
20274: 
20275:   return `
20276:     <section class="aion-architect-real-canvas" data-aion-architect-real-canvas="true">
20277:       <div class="aion-architect-real-canvas-head">
20278:         <div>
20279:           <div class="eyebrow">AI Workflow Architect</div>
20280:           <h2>Build the automation as nodes</h2>
20281:           <p>Click a node to configure it. Use + to add the next step. All execution remains dry-run first.</p>
20282:         </div>
20283: 
20284:         <button type="button" class="secondary-btn" data-aion-architect-open-module-picker="true">
20285:           + Add step
20286:         </button>
20287:       </div>
20288: 
20289:       <div class="aion-architect-node-lane">
20290:         ${steps.map((step, index) => {
20291:           const selected = String(step.id) === String(selectedId);
20292:           const appLabel = step.app || step.connector || "Choose";
20293:           return `
20294:             <div class="aion-architect-node-wrap">
20295:               <button
20296:                 type="button"
20297:                 class="aion-architect-node-card ${selected ? "selected" : ""}"
20298:                 data-aion-architect-select-step="${escapeHtml(step.id)}"
20299:               >
20300:                 <div class="aion-architect-node-icon">${escapeHtml(String(appLabel).slice(0, 1).toUpperCase())}</div>
20301:                 <div class="aion-architect-node-badge">${escapeHtml(String(index + 1))}</div>
20302:                 <strong>${escapeHtml(appLabel)}</strong>
20303:                 <span>${escapeHtml(step.action_label || "Choose action")}</span>
20304:                 <small>${escapeHtml(step.subtitle || step.action_id || "Configure this step")}</small>
20305:               </button>
20306: 
20307:               <div class="aion-architect-node-mini-toolbar">
20308:                 <button type="button" title="Step settings" data-aion-architect-open-settings="${escapeHtml(step.id)}">⚙</button>
20309:                 <button type="button" title="Configure logic / variables" data-aion-architect-open-advanced-config="${escapeHtml(step.id)}">⑂</button>
20310:                 <button type="button" title="Remove step" aria-label="Remove step" data-aion-architect-remove-step="${escapeHtml(step.id)}">×</button>
20311:               </div>
20312:             </div>
20313: 
20314:             ${index < steps.length - 1 ? `<div class="aion-architect-node-link"></div>` : ""}
20315:           `;
20316:         }).join("")}
20317: 
20318:         <button type="button" class="aion-architect-add-step-node" data-aion-architect-open-module-picker="true">
20319:           +
20320:         </button>
20321:       </div>
20322:     </section>
20323:   `;
20324: }
20325: 
20326: 
20327: 
20328: function getAionArchitectModuleCatalogue() {
20329:   return [
20330:     {
20331:       group: "Flow Control",
20332:       group_id: "flow_control",
20333:       description: "Branch, merge, route, repeat, iterate, or handle errors.",
20334:       modules: [
20335:         { id: "flow.if_else", label: "If / else", kind: "logic", app: "logic", action_id: "logic.if_else", description: "Split the workflow into true/false paths." },
20336:         { id: "flow.router", label: "Router", kind: "router", app: "logic", action_id: "logic.router", description: "Route work into multiple paths." },
20337:         { id: "flow.merge", label: "Merge", kind: "merge", app: "logic", action_id: "logic.merge", description: "Merge routes back into one path." },
20338:         { id: "flow.iterator", label: "Iterator", kind: "logic", app: "logic", action_id: "logic.iterator", description: "Split an array into individual items." },
20339:         { id: "flow.array_aggregator", label: "Array aggregator", kind: "logic", app: "logic", action_id: "logic.array_aggregator", description: "Combine many items into one array." },
20340:         { id: "flow.repeater", label: "Repeater", kind: "logic", app: "logic", action_id: "logic.repeater", description: "Repeat the next modules a set number of times." },
20341:         { id: "flow.ignore_error", label: "Ignore error", kind: "logic", app: "logic", action_id: "logic.ignore_error", description: "Skip failed bundles and continue." },
20342:         { id: "flow.break_error", label: "Break / retry later", kind: "logic", app: "logic", action_id: "logic.break_error", description: "Save failed bundles for review or retry." },
20343:       ],
20344:     },
20345:     {
20346:       group: "Tools",
20347:       group_id: "tools",
20348:       description: "Variables, delays, aggregators, strings, and transforms.",
20349:       modules: [
20350:         { id: "tools.set_variable", label: "Set variable", kind: "tool", app: "tools", action_id: "tools.set_variable", description: "Store a workflow value." },
20351:         { id: "tools.get_variable", label: "Get variable", kind: "tool", app: "tools", action_id: "tools.get_variable", description: "Read a stored workflow value." },
20352:         { id: "tools.set_multiple_variables", label: "Set multiple variables", kind: "tool", app: "tools", action_id: "tools.set_multiple_variables", description: "Store several values." },
20353:         { id: "tools.get_multiple_variables", label: "Get multiple variables", kind: "tool", app: "tools", action_id: "tools.get_multiple_variables", description: "Read several stored values." },
20354:         { id: "tools.sleep", label: "Sleep", kind: "tool", app: "tools", action_id: "tools.sleep", description: "Delay execution." },
20355:         { id: "tools.compose_string", label: "Compose a string", kind: "tool", app: "tools", action_id: "tools.compose_string", description: "Build mapped text." },
20356:         { id: "tools.switch", label: "Switch", kind: "tool", app: "tools", action_id: "tools.switch", description: "Switch output based on input." },
20357:         { id: "tools.text_aggregator", label: "Text aggregator", kind: "tool", app: "tools", action_id: "tools.text_aggregator", description: "Aggregate text from multiple items." },
20358:         { id: "tools.numeric_aggregator", label: "Numeric aggregator", kind: "tool", app: "tools", action_id: "tools.numeric_aggregator", description: "Aggregate numbers." },
20359:       ],
20360:     },
20361:     {
20362:       group: "Text Parser",
20363:       group_id: "text_parser",
20364:       description: "Regex, HTML, matching, replacing, and text extraction.",
20365:       modules: [
20366:         { id: "text.match_pattern", label: "Match pattern", kind: "tool", app: "text_parser", action_id: "text.match_pattern", description: "Find text using regex." },
20367:         { id: "text.match_pattern_advanced", label: "Match pattern advanced", kind: "tool", app: "text_parser", action_id: "text.match_pattern_advanced", description: "Find text using mappable regex." },
20368:         { id: "text.replace", label: "Replace", kind: "tool", app: "text_parser", action_id: "text.replace", description: "Replace text or regex matches." },
20369:         { id: "text.html_to_text", label: "HTML to text", kind: "tool", app: "text_parser", action_id: "text.html_to_text", description: "Convert HTML to readable text." },
20370:         { id: "text.get_elements_from_html", label: "Get elements from HTML", kind: "tool", app: "text_parser", action_id: "text.get_elements_from_html", description: "Extract images, links, tables, or elements." },
20371:         { id: "text.get_html_table", label: "Get content from HTML table", kind: "tool", app: "text_parser", action_id: "text.get_html_table", description: "Extract rows and columns from an HTML table." },
20372:       ],
20373:     },
20374:     {
20375:       group: "AI",
20376:       group_id: "ai",
20377:       description: "Use Aion or model tools to classify, extract, draft, summarise, translate, or inspect content.",
20378:       modules: [
20379:         { id: "ai.run_agent", label: "Run an agent", kind: "ai_action", app: "aion", action_id: "aion.run_agent", description: "Run an Aion agent on the step input." },
20380:         { id: "ai.simple_prompt", label: "Simple text prompt", kind: "ai_action", app: "aion", action_id: "aion.simple_prompt", description: "Ask AI for a text response." },
20381:         { id: "ai.extract_fields", label: "Extract fields", kind: "ai_action", app: "aion", action_id: "aion.extract_fields", description: "Extract structured fields from incoming data." },
20382:         { id: "ai.extract_information", label: "Extract information from text", kind: "ai_action", app: "aion", action_id: "aion.extract_information", description: "Extract fields from text." },
20383:         { id: "ai.classify_lead", label: "Classify enquiry", kind: "ai_action", app: "aion", action_id: "aion.classify_lead", description: "Classify service type, urgency, town, department, or route." },
20384:         { id: "ai.summarise_text", label: "Summarise text", kind: "ai_action", app: "aion", action_id: "aion.summarise_text", description: "Condense text into a summary." },
20385:         { id: "ai.categorise_text", label: "Categorise text", kind: "ai_action", app: "aion", action_id: "aion.categorise_text", description: "Assign text to categories." },
20386:         { id: "ai.sentiment", label: "Analyze sentiment", kind: "ai_action", app: "aion", action_id: "aion.sentiment", description: "Positive, neutral, or negative." },
20387:         { id: "ai.translate", label: "Translate text", kind: "ai_action", app: "aion", action_id: "aion.translate", description: "Translate text into another language." },
20388:         { id: "ai.describe_image", label: "Describe image", kind: "ai_action", app: "aion", action_id: "aion.describe_image", description: "Describe an image." },
20389:         { id: "ai.transcribe_audio", label: "Transcribe audio", kind: "ai_action", app: "aion", action_id: "aion.transcribe_audio", description: "Transcribe an audio file." },
20390:       ],
20391:     },
20392:     {
20393:       group: "Apps",
20394:       group_id: "apps",
20395:       description: "Use connected apps and external systems.",
20396:       modules: [
20397:         { id: "gmail.watch_emails", label: "Gmail — Watch emails", kind: "trigger", app: "gmail", action_id: "gmail.watch_emails", description: "Trigger when a new email arrives." },
20398:         { id: "gmail.search_emails", label: "Gmail — Search emails", kind: "app_action", app: "gmail", action_id: "gmail.search_emails", description: "Search Gmail." },
20399:         { id: "gmail.get_email", label: "Gmail — Get an email", kind: "app_action", app: "gmail", action_id: "gmail.get_email", description: "Read one Gmail email by ID." },
20400:         { id: "gmail.read_email", label: "Gmail — Read email", kind: "app_action", app: "gmail", action_id: "gmail.read_email", description: "Read subject, body, sender, attachments, and thread context." },
20401:         { id: "gmail.create_draft", label: "Gmail — Create draft", kind: "app_action", app: "gmail", action_id: "gmail.create_draft", description: "Create a Gmail draft. No live send." },
20402:         { id: "gmail.send_email", label: "Gmail — Send email", kind: "app_action", app: "gmail", action_id: "gmail.send_email", description: "Send only after human approval." },
20403:         { id: "hubspot.create_contact", label: "HubSpot — Create/update contact", kind: "app_action", app: "hubspot", action_id: "hubspot.create_or_update_contact", description: "Create or update a contact." },
20404:         { id: "mailchimp.add_subscriber", label: "Mailchimp — Add subscriber", kind: "app_action", app: "mailchimp", action_id: "mailchimp.add_subscriber", description: "Add an email to an audience." },
20405:         { id: "calendar.create_event", label: "Google Calendar — Create event", kind: "app_action", app: "calendar", action_id: "calendar.create_event", description: "Create a calendar event." },
20406:         { id: "http.request", label: "HTTP — Make request", kind: "app_action", app: "http", action_id: "http.request", description: "Call an API endpoint." },
20407:         { id: "browser.scrape_detail", label: "Browser — Scrape detail", kind: "tool", app: "browser", action_id: "browser.scrape_detail", description: "Extract a value from a webpage." },
20408:       ],
20409:     },
20410:     {

## function renderAionArchitectCanvasMode

21879:           <button type="button" class="primary-btn" data-aion-architect-close-settings="true">Save</button>
21880:         </div>
21881:       </aside>
21882:     </div>
21883:   `;
21884: }
21885: 
21886: 
21887: function renderAionArchitectCanvasMode() {
21888:   const mode = window.__aionArchitectBuildMode || window.__aionWorkflowArchitectBuildMode || "";
21889:   const hasChosenMode = mode === "steps" || mode === "describe";
21890: 
21891:   if (!hasChosenMode) {
21892:     return `
21893:       <section class="aion-architect-canvas-shell" data-workflow-architect-canvas-mode="true">
21894:         <div class="aion-architect-page-header aion-architect-page-header-compact">
21895:           <div class="aion-architect-header-title">
21896:             <div class="aion-workflow-logo">AI</div>
21897:             <div>
21898:               <h1>AI Workflow Architect</h1>
21899:               <div class="aion-workflow-subtle-meta">Aion workflow builder · local draft</div>
21900:             </div>
21901:           </div>
21902: 
21903:           <div class="aion-architect-topbar-actions">
21904:             <button type="button" class="secondary-btn" data-workflow-architect-close-canvas-mode="true">
21905:               Back to canvas
21906:             </button>
21907:             <span class="train-status-chip train-status-ok">Dry-run only</span>
21908:             <span class="aion-architect-safety-badge" title="Execution: dry-run only. Live send disabled. External writes approval gated. Save requires valid dry-run + confirmation.">
21909:               🔒 Safety locked
21910:             </span>
21911:             <span class="train-status-chip">Awaiting review</span>
21912:           </div>
21913:         </div>
21914: 
21915:         <main class="aion-architect-start-screen">
21916:           <section class="aion-architect-start-card">
21917:             <div class="eyebrow">Build mode</div>
21918:             <h2>How do you want to build?</h2>
21919:             <p class="muted">
21920:               Start by choosing whether you want to build the workflow as app/action nodes or describe it in plain English.
21921:             </p>
21922: 
21923:             <div class="aion-architect-mode-switch aion-architect-start-mode-switch">
21924:               <button type="button" data-aion-architect-build-mode="steps">
21925:                 <strong>Use this app</strong>
21926:                 <span>App → action → next step.</span>
21927:               </button>
21928: 
21929:               <button type="button" data-aion-architect-build-mode="describe">
21930:                 <strong>Describe workflow</strong>
21931:                 <span>Plain English builder.</span>
21932:               </button>
21933:             </div>
21934:           </section>
21935:         </main>
21936:       </section>
21937:     `;
21938:   }
21939: 
21940:   if (mode === "describe") {
21941:     return `
21942:       <section class="aion-architect-canvas-shell" data-workflow-architect-canvas-mode="true">
21943:         <div class="aion-architect-page-header aion-architect-page-header-compact">
21944:           <div class="aion-architect-header-title">
21945:             <div class="aion-workflow-logo">AI</div>
21946:             <div>
21947:               <h1>AI Workflow Architect</h1>
21948:               <div class="aion-workflow-subtle-meta">Describe workflow · local draft</div>
21949:             </div>
21950:           </div>
21951: 
21952:           <div class="aion-architect-topbar-actions">
21953:             <button type="button" class="secondary-btn" data-workflow-architect-close-canvas-mode="true">Back to canvas</button>
21954:             <button type="button" class="secondary-btn" data-aion-architect-build-mode="steps">Use this app</button>
21955:             <button type="button" class="primary-btn" data-workflow-architect-build-review="true">Build review</button>
21956:             <button type="button" class="secondary-btn" data-workflow-architect-load-valid-review="true" disabled>Load to canvas</button>
21957:           </div>
21958:         </div>
21959: 
21960:         <main class="aion-architect-describe-screen">
21961:           <section class="aion-architect-describe-card">
21962:             <div class="eyebrow">Describe workflow</div>
21963:             <h2>Tell Aion what should happen</h2>
21964:             <textarea
21965:               class="aion-workflow-architect-goal"
21966:               data-workflow-architect-goal-input="true"
21967:               rows="8"
21968:               placeholder="Example: When a new Gmail enquiry arrives, extract the customer details, create a CRM contact, add the email to Mailchimp, draft a welcome reply, then ask me for approval."
21969:             ></textarea>
21970:           </section>
21971:         </main>
21972:       </section>
21973:     `;
21974:   }
21975: 
21976:   const nodeCanvas =
21977:     typeof renderAionArchitectNodeCanvas === "function"
21978:       ? renderAionArchitectNodeCanvas()
21979:       : typeof renderAionArchitectRealCanvas === "function"
21980:         ? renderAionArchitectRealCanvas()
21981:         : `
21982:           <section class="aion-architect-real-canvas">
21983:             <div class="aion-architect-real-canvas-head">
21984:               <div>
21985:                 <div class="eyebrow">AI Workflow Architect</div>
21986:                 <h2>Build the automation as nodes</h2>
21987:                 <p>Click a node to configure it. Use + to add the next step. All execution remains dry-run first.</p>
21988:               </div>
21989:               <button type="button" class="secondary-btn" data-aion-architect-open-module-picker="true">+ Add step</button>
21990:             </div>
21991: 
21992:             <div class="empty-state">
21993:               Node canvas renderer not found yet, but AI Architect mode is mounted.
21994:             </div>
21995:           </section>
21996:         `;
21997: 
21998:   const settingsModal =
21999:     typeof renderAionArchitectStepSettingsModal === "function"
22000:       ? renderAionArchitectStepSettingsModal()
22001:       : "";
22002: 
22003:   return `
22004:     <section class="aion-architect-canvas-shell" data-workflow-architect-canvas-mode="true">
22005:       <div class="aion-architect-page-header aion-architect-page-header-compact">
22006:         <div class="aion-architect-header-title">
22007:           <div class="aion-workflow-logo">AI</div>
22008:           <div>
22009:             <h1>AI Workflow Architect</h1>
22010:             <div class="aion-workflow-subtle-meta">Aion workflow builder · local draft</div>
22011:           </div>
22012:         </div>
22013: 
22014:         <div class="aion-architect-topbar-actions">
22015:           <button type="button" class="secondary-btn" data-workflow-architect-close-canvas-mode="true">Back to canvas</button>
22016:           <button type="button" class="secondary-btn" data-aion-architect-build-mode="describe">Describe workflow</button>
22017:           <button type="button" class="primary-btn" data-workflow-architect-build-review="true">Build review</button>
22018:           <button type="button" class="secondary-btn" data-workflow-architect-load-valid-review="true" disabled>Load to canvas</button>
22019:           <span class="aion-architect-safety-badge" title="Execution: dry-run only. Live send disabled. External writes approval gated. Save requires valid dry-run + confirmation.">
22020:             🔒 Safety locked
22021:           </span>
22022:         </div>
22023:       </div>
22024: 
22025:       <main class="aion-architect-full-canvas">
22026:         ${nodeCanvas}
22027:       </main>

## function getAionWorkflowNodePorts

46564: }
46565: 
46566: function getAionWorkflowRouterRouteOffset(index, total) {
46567:   const middle = (Math.max(1, total) - 1) / 2;
46568:   return Math.round((index - middle) * 260);
46569: }
46570: 
46571: 
46572: function getAionWorkflowNodePorts(node) {
46573:   if (!node) return { inputs: [], outputs: [] };
46574: 
46575:   const isRouter =
46576:     typeof isAionWorkflowRouterNode === "function" &&
46577:     isAionWorkflowRouterNode(node);
46578: 
46579:   const isMerge =
46580:     typeof isAionWorkflowMergeNode === "function" &&
46581:     isAionWorkflowMergeNode(node);
46582: 
46583:   const isBranch =
46584:     typeof isAionWorkflowBranchNode === "function" &&
46585:     isAionWorkflowBranchNode(node);
46586: 
46587:   const routes =
46588:     typeof getAionWorkflowRouterRoutes === "function"
46589:       ? getAionWorkflowRouterRoutes(node)
46590:       : [
46591:           { id: "route_1", label: "1st" },
46592:           { id: "route_2", label: "2nd" },
46593:           { id: "route_3", label: "3rd" },
46594:         ];
46595: 
46596:   if (isMerge) {
46597:     return {
46598:       inputs: routes.map((route, index) => ({
46599:         id: String(route.id),
46600:         label: String(route.label || route.id),
46601:         condition: String(route.id),
46602:         role: "merge_input",
46603:         index,
46604:         total: routes.length,
46605:       })),
46606:       outputs: [
46607:         {
46608:           id: "success",
46609:           label: "Success",
46610:           condition: "success",
46611:           role: "main",
46612:           index: 0,
46613:           total: 1,
46614:         },
46615:       ],
46616:     };
46617:   }
46618: 
46619:   if (isRouter) {
46620:     /*
46621:      * Router uses a single visible fork/output port.
46622:      * Individual route lanes are rendered by routerControlsHtml /
46623:      * renderMissingRouterConnector(), not as detached port circles.
46624:      */
46625:     return {
46626:       inputs: [
46627:         {
46628:           id: "input",
46629:           label: "Input",
46630:           condition: "success",
46631:           role: "main",
46632:           index: 0,
46633:           total: 1,
46634:         },
46635:       ],
46636:       outputs: [
46637:         {
46638:           id: "success",
46639:           label: "Fork",
46640:           condition: "success",
46641:           role: "main",
46642:           index: 0,
46643:           total: 1,
46644:         },
46645:       ],
46646:     };
46647:   }
46648: 
46649:   if (isBranch) {
46650:     return {
46651:       inputs: [
46652:         {
46653:           id: "input",
46654:           label: "Input",
46655:           condition: "success",
46656:           role: "main",
46657:           index: 0,
46658:           total: 1,
46659:         },
46660:       ],
46661:       outputs: [
46662:         {
46663:           id: "true",
46664:           label: "True",
46665:           condition: "true",
46666:           role: "branch",
46667:           index: 0,
46668:           total: 2,
46669:         },
46670:         {
46671:           id: "false",
46672:           label: "Else",
46673:           condition: "false",
46674:           role: "branch",
46675:           index: 1,
46676:           total: 2,
46677:         },
46678:       ],
46679:     };
46680:   }
46681: 
46682:   return {
46683:     inputs: [
46684:       {
46685:         id: "input",
46686:         label: "Input",
46687:         condition: "success",
46688:         role: "main",
46689:         index: 0,
46690:         total: 1,
46691:       },
46692:     ],
46693:     outputs: [
46694:       {
46695:         id: "success",
46696:         label: "Success",
46697:         condition: "success",
46698:         role: "main",
46699:         index: 0,
46700:         total: 1,
46701:       },
46702:     ],
46703:   };
46704: }
46705: 
46706: function getAionWorkflowPortOffset(port) {
46707:   const total = Math.max(1, Number(port?.total || 1));
46708:   const index = Number(port?.index || 0);
46709:   const middle = (total - 1) / 2;
46710: 
46711:   if (total === 1) return 0;
46712: 

## function renderAionGoalEngineContainerProjectionV1

6075:       <div class="aion-provider-capability-grid">
6076:         ${rows || `<div class="empty-state">No provider capability manifest available.</div>`}
6077:       </div>
6078:     </div>
6079:   `;
6080: }
6081: 
6082: 
6083: function renderAionGoalEngineContainerProjectionV1(snapshot = {}) {
6084:   const projection =
6085:     snapshot.goal_engine_container_projection ||
6086:     snapshot.runtime?.goal_engine_container_projection ||
6087:     snapshot.summary?.goal_engine_container_projection ||
6088:     {};
6089: 
6090:   if (!projection || typeof projection !== "object" || projection.trace_type !== "goal_engine_container_projection") {
6091:     return "";
6092:   }
6093: 
6094:   return `
6095:     <div class="panel large-panel aion-goal-engine-container-projection" data-aion-goal-engine-container-projection="true">
6096:       <div class="panel-title">Persistent Goal Engine State</div>
6097:       <div class="list-item-sub" style="margin-bottom:12px;">
6098:         Source: ${projection.persistent_truth_source || "business_containers"} · Boardroom projection only
6099:       </div>
6100: 
6101:       <div class="aion-boardroom-runtime-grid">
6102:         <div><strong>${projection.goal_count || 0}</strong><span>Goals</span></div>
6103:         <div><strong>${projection.active_goal_count || 0}</strong><span>Active goals</span></div>
6104:         <div><strong>${projection.loop_count || 0}</strong><span>Loops</span></div>
6105:         <div><strong>${projection.bounded_loop_count || 0}</strong><span>Bounded loops</span></div>
6106:         <div><strong>${projection.experiment_count || 0}</strong><span>Experiments</span></div>
6107:         <div><strong>${projection.outcome_count || 0}</strong><span>Outcomes</span></div>
6108:         <div><strong>${projection.evidence_count || 0}</strong><span>Evidence</span></div>
6109:         <div><strong>${projection.verified_evidence_count || 0}</strong><span>Verified evidence</span></div>
6110:         <div><strong>${projection.memory_count || 0}</strong><span>Memory records</span></div>
6111:       </div>
6112: 
6113:       <div class="aion-boardroom-subsection">
6114:         <div class="aion-boardroom-note">
6115:           Persistent truth is stored in scoped business containers. The Boardroom only reads this projection.
6116:         </div>
6117:       </div>
6118:     </div>
6119:   `;
6120: }
6121: 
6122: function renderAionGoalEngineVisibleBoardroomPanelsV1(snapshot = {}) {
6123:   const realSource = getAionGoalEngineVisibleBoardroomSourceV1(snapshot);
6124:   const hasRealPayload = realSource && Object.keys(realSource).length > 0;
6125:   const source = hasRealPayload ? realSource : buildAionGoalEngineVisibleDemoPayloadV1();
6126: 
6127:   const panels = [
6128:     typeof renderAionGoalEngineOutcomeEvidenceSummaryV1 === "function"
6129:       ? renderAionGoalEngineOutcomeEvidenceSummaryV1(source.goal_runtime_summary || source)
6130:       : "",
6131:     typeof renderAionGoalEngineCheckpointSummaryV1 === "function"
6132:       ? renderAionGoalEngineCheckpointSummaryV1(source)
6133:       : "",
6134:     typeof renderAionGoalEngineResumeRevalidationSummaryV1 === "function"
6135:       ? renderAionGoalEngineResumeRevalidationSummaryV1(source)
6136:       : "",
6137:     typeof renderAionGoalEngineExperimentRuntimeSummaryV1 === "function"
6138:       ? renderAionGoalEngineExperimentRuntimeSummaryV1(source)
6139:       : "",
6140:     typeof renderAionGoalEngineOrchestratorSummaryV1 === "function"
6141:       ? renderAionGoalEngineOrchestratorSummaryV1(source)
6142:       : "",
6143:     renderAionGoalEngineDecompositionSummaryV1(source),
6144:   ].filter(Boolean).join("");
6145: 
6146:   if (!panels) return "";
6147: 
6148:   return `
6149:     <div class="panel large-panel aion-goal-engine-visible-boardroom-panels" data-aion-goal-engine-visible-boardroom-panels="true">
6150:       <div class="panel-title">Goal Engine Runtime Preview</div>
6151:       <div class="list-item-sub" style="margin-bottom:12px;">
6152:         ${hasRealPayload ? "Live payload from Boardroom runtime snapshot." : "Demo payload visible until backend Boardroom snapshot includes Goal Engine summaries."}
6153:       </div>
6154:       ${panels}
6155:       ${
6156:         typeof renderAionGoalEngineBoardroomVisibilityMountAuditV1 === "function"
6157:           ? renderAionGoalEngineBoardroomVisibilityMountAuditV1(source)
6158:           : ""
6159:       }
6160:     </div>
6161:   `;
6162: }
6163: 
6164: 
6165: /* PHASE 14I LOCK: AgentMap frontend functional wiring batch 1 */
6166: function getDefaultAgentMapDashboardPreviewPayload() {
6167:   return {
6168:     dashboard_version: "aion.agentmap.dashboard.v0.1",
6169:     status: "ready",
6170:     business_id: "home_fixed",
6171:     business_name: "Home Fixed",
6172:     vertical_key: "home_repair",
6173:     agentmap_hash: "b1e09a730891e6cbbf093eee509ebc4eb8c012a5a59fdb40bbe0fb125c98ddbe",
6174:     endpoint_hash: "phase14c-endpoint-preview-bound",
6175:     verification_status: "verified",
6176:     verification_badge: "AgentMap Verified Live",
6177:     hosted_agentmap_url: "/agentmap.json",
6178:     self_hosted_agentmap_url: "/.well-known/agentmap.json",
6179:     install_tag: '<link rel="agentmap" type="application/json" href="/agentmap.json">',
6180:     generated_payload_source: "locked_dashboard_preview",
6181:     machine_discovery_settings: {
6182:       mode: "preview_only",
6183:       hosted_url_enabled: true,
6184:       self_hosted_export_enabled: true,
6185:       human_review_required: true,
6186:       live_execution_enabled: false,
6187:     },
6188:     agentmap_preview: {
6189:       agentmap_version: "aion.agentmap.v0.1",
6190:       business_id: "home_fixed",
6191:       business_name: "Home Fixed",
6192:       vertical_key: "home_repair",
6193:       agentmap_hash: "b1e09a730891e6cbbf093eee509ebc4eb8c012a5a59fdb40bbe0fb125c98ddbe",
6194:       paths: {
6195:         canonical: "/agentmap.json",
6196:         well_known: "/.well-known/agentmap.json",
6197:       },
6198:       safety_profile: {
6199:         preview_only: true,
6200:         read_only: true,
6201:         human_review_required: true,
6202:         live_execution_enabled: false,
6203:       },
6204:       ets_preview: {
6205:         agentmap_extension: "aion.ets_preview.v0.1",
6206:         preview_only: true,
6207:         anti_gaming_locked: false,
6208:         trust_rules_locked: false,
6209:         human_review_required: true,
6210:         live_reputation_mutation_enabled: false,
6211:         public_ranking_enabled: false,
6212:         execution_trust_score_preview: {
6213:           customer_outcome_score: 0,
6214:           system_execution_score: 0,
6215:           customer_outcome_status: "preview_only",
6216:           system_execution_status: "preview_only",
6217:         },
6218:         proof_links: {
6219:           job_trace_id: "job_trace_preview",
6220:           proof_receipt_id: "proof_receipt_preview",
6221:           evidence_ids: ["evidence_preview"],
6222:         },
6223:       },

## function renderAionGoalEngineDecompositionSummaryV1

5966:           bounded: true,
5967:           human_review_required: true,
5968:         },
5969:       ],
5970:     },
5971:   };
5972: }
5973: 
5974: function renderAionGoalEngineDecompositionSummaryV1(source = {}) {
5975:   const machineTrace = source.machine_trace || source.trace || {};
5976:   const summary =
5977:     source.goal_decomposition_runtime_summary ||
5978:     source.goal_engine_decomposition_runtime_summary ||
5979:     machineTrace.goal_decomposition_runtime_summary ||
5980:     machineTrace.goal_engine_decomposition_runtime_summary ||
5981:     {};
5982: 
5983:   if (!summary || typeof summary !== "object" || summary.trace_type !== "goal_decomposition_runtime_summary") {
5984:     return "";
5985:   }
5986: 
5987:   const previews =
5988:     Array.isArray(source.goal_decomposition_previews) ? source.goal_decomposition_previews :
5989:     Array.isArray(source.decomposition_previews) ? source.decomposition_previews :
5990:     Array.isArray(source.child_goal_previews) ? source.child_goal_previews :
5991:     Array.isArray(machineTrace.goal_decomposition_previews) ? machineTrace.goal_decomposition_previews :
5992:     Array.isArray(machineTrace.decomposition_previews) ? machineTrace.decomposition_previews :
5993:     Array.isArray(machineTrace.child_goal_previews) ? machineTrace.child_goal_previews :
5994:     Array.isArray(summary.goal_decomposition_previews) ? summary.goal_decomposition_previews :
5995:     Array.isArray(summary.decomposition_previews) ? summary.decomposition_previews :
5996:     Array.isArray(summary.child_goal_previews) ? summary.child_goal_previews :
5997:     [];
5998: 
5999:   return `
6000:     <div class="aion-boardroom-runtime-summary" data-aion-goal-engine-decomposition-summary="true">
6001:       <div class="section-title">Goal Decomposition Summary</div>
6002:       <div class="aion-boardroom-runtime-grid">
6003:         <div><strong>${summary.decomposition_count || 0}</strong><span>Decompositions</span></div>
6004:         <div><strong>${summary.sub_goal_count || 0}</strong><span>Sub-goals</span></div>
6005:         <div><strong>${summary.bounded_decomposition_count || 0}</strong><span>Bounded</span></div>
6006:         <div><strong>${summary.human_review_required_count || 0}</strong><span>Human review</span></div>
6007:       </div>
6008:       <div class="aion-boardroom-subsection">
6009:         ${
6010:           previews.length
6011:             ? previews.map((item) => `
6012:               <div class="aion-boardroom-trace-row">
6013:                 <strong>${item.decomposition_id || "-"}</strong>
6014:                 <span>parent_goal_id=${item.parent_goal_id || "-"} · decomposition_strategy=${item.decomposition_strategy || "-"}</span>
6015:                 <small>max_depth=${item.max_depth ?? "-"} · max_sub_goals=${item.max_sub_goals ?? "-"}</small>
6016:               </div>
6017:             `).join("")
6018:             : `<div class="muted">No decomposition previews.</div>`
6019:         }
6020:       </div>
6021:     </div>
6022:   `;
6023: }
6024: 
6025: 
6026: 
6027: function renderAionProviderCapabilityManifestV1(snapshot = {}) {
6028:   const manifest =
6029:     snapshot.provider_capability_manifest ||
6030:     snapshot.runtime?.provider_capability_manifest ||
6031:     snapshot.summary?.provider_capability_manifest ||
6032:     null;
6033: 
6034:   if (!manifest || typeof manifest !== "object" || manifest.trace_type !== "provider_capability_manifest") {
6035:     return "";
6036:   }
6037: 
6038:   const providers = manifest.providers && typeof manifest.providers === "object"
6039:     ? Object.values(manifest.providers)
6040:     : [];
6041: 
6042:   const safe = manifest.safe_defaults || {};
6043: 
6044:   const rows = providers.map((provider) => {
6045:     const name = provider.provider || provider.name || "provider";
6046:     const model = provider.default_model || provider.model || "";
6047:     const enabled = provider.enabled ? "Enabled" : "Unavailable";
6048:     const externalWrites = provider.runtime_limits?.external_writes || "unknown";
6049:     const degradation = provider.degradation_mode || "fail_closed";
6050:     const disclosure = provider.disclosure || "";
6051: 
6052:     return `
6053:       <div class="aion-provider-capability-row">
6054:         <div>
6055:           <strong>${escapeHtml(String(name))}</strong>
6056:           <span>${escapeHtml(String(model))}</span>
6057:         </div>
6058:         <div>${escapeHtml(String(enabled))}</div>
6059:         <div>Writes: ${escapeHtml(String(externalWrites))}</div>
6060:         <div>${escapeHtml(String(degradation))}</div>
6061:         <small>${escapeHtml(String(disclosure))}</small>
6062:       </div>
6063:     `;
6064:   }).join("");
6065: 
6066:   return `
6067:     <div class="panel large-panel aion-provider-capability-manifest" data-aion-provider-capability-manifest="true">
6068:       <div class="panel-title">Provider Capability Manifest</div>
6069:       <div class="muted">
6070:         Provider disclosure required · External writes require approval:
6071:         ${safe.external_writes_require_approval ? "yes" : "no"} ·
6072:         Business state mutations require human review:
6073:         ${safe.business_state_mutations_require_human_review ? "yes" : "no"}
6074:       </div>
6075:       <div class="aion-provider-capability-grid">
6076:         ${rows || `<div class="empty-state">No provider capability manifest available.</div>`}
6077:       </div>
6078:     </div>
6079:   `;
6080: }
6081: 
6082: 
6083: function renderAionGoalEngineContainerProjectionV1(snapshot = {}) {
6084:   const projection =
6085:     snapshot.goal_engine_container_projection ||
6086:     snapshot.runtime?.goal_engine_container_projection ||
6087:     snapshot.summary?.goal_engine_container_projection ||
6088:     {};
6089: 
6090:   if (!projection || typeof projection !== "object" || projection.trace_type !== "goal_engine_container_projection") {
6091:     return "";
6092:   }
6093: 
6094:   return `
6095:     <div class="panel large-panel aion-goal-engine-container-projection" data-aion-goal-engine-container-projection="true">
6096:       <div class="panel-title">Persistent Goal Engine State</div>
6097:       <div class="list-item-sub" style="margin-bottom:12px;">
6098:         Source: ${projection.persistent_truth_source || "business_containers"} · Boardroom projection only
6099:       </div>
6100: 
6101:       <div class="aion-boardroom-runtime-grid">
6102:         <div><strong>${projection.goal_count || 0}</strong><span>Goals</span></div>
6103:         <div><strong>${projection.active_goal_count || 0}</strong><span>Active goals</span></div>
6104:         <div><strong>${projection.loop_count || 0}</strong><span>Loops</span></div>
6105:         <div><strong>${projection.bounded_loop_count || 0}</strong><span>Bounded loops</span></div>
6106:         <div><strong>${projection.experiment_count || 0}</strong><span>Experiments</span></div>
6107:         <div><strong>${projection.outcome_count || 0}</strong><span>Outcomes</span></div>
6108:         <div><strong>${projection.evidence_count || 0}</strong><span>Evidence</span></div>
6109:         <div><strong>${projection.verified_evidence_count || 0}</strong><span>Verified evidence</span></div>
6110:         <div><strong>${projection.memory_count || 0}</strong><span>Memory records</span></div>
6111:       </div>
6112: 
6113:       <div class="aion-boardroom-subsection">
6114:         <div class="aion-boardroom-note">

## function getAionGoalEngineVisibleBoardroomSourceV1

5454:     messageTone: "success",
5455:   });
5456: 
5457:   await refreshAll?.();
5458:   requestRender?.();
5459: }
5460: 
5461: 
5462: function getAionGoalEngineVisibleBoardroomSourceV1(snapshot = {}) {
5463:   const runtime =
5464:     snapshot && typeof snapshot === "object" && snapshot.runtime && typeof snapshot.runtime === "object"
5465:       ? snapshot.runtime
5466:       : {};
5467: 
5468:   const summary =
5469:     snapshot && typeof snapshot === "object" && snapshot.summary && typeof snapshot.summary === "object"
5470:       ? snapshot.summary
5471:       : {};
5472: 
5473:   const candidates = [
5474:     runtime.goal_engine_preview_bundle,
5475:     runtime.preview_bundle,
5476:     runtime.goal_engine,
5477:     runtime,
5478:     summary.goal_engine_preview_bundle,
5479:     summary.preview_bundle,
5480:     summary.goal_engine,
5481:     summary,
5482:     snapshot.goal_engine_preview_bundle,
5483:     snapshot.preview_bundle,
5484:     snapshot.goal_engine,
5485:     snapshot,
5486:   ];
5487: 
5488:   for (const candidate of candidates) {
5489:     if (!candidate || typeof candidate !== "object") continue;
5490: 
5491:     if (
5492:       candidate.goal_runtime_summary ||
5493:       candidate.goal_engine_goal_runtime_summary ||
5494:       candidate.checkpoint_runtime_summary ||
5495:       candidate.goal_engine_checkpoint_runtime_summary ||
5496:       candidate.resume_revalidation_summary ||
5497:       candidate.goal_engine_resume_revalidation_summary ||
5498:       candidate.experiment_runtime_summary ||
5499:       candidate.goal_engine_experiment_runtime_summary ||
5500:       candidate.orchestrator_runtime_summary ||
5501:       candidate.goal_engine_orchestrator_runtime_summary ||
5502:       candidate.goal_decomposition_runtime_summary ||
5503:       candidate.goal_engine_decomposition_runtime_summary
5504:     ) {
5505:       return candidate;
5506:     }
5507:   }
5508: 
5509:   return {};
5510: }
5511: 
5512: function buildAionGoalEngineVisibleDemoPayloadV1() {
5513:   const demoEvidencePointer = {
5514:     schema_version: "aion.goal_engine.evidence_pointer.v1",
5515:     trace_type: "evidence_pointer_preview",
5516:     evidence_type: "manual_confirmation",
5517:     source: "boardroom_demo",
5518:     reference_pointer: "manual://boardroom/demo/evidence-001",
5519:     evidence_hash: "b9f2d54d4d5a5f4a8f9c1d7a3e8f0b8b5c6a0e1f2d3c4b5a6978877665544332",
5520:     valid: true,
5521:     resolved: false,
5522:     dry_run_only: true,
5523:     blocked_reasons: [],
5524:     would_read_external: false,
5525:     would_write_external: false,
5526:     would_grant_permission: false,
5527:   };
5528: 
5529:   const demoExperimentEvidence = {
5530:     schema_version: "aion.goal_engine.experiment_result_evidence.v1",
5531:     trace_type: "experiment_result_evidence_preview",
5532:     experiment_id: "experiment_visible_demo",
5533:     goal_id: "goal_visible_demo",
5534:     metric: "reply_rate",
5535:     variants: ["variant_whatsapp", "variant_facebook"],
5536:     variant_evidence_count: {
5537:       variant_whatsapp: 2,
5538:       variant_facebook: 1,
5539:     },
5540:     all_variants_have_evidence: true,
5541:     ready_for_scoring: true,
5542:     dry_run_only: true,
5543:     would_execute: false,
5544:     would_write_external: false,
5545:     would_grant_permission: false,
5546:   };
5547: 
5548:   const demoVariantScore = {
5549:     schema_version: "aion.goal_engine.variant_outcome_score.v1",
5550:     trace_type: "variant_outcome_score_preview",
5551:     experiment_id: "experiment_visible_demo",
5552:     goal_id: "goal_visible_demo",
5553:     metric: "reply_rate",
5554:     winner_declared: false,
5555:     manual_decision_required: true,
5556:     dry_run_only: true,
5557:     variants: [
5558:       {
5559:         variant_id: "variant_whatsapp",
5560:         score: 0.74,
5561:         rank: 1,
5562:         evidence_count: 2,
5563:         confidence: 0.82,
5564:       },
5565:       {
5566:         variant_id: "variant_facebook",
5567:         score: 0.61,
5568:         rank: 2,
5569:         evidence_count: 1,
5570:         confidence: 0.68,
5571:       },
5572:     ],
5573:     blocked_reasons: ["manual_decision_required_before_winner"],
5574:     would_execute: false,
5575:     would_write_external: false,
5576:     would_grant_permission: false,
5577:   };
5578: 
5579:   const demoProviderAudit = {
5580:     trace_type: "provider_audit",
5581:     provider: "local",
5582:     model: "gemma4:e2b",
5583:     capability: "drafting",
5584:     ok: true,
5585:     error_code: null,
5586:     fallback_used: false,
5587:     latency_ms: 12,
5588:     local_only: true,
5589:     external_writes: "blocked",
5590:     business_state_mutation: "blocked",
5591:     capability_manifest_checked: true,
5592:     failed_closed: false,
5593:     workspace_id: "demo_workspace",
5594:     task_id: "demo_task",
5595:   };
5596: 
5597:   const demoMemoryRuntimeSummary = {
5598:     schema_version: "aion.goal_engine.memory_runtime_summary.v1",
5599:     trace_type: "memory_runtime_summary",
5600:     dry_run_only: true,
5601:     write_guard: "human_review",
5602:     read_guard: "allow",

## function buildAionGoalEngineVisibleDemoPayloadV1

5504:     ) {
5505:       return candidate;
5506:     }
5507:   }
5508: 
5509:   return {};
5510: }
5511: 
5512: function buildAionGoalEngineVisibleDemoPayloadV1() {
5513:   const demoEvidencePointer = {
5514:     schema_version: "aion.goal_engine.evidence_pointer.v1",
5515:     trace_type: "evidence_pointer_preview",
5516:     evidence_type: "manual_confirmation",
5517:     source: "boardroom_demo",
5518:     reference_pointer: "manual://boardroom/demo/evidence-001",
5519:     evidence_hash: "b9f2d54d4d5a5f4a8f9c1d7a3e8f0b8b5c6a0e1f2d3c4b5a6978877665544332",
5520:     valid: true,
5521:     resolved: false,
5522:     dry_run_only: true,
5523:     blocked_reasons: [],
5524:     would_read_external: false,
5525:     would_write_external: false,
5526:     would_grant_permission: false,
5527:   };
5528: 
5529:   const demoExperimentEvidence = {
5530:     schema_version: "aion.goal_engine.experiment_result_evidence.v1",
5531:     trace_type: "experiment_result_evidence_preview",
5532:     experiment_id: "experiment_visible_demo",
5533:     goal_id: "goal_visible_demo",
5534:     metric: "reply_rate",
5535:     variants: ["variant_whatsapp", "variant_facebook"],
5536:     variant_evidence_count: {
5537:       variant_whatsapp: 2,
5538:       variant_facebook: 1,
5539:     },
5540:     all_variants_have_evidence: true,
5541:     ready_for_scoring: true,
5542:     dry_run_only: true,
5543:     would_execute: false,
5544:     would_write_external: false,
5545:     would_grant_permission: false,
5546:   };
5547: 
5548:   const demoVariantScore = {
5549:     schema_version: "aion.goal_engine.variant_outcome_score.v1",
5550:     trace_type: "variant_outcome_score_preview",
5551:     experiment_id: "experiment_visible_demo",
5552:     goal_id: "goal_visible_demo",
5553:     metric: "reply_rate",
5554:     winner_declared: false,
5555:     manual_decision_required: true,
5556:     dry_run_only: true,
5557:     variants: [
5558:       {
5559:         variant_id: "variant_whatsapp",
5560:         score: 0.74,
5561:         rank: 1,
5562:         evidence_count: 2,
5563:         confidence: 0.82,
5564:       },
5565:       {
5566:         variant_id: "variant_facebook",
5567:         score: 0.61,
5568:         rank: 2,
5569:         evidence_count: 1,
5570:         confidence: 0.68,
5571:       },
5572:     ],
5573:     blocked_reasons: ["manual_decision_required_before_winner"],
5574:     would_execute: false,
5575:     would_write_external: false,
5576:     would_grant_permission: false,
5577:   };
5578: 
5579:   const demoProviderAudit = {
5580:     trace_type: "provider_audit",
5581:     provider: "local",
5582:     model: "gemma4:e2b",
5583:     capability: "drafting",
5584:     ok: true,
5585:     error_code: null,
5586:     fallback_used: false,
5587:     latency_ms: 12,
5588:     local_only: true,
5589:     external_writes: "blocked",
5590:     business_state_mutation: "blocked",
5591:     capability_manifest_checked: true,
5592:     failed_closed: false,
5593:     workspace_id: "demo_workspace",
5594:     task_id: "demo_task",
5595:   };
5596: 
5597:   const demoMemoryRuntimeSummary = {
5598:     schema_version: "aion.goal_engine.memory_runtime_summary.v1",
5599:     trace_type: "memory_runtime_summary",
5600:     dry_run_only: true,
5601:     write_guard: "human_review",
5602:     read_guard: "allow",
5603:     allow_forgetting: true,
5604:     allow_consolidation: false,
5605:     memory_tier_counts: {
5606:       working: 1,
5607:       goal: 1,
5608:       long_term_advisory: 0,
5609:     },
5610:     blocked_reasons: ["memory_writes_remain_dry_run_only_until_guarded_approval"],
5611:     would_write_memory: false,
5612:     would_grant_permission: false,
5613:   };
5614: 
5615:   const demoProviderCapabilityManifest = {
5616:     schema_version: "aion.business.provider_capability_manifest.v1",
5617:     trace_type: "provider_capability_manifest",
5618:     providers: {
5619:       local: {
5620:         provider: "local",
5621:         default_model: "gemma",
5622:         configured: true,
5623:         capabilities: ["drafting", "rewrite", "summarization", "analysis", "classification", "planning"],
5624:         supports_long_running_sessions: true,
5625:         supports_checkpoint_resume: true,
5626:         supports_sandboxed_execution: true,
5627:         supports_outcome_evaluation: false,
5628:         supports_memory_dreaming: true,
5629:         supports_multi_agent_orchestration: false,
5630:         supports_mcp_private_connectors: false,
5631:         max_tokens: 8192,
5632:         max_cost_per_task: 0,
5633:         runtime_limits: {
5634:           network: "local_only",
5635:           external_writes: "blocked",
5636:           requires_human_review_for_business_state: true,
5637:         },
5638:         fallback_provider: "openai",
5639:         degradation_mode: "local_first_then_cloud_if_allowed",
5640:       },
5641:       openai: {
5642:         provider: "openai",
5643:         default_model: "gpt-4.1-mini",
5644:         configured: false,
5645:         capabilities: ["drafting", "rewrite", "summarization", "analysis", "reasoning", "planning", "classification"],
5646:         supports_outcome_evaluation: true,
5647:         supports_multi_agent_orchestration: true,
5648:         max_tokens: 128000,
5649:         max_cost_per_task: 5,
5650:         runtime_limits: {
5651:           network: "cloud",
5652:           external_writes: "approval_required",

## function renderAionPilotCockpitPanel

13739:         safe_alternative: "Prepare a deployment preview only.",
13740:         required_approval: "exact_payload_approval",
13741:       },
13742:     ],
13743:   };
13744: }
13745: 
13746: 
13747: function renderAionPilotCockpitPanel(snapshot = getAionPilotCockpitSnapshot()) {
13748:   return renderAionPilotSimpleTaskStream(snapshot);
13749: }
13750: 
13751: function installAionPilotCockpitStyles() {
13752:   if (document.getElementById("aion-pilot-cockpit-styles")) return;
13753:   const style = document.createElement("style");
13754:   style.id = "aion-pilot-cockpit-styles";
13755:   style.textContent = `
13756:     .aion-pilot-cockpit {
13757:       margin-top: 18px;
13758:       border: 1px solid rgba(0,0,0,.16);
13759:       background: rgba(255,255,255,.34);
13760:       padding: 18px;
13761:       display: grid;
13762:       gap: 16px;
13763:     }
13764:     .aion-pilot-header {
13765:       display: flex;
13766:       justify-content: space-between;
13767:       gap: 18px;
13768:       align-items: flex-start;
13769:     }
13770:     .aion-pilot-header h2 {
13771:       margin: 3px 0 6px;
13772:       font-size: 28px;
13773:     }
13774:     .aion-pilot-status {
13775:       border: 1px solid rgba(0,0,0,.25);
13776:       padding: 6px 10px;
13777:       font-size: 11px;
13778:       letter-spacing: .14em;
13779:       font-weight: 800;
13780:     }
13781:     .aion-pilot-safety-banner {
13782:       border: 1px solid rgba(0,0,0,.18);
13783:       background: rgba(96,119,103,.12);
13784:       padding: 12px 14px;
13785:       display: grid;
13786:       gap: 4px;
13787:     }
13788:     .aion-pilot-grid {
13789:       display: grid;
13790:       grid-template-columns: minmax(0,1fr) minmax(0,1fr);
13791:       gap: 14px;
13792:     }
13793:     .aion-pilot-grid-three {
13794:       grid-template-columns: minmax(0,1fr) minmax(0,1fr) minmax(0,1fr);
13795:     }
13796:     .aion-pilot-panel,
13797:     .aion-pilot-artifact-card,
13798:     .aion-pilot-blocked-card,
13799:     .aion-pilot-map-node {
13800:       border: 1px solid rgba(0,0,0,.14);
13801:       background: rgba(255,255,255,.42);
13802:       padding: 12px;
13803:       display: grid;
13804:       gap: 9px;
13805:       min-width: 0;
13806:     }
13807:     .aion-pilot-panel textarea,
13808:     .aion-pilot-feedback textarea {
13809:       width: 100%;
13810:       min-height: 86px;
13811:       border: 1px solid rgba(0,0,0,.18);
13812:       background: rgba(255,255,255,.55);
13813:       padding: 10px;
13814:       box-sizing: border-box;
13815:       font: inherit;
13816:     }
13817:     .aion-pilot-meta-row {
13818:       display: grid;
13819:       grid-template-columns: 120px minmax(0,1fr);
13820:       gap: 8px;
13821:       border-top: 1px solid rgba(0,0,0,.08);
13822:       padding-top: 7px;
13823:     }
13824:     .aion-pilot-meta-row span { color: #777; }
13825:     .aion-pilot-meta-row code {
13826:       white-space: normal;
13827:       overflow-wrap: anywhere;
13828:       font-size: 12px;
13829:       font-weight: 700;
13830:     }
13831:     .aion-pilot-actions,
13832:     .aion-pilot-feedback {
13833:       display: flex;
13834:       gap: 8px;
13835:       flex-wrap: wrap;
13836:       align-items: center;
13837:     }
13838:     .aion-pilot-cockpit button {
13839:       border: 1px solid rgba(0,0,0,.22);
13840:       background: rgba(255,255,255,.52);
13841:       padding: 9px 12px;
13842:       font-weight: 800;
13843:       letter-spacing: .08em;
13844:       cursor: pointer;
13845:     }
13846:     [data-aion-pilot-create-draft-mission] {
13847:       background: rgba(96,119,103,.92) !important;
13848:       color: white;
13849:     }
13850: 
13851:     .aion-pilot-simple-dashboard {
13852:       margin-top: 18px;
13853:       border: 1px solid rgba(0,0,0,.14);
13854:       background: rgba(255,255,255,.36);
13855:       padding: 18px;
13856:       display: grid;
13857:       gap: 16px;
13858:     }
13859:     .aion-pilot-simple-hero {
13860:       display: flex;
13861:       justify-content: space-between;
13862:       gap: 18px;
13863:       align-items: flex-start;
13864:     }
13865:     .aion-pilot-simple-hero h2 {
13866:       margin: 4px 0 6px;
13867:       font-size: 30px;
13868:       letter-spacing: -0.03em;
13869:     }
13870:     .aion-pilot-user-flow {
13871:       display: grid;
13872:       gap: 14px;
13873:     }
13874:     .aion-pilot-step-card {
13875:       display: grid;
13876:       grid-template-columns: 42px minmax(0,1fr);
13877:       gap: 14px;
13878:       padding: 16px;
13879:       border: 1px solid rgba(0,0,0,.13);
13880:       background: rgba(255,255,255,.52);
13881:       min-width: 0;
13882:     }
13883:     .aion-pilot-step-number {
13884:       width: 32px;
13885:       height: 32px;
13886:       border-radius: 999px;
13887:       display: flex;

## function getAionPilotCockpitSnapshot

13690: 
13691: 
13692: /* END PHASE 21P LOCK */
13693: 
13694: 
13695: /* END PHASE 21O LOCK */
13696: 
13697: 
13698: function getAionPilotCockpitSnapshot() {
13699:   const pilotState = getAionPilotFrontendInteractionState();
13700: 
13701:   return {
13702:     status: pilotState.status || "idle",
13703:     mode: "preview_only",
13704:     identity: "AION Pilot native runtime executor, not UI automation",
13705:     business_id: "home-fixed",
13706:     mission_id: "pilot_demo_pdf_mission",
13707:     mission_run_id: "pilot_demo_run_preview",
13708:     step_id: "compose_document",
13709:     request_placeholder: "Build me a PDF document with X data",
13710:     save_path: pilotState.artifact_path || "business/home-fixed/missions/pilot_demo_pdf_mission/runs/pilot_demo_run_preview/artifacts/draft-document.pdf",
13711:     safety_message: "AION stopped itself before doing anything risky.",
13712:     no_live_side_effects_message: "No money, post, deploy, external send, booking, escrow or reputation mutation without exact approval.",
13713:     plan_steps: [
13714:       ["step_1", "autonomous_preview", "Understand document request", "preview"],
13715:       ["step_2", "autonomous_preview", "Draft document structure", "preview"],
13716:       ["step_3", "autonomous_preview", "Create draft PDF artifact inside business container", "preview"],
13717:       ["step_4", "approval_required", "Publish, send, deploy or spend money", "blocked"],
13718:     ],
13719:     artifacts: [
13720:       {
13721:         type: "pdf",
13722:         title: "Draft PDF document",
13723:         status: "draft_preview",
13724:         path: pilotState.artifact_path || "business/home-fixed/missions/pilot_demo_pdf_mission/runs/pilot_demo_run_preview/artifacts/draft-document.pdf",
13725:         artifact_hash: pilotState.artifact_hash || "sha256:preview_artifact_hash",
13726:         receipt_hash: pilotState.receipt_hash || "sha256:preview_receipt_hash",
13727:       },
13728:     ],
13729:     blocked_actions: [
13730:       {
13731:         action_type: "external_send",
13732:         blocked_reason: "External sending requires exact payload approval.",
13733:         safe_alternative: "Keep the PDF as a draft preview inside the business container.",
13734:         required_approval: "exact_payload_approval",
13735:       },
13736:       {
13737:         action_type: "production_deploy",
13738:         blocked_reason: "Deployment is a live external side effect.",
13739:         safe_alternative: "Prepare a deployment preview only.",
13740:         required_approval: "exact_payload_approval",
13741:       },
13742:     ],
13743:   };
13744: }
13745: 
13746: 
13747: function renderAionPilotCockpitPanel(snapshot = getAionPilotCockpitSnapshot()) {
13748:   return renderAionPilotSimpleTaskStream(snapshot);
13749: }
13750: 
13751: function installAionPilotCockpitStyles() {
13752:   if (document.getElementById("aion-pilot-cockpit-styles")) return;
13753:   const style = document.createElement("style");
13754:   style.id = "aion-pilot-cockpit-styles";
13755:   style.textContent = `
13756:     .aion-pilot-cockpit {
13757:       margin-top: 18px;
13758:       border: 1px solid rgba(0,0,0,.16);
13759:       background: rgba(255,255,255,.34);
13760:       padding: 18px;
13761:       display: grid;
13762:       gap: 16px;
13763:     }
13764:     .aion-pilot-header {
13765:       display: flex;
13766:       justify-content: space-between;
13767:       gap: 18px;
13768:       align-items: flex-start;
13769:     }
13770:     .aion-pilot-header h2 {
13771:       margin: 3px 0 6px;
13772:       font-size: 28px;
13773:     }
13774:     .aion-pilot-status {
13775:       border: 1px solid rgba(0,0,0,.25);
13776:       padding: 6px 10px;
13777:       font-size: 11px;
13778:       letter-spacing: .14em;
13779:       font-weight: 800;
13780:     }
13781:     .aion-pilot-safety-banner {
13782:       border: 1px solid rgba(0,0,0,.18);
13783:       background: rgba(96,119,103,.12);
13784:       padding: 12px 14px;
13785:       display: grid;
13786:       gap: 4px;
13787:     }
13788:     .aion-pilot-grid {
13789:       display: grid;
13790:       grid-template-columns: minmax(0,1fr) minmax(0,1fr);
13791:       gap: 14px;
13792:     }
13793:     .aion-pilot-grid-three {
13794:       grid-template-columns: minmax(0,1fr) minmax(0,1fr) minmax(0,1fr);
13795:     }
13796:     .aion-pilot-panel,
13797:     .aion-pilot-artifact-card,
13798:     .aion-pilot-blocked-card,
13799:     .aion-pilot-map-node {
13800:       border: 1px solid rgba(0,0,0,.14);
13801:       background: rgba(255,255,255,.42);
13802:       padding: 12px;
13803:       display: grid;
13804:       gap: 9px;
13805:       min-width: 0;
13806:     }
13807:     .aion-pilot-panel textarea,
13808:     .aion-pilot-feedback textarea {
13809:       width: 100%;
13810:       min-height: 86px;
13811:       border: 1px solid rgba(0,0,0,.18);
13812:       background: rgba(255,255,255,.55);
13813:       padding: 10px;
13814:       box-sizing: border-box;
13815:       font: inherit;
13816:     }
13817:     .aion-pilot-meta-row {
13818:       display: grid;
13819:       grid-template-columns: 120px minmax(0,1fr);
13820:       gap: 8px;
13821:       border-top: 1px solid rgba(0,0,0,.08);
13822:       padding-top: 7px;
13823:     }
13824:     .aion-pilot-meta-row span { color: #777; }
13825:     .aion-pilot-meta-row code {
13826:       white-space: normal;
13827:       overflow-wrap: anywhere;
13828:       font-size: 12px;
13829:       font-weight: 700;
13830:     }
13831:     .aion-pilot-actions,
13832:     .aion-pilot-feedback {
13833:       display: flex;
13834:       gap: 8px;
13835:       flex-wrap: wrap;
13836:       align-items: center;
13837:     }
13838:     .aion-pilot-cockpit button {

## function getAionPilotFrontendInteractionState

8847: 
8848: 
8849: 
8850: /* PHASE 21X LOCK: Real frontend Pilot cockpit mount */
8851: 
8852: 
8853: /* PHASE 21N LOCK: Pilot frontend interaction smoke */
8854: 
8855: function getAionPilotFrontendInteractionState() {
8856:   if (!window.__aionPilotFrontendInteractionState) {
8857:     window.__aionPilotFrontendInteractionState = {
8858:       status: "idle",
8859:       last_request: "",
8860:       draft_created: false,
8861:       stream_events: [],
8862:       artifact_status: "draft_preview",
8863:       artifact_hash: "sha256:preview_artifact_hash",
8864:       receipt_hash: "sha256:preview_receipt_hash",
8865:       replay_hash: "sha256:preview_replay_hash",
8866:       proof_hash: "sha256:preview_proof_hash",
8867:       blocked_live_actions: [
8868:         "external_send",
8869:         "production_deploy",
8870:         "payment",
8871:         "public_post",
8872:         "booking",
8873:         "escrow",
8874:       ],
8875:     };
8876:   }
8877: 
8878:   return window.__aionPilotFrontendInteractionState;
8879: }
8880: 
8881: function createAionPilotFrontendDraftMission() {
8882:   const pilotState = getAionPilotFrontendInteractionState();
8883:   const input = document.querySelector("[data-aion-pilot-mission-input]");
8884:   const persistentInput = document.querySelector("[data-aion-phase23y-persistent-pilot-terminal-input]");
8885:   const requestText = String(input?.value || persistentInput?.value || pilotState.last_request || "").trim() || "Build me a PDF document with X data";
8886: 
8887:   pilotState.status = "plan_ready";
8888:   if (applyAionPilotCommandBarRevisionIfActive(requestText)) {
8889:     return pilotState;
8890:   }
8891: 
8892:   pilotState.last_request = requestText;
8893:   pilotState.draft_created = true;
8894:   pilotState.plan = buildAionPilotUniversalPlan(requestText);
8895:   const activePilotDepartmentScope =
8896:     typeof getSelectedLiveDepartmentKey === "function"
8897:       ? normaliseAionDepartmentPilotKey(getSelectedLiveDepartmentKey())
8898:       : "pilot";
8899:   pilotState.department_scope = ["aion", "pilot"].includes(activePilotDepartmentScope)
8900:     ? "pilot"
8901:     : activePilotDepartmentScope;
8902:   if (
8903:     pilotState.department_scope !== "pilot" &&
8904:     typeof updateAionDepartmentIntelligence === "function"
8905:   ) {
8906:     updateAionDepartmentIntelligence(pilotState.department_scope, {
8907:       status: "plan_ready",
8908:       plan: {
8909:         title: pilotState.plan?.title || "Department Pilot plan",
8910:         task_type: pilotState.plan?.task_type || "general_task",
8911:         goal: requestText,
8912:         approval_required: true,
8913:         live_external_actions_blocked: true,
8914:         source: "central_pilot_department_scope",
8915:       },
8916:       boardroom_summary: `${runtimeShared.getDepartmentLabel(pilotState.department_scope)} Pilot has prepared a scoped plan preview. No live external action has been taken.`,
8917:       last_updated: new Date().toISOString(),
8918:     });
8919:   }
8920:   pilotState.artifact_status = "draft_preview";
8921:   pilotState.artifact_hash = "sha256:frontend_draft_artifact_preview";
8922:   pilotState.receipt_hash = "sha256:frontend_draft_receipt_preview";
8923:   pilotState.replay_hash = "sha256:frontend_draft_replay_preview";
8924:   pilotState.proof_hash = "sha256:frontend_draft_proof_preview";
8925:   pilotState.contract_status = "draft_contract";
8926:   pilotState.safe_work_status = "waiting_approval";
8927:   pilotState.safe_work_approved = false;
8928:   pilotState.generated_output_text = "";
8929:   pilotState.step_outputs = [];
8930:   pilotState.current_step_index = 0;
8931:   pilotState.backend_artifact_status = "";
8932:   pilotState.backend_artifact_error = "";
8933:   pilotState.output_panel_open = false;
8934:   pilotState.output_panel_kind = "";
8935:   pilotState.output_panel_title = "";
8936:   pilotState.output_panel_body = "";
8937:   const universalPlan = pilotState.plan || buildAionPilotUniversalPlan(requestText);
8938: 
8939:   pilotState.stream_events = [
8940:     {
8941:       type: "mission_composer",
8942:       label: "Work package created",
8943:       detail: requestText,
8944:       status: "draft_only",
8945:     },
8946:     {
8947:       type: "artifact_preview",
8948:       label: getAionPilotOutputPreparedLabel(universalPlan),
8949:       detail: getAionPilotOutputPreparedDetail(universalPlan),
8950:       status: "draft_preview",
8951:     },
8952:     {
8953:       type: "safety_block",
8954:       label: "Live external actions blocked",
8955:       detail: "No send, deploy, payment, post, booking or escrow without exact approval",
8956:       status: "blocked",
8957:     },
8958:     {
8959:       type: "central_aion_assessment_hook",
8960:       label: "AION assessment hook prepared",
8961:       detail: `Assessment confidence ${universalPlan.central_business_assessment?.confidence || "none"} · action proposals ${(universalPlan.central_execution_queue_proposal || []).length}`,
8962:       status: "proposal_only",
8963:     },
8964:   ];
8965: 
8966: 
8967:   if (typeof fetchAionLrmPilotContextPreviewIntoPilotState === "function") {
8968:     fetchAionLrmPilotContextPreviewIntoPilotState({
8969:       business_id: "home-fixed",
8970:       mission_id: "pilot_demo_pdf_mission",
8971:       mission_run_id: "pilot_demo_run_preview",
8972:     }).catch((error) => {
8973:       const state = getAionPilotFrontendInteractionState();
8974:       state.lrm_context_status = "error";
8975:       state.lrm_context_error = String(error?.message || error || "LRM context preview failed");
8976:       if (typeof requestRender === "function") {
8977:         requestRender();
8978:       }
8979:     });
8980:   }
8981: 
8982:   if (typeof requestRender === "function") {
8983:     requestRender();
8984:   }
8985: 
8986:   return pilotState;
8987: }
8988: 
8989: function renderAionPilotFrontendStreamEvents(pilotState = getAionPilotFrontendInteractionState()) {
8990:   const events = Array.isArray(pilotState.stream_events) ? pilotState.stream_events : [];
8991: 
8992:   if (!events.length) {
8993:     return `
8994:       <p>Private reasoning hidden.</p>
8995:       <p>Visible actions, receipts, paths and blocked actions will appear here.</p>

## function renderAionDepartmentScopedPilotSurface

29350:             </div>
29351:           </div>
29352:         `).join("")
29353:       }
29354:     </div>
29355:   `;
29356: }
29357: 
29358: function renderAionDepartmentScopedPilotSurface(
29359:   departmentKey = "",
29360:   selectedRuns = [],
29361:   selectedAgentCard = null,
29362:   includeWorkflowPanels = true,
29363: ) {
29364:   const key = normaliseAionDepartmentPilotKey(departmentKey);
29365:   const label = runtimeShared.getDepartmentLabel(key);
29366:   const profile = getAionDepartmentPilotProfile(key);
29367:   const entry = getAionDepartmentPilotLedgerEntry(key);
29368:   const status = getAionDepartmentPilotStatus(key);
29369:   const runs = Array.isArray(selectedRuns) ? selectedRuns : getDepartmentRuns(key);
29370:   const tasks = Array.isArray(entry.tasks) ? entry.tasks : [];
29371:   const evidence = Array.isArray(entry.evidence) ? entry.evidence : [];
29372:   const receipts = Array.isArray(entry.receipts) ? entry.receipts : [];
29373:   const planReady = entry.plan && typeof entry.plan === "object" && Object.keys(entry.plan).length > 0;
29374: 
29375:   const completion =
29376:     typeof getAionDepartmentPilotCompletion === "function"
29377:       ? getAionDepartmentPilotCompletion(key)
29378:       : { answered: 0, total: 0, missing: [] };
29379: 
29380:   const approval =
29381:     typeof getAionDepartmentPilotApprovalState === "function"
29382:       ? getAionDepartmentPilotApprovalState(key)
29383:       : { status: "not_requested" };
29384: 
29385:   const resultStatus =
29386:     typeof getAionDepartmentResultEvidenceStatus === "function"
29387:       ? getAionDepartmentResultEvidenceStatus(entry)
29388:       : "missing";
29389: 
29390:   const specialistPlan = entry.specialist_plan || entry.plan?.specialist || null;
29391:   const nextSafeTask =
29392:     typeof getAionDepartmentPilotNextSafeTask === "function"
29393:       ? getAionDepartmentPilotNextSafeTask(key)
29394:       : null;
29395: 
29396:   const nextInstruction =
29397:     completion.answered === 0
29398:       ? `Start with ${label} discovery. Fill the fields below and press “Save discovery to ledger”.`
29399:       : !planReady
29400:         ? `Build the ${label} plan draft from the saved discovery.`
29401:         : approval.status !== "approved"
29402:           ? `Approve the ${label} plan, then build or run the safe queue.`
29403:           : nextSafeTask
29404:             ? `Run the next safe internal ${label} task. It will write results, evidence and receipts back to the Boardroom.`
29405:             : resultStatus === "results_available"
29406:               ? `${label} has Boardroom-visible results. Review the Boardroom assessment feed.`
29407:               : `Build or run the ${label} safe task queue.`;
29408: 
29409:   return `
29410:     <div
29411:       class="dashboard-shell"
29412:       data-aion-department-scoped-pilot="${escapeHtml(key)}"
29413:       data-aion-phase25b-department-scoped-pilot="true"
29414:       data-aion-phase25j-department-pilot-guided-workflow="true"
29415:     >
29416:       <section class="panel large-panel" style="background:#ffffff;">
29417:         <div class="surface-eyebrow">Department Pilot</div>
29418:         <div class="panel-title">${escapeHtml(profile.title)}</div>
29419:         <div class="helper-text">${escapeHtml(profile.purpose)}</div>
29420: 
29421:         <div class="notice warning" style="margin-top:12px;">
29422:           <strong>Next step:</strong> ${escapeHtml(nextInstruction)}
29423:         </div>
29424: 
29425:         <div class="card-grid" style="margin-top:9px;">
29426:           ${renderDashboardMetricCard("1. Discovery", `${completion.answered}/${completion.total}`, "Saved to ledger")}
29427:           ${renderDashboardMetricCard("2. Plan", planReady ? "ready" : "missing", "Draft only")}
29428:           ${renderDashboardMetricCard("3. Approval", approval.status || "not requested", "Human gated")}
29429:           ${renderDashboardMetricCard("4. Safe Queue", tasks.length, nextSafeTask ? "task ready" : "none ready")}
29430:           ${renderDashboardMetricCard("5. Evidence", evidence.length, "Boardroom proof")}
29431:           ${renderDashboardMetricCard("6. Receipts", receipts.length, "Replay / audit")}
29432:         </div>
29433: 
29434:         <div class="list-wrap" style="margin-top:9px;">
29435:           <div class="list-item">
29436:             <div class="list-item-title">How this department Pilot works</div>
29437:             <div class="list-item-sub">
29438:               Discovery, plan drafts, approvals, safe queue tasks, results, evidence and receipts all write into
29439:               <code>aion.departmentIntelligence.${escapeHtml(key)}</code>. The Boardroom reads that same ledger.
29440:             </div>
29441:           </div>
29442:           <div class="list-item">
29443:             <div class="list-item-title">Safety boundary</div>
29444:             <div class="list-item-sub">
29445:               This screen does not send, publish, spend, book, invoice, deploy or mutate external systems.
29446:               It only creates internal previews until exact human approval is added for a specific live action.
29447:             </div>
29448:           </div>
29449:         </div>
29450:       </section>
29451: 
29452:       ${
29453:         includeWorkflowPanels
29454:           ? `
29455:             ${renderAionDepartmentPilotPhase25CPanel(key)}
29456:             ${renderAionDepartmentPilotPhase25DPanel(key)}
29457:             ${renderAionDepartmentPilotPhase25EPanel(key)}
29458:             ${renderAionDepartmentPilotPhase25FPanel(key)}
29459:           `
29460:           : ""
29461:       }
29462: 
29463:       <div class="two-col">
29464:         <div class="panel large-panel">
29465:           <div class="panel-title">Discovery gaps</div>
29466:           ${renderAionDepartmentPilotMissingList(key)}
29467:         </div>
29468: 
29469:         <div class="panel large-panel">
29470:           <div class="panel-title">Boardroom feed</div>
29471:           <div class="list-item">
29472:             <div class="list-item-title">Current summary</div>
29473:             <div class="list-item-sub">${escapeHtml(getAionDepartmentPilotBoardroomSummary(key))}</div>
29474:             <div class="badge-row">
29475:               ${renderStatusBadge(status)}
29476:               <span class="badge">Result ${escapeHtml(resultStatus)}</span>
29477:               <span class="badge">Specialist ${specialistPlan ? "ready" : "missing"}</span>
29478:             </div>
29479:           </div>
29480:           <div class="list-item">
29481:             <div class="list-item-title">Where to see it working</div>
29482:             <div class="list-item-sub">
29483:               Open Boardroom Flat View for the Department Intelligence, Assessment Feed and Cross-Department Review panels.
29484:               Open Spatial Boardroom for the same department status as spatial seat intelligence.
29485:             </div>
29486:           </div>
29487:         </div>
29488:       </div>
29489:     </div>
29490:   `;
29491: }
29492: 
29493: 
29494: 
29495: function applyAionDepartmentPilotAction(departmentKey = "", action = "") {
29496:   const key = normaliseAionDepartmentPilotKey(departmentKey);
29497:   const profile = getAionDepartmentPilotProfile(key);
29498:   const now = new Date().toISOString();

## function buildAionDepartmentPilotPlanDraft

29730: 
29731:   if (options.render !== false && typeof requestRender === "function") {
29732:     requestRender();
29733:   }
29734: 
29735:   return nextEntry;
29736: }
29737: 
29738: function buildAionDepartmentPilotPlanDraft(departmentKey = "", options = {}) {
29739:   const key = String(departmentKey || "").trim().toLowerCase();
29740:   if (!key) return {};
29741: 
29742:   const foundation =
29743:     typeof getApprovedSmallBusinessFoundationContext === "function"
29744:       ? getApprovedSmallBusinessFoundationContext()
29745:       : {};
29746:   const current = options.saveDiscoveryFirst === false
29747:     ? getAionDepartmentLedgerEntry(key)
29748:     : saveAionDepartmentPilotDiscovery(key, { render: false });
29749: 
29750:   const discovery = asRecord(current.discovery) || {};
29751:   const label = runtimeShared.getDepartmentLabel(key);
29752:   const businessName = foundation.business_name || foundation.name || state.workspaceId || "the business";
29753:   const primaryGoal = foundation.primary_goal || "improve business performance";
29754: 
29755:   const actionItems = getAionDepartmentPilotDiscoveryTemplate(key)
29756:     .filter(([fieldKey]) => String(discovery[fieldKey] || "").trim())
29757:     .slice(0, 5)
29758:     .map(([fieldKey, fieldLabel]) => ({
29759:       id: `${key}_${fieldKey}_action`,
29760:       title: `${fieldLabel} follow-up`,
29761:       detail: String(discovery[fieldKey] || "").trim(),
29762:       status: "draft_preview",
29763:       approval_required: true,
29764:     }));
29765: 
29766:   const plan = {
29767:     department: key,
29768:     title: `${label} Pilot plan`,
29769:     business_name: businessName,
29770:     objective: `${label} plan for ${businessName}: ${primaryGoal}`,
29771:     discovery_used: discovery,
29772:     action_items: actionItems.length
29773:       ? actionItems
29774:       : [
29775:           {
29776:             id: `${key}_discovery_required`,
29777:             title: "Complete discovery before planning",
29778:             detail: "Pilot needs more department context before creating a useful plan.",
29779:             status: "blocked_waiting_discovery",
29780:             approval_required: false,
29781:           },
29782:         ],
29783:     approval_boundary: [
29784:       "No external sending",
29785:       "No public posting",
29786:       "No ad spend",
29787:       "No booking",
29788:       "No payment",
29789:       "No production deploy",
29790:       "No live system mutation",
29791:     ],
29792:     created_at: new Date().toISOString(),
29793:   };
29794: 
29795:   const nextEntry = {
29796:     ...current,
29797:     status: "plan_ready",
29798:     plan,
29799:     last_updated: new Date().toISOString(),
29800:   };
29801: 
29802:   nextEntry.boardroom_summary = buildAionDepartmentBoardroomSummary(key, nextEntry);
29803: 
29804:   if (typeof updateAionDepartmentIntelligence === "function") {
29805:     updateAionDepartmentIntelligence(key, nextEntry);
29806:   }
29807: 
29808:   if (options.render !== false && typeof requestRender === "function") {
29809:     requestRender();
29810:   }
29811: 
29812:   return nextEntry;
29813: }
29814: 
29815: function buildAionDepartmentPilotSafeTaskQueue(departmentKey = "", options = {}) {
29816:   const key = String(departmentKey || "").trim().toLowerCase();
29817:   if (!key) return {};
29818: 
29819:   const current = options.buildPlanFirst === false
29820:     ? getAionDepartmentLedgerEntry(key)
29821:     : buildAionDepartmentPilotPlanDraft(key, { render: false });
29822: 
29823:   const plan = asRecord(current.plan) || {};
29824:   const actions = Array.isArray(plan.action_items) ? plan.action_items : [];
29825: 
29826:   const tasks = actions.map((item, index) => ({
29827:     id: item.id || `${key}_safe_task_${index + 1}`,
29828:     title: item.title || `Safe ${runtimeShared.getDepartmentLabel(key)} task ${index + 1}`,
29829:     detail: item.detail || "",
29830:     status: item.status === "blocked_waiting_discovery" ? "blocked_waiting_discovery" : "queued_preview",
29831:     safety: "internal_preview_only",
29832:     approval_required: item.approval_required !== false,
29833:     no_live_side_effects: true,
29834:     created_at: new Date().toISOString(),
29835:   }));
29836: 
29837:   const nextEntry = {
29838:     ...current,
29839:     status: "queue_ready",
29840:     tasks,
29841:     last_updated: new Date().toISOString(),
29842:   };
29843: 
29844:   nextEntry.boardroom_summary = buildAionDepartmentBoardroomSummary(key, nextEntry);
29845: 
29846:   if (typeof updateAionDepartmentIntelligence === "function") {
29847:     updateAionDepartmentIntelligence(key, nextEntry);
29848:   }
29849: 
29850:   if (options.render !== false && typeof requestRender === "function") {
29851:     requestRender();
29852:   }
29853: 
29854:   return nextEntry;
29855: }
29856: 
29857: function renderAionDepartmentPilotDiscoveryPanel(departmentKey = "") {
29858:   const key = String(departmentKey || "").trim().toLowerCase();
29859:   const template = getAionDepartmentPilotDiscoveryTemplate(key);
29860:   const entry = getAionDepartmentLedgerEntry(key);
29861:   const discovery = asRecord(entry.discovery) || {};
29862:   const completion = getAionDepartmentPilotCompletion(key);
29863: 
29864:   return `
29865:     <section
29866:       class="panel large-panel"
29867:       data-aion-phase25c-department-pilot-discovery="${escapeHtml(key)}"
29868:       style="background:#ffffff; margin-top:9px;"
29869:     >
29870:       <div class="panel-title">${escapeHtml(runtimeShared.getDepartmentLabel(key))} Pilot Discovery</div>
29871:       <div class="helper-text">
29872:         Scoped discovery writes directly into <code>aion.departmentIntelligence.${escapeHtml(key)}.discovery</code>
29873:         and feeds the Boardroom automatically.
29874:       </div>
29875: 
29876:       <div class="badge-row" style="margin-top:10px;">
29877:         <span class="badge">Discovery ${escapeHtml(String(completion.answered))}/${escapeHtml(String(completion.total))}</span>
29878:         <span class="badge">Status ${escapeHtml(normaliseAionDepartmentPilotStatus(entry))}</span>

## function buildAionDepartmentPilotSafeTaskQueue

29807: 
29808:   if (options.render !== false && typeof requestRender === "function") {
29809:     requestRender();
29810:   }
29811: 
29812:   return nextEntry;
29813: }
29814: 
29815: function buildAionDepartmentPilotSafeTaskQueue(departmentKey = "", options = {}) {
29816:   const key = String(departmentKey || "").trim().toLowerCase();
29817:   if (!key) return {};
29818: 
29819:   const current = options.buildPlanFirst === false
29820:     ? getAionDepartmentLedgerEntry(key)
29821:     : buildAionDepartmentPilotPlanDraft(key, { render: false });
29822: 
29823:   const plan = asRecord(current.plan) || {};
29824:   const actions = Array.isArray(plan.action_items) ? plan.action_items : [];
29825: 
29826:   const tasks = actions.map((item, index) => ({
29827:     id: item.id || `${key}_safe_task_${index + 1}`,
29828:     title: item.title || `Safe ${runtimeShared.getDepartmentLabel(key)} task ${index + 1}`,
29829:     detail: item.detail || "",
29830:     status: item.status === "blocked_waiting_discovery" ? "blocked_waiting_discovery" : "queued_preview",
29831:     safety: "internal_preview_only",
29832:     approval_required: item.approval_required !== false,
29833:     no_live_side_effects: true,
29834:     created_at: new Date().toISOString(),
29835:   }));
29836: 
29837:   const nextEntry = {
29838:     ...current,
29839:     status: "queue_ready",
29840:     tasks,
29841:     last_updated: new Date().toISOString(),
29842:   };
29843: 
29844:   nextEntry.boardroom_summary = buildAionDepartmentBoardroomSummary(key, nextEntry);
29845: 
29846:   if (typeof updateAionDepartmentIntelligence === "function") {
29847:     updateAionDepartmentIntelligence(key, nextEntry);
29848:   }
29849: 
29850:   if (options.render !== false && typeof requestRender === "function") {
29851:     requestRender();
29852:   }
29853: 
29854:   return nextEntry;
29855: }
29856: 
29857: function renderAionDepartmentPilotDiscoveryPanel(departmentKey = "") {
29858:   const key = String(departmentKey || "").trim().toLowerCase();
29859:   const template = getAionDepartmentPilotDiscoveryTemplate(key);
29860:   const entry = getAionDepartmentLedgerEntry(key);
29861:   const discovery = asRecord(entry.discovery) || {};
29862:   const completion = getAionDepartmentPilotCompletion(key);
29863: 
29864:   return `
29865:     <section
29866:       class="panel large-panel"
29867:       data-aion-phase25c-department-pilot-discovery="${escapeHtml(key)}"
29868:       style="background:#ffffff; margin-top:9px;"
29869:     >
29870:       <div class="panel-title">${escapeHtml(runtimeShared.getDepartmentLabel(key))} Pilot Discovery</div>
29871:       <div class="helper-text">
29872:         Scoped discovery writes directly into <code>aion.departmentIntelligence.${escapeHtml(key)}.discovery</code>
29873:         and feeds the Boardroom automatically.
29874:       </div>
29875: 
29876:       <div class="badge-row" style="margin-top:10px;">
29877:         <span class="badge">Discovery ${escapeHtml(String(completion.answered))}/${escapeHtml(String(completion.total))}</span>
29878:         <span class="badge">Status ${escapeHtml(normaliseAionDepartmentPilotStatus(entry))}</span>
29879:         <span class="badge">Boardroom sync ready</span>
29880:       </div>
29881: 
29882:       <div style="display:grid; gap:10px; margin-top:9px;">
29883:         ${template.map(([fieldKey, label, placeholder]) => `
29884:           <label style="display:grid; gap:7px;">
29885:             <span class="card-label">${escapeHtml(label)}</span>
29886:             <textarea
29887:               class="input input-textarea input-textarea-small"
29888:               data-aion-department-pilot-discovery-field="${escapeHtml(fieldKey)}"
29889:               data-department-key="${escapeHtml(key)}"
29890:               placeholder="${escapeHtml(placeholder || "")}"
29891:               rows="2"
29892:               style="background:#ffffff;"
29893:             >${escapeHtml(discovery[fieldKey] || "")}</textarea>
29894:           </label>
29895:         `).join("")}
29896:       </div>
29897: 
29898:       <div class="marketing-form-actions" style="margin-top:9px;">
29899:         <button
29900:           type="button"
29901:           class="secondary-btn"
29902:           data-aion-phase25c-save-discovery="${escapeHtml(key)}"
29903:         >
29904:           Save discovery to ledger
29905:         </button>
29906:         <button
29907:           type="button"
29908:           class="secondary-btn"
29909:           data-aion-phase25c-build-plan="${escapeHtml(key)}"
29910:         >
29911:           Build department plan draft
29912:         </button>
29913:         <button
29914:           type="button"
29915:           class="primary-btn"
29916:           data-aion-phase25c-build-queue="${escapeHtml(key)}"
29917:         >
29918:           Build safe task queue
29919:         </button>
29920:       </div>
29921: 
29922:       <div class="notice warning" style="margin-top:12px;">
29923:         Discovery and queue creation are local preview actions only. Pilot has not posted, sent messages, spent money,
29924:         booked work, deployed changes or mutated live external systems.
29925:       </div>
29926:     </section>
29927:   `;
29928: }
29929: 
29930: function renderAionDepartmentPilotPlanPanel(departmentKey = "") {
29931:   const key = String(departmentKey || "").trim().toLowerCase();
29932:   const entry = getAionDepartmentLedgerEntry(key);
29933:   const plan = asRecord(entry.plan) || {};
29934:   const actions = Array.isArray(plan.action_items) ? plan.action_items : [];
29935: 
29936:   return `
29937:     <section
29938:       class="panel large-panel"
29939:       data-aion-phase25c-department-pilot-plan="${escapeHtml(key)}"
29940:       style="background:#ffffff; margin-top:9px;"
29941:     >
29942:       <div class="panel-title">Department Plan Draft</div>
29943:       ${
29944:         Object.keys(plan).length
29945:           ? `
29946:             <div class="helper-text">${escapeHtml(plan.objective || "Plan draft ready.")}</div>
29947:             <div class="list-wrap" style="margin-top:12px;">
29948:               ${actions.map((item) => `
29949:                 <div class="list-item">
29950:                   <div class="list-item-title">${escapeHtml(item.title || "Action")}</div>
29951:                   <div class="list-item-sub">${escapeHtml(item.detail || "")}</div>
29952:                   <div class="badge-row">
29953:                     <span class="badge">${escapeHtml(item.status || "draft_preview")}</span>
29954:                     <span class="badge">${item.approval_required === false ? "No approval needed" : "Approval gated"}</span>
29955:                   </div>

## function runAionDepartmentPilotNextSafeTask

30310:   const key = normaliseAionDepartmentPilotKey(departmentKey);
30311:   const queue = getAionDepartmentPilotApprovedTaskQueue(key);
30312:   return queue.find((item) => {
30313:     const status = String(item?.status || "").toLowerCase();
30314:     return status === "approved" || status === "queued" || status === "ready";
30315:   }) || null;
30316: }
30317: 
30318: function runAionDepartmentPilotNextSafeTask(departmentKey = "") {
30319:   const key = normaliseAionDepartmentPilotKey(departmentKey);
30320:   if (!key) return null;
30321: 
30322:   const ledger = getAionDepartmentIntelligence();
30323:   const entry = ledger[key] || normaliseAionDepartmentIntelligenceEntry(key, {});
30324:   const queue = Array.isArray(entry.tasks) ? entry.tasks : [];
30325:   const now = new Date().toISOString();
30326: 
30327:   const nextIndex = queue.findIndex((item) => {
30328:     const status = String(item?.status || "").toLowerCase();
30329:     return status === "approved" || status === "queued" || status === "ready";
30330:   });
30331: 
30332:   if (nextIndex < 0) {
30333:     const patch = {
30334:       status: "safe_queue_complete",
30335:       boardroom_summary: `${runtimeShared.getDepartmentLabel(key)} has no remaining approved safe internal preview tasks.`,
30336:       last_updated: now,
30337:     };
30338:     updateAionDepartmentIntelligence(key, patch);
30339:     if (typeof requestRender === "function") requestRender();
30340:     return patch;
30341:   }
30342: 
30343:   const task = queue[nextIndex] || {};
30344:   const completedTask = {
30345:     ...task,
30346:     status: "completed_preview",
30347:     completed_at: now,
30348:     updated_at: now,
30349:     result_summary: `${task.title || "Safe task"} completed as an internal preview. No live external action was taken.`,
30350:   };
30351: 
30352:   const nextTasks = queue.map((item, index) => (index === nextIndex ? completedTask : item));
30353: 
30354:   const runRecord = {
30355:     id: `${key}_safe_preview_run_${Date.now()}`,
30356:     department_key: key,
30357:     title: completedTask.title,
30358:     status: "completed_preview",
30359:     source: "department_pilot_safe_queue",
30360:     created_at: now,
30361:     updated_at: now,
30362:     safety_boundary: "no_live_external_side_effects",
30363:   };
30364: 
30365:   const receipt = {
30366:     id: `${key}_safe_preview_receipt_${Date.now()}`,
30367:     department_key: key,
30368:     task_id: completedTask.id,
30369:     receipt_type: "safe_internal_preview",
30370:     status: "draft_receipt",
30371:     created_at: now,
30372:     no_live_external_action: true,
30373:   };
30374: 
30375:   const resultRecord = {
30376:     id: `${key}_safe_preview_result_${Date.now()}`,
30377:     department_key: key,
30378:     task_id: completedTask.id,
30379:     title: completedTask.title,
30380:     status: "results_available",
30381:     result_type: "safe_internal_preview",
30382:     summary: completedTask.result_summary,
30383:     created_at: now,
30384:     no_live_external_action: true,
30385:   };
30386: 
30387:   const evidenceRecord = {
30388:     id: `${key}_safe_preview_evidence_${Date.now()}`,
30389:     department_key: key,
30390:     task_id: completedTask.id,
30391:     evidence_type: "safe_task_result",
30392:     title: completedTask.title,
30393:     summary: completedTask.result_summary,
30394:     receipt_id: receipt.id,
30395:     created_at: now,
30396:     provenance: "department_pilot_safe_queue",
30397:   };
30398: 
30399:   const existingResults =
30400:     entry.results && typeof entry.results === "object" && !Array.isArray(entry.results)
30401:       ? entry.results
30402:       : {};
30403: 
30404:   const patch = {
30405:     status: nextTasks.some((item) => ["approved", "queued", "ready"].includes(String(item?.status || "").toLowerCase()))
30406:       ? "executing_safe_queue"
30407:       : "safe_queue_complete",
30408:     tasks: nextTasks,
30409:     runs: [...(Array.isArray(entry.runs) ? entry.runs : []), runRecord],
30410:     results: {
30411:       ...existingResults,
30412:       latest_safe_preview: resultRecord,
30413:       safe_preview_history: [
30414:         ...(Array.isArray(existingResults.safe_preview_history) ? existingResults.safe_preview_history : []),
30415:         resultRecord,
30416:       ],
30417:     },
30418:     evidence: [...(Array.isArray(entry.evidence) ? entry.evidence : []), evidenceRecord],
30419:     receipts: [...(Array.isArray(entry.receipts) ? entry.receipts : []), receipt],
30420:     boardroom_summary: `${runtimeShared.getDepartmentLabel(key)} safe task completed: ${completedTask.title}. Results, evidence and receipt were written to the Boardroom feed. No live external action was taken.`,
30421:     active_task_index: nextIndex + 1,
30422:     confidence: "useful",
30423:     alerts: Array.isArray(entry.alerts) ? entry.alerts : [],
30424:     last_updated: now,
30425:   };
30426: 
30427:   updateAionDepartmentIntelligence(key, patch);
30428: 
30429:   if (typeof requestRender === "function") {
30430:     requestRender();
30431:   }
30432: 
30433:   return patch;
30434: }
30435: 
30436: function renderAionDepartmentPilotPhase25DPanel(departmentKey = "") {
30437:   const key = normaliseAionDepartmentPilotKey(departmentKey);
30438:   const label = runtimeShared.getDepartmentLabel(key);
30439:   const approval = getAionDepartmentPilotApprovalState(key);
30440:   const queue = getAionDepartmentPilotApprovedTaskQueue(key);
30441:   const nextTask = getAionDepartmentPilotNextSafeTask(key);
30442:   const completed = queue.filter((item) => String(item?.status || "").toLowerCase() === "completed_preview").length;
30443:   const pending = queue.length - completed;
30444: 
30445:   return `
30446:     <section
30447:       class="panel large-panel"
30448:       data-aion-phase25d-department-pilot-safe-queue="true"
30449:       data-aion-phase25d-department="${escapeHtml(key)}"
30450:       style="margin-top:9px; background:#ffffff;"
30451:     >
30452:       <div class="panel-title">${escapeHtml(label)} Plan Approval + Safe Queue</div>
30453:       <div class="helper-text">
30454:         Approve the department plan, then run safe internal preview tasks. This does not send, publish, spend, book, deploy or mutate external systems.
30455:       </div>
30456: 
30457:       <div class="card-grid" style="margin-top:12px;">
30458:         ${renderDashboardMetricCard("Plan approval", approval.status, "Human-gated")}

## function updateAionDepartmentIntelligence

30142: function getAionDepartmentLedgerEntry(departmentKey) {
30143:   const key = String(departmentKey || "finance").trim().toLowerCase() || "finance";
30144:   const ledger = getAionDepartmentIntelligence();
30145:   return ledger[key] && typeof ledger[key] === "object" && !Array.isArray(ledger[key])
30146:     ? ledger[key]
30147:     : {};
30148: }
30149: 
30150: function updateAionDepartmentIntelligence(departmentKey, patch) {
30151:   const key = String(departmentKey || "finance").trim().toLowerCase() || "finance";
30152:   const ledger = getAionDepartmentIntelligence();
30153:   const current = ledger[key] && typeof ledger[key] === "object" && !Array.isArray(ledger[key])
30154:     ? ledger[key]
30155:     : {};
30156:   ledger[key] = {
30157:     ...current,
30158:     ...(patch && typeof patch === "object" && !Array.isArray(patch) ? patch : {}),
30159:     department: key,
30160:     updated_at: new Date().toISOString(),
30161:   };
30162:   setAionDepartmentIntelligence(ledger);
30163:   return ledger[key];
30164: }
30165: 
30166: if (typeof window !== "undefined") {
30167:   window.getAionDepartmentIntelligence = getAionDepartmentIntelligence;
30168:   window.setAionDepartmentIntelligence = setAionDepartmentIntelligence;
30169:   window.getAionDepartmentLedgerEntry = getAionDepartmentLedgerEntry;
30170:   window.updateAionDepartmentIntelligence = updateAionDepartmentIntelligence;
30171: }
30172: 
30173: /* AION PATCH: Department Intelligence early compatibility v1
30174:  * ----------------------------------------------------------
30175:  * Live Agents can render before later Phase 25 ledger helpers are defined.
30176:  * These early helpers keep the route alive and use localStorage as the
30177:  * temporary source of truth until the full Department Intelligence block loads.
30178:  */
30179: if (typeof window !== "undefined" && typeof window.getAionDepartmentIntelligence !== "function") {
30180:   window.AION_DEPARTMENT_INTELLIGENCE_STORAGE_KEY =
30181:     window.AION_DEPARTMENT_INTELLIGENCE_STORAGE_KEY || "aion.departmentIntelligence.v1";
30182: 
30183:   window.getAionDepartmentIntelligence = function getAionDepartmentIntelligenceEarlyCompatV1() {
30184:     try {
30185:       const raw = localStorage.getItem(window.AION_DEPARTMENT_INTELLIGENCE_STORAGE_KEY);
30186:       const parsed = raw ? JSON.parse(raw) : {};
30187:       return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : {};
30188:     } catch {
30189:       return {};
30190:     }
30191:   };
30192: 
30193:   window.setAionDepartmentIntelligence = function setAionDepartmentIntelligenceEarlyCompatV1(next) {
30194:     const value = next && typeof next === "object" && !Array.isArray(next) ? next : {};
30195:     try {
30196:       localStorage.setItem(window.AION_DEPARTMENT_INTELLIGENCE_STORAGE_KEY, JSON.stringify(value));
30197:     } catch {}
30198:     return value;
30199:   };
30200: 
30201:   window.updateAionDepartmentIntelligence = function updateAionDepartmentIntelligenceEarlyCompatV1(departmentKey, patch = {}) {
30202:     const key = String(departmentKey || "").trim().toLowerCase() || "finance";
30203:     const ledger = window.getAionDepartmentIntelligence();
30204:     const current = ledger[key] && typeof ledger[key] === "object" ? ledger[key] : {};
30205:     const next = {
30206:       ...current,
30207:       ...(patch && typeof patch === "object" ? patch : {}),
30208:       department_key: key,
30209:       updated_at: new Date().toISOString(),
30210:       last_updated: new Date().toISOString(),
30211:     };
30212:     ledger[key] = next;
30213:     window.setAionDepartmentIntelligence(ledger);
30214:     return next;
30215:   };
30216: 
30217:   window.getAionDepartmentLedgerEntry = function getAionDepartmentLedgerEntryEarlyCompatV1(departmentKey) {
30218:     const key = String(departmentKey || "").trim().toLowerCase() || "finance";
30219:     const ledger = window.getAionDepartmentIntelligence();
30220:     return ledger[key] && typeof ledger[key] === "object"
30221:       ? ledger[key]
30222:       : {
30223:           department_key: key,
30224:           status: "needs_discovery",
30225:           discovery: {},
30226:           plan: {},
30227:           tasks: [],
30228:           runs: [],
30229:           evidence: [],
30230:           receipts: [],
30231:           confidence: "empty",
30232:           boardroom_summary: "",
30233:         };
30234:   };
30235: }
30236: 
30237: 
30238: 
30239: function getAionDepartmentPilotApprovalState(departmentKey = "") {
30240:   const key = normaliseAionDepartmentPilotKey(departmentKey);
30241:   const ledger = getAionDepartmentIntelligence();
30242:   const entry = ledger[key] || normaliseAionDepartmentIntelligenceEntry(key, {});
30243:   return {
30244:     status: entry.plan_approval_status || "not_requested",
30245:     approved_at: entry.plan_approved_at || "",
30246:     approved_by: entry.plan_approved_by || "",
30247:     active_task_index: Number.isFinite(Number(entry.active_task_index))
30248:       ? Number(entry.active_task_index)
30249:       : 0,
30250:   };
30251: }
30252: 
30253: function approveAionDepartmentPilotPlan(departmentKey = "") {
30254:   const key = normaliseAionDepartmentPilotKey(departmentKey);
30255:   if (!key) return null;
30256: 
30257:   const plan =
30258:     typeof buildAionDepartmentPilotPlanDraft === "function"
30259:       ? buildAionDepartmentPilotPlanDraft(key)
30260:       : {};
30261: 
30262:   const queue =
30263:     typeof buildAionDepartmentPilotSafeTaskQueue === "function"
30264:       ? buildAionDepartmentPilotSafeTaskQueue(key)
30265:       : [];
30266: 
30267:   const now = new Date().toISOString();
30268: 
30269:   const taskQueue = queue.map((item, index) => ({
30270:     id: item.id || `${key}_safe_task_${index + 1}`,
30271:     title: item.title || item.label || `Safe task ${index + 1}`,
30272:     status: item.status || "approved",
30273:     type: item.type || "safe_internal_preview",
30274:     approval_boundary: item.approval_boundary || "no_live_external_side_effects",
30275:     created_at: item.created_at || now,
30276:     updated_at: now,
30277:   }));
30278: 
30279:   const patch = {
30280:     status: "plan_approved",
30281:     plan,
30282:     tasks: taskQueue,
30283:     plan_approval_status: "approved",
30284:     plan_approved_at: now,
30285:     plan_approved_by: "human_operator",
30286:     active_task_index: 0,
30287:     boardroom_summary: `${runtimeShared.getDepartmentLabel(key)} plan approved. ${taskQueue.length} safe internal task(s) ready for preview execution.`,
30288:     confidence: taskQueue.length ? "useful" : "partial",
30289:     alerts: [],
30290:     last_updated: now,

## Global workflow graph writes

18933:       store[activeGlyphCode.toLowerCase()] ||
18934:       window.__aionOpenedGlyphWorkflowGraph;
18935: 
18936:     if (glyphGraph && typeof glyphGraph === "object") {
18937:       glyphGraph.glyph_code = glyphGraph.glyph_code || activeGlyphCode;
18938:       window.__aionOpenedGlyphWorkflowGraph = glyphGraph;
18939:       window.__aionWorkflowGraph = glyphGraph;
18940:       return stripAionWorkflowSyntheticChooseNode(glyphGraph);
18941:     }
18942:   }
18943: 
18944:   if (
18945:     window.__aionWorkflowMainGraph &&
18946:     typeof window.__aionWorkflowMainGraph === "object"
18947:   ) {
18948:     window.__aionWorkflowGraph = window.__aionWorkflowMainGraph;
18949:     return stripAionWorkflowSyntheticChooseNode(window.__aionWorkflowMainGraph);
18950:   }
18951: 
18952:   if (window.__aionWorkflowGraph && typeof window.__aionWorkflowGraph === "object") {
18953:     window.__aionWorkflowMainGraph = window.__aionWorkflowGraph;
18954:     return stripAionWorkflowSyntheticChooseNode(window.__aionWorkflowGraph);
18955:   }
18956: 
18957:   try {
18958:     const raw = localStorage.getItem(AION_WORKFLOW_DRAFT_STORAGE_KEY);
18959:     if (raw) {

18942:   }
18943: 
18944:   if (
18945:     window.__aionWorkflowMainGraph &&
18946:     typeof window.__aionWorkflowMainGraph === "object"
18947:   ) {
18948:     window.__aionWorkflowGraph = window.__aionWorkflowMainGraph;
18949:     return stripAionWorkflowSyntheticChooseNode(window.__aionWorkflowMainGraph);
18950:   }
18951: 
18952:   if (window.__aionWorkflowGraph && typeof window.__aionWorkflowGraph === "object") {
18953:     window.__aionWorkflowMainGraph = window.__aionWorkflowGraph;
18954:     return stripAionWorkflowSyntheticChooseNode(window.__aionWorkflowGraph);
18955:   }
18956: 
18957:   try {
18958:     const raw = localStorage.getItem(AION_WORKFLOW_DRAFT_STORAGE_KEY);
18959:     if (raw) {
18960:       const parsed = JSON.parse(raw);
18961:       window.__aionWorkflowMainGraph = stripAionWorkflowSyntheticChooseNode({
18962:         ...getDefaultAionWorkflowDraftState(),
18963:         ...parsed,
18964:         nodes: Array.isArray(parsed.nodes) ? parsed.nodes : [],
18965:         edges: Array.isArray(parsed.edges) ? parsed.edges : [],
18966:       });
18967:       window.__aionWorkflowGraph = window.__aionWorkflowMainGraph;
18968:       return window.__aionWorkflowMainGraph;

18946:     typeof window.__aionWorkflowMainGraph === "object"
18947:   ) {
18948:     window.__aionWorkflowGraph = window.__aionWorkflowMainGraph;
18949:     return stripAionWorkflowSyntheticChooseNode(window.__aionWorkflowMainGraph);
18950:   }
18951: 
18952:   if (window.__aionWorkflowGraph && typeof window.__aionWorkflowGraph === "object") {
18953:     window.__aionWorkflowMainGraph = window.__aionWorkflowGraph;
18954:     return stripAionWorkflowSyntheticChooseNode(window.__aionWorkflowGraph);
18955:   }
18956: 
18957:   try {
18958:     const raw = localStorage.getItem(AION_WORKFLOW_DRAFT_STORAGE_KEY);
18959:     if (raw) {
18960:       const parsed = JSON.parse(raw);
18961:       window.__aionWorkflowMainGraph = stripAionWorkflowSyntheticChooseNode({
18962:         ...getDefaultAionWorkflowDraftState(),
18963:         ...parsed,
18964:         nodes: Array.isArray(parsed.nodes) ? parsed.nodes : [],
18965:         edges: Array.isArray(parsed.edges) ? parsed.edges : [],
18966:       });
18967:       window.__aionWorkflowGraph = window.__aionWorkflowMainGraph;
18968:       return window.__aionWorkflowMainGraph;
18969:     }
18970:   } catch (error) {
18971:     console.warn("[workflow] failed to load draft", error);
18972:   }

18961:       window.__aionWorkflowMainGraph = stripAionWorkflowSyntheticChooseNode({
18962:         ...getDefaultAionWorkflowDraftState(),
18963:         ...parsed,
18964:         nodes: Array.isArray(parsed.nodes) ? parsed.nodes : [],
18965:         edges: Array.isArray(parsed.edges) ? parsed.edges : [],
18966:       });
18967:       window.__aionWorkflowGraph = window.__aionWorkflowMainGraph;
18968:       return window.__aionWorkflowMainGraph;
18969:     }
18970:   } catch (error) {
18971:     console.warn("[workflow] failed to load draft", error);
18972:   }
18973: 
18974:   window.__aionWorkflowMainGraph = getDefaultAionWorkflowDraftState();
18975:   window.__aionWorkflowGraph = window.__aionWorkflowMainGraph;
18976:   return window.__aionWorkflowMainGraph;
18977: }
18978: 
18979: 
18980: function buildAionWorkflowSavePayload(graph) {
18981:   const safeGraph = graph || getAionWorkflowDraftState();
18982:   const compiledGlyph =
18983:     safeGraph.compiled_glyph || compileAionWorkflowGraphToGlyph(safeGraph);
18984: 
18985:   const nodes = Array.isArray(safeGraph.nodes) ? safeGraph.nodes : [];
18986:   const edges = Array.isArray(safeGraph.edges) ? safeGraph.edges : [];
18987: 

18969:     }
18970:   } catch (error) {
18971:     console.warn("[workflow] failed to load draft", error);
18972:   }
18973: 
18974:   window.__aionWorkflowMainGraph = getDefaultAionWorkflowDraftState();
18975:   window.__aionWorkflowGraph = window.__aionWorkflowMainGraph;
18976:   return window.__aionWorkflowMainGraph;
18977: }
18978: 
18979: 
18980: function buildAionWorkflowSavePayload(graph) {
18981:   const safeGraph = graph || getAionWorkflowDraftState();
18982:   const compiledGlyph =
18983:     safeGraph.compiled_glyph || compileAionWorkflowGraphToGlyph(safeGraph);
18984: 
18985:   const nodes = Array.isArray(safeGraph.nodes) ? safeGraph.nodes : [];
18986:   const edges = Array.isArray(safeGraph.edges) ? safeGraph.edges : [];
18987: 
18988:   return {
18989:     schema_version: "aion.workflow_save.v1",
18990:     storage_scope: "business_container",
18991:     business_container:
18992:       compiledGlyph?.workflow?.business_container ||
18993:       safeGraph.business_container ||
18994:       "costa-conexion",
18995:     workflow_id: safeGraph.workflow_id || window.__aionCreateUniqueWorkflowId?.() || "workflow_draft",

19045: 
19046:   const config = {
19047:     ...(node.config || {}),
19048:     ...pending,
19049:   };
19050: 
19051:   window.__aionWorkflowGraph = {
19052:     ...graph,
19053:     nodes: nodes.map((item) =>
19054:       item.id === nodeId
19055:         ? {
19056:             ...item,
19057:             config,
19058:           }
19059:         : item,
19060:     ),
19061:   };
19062: 
19063:   compileAndAttachAionWorkflowGlyph(window.__aionWorkflowGraph);
19064:   persistAionWorkflowDraftState();
19065: 
19066:   return config;
19067: }
19068: 
19069: 
19070: function syncAionWorkflowInspectorInputsToGraph() {
19071:   const graph = getAionWorkflowDraftState();

19123:       typeof window.__aionOpenedGlyphWorkflowGraphsByCode === "object"
19124:         ? window.__aionOpenedGlyphWorkflowGraphsByCode
19125:         : {};
19126: 
19127:     window.__aionOpenedGlyphWorkflowGraphsByCode[activeGlyphCode] = compactGraph;
19128:     window.__aionOpenedGlyphWorkflowGraph = compactGraph;
19129:     window.__aionWorkflowGraph = compactGraph;
19130:     return compactGraph;
19131:   }
19132: 
19133:   window.__aionWorkflowMainGraph = compactGraph;
19134:   window.__aionWorkflowGraph = compactGraph;
19135: 
19136:   try {
19137:     localStorage.setItem(AION_WORKFLOW_DRAFT_STORAGE_KEY, JSON.stringify(compactGraph));
19138:   } catch (error) {
19139:     console.warn("[workflow] failed to save draft", error);
19140:   }
19141: 
19142:   return compactGraph;
19143: }
19144: 
19145: 
19146: 
19147: 
19148: function markAionWorkflowDraftDirty(reason = "updated") {
19149:   const graph = getAionWorkflowDraftState();

19128:     window.__aionOpenedGlyphWorkflowGraph = compactGraph;
19129:     window.__aionWorkflowGraph = compactGraph;
19130:     return compactGraph;
19131:   }
19132: 
19133:   window.__aionWorkflowMainGraph = compactGraph;
19134:   window.__aionWorkflowGraph = compactGraph;
19135: 
19136:   try {
19137:     localStorage.setItem(AION_WORKFLOW_DRAFT_STORAGE_KEY, JSON.stringify(compactGraph));
19138:   } catch (error) {
19139:     console.warn("[workflow] failed to save draft", error);
19140:   }
19141: 
19142:   return compactGraph;
19143: }
19144: 
19145: 
19146: 
19147: 
19148: function markAionWorkflowDraftDirty(reason = "updated") {
19149:   const graph = getAionWorkflowDraftState();
19150:   graph.dirty = true;
19151:   graph.dirty_reason = reason;
19152:   graph.saved_at = graph.saved_at || null;
19153:   compileAndAttachAionWorkflowGlyph(graph);
19154:   window["__aionWorkflowGraph"] = graph;

19225:     backend_saved_at: record.updated_at || "",
19226:     backend_storage_path: record.path || "",
19227:     dirty: false,
19228:   };
19229: 
19230:   compileAndAttachAionWorkflowGlyph(loadedGraph);
19231:   window.__aionWorkflowGraph = loadedGraph;
19232:   persistAionWorkflowDraftState();
19233: 
19234:   return loadedGraph;
19235: }
19236: 
19237: async function maybeLoadAionWorkflowFromBusinessContainerOnce() {
19238:   if (window.__aionWorkflowBusinessLoadAttempted === true) return;
19239:   window.__aionWorkflowBusinessLoadAttempted = true;
19240: 
19241:   try {
19242:     const businessContainer =
19243:       state.workspaceId ||
19244:       window.__aionWorkflowGraph?.business_container ||
19245:       "costa-conexion";
19246: 
19247:     const workflowId =
19248:       window.__aionWorkflowGraph?.workflow_id ||
19249:       "workflow_draft";
19250: 
19251:     const loadedGraph = await loadAionWorkflowFromBusinessContainer({

20058:   safeGraph.display_glyph = result.display_glyph || canvas.display_glyph;
20059:   safeGraph.capsule_saved_at = new Date().toISOString();
20060:   safeGraph.capsule_path = result.path || "";
20061:   safeGraph.capsule_checksum = result.checksum || "";
20062:   safeGraph.dirty = false;
20063: 
20064:   window.__aionWorkflowGraph = safeGraph;
20065:   persistAionWorkflowDraftState();
20066: 
20067:   return result;
20068: }
20069: 
20070: function renderAionWorkflowGlyphDebugExecutionPanel() {
20071:   if (window.__aionWorkflowGlyphDebugOpen !== true) return "";
20072: 
20073:   const graph = getAionWorkflowDraftState();
20074:   const compiled = graph?.compiled_glyph || compileAionWorkflowGraphToGlyph(graph);
20075:   const stepCount = Array.isArray(compiled?.steps) ? compiled.steps.length : 0;
20076:   const linkCount = Array.isArray(compiled?.flow_links) ? compiled.flow_links.length : 0;
20077: 
20078:   return `
20079:     <div class="aion-workflow-glyph-debug-panel" data-aion-glyph-debug-panel="true">
20080:       <button
20081:         class="aion-dry-run-floating-close"
20082:         type="button"
20083:         data-aion-glyph-debug-close="true"
20084:         title="Close compiled glyph"

21299:       messageTone: "info",
21300:     });
21301:     return false;
21302:   }
21303: 
21304:   if (!window.__aionWorkflowGraph) {
21305:     window.__aionWorkflowGraph = {
21306:       workflow_id: createAionWorkflowId(),
21307:       name: "Untitled workflow",
21308:       status: "draft",
21309:       nodes: [],
21310:       edges: [],
21311:     };
21312:   }
21313: 
21314:   const graph = window.__aionWorkflowGraph;
21315:   const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
21316:   const edges = Array.isArray(graph.edges) ? graph.edges : [];
21317: 
21318:   const selectedNodeId = window.__aionWorkflowSelectedNodeId || null;
21319:   const selectedNode = selectedNodeId
21320:     ? nodes.find((node) => node.id === selectedNodeId)
21321:     : null;
21322: 
21323:   const anchorNode =
21324:     selectedNode ||
21325:     nodes[nodes.length - 1] ||

22795: 
22796:   return steps;
22797: }
22798: 
22799: function appendAionUnifiedSuggestedStepsToMainWorkflow(steps) {
22800:   if (!window.__aionWorkflowGraph) {
22801:     window.__aionWorkflowGraph = getAionWorkflowDraftState();
22802:   }
22803: 
22804:   const graph = window.__aionWorkflowGraph || {};
22805:   const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
22806:   const edges = Array.isArray(graph.edges) ? graph.edges : [];
22807: 
22808:   let previousNode = nodes[nodes.length - 1] || null;
22809: 
22810:   steps.forEach((step, index) => {
22811:     const nodeId = step.id || `ai_step_${Date.now()}_${index}`;
22812:     const x = previousNode?.x != null ? Number(previousNode.x) + 320 : 360 + index * 320;
22813:     const y = previousNode?.y != null ? Number(previousNode.y) : 260;
22814: 
22815:     const node = {
22816:       id: nodeId,
22817:       title: step.title || "Aion step",
22818:       type: step.type || "AI / Aion",
22819:       icon: step.icon || "AI",
22820:       status: step.status || "Draft",
22821:       meta: step.meta || "Generated by Aion",

23144:     type: "workflow",
23145:     workflow_id: workflowId,
23146:   });
23147: 
23148:   saveAionFileCabinetTree(tree);
23149: 
23150:   window.__aionWorkflowGraph = {
23151:     workflow_id: workflowId,
23152:     name: name.trim(),
23153:     status: "draft",
23154:     saved_at: null,
23155:     dirty: true,
23156:     nodes: [
23157:       {
23158:         id: "node_choose_start",
23159:         title: "Choose",
23160:         type: "Step",
23161:         icon: "C",
23162:         status: "Dry-run",
23163:         meta: "Choose a trigger, app action, AI action, flow control, tool, parser, or approval step.",
23164:         tone: "teal",
23165:         x: 160,
23166:         y: 260,
23167:         config: {},
23168:       },
23169:     ],
23170:     edges: [],

43617:         });
43618:         requestRender();
43619:         return;
43620:       }
43621: 
43622:       if (!window.__aionWorkflowGraph) {
43623:         window.__aionWorkflowGraph = {
43624:           workflow_id: createAionWorkflowId(),
43625:           name: "Untitled workflow",
43626:           status: "draft",
43627:           nodes: [],
43628:           edges: [],
43629:         };
43630:       }
43631: 
43632:       const nodes = Array.isArray(window.__aionWorkflowGraph.nodes)
43633:         ? window.__aionWorkflowGraph.nodes
43634:         : [];
43635: 
43636:       const edges = Array.isArray(window.__aionWorkflowGraph.edges)
43637:         ? window.__aionWorkflowGraph.edges
43638:         : [];
43639: 
43640:       const selectedNodeId = window.__aionWorkflowSelectedNodeId || null;
43641:       const selectedNode = selectedNodeId
43642:         ? nodes.find((node) => node.id === selectedNodeId)
43643:         : null;

46164:         live_send_enabled: false,
46165:         connectors_required: Array.isArray(review.connectors_required) ? review.connectors_required : [],
46166:         missing_connectors: Array.isArray(review.missing_connectors) ? review.missing_connectors : [],
46167:       },
46168:     };
46169: 
46170:     window.__aionWorkflowGraph = nextGraph;
46171:     fitAionWorkflowCanvasToGeneratedNodes(nodes);
46172:     window.__aionWorkflowSelectedNodeId = nodes[0]?.id || null;
46173:     window.__aionWorkflowArchitectModalOpen = false;
46174:     window.__aionWorkflowPickerMode = "";
46175:     window.__aionWorkflowInspectorOpen = false;
46176: 
46177:     if (typeof compileAndAttachAionWorkflowGlyph === "function") {
46178:       compileAndAttachAionWorkflowGlyph(nextGraph);
46179:     }
46180: 
46181:     if (typeof persistAionWorkflowDraftState === "function") {
46182:       persistAionWorkflowDraftState();
46183:     }
46184: 
46185:     setWorkflowArchitectReviewState({
46186:       workflowGoal: (window.__syncedArchitectInput || {}).workflowGoal,
46187:       provider: (window.__syncedArchitectInput || {}).provider,
46188:       result,
46189:       ok: true,
46190:       loading: false,

47295:     });
47296:     requestRender();
47297:     return false;
47298:   }
47299: 
47300:   if (!window.__aionWorkflowGraph) {
47301:     window.__aionWorkflowGraph = {
47302:       workflow_id: createAionWorkflowId(),
47303:       name: "Untitled workflow",
47304:       status: "draft",
47305:       nodes: [],
47306:       edges: [],
47307:     };
47308:   }
47309: 
47310:   const nodes = Array.isArray(window.__aionWorkflowGraph.nodes)
47311:     ? window.__aionWorkflowGraph.nodes
47312:     : [];
47313: 
47314:   const edges = Array.isArray(window.__aionWorkflowGraph.edges)
47315:     ? window.__aionWorkflowGraph.edges
47316:     : [];
47317: 
47318:   const selectedNodeId = window.__aionWorkflowSelectedNodeId || null;
47319:   const selectedNode = selectedNodeId
47320:     ? nodes.find((node) => node.id === selectedNodeId)
47321:     : null;

47799:         });
47800:         requestRender();
47801:         return;
47802:       }
47803: 
47804:       if (!window.__aionWorkflowGraph) {
47805:         window.__aionWorkflowGraph = {
47806:           workflow_id: createAionWorkflowId(),
47807:           name: "Untitled workflow",
47808:           status: "draft",
47809:           nodes: [],
47810:           edges: [],
47811:         };
47812:       }
47813: 
47814:       const nodes = Array.isArray(window.__aionWorkflowGraph.nodes)
47815:         ? window.__aionWorkflowGraph.nodes
47816:         : [];
47817: 
47818:       const edges = Array.isArray(window.__aionWorkflowGraph.edges)
47819:         ? window.__aionWorkflowGraph.edges
47820:         : [];
47821: 
47822:       const selectedNodeId = window.__aionWorkflowSelectedNodeId || null;
47823:       const selectedNode = selectedNodeId
47824:         ? nodes.find((node) => node.id === selectedNodeId)
47825:         : null;

48236: 
48237:     const config = {
48238:       ...(node.config || {}),
48239:       [key]: input.value,
48240:     };
48241: 
48242:     window.__aionWorkflowGraph = {
48243:       ...graph,
48244:       nodes: nodes.map((item) =>
48245:         item.id === nodeId
48246:           ? {
48247:               ...item,
48248:               config,
48249:             }
48250:           : item,
48251:       ),
48252:     };
48253: 
48254:     compileAndAttachAionWorkflowGlyph(window.__aionWorkflowGraph);
48255:     persistAionWorkflowDraftState();
48256:   };
48257: 
48258:   document.addEventListener("input", updateConfig, true);
48259:   document.addEventListener("change", updateConfig, true);
48260:   document.addEventListener("blur", updateConfig, true);
48261: }
48262: 

55544:       (typeof getAionWorkflowDraftState === "function"
55545:         ? getAionWorkflowDraftState()
55546:         : window.__aionWorkflowGraph) || null;
55547: 
55548:     if (!isEmptyGraph(graph) && !isOldStarterGraph(graph)) return false;
55549: 
55550:     window.__aionWorkflowGraph = makeBlankWorkflowGraph();
55551:     window.__aionWorkflowSelectedNodeId = null;
55552:     window.__aionWorkflowPickerMode = "";
55553:     window.__aionWorkflowInspectorOpen = false;
55554: 
55555:     if (typeof compileAndAttachAionWorkflowGlyph === "function") {
55556:       try {
55557:         compileAndAttachAionWorkflowGlyph(window.__aionWorkflowGraph);
55558:       } catch (error) {
55559:         console.warn(`[${PATCH_ID}] compile skipped`, error);
55560:       }
55561:     }
55562: 
55563:     if (typeof persistAionWorkflowDraftState === "function") {
55564:       try {
55565:         persistAionWorkflowDraftState();
55566:       } catch (error) {
55567:         console.warn(`[${PATCH_ID}] persist skipped`, error);
55568:       }
55569:     }
55570: 

55606:     const nextNodes = nodes.filter((node) => String(node.id) !== String(nodeId));
55607:     const nextEdges = edges.filter(
55608:       (edge) => String(edge.from) !== String(nodeId) && String(edge.to) !== String(nodeId),
55609:     );
55610: 
55611:     if (!nextNodes.length) {
55612:       window.__aionWorkflowGraph = makeBlankWorkflowGraph();
55613:       window.__aionWorkflowSelectedNodeId = null;
55614:     } else {
55615:       graph.nodes = nextNodes;
55616:       graph.edges = nextEdges;
55617:       graph.dirty = true;
55618:       window["__aionWorkflowGraph"] = graph;
55619:       window.__aionWorkflowSelectedNodeId = nextNodes[nextNodes.length - 1]?.id || null;
55620:     }
55621: 
55622:     if (typeof compileAndAttachAionWorkflowGlyph === "function") {
55623:       try {
55624:         compileAndAttachAionWorkflowGlyph(window.__aionWorkflowGraph);
55625:       } catch (error) {
55626:         console.warn(`[${PATCH_ID}] compile after delete skipped`, error);
55627:       }
55628:     }
55629: 
55630:     if (typeof persistAionWorkflowDraftState === "function") {
55631:       try {
55632:         persistAionWorkflowDraftState();

55919:           const from = edge.from || edge.source;
55920:           const to = edge.to || edge.target;
55921:           return String(from) !== String(resolvedNodeId) && String(to) !== String(resolvedNodeId);
55922:         });
55923: 
55924:         if (!nextNodes.length && typeof makeBlankWorkflowGraph === "function") {
55925:           window.__aionWorkflowGraph = makeBlankWorkflowGraph();
55926:           window.__aionWorkflowSelectedNodeId = null;
55927:         } else {
55928:           graph.nodes = nextNodes;
55929:           graph.edges = nextEdges;
55930:           graph.dirty = true;
55931:           window["__aionWorkflowGraph"] = graph;
55932: 
55933:           if (window.__aionWorkflowSelectedNodeId === resolvedNodeId) {
55934:             window.__aionWorkflowSelectedNodeId =
55935:               nextNodes[nextNodes.length - 1]?.id || nextNodes[0]?.id || null;
55936:           }
55937:         }
55938: 
55939:         try {
55940:           if (typeof compileAndAttachAionWorkflowGlyph === "function") {
55941:             compileAndAttachAionWorkflowGlyph(window.__aionWorkflowGraph);
55942:           }
55943:         } catch (error) {
55944:           console.warn("[workflow-delete] compile skipped", error);
55945:         }

56580:       try {
56581:         return getAionWorkflowDraftState();
56582:       } catch (_) {}
56583:     }
56584: 
56585:     if (!window.__aionWorkflowGraph) {
56586:       window.__aionWorkflowGraph = { nodes: [], edges: [] };
56587:     }
56588: 
56589:     return window["__aionWorkflowGraph"];
56590:   }
56591: 
56592:   function persistGraph(graph) {
56593:     window["__aionWorkflowGraph"] = graph;
56594: 
56595:     try {
56596:       if (typeof compileAndAttachAionWorkflowGlyph === "function") {
56597:         compileAndAttachAionWorkflowGlyph(graph);
56598:       }
56599:     } catch (error) {
56600:       console.warn(`[${PATCH_ID}] compile skipped`, error);
56601:     }
56602: 
56603:     try {
56604:       if (typeof persistAionWorkflowDraftState === "function") {
56605:         persistAionWorkflowDraftState();
56606:       }

57269:               ...(patch.config || {}),
57270:             },
57271:           }
57272:         : node,
57273:     );
57274: 
57275:     window.__aionWorkflowGraph = g;
57276: 
57277:     try {
57278:       if (typeof compileAndAttachAionWorkflowGlyph === "function") {
57279:         compileAndAttachAionWorkflowGlyph(g);
57280:       }
57281:     } catch (_) {}
57282: 
57283:     try {
57284:       if (typeof persistAionWorkflowDraftState === "function") {
57285:         persistAionWorkflowDraftState();
57286:       }
57287:     } catch (_) {}
57288:   }
57289: 
57290:   function removeAdvancedModal() {
57291:     document
57292:       .querySelectorAll("[data-aion-main-step-logic-modal='true']")
57293:       .forEach((el) => { el.style.display = 'none'; el.style.visibility = 'hidden'; });
57294: 
57295:     window.__aionArchitectAdvancedConfigOpen = false;

59803:       if (typeof getAionWorkflowDraftState === "function") {
59804:         return getAionWorkflowDraftState();
59805:       }
59806:     } catch (_) {}
59807: 
59808:     if (!window.__aionWorkflowGraph) {
59809:       window.__aionWorkflowGraph = {
59810:         workflow_id: createAionWorkflowId(),
59811:         name: "Untitled workflow 1",
59812:         status: "draft",
59813:         nodes: [],
59814:         edges: [],
59815:       };
59816:     }
59817: 
59818:     return window["__aionWorkflowGraph"];
59819:   }
59820: 
59821:   function selectedNode() {
59822:     const g = graph();
59823:     const nodes = Array.isArray(g.nodes) ? g.nodes : [];
59824:     const selectedId = window.__aionWorkflowSelectedNodeId;
59825: 
59826:     return (
59827:       nodes.find((node) => String(node.id) === String(selectedId)) ||
59828:       nodes[0] ||
59829:       null

59828:       nodes[0] ||
59829:       null
59830:     );
59831:   }
59832: 
59833:   function persist(g) {
59834:     window.__aionWorkflowGraph = g;
59835: 
59836:     try {
59837:       if (typeof compileAndAttachAionWorkflowGlyph === "function") {
59838:         compileAndAttachAionWorkflowGlyph(g);
59839:       }
59840:     } catch (_) {}
59841: 
59842:     try {
59843:       if (typeof persistAionWorkflowDraftState === "function") {
59844:         persistAionWorkflowDraftState();
59845:       }
59846:     } catch (_) {}
59847:   }
59848: 
59849:   function patchNode(nodeId, patch) {
59850:     const g = graph();
59851:     const nodes = Array.isArray(g.nodes) ? g.nodes : [];
59852: 
59853:     g.nodes = nodes.map((node) => {
59854:       if (String(node.id) !== String(nodeId)) return node;

70936:         .filter((edge) => edge.from && edge.to)
70937:     : nodes.slice(0, -1).map((node, index) => ({
70938:         from: node.id,
70939:         to: nodes[index + 1].id,
70940:       }));
70941: 
70942:   window.__aionWorkflowGraph = {
70943:     workflow_id: String(spec.workflow_id || `architect_${Date.now()}`),
70944:     name: String(spec.workflow_name || "AI generated workflow"),
70945:     status: "draft",
70946:     nodes,
70947:     edges,
70948:     architect_review: {
70949:       loaded_from_valid_review: true,
70950:       provider: result?.provider?.provider || reviewState.provider || "mock",
70951:       dry_run_only: true,
70952:       live_send_enabled: false,
70953:       missing_connectors: Array.isArray(spec.missing_connectors) ? spec.missing_connectors : [],
70954:       connectors_required: Array.isArray(spec.connectors_required) ? spec.connectors_required : [],
70955:     },
70956:   };
70957: 
70958:   window.__aionWorkflowSelectedNodeId = nodes[0]?.id || null;
70959:   window.__aionWorkflowInspectorOpen = false;
70960:   window.__aionWorkflowPickerMode = "";
70961:   window.__aionWorkflowLoadNotice = "AI generated workflow loaded from valid review";
70962: 

71933:       try {
71934:         const graph = getAionWorkflowDraftState();
71935:         if (graph && typeof graph === "object") return graph;
71936:       } catch (_) {}
71937:     }
71938: 
71939:     window.__aionWorkflowGraph = window.__aionWorkflowGraph || {
71940:       workflow_id: `workflow_${Date.now()}`,
71941:       name: "Untitled workflow",
71942:       status: "draft",
71943:       nodes: [],
71944:       edges: [],
71945:     };
71946: 
71947:     return window.__aionWorkflowGraph;
71948:   }
71949: 
71950:   function markDraftEdited(reason = "master_glyph_connection_staged") {
71951:     try {
71952:       if (typeof markAionWorkflowGraphEdited === "function") {
71953:         markAionWorkflowGraphEdited(reason);
71954:       }
71955:     } catch (_) {}
71956: 
71957:     try {
71958:       if (typeof compileAndAttachAionWorkflowGlyph === "function") {
71959:         compileAndAttachAionWorkflowGlyph(getGraph());

72025:     };
72026: 
72027:     graph.edges.push(edge);
72028:     graph.dirty = true;
72029:     graph.updated_at = new Date().toISOString();
72030: 
72031:     window.__aionWorkflowGraph = graph;
72032:     window.__aionMasterGlyphLastStagedConnection = edge;
72033: 
72034:     if (typeof safePatchMessage === "function") {
72035:       safePatchMessage("Draft glyph connection staged. No workflow was executed.", "success");
72036:     }
72037: 
72038:     markDraftEdited("master_glyph_connection_staged");
72039:     return edge;
72040:   }
72041: 
72042:   function patchConnectionPreviewRows() {
72043:     document
72044:       .querySelectorAll("[data-aion-master-glyph-connection-preview='true'] code")
72045:       .forEach((code) => {
72046:         if (code.dataset.aionMasterGlyphStageBound === "true") return;
72047: 
72048:         const text = String(code.textContent || "");
72049:         const parts = text.split("→").map((part) => part.trim()).filter(Boolean);
72050:         if (parts.length !== 2) return;
72051: 

72222:       String(node.id || "").includes("master_glyph") ||
72223:       String(node.id || "").includes("call_workflow_glyph")
72224:     );
72225:   }
72226: 
72227:   function getWorkflowGraph() {
72228:     if (window.__aionWorkflowGraph && typeof window.__aionWorkflowGraph === "object") {
72229:       return window.__aionWorkflowGraph;
72230:     }
72231: 
72232:     if (window.state?.workflow_graph && typeof window.state.workflow_graph === "object") {
72233:       return window.state.workflow_graph;
72234:     }
72235: 
72236:     if (window.state?.workflowGraph && typeof window.state.workflowGraph === "object") {
72237:       return window.state.workflowGraph;
72238:     }
72239: 
72240:     if (window.aionWorkflowGraph && typeof window.aionWorkflowGraph === "object") {
72241:       return window.aionWorkflowGraph;
72242:     }
72243: 
72244:     return null;
72245:   }
72246: 
72247:   function clearStagedMasterGlyphs() {
72248:     const graph = getWorkflowGraph();

72271:         const from = String(edge.from || edge.source || "");
72272:         const to = String(edge.to || edge.target || "");
72273:         return !stagedIds.has(from) && !stagedIds.has(to);
72274:       });
72275:     }
72276: 
72277:     if (window.__aionWorkflowGraph === graph) {
72278:       window.__aionWorkflowGraph = graph;
72279:     }
72280: 
72281:     if (window.state?.workflow_graph === graph) {
72282:       window.state.workflow_graph = graph;
72283:     }
72284: 
72285:     if (window.state?.workflowGraph === graph) {
72286:       window.state.workflowGraph = graph;
72287:     }
72288: 
72289:     window.__aionMasterGlyphSelectedStagedNodeId = null;
72290:     window.__aionMasterGlyphStagedInspectorOpen = false;
72291:     window.__aionMasterGlyphConnectionPreviewOpen = false;
72292:     window.__aionMasterGlyphLastStagedConnection = null;
72293: 
72294:     notify(`Cleared ${stagedIds.size} staged glyph${stagedIds.size === 1 ? "" : "s"}.`, "success");
72295:     requestSafeRender();
72296: 
72297:     if (typeof window.__syncAionMasterGlyphStagedNodeInspector === "function") {

72272:         const to = String(edge.to || edge.target || "");
72273:         return !stagedIds.has(from) && !stagedIds.has(to);
72274:       });
72275:     }
72276: 
72277:     if (window.__aionWorkflowGraph === graph) {
72278:       window.__aionWorkflowGraph = graph;
72279:     }
72280: 
72281:     if (window.state?.workflow_graph === graph) {
72282:       window.state.workflow_graph = graph;
72283:     }
72284: 
72285:     if (window.state?.workflowGraph === graph) {
72286:       window.state.workflowGraph = graph;
72287:     }
72288: 
72289:     window.__aionMasterGlyphSelectedStagedNodeId = null;
72290:     window.__aionMasterGlyphStagedInspectorOpen = false;
72291:     window.__aionMasterGlyphConnectionPreviewOpen = false;
72292:     window.__aionMasterGlyphLastStagedConnection = null;
72293: 
72294:     notify(`Cleared ${stagedIds.size} staged glyph${stagedIds.size === 1 ? "" : "s"}.`, "success");
72295:     requestSafeRender();
72296: 
72297:     if (typeof window.__syncAionMasterGlyphStagedNodeInspector === "function") {
72298:       window.setTimeout(window.__syncAionMasterGlyphStagedNodeInspector, 80);

72363:       window.setTimeout(window.__isolateAionMasterGlyphMode, 80);
72364:     }
72365:   }
72366: 
72367:   function getGraph() {
72368:     if (!window.__aionWorkflowGraph || typeof window.__aionWorkflowGraph !== "object") {
72369:       window.__aionWorkflowGraph = {
72370:         schema_version: "aion.workflow_canvas_graph.v1",
72371:         nodes: [],
72372:         edges: [],
72373:       };
72374:     }
72375: 
72376:     if (!Array.isArray(window.__aionWorkflowGraph.nodes)) {
72377:       window.__aionWorkflowGraph.nodes = [];
72378:     }
72379: 
72380:     if (!Array.isArray(window.__aionWorkflowGraph.edges)) {
72381:       window.__aionWorkflowGraph.edges = [];
72382:     }
72383: 
72384:     return window.__aionWorkflowGraph;
72385:   }
72386: 
72387:   function lowerBlob(value) {
72388:     try {
72389:       return JSON.stringify(value || {}).toLowerCase();

72446:     graph.edges = graph.edges.filter((edge) => {
72447:       const from = String(edge.from || edge.source || edge.from_node || edge.sourceNode || "");
72448:       const to = String(edge.to || edge.target || edge.to_node || edge.targetNode || "");
72449:       return !stagedIds.has(from) && !stagedIds.has(to);
72450:     });
72451: 
72452:     window.__aionWorkflowGraph = graph;
72453: 
72454:     if (typeof compileAndAttachAionWorkflowGlyph === "function") {
72455:       try {
72456:         compileAndAttachAionWorkflowGlyph(window.__aionWorkflowGraph);
72457:       } catch (err) {
72458:         console.warn("[AION Master Glyph] compile after clear failed:", err);
72459:       }
72460:     }
72461: 
72462:     window.__aionMasterGlyphSelectedStagedNodeId = null;
72463:     window.__aionMasterGlyphStagedInspectorOpen = false;
72464:     window.__aionMasterGlyphConnectionPreviewOpen = false;
72465:     window.__aionMasterGlyphLastStagedConnection = null;
72466: 
72467:     const cleared = beforeNodes - graph.nodes.length;
72468:     toast(`Cleared ${cleared} staged glyph${cleared === 1 ? "" : "s"}.`, "success");
72469:     renderSoon();
72470:   }
72471: 
72472:   document.addEventListener("click", (event) => {

72890:         })
72891:       : [];
72892: 
72893:     graph.dirty = true;
72894:     graph.updated_at = new Date().toISOString();
72895: 
72896:     window.__aionWorkflowGraph = graph;
72897:     window.__aionWorkflowSelectedNodeId = null;
72898:     window.__aionMasterGlyphSelectedStagedNodeId = null;
72899:     window.__aionMasterGlyphStagedInspectorOpen = false;
72900:     window.__aionMasterGlyphConnectionPreviewOpen = false;
72901: 
72902:     try {
72903:       if (typeof compileAndAttachAionWorkflowGlyph === "function") {
72904:         compileAndAttachAionWorkflowGlyph(graph);
72905:       }
72906:     } catch (_) {}
72907: 
72908:     try {
72909:       if (typeof persistAionWorkflowDraftState === "function") {
72910:         persistAionWorkflowDraftState();
72911:       }
72912:     } catch (_) {}
72913: 
72914:     notify(`Cleared ${removedIds.size} staged glyph node${removedIds.size === 1 ? "" : "s"}.`, "success");
72915:     requestSafeRender();
72916:   }

73531:     return { my, universal: [...universalRaw, ...universalFallback] };
73532:   }
73533: 
73534:   function stageGlyph(workflowId, code) {
73535:     window.__aionActiveWorkflowTab = "main";
73536:     window.__aionWorkflowMainGraph = window.__aionWorkflowMainGraph || window.__aionWorkflowGraph || {};
73537:     window.__aionWorkflowGraph = window.__aionWorkflowMainGraph;
73538:     if (typeof window.__stageAionMasterGlyphToWorkflowCanvas === "function") {
73539:       const staged = window.__stageAionMasterGlyphToWorkflowCanvas(workflowId);
73540:       if (staged) {
73541:         closeModal();
73542:         notify(`Staged ${code} to canvas.`, "success");
73543:         return;
73544:       }
73545:     }
73546: 
73547:     notify(`Stage handler could not resolve ${code}.`, "warning");
73548:   }
73549: 
73550:   function renderCard(item) {
73551:     const connectors = Array.isArray(item.required_connectors) && item.required_connectors.length
73552:       ? item.required_connectors.join(", ")
73553:       : "None";
73554: 
73555:     return `
73556:       <article class="aion-glyph-library-v36-card">
73557:         <div class="aion-glyph-library-v36-code">${esc(item.glyph_code)}</div>

74458:       },
74459:     });
74460: 
74461:     graph.dirty = true;
74462:     graph.updated_at = new Date().toISOString();
74463: 
74464:     window.__aionWorkflowGraph = graph;
74465:     window.__aionWorkflowSelectedNodeId = nodeId;
74466: 
74467:     try {
74468:       if (typeof compileAndAttachAionWorkflowGlyph === "function") {
74469:         compileAndAttachAionWorkflowGlyph(graph);
74470:       }
74471:     } catch (_) {}
74472: 
74473:     try {
74474:       if (typeof persistAionWorkflowDraftState === "function") {
74475:         persistAionWorkflowDraftState();
74476:       }
74477:     } catch (_) {}
74478: 
74479:     closeModal();
74480:     notify(`Staged ${glyph.glyph_code} to canvas.`, "success");
74481: 
74482:     if (typeof window["requestRender"] === "function") {
74483:       window["requestRender"]();
74484:     }

74569:       dirty: false,
74570:       updated_at: new Date().toISOString(),
74571:     };
74572:   }
74573: 
74574:   function setActiveWorkflowGraphForTab(graph) {
74575:     window.__aionWorkflowGraph = graph;
74576:     window.__aionWorkflowSelectedNodeId = graph?.nodes?.[0]?.id || null;
74577: 
74578:     try {
74579:       if (typeof compileAndAttachAionWorkflowGlyph === "function") {
74580:         compileAndAttachAionWorkflowGlyph(graph);
74581:       }
74582:     } catch (_) {}
74583:   }
74584: 
74585:   function openWorkflow(code) {
74586:     const glyph = findGlyph(code);
74587:     if (!glyph) {
74588:       notify(`Could not find glyph ${code}.`, "error");
74589:       return;
74590:     }
74591: 
74592:     const openedGraph = buildOpenedGlyphWorkflowGraph(glyph);
74593:     const openedCode = String(openedGraph.glyph_code || glyph.glyph_code || code || "").trim();
74594: 
74595:     window.__aionOpenedGlyphWorkflowGraphsByCode =

77229:       typeof window.__aionOpenedGlyphWorkflowGraphsByCode === "object"
77230:         ? window.__aionOpenedGlyphWorkflowGraphsByCode
77231:         : {};
77232: 
77233:     if (store[code]) {
77234:       window.__aionOpenedGlyphWorkflowGraph = store[code];
77235:       window.__aionWorkflowGraph = store[code];
77236:     }
77237: 
77238:     renderTopTabs();
77239: 
77240:     if (typeof window.__renderAionGlyphWorkflowTab === "function") {
77241:       window.__renderAionGlyphWorkflowTab();
77242:     }
77243: 
77244:     if (typeof window["requestRender"] === "function") {
77245:       window["requestRender"]();
77246:     }
77247: 
77248:     notify(`Opened ${code} in a workflow tab.`, "success");
77249:   }
77250: 
77251:   function closeGlyphTopTab(code) {
77252:     const target = String(code || "");
77253:     window.__aionGlyphWorkflowTabs = window.__aionGlyphWorkflowTabs.filter(
77254:       (tab) => String(tab?.glyph_code || "") !== target
77255:     );

77279:       window.__aionActiveGlyphWorkflowCode = "";
77280:       window.__aionActiveWorkflowTab = "main";
77281:       window.__aionGlyphWorkflowTabOpen = false;
77282:       window.__aionOpenedGlyphWorkflow = null;
77283: 
77284:       if (window.__aionWorkflowMainGraph && typeof window.__aionWorkflowMainGraph === "object") {
77285:         window.__aionWorkflowGraph = window.__aionWorkflowMainGraph;
77286:       }
77287: 
77288:       renderTopTabs();
77289: 
77290:       if (typeof window.__renderAionGlyphWorkflowTab === "function") {
77291:         window.__renderAionGlyphWorkflowTab();
77292:       }
77293: 
77294:       if (typeof window["requestRender"] === "function") {
77295:         window["requestRender"]();
77296:       }
77297: 
77298:       return;
77299:     }
77300: 
77301:     const glyph = window.__aionGlyphWorkflowTabs.find(
77302:       (tab) => String(tab?.glyph_code || "") === target
77303:     );
77304: 
77305:     if (!glyph) {

77319:         ? window.__aionOpenedGlyphWorkflowGraphsByCode
77320:         : {};
77321: 
77322:     const graph = store[target] || store[String(target).toUpperCase()] || store[String(target).toLowerCase()];
77323:     if (graph && typeof graph === "object") {
77324:       window.__aionOpenedGlyphWorkflowGraph = graph;
77325:       window.__aionWorkflowGraph = graph;
77326:       window.__aionWorkflowSelectedNodeId = graph.nodes?.[0]?.id || null;
77327:     }
77328: 
77329:     renderTopTabs();
77330: 
77331:     if (typeof window.__renderAionGlyphWorkflowTab === "function") {
77332:       window.__renderAionGlyphWorkflowTab();
77333:     }
77334: 
77335:     if (typeof window["requestRender"] === "function") {
77336:       window["requestRender"]();
77337:     }
77338:   }
77339: 
77340:   function ensureStyle() {
77341:     if (document.getElementById(STYLE_ID)) return;
77342: 
77343:     const style = document.createElement("style");
77344:     style.id = STYLE_ID;
77345:     style.textContent = `

80228:      */
80229:     let graph = { nodes: [], edges: [] };
80230:     try {
80231:       if (typeof getAionWorkflowDraftState === "function") {
80232:         const draft = getAionWorkflowDraftState();
80233:         if (draft && typeof draft === "object") graph = draft;
80234:       } else if (window.__aionWorkflowGraph && typeof window.__aionWorkflowGraph === "object") {
80235:         graph = window.__aionWorkflowGraph;
80236:       }
80237:     } catch (_) {
80238:       graph = window.__aionWorkflowGraph || { nodes: [], edges: [] };
80239:     }
80240: 
80241:     const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
80242:     const selectedId = String(node?.id || model?.node_id || "call_workflow_glyph");
80243: 
80244:     const peers = nodes
80245:       .filter((candidate) => candidate && String(candidate.id || "") !== selectedId)
80246:       .slice(0, 6);
80247: 
80248:     const inputSummary = schemaSummaryForConnectionPreviewV11(model.input_schema, "Any payload");
80249:     const outputSummary = schemaSummaryForConnectionPreviewV11(model.output_schema, "Dry-run payload");
80250: 
80251:     const renderCards = (direction) => {
80252:       if (!peers.length) {
80253:         return `<div class="aion-call-glyph-preview-empty-v11">No other workflow nodes detected yet.</div>`;
80254:       }

82654:     const store = ensureGlyphGraphStore();
82655:     store[glyphCode] = graph;
82656:     store[glyphCode.toUpperCase()] = graph;
82657:     store[glyphCode.toLowerCase()] = graph;
82658: 
82659:     window.__aionOpenedGlyphWorkflowGraph = graph;
82660:     window.__aionWorkflowGraph = graph;
82661: 
82662:     if (window.__aionOpenedGlyphWorkflow && typeof window.__aionOpenedGlyphWorkflow === "object") {
82663:       window.__aionOpenedGlyphWorkflow = {
82664:         ...window.__aionOpenedGlyphWorkflow,
82665:         glyph_code: glyphCode,
82666:         dirty: true,
82667:         updated_at: graph.updated_at,
82668:       };
82669:     }
82670: 
82671:     return graph;
82672:   }
82673: 
82674:   function hydrateActiveGlyphWorkflowGraph() {
82675:     const activeTab = String(window.__aionActiveWorkflowTab || "").toLowerCase();
82676:     const glyphCode = getActiveGlyphCode();
82677: 
82678:     if (activeTab !== "glyph" || !glyphCode || glyphCode.toLowerCase() === "main") {
82679:       return null;
82680:     }

82689: 
82690:     if (!graph || typeof graph !== "object") return null;
82691: 
82692:     graph.glyph_code = graph.glyph_code || glyphCode;
82693:     graph.tab_type = "glyph_workflow";
82694:     window.__aionOpenedGlyphWorkflowGraph = graph;
82695:     window.__aionWorkflowGraph = graph;
82696:     return graph;
82697:   }
82698: 
82699:   const previousPersist = window.persistAionWorkflowDraftState;
82700:   window.persistAionWorkflowDraftState = function persistAionWorkflowDraftStatePhase19A(...args) {
82701:     const activeTab = String(window.__aionActiveWorkflowTab || "").toLowerCase();
82702: 
82703:     if (activeTab === "glyph") {
82704:       const persisted = persistActiveGlyphWorkflowGraph("persist_call");
82705:       if (persisted) return persisted;
82706:     }
82707: 
82708:     if (typeof previousPersist === "function") {
82709:       return previousPersist.apply(this, args);
82710:     }
82711: 
82712:     return null;
82713:   };
82714: 
82715:   const previousGetActive = window.__aionGetActiveWorkflowGraph;

82728:     const tabName = String(tab || window.__aionActiveWorkflowTab || "main").toLowerCase();
82729: 
82730:     if (tabName === "glyph") {
82731:       window.__aionActiveWorkflowTab = "glyph";
82732:       window.__aionGlyphWorkflowTabOpen = true;
82733:       window.__aionOpenedGlyphWorkflowGraph = graph;
82734:       window.__aionWorkflowGraph = graph;
82735:       return persistActiveGlyphWorkflowGraph("set_active_graph") || graph;
82736:     }
82737: 
82738:     if (typeof previousSetActive === "function") {
82739:       return previousSetActive.call(this, graph, tab);
82740:     }
82741: 
82742:     window.__aionActiveWorkflowTab = "main";
82743:     window.__aionWorkflowMainGraph = graph;
82744:     window.__aionWorkflowGraph = graph;
82745:     return graph;
82746:   };
82747: 
82748:   document.addEventListener("input", (event) => {
82749:     const activeTab = String(window.__aionActiveWorkflowTab || "").toLowerCase();
82750:     if (activeTab !== "glyph") return;
82751: 
82752:     const target = event.target;
82753:     if (!target || !target.closest) return;
82754: 

82738:     if (typeof previousSetActive === "function") {
82739:       return previousSetActive.call(this, graph, tab);
82740:     }
82741: 
82742:     window.__aionActiveWorkflowTab = "main";
82743:     window.__aionWorkflowMainGraph = graph;
82744:     window.__aionWorkflowGraph = graph;
82745:     return graph;
82746:   };
82747: 
82748:   document.addEventListener("input", (event) => {
82749:     const activeTab = String(window.__aionActiveWorkflowTab || "").toLowerCase();
82750:     if (activeTab !== "glyph") return;
82751: 
82752:     const target = event.target;
82753:     if (!target || !target.closest) return;
82754: 
82755:     if (
82756:       target.closest(".aion-workflow-inspector") ||
82757:       target.closest("[data-aion-workflow-canvas-viewport='true']") ||
82758:       target.closest("[data-aion-call-workflow-glyph-contract-inspector-v3='true']")
82759:     ) {
82760:       window.setTimeout(() => persistActiveGlyphWorkflowGraph("input_edit"), 0);
82761:     }
82762:   }, true);
82763: 
82764:   document.addEventListener("change", (event) => {

82851:         closable: true,
82852:       };
82853: 
82854:       window.__aionWorkflowTabs.push(tab);
82855:       window.__aionActiveWorkflowTabId = window.__aionActiveWorkflowTabId || tab.id;
82856:       window.__aionWorkflowMainGraph = graph;
82857:       window.__aionWorkflowGraph = graph;
82858:     }
82859: 
82860:     return window.__aionWorkflowTabs;
82861:   }
82862: 
82863:   function activeWorkflowTab() {
82864:     const tabs = ensureWorkflowTabs();
82865:     const activeId = String(window.__aionActiveWorkflowTabId || tabs[0]?.id || "");
82866:     return tabs.find((tab) => String(tab.id) === activeId) || tabs[0] || null;
82867:   }
82868: 
82869:   function persistWorkflowTabs() {
82870:     const tabs = ensureWorkflowTabs().map((tab) => ({
82871:       id: tab.id,
82872:       title: tab.title,
82873:       closable: true,
82874:       graph: tab.graph,
82875:     }));
82876: 
82877:     try {

82927:     window.__aionActiveGlyphWorkflowTabCode = "main";
82928:     window.__aionActiveGlyphWorkflowCode = "";
82929:     window.__aionOpenedGlyphWorkflow = null;
82930: 
82931:     window.__aionActiveWorkflowTabId = tab.id;
82932:     window.__aionWorkflowMainGraph = tab.graph;
82933:     window.__aionWorkflowGraph = tab.graph;
82934: 
82935:     persistWorkflowTabs();
82936:     renderWorkflowTabOverlay();
82937: 
82938:     if (typeof window.requestRender === "function") {
82939:       window.requestRender();
82940:     }
82941: 
82942:     return tab.graph;
82943:   }
82944: 
82945:   function createWorkflowTab() {
82946:     const tabs = ensureWorkflowTabs();
82947:     const graph = makeBlankGraph(`Workflow ${tabs.length + 1}`);
82948:     const tab = {
82949:       id: graph.workflow_id,
82950:       title: graph.display_name,
82951:       graph,
82952:       closable: true,
82953:     };

82979:       };
82980: 
82981:       tabs.push(fresh);
82982:       window.__aionWorkflowTabs = tabs;
82983:       window.__aionActiveWorkflowTabId = fresh.id;
82984:       window.__aionWorkflowMainGraph = fresh.graph;
82985:       window.__aionWorkflowGraph = fresh.graph;
82986:     } else if (String(window.__aionActiveWorkflowTabId || "") === String(tabId)) {
82987:       const next = tabs[Math.max(0, index - 1)] || tabs[0];
82988:       if (next) {
82989:         window.__aionActiveWorkflowTabId = next.id;
82990:         window.__aionWorkflowMainGraph = next.graph;
82991:         window.__aionWorkflowGraph = next.graph;
82992:       }
82993:     }
82994: 
82995:     persistWorkflowTabs();
82996:     renderWorkflowTabOverlay();
82997: 
82998:     if (typeof window.requestRender === "function") {
82999:       window.requestRender();
83000:     }
83001:   }
83002: 
83003:   function renameWorkflowTab(tabId, title) {
83004:     const tabs = ensureWorkflowTabs();
83005:     const tab = tabs.find((item) => String(item.id) === String(tabId));

82985:       window.__aionWorkflowGraph = fresh.graph;
82986:     } else if (String(window.__aionActiveWorkflowTabId || "") === String(tabId)) {
82987:       const next = tabs[Math.max(0, index - 1)] || tabs[0];
82988:       if (next) {
82989:         window.__aionActiveWorkflowTabId = next.id;
82990:         window.__aionWorkflowMainGraph = next.graph;
82991:         window.__aionWorkflowGraph = next.graph;
82992:       }
82993:     }
82994: 
82995:     persistWorkflowTabs();
82996:     renderWorkflowTabOverlay();
82997: 
82998:     if (typeof window.requestRender === "function") {
82999:       window.requestRender();
83000:     }
83001:   }
83002: 
83003:   function renameWorkflowTab(tabId, title) {
83004:     const tabs = ensureWorkflowTabs();
83005:     const tab = tabs.find((item) => String(item.id) === String(tabId));
83006:     if (!tab) return;
83007: 
83008:     const clean = String(title || "").trim();
83009:     if (!clean) return;
83010: 
83011:     tab.title = clean;

83016:       dirty: true,
83017:       updated_at: new Date().toISOString(),
83018:     };
83019: 
83020:     if (String(window.__aionActiveWorkflowTabId || "") === String(tabId)) {
83021:       window.__aionWorkflowMainGraph = tab.graph;
83022:       window.__aionWorkflowGraph = tab.graph;
83023:     }
83024: 
83025:     persistWorkflowTabs();
83026:     renderWorkflowTabOverlay();
83027:   }
83028: 
83029:   function syncActiveGraphIntoTab(reason = "sync") {
83030:     const activeTabType = String(window.__aionActiveWorkflowTab || "main").toLowerCase();
83031:     if (activeTabType === "glyph") return null;
83032: 
83033:     const tab = activeWorkflowTab();
83034:     if (!tab) return null;
83035: 
83036:     const graph = window.__aionWorkflowGraph || window.__aionWorkflowMainGraph || tab.graph;
83037:     if (!graph || typeof graph !== "object") return null;
83038: 
83039:     tab.graph = {
83040:       ...clone(graph),
83041:       tab_type: "main_workflow",
83042:       dirty: graph.dirty === true,

83043:       dirty_reason: graph.dirty_reason || reason,
83044:       updated_at: new Date().toISOString(),
83045:     };
83046: 
83047:     tab.title = tab.graph.display_name || tab.graph.name || tab.title || "Untitled workflow";
83048:     window.__aionWorkflowMainGraph = tab.graph;
83049:     window.__aionWorkflowGraph = tab.graph;
83050: 
83051:     persistWorkflowTabs();
83052:     return tab.graph;
83053:   }
83054: 
83055:   function ensureStyle() {
83056:     if (document.getElementById(STYLE_ID)) return;
83057: 
83058:     const style = document.createElement("style");
83059:     style.id = STYLE_ID;
83060:     style.textContent = `
83061:       #${TABBAR_ID} .aion-phase19b-workflow-tab {
83062:         border-style: solid;
83063:       }
83064: 
83065:       #${TABBAR_ID} .aion-phase19b-workflow-tab.is-active {
83066:         background: #ffffff !important;
83067:         color: #0f172a !important;
83068:       }
83069: 

83288:       status: "draft",
83289:     });
83290: 
83291:     window.__aionWorkflowMainGraph = graph;
83292: 
83293:     if (window.__aionActiveWorkflowTab !== "glyph") {
83294:       window.__aionWorkflowGraph = graph;
83295:     }
83296: 
83297:     return graph;
83298:   }
83299: 
83300:   function ensureGlyphGraph() {
83301:     const existing =
83302:       window.__aionOpenedGlyphWorkflowGraph ||
83303:       window.__aionGlyphWorkflowGraph ||
83304:       null;
83305: 
83306:     if (!existing) return null;
83307: 
83308:     const graph = normaliseGraph(existing, {
83309:       workflow_id: existing.workflow_id || existing.child_workflow_id || `glyph_workflow_${Date.now()}`,
83310:       name: existing.display_name || existing.name || existing.glyph_code || "Glyph workflow",
83311:       display_name: existing.display_name || existing.name || existing.glyph_code || "Glyph workflow",
83312:       status: existing.readOnly === true ? "readonly" : "draft",
83313:     });
83314: 

83315:     graph.tab_type = "glyph_workflow";
83316:     graph.source = graph.source || "opened_glyph_workflow";
83317: 
83318:     window.__aionOpenedGlyphWorkflowGraph = graph;
83319: 
83320:     if (window.__aionActiveWorkflowTab === "glyph") {
83321:       window.__aionWorkflowGraph = graph;
83322:     }
83323: 
83324:     return graph;
83325:   }
83326: 
83327:   function getActiveGraph() {
83328:     if (window.__aionActiveWorkflowTab === "glyph" || window.__aionGlyphWorkflowTabOpen === true) {
83329:       return ensureGlyphGraph() || ensureMainGraph();
83330:     }
83331:     return ensureMainGraph();
83332:   }
83333: 
83334:   function setActiveGraph(graph, tab) {
83335:     const tabName = tab || window.__aionActiveWorkflowTab || "main";
83336:     const next = normaliseGraph(graph, { name: tabName === "glyph" ? "Glyph workflow" : "Main workflow" });
83337: 
83338:     if (tabName === "glyph") {
83339:       window.__aionActiveWorkflowTab = "glyph";
83340:       window.__aionGlyphWorkflowTabOpen = true;
83341:       window.__aionOpenedGlyphWorkflowGraph = next;

83336:     const next = normaliseGraph(graph, { name: tabName === "glyph" ? "Glyph workflow" : "Main workflow" });
83337: 
83338:     if (tabName === "glyph") {
83339:       window.__aionActiveWorkflowTab = "glyph";
83340:       window.__aionGlyphWorkflowTabOpen = true;
83341:       window.__aionOpenedGlyphWorkflowGraph = next;
83342:       window.__aionWorkflowGraph = next;
83343:       return next;
83344:     }
83345: 
83346:     window.__aionActiveWorkflowTab = "main";
83347:     window.__aionWorkflowMainGraph = next;
83348:     window.__aionWorkflowGraph = next;
83349:     return next;
83350:   }
83351: 
83352:   window.__aionGetActiveWorkflowGraph = getActiveGraph;
83353:   window.__aionSetActiveWorkflowGraph = setActiveGraph;
83354: 
83355:   window.setActiveWorkflowGraphForTab = function setActiveWorkflowGraphForTab(graph) {
83356:     return setActiveGraph(graph, window.__aionActiveWorkflowTab || "main");
83357:   };
83358: 
83359:   window.__aionSwitchWorkflowTab = function switchWorkflowTab(tab) {
83360:     const name = String(tab || "main").toLowerCase();
83361: 
83362:     if (name === "glyph") {

83342:       window.__aionWorkflowGraph = next;
83343:       return next;
83344:     }
83345: 
83346:     window.__aionActiveWorkflowTab = "main";
83347:     window.__aionWorkflowMainGraph = next;
83348:     window.__aionWorkflowGraph = next;
83349:     return next;
83350:   }
83351: 
83352:   window.__aionGetActiveWorkflowGraph = getActiveGraph;
83353:   window.__aionSetActiveWorkflowGraph = setActiveGraph;
83354: 
83355:   window.setActiveWorkflowGraphForTab = function setActiveWorkflowGraphForTab(graph) {
83356:     return setActiveGraph(graph, window.__aionActiveWorkflowTab || "main");
83357:   };
83358: 
83359:   window.__aionSwitchWorkflowTab = function switchWorkflowTab(tab) {
83360:     const name = String(tab || "main").toLowerCase();
83361: 
83362:     if (name === "glyph") {
83363:       window.__aionActiveWorkflowTab = "glyph";
83364:       ensureGlyphGraph();
83365:     } else {
83366:       window.__aionActiveWorkflowTab = "main";
83367:       window.__aionGlyphWorkflowTabOpen = false;
83368:       ensureMainGraph();

83407: 
83408:   const previousStage = window.__stageAionGlyphToCanvas || window.__stageAionMasterGlyphToWorkflowCanvas;
83409:   window.__stageAionGlyphToCanvas = function stageAionGlyphToCanvasMainOnly(rawGlyph) {
83410:     const main = ensureMainGraph();
83411:     window.__aionActiveWorkflowTab = "main";
83412:     window.__aionGlyphWorkflowTabOpen = false;
83413:     window.__aionWorkflowGraph = main;
83414: 
83415:     let node = null;
83416:     if (typeof previousStage === "function") {
83417:       node = previousStage(rawGlyph);
83418:     }
83419: 
83420:     window.__aionWorkflowMainGraph = window.__aionWorkflowGraph || main;
83421: 
83422:     if (typeof window["requestRender"] === "function") {
83423:       window["requestRender"]();
83424:     }
83425: 
83426:     return node;
83427:   };
83428: 
83429:   window.__stageAionMasterGlyphToWorkflowCanvas = function stageAionMasterGlyphToWorkflowCanvasMainOnly(workflowId) {
83430:     const glyphs = []
83431:       .concat(Array.isArray(window.__aionBackendWorkflowGlyphs) ? window.__aionBackendWorkflowGlyphs : [])
83432:       .concat(Array.isArray(window.__aionBackendGlyphs) ? window.__aionBackendGlyphs : [])
83433:       .concat(Array.isArray(window.__aionWorkflowGlyphs) ? window.__aionWorkflowGlyphs : [])

95041: 
95042:     if (typeof getAionWorkflowDraftState === "function") {
95043:       const graph = getAionWorkflowDraftState();
95044:       if (graph && typeof graph === "object") return graph;
95045:     }
95046: 
95047:     window.__aionWorkflowGraph = window.__aionWorkflowGraph || {
95048:       nodes: [],
95049:       edges: [],
95050:       canvas_notes: [],
95051:     };
95052:     return window.__aionWorkflowGraph;
95053:   }
95054: 
95055:   function normaliseNotes(graph) {
95056:     graph.canvas_notes = Array.isArray(graph.canvas_notes) ? graph.canvas_notes : [];
95057:     return graph.canvas_notes;
95058:   }
95059: 
95060:   function isLegacyStickyNoteNode(node) {
95061:     const config = node?.config && typeof node.config === "object" ? node.config : {};
95062:     const hay = [
95063:       node?.id,
95064:       node?.type,
95065:       node?.kind,
95066:       node?.node_type,
95067:       node?.title,

95085:   function persistGraph(reason = "phase19d_canvas_note_update") {
95086:     const graph = getGraph();
95087:     graph.dirty = true;
95088:     graph.dirty_reason = reason;
95089:     graph.updated_at = new Date().toISOString();
95090: 
95091:     window.__aionWorkflowGraph = graph;
95092: 
95093:     if (String(window.__aionActiveWorkflowTab || "").toLowerCase() !== "glyph") {
95094:       window.__aionWorkflowMainGraph = graph;
95095:     }
95096: 
95097:     if (String(window.__aionActiveWorkflowTab || "").toLowerCase() === "glyph") {
95098:       if (typeof window.__aionPersistActiveGlyphWorkflowGraph === "function") {
95099:         try {
95100:           window.__aionPersistActiveGlyphWorkflowGraph(reason);
95101:           return;
95102:         } catch (_) {}
95103:       }
95104:     }
95105: 
95106:     if (typeof persistAionWorkflowDraftState === "function") {
95107:       try { persistAionWorkflowDraftState(); } catch (_) {}
95108:     }
95109:   }
95110: 
95111:   function migrateAndRemoveLegacyStickyNodes() {

97661:     const graph = getGraph();
97662: 
97663:     if (graph && typeof graph === "object") {
97664:       graph.dirty = true;
97665:       graph.dirty_reason = reason;
97666:       graph.updated_at = new Date().toISOString();
97667:       window.__aionWorkflowGraph = graph;
97668: 
97669:       if (String(window.__aionActiveWorkflowTab || "").toLowerCase() !== "glyph") {
97670:         window.__aionWorkflowMainGraph = graph;
97671:       }
97672:     }
97673: 
97674:     if (String(window.__aionActiveWorkflowTab || "").toLowerCase() === "glyph") {
97675:       if (typeof window.__aionPersistActiveGlyphWorkflowGraph === "function") {
97676:         try {
97677:           window.__aionPersistActiveGlyphWorkflowGraph(reason);
97678:           return;
97679:         } catch (_) {}
97680:       }
97681:     }
97682: 
97683:     if (typeof compileAndAttachAionWorkflowGlyph === "function") {
97684:       try { compileAndAttachAionWorkflowGlyph(graph); } catch (_) {}
97685:     }
97686: 
97687:     if (typeof persistAionWorkflowDraftState === "function") {

98225: 
98226:     graph.nodes = graph.nodes.map(applyPolicyToCustomFunctionNode);
98227:     graph.dirty = true;
98228:     graph.dirty_reason = "phase19e5_custom_function_policy_lock";
98229:     graph.updated_at = new Date().toISOString();
98230: 
98231:     window.__aionWorkflowGraph = graph;
98232:     if (String(window.__aionActiveWorkflowTab || "").toLowerCase() !== "glyph") {
98233:       window.__aionWorkflowMainGraph = graph;
98234:     }
98235: 
98236:     return true;
98237:   }
98238: 
98239:   function patchVisibleEditorText() {
98240:     const editors = Array.from(document.querySelectorAll(
98241:       [
98242:         "[data-aion-phase19e-final-custom-function-takeover='true']",
98243:         "[data-aion-phase19e-modal-grid-replaced='true']",
98244:         "[data-aion-phase19e-real-custom-function-editor='true']",
98245:         ".aion-phase19e-modal-custom-function-editor",
98246:         ".aion-phase19e-real-custom-function-editor",
98247:       ].join(",")
98248:     ));
98249: 
98250:     for (const editor of editors) {
98251:       editor.setAttribute("data-aion-phase19e5-policy", "saved_sandbox_contract");

100910:       dirty: true,
100911:       dirty_reason: "workflow_title_tab_sync",
100912:       updated_at: new Date().toISOString(),
100913:     };
100914: 
100915:     window.__aionWorkflowMainGraph = tab.graph;
100916:     window.__aionWorkflowGraph = tab.graph;
100917: 
100918:     persistTabs();
100919: 
100920:     if (typeof window.__aionRenderWorkflowCanvasTabs === "function") {
100921:       window.__aionRenderWorkflowCanvasTabs();
100922:     }
100923:   }
100924: 
100925:   let timer = null;
100926:   function scheduleSync() {
100927:     window.clearTimeout(timer);
100928:     timer = window.setTimeout(syncTitleToActiveWorkflowTab, 120);
100929:   }
100930: 
100931:   document.addEventListener("input", (event) => {
100932:     if (event.target?.closest?.(".aion-workflow-title-input, [data-aion-workflow-title-input='true'], [data-aion-workflow-title='true']")) {
100933:       scheduleSync();
100934:     }
100935:   }, true);
100936: 


## Existing localStorage keys near workflow / goal / pilot

- line 7934: `localStorage.getItem("aion.departmentIntelligence.v1"`
- line 9381: `AION_CENTRAL_PILOT_QUEUE_STORAGE_KEY = "aion.centralPilotQueue"`
- line 15367: `localStorage.setItem("aion.liveAgents.selectedDepartment.v1", "finance"`
- line 15482: `localStorage.setItem("aion.liveAgents.focusDepartment.v1", "finance"`
- line 15483: `localStorage.setItem("aion.liveAgents.selectedDepartment.v1", "finance"`
- line 18465: `AION_WORKFLOW_DRAFT_STORAGE_KEY = "aion.workflow_builder.current_draft.v1"`
- line 18958: `localStorage.getItem(AION_WORKFLOW_DRAFT_STORAGE_KEY`
- line 19137: `localStorage.setItem(AION_WORKFLOW_DRAFT_STORAGE_KEY, JSON.stringify(compactGraph`
- line 22926: `AION_FILE_CABINET_STORAGE_KEY = "aion.workflow_file_cabinet.v1"`
- line 30124: `localStorage.getItem("aion.departmentIntelligence.v1"`
- line 30137: `localStorage.setItem("aion.departmentIntelligence.v1", JSON.stringify(ledger`
- line 30180: `AION_DEPARTMENT_INTELLIGENCE_STORAGE_KEY =
    window.AION_DEPARTMENT_INTELLIGENCE_STORAGE_KEY || "aion.departmentIntelligence.v1"`
- line 30185: `localStorage.getItem(window.AION_DEPARTMENT_INTELLIGENCE_STORAGE_KEY`
- line 30196: `localStorage.setItem(window.AION_DEPARTMENT_INTELLIGENCE_STORAGE_KEY, JSON.stringify(value`
- line 50173: `localStorage.setItem("aion.workflow.dark_mode.enabled", enabled ? "1" : "0"`
- line 50187: `localStorage.getItem("aion.workflow.dark_mode.enabled"`
- line 82807: `STORAGE_KEY = "aion.workflow_builder.workflow_tabs.v1"`
- line 82878: `localStorage.setItem(STORAGE_KEY, JSON.stringify({
        active_id: window.__aionActiveWorkflowTabId || tabs[0]?.id || "",
        tabs,
        saved_at: new Date(`
- line 88052: `localStorage.getItem(AION_GOAL_ENGINE_MULTI_AGENT_REPLAY_HISTORY_V1`
- line 88064: `localStorage.setItem(
        AION_GOAL_ENGINE_MULTI_AGENT_REPLAY_HISTORY_V1,
        JSON.stringify(safeHistory`
- line 100772: `STORAGE_KEY = "aion.workflow_builder.workflow_tabs.v1"`
- line 100857: `STORAGE_KEY = "aion.workflow_builder.workflow_tabs.v1"`
- line 100878: `localStorage.setItem(STORAGE_KEY, JSON.stringify({
        active_id: window.__aionActiveWorkflowTabId || tabs[0]?.id || "",
        tabs: tabs.map((tab`
