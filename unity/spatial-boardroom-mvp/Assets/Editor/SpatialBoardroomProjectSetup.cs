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

        [MenuItem("Tessaris/Build Spatial Boardroom/macOS Apple Silicon")]
        private static void BuildMac()
        {
            EnsureScene();
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
    }
}
