using System.Text.Json;

namespace CassetteDatasetCapture.Dataset;

public static class JsonlWriter
{
    public static string Serialize<T>(T value) => JsonSerializer.Serialize(value, new JsonSerializerOptions { WriteIndented = false });
}
