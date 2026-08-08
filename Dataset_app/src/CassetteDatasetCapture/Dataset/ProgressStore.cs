using System.Text.Json;

namespace CassetteDatasetCapture.Dataset;

public sealed class ProgressStore
{
    public ProgressState State { get; }
    public ProgressStore(ProgressState state) => State = state;

    public void Set(string configId, string status, int shotsDone)
    {
        if (!State.Configs.TryGetValue(configId, out var item))
        {
            item = new ProgressItem();
            State.Configs[configId] = item;
        }
        item.Status = status;
        item.ShotsDone = shotsDone;
        State.CurrentConfigId = configId;
    }

    public void Save(string path)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(path)!);
        File.WriteAllText(path, JsonSerializer.Serialize(State, new JsonSerializerOptions { WriteIndented = true }));
    }
}
