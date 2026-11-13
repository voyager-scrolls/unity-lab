#!/bin/bash
# mcp_head22.sh — grep for HandleExecute + compile method in ExecuteCode.cs
grep -n "HandleExecute\|CompileAndRun\|Roslyn\|CSharpCodeProvider\|ExecuteCode\|assembly\|CompilationPipeline" /content/work/mfps/Library/PackageCache/com.coplaydev.unity-mcp@4384f8b518e8/Editor/Tools/ExecuteCode.cs | head -40