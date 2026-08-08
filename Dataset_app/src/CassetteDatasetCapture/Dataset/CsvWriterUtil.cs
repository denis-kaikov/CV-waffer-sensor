using System.Globalization;
using System.Text;

namespace CassetteDatasetCapture.Dataset;

public static class CsvWriterUtil
{
    public static string Escape(string value)
    {
        if (value.Contains('"') || value.Contains(',') || value.Contains('\n') || value.Contains('\r'))
            return $"\"{value.Replace("\"", "\"\"")}\"";
        return value;
    }
}
