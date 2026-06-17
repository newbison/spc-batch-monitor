$root = 'd:\coding_is_fun\polymer_simulation'
$files = @(
    (Join-Path $root 'lib\renderer.js'),
    (Join-Path $root 'lib\ui-base.js'),
    (Join-Path $root 'free-radical\simulation.js'),
    (Join-Path $root 'free-radical\theme.js'),
    (Join-Path $root 'free-radical\ui.js'),
    (Join-Path $root 'free-radical\main.js')
)
$output = New-Object System.Collections.Generic.List[string]
foreach ($f in $files) {
    $lines = Get-Content $f -Encoding UTF8
    foreach ($line in $lines) {
        $line2 = $line -replace '^export ', ''
        if ($line2 -match '^import ') { continue }
        $output.Add($line2)
    }
    $output.Add('')
}
$outputPath = Join-Path $root 'free-radical\bundle.js'
[System.IO.File]::WriteAllLines($outputPath, $output, [System.Text.Encoding]::UTF8)
Write-Output ("Lines: " + $output.Count)
