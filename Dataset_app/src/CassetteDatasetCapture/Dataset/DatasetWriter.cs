using System.Globalization;
using System.Text;
using System.Text.Json;

namespace CassetteDatasetCapture.Dataset;

public sealed class DatasetWriter
{
    private const string CsvHeader = "image_path,cassette_size_mm,slot_count,config_id,shot_index,normal_occupancy,blocked_slots,slot_states,anomalies_json,image_quality,exposure_us,gain,timestamp,operator_name,status,notes";
    private readonly object _gate = new();

    public DatasetPaths Paths { get; }

    public DatasetWriter(DatasetPaths paths) => Paths = paths;

    public void EnsureLayout()
    {
        Directory.CreateDirectory(Paths.Root);
        Directory.CreateDirectory(Paths.ImagesRoot);
        Directory.CreateDirectory(Paths.RejectedRoot);
    }

    public void Append(DatasetRecord record)
    {
        lock (_gate)
        {
            EnsureLayout();
            var csvExists = File.Exists(Paths.LabelsCsv);
            using var sw = new StreamWriter(Paths.LabelsCsv, append: true, Encoding.UTF8);
            if (!csvExists)
            {
                sw.WriteLine(CsvHeader);
            }

            sw.WriteLine(ToCsvRow(record));
            File.AppendAllText(Paths.LabelsJsonl, JsonlWriter.Serialize(record) + Environment.NewLine, Encoding.UTF8);
        }
    }

    public bool MarkImageRejected(string imagePath, string note)
    {
        lock (_gate)
        {
            var records = ReadJsonlRecords();
            var index = records.FindLastIndex(r =>
                string.Equals(r.ImagePath, imagePath, StringComparison.OrdinalIgnoreCase) &&
                string.Equals(r.Status, "accepted", StringComparison.OrdinalIgnoreCase));

            if (index < 0)
            {
                return false;
            }

            var record = records[index];
            record.Status = "rejected";
            record.ImageQuality = "rejected";
            record.Notes = string.IsNullOrWhiteSpace(record.Notes)
                ? note
                : $"{record.Notes}; {note}";

            RewriteLabels(records);
            return true;
        }
    }

    public void WriteProgress(ProgressStore progressStore, string path) => progressStore.Save(path);

    private List<DatasetRecord> ReadJsonlRecords()
    {
        if (!File.Exists(Paths.LabelsJsonl))
        {
            return new List<DatasetRecord>();
        }

        var records = new List<DatasetRecord>();
        foreach (var line in File.ReadLines(Paths.LabelsJsonl, Encoding.UTF8))
        {
            if (string.IsNullOrWhiteSpace(line))
            {
                continue;
            }

            var record = JsonSerializer.Deserialize<DatasetRecord>(line);
            if (record is not null)
            {
                records.Add(record);
            }
        }

        return records;
    }

    private void RewriteLabels(IReadOnlyList<DatasetRecord> records)
    {
        EnsureLayout();
        using (var csv = new StreamWriter(Paths.LabelsCsv, append: false, Encoding.UTF8))
        {
            csv.WriteLine(CsvHeader);
            foreach (var record in records)
            {
                csv.WriteLine(ToCsvRow(record));
            }
        }

        var jsonl = string.Join(Environment.NewLine, records.Select(JsonlWriter.Serialize));
        File.WriteAllText(Paths.LabelsJsonl, jsonl + Environment.NewLine, Encoding.UTF8);
    }

    private static string ToCsvRow(DatasetRecord record)
    {
        return string.Join(",",
            CsvWriterUtil.Escape(record.ImagePath),
            record.CassetteSizeMm.ToString(CultureInfo.InvariantCulture),
            record.SlotCount.ToString(CultureInfo.InvariantCulture),
            CsvWriterUtil.Escape(record.ConfigId),
            record.ShotIndex.ToString(CultureInfo.InvariantCulture),
            CsvWriterUtil.Escape(record.NormalOccupancy),
            CsvWriterUtil.Escape(record.BlockedSlots),
            CsvWriterUtil.Escape(record.SlotStates),
            CsvWriterUtil.Escape(JsonSerializer.Serialize(record.Anomalies)),
            CsvWriterUtil.Escape(record.ImageQuality),
            record.ExposureUs.ToString(CultureInfo.InvariantCulture),
            record.Gain.ToString(CultureInfo.InvariantCulture),
            CsvWriterUtil.Escape(record.Timestamp.ToString("O")),
            CsvWriterUtil.Escape(record.OperatorName),
            CsvWriterUtil.Escape(record.Status),
            CsvWriterUtil.Escape(record.Notes));
    }
}
