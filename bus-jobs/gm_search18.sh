#!/bin/bash
# gm_search18.sh — get bl_SpawnPoint fields + Team enum
grep -n "m_Team\|enum Team\|Team1\|Team2\|Team\.All\|public Team\|m_Team =" $(find /content/work/mfps -name "bl_SpawnPoint.cs" | head -1)
echo "---ENUM---"
grep -rn "enum Team" /content/work/mfps/Assets/MFPS/Scripts/ | head -5