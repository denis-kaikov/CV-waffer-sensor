using System;
using System.Diagnostics;
using System.IO;
using System.Windows.Forms;

internal static class Launcher
{
    [STAThread]
    private static void Main()
    {
        try
        {
            var appRoot = AppDomain.CurrentDomain.BaseDirectory;
            var dotnetRoot = Path.Combine(appRoot, "dotnet");
            var dotnetExe = Path.Combine(dotnetRoot, "dotnet.exe");
            var appDll = Path.Combine(appRoot, "CassetteDatasetCapture.dll");

            if (!File.Exists(dotnetExe))
            {
                MessageBox.Show(
                    "Не найден встроенный dotnet.exe. Переустановите приложение.",
                    "CassetteDatasetCapture",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Error);
                return;
            }

            if (!File.Exists(appDll))
            {
                MessageBox.Show(
                    "Не найден CassetteDatasetCapture.dll. Переустановите приложение.",
                    "CassetteDatasetCapture",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Error);
                return;
            }

            var startInfo = new ProcessStartInfo
            {
                FileName = dotnetExe,
                Arguments = "\"" + appDll + "\"",
                WorkingDirectory = appRoot,
                UseShellExecute = false,
                CreateNoWindow = true,
                WindowStyle = ProcessWindowStyle.Hidden
            };

            startInfo.EnvironmentVariables["DOTNET_ROOT"] = dotnetRoot;
            startInfo.EnvironmentVariables["DOTNET_ROOT_X64"] = dotnetRoot;

            var existingPath = startInfo.EnvironmentVariables["PATH"] ?? string.Empty;
            var separator = string.IsNullOrWhiteSpace(existingPath) ? string.Empty : ";";
            startInfo.EnvironmentVariables["PATH"] = dotnetRoot + separator + existingPath;

            Process.Start(startInfo);
        }
        catch (Exception ex)
        {
            MessageBox.Show(
                ex.Message,
                "CassetteDatasetCapture",
                MessageBoxButtons.OK,
                MessageBoxIcon.Error);
        }
    }
}
