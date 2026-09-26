# 中身が同じファイル(重複)を見つけ、1つだけ残して「重複」フォルダへ移動するスクリプト
# 使い方:
#   確認のみ(何も動かさない): powershell -ExecutionPolicy Bypass -File .\move-duplicates.ps1
#   実際に移動する         : powershell -ExecutionPolicy Bypass -File .\move-duplicates.ps1 -Run
param(
    [string]$Target = "I:\くらしのマーケット\20260926一宮松本様撮影",
    [switch]$Run
)

$Target = $Target.TrimEnd("\")
if (-not (Test-Path -LiteralPath $Target)) {
    Write-Host "フォルダが見つかりません: $Target" -ForegroundColor Red
    return
}

$DupDir = Join-Path $Target "重複"
$log = New-Object System.Collections.Generic.List[object]

# 「重複」フォルダ自体は対象外にする
$files = Get-ChildItem -LiteralPath $Target -File -Recurse |
    Where-Object { -not $_.FullName.StartsWith($DupDir + "\") }

Write-Host "対象ファイル数: $($files.Count)"

# まずサイズで絞り込み、同じサイズのものだけハッシュを計算する(大きな動画でも速くするため)
# 0バイトのファイルは対象外にする
$sizeGroups = $files | Where-Object { $_.Length -gt 0 } |
    Group-Object Length | Where-Object { $_.Count -gt 1 }

foreach ($sg in $sizeGroups) {
    $hashed = foreach ($f in $sg.Group) {
        Write-Host "照合中: $($f.Name)"
        [PSCustomObject]@{
            File = $f
            Hash = (Get-FileHash -LiteralPath $f.FullName -Algorithm SHA256).Hash
        }
    }

    foreach ($hg in ($hashed | Group-Object Hash | Where-Object { $_.Count -gt 1 })) {
        # 一番古いファイルを残し、それ以外を移動する
        $sorted = $hg.Group | ForEach-Object { $_.File } | Sort-Object LastWriteTime, FullName
        $keep = $sorted[0]

        foreach ($dup in ($sorted | Select-Object -Skip 1)) {
            # 元のフォルダ構成を保ったまま「重複」フォルダへ移動する
            $rel  = $dup.FullName.Substring($Target.Length).TrimStart("\")
            $dest = Join-Path $DupDir $rel

            # 移動先に同名ファイルがある場合は名前の後ろに番号を付ける
            $n = 1
            while (Test-Path -LiteralPath $dest) {
                $dir  = Split-Path $dest
                $base = [System.IO.Path]::GetFileNameWithoutExtension($dup.Name)
                $dest = Join-Path $dir ("{0}_{1}{2}" -f $base, $n, $dup.Extension)
                $n++
            }

            $log.Add([PSCustomObject]@{
                残したファイル = $keep.FullName
                移動したファイル = $dup.FullName
                移動先 = $dest
                サイズMB = [math]::Round($dup.Length / 1MB, 1)
            })

            if ($Run) {
                New-Item -ItemType Directory -Path (Split-Path $dest) -Force | Out-Null
                Move-Item -LiteralPath $dup.FullName -Destination $dest
                Write-Host "移動: $rel" -ForegroundColor Yellow
            } else {
                Write-Host "[確認] 移動予定: $rel  (残す: $($keep.Name))" -ForegroundColor Cyan
            }
        }
    }
}

if ($log.Count -eq 0) {
    Write-Host "重複ファイルは見つかりませんでした。" -ForegroundColor Green
    return
}

$totalMB = ($log | Measure-Object サイズMB -Sum).Sum
if ($Run) {
    $csv = Join-Path $DupDir ("重複リスト_{0}.csv" -f (Get-Date -Format "yyyyMMdd_HHmmss"))
    $log | Export-Csv -LiteralPath $csv -NoTypeInformation -Encoding UTF8
    Write-Host "完了: $($log.Count) 件 / $totalMB MB を移動しました。一覧は $csv にあります。" -ForegroundColor Green
} else {
    Write-Host "確認のみ: $($log.Count) 件 / $totalMB MB が移動対象です。問題なければ -Run を付けて実行してください。" -ForegroundColor Green
}
