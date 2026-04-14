using System.Diagnostics;
using System.Net.Http.Json;
using System.Text.Json.Serialization;

if (args.Length == 0)
{
    Console.WriteLine("Usage: GemmaOcrTest <file-path> [prompt]");
    Console.WriteLine("  file-path: Path to an image (PNG, JPG, WebP) or PDF file");
    Console.WriteLine("  prompt:    Optional custom prompt (default: extract all text)");
    return 1;
}

var filePath = Path.GetFullPath(args[0]);
if (!File.Exists(filePath))
{
    Console.Error.WriteLine($"File not found: {filePath}");
    return 1;
}

var prompt = args.Length > 1
    ? string.Join(' ', args.Skip(1))
    : "Extract all text from this image. Return only the extracted text, preserving the original formatting as closely as possible.";

using var httpClient = new HttpClient { Timeout = TimeSpan.FromMinutes(5) };
var ollamaUrl = Environment.GetEnvironmentVariable("OLLAMA_HOST") ?? "http://localhost:11434";

var isPdf = Path.GetExtension(filePath).Equals(".pdf", StringComparison.OrdinalIgnoreCase);

if (isPdf)
{
    var pageImages = await ConvertPdfToPngImages(filePath);
    Console.Error.WriteLine($"PDF has {pageImages.Count} page(s)");

    for (int i = 0; i < pageImages.Count; i++)
    {
        Console.Error.WriteLine($"\n--- Processing page {i + 1}/{pageImages.Count} ---");
        var result = await SendToGemma(httpClient, ollamaUrl, pageImages[i], prompt,
            $"page {i + 1}", pageImages[i].Length / 1024);

        if (pageImages.Count > 1)
            Console.WriteLine($"\n=== PAGE {i + 1} ===");
        Console.WriteLine(result);
    }
}
else
{
    var imageBytes = await File.ReadAllBytesAsync(filePath);
    Console.Error.WriteLine($"Sending image to Gemma 4 ({Path.GetFileName(filePath)}, {imageBytes.Length / 1024} KB)...");
    var result = await SendToGemma(httpClient, ollamaUrl, imageBytes, prompt,
        Path.GetFileName(filePath), imageBytes.Length / 1024);
    Console.WriteLine(result);
}

return 0;

static async Task<string> SendToGemma(HttpClient httpClient, string ollamaUrl, byte[] imageBytes, string prompt, string label, long sizeKb)
{
    var base64Image = Convert.ToBase64String(imageBytes);
    var request = new OllamaGenerateRequest
    {
        Model = "gemma4:e4b",
        Prompt = prompt,
        Images = [base64Image],
        Stream = false
    };

    Console.Error.WriteLine($"Sending {label} ({sizeKb} KB) to Gemma 4...");

    try
    {
        var response = await httpClient.PostAsJsonAsync($"{ollamaUrl}/api/generate", request);
        response.EnsureSuccessStatusCode();
        var result = await response.Content.ReadFromJsonAsync<OllamaGenerateResponse>();
        return result?.Response ?? "(no response)";
    }
    catch (HttpRequestException ex)
    {
        Console.Error.WriteLine($"Error connecting to Ollama at {ollamaUrl}: {ex.Message}");
        Console.Error.WriteLine("Make sure Ollama is running (ollama serve)");
        Environment.Exit(1);
        return "";
    }
    catch (TaskCanceledException)
    {
        Console.Error.WriteLine("Request timed out. The image may be too large or the model is still loading.");
        Environment.Exit(1);
        return "";
    }
}

static async Task<List<byte[]>> ConvertPdfToPngImages(string pdfPath)
{
    // Use PyMuPDF via Python for reliable PDF rendering
    var tempDir = Path.Combine(Path.GetTempPath(), $"gemma_ocr_{Guid.NewGuid():N}");
    Directory.CreateDirectory(tempDir);

    // Find the helper script next to the executable or in the project directory
    var exeDir = AppContext.BaseDirectory;
    var scriptPath = Path.Combine(exeDir, "pdf_to_png.py");
    if (!File.Exists(scriptPath))
    {
        // Look relative to working directory
        scriptPath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "..", "..", "..", "pdf_to_png.py");
        if (!File.Exists(scriptPath))
            scriptPath = Path.Combine(Directory.GetCurrentDirectory(), "pdf_to_png.py");
    }

    var psi = new ProcessStartInfo("python", $"\"{scriptPath}\" \"{pdfPath}\" \"{tempDir}\"")
    {
        RedirectStandardOutput = true,
        RedirectStandardError = true,
        UseShellExecute = false
    };

    var process = Process.Start(psi)!;
    var stdout = await process.StandardOutput.ReadToEndAsync();
    var stderr = await process.StandardError.ReadToEndAsync();
    await process.WaitForExitAsync();

    if (process.ExitCode != 0)
    {
        Console.Error.WriteLine($"PDF conversion failed: {stderr}");
        Console.Error.WriteLine("Make sure pymupdf is installed: pip install pymupdf");
        Environment.Exit(1);
    }

    var images = new List<byte[]>();
    var pngFiles = Directory.GetFiles(tempDir, "page_*.png").OrderBy(f => f).ToList();
    foreach (var pngFile in pngFiles)
    {
        images.Add(await File.ReadAllBytesAsync(pngFile));
    }

    // Cleanup temp files
    Directory.Delete(tempDir, true);

    return images;
}

record OllamaGenerateRequest
{
    [JsonPropertyName("model")] public string Model { get; init; } = "";
    [JsonPropertyName("prompt")] public string Prompt { get; init; } = "";
    [JsonPropertyName("images")] public string[] Images { get; init; } = [];
    [JsonPropertyName("stream")] public bool Stream { get; init; }
}

record OllamaGenerateResponse
{
    [JsonPropertyName("response")] public string Response { get; init; } = "";
}
