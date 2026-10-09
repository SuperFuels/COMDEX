using System.IO;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace Tessaris.SpatialBoardroom.Editor
{
    [InitializeOnLoad]
    internal static class SpatialBoardroomProjectSetup
    {
        private const string ScenePath = "Assets/Scenes/SpatialBoardroom.unity";

        static SpatialBoardroomProjectSetup()
        {
            EditorApplication.delayCall += EnsureScene;
        }

        [MenuItem("Tessaris/Prepare Spatial Boardroom MVP")]
        private static void EnsureScene()
        {
            if (File.Exists(ScenePath)) return;
            Directory.CreateDirectory("Assets/Scenes");
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            new GameObject("Spatial Boardroom Bootstrap").AddComponent<SpatialBoardroomBootstrap>();
            EditorSceneManager.SaveScene(scene, ScenePath);
            EditorBuildSettings.scenes = new[] { new EditorBuildSettingsScene(ScenePath, true) };
            AssetDatabase.SaveAssets();
            Debug.Log("Tessaris Spatial Boardroom MVP scene created.");
        }

        // Public entry points are used by the SD-card build scripts.
        public static void PrepareForBatch()
        {
            EnsureScene();
        }

        public static void BuildForBatch()
        {
            BuildMac();
        }

        public static void BuildWebForBatch()
        {
            BuildWeb();
        }

        [MenuItem("Tessaris/Build Spatial Boardroom/macOS Apple Silicon")]
        private static void BuildMac()
        {
            EnsureScene();
            PlayerSettings.companyName = "Tessaris";
            PlayerSettings.productName = "Tessaris Spatial Boardroom";
            PlayerSettings.SetApplicationIdentifier(BuildTargetGroup.Standalone, "ai.tessaris.spatial-boardroom");
            EnsureRuntimeMaterial();
            Directory.CreateDirectory("Builds/macOS");
            var report = BuildPipeline.BuildPlayer(
                new[] { ScenePath },
                "Builds/macOS/Tessaris Spatial Boardroom.app",
                BuildTarget.StandaloneOSX,
                BuildOptions.None);
            Debug.Log(report.summary.result == BuildResult.Succeeded
                ? "Spatial Boardroom build completed."
                : "Spatial Boardroom build failed: " + report.summary.result);
        }

        [MenuItem("Tessaris/Build Spatial Boardroom/Embedded WebGL")]
        private static void BuildWeb()
        {
            EnsureScene();
            PlayerSettings.companyName = "Tessaris";
            PlayerSettings.productName = "Tessaris Spatial Boardroom";
            PlayerSettings.SetApplicationIdentifier(BuildTargetGroup.WebGL, "ai.tessaris.spatial-boardroom.web");
            PlayerSettings.WebGL.compressionFormat = WebGLCompressionFormat.Disabled;
            PlayerSettings.WebGL.dataCaching = false;
            PlayerSettings.WebGL.decompressionFallback = true;
            EnsureRuntimeMaterial();
            Directory.CreateDirectory("Builds/WebGL");
            var report = BuildPipeline.BuildPlayer(
                new[] { ScenePath },
                "Builds/WebGL",
                BuildTarget.WebGL,
                BuildOptions.None);
            if (report.summary.result == BuildResult.Succeeded) PolishEmbeddedWebPlayer();
            Debug.Log(report.summary.result == BuildResult.Succeeded
                ? "Embedded Spatial Boardroom build completed."
                : "Embedded Spatial Boardroom build failed: " + report.summary.result);
        }

        private static void PolishEmbeddedWebPlayer()
        {
            const string stylesheetPath = "Builds/WebGL/TemplateData/style.css";
            if (!File.Exists(stylesheetPath)) return;
            var stylesheet = File.ReadAllText(stylesheetPath);
            const string marker = "/* Tessaris embedded Boardroom */";
            if (stylesheet.Contains(marker)) return;
            File.AppendAllText(stylesheetPath, @"

/* Tessaris embedded Boardroom */
html, body { width: 100%; height: 100%; overflow: hidden; background: transparent; }
#unity-container.unity-desktop { position: fixed; inset: 0; width: 100%; height: 100%; transform: none; }
#unity-canvas { width: 100% !important; height: 100% !important; display: block; background: transparent; }
#unity-footer { display: none !important; }
");
        }

        private static void EnsureRuntimeMaterial()
        {
            var standard = Shader.Find("Standard");
            if (standard == null) throw new System.InvalidOperationException("Unity's Standard shader is unavailable.");
            const string materialPath = "Assets/Resources/TessarisStandard.mat";
            if (AssetDatabase.LoadAssetAtPath<Material>(materialPath) != null) return;
            Directory.CreateDirectory("Assets/Resources");
            AssetDatabase.CreateAsset(new Material(standard) { name = "Tessaris Standard" }, materialPath);
            AssetDatabase.SaveAssets();
        }
    }
}
