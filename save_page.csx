#r "nuget: Docnet.Core, 2.6.0"
#r "nuget: SkiaSharp, 3.116.1"
using Docnet.Core;
using Docnet.Core.Models;
using SkiaSharp;

var pdfPath = @"../test-pdfs/lab_report_01.pdf";
using var docReader = DocLib.Instance.GetDocReader(pdfPath, new PageDimensions(1440, 1864));
using var pageReader = docReader.GetPageReader(0);
var rawBytes = pageReader.GetImage();
var width = pageReader.GetPageWidth();
var height = pageReader.GetPageHeight();
Console.WriteLine($"Page size: {width}x{height}, raw bytes: {rawBytes.Length}");

using var bitmap = new SKBitmap(width, height, SKColorType.Bgra8888, SKAlphaType.Premul);
System.Runtime.InteropServices.Marshal.Copy(rawBytes, 0, bitmap.GetPixels(), rawBytes.Length);
using var image = SKImage.FromBitmap(bitmap);
using var data = image.Encode(SKEncodedImageFormat.Png, 85);
File.WriteAllBytes(@"../test_page_render.png", data.ToArray());
Console.WriteLine($"Saved test_page_render.png ({data.Size / 1024} KB)");
