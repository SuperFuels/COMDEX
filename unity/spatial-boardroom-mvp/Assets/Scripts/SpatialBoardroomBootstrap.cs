using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Networking;
using UnityEngine.Rendering;

namespace Tessaris.SpatialBoardroom
{
    /// <summary>
    /// Native Boardroom runtime. The Tessaris bridge stays independent of the
    /// presentation layer, while the room uses redistributable PBR assets when
    /// available and retains a procedural fallback for recovery builds.
    /// </summary>
    public sealed class SpatialBoardroomBootstrap : MonoBehaviour
    {
        private readonly List<BoardroomAgentView> agents = new();
        private readonly List<BoardroomAgentView> executiveAgents = new();
        private readonly List<BoardroomAgentView> dynamicBoardMembers = new();
        private readonly List<TessarisBoardroomMember> boardMembers = new();
        private GameObject executiveTeamRoot;
        private GameObject boardTeamRoot;
        private bool showingBoardTeam;
        private Transform cameraRig;
        private Camera sceneCamera;
        private Vector3 desiredCameraPosition;
        private Vector3 desiredLookTarget;
        private string meetingCaption = "Boardroom ready — choose an adviser.";
        private Material pearlWhite;
        private Material charcoal;
        private Material warmWhite;
        private Material glass;
        private Material aionBlue;
        private Material brushedMetal;
        private Material darkMetal;
        private Material pearlMetalTable;
        private Material ivoryWallTextile;
        private Material architecturalWhite;
        private Material softStone;
        private Material iceGlass;
        private Material coastalSkyline;
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
            QualitySettings.antiAliasing = 4;
            QualitySettings.shadowDistance = 40f;
            CreateMaterials();
            BuildRoom();
            BuildTable();
            BuildAgents();
            ApplyBoardMembers(new[]
            {
                new TessarisBoardroomMember { id = "aion", label = "AION", role = "Pilot", connected = true },
            });
            ShowBoardTeam(false);
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

            if (Input.GetKeyDown(KeyCode.Alpha1)) FocusAgent(showingBoardTeam ? "AION" : "Marketing");
            if (Input.GetKeyDown(KeyCode.Alpha2)) FocusAgent(showingBoardTeam ? BoardRoleAt(1) : "Sales");
            if (Input.GetKeyDown(KeyCode.Alpha3)) FocusAgent(showingBoardTeam ? BoardRoleAt(2) : "Finance");
            if (Input.GetKeyDown(KeyCode.Alpha4)) FocusAgent(showingBoardTeam ? BoardRoleAt(3) : "Operations");
            if (Input.GetKeyDown(KeyCode.Alpha5)) FocusAgent(showingBoardTeam ? BoardRoleAt(4) : "Support");
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
            brushedMetal = MakeMaterial("Brushed aluminium", new Color(0.46f, 0.52f, 0.60f), 0.92f, 0.82f);
            darkMetal = MakeMaterial("Black titanium", new Color(0.018f, 0.024f, 0.036f), 0.96f, 0.76f);
            pearlMetalTable = MakeMaterial("Pearl metallic table", new Color(0.94f, 0.96f, 0.98f), 0.72f, 0.82f);
            ivoryWallTextile = MakeMaterial("Ivory acoustic textile", new Color(0.95f, 0.94f, 0.90f), 0.02f, 0.32f);
            architecturalWhite = MakeMaterial("Architectural white", new Color(0.91f, 0.94f, 0.97f), 0.10f, 0.78f);
            softStone = MakeMaterial("Soft stone", new Color(0.29f, 0.34f, 0.41f), 0.12f, 0.62f);
            iceGlass = MakeMaterial("Ice glass", new Color(0.43f, 0.60f, 0.72f), 0.48f, 0.94f);
            coastalSkyline = MakeMaterial("Coastal skyline", Color.white, 0f, 0.16f);
            ApplyPanoramaTexture(coastalSkyline, "Boardroom/Environment/Textures/T_CoastalSkyline_Panorama_v1");
            ApplyBaseTexture(pearlMetalTable, "Boardroom/Environment/Textures/T_Table_PearlMetal_BaseColor", new Vector2(2.2f, 1.2f));
            ApplyBaseTexture(ivoryWallTextile, "Boardroom/Environment/Textures/T_Wall_IvoryTextile_BaseColor", new Vector2(2.0f, 3.2f));
            if (ivoryWallTextile.HasProperty("_EmissionColor"))
            {
                ivoryWallTextile.EnableKeyword("_EMISSION");
                ivoryWallTextile.SetColor("_EmissionColor", new Color(0.26f, 0.27f, 0.30f));
            }
        }

        private static void ApplyBaseTexture(Material material, string resourcePath, Vector2 tiling)
        {
            var texture = Resources.Load<Texture2D>(resourcePath);
            if (texture == null || material == null) return;
            texture.wrapMode = TextureWrapMode.Repeat;
            if (material.HasProperty("_MainTex"))
            {
                material.SetTexture("_MainTex", texture);
                material.SetTextureScale("_MainTex", tiling);
            }
            if (material.HasProperty("_BaseMap"))
            {
                material.SetTexture("_BaseMap", texture);
                material.SetTextureScale("_BaseMap", tiling);
            }
        }

        private static void ApplyPanoramaTexture(Material material, string resourcePath)
        {
            var texture = Resources.Load<Texture2D>(resourcePath);
            if (texture == null || material == null) return;
            texture.wrapMode = TextureWrapMode.Clamp;
            texture.filterMode = FilterMode.Trilinear;
            if (material.HasProperty("_MainTex")) material.SetTexture("_MainTex", texture);
            if (material.HasProperty("_BaseMap")) material.SetTexture("_BaseMap", texture);
            if (material.HasProperty("_EmissionMap"))
            {
                material.EnableKeyword("_EMISSION");
                material.SetTexture("_EmissionMap", texture);
                material.SetColor("_EmissionColor", new Color(0.32f, 0.32f, 0.32f));
            }
        }

        private Material CreatePanoramaSliceMaterial(string label, float horizontalOffset, float horizontalScale, bool flipVertical = true)
        {
            var material = new Material(coastalSkyline) { name = label };
            // Unity's built-in cube uses opposite V orientation on its rear and
            // side faces, so the caller selects the correct orientation per wall.
            var scale = new Vector2(horizontalScale, flipVertical ? -1f : 1f);
            var offset = new Vector2(horizontalOffset, flipVertical ? 1f : 0f);
            if (material.HasProperty("_MainTex"))
            {
                material.SetTextureScale("_MainTex", scale);
                material.SetTextureOffset("_MainTex", offset);
            }
            if (material.HasProperty("_BaseMap"))
            {
                material.SetTextureScale("_BaseMap", scale);
                material.SetTextureOffset("_BaseMap", offset);
            }
            if (material.HasProperty("_EmissionMap"))
            {
                material.SetTextureScale("_EmissionMap", scale);
                material.SetTextureOffset("_EmissionMap", offset);
            }
            return material;
        }

        private static Material MakeMaterial(string label, Color color, float metallic, float smoothness, bool emissive = false)
        {
            var template = Resources.Load<Material>("TessarisStandard");
            var shader = template == null ? Shader.Find("Universal Render Pipeline/Lit") ?? Shader.Find("Standard") : null;
            if (template == null && shader == null) throw new InvalidOperationException("No supported Boardroom shader is available.");
            var material = template == null ? new Material(shader) : new Material(template);
            material.name = label;
            material.color = color;
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
            CreateBlock("Seamless pearl floor", new Vector3(0, -0.12f, 0), new Vector3(15, 0.24f, 11), architecturalWhite);
            CreateBlock("Presentation wall backing", new Vector3(0, 3.5f, 5.35f), new Vector3(15, 7, 0.18f), architecturalWhite);
            CreateBlock("Left glass wall", new Vector3(-7.35f, 3.5f, 0), new Vector3(0.16f, 7, 11), iceGlass);
            CreateBlock("Right wall backing", new Vector3(7.35f, 3.5f, 0), new Vector3(0.18f, 7, 11), architecturalWhite);
            CreateBlock("Floating white ceiling", new Vector3(0, 7.0f, 0), new Vector3(15, 0.18f, 11), architecturalWhite);

            BuildDetailedArchitecture();

            for (var i = -1; i <= 1; i++)
            {
                var strip = CreateBlock("Ceiling light", new Vector3(i * 3.9f, 6.82f, 0), new Vector3(2.85f, 0.035f, 6.6f), warmWhite);
                AddPointLight(strip.transform.position + Vector3.down * 0.30f, new Color(0.82f, 0.90f, 1f), 1.05f, 8f);
            }
        }

        private void BuildDetailedArchitecture()
        {
            // A single calm stone inset anchors the table without the repeated
            // metal floor plates that made the room feel like a warehouse.
            var floorInset = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            floorInset.name = "Executive floor inset";
            floorInset.transform.position = new Vector3(0, 0.012f, 0.10f);
            floorInset.transform.localScale = new Vector3(6.15f, 0.018f, 3.75f);
            floorInset.GetComponent<Renderer>().sharedMaterial = softStone;

            // The side and rear windows share one continuous panorama. The
            // narrower side panes receive the edge slices, while the full rear
            // wall is one uninterrupted central view with no artificial breaks.
            const float sideSlice = 0.159f;
            const float rearSlice = 1f - sideSlice * 2f;
            CreateBlock(
                "Coastal skyline panoramic rear window",
                new Vector3(0, 3.65f, 5.08f),
                new Vector3(12.02f, 4.75f, 0.075f),
                CreatePanoramaSliceMaterial("Coastal skyline uninterrupted rear view", sideSlice, rearSlice));
            CreateBlock("Panoramic window lower rail", new Vector3(0, 1.18f, 4.98f), new Vector3(12.02f, 0.035f, 0.05f), aionBlue);

            CreateBlock("Horizon canopy", new Vector3(0, 6.20f, 4.96f), new Vector3(12.8f, 0.09f, 0.18f), architecturalWhite);
            CreateBlock("Horizon light line", new Vector3(0, 6.08f, 4.84f), new Vector3(12.35f, 0.035f, 0.035f), aionBlue);
            CreateBlock("Floating rear plinth", new Vector3(0, 0.54f, 4.96f), new Vector3(12.8f, 0.12f, 0.16f), architecturalWhite);

            // Full-height side glazing carries the panorama around the room. The
            // panes deliberately fill most of each wall so they read as exterior
            // windows rather than framed display panels.
            CreateBlock(
                "Coastal skyline left side window",
                new Vector3(-7.18f, 3.55f, 1.45f),
                new Vector3(0.025f, 5.25f, 6.70f),
                CreatePanoramaSliceMaterial("Coastal skyline far-left pane", 0f, sideSlice, false));
            CreateBlock(
                "Coastal skyline right side window",
                new Vector3(7.18f, 3.55f, 1.45f),
                new Vector3(0.025f, 5.25f, 6.70f),
                CreatePanoramaSliceMaterial("Coastal skyline far-right pane", 1f - sideSlice, sideSlice, false));

            CreateBlock("Left window sill", new Vector3(-7.04f, 0.90f, 1.45f), new Vector3(0.12f, 0.08f, 6.82f), architecturalWhite);
            CreateBlock("Right window sill", new Vector3(7.04f, 0.90f, 1.45f), new Vector3(0.12f, 0.08f, 6.82f), architecturalWhite);
            CreateBlock("Left window head", new Vector3(-7.04f, 6.20f, 1.45f), new Vector3(0.12f, 0.08f, 6.82f), architecturalWhite);
            CreateBlock("Right window head", new Vector3(7.04f, 6.20f, 1.45f), new Vector3(0.12f, 0.08f, 6.82f), architecturalWhite);

            // A concealed flush door replaces the black industrial opening.
            CreateBlock("Concealed operations door", new Vector3(5.90f, 2.25f, 4.91f), new Vector3(1.68f, 4.30f, 0.055f), architecturalWhite);
            CreateBlock("Operations door reveal", new Vector3(4.99f, 2.25f, 4.84f), new Vector3(0.035f, 4.34f, 0.035f), aionBlue);
            CreateBlock("Operations door handle", new Vector3(5.30f, 2.20f, 4.80f), new Vector3(0.035f, 0.48f, 0.035f), brushedMetal);
        }

        private void BuildTable()
        {
            // A conventional executive table: human-height, visually thin and
            // supported by two quiet pedestals. The earlier stacked cylinders
            // read as a stage and hid seated advisers from the room camera.
            var lightInset = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            lightInset.name = "Executive table inset light";
            lightInset.transform.position = new Vector3(0, 0.775f, 0.15f);
            lightInset.transform.localScale = new Vector3(4.96f, 0.018f, 2.31f);
            lightInset.GetComponent<Renderer>().sharedMaterial = aionBlue;

            var surface = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            surface.name = "Executive oval table surface";
            surface.transform.position = new Vector3(0, 0.82f, 0.15f);
            surface.transform.localScale = new Vector3(4.88f, 0.055f, 2.23f);
            surface.GetComponent<Renderer>().sharedMaterial = pearlMetalTable;

            foreach (var x in new[] { -1.65f, 1.65f })
            {
                var pedestal = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
                pedestal.name = "Executive table pedestal";
                pedestal.transform.position = new Vector3(x, 0.37f, 0.15f);
                pedestal.transform.localScale = new Vector3(0.64f, 0.36f, 0.78f);
                pedestal.GetComponent<Renderer>().sharedMaterial = darkMetal;
            }

            var evidencePuck = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            evidencePuck.name = "AION evidence puck";
            evidencePuck.transform.position = new Vector3(0, 0.89f, 0.15f);
            evidencePuck.transform.localScale = new Vector3(0.38f, 0.018f, 0.38f);
            evidencePuck.GetComponent<Renderer>().sharedMaterial = aionBlue;
        }

        private void BuildPresentationWall()
        {
            var display = CreateBlock("Board presentation display", new Vector3(0, 3.85f, 4.91f), new Vector3(6.7f, 3.1f, 0.12f), charcoal);
            var bars = new[] { 0.9f, 1.45f, 1.1f, 1.9f, 1.55f, 2.25f, 1.75f };
            for (var i = 0; i < bars.Length; i++)
            {
                CreateBlock(
                    "Evidence bar " + i,
                    new Vector3(-2.4f + i * 0.8f, 2.75f + bars[i] * 0.42f, 4.82f),
                    new Vector3(0.38f, bars[i] * 0.82f, 0.08f),
                    i == 5 ? aionBlue : warmWhite);
            }
            AddLabel("LIVE BOARD EVIDENCE", new Vector3(0f, 5.62f, 4.76f), 0.045f, Color.white);
        }

        private void BuildAgents()
        {
            executiveTeamRoot = new GameObject("Executive team");
            executiveAgents.Add(AddAgent("Marketing", new Vector3(-3.00f, 0, 0.00f), new Color(0.72f, 0.53f, 0.28f), 88f, executiveTeamRoot.transform));
            executiveAgents.Add(AddAgent("Sales", new Vector3(-2.80f, 0, 1.65f), new Color(0.12f, 0.35f, 0.60f), 118f, executiveTeamRoot.transform));
            executiveAgents.Add(AddAgent("Finance", new Vector3(-0.95f, 0, 2.05f), new Color(0.16f, 0.42f, 0.32f), 153f, executiveTeamRoot.transform));
            executiveAgents.Add(AddAgent("People", new Vector3(0.95f, 0, 2.05f), new Color(0.46f, 0.28f, 0.58f), 207f, executiveTeamRoot.transform));
            executiveAgents.Add(AddAgent("Support", new Vector3(3.00f, 0, 0.00f), new Color(0.35f, 0.34f, 0.68f), 272f, executiveTeamRoot.transform));
            executiveAgents.Add(AddAgent("Operations", new Vector3(2.80f, 0, 1.65f), new Color(0.52f, 0.25f, 0.16f), 242f, executiveTeamRoot.transform));
        }

        private BoardroomAgentView AddAgent(string role, Vector3 position, Color suitColor, float yaw, Transform groupRoot = null, bool waitingOutside = false, string memberId = "", bool isBoardMember = false)
        {
            var root = new GameObject(role + " agent");
            if (groupRoot != null) root.transform.SetParent(groupRoot, true);
            root.transform.position = position;
            root.transform.rotation = Quaternion.Euler(0, yaw, 0);
            var agent = root.AddComponent<BoardroomAgentView>();
            agent.Configure(role, suitColor, pearlWhite, charcoal, aionBlue, waitingOutside, memberId, isBoardMember);
            agents.Add(agent);
            if (!waitingOutside)
            {
                var chairOffset = -(Quaternion.Euler(0, yaw, 0) * Vector3.forward) * 0.34f;
                BuildChair(position + chairOffset, yaw, groupRoot);
                agent.SeatAt(chairOffset);
            }
            return agent;
        }

        private void BuildChair(Vector3 position, float yaw, Transform groupRoot = null)
        {
            var chair = new GameObject("Executive chair");
            if (groupRoot != null) chair.transform.SetParent(groupRoot, true);
            chair.transform.position = position;
            chair.transform.rotation = Quaternion.Euler(0, yaw, 0);
            var imported = PlaceModel("Boardroom/Furniture/ExecutiveChair", "Executive chair shell",
                position + Vector3.up * 0.95f, new Vector3(0, yaw + 180f, 0), 1.55f);
            if (imported != null) imported.transform.SetParent(chair.transform, true);
            if (imported == null)
            {
                CreateChildBlock(chair.transform, "Seat", new Vector3(0, 0.72f, 0), new Vector3(0.9f, 0.18f, 0.85f), charcoal);
                CreateChildBlock(chair.transform, "Back", new Vector3(0, 1.55f, 0.36f), new Vector3(0.92f, 1.5f, 0.18f), charcoal);
            }
        }

        private void BuildLightingAndCamera()
        {
            RenderSettings.ambientMode = AmbientMode.Trilight;
            RenderSettings.ambientSkyColor = new Color(0.78f, 0.84f, 0.92f);
            RenderSettings.ambientEquatorColor = new Color(0.58f, 0.65f, 0.74f);
            RenderSettings.ambientGroundColor = new Color(0.30f, 0.36f, 0.44f);
            RenderSettings.fog = false;
            var sunObject = new GameObject("Soft architectural daylight");
            var sun = sunObject.AddComponent<Light>();
            sun.type = LightType.Directional;
            sun.color = new Color(0.91f, 0.95f, 1f);
            sun.intensity = 1.08f;
            sun.shadows = LightShadows.Soft;
            sun.shadowStrength = 0.58f;
            sunObject.transform.rotation = Quaternion.Euler(44f, -28f, 0);

            AddSpotLight(new Vector3(-4.8f, 6.35f, -1.8f), new Vector3(-2.4f, 1.2f, 0.8f), new Color(0.78f, 0.88f, 1f), 2.15f, 62f);
            AddSpotLight(new Vector3(4.8f, 6.35f, -1.8f), new Vector3(2.4f, 1.2f, 0.8f), new Color(0.82f, 0.90f, 1f), 2.15f, 62f);
            AddSpotLight(new Vector3(0, 6.55f, 2.8f), new Vector3(0, 1.5f, 0.4f), new Color(0.70f, 0.86f, 1f), 2.4f, 68f);

            var reflectionObject = new GameObject("Boardroom reflection probe");
            reflectionObject.transform.position = new Vector3(0, 2.8f, 0.2f);
            var reflection = reflectionObject.AddComponent<ReflectionProbe>();
            reflection.mode = ReflectionProbeMode.Realtime;
            reflection.refreshMode = ReflectionProbeRefreshMode.OnAwake;
            reflection.timeSlicingMode = ReflectionProbeTimeSlicingMode.AllFacesAtOnce;
            reflection.size = new Vector3(14f, 7f, 10f);
            reflection.intensity = 1.05f;

            cameraRig = new GameObject("Founder cinematic camera").transform;
            sceneCamera = cameraRig.gameObject.AddComponent<Camera>();
            sceneCamera.fieldOfView = 48f;
            sceneCamera.nearClipPlane = 0.08f;
            sceneCamera.allowHDR = true;
            sceneCamera.allowMSAA = true;
            sceneCamera.renderingPath = RenderingPath.Forward;
            sceneCamera.clearFlags = CameraClearFlags.SolidColor;
            sceneCamera.backgroundColor = new Color(0.89f, 0.93f, 0.97f);
            cameraRig.gameObject.AddComponent<AudioListener>();

            var oldCamera = Camera.main;
            if (oldCamera != null && oldCamera != sceneCamera) oldCamera.gameObject.SetActive(false);
        }

        private void FocusOverview()
        {
            SetAllSpeaking(null);
            // Start nearer the meeting table so the room reads as an active
            // board meeting rather than a distant architectural overview.
            desiredCameraPosition = new Vector3(0, 2.24f, -3.76f);
            desiredLookTarget = new Vector3(0, 1.58f, 0.55f);
            meetingCaption = "Boardroom ready — choose an adviser.";
        }

        private void FocusAgent(string role)
        {
            if (string.IsNullOrWhiteSpace(role)) return;
            var activeAgents = showingBoardTeam ? dynamicBoardMembers : executiveAgents;
            var agent = activeAgents.Find(candidate => candidate.Role.Equals(role, StringComparison.OrdinalIgnoreCase));
            if (agent == null) return;
            SetAllSpeaking(agent);
            var forward = agent.transform.forward;
            // Move to the adviser-facing side. Using -forward placed the camera
            // behind the selected robot and framed the back of its head.
            desiredCameraPosition = agent.HeadPosition + forward * 1.80f + Vector3.up * 0.10f;
            desiredLookTarget = agent.HeadPosition;
            meetingCaption = role + " has the floor. AION supplies the governed dialogue; Unity performs the meeting.";
        }

        private void SetAllSpeaking(BoardroomAgentView active)
        {
            foreach (var agent in agents) agent.SetSpeaking(agent == active);
        }

        private void CallOperations()
        {
            if (showingBoardTeam) ShowExecutiveTeam();
            FocusAgent("Operations");
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
                case "team_mode":
                    if (string.Equals(boardroomEvent.mode, "executive", StringComparison.OrdinalIgnoreCase)) ShowExecutiveTeam();
                    else ShowBoardTeam();
                    break;
            }
        }

        private void ApplyBoardMembers(TessarisBoardroomMember[] members)
        {
            boardMembers.Clear();
            boardMembers.Add(new TessarisBoardroomMember { id = "aion", label = "AION", role = "Pilot", connected = true });
            if (members != null)
            {
                foreach (var member in members)
                {
                    if (member == null || !member.connected || string.IsNullOrWhiteSpace(member.id)) continue;
                    if (boardMembers.Exists(existing => existing.id.Equals(member.id, StringComparison.OrdinalIgnoreCase))) continue;
                    boardMembers.Add(member);
                }
            }
            foreach (var previous in dynamicBoardMembers)
            {
                agents.Remove(previous);
                if (previous != null) Destroy(previous.gameObject);
            }
            dynamicBoardMembers.Clear();
            if (boardTeamRoot != null) Destroy(boardTeamRoot);
            boardTeamRoot = new GameObject("Connected AI Board");

            var positions = new[]
            {
                new Vector3(-3.00f, 0, 0.00f),
                new Vector3(-2.80f, 0, 1.65f),
                new Vector3(-0.95f, 0, 2.05f),
                new Vector3(0.95f, 0, 2.05f),
                new Vector3(2.80f, 0, 1.65f),
                new Vector3(3.00f, 0, 0.00f),
            };
            var yaws = new[] { 88f, 118f, 153f, 207f, 242f, 272f };
            var colours = new[]
            {
                new Color(0.02f, 0.44f, 0.90f),
                new Color(0.18f, 0.58f, 0.95f),
                new Color(0.12f, 0.72f, 0.78f),
                new Color(0.35f, 0.55f, 0.96f),
                new Color(0.45f, 0.38f, 0.88f),
                new Color(0.10f, 0.66f, 0.92f),
            };
            var seatIndexes = SelectSeatIndexes(Mathf.Min(boardMembers.Count, positions.Length));
            for (var i = 0; i < seatIndexes.Length; i++)
            {
                var member = boardMembers[i];
                var seat = seatIndexes[i];
                var label = string.IsNullOrWhiteSpace(member.label) ? member.id : member.label;
                dynamicBoardMembers.Add(AddAgent(label, positions[seat], colours[i % colours.Length], yaws[seat],
                    boardTeamRoot.transform, false, member.id, true));
            }
            boardTeamRoot.SetActive(showingBoardTeam);
            if (showingBoardTeam) SetBoardCaption();
        }

        private static int[] SelectSeatIndexes(int count)
        {
            return count switch
            {
                1 => new[] { 2 },
                2 => new[] { 1, 4 },
                3 => new[] { 0, 2, 5 },
                4 => new[] { 0, 2, 3, 5 },
                5 => new[] { 0, 1, 2, 4, 5 },
                _ => new[] { 0, 1, 2, 3, 4, 5 },
            };
        }

        private string BoardRoleAt(int index)
        {
            return index >= 0 && index < dynamicBoardMembers.Count ? dynamicBoardMembers[index].Role : string.Empty;
        }

        private void ShowBoardTeam(bool resetCamera = true)
        {
            showingBoardTeam = true;
            if (executiveTeamRoot != null) executiveTeamRoot.SetActive(false);
            if (boardTeamRoot != null) boardTeamRoot.SetActive(true);
            if (resetCamera) FocusOverview();
            SetBoardCaption();
        }

        private void ShowExecutiveTeam(bool resetCamera = true)
        {
            showingBoardTeam = false;
            if (boardTeamRoot != null) boardTeamRoot.SetActive(false);
            if (executiveTeamRoot != null) executiveTeamRoot.SetActive(true);
            if (resetCamera) FocusOverview();
            meetingCaption = "Executive Team: Marketing, Sales, Finance, Operations, Support and People.";
        }

        private void SetBoardCaption()
        {
            meetingCaption = boardMembers.Count > 0
                ? "Connected Board intelligence: " + string.Join(", ", boardMembers.ConvertAll(member => member.label)) + ". Select a member to open their Tessaris chat."
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

            GUI.Label(new Rect(28, 24, 540, 35), "TESSARIS · SPATIAL BOARDROOM", titleStyle);

            GUI.Label(new Rect(Screen.width - 292, 24, 264, 28),
                showingBoardTeam ? "BOARD · CONNECTED AI" : "EXECUTIVE TEAM · DEPARTMENTS", captionStyle);

            if (showingBoardTeam)
            {
                var x = 28f;
                foreach (var member in boardMembers)
                {
                    var label = string.IsNullOrWhiteSpace(member.label) ? member.id : member.label;
                    var width = Mathf.Clamp(82f + label.Length * 5f, 106f, 190f);
                    if (GUI.Button(new Rect(x, 78, width, 36), label, buttonStyle))
                    {
                        var selected = dynamicBoardMembers.Find(candidate => candidate.MemberId.Equals(member.id, StringComparison.OrdinalIgnoreCase));
                        if (selected != null) SelectAgent(selected);
                    }
                    x += width + 10f;
                }
                if (GUI.Button(new Rect(28, 122, 106, 34), "Overview", buttonStyle)) FocusOverview();
                return;
            }

            var roles = new[] { "Marketing", "Sales", "Finance", "Operations", "Support", "People" };
            for (var i = 0; i < roles.Length; i++)
            {
                if (GUI.Button(new Rect(28 + i * 116, 78, 106, 34), roles[i], buttonStyle))
                {
                    var selected = executiveAgents.Find(candidate => candidate.Role == roles[i]);
                    if (selected != null) SelectAgent(selected);
                }
            }
            if (GUI.Button(new Rect(724, 78, 106, 34), "Overview", buttonStyle)) FocusOverview();
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
            light.shadows = LightShadows.Soft;
        }

        private void AddSpotLight(Vector3 position, Vector3 target, Color color, float intensity, float angle)
        {
            var lightObject = new GameObject("Boardroom cinematic light");
            lightObject.transform.position = position;
            lightObject.transform.rotation = Quaternion.LookRotation((target - position).normalized, Vector3.up);
            var light = lightObject.AddComponent<Light>();
            light.type = LightType.Spot;
            light.color = color;
            light.intensity = intensity;
            light.range = 18f;
            light.spotAngle = angle;
            light.shadows = LightShadows.Soft;
            light.shadowStrength = 0.68f;
        }

        private static GameObject PlaceModel(string resourcePath, string label, Vector3 center, Vector3 euler, float targetLargestDimension)
        {
            var prefab = Resources.Load<GameObject>(resourcePath);
            if (prefab == null) return null;

            var instance = Instantiate(prefab);
            instance.name = label;
            instance.transform.position = Vector3.zero;
            instance.transform.rotation = Quaternion.Euler(euler);
            instance.transform.localScale = Vector3.one;
            var bounds = CalculateBounds(instance);
            var largest = Mathf.Max(bounds.size.x, bounds.size.y, bounds.size.z);
            if (largest > 0.0001f)
            {
                instance.transform.localScale = Vector3.one * (targetLargestDimension / largest);
            }
            bounds = CalculateBounds(instance);
            instance.transform.position += center - bounds.center;
            return instance;
        }

        private static Bounds CalculateBounds(GameObject root)
        {
            var renderers = root.GetComponentsInChildren<Renderer>(true);
            if (renderers.Length == 0) return new Bounds(root.transform.position, Vector3.one);
            var bounds = renderers[0].bounds;
            for (var i = 1; i < renderers.Length; i++) bounds.Encapsulate(renderers[i].bounds);
            return bounds;
        }

        private static void AddLabel(string value, Vector3 position, float size, Color color)
        {
            var label = new GameObject(value);
            label.transform.position = position;
            label.transform.rotation = Quaternion.identity;
            var mesh = label.AddComponent<TextMesh>();
            mesh.text = value;
            mesh.fontSize = 64;
            mesh.characterSize = size;
            mesh.color = color;
            mesh.anchor = TextAnchor.MiddleCenter;
        }
    }

    internal sealed class BoardroomAgentView : MonoBehaviour
    {
        public string Role { get; private set; }
        public string MemberId { get; private set; }
        public bool IsBoardMember { get; private set; }
        public Vector3 HeadPosition => head == null ? transform.TransformPoint(new Vector3(0, 2.0f, 0)) : head.position;
        private Transform head;
        private Transform body;
        private Transform identityCore;
        private Material baseSuit;
        private Material speakingSuit;
        private readonly List<Renderer> shellRenderers = new();
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

            if (!BuildImportedRobot(roleLight, blackGlass))
            {
                BuildProceduralFallback(shell, blackGlass, roleLight);
            }
            CreatePart("Department status light", PrimitiveType.Cylinder, new Vector3(0, 0.08f, 0), new Vector3(0.42f, 0.025f, 0.42f), roleLight);
            bodyStart = body.localPosition;
            var hitTarget = gameObject.AddComponent<CapsuleCollider>();
            hitTarget.center = new Vector3(0, 1.08f, 0);
            hitTarget.height = 2.2f;
            hitTarget.radius = 0.54f;
            phase = UnityEngine.Random.Range(0f, 5f);
            gameObject.SetActive(!waitingOutside);
        }

        private bool BuildImportedRobot(Material roleLight, Material blackGlass)
        {
            const string robotResource = "Boardroom/Robots/AstraLumen/AstraLumen";
            var prefab = Resources.Load<GameObject>(robotResource);
            if (prefab == null) return false;

            var visual = Instantiate(prefab, transform, false);
            visual.name = "Detailed articulated robot";
            visual.transform.localPosition = Vector3.zero;
            // The agent root already faces the centre of the boardroom. The imported
            // robot's additional half-turn made every adviser face away from the table.
            visual.transform.localRotation = Quaternion.identity;
            visual.transform.localScale = Vector3.one;
            var renderers = visual.GetComponentsInChildren<Renderer>(true);
            if (renderers.Length == 0)
            {
                Destroy(visual);
                return false;
            }

            var bounds = renderers[0].bounds;
            for (var i = 1; i < renderers.Length; i++) bounds.Encapsulate(renderers[i].bounds);
            // Executive-scale humanoids should feel human-sized beside the table,
            // rather than dominating the room like the previous mascot robot.
            var scale = 1.82f / Mathf.Max(0.01f, bounds.size.y);
            visual.transform.localScale = Vector3.one * scale;
            bounds = renderers[0].bounds;
            for (var i = 1; i < renderers.Length; i++) bounds.Encapsulate(renderers[i].bounds);
            visual.transform.position += new Vector3(
                transform.position.x - bounds.center.x,
                transform.position.y - bounds.min.y,
                transform.position.z - bounds.center.z);

            var albedo = Resources.Load<Texture2D>("Boardroom/Robots/AstraLumen/Material_001_Tessaris");
            foreach (var renderer in renderers)
            {
                var sourceMaterials = renderer.sharedMaterials;
                var replacements = new Material[sourceMaterials.Length];
                for (var index = 0; index < replacements.Length; index++)
                {
                    var source = sourceMaterials[index];
                    var tessarisMaterial = source == null ? new Material(baseSuit) : new Material(source);
                    tessarisMaterial.name = "Tessaris Astra pearl shell";
                    if (albedo != null)
                    {
                        if (tessarisMaterial.HasProperty("_MainTex")) tessarisMaterial.SetTexture("_MainTex", albedo);
                        if (tessarisMaterial.HasProperty("_BaseMap")) tessarisMaterial.SetTexture("_BaseMap", albedo);
                    }
                    if (tessarisMaterial.HasProperty("_Color")) tessarisMaterial.SetColor("_Color", Color.white);
                    if (tessarisMaterial.HasProperty("_BaseColor")) tessarisMaterial.SetColor("_BaseColor", Color.white);
                    if (tessarisMaterial.HasProperty("_Metallic")) tessarisMaterial.SetFloat("_Metallic", 0.32f);
                    if (tessarisMaterial.HasProperty("_Glossiness")) tessarisMaterial.SetFloat("_Glossiness", 0.68f);
                    if (tessarisMaterial.HasProperty("_Smoothness")) tessarisMaterial.SetFloat("_Smoothness", 0.68f);
                    replacements[index] = tessarisMaterial;
                }
                renderer.sharedMaterials = replacements;
            }

            body = visual.transform;
            head = FindNamedTransform(visual.transform, "head") ?? visual.transform;
            identityCore = CreatePart("Executive identity core", PrimitiveType.Cylinder, new Vector3(0, 1.23f, 0.22f), new Vector3(0.055f, 0.014f, 0.055f), roleLight).transform;
            identityCore.transform.rotation = Quaternion.Euler(90f, 0, 0);
            return true;
        }

        public void SeatAt(Vector3 chairOffset)
        {
            transform.position += chairOffset;
            if (body != null)
            {
                // Pose the articulated rig into the chair instead of sinking the
                // whole standing model through it. Thighs move forward, calves
                // return toward the floor, and the torso only settles slightly.
                PoseBone("CC_Base_L_Thigh", body.right, -76f);
                PoseBone("CC_Base_R_Thigh", body.right, -76f);
                PoseBone("CC_Base_L_Calf", body.right, 82f);
                PoseBone("CC_Base_R_Calf", body.right, 82f);
                PoseBone("CC_Base_L_Upperarm", body.forward, -12f);
                PoseBone("CC_Base_R_Upperarm", body.forward, 12f);
                body.localPosition += Vector3.down * 0.07f;
                bodyStart = body.localPosition;
            }
            if (identityCore != null) identityCore.localPosition += Vector3.down * 0.07f;
        }

        private void PoseBone(string boneName, Vector3 worldAxis, float degrees)
        {
            var bone = FindExactTransform(body, boneName);
            if (bone != null) bone.rotation = Quaternion.AngleAxis(degrees, worldAxis.normalized) * bone.rotation;
        }

        private static Transform FindExactTransform(Transform root, string name)
        {
            if (root == null) return null;
            if (root.name.Equals(name, StringComparison.OrdinalIgnoreCase)) return root;
            foreach (Transform child in root)
            {
                var match = FindExactTransform(child, name);
                if (match != null) return match;
            }
            return null;
        }

        private void BuildProceduralFallback(Material shell, Material blackGlass, Material roleLight)
        {
            body = CreatePart("Ceramic torso shell", PrimitiveType.Capsule, new Vector3(0, 1.65f, 0), new Vector3(0.62f, 0.72f, 0.42f), baseSuit).transform;
            shellRenderers.Add(body.GetComponent<Renderer>());
            CreatePart("Torso glass inset", PrimitiveType.Cube, new Vector3(0, 1.82f, 0.36f), new Vector3(0.32f, 0.38f, 0.05f), blackGlass);
            head = CreatePart("Robotic head shell", PrimitiveType.Sphere, new Vector3(0, 2.68f, -0.02f), new Vector3(0.54f, 0.64f, 0.54f), shell).transform;
            CreatePart("Black glass face", PrimitiveType.Sphere, new Vector3(0, 2.67f, 0.25f), new Vector3(0.42f, 0.42f, 0.12f), blackGlass);
            CreatePart("Left eye light", PrimitiveType.Sphere, new Vector3(-0.13f, 2.70f, 0.36f), new Vector3(0.045f, 0.032f, 0.025f), roleLight);
            CreatePart("Right eye light", PrimitiveType.Sphere, new Vector3(0.13f, 2.70f, 0.36f), new Vector3(0.045f, 0.032f, 0.025f), roleLight);
            CreatePart("Left shoulder", PrimitiveType.Sphere, new Vector3(-0.50f, 1.98f, 0), new Vector3(0.25f, 0.25f, 0.25f), blackGlass);
            CreatePart("Right shoulder", PrimitiveType.Sphere, new Vector3(0.50f, 1.98f, 0), new Vector3(0.25f, 0.25f, 0.25f), blackGlass);
            CreatePart("Left arm shell", PrimitiveType.Capsule, new Vector3(-0.48f, 1.55f, -0.08f), new Vector3(0.17f, 0.58f, 0.17f), baseSuit).transform.rotation = Quaternion.Euler(25, 0, -18);
            CreatePart("Right arm shell", PrimitiveType.Capsule, new Vector3(0.48f, 1.55f, -0.08f), new Vector3(0.17f, 0.58f, 0.17f), baseSuit).transform.rotation = Quaternion.Euler(25, 0, 18);
        }

        private static Transform FindNamedTransform(Transform root, string fragment)
        {
            if (root.name.IndexOf(fragment, StringComparison.OrdinalIgnoreCase) >= 0) return root;
            foreach (Transform child in root)
            {
                var match = FindNamedTransform(child, fragment);
                if (match != null) return match;
            }
            return null;
        }

        public void SetSpeaking(bool value) => speaking = value;
        public void SetWalking(bool value) => walking = value;

        public void SetDisplayLabel(string value)
        {
            var label = new GameObject("Board member label");
            label.transform.SetParent(transform, false);
            label.transform.localPosition = new Vector3(0, 2.55f, 0);
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
            foreach (var renderer in shellRenderers)
            {
                if (renderer != null) renderer.sharedMaterial = speaking ? speakingSuit : baseSuit;
            }
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
        public string mode;
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
        private string initialMode;
        private string lastEventId;

        private void Start()
        {
            foreach (var argument in Environment.GetCommandLineArgs())
            {
                if (argument.StartsWith("--tessaris-endpoint=")) endpoint = argument[20..];
                if (argument.StartsWith("--tessaris-actions=")) actionsEndpoint = argument[19..];
                if (argument.StartsWith("--tessaris-session=")) token = argument[19..];
            }

            // The native player receives short-lived bridge details through
            // command-line arguments. The embedded WebGL player receives the
            // same values in its loopback page URL because browsers do not
            // expose a meaningful process command line to Unity content.
            if (string.IsNullOrWhiteSpace(endpoint) && !string.IsNullOrWhiteSpace(Application.absoluteURL))
            {
                ApplyWebQuery(Application.absoluteURL);
            }

            if (!string.IsNullOrWhiteSpace(initialMode))
            {
                EventReceived?.Invoke(new TessarisBoardroomEvent { type = "team_mode", mode = initialMode });
            }

            if (!string.IsNullOrWhiteSpace(endpoint) && IsLoopback(endpoint) && !string.IsNullOrWhiteSpace(token))
            {
                StartCoroutine(Poll());
            }
        }

        private void ApplyWebQuery(string absoluteUrl)
        {
            if (!Uri.TryCreate(absoluteUrl, UriKind.Absolute, out var uri)) return;
            var query = uri.Query.TrimStart('?').Split('&', StringSplitOptions.RemoveEmptyEntries);
            foreach (var pair in query)
            {
                var parts = pair.Split('=', 2);
                var key = Uri.UnescapeDataString(parts[0]);
                var value = parts.Length > 1 ? Uri.UnescapeDataString(parts[1]) : string.Empty;
                if (key == "tessaris-endpoint") endpoint = value;
                if (key == "tessaris-actions") actionsEndpoint = value;
                if (key == "tessaris-session") token = value;
                if (key == "tessaris-mode") initialMode = value;
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
