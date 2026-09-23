using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Networking;

namespace Tessaris.SpatialBoardroom
{
    /// <summary>
    /// Dependency-free visual MVP. The scene is assembled procedurally so the
    /// first build can be proven without purchasing or redistributing assets.
    /// </summary>
    public sealed class SpatialBoardroomBootstrap : MonoBehaviour
    {
        private readonly List<BoardroomAgentView> agents = new();
        private readonly List<BoardroomAgentView> dynamicBoardMembers = new();
        private readonly List<TessarisBoardroomMember> boardMembers = new();
        private Transform cameraRig;
        private Camera sceneCamera;
        private Vector3 desiredCameraPosition;
        private Vector3 desiredLookTarget;
        private string meetingCaption = "Boardroom ready — choose an adviser or call Operations.";
        private bool operationsCalled;
        private Material pearlWhite;
        private Material charcoal;
        private Material warmWhite;
        private Material glass;
        private Material aionBlue;
        private GUIStyle titleStyle;
        private GUIStyle captionStyle;
        private GUIStyle buttonStyle;
        private TessarisSessionBridge bridge;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        private static void EnsureRuntime()
        {
            if (FindFirstObjectByType<SpatialBoardroomBootstrap>() == null)
            {
                new GameObject("Tessaris Spatial Boardroom").AddComponent<SpatialBoardroomBootstrap>();
            }
        }

        private void Awake()
        {
            Application.targetFrameRate = 60;
            QualitySettings.vSyncCount = 1;
            CreateMaterials();
            BuildRoom();
            BuildTable();
            BuildPresentationWall();
            BuildAgents();
            boardMembers.Add(new TessarisBoardroomMember { id = "aion", label = "AION", role = "Pilot", connected = true });
            BuildLightingAndCamera();
            FocusOverview();

            bridge = gameObject.AddComponent<TessarisSessionBridge>();
            bridge.EventReceived += HandleTessarisEvent;
        }

        private void Update()
        {
            if (sceneCamera == null) return;
            cameraRig.position = Vector3.Lerp(cameraRig.position, desiredCameraPosition, Time.deltaTime * 2.3f);
            var direction = desiredLookTarget - cameraRig.position;
            if (direction.sqrMagnitude > 0.01f)
            {
                cameraRig.rotation = Quaternion.Slerp(
                    cameraRig.rotation,
                    Quaternion.LookRotation(direction.normalized, Vector3.up),
                    Time.deltaTime * 2.8f);
            }

            if (Input.GetKeyDown(KeyCode.Alpha1)) FocusAgent("AION");
            if (Input.GetKeyDown(KeyCode.Alpha2)) FocusAgent("Sales");
            if (Input.GetKeyDown(KeyCode.Alpha3)) FocusAgent("Finance");
            if (Input.GetKeyDown(KeyCode.Alpha4)) FocusAgent("Marketing");
            if (Input.GetKeyDown(KeyCode.Alpha5)) FocusAgent("People");
            if (Input.GetKeyDown(KeyCode.O)) CallOperations();
            if (Input.GetKeyDown(KeyCode.Escape)) FocusOverview();
            if (Input.GetMouseButtonDown(0) && sceneCamera != null && Input.mousePosition.y < Screen.height - 165f)
            {
                var ray = sceneCamera.ScreenPointToRay(Input.mousePosition);
                if (Physics.Raycast(ray, out var hit, 100f))
                {
                    var selected = hit.collider.GetComponentInParent<BoardroomAgentView>();
                    if (selected != null) SelectAgent(selected);
                }
            }
        }

        private void CreateMaterials()
        {
            pearlWhite = MakeMaterial("Pearl ceramic", new Color(0.86f, 0.90f, 0.94f), 0.22f, 0.88f);
            charcoal = MakeMaterial("Charcoal", new Color(0.025f, 0.035f, 0.055f), 0.65f, 0.32f);
            warmWhite = MakeMaterial("Warm white", new Color(0.94f, 0.96f, 0.98f), 0.08f, 0.72f);
            glass = MakeMaterial("Glass", new Color(0.18f, 0.30f, 0.38f), 0.72f, 0.9f);
            aionBlue = MakeMaterial("AION blue", new Color(0.01f, 0.42f, 0.95f), 0.35f, 0.88f, true);
        }

        private static Material MakeMaterial(string label, Color color, float metallic, float smoothness, bool emissive = false)
        {
            var shader = Shader.Find("Universal Render Pipeline/Lit") ?? Shader.Find("Standard");
            var material = new Material(shader) { name = label, color = color };
            if (material.HasProperty("_Metallic")) material.SetFloat("_Metallic", metallic);
            if (material.HasProperty("_Smoothness")) material.SetFloat("_Smoothness", smoothness);
            if (emissive && material.HasProperty("_EmissionColor"))
            {
                material.EnableKeyword("_EMISSION");
                material.SetColor("_EmissionColor", color * 2.8f);
            }
            return material;
        }

        private void BuildRoom()
        {
            CreateBlock("Floor", new Vector3(0, -0.16f, 0), new Vector3(15, 0.3f, 11), charcoal);
            CreateBlock("Presentation wall", new Vector3(0, 3.5f, 5.35f), new Vector3(15, 7, 0.25f), pearlWhite);
            CreateBlock("Left glass wall", new Vector3(-7.35f, 3.5f, 0), new Vector3(0.18f, 7, 11), glass);
            CreateBlock("Right wall", new Vector3(7.35f, 3.5f, 0), new Vector3(0.25f, 7, 11), pearlWhite);
            CreateBlock("Ceiling", new Vector3(0, 7.0f, 0), new Vector3(15, 0.22f, 11), charcoal);

            for (var i = -2; i <= 2; i++)
            {
                var strip = CreateBlock("Ceiling light", new Vector3(i * 2.2f, 6.82f, 0), new Vector3(0.07f, 0.04f, 7.8f), aionBlue);
                AddPointLight(strip.transform.position + Vector3.down * 0.2f, new Color(0.70f, 0.82f, 1f), 1.2f, 7f);
            }

            CreateBlock("Operations doorway", new Vector3(5.9f, 2.25f, 5.05f), new Vector3(2.1f, 4.5f, 0.12f), charcoal);
            CreateBlock("Left architectural rib", new Vector3(-6.55f, 3.7f, 3.7f), new Vector3(0.24f, 6.2f, 2.5f), pearlWhite);
            CreateBlock("Right architectural rib", new Vector3(6.55f, 3.7f, 3.7f), new Vector3(0.24f, 6.2f, 2.5f), pearlWhite);
        }

        private void BuildTable()
        {
            var table = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            table.name = "Executive oval table";
            table.transform.position = new Vector3(0, 1.42f, 0.15f);
            table.transform.localScale = new Vector3(5.25f, 0.16f, 2.55f);
            table.GetComponent<Renderer>().sharedMaterial = charcoal;

            var tableLight = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            tableLight.name = "Executive table light band";
            tableLight.transform.position = new Vector3(0, 1.58f, 0.15f);
            tableLight.transform.localScale = new Vector3(5.38f, 0.025f, 2.68f);
            tableLight.GetComponent<Renderer>().sharedMaterial = aionBlue;

            var tableSurface = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            tableSurface.name = "Executive table surface";
            tableSurface.transform.position = new Vector3(0, 1.62f, 0.15f);
            tableSurface.transform.localScale = new Vector3(5.12f, 0.035f, 2.42f);
            tableSurface.GetComponent<Renderer>().sharedMaterial = charcoal;

            var aionCore = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            aionCore.name = "AION table presence";
            aionCore.transform.position = new Vector3(0, 1.62f, 0.15f);
            aionCore.transform.localScale = new Vector3(0.72f, 0.025f, 0.72f);
            aionCore.GetComponent<Renderer>().sharedMaterial = aionBlue;

            for (var i = 0; i < 3; i++)
            {
                var ring = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
                ring.name = "AION light ring";
                ring.transform.position = new Vector3(0, 1.67f + i * 0.13f, 0.15f);
                ring.transform.localScale = new Vector3(0.60f - i * 0.12f, 0.018f, 0.60f - i * 0.12f);
                ring.GetComponent<Renderer>().sharedMaterial = aionBlue;
            }

            for (var i = 0; i < 5; i++)
            {
                CreateBlock(
                    "AION vertical light " + i,
                    new Vector3((i - 2) * 0.07f, 2.35f + i * 0.34f, 0.15f),
                    new Vector3(0.025f, 1.5f + i * 0.18f, 0.025f),
                    aionBlue);
            }
        }

        private void BuildPresentationWall()
        {
            var display = CreateBlock("Board presentation display", new Vector3(0, 3.85f, 5.1f), new Vector3(6.7f, 3.1f, 0.12f), charcoal);
            var bars = new[] { 0.9f, 1.45f, 1.1f, 1.9f, 1.55f, 2.25f, 1.75f };
            for (var i = 0; i < bars.Length; i++)
            {
                CreateBlock(
                    "Evidence bar " + i,
                    new Vector3(-2.4f + i * 0.8f, 2.75f + bars[i] * 0.42f, 4.96f),
                    new Vector3(0.38f, bars[i] * 0.82f, 0.08f),
                    i == 5 ? aionBlue : warmWhite);
            }
            AddLabel("LIVE BOARD EVIDENCE", new Vector3(-2.75f, 4.92f, 4.92f), 0.22f, Color.white);
        }

        private void BuildAgents()
        {
            AddAgent("Marketing", new Vector3(-4.4f, 0, 0.1f), new Color(0.72f, 0.53f, 0.28f), 75f);
            AddAgent("Sales", new Vector3(-3.0f, 0, 2.55f), new Color(0.12f, 0.35f, 0.60f), 145f);
            AddAgent("Finance", new Vector3(0, 0, 3.15f), new Color(0.16f, 0.42f, 0.32f), 180f);
            AddAgent("People", new Vector3(3.0f, 0, 2.55f), new Color(0.46f, 0.28f, 0.58f), 215f);
            AddAgent("AION", new Vector3(4.4f, 0, 0.1f), new Color(0.02f, 0.44f, 0.90f), 285f, false, "aion", true);
            AddAgent("Operations", new Vector3(5.9f, 0, 5.65f), new Color(0.52f, 0.25f, 0.16f), 220f, true);
        }

        private BoardroomAgentView AddAgent(string role, Vector3 position, Color suitColor, float yaw, bool waitingOutside = false, string memberId = "", bool isBoardMember = false)
        {
            var root = new GameObject(role + " agent");
            root.transform.position = position;
            root.transform.rotation = Quaternion.Euler(0, yaw, 0);
            var agent = root.AddComponent<BoardroomAgentView>();
            agent.Configure(role, suitColor, pearlWhite, charcoal, aionBlue, waitingOutside, memberId, isBoardMember);
            agents.Add(agent);
            if (!waitingOutside) BuildChair(position, yaw);
            return agent;
        }

        private void BuildChair(Vector3 position, float yaw)
        {
            var chair = new GameObject("Executive chair");
            chair.transform.position = position;
            chair.transform.rotation = Quaternion.Euler(0, yaw, 0);
            CreateChildBlock(chair.transform, "Seat", new Vector3(0, 0.72f, 0), new Vector3(0.9f, 0.18f, 0.85f), charcoal);
            CreateChildBlock(chair.transform, "Back", new Vector3(0, 1.55f, 0.36f), new Vector3(0.92f, 1.5f, 0.18f), charcoal);
        }

        private void BuildLightingAndCamera()
        {
            RenderSettings.ambientLight = new Color(0.31f, 0.33f, 0.38f);
            var sunObject = new GameObject("Morning sun");
            var sun = sunObject.AddComponent<Light>();
            sun.type = LightType.Directional;
            sun.color = new Color(1f, 0.83f, 0.67f);
            sun.intensity = 1.55f;
            sunObject.transform.rotation = Quaternion.Euler(38f, -42f, 0);

            cameraRig = new GameObject("Founder cinematic camera").transform;
            sceneCamera = cameraRig.gameObject.AddComponent<Camera>();
            sceneCamera.fieldOfView = 48f;
            sceneCamera.nearClipPlane = 0.08f;
            sceneCamera.clearFlags = CameraClearFlags.SolidColor;
            sceneCamera.backgroundColor = new Color(0.035f, 0.045f, 0.065f);
            cameraRig.gameObject.AddComponent<AudioListener>();

            var oldCamera = Camera.main;
            if (oldCamera != null && oldCamera != sceneCamera) oldCamera.gameObject.SetActive(false);
        }

        private void FocusOverview()
        {
            SetAllSpeaking(null);
            desiredCameraPosition = new Vector3(0, 2.55f, -7.9f);
            desiredLookTarget = new Vector3(0, 1.85f, 0.6f);
            meetingCaption = "Boardroom ready — choose an adviser or call Operations.";
        }

        private void FocusAgent(string role)
        {
            var agent = agents.Find(candidate => candidate.Role.Equals(role, StringComparison.OrdinalIgnoreCase));
            if (agent == null) return;
            SetAllSpeaking(agent);
            var forward = agent.transform.forward;
            desiredCameraPosition = agent.HeadPosition - forward * 2.25f + Vector3.up * 0.18f;
            desiredLookTarget = agent.HeadPosition;
            meetingCaption = role + " has the floor. AION supplies the governed dialogue; Unity performs the meeting.";
        }

        private void SetAllSpeaking(BoardroomAgentView active)
        {
            foreach (var agent in agents) agent.SetSpeaking(agent == active);
        }

        private void CallOperations()
        {
            if (operationsCalled) { FocusAgent("Operations"); return; }
            operationsCalled = true;
            var operations = agents.Find(candidate => candidate.Role == "Operations");
            if (operations == null) return;
            meetingCaption = "Operations requested — entering the Boardroom.";
            StartCoroutine(EnterOperations(operations));
        }

        private IEnumerator EnterOperations(BoardroomAgentView operations)
        {
            operations.gameObject.SetActive(true);
            var destination = new Vector3(4.45f, 0, -1.6f);
            BuildChair(destination, 300f);
            while (Vector3.Distance(operations.transform.position, destination) > 0.05f)
            {
                operations.transform.position = Vector3.MoveTowards(operations.transform.position, destination, Time.deltaTime * 1.5f);
                operations.transform.rotation = Quaternion.Slerp(operations.transform.rotation, Quaternion.Euler(0, 220f, 0), Time.deltaTime * 4f);
                operations.SetWalking(true);
                yield return null;
            }
            operations.SetWalking(false);
            operations.transform.rotation = Quaternion.Euler(0, 300f, 0);
            FocusAgent("Operations");
            meetingCaption = "Operations is seated and ready to report.";
        }

        private void HandleTessarisEvent(TessarisBoardroomEvent boardroomEvent)
        {
            switch (boardroomEvent.type)
            {
                case "focus_agent": FocusAgent(boardroomEvent.role); break;
                case "operations_agent_requested": CallOperations(); break;
                case "meeting_overview": FocusOverview(); break;
                case "caption": meetingCaption = boardroomEvent.text; break;
                case "board_members_snapshot": ApplyBoardMembers(boardroomEvent.members); break;
            }
        }

        private void ApplyBoardMembers(TessarisBoardroomMember[] members)
        {
            boardMembers.Clear();
            if (members != null)
            {
                foreach (var member in members)
                {
                    if (member == null || !member.connected || string.IsNullOrWhiteSpace(member.id)) continue;
                    boardMembers.Add(member);
                }
            }
            foreach (var previous in dynamicBoardMembers)
            {
                agents.Remove(previous);
                if (previous != null) Destroy(previous.gameObject);
            }
            dynamicBoardMembers.Clear();
            var externalMembers = boardMembers.FindAll(member => !member.id.Equals("aion", StringComparison.OrdinalIgnoreCase));
            for (var index = 0; index < externalMembers.Count; index++)
            {
                var member = externalMembers[index];
                var x = (index - (externalMembers.Count - 1) * 0.5f) * 1.55f;
                var color = Color.HSVToRGB((0.54f + index * 0.12f) % 1f, 0.58f, 0.92f);
                var agent = AddAgent(member.label, new Vector3(x, 0, 4.15f), color, 180f, false, member.id, true);
                agent.SetDisplayLabel(member.label);
                dynamicBoardMembers.Add(agent);
            }
            meetingCaption = boardMembers.Count > 0
                ? "Connected Board: " + string.Join(", ", boardMembers.ConvertAll(member => member.label)) + ". Select a member to open their Tessaris chat."
                : "AION is ready. Connect another model in Tessaris to add it to the Board.";
        }

        private void SelectAgent(BoardroomAgentView agent)
        {
            FocusAgent(agent.Role);
            if (agent.IsBoardMember)
            {
                bridge?.SendAction("open_board_member_chat", agent.MemberId, agent.Role, "AI Board member");
            }
            else
            {
                bridge?.SendAction("open_executive_chat", agent.Role.ToLowerInvariant(), agent.Role, "Department-specific AION agent");
            }
        }

        private void OnGUI()
        {
            titleStyle ??= new GUIStyle(GUI.skin.label) { fontSize = 22, fontStyle = FontStyle.Bold, normal = { textColor = Color.white } };
            captionStyle ??= new GUIStyle(GUI.skin.box) { fontSize = 17, alignment = TextAnchor.MiddleLeft, normal = { textColor = Color.white } };
            buttonStyle ??= new GUIStyle(GUI.skin.button) { fontSize = 14, fontStyle = FontStyle.Bold };

            GUI.Label(new Rect(28, 24, 540, 35), "TESSARIS · SPATIAL BOARDROOM MVP", titleStyle);
            GUI.Box(new Rect(24, Screen.height - 92, Screen.width - 48, 54), meetingCaption, captionStyle);

            var x = 28f;
            foreach (var member in boardMembers)
            {
                var width = Mathf.Clamp(82f + member.label.Length * 5f, 106f, 170f);
                if (GUI.Button(new Rect(x, 70, width, 36), member.label, buttonStyle))
                {
                    var selected = agents.Find(candidate => candidate.MemberId.Equals(member.id, StringComparison.OrdinalIgnoreCase));
                    if (selected != null) SelectAgent(selected);
                }
                x += width + 10f;
            }
            var roles = new[] { "Sales", "Finance", "Marketing", "People" };
            for (var i = 0; i < roles.Length; i++)
            {
                if (GUI.Button(new Rect(28 + i * 116, 116, 106, 34), roles[i], buttonStyle))
                {
                    var selected = agents.Find(candidate => candidate.Role == roles[i]);
                    if (selected != null) SelectAgent(selected);
                }
            }
            if (GUI.Button(new Rect(492, 116, 152, 34), operationsCalled ? "Focus Operations" : "Call Operations", buttonStyle)) CallOperations();
            if (GUI.Button(new Rect(654, 116, 106, 34), "Overview", buttonStyle)) FocusOverview();
        }

        private GameObject CreateBlock(string label, Vector3 position, Vector3 scale, Material material)
        {
            var block = GameObject.CreatePrimitive(PrimitiveType.Cube);
            block.name = label;
            block.transform.position = position;
            block.transform.localScale = scale;
            block.GetComponent<Renderer>().sharedMaterial = material;
            return block;
        }

        private static GameObject CreateChildBlock(Transform parent, string label, Vector3 localPosition, Vector3 localScale, Material material)
        {
            var block = GameObject.CreatePrimitive(PrimitiveType.Cube);
            block.name = label;
            block.transform.SetParent(parent, false);
            block.transform.localPosition = localPosition;
            block.transform.localScale = localScale;
            block.GetComponent<Renderer>().sharedMaterial = material;
            return block;
        }

        private void AddPointLight(Vector3 position, Color color, float intensity, float range)
        {
            var lightObject = new GameObject("Boardroom practical light");
            lightObject.transform.position = position;
            var light = lightObject.AddComponent<Light>();
            light.type = LightType.Point;
            light.color = color;
            light.intensity = intensity;
            light.range = range;
        }

        private static void AddLabel(string value, Vector3 position, float size, Color color)
        {
            var label = new GameObject(value);
            label.transform.position = position;
            label.transform.rotation = Quaternion.Euler(0, 180, 0);
            var mesh = label.AddComponent<TextMesh>();
            mesh.text = value;
            mesh.fontSize = 64;
            mesh.characterSize = size;
            mesh.color = color;
            mesh.anchor = TextAnchor.MiddleLeft;
        }
    }

    internal sealed class BoardroomAgentView : MonoBehaviour
    {
        public string Role { get; private set; }
        public string MemberId { get; private set; }
        public bool IsBoardMember { get; private set; }
        public Vector3 HeadPosition => transform.TransformPoint(new Vector3(0, 2.68f, 0));
        private Transform head;
        private Transform body;
        private Material baseSuit;
        private Material speakingSuit;
        private Vector3 bodyStart;
        private float phase;
        private bool speaking;
        private bool walking;

        public void Configure(string role, Color roleColor, Material shell, Material blackGlass, Material highlight, bool waitingOutside, string memberId, bool isBoardMember)
        {
            Role = role;
            MemberId = string.IsNullOrWhiteSpace(memberId) ? role.ToLowerInvariant() : memberId;
            IsBoardMember = isBoardMember;
            baseSuit = new Material(shell);
            speakingSuit = new Material(shell);
            if (speakingSuit.HasProperty("_EmissionColor"))
            {
                speakingSuit.EnableKeyword("_EMISSION");
                speakingSuit.SetColor("_EmissionColor", roleColor * 0.8f);
            }
            var roleLight = new Material(highlight) { color = roleColor };
            if (roleLight.HasProperty("_EmissionColor")) roleLight.SetColor("_EmissionColor", roleColor * 3.2f);

            body = CreatePart("Ceramic torso shell", PrimitiveType.Capsule, new Vector3(0, 1.65f, 0), new Vector3(0.62f, 0.72f, 0.42f), baseSuit).transform;
            CreatePart("Torso glass inset", PrimitiveType.Cube, new Vector3(0, 1.82f, 0.36f), new Vector3(0.32f, 0.38f, 0.05f), blackGlass);
            head = CreatePart("Robotic head shell", PrimitiveType.Sphere, new Vector3(0, 2.68f, -0.02f), new Vector3(0.54f, 0.64f, 0.54f), shell).transform;
            CreatePart("Black glass face", PrimitiveType.Sphere, new Vector3(0, 2.67f, 0.25f), new Vector3(0.42f, 0.42f, 0.12f), blackGlass);
            CreatePart("Left eye light", PrimitiveType.Sphere, new Vector3(-0.13f, 2.70f, 0.36f), new Vector3(0.045f, 0.032f, 0.025f), roleLight);
            CreatePart("Right eye light", PrimitiveType.Sphere, new Vector3(0.13f, 2.70f, 0.36f), new Vector3(0.045f, 0.032f, 0.025f), roleLight);
            CreatePart("Left shoulder", PrimitiveType.Sphere, new Vector3(-0.50f, 1.98f, 0), new Vector3(0.25f, 0.25f, 0.25f), blackGlass);
            CreatePart("Right shoulder", PrimitiveType.Sphere, new Vector3(0.50f, 1.98f, 0), new Vector3(0.25f, 0.25f, 0.25f), blackGlass);
            CreatePart("Left arm shell", PrimitiveType.Capsule, new Vector3(-0.48f, 1.55f, -0.08f), new Vector3(0.17f, 0.58f, 0.17f), baseSuit).transform.rotation = Quaternion.Euler(25, 0, -18);
            CreatePart("Right arm shell", PrimitiveType.Capsule, new Vector3(0.48f, 1.55f, -0.08f), new Vector3(0.17f, 0.58f, 0.17f), baseSuit).transform.rotation = Quaternion.Euler(25, 0, 18);
            CreatePart("Department status light", PrimitiveType.Cylinder, new Vector3(0, 0.08f, 0), new Vector3(0.42f, 0.025f, 0.42f), roleLight);
            bodyStart = body.localPosition;
            var hitTarget = gameObject.AddComponent<CapsuleCollider>();
            hitTarget.center = new Vector3(0, 1.55f, 0);
            hitTarget.height = 3.1f;
            hitTarget.radius = 0.68f;
            phase = UnityEngine.Random.Range(0f, 5f);
            gameObject.SetActive(!waitingOutside);
        }

        public void SetSpeaking(bool value) => speaking = value;
        public void SetWalking(bool value) => walking = value;

        public void SetDisplayLabel(string value)
        {
            var label = new GameObject("Board member label");
            label.transform.SetParent(transform, false);
            label.transform.localPosition = new Vector3(0, 3.45f, 0);
            label.transform.localRotation = Quaternion.Euler(0, 180, 0);
            var mesh = label.AddComponent<TextMesh>();
            mesh.text = value;
            mesh.fontSize = 54;
            mesh.characterSize = 0.08f;
            mesh.color = Color.white;
            mesh.anchor = TextAnchor.MiddleCenter;
        }

        private void Update()
        {
            if (body == null || head == null) return;
            var breathing = Mathf.Sin(Time.time * 1.5f + phase) * 0.012f;
            body.localPosition = bodyStart + Vector3.up * breathing;
            head.localRotation = Quaternion.Euler(
                speaking ? Mathf.Sin(Time.time * 2.2f) * 2f : 0,
                Mathf.Sin(Time.time * 0.45f + phase) * (speaking ? 5f : 2f),
                0);
            body.GetComponent<Renderer>().sharedMaterial = speaking ? speakingSuit : baseSuit;
            if (walking) body.localPosition += Vector3.up * Mathf.Abs(Mathf.Sin(Time.time * 7f)) * 0.035f;
        }

        private GameObject CreatePart(string label, PrimitiveType type, Vector3 localPosition, Vector3 localScale, Material material)
        {
            var part = GameObject.CreatePrimitive(type);
            part.name = label;
            part.transform.SetParent(transform, false);
            part.transform.localPosition = localPosition;
            part.transform.localScale = localScale;
            part.GetComponent<Renderer>().sharedMaterial = material;
            var collider = part.GetComponent<Collider>();
            if (collider != null) Destroy(collider);
            return part;
        }
    }

    [Serializable]
    public sealed class TessarisBoardroomEvent
    {
        public string id;
        public string type;
        public string role;
        public string text;
        public TessarisBoardroomMember[] members;
    }

    [Serializable]
    public sealed class TessarisBoardroomMember
    {
        public string id;
        public string label;
        public string role;
        public bool connected;
    }

    [Serializable]
    public sealed class TessarisBoardroomAction
    {
        public string type;
        public string member_id;
        public string label;
        public string role;
    }

    /// <summary>
    /// Optional read-only bridge. The native build accepts a loopback endpoint
    /// and an opaque, short-lived session token. No credentials or broad
    /// business records belong in the Unity process.
    /// </summary>
    internal sealed class TessarisSessionBridge : MonoBehaviour
    {
        public event Action<TessarisBoardroomEvent> EventReceived;
        private string endpoint;
        private string actionsEndpoint;
        private string token;
        private string lastEventId;

        private void Start()
        {
            foreach (var argument in Environment.GetCommandLineArgs())
            {
                if (argument.StartsWith("--tessaris-endpoint=")) endpoint = argument[20..];
                if (argument.StartsWith("--tessaris-actions=")) actionsEndpoint = argument[19..];
                if (argument.StartsWith("--tessaris-session=")) token = argument[19..];
            }

            if (!string.IsNullOrWhiteSpace(endpoint) && IsLoopback(endpoint) && !string.IsNullOrWhiteSpace(token))
            {
                StartCoroutine(Poll());
            }
        }

        public void SendAction(string type, string memberId, string label, string role)
        {
            if (string.IsNullOrWhiteSpace(actionsEndpoint) || !IsLoopback(actionsEndpoint) || string.IsNullOrWhiteSpace(token)) return;
            StartCoroutine(PostAction(new TessarisBoardroomAction
            {
                type = type,
                member_id = memberId,
                label = label,
                role = role,
            }));
        }

        private IEnumerator PostAction(TessarisBoardroomAction action)
        {
            var bytes = System.Text.Encoding.UTF8.GetBytes(JsonUtility.ToJson(action));
            using var request = new UnityWebRequest(actionsEndpoint, UnityWebRequest.kHttpVerbPOST)
            {
                uploadHandler = new UploadHandlerRaw(bytes),
                downloadHandler = new DownloadHandlerBuffer(),
                timeout = 4,
            };
            request.SetRequestHeader("Content-Type", "application/json");
            request.SetRequestHeader("Authorization", "Bearer " + token);
            yield return request.SendWebRequest();
        }

        private IEnumerator Poll()
        {
            while (enabled)
            {
                var separator = endpoint.Contains("?") ? "&" : "?";
                var url = endpoint + separator + "after=" + UnityWebRequest.EscapeURL(lastEventId ?? string.Empty);
                using var request = UnityWebRequest.Get(url);
                request.SetRequestHeader("Authorization", "Bearer " + token);
                request.timeout = 4;
                yield return request.SendWebRequest();
                if (request.result == UnityWebRequest.Result.Success && !string.IsNullOrWhiteSpace(request.downloadHandler.text))
                {
                    var nextEvent = JsonUtility.FromJson<TessarisBoardroomEvent>(request.downloadHandler.text);
                    if (nextEvent != null && nextEvent.id != lastEventId)
                    {
                        lastEventId = nextEvent.id;
                        EventReceived?.Invoke(nextEvent);
                    }
                }
                yield return new WaitForSecondsRealtime(0.75f);
            }
        }

        private static bool IsLoopback(string value)
        {
            return Uri.TryCreate(value, UriKind.Absolute, out var uri)
                && (uri.Host == "127.0.0.1" || uri.Host.Equals("localhost", StringComparison.OrdinalIgnoreCase));
        }
    }
}
