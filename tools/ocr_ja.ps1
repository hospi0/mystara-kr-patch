# Windows 내장 OCR(일본어)로 폴더 안 PNG 의 글자를 읽어 TSV 로 (2026-11-04 쉔무 맵 텍스처 일본어 후보 고르기)
#   powershell -ExecutionPolicy Bypass -File tools\ocr_ja.ps1 <입력폴더> <출력.tsv>
param([string]$InDir, [string]$OutTsv)
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime]
$null = [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics, ContentType = WindowsRuntime]
$asTask = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]
function Await($op, [Type]$t) { $task = $asTask.MakeGenericMethod($t).Invoke($null, @($op)); $task.Wait(-1) | Out-Null; $task.Result }
$null = [Windows.Globalization.Language, Windows.Globalization, ContentType = WindowsRuntime]
$lang = New-Object Windows.Globalization.Language("ja")
$eng = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage($lang)
$sw = New-Object System.IO.StreamWriter($OutTsv, $false, (New-Object System.Text.UTF8Encoding($false)))
$sw.WriteLine("id`ttext")
$files = Get-ChildItem -Path $InDir -Filter *.png
$i = 0
foreach ($f in $files) {
    try {
        $sf = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync($f.FullName)) ([Windows.Storage.StorageFile])
        $st = Await ($sf.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
        $dec = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($st)) ([Windows.Graphics.Imaging.BitmapDecoder])
        $bmp = Await ($dec.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
        $res = Await ($eng.RecognizeAsync($bmp)) ([Windows.Media.Ocr.OcrResult])
        $t = ($res.Lines | ForEach-Object { $_.Text }) -join ' / '
        $st.Dispose()
        if ($t) { $sw.WriteLine($f.BaseName + "`t" + ($t -replace "`t", ' ')) }
    } catch { }
    $i++
    if ($i % 500 -eq 0) { Write-Output "$i / $($files.Count)"; $sw.Flush() }
}
$sw.Close()
Write-Output "done $i"
