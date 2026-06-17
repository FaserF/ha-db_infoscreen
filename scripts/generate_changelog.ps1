<#
.SYNOPSIS
    Generates a structured, deduplicated, user-friendly changelog from git commit history.

.DESCRIPTION
    - Reads commits between $FromTag and HEAD (or all commits if no tag)
    - Filters noise: lazy commits, merge commits, version bumps, file-only updates
    - Groups by conventional commit type with friendly emoji headers
    - Deduplicates: exact matches + near-duplicate collapsing
    - Breaking changes bubble to the top in a dedicated callout block
    - Collapses large categories gracefully with a summary instead of a wall of text
    - Outputs clean GitHub-flavored Markdown

.PARAMETER FromTag
    Git ref to start log from. Empty = all history (capped at 2000).

.PARAMETER TotalCommits
    Raw commit count to show in footer.
#>
param(
    [string]$FromTag = "",
    [string]$TotalCommits = "",
    [string]$Repo = ""
)

Set-StrictMode -Version 3.0

# Noise filter — commits matching ANY pattern are silently dropped
$noisePatterns = [System.Collections.Generic.List[string]]@(
    '^\s*$'
    '^(Update|Aktualisier[et]?|Add|Adds|Adde|Delete|Deletes|Remove|Removes|Rename|Renames|Move|Moves|Fix|Edit|Change|Modify)\s+[\w\-\.\/]+\.\w{1,10}\s*$'
    '^Merge (pull request|branch|remote-tracking branch)\b'
    '^Merge from\b'
    '^(chore|build)(\([^)]*\))?:\s*(bump|release|version)\b'
    '^(bump|release)(\s+version)?\s+v?\d'
    '^v?\d+\.\d+\.\d+\s*$'
    '^\[skip[- ]ci\]'
    '^chore: regenerate (manifest|connections|changelog)\b'
    '^(auto.?generated?|automated?|bot:)\b'
    '^Revert "Revert'
    '^Initial commit\s*$'
    '^WIP\b'
    '^wip\b'
    '^.{1,3}$'
    '\[skip[- ]ci\]\s*$'
)

# Category order & display labels
$categoryOrder  = @('breaking','feat','fix','security','perf','refactor','ui','docs','test','ci','chore','other')
$categoryEmoji  = @{
    breaking  = '💥 Breaking Changes'
    feat      = '✨ New Features'
    fix       = '🐛 Bug Fixes'
    security  = '🔒 Security'
    perf      = '⚡ Performance'
    refactor  = '♻️ Code Improvements'
    ui        = '🎨 UI / Translations'
    docs      = '📚 Documentation'
    test      = '🧪 Tests'
    ci        = '🔄 CI / CD'
    chore     = '🔧 Maintenance'
    other     = '📦 Other Changes'
}

# Conventional commit type → bucket mapping
$typeMap = @{
    feat      = 'feat'
    feature   = 'feat'
    fix       = 'fix'
    bugfix    = 'fix'
    hotfix    = 'fix'
    security  = 'security'
    sec       = 'security'
    perf      = 'perf'
    optim     = 'perf'
    refactor  = 'refactor'
    refact    = 'refactor'
    ui        = 'ui'
    style     = 'ui'
    ux        = 'ui'
    docs      = 'docs'
    doc       = 'docs'
    test      = 'test'
    tests     = 'test'
    ci        = 'ci'
    cd        = 'ci'
    build     = 'ci'
    chore     = 'chore'
    maint     = 'chore'
    deps      = 'chore'
    bump      = 'chore'
    revert    = 'fix'
}

# Scope overrides
$scopeMap = @{
    ui         = 'ui'
    translation= 'ui'
    translate  = 'ui'
    docs       = 'docs'
    readme     = 'docs'
    test       = 'test'
    tests      = 'test'
    ci         = 'ci'
    workflow   = 'ci'
    actions    = 'ci'
}

# Max items shown per section before collapsing
$maxPerSection = 15
$neverCollapse = @('breaking','security')

function Get-NormKey([string]$msg) {
    $n = $msg.ToLower()
    $n = $n -replace '^(feat|fix|docs|style|refactor|perf|test|chore|ci|security|build|ui|ux|revert)(\([^)]*\))?(!)?:\s*',''
    $n = $n -replace '[\.\!\?\,\;\:\"''`]',''
    $n = $n -replace '\b(the|a|an|for|of|in|to|with|from|on|at|by)\b',''
    $n = $n -replace '\s+',' '
    return $n.Trim()
}

function Get-FormattedItem([PSCustomObject]$item, [string]$repo) {
    if ($item.hashes.Count -gt 0) {
        $links = @()
        foreach ($h in $item.hashes) {
            if ($repo) {
                $links += "[$h](https://github.com/$repo/commit/$h)"
            } else {
                $links += "``$h``"
            }
        }
        $hashStr = $links -join ", "
        return "$($item.display) ($hashStr)"
    }
    return $item.display
}

if ($FromTag) {
    $rawLines = git log "${FromTag}..HEAD" --pretty=format:"%h %s" 2>$null
} else {
    $rawLines = git log --pretty=format:"%h %s" --max-count=2000 2>$null
}

$commitLines = if ($rawLines) { @($rawLines) } else { @() }
$totalRaw    = if ($TotalCommits -and $TotalCommits -ne '') { [int]$TotalCommits } else { $commitLines.Count }

$buckets = @{}
foreach ($k in $categoryOrder) {
    $buckets[$k] = [System.Collections.Generic.List[PSCustomObject]]::new()
}

$seenItems = @{}

foreach ($line in $commitLines) {
    $hash = ""
    $msg = ""
    if ($line -match '^([0-9a-fA-F]+)\s+(.*)$') {
        $hash = $Matches[1]
        $msg = $Matches[2].Trim()
    } else {
        $msg = $line.Trim()
    }
    if (-not $msg) { continue }

    $skip = $false
    foreach ($p in $noisePatterns) {
        if ($msg -match $p) { $skip = $true; break }
    }
    if ($skip) { continue }

    $bucket   = 'other'
    $display  = $msg
    $isBreak  = $false

    if ($msg -match '^([A-Za-z][A-Za-z0-9_-]*)(\([^)]*\))?(!)?:\s*(.+)$') {
        $rawType  = $Matches[1].ToLower()
        $rawScope = if ($Matches[2]) { ($Matches[2] -replace '[()]','').ToLower().Trim() } else { '' }
        $isBreak  = ($Matches[3] -eq '!')
        $desc     = $Matches[4].Trim()

        if ($rawScope -and $scopeMap.ContainsKey($rawScope)) {
            $bucket = $scopeMap[$rawScope]
        } elseif ($typeMap.ContainsKey($rawType)) {
            $bucket = $typeMap[$rawType]
        }

        $descCap = if ($desc.Length -gt 0) { $desc.Substring(0,1).ToUpper() + $desc.Substring(1) } else { $desc }
        if ($rawScope) {
            $display = "**$($rawScope):** $descCap"
        } else {
            $display = $descCap
        }
    } else {
        $display = if ($msg.Length -gt 0) { $msg.Substring(0,1).ToUpper() + $msg.Substring(1) } else { $msg }
        $msgLower = $msg.ToLower()
        if ($msgLower -match '\b(general\s+fix|small\s+fix|bug\s+fix|fix(es|ed)?\b|fix\s+\w|general\s+improve)') {
            $bucket = 'fix'
        } elseif ($msgLower -match '\b(ci\b|linter?|lint\s+fix|pipeline|workflow|github\s+action|generate[_\s]changelog|changelog\s+)') {
            $bucket = 'ci'
        } elseif ($msgLower -match '\b(update\s+depend|bump\s+depend|renovate|dependency\s+update|upgrade\s+dep)') {
            $bucket = 'chore'
        } elseif ($msgLower -match '\b(add(ed|s)?\s+(missing\s+)?feature|new\s+feature|add\s+support)') {
            $bucket = 'feat'
        } elseif ($msgLower -match '\b(security|vulnerability|cve|auth(en|oriz))') {
            $bucket = 'security'
        } elseif ($msgLower -match '\b(perf(ormance)?|speed|faster|optim)') {
            $bucket = 'perf'
        } elseif ($msgLower -match '\b(refactor(ing)?|clean.?up|improve(d|s|ment)?)\b') {
            $bucket = 'refactor'
        } elseif ($msgLower -match '\b(doc(s|ument(ation)?)?|readme|wiki|guide)\b') {
            $bucket = 'docs'
        } elseif ($msgLower -match '\b(test(s|ing)?|spec|unit\s+test)') {
            $bucket = 'test'
        } elseif ($msgLower -match '\b(ui\b|ux\b|layout|style|theme|translation|translations|strings|lang)\b') {
            $bucket = 'ui'
        }
    }

    $normKey = Get-NormKey $display

    if ($isBreak) {
        $breakDisplay = "**$display**"
        $breakKey = "breaking:$normKey"
        if ($seenItems.ContainsKey($breakKey)) {
            $existingBreak = $seenItems[$breakKey]
            if ($hash -and $existingBreak.hashes -notcontains $hash) {
                $existingBreak.hashes.Add($hash)
            }
        } else {
            $breakItem = [PSCustomObject]@{
                display = $breakDisplay
                hashes  = [System.Collections.Generic.List[string]]::new()
            }
            if ($hash) { $breakItem.hashes.Add($hash) }
            $seenItems[$breakKey] = $breakItem
            $buckets['breaking'].Add($breakItem)
        }
    }

    if ($seenItems.ContainsKey($normKey)) {
        $existingItem = $seenItems[$normKey]
        if ($hash -and $existingItem.hashes -notcontains $hash) {
            $existingItem.hashes.Add($hash)
        }
        continue
    }

    $item = [PSCustomObject]@{
        display = $display
        hashes  = [System.Collections.Generic.List[string]]::new()
    }
    if ($hash) { $item.hashes.Add($hash) }
    $seenItems[$normKey] = $item
    $buckets[$bucket].Add($item)
}

$out = [System.Collections.Generic.List[string]]::new()
$hasAny        = $false
$filteredCount = 0
foreach ($k in $categoryOrder) { $filteredCount += $buckets[$k].Count }

if ($buckets['breaking'].Count -gt 0) {
    $hasAny = $true
    $out.Add('> [!CAUTION]')
    $out.Add('> **This release contains breaking changes. Please review before updating.**')
    $out.Add('>')
    foreach ($item in $buckets['breaking']) {
        $formatted = Get-FormattedItem $item $Repo
        $out.Add("> - $formatted")
    }
    $out.Add('')
}

foreach ($key in $categoryOrder) {
    if ($key -eq 'breaking') { continue }
    $bucket = $buckets[$key]
    if ($bucket.Count -eq 0) { continue }
    $hasAny = $true

    $out.Add("### $($categoryEmoji[$key])")
    $out.Add('')

    $collapse = ($bucket.Count -gt $maxPerSection) -and ($key -notin $neverCollapse)

    if ($collapse) {
        for ($i = 0; $i -lt $maxPerSection; $i++) {
            $formatted = Get-FormattedItem $bucket[$i] $Repo
            $out.Add("- $formatted")
        }
        $remaining = $bucket.Count - $maxPerSection
        $out.Add('')
        $out.Add("<details>")
        $out.Add("<summary>Show $remaining more changes…</summary>")
        $out.Add('')
        for ($i = $maxPerSection; $i -lt $bucket.Count; $i++) {
            $formatted = Get-FormattedItem $bucket[$i] $Repo
            $out.Add("- $formatted")
        }
        $out.Add('')
        $out.Add("</details>")
    } else {
        foreach ($item in $bucket) {
            $formatted = Get-FormattedItem $item $Repo
            $out.Add("- $formatted")
        }
    }
    $out.Add('')
}

if (-not $hasAny) {
    $out.Add('> *No categorised changes found in this release.*')
    $out.Add('> Most commits were maintenance, dependency updates, or automated changes.')
    $out.Add('')
}

$range = if ($FromTag) { "${FromTag}..HEAD" } else { 'all history' }
$out.Add('---')

if ($totalRaw -gt 0) {
    $out.Add("*$filteredCount significant changes from $totalRaw total commits since ``$FromTag``.*")
} else {
    $out.Add("*Changelog generated from ``$range``.*")
}

Write-Output ($out -join "`n")
