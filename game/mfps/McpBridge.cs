using System;
using System.IO;
using System.Threading.Tasks;
using MCPForUnity.Editor.Tools;
using MCPForUnity.Editor.Tools.Prefabs;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using UnityEngine;

public static class McpBridge
{
    private const string CommandFile = "/content/mcp_command.json";
    private const string ResultFile = "/content/mcp_result.json";

    public static void Run()
    {
        try
        {
            if (!File.Exists(CommandFile))
            {
                WriteResult("{\"success\":false,\"error\":\"No command file at " + CommandFile + "\"}");
                return;
            }

            string json = File.ReadAllText(CommandFile);
            var cmd = JObject.Parse(json);
            string tool = cmd["tool"]?.ToString();
            var p = cmd["params"] as JObject ?? new JObject();

            object result = null;
            switch (tool)
            {
                case "read_console":
                    result = ReadConsole.HandleCommand(p);
                    break;
                case "manage_scene":
                    result = ManageScene.HandleCommand(p);
                    break;
                case "manage_asset":
                    result = ManageAsset.HandleCommand(p);
                    break;
                case "manage_prefabs":
                    result = ManagePrefabs.HandleCommand(p);
                    break;
                case "execute_code":
                    result = ExecuteCode.HandleCommand(p);
                    break;
                case "batch_execute":
                    var task = BatchExecute.HandleCommand(p);
                    task.GetAwaiter().GetResult();
                    result = task.Result;
                    break;
                case "manage_gameobject":
                    result = ManageGameObject.HandleCommand(p);
                    break;
                default:
                    result = new ErrorResponse("Unknown tool: " + tool);
                    break;
            }

            string resultJson = JsonConvert.SerializeObject(result);
            WriteResult(resultJson);
            Debug.Log("MCP_BRIDGE_RESULT: " + resultJson);
        }
        catch (Exception e)
        {
            string errJson = JsonConvert.SerializeObject(new { success = false, error = e.ToString() });
            WriteResult(errJson);
            Debug.LogError("MCP_BRIDGE_ERROR: " + e);
        }
    }

    private static void WriteResult(string json)
    {
        File.WriteAllText(ResultFile, json);
    }
}
