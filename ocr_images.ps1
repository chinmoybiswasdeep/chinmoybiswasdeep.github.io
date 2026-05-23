Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics.Imaging, ContentType = WindowsRuntime]
$null = [Windows.Graphics.Imaging.SoftwareBitmap, Windows.Graphics.Imaging, ContentType = WindowsRuntime]
$null = [Windows.Media.Ocr.OcrEngine, Windows.Media.Ocr, ContentType = WindowsRuntime]

function Await($Operation, [Type]$ResultType) {
    $AsTaskMethod = ([System.WindowsRuntimeSystemExtensions].GetMethods() |
        Where-Object {
            $_.Name -eq 'AsTask' -and
            $_.IsGenericMethod -and
            $_.GetParameters().Count -eq 1
        } |
        Select-Object -First 1)

    if (-not $AsTaskMethod) {
        throw 'Unable to find a compatible AsTask overload.'
    }

    $Task = $AsTaskMethod.MakeGenericMethod($ResultType).Invoke($null, @($Operation))
    $Task.Wait()
    return $Task.Result
}

function Read-OcrText($Path) {
    $FullPath = (Resolve-Path $Path).Path
    $File = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync($FullPath)) ([Windows.Storage.StorageFile])
    $Stream = Await ($File.OpenReadAsync()) ([Windows.Storage.Streams.IRandomAccessStreamWithContentType])
    $Decoder = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($Stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
    $Bitmap = Await ($Decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
    $Engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
    $Result = Await ($Engine.RecognizeAsync($Bitmap)) ([Windows.Media.Ocr.OcrResult])
    return $Result.Text
}

Write-Output "OCR RESULTS"
foreach ($ImageName in @("style_example.png", "experiences.png")) {
    Write-Output ("-- " + $ImageName + " --")
    try {
        $Text = Read-OcrText $ImageName
        if ([string]::IsNullOrWhiteSpace($Text)) {
            Write-Output "no OCR text found"
        }
        else {
            Write-Output $Text
        }
    }
    catch {
        Write-Output ("error: " + $_.Exception.Message)
    }
}