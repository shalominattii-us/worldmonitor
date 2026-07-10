class CybergeneticRegistrationStrand {
    [string]$StrandId
    [string]$Name
    [string]$Domain
    [string]$Purpose
    [string]$Authority
    [string]$Class
    [string]$Phase
    [string[]]$Inputs
    [string[]]$Outputs
    [string[]]$Controls
    [string[]]$Evidence
    [string[]]$Lineage
    [datetime]$GeneratedAt

    CybergeneticRegistrationStrand() {
        $this.StrandId = [guid]::NewGuid().ToString()
        $this.Authority = "CANONICAL_PRIME_PRIORITY"
        $this.Class = "RAW_BUILD"
        $this.Phase = "respect"
        $this.GeneratedAt = [datetime]::UtcNow
    }

    [hashtable] ToHashtable() {
        return @{
            strand_id = $this.StrandId
            name = $this.Name
            domain = $this.Domain
            purpose = $this.Purpose
            authority = $this.Authority
            class = $this.Class
            phase = $this.Phase
            inputs = $this.Inputs
            outputs = $this.Outputs
            controls = $this.Controls
            evidence = $this.Evidence
            lineage = $this.Lineage
            generated_at = $this.GeneratedAt.ToString("o")
        }
    }
}

class CanonicalPrimePriorityAuthority {
    [string]$AuthorityId
    [string]$Office
    [string]$Doctrine
    [int]$PriorityLevel
    [string[]]$Controls
    [datetime]$GeneratedAt

    CanonicalPrimePriorityAuthority() {
        $this.AuthorityId = "CANONICAL_PRIME_PRIORITY"
        $this.Office = "SKILL_AUTHORING_AUTHORITY"
        $this.Doctrine = "Heed Canonical Prime Priority. It authors DNA. Respect gives class."
        $this.PriorityLevel = 0
        $this.Controls = @(
            "facts_before_claims",
            "evidence_before_authority",
            "respect_before_money",
            "class_earned_by_proof",
            "operator_execution_required",
            "human_review_required"
        )
        $this.GeneratedAt = [datetime]::UtcNow
    }

    [CybergeneticRegistrationStrand] AuthorStrand(
        [string]$Name,
        [string]$Domain,
        [string]$Purpose,
        [string[]]$Inputs,
        [string[]]$Outputs,
        [string[]]$Controls,
        [string[]]$Evidence
    ) {
        $s = [CybergeneticRegistrationStrand]::new()
        $s.Name = $Name
        $s.Domain = $Domain
        $s.Purpose = $Purpose
        $s.Authority = $this.AuthorityId
        $s.Class = "RAW_BUILD"
        $s.Phase = "respect"
        $s.Inputs = $Inputs
        $s.Outputs = $Outputs
        $s.Controls = $Controls
        $s.Evidence = $Evidence
        $s.Lineage = @(
            "authority:CANONICAL_PRIME_PRIORITY",
            "office:SKILL_AUTHORING_AUTHORITY",
            "doctrine:Respect creates DNA. Class is earned."
        )
        return $s
    }
}

function New-CanonicalPrimePriorityAuthority {
    [CanonicalPrimePriorityAuthority]::new()
}

function New-CanonicalSkillDNA {
    param(
        [Parameter(Mandatory=$true)][string]$SkillName,
        [Parameter(Mandatory=$true)][string]$Domain,
        [Parameter(Mandatory=$true)][string]$Purpose,
        [string[]]$Inputs = @(),
        [string[]]$Outputs = @(),
        [string[]]$Controls = @(),
        [string[]]$Evidence = @(),
        [string]$OutDir = "C:\Users\eagle\code\worldmonitor\cybercore\skill_authoring_authority\dna"
    )

    $authority = [CanonicalPrimePriorityAuthority]::new()

    $baseControls = @(
        "canonical_prime_priority_required",
        "respect_gate_required",
        "class_earned_by_score",
        "no_fabricated_capability",
        "no_secret_collection",
        "human_review_required"
    )

    $mergedControls = @($baseControls + $Controls | Select-Object -Unique)

    $strand = $authority.AuthorStrand(
        $SkillName,
        $Domain,
        $Purpose,
        $Inputs,
        $Outputs,
        $mergedControls,
        $Evidence
    )

    New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

    $slug = ($SkillName.ToLower() -replace '[^a-z0-9]+','-').Trim('-')
    if ([string]::IsNullOrWhiteSpace($slug)) { $slug = "skill-dna" }

    $out = Join-Path $OutDir "$slug.skill_dna.json"

    $dna = [ordered]@{
        ok = $true
        generated_at = (Get-Date).ToString("o")
        authority = "CANONICAL_PRIME_PRIORITY"
        office = "SKILL_AUTHORING_AUTHORITY"
        doctrine = "Heed Canonical Prime Priority. It authors DNA. Respect gives class."
        skill_name = $SkillName
        domain = $Domain
        purpose = $Purpose
        dna_strands = $strand.ToHashtable()
        class = @{
            initial = "RAW_BUILD"
            earned = "RAW_BUILD"
            promotion_rule = "Promotion requires respect score and evidence."
        }
        phase = @{
            current = "respect"
            money_unlocked = $false
            operator_required = $true
        }
        controls = $mergedControls
        output_path = $out
    }

    $dna | ConvertTo-Json -Depth 80 | Set-Content $out -Encoding UTF8

    return [pscustomobject]@{
        ok = $true
        skill_name = $SkillName
        authority = "CANONICAL_PRIME_PRIORITY"
        class = "RAW_BUILD"
        phase = "respect"
        dna_path = $out
    }
}

function Register-CanonicalSkillDNA {
    param(
        [Parameter(Mandatory=$true)][string]$DnaPath,
        [string]$RegistryDir = "C:\Users\eagle\code\worldmonitor\cybercore\skill_authoring_authority\registry"
    )

    if (-not (Test-Path $DnaPath)) {
        throw "DNA path not found: $DnaPath"
    }

    New-Item -ItemType Directory -Force -Path $RegistryDir | Out-Null

    $dna = Get-Content $DnaPath -Raw | ConvertFrom-Json
    if ($dna.authority -ne "CANONICAL_PRIME_PRIORITY") {
        throw "Rejected: DNA is not authored by CANONICAL_PRIME_PRIORITY."
    }

    $registryPath = Join-Path $RegistryDir "skill_dna_registry.jsonl"

    $record = [ordered]@{
        registered_at = (Get-Date).ToString("o")
        authority = $dna.authority
        office = $dna.office
        skill_name = $dna.skill_name
        domain = $dna.domain
        class = $dna.class.initial
        phase = $dna.phase.current
        dna_path = $DnaPath
        valid = $true
    }

    Add-Content -Path $registryPath -Value ($record | ConvertTo-Json -Depth 30 -Compress) -Encoding UTF8

    return [pscustomobject]@{
        ok = $true
        registered = $true
        registry = $registryPath
        skill_name = $dna.skill_name
        dna_path = $DnaPath
    }
}
