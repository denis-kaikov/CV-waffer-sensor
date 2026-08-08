namespace CassetteDatasetCapture.Utils;

public static class StringMaskUtil
{
    public static string EnsureLength(string value, int length, char pad = '0') => value.Length >= length ? value[..length] : value.PadRight(length, pad);
}
