#!/bin/bash
# inspect_character.sh - check what a character prefab actually instantiates (renderers, active states).
set -e
PROJ=/content/work/mfps
UNITY=/content/ue/Editor/Unity
echo "=== PREFLIGHT ==="
test -x "$UNITY" || { echo NO_EDITOR; exit 6; }
test -f "$PROJ/Assets/MFPS/Scenes/HeistLevel.unity" || { echo NO_SCENE; exit 6; }
echo PREFLIGHT_OK

cat > "$PROJ/Assets/Editor/InspectCharacter.cs" << 'CSEOF'
using System.IO;
using System.Text;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

public static class InspectCharacter
{
    public static void Run()
    {
        EditorSceneManager.OpenScene("Assets/MFPS/Scenes/HeistLevel.unity", OpenSceneMode.Single);
        var sb = new StringBuilder();
        string[] names = { "Character_Male_SWAT_01", "Character_Male_FBI", "Character_Male_SuitVest_01" };
        foreach (var nm in names)
        {
            var guids = AssetDatabase.FindAssets(nm + " t:Prefab");
            if (guids.Length == 0) { sb.AppendLine(nm + " NOT FOUND"); continue; }
            string path = AssetDatabase.GUIDToAssetPath(guids[0]);
            sb.AppendLine("== " + nm + " path=" + path);
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(path);
            var inst = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
            int n = 0;
            foreach (var r in inst.GetComponentsInChildren<SkinnedMeshRenderer>(true))
            {
                n++;
                sb.AppendLine(string.Format("  SMR {0} active={1} goActive={2} bounds={3}",
                    r.name, r.enabled, r.gameObject.activeSelf, r.bounds.size.ToString("F2")));
            }
            sb.AppendLine("  SkinnedMeshRenderers=" + n);
            foreach (var r in inst.GetComponentsInChildren<MeshRenderer>(true))
            {
                sb.AppendLine(string.Format("  MR {0} active={1} goActive={2} size={3}",
                    r.name, r.enabled, r.gameObject.activeSelf, r.bounds.size.ToString("F2")));
            }
            Object.DestroyImmediate(inst);
        }
        File.WriteAllText("/content/inspect_character.txt", sb.ToString());
        Debug.Log("INSPECT_CHARACTER_DONE");
    }
}
CSEOF
echo SCRIPT_WRITTEN

rm -rf "$PROJ/Temp"
"$UNITY" -batchmode -nographics -quit -projectPath "$PROJ" -executeMethod InspectCharacter.Run -logFile /content/inspect_character.log 2>&1 || true
grep -q "INSPECT_CHARACTER_DONE" /content/inspect_character.log && echo DUMPED || { echo INSPECT_FAIL; tail -20 /content/inspect_character.log; exit 6; }
cp /content/inspect_character.txt /content/drive/MyDrive/unity-lab/specs/inspect_character.txt && echo DUMP_STAGED
wc -l /content/inspect_character.txt
echo INSPECT_COMPLETE
