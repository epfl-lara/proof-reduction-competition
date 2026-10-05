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
  · have hlen := UpdateStatesLength Hup
    have hdisj : (ks.zip vs).unzip.1.Disjoint (ks'.zip vs').unzip.1 := by
      rw [List.unzip_zip (UpdateStatesLength Hup),
        List.unzip_zip (InitStatesLength Hinit)]
      intro k hk hk'
      simpa [InitStatesNotDefined Hinit k hk'] using
        UpdateStatesDefined Hup k hk
    have hcomm := updatedStatesComm (σ := σ) hdisj
    have heq : updatedStates (updatedStates σ ks' vs') ks vs = σ'' := by
      rw [InitStatesUpdated Hinit, UpdateStatesUpdated Hup]
      simpa [updatedStates] using hcomm.symm
    rw [← heq]
    exact updatedStatesUpdate hlen (updatedStatesDefMonotone (UpdateStatesDefined' Hup))