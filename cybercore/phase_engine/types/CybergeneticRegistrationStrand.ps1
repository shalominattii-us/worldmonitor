class CybergeneticRegistrationStrand {
    [string]$Id
    [string]$Name
    [string]$Class
    [string]$Phase
    [string]$Doctrine
    [string[]]$Strands
    [hashtable]$Evidence
    [hashtable]$Controls
    [datetime]$GeneratedAt

    CybergeneticRegistrationStrand() {
        $this.Id = [guid]::NewGuid().ToString()
        $this.Name = "respect-dna-registration"
        $this.Class = "UNCLASSIFIED"
        $this.Phase = "respect"
        $this.Doctrine = "Respect produces DNA. Class is earned."
        $this.Strands = @("proof","discipline","utility","trust","class")
        $this.Evidence = @{}
        $this.Controls = @{
            human_review_required = $true
            no_fabricated_evidence = $true
            no_secret_collection = $true
            operator_required = $true
        }
        $this.GeneratedAt = [datetime]::UtcNow
    }

    CybergeneticRegistrationStrand(
        [string]$Name,
        [string]$Class,
        [string]$Phase,
        [string[]]$Strands
    ) {
        $this.Id = [guid]::NewGuid().ToString()
        $this.Name = $Name
        $this.Class = $Class
        $this.Phase = $Phase
        $this.Doctrine = "Respect produces DNA. Class is earned."
        $this.Strands = $Strands
        $this.Evidence = @{}
        $this.Controls = @{
            human_review_required = $true
            no_fabricated_evidence = $true
            no_secret_collection = $true
            operator_required = $true
        }
        $this.GeneratedAt = [datetime]::UtcNow
    }

    [hashtable] ToHashtable() {
        return @{
            id = $this.Id
            name = $this.Name
            class = $this.Class
            phase = $this.Phase
            doctrine = $this.Doctrine
            strands = $this.Strands
            evidence = $this.Evidence
            controls = $this.Controls
            generated_at = $this.GeneratedAt.ToString("o")
        }
    }
}
