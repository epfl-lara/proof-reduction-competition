theorem InitsUpdatesComm
  {P : PureExpr} {σ σ' σ'' : SemanticStore P}
  {ks ks' : List P.Ident} {vs vs' : List P.Expr} :
  UpdateStates σ ks vs σ' →
  InitStates σ' ks' vs' σ'' →
  ∃ σ₁,
    σ₁ = (updatedStates σ ks' vs') ∧
    InitStates σ ks' vs' σ₁ ∧
    UpdateStates σ₁ ks vs σ'' := by
  intro Hup Hinit
  refine ⟨updatedStates σ ks' vs', rfl, ?_, ?_⟩
  · exact updatedStatesInit (InitStatesLength Hinit)
      (UpdateStatesNotDefMonotone' (InitStatesNotDefined Hinit) Hup)
      (InitStatesNodup Hinit)
  · have Hdis : ks.Disjoint ks' := by
      intro k hk hk'
      have hdef := UpdateStatesDefined Hup k hk
      have hnone := InitStatesNotDefined Hinit k hk'
      simp_all
    have Hdis' : (ks.zip vs).unzip.1.Disjoint (ks'.zip vs').unzip.1 := by
      simpa only [List.unzip_zip (UpdateStatesLength Hup),
        List.unzip_zip (InitStatesLength Hinit)] using Hdis
    have Hcomm : updatedStates (updatedStates σ ks vs) ks' vs' =
        updatedStates (updatedStates σ ks' vs') ks vs := by
      simpa [updatedStates] using (updatedStatesComm (σ:=σ) Hdis')
    have Hdef : isDefined (updatedStates σ ks' vs') ks := by
      unfold updatedStates
      exact updatedStatesDefMonotone (UpdateStatesDefined' Hup)
    have Hupd : UpdateStates (updatedStates σ ks' vs') ks vs
        (updatedStates (updatedStates σ ks' vs') ks vs) :=
      updatedStatesUpdate (UpdateStatesLength Hup) Hdef
    have Hfinal : updatedStates (updatedStates σ ks' vs') ks vs = σ'' := by
      rw [InitStatesUpdated Hinit, UpdateStatesUpdated Hup]
      exact Hcomm.symm
    exact Hfinal ▸ Hupd
