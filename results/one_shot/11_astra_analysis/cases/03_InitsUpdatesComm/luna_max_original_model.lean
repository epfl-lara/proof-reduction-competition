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
  · have Hdisj : (ks.zip vs).unzip.1.Disjoint (ks'.zip vs').unzip.1 := by
      rw [List.unzip_zip (UpdateStatesLength Hup),
        List.unzip_zip (InitStatesLength Hinit)]
      intro x hx hx'
      have hsome := UpdateStatesDefined Hup x hx
      have hnone := InitStatesNotDefined Hinit x hx'
      simp [isDefined, hnone] at hsome
    have Hdef : isDefined (updatedStates σ ks' vs') ks := by
      simpa [updatedStates] using
        (updatedStatesDefMonotone (σ := σ) (vs := ks)
          (ves := ks'.zip vs') (UpdateStatesDefined' Hup))
    have Hrun := updatedStatesUpdate (UpdateStatesLength Hup) Hdef
    have Hcomm := updatedStatesComm (σ := σ) Hdisj
    have Hcomm' : updatedStates (updatedStates σ ks vs) ks' vs' =
        updatedStates (updatedStates σ ks' vs') ks vs := by
      simpa [updatedStates] using Hcomm
    have Hfinal : σ'' = updatedStates (updatedStates σ ks' vs') ks vs := by
      rw [InitStatesUpdated Hinit, UpdateStatesUpdated Hup]
      exact Hcomm'
    rw [Hfinal]
    exact Hrun
