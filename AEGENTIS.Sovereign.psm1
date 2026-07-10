function New-AEGENTISPlatform {
    $planes = @(
        [pscustomobject]@{ Name="Identity Plane"; Owner="Identity Service"; Boundary="Does not store money or private keys." }
        [pscustomobject]@{ Name="Treasury Plane"; Owner="Treasury Service"; Boundary="Does not authenticate users or hold private keys." }
        [pscustomobject]@{ Name="Key Plane"; Owner="Key Service"; Boundary="Does not expose private keys." }
        [pscustomobject]@{ Name="Commerce Plane"; Owner="Commerce Service"; Boundary="Does not move funds directly." }
        [pscustomobject]@{ Name="Execution Plane"; Owner="Runtime Service"; Boundary="Instruction execution remains policy-gated." }
        [pscustomobject]@{ Name="Lineage Plane"; Owner="Lineage Service"; Boundary="Does not bypass governance." }
        [pscustomobject]@{ Name="Governance Plane"; Owner="Policy Service"; Boundary="Controls cross-plane authority." }
        [pscustomobject]@{ Name="Observability Plane"; Owner="Telemetry Service"; Boundary="Read-mostly monitoring boundary." }
        [pscustomobject]@{ Name="Civilization Plane"; Owner="Civilization Registry"; Boundary="Top-level registry, not a secret store." }
    )

    [pscustomobject]@{
        Name = "AEGENTIS Sovereign Platform"
        Mode = "healthy_functional"
        SafetyBoundary = "active"
        Planes = $planes
    }
}

function Get-AEGENTISTopology {
    (New-AEGENTISPlatform).Planes
}

Export-ModuleMember -Function New-AEGENTISPlatform,Get-AEGENTISTopology