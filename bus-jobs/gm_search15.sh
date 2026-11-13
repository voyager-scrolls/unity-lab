#!/bin/bash
# gm_search15.sh — get bl_GameManager Awake/Instance
grep -n "Instance\|Awake\|OnEnable\|RegisterSpawnPoint\|GetAnTeamSpawnPoint\|GetSpawn" $(find /content/work/mfps -name "bl_GameManager.cs" | head -1)