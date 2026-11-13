using System.Collections.Generic;
using UnityEngine;

/// <summary>
/// Poisson disk sampling for even prop placement in 2D/3D spaces.
/// Based on Bridson's algorithm (2007). Pure C#, no external dependencies.
/// </summary>
public static class PoissonDiskSampler
{
    /// <summary>
    /// Generate evenly-spaced points in a 2D rectangle.
    /// </summary>
    /// <param name="width">Rectangle width (X axis)</param>
    /// <param name="height">Rectangle height (Z axis)</param>
    /// <param name="minDistance">Minimum distance between any two points</param>
    /// <param name="maxAttempts">Max attempts per active point (default 30)</param>
    /// <param name="seed">Random seed for reproducibility</param>
    /// <returns>List of sampled (x, z) positions</returns>
    public static List<Vector2> Sample2D(float width, float height, float minDistance, int maxAttempts = 30, int seed = 0)
    {
        System.Random rng = new System.Random(seed);
        float cellSize = minDistance / Mathf.Sqrt(2f);
        int gridW = Mathf.CeilToInt(width / cellSize);
        int gridH = Mathf.CeilToInt(height / cellSize);

        int[,] grid = new int[gridW, gridH];
        for (int x = 0; x < gridW; x++)
            for (int y = 0; y < gridH; y++)
                grid[x, y] = -1;

        List<Vector2> points = new List<Vector2>();
        List<int> active = new List<int>();

        // First point: random
        Vector2 first = new Vector2(
            (float)(rng.NextDouble() * width),
            (float)(rng.NextDouble() * height));
        points.Add(first);
        active.Add(0);
        grid[Mathf.FloorToInt(first.x / cellSize), Mathf.FloorToInt(first.y / cellSize)] = 0;

        while (active.Count > 0)
        {
            int idx = rng.Next(active.Count);
            int activeIdx = active[idx];
            Vector2 center = points[activeIdx];
            bool found = false;

            for (int attempt = 0; attempt < maxAttempts; attempt++)
            {
                float angle = (float)(rng.NextDouble() * Mathf.PI * 2f);
                float dist = minDistance + (float)(rng.NextDouble() * minDistance);
                Vector2 candidate = center + new Vector2(
                    Mathf.Cos(angle) * dist,
                    Mathf.Sin(angle) * dist);

                if (candidate.x < 0 || candidate.x >= width || candidate.y < 0 || candidate.y >= height)
                    continue;

                int gx = Mathf.FloorToInt(candidate.x / cellSize);
                int gy = Mathf.FloorToInt(candidate.y / cellSize);
                if (gx < 0 || gx >= gridW || gy < 0 || gy >= gridH) continue;

                // Check neighbors (3x3 grid around candidate)
                bool tooClose = false;
                for (int nx = Mathf.Max(0, gx - 1); nx <= Mathf.Min(gridW - 1, gx + 1); nx++)
                {
                    for (int ny = Mathf.Max(0, gy - 1); ny <= Mathf.Min(gridH - 1, gy + 1); ny++)
                    {
                        int neighborIdx = grid[nx, ny];
                        if (neighborIdx >= 0)
                        {
                            float d = Vector2.Distance(candidate, points[neighborIdx]);
                            if (d < minDistance) { tooClose = true; break; }
                        }
                    }
                    if (tooClose) break;
                }

                if (!tooClose)
                {
                    points.Add(candidate);
                    active.Add(points.Count - 1);
                    grid[gx, gy] = points.Count - 1;
                    found = true;
                    break;
                }
            }

            if (!found)
                active.RemoveAt(idx);
        }

        return points;
    }

    /// <summary>
    /// Generate evenly-spaced points in a 3D box.
    /// </summary>
    public static List<Vector3> Sample3D(Vector3 min, Vector3 max, float minDistance, int maxAttempts = 30, int seed = 0)
    {
        System.Random rng = new System.Random(seed);
        float cellSize = minDistance / Mathf.Sqrt(3f);
        Vector3 size = max - min;
        int gridX = Mathf.CeilToInt(size.x / cellSize);
        int gridY = Mathf.CeilToInt(size.y / cellSize);
        int gridZ = Mathf.CeilToInt(size.z / cellSize);

        // Flatten 3D grid to 1D for simplicity
        int[,,] grid = new int[gridX, gridY, gridZ];
        for (int x = 0; x < gridX; x++)
            for (int y = 0; y < gridY; y++)
                for (int z = 0; z < gridZ; z++)
                    grid[x, y, z] = -1;

        List<Vector3> points = new List<Vector3>();
        List<int> active = new List<int>();

        Vector3 first = new Vector3(
            min.x + (float)(rng.NextDouble() * size.x),
            min.y + (float)(rng.NextDouble() * size.y),
            min.z + (float)(rng.NextDouble() * size.z));
        points.Add(first);
        active.Add(0);
        grid[Mathf.FloorToInt((first.x - min.x) / cellSize),
             Mathf.FloorToInt((first.y - min.y) / cellSize),
             Mathf.FloorToInt((first.z - min.z) / cellSize)] = 0;

        while (active.Count > 0)
        {
            int idx = rng.Next(active.Count);
            int activeIdx = active[idx];
            Vector3 center = points[activeIdx];
            bool found = false;

            for (int attempt = 0; attempt < maxAttempts; attempt++)
            {
                // Random point on sphere surface around center
                float theta = (float)(rng.NextDouble() * Mathf.PI * 2f);
                float phi = Mathf.Acos(2f * (float)rng.NextDouble() - 1f);
                float dist = minDistance + (float)(rng.NextDouble() * minDistance);
                Vector3 candidate = center + new Vector3(
                    Mathf.Sin(phi) * Mathf.Cos(theta) * dist,
                    Mathf.Sin(phi) * Mathf.Sin(theta) * dist,
                    Mathf.Cos(phi) * dist);

                if (candidate.x < min.x || candidate.x >= max.x ||
                    candidate.y < min.y || candidate.y >= max.y ||
                    candidate.z < min.z || candidate.z >= max.z)
                    continue;

                int gx = Mathf.FloorToInt((candidate.x - min.x) / cellSize);
                int gy = Mathf.FloorToInt((candidate.y - min.y) / cellSize);
                int gz = Mathf.FloorToInt((candidate.z - min.z) / cellSize);
                if (gx < 0 || gx >= gridX || gy < 0 || gy >= gridY || gz < 0 || gz >= gridZ) continue;

                bool tooClose = false;
                for (int nx = Mathf.Max(0, gx - 1); nx <= Mathf.Min(gridX - 1, gx + 1); nx++)
                {
                    for (int ny = Mathf.Max(0, gy - 1); ny <= Mathf.Min(gridY - 1, gy + 1); ny++)
                    {
                        for (int nz = Mathf.Max(0, gz - 1); nz <= Mathf.Min(gridZ - 1, gz + 1); nz++)
                        {
                            int neighborIdx = grid[nx, ny, nz];
                            if (neighborIdx >= 0)
                            {
                                float d = Vector3.Distance(candidate, points[neighborIdx]);
                                if (d < minDistance) { tooClose = true; break; }
                            }
                        }
                        if (tooClose) break;
                    }
                    if (tooClose) break;
                }

                if (!tooClose)
                {
                    points.Add(candidate);
                    active.Add(points.Count - 1);
                    grid[gx, gy, gz] = points.Count - 1;
                    found = true;
                    break;
                }
            }

            if (!found)
                active.RemoveAt(idx);
        }

        return points;
    }

    /// <summary>
    /// Generate a level layout JSON string from a Poisson-sampled prop placement.
    /// </summary>
    public static string GenerateLayoutJson(Vector3 roomMin, Vector3 roomMax, float minDistance, string[] propPaths, int seed = 0)
    {
        var points = Sample3D(roomMin, roomMax, minDistance, 30, seed);
        System.Text.StringBuilder sb = new System.Text.StringBuilder();
        sb.Append("{\n");
        sb.Append("  \"room\": { \"min\": [" + roomMin.x + ", " + roomMin.y + ", " + roomMin.z + "], \"max\": [" + roomMax.x + ", " + roomMax.y + ", " + roomMax.z + "] },\n");
        sb.Append("  \"minDistance\": " + minDistance + ",\n");
        sb.Append("  \"props\": [\n");

        System.Random rng = new System.Random(seed + 1);
        for (int i = 0; i < points.Count; i++)
        {
            if (i > 0) sb.Append(",\n");
            string propPath = propPaths[rng.Next(propPaths.Length)];
            sb.Append("    { \"prefab\": \"" + propPath + "\", \"position\": [" + points[i].x + ", " + points[i].y + ", " + points[i].z + "], \"rotation\": [0, " + (rng.Next(0, 4) * 90) + ", 0] }");
        }

        sb.Append("\n  ]\n}\n");
        return sb.ToString();
    }
}
