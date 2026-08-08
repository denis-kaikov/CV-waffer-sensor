using System.Text.Json;

namespace CassetteDatasetCapture.CapturePlan;

public static class CapturePlanLoader
{
    public static CapturePlan Load(string path) => JsonSerializer.Deserialize<CapturePlan>(
        File.ReadAllText(path),
        new JsonSerializerOptions { PropertyNameCaseInsensitive = true })
        ?? throw new InvalidDataException("capture_plan.json is empty or invalid.");
}
