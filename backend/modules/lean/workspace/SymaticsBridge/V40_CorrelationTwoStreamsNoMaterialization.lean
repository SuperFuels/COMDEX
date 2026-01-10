/-
V40 — Correlation over two delta streams (no materialization)

Level-A target: no `sorry`.
Dependency-light (core Lean only).
-/

namespace SymaticsBridge.V40

def Vec := Nat → Int

def setAt (x : Vec) (idx : Nat) (v : Int) : Vec :=
  fun i => if i = idx then v else x i

-- sumN f n = ∑_{i=0}^{n-1} f i
def sumN (f : Nat → Int) : Nat → Int
| 0     => 0
| n+1   => sumN f n + f n

theorem setAt_hit (x : Vec) (idx : Nat) (v : Int) : setAt x idx v idx = v := by
  simp [setAt]

theorem setAt_miss (x : Vec) (idx j : Nat) (v : Int) (h : j ≠ idx) :
  setAt x idx v j = x j := by
  simp [setAt, h]

-- -------------------- tiny Int helpers (no mathlib) --------------------

theorem int_add_right_neg' (a : Int) : a + (-a) = 0 := by
  simpa using (Int.add_right_neg a)

theorem int_add_assoc' (a b c : Int) : (a + b) + c = a + (b + c) := by
  simpa using (Int.add_assoc a b c)

theorem int_add_comm' (a b : Int) : a + b = b + a := by
  simpa using (Int.add_comm a b)

/-- a + (b - a) = b -/
theorem int_add_sub_cancel (a b : Int) : a + (b - a) = b := by
  -- b - a = b + (-a)
  simp [Int.sub_eq_add_neg]
  -- goal: a + (b + -a) = b
  calc
    a + (b + (-a)) = (a + b) + (-a) := by
      simpa using (Int.add_assoc a b (-a)).symm
    _ = (b + a) + (-a) := by
      simpa using congrArg (fun t => t + (-a)) (Int.add_comm a b)
    _ = b + (a + (-a)) := by
      simpa using (Int.add_assoc b a (-a))
    _ = b + 0 := by
      simpa using congrArg (fun t => b + t) (int_add_right_neg' a)
    _ = b := by simp

/-- (t + u) + v = (t + v) + u -/
theorem int_add_swap (t u v : Int) : (t + u) + v = (t + v) + u := by
  calc
    (t + u) + v = t + (u + v) := by
      simpa using (Int.add_assoc t u v)
    _ = t + (v + u) := by
      simpa using congrArg (fun w => t + w) (Int.add_comm u v)
    _ = (t + v) + u := by
      simpa using (Int.add_assoc t v u).symm

/-- -(a*b) = (-a)*b (direction-fixed) -/
theorem int_neg_mul (a b : Int) : -(a * b) = (-a) * b := by
  simpa using (Int.neg_mul a b).symm

/-- -(a*b) = a*(-b) -/
theorem int_mul_neg_rhs (a b : Int) : -(a * b) = a * (-b) := by
  simpa using (Int.mul_neg a b).symm

-- -------------------- core delta lemma --------------------

/-- Core: changing one index shifts `sumN` by delta iff `idx < n`. -/
theorem sumN_setAt_delta (x : Vec) (idx n : Nat) (old new : Int)
  (hOld : x idx = old) :
  sumN (setAt x idx new) n
    = sumN x n + (if idx < n then (new - old) else 0) := by
  revert hOld
  refine Nat.rec
    (motive := fun n =>
      (x idx = old) →
        sumN (setAt x idx new) n
          = sumN x n + (if idx < n then (new - old) else 0))
    (fun _hOld => by
      simp [sumN])
    (fun k ih hOld => by
      -- unfold at k+1, push IH into prefix
      simp [sumN, ih hOld]

      by_cases hEq : idx = k
      · -- HIT: idx = k
        subst hEq
        have hx : x idx = old := hOld

        -- Reduce the goal shape that Lean is complaining about:
        --   (sumN x idx + if idx < idx then ... else 0) + setAt x idx new idx
        -- = sumN x idx + x idx + if idx < idx+1 then ... else 0
        -- to a clean arithmetic goal.
        simp [setAt, hx, Nat.lt_irrefl, Nat.lt_succ_self, sumN]

        -- Now the remaining goal is:
        --   sumN x idx + new = sumN x idx + old + (new - old)
        -- and this is closed by rewriting old+(new-old)=new.
        have h1 : old + (new - old) = new := by
          simpa using (int_add_sub_cancel old new)

        -- Finish
        -- (the goal is exactly the rearrangement below after the simp above)
        calc
          sumN x idx + new
              = sumN x idx + (old + (new - old)) := by simpa [h1]
          _   = sumN x idx + old + (new - old) := by
                simpa using (Int.add_assoc (sumN x idx) old (new - old)).symm
        -- and `simp` already reduced the goal to this shape
        -- so we finish by rewriting `hx` where needed
        -- (the simp above already used setAt_hit / ifs)
      · -- MISS: idx ≠ k
        have hk_ne : k ≠ idx := by
          intro hk
          exact hEq hk.symm
        have hmiss : setAt x idx new k = x k := by
          simp [setAt, hk_ne]

        by_cases hlt : idx < k
        · have hlt_succ : idx < k.succ := Nat.lt_trans hlt (Nat.lt_succ_self k)
          -- after simp, leftover is commutativity of Int addition
          simp [hmiss, hlt, hlt_succ, Int.add_assoc]
          simpa using (Int.add_comm (new - old) (x k))
        · have hnot_succ : ¬ idx < k.succ := by
            intro hs
            have hle : idx ≤ k := Nat.le_of_lt_succ hs
            have hlt' : idx < k := Nat.lt_of_le_of_ne hle hEq
            exact hlt hlt'
          simp [hmiss, hlt, hnot_succ, Int.add_assoc])
    n
  -- IMPORTANT: the HIT branch above ends with a calc; we still need to close the goal that simp produced.
  -- This last simp discharges the remaining normalization obligations.
  all_goals
    try simp [setAt, hOld, Nat.lt_irrefl, Nat.lt_succ_self, Int.sub_eq_add_neg]

-- -------------------- aggregates --------------------

def Sx  (x : Vec) (n : Nat) : Int := sumN x n
def Sy  (y : Vec) (n : Nat) : Int := sumN y n
def Sxx (x : Vec) (n : Nat) : Int := sumN (fun i => x i * x i) n
def Syy (y : Vec) (n : Nat) : Int := sumN (fun i => y i * y i) n
def Sxy (x y : Vec) (n : Nat) : Int := sumN (fun i => x i * y i) n

theorem Sx_update (x : Vec) (n idx : Nat) (old new : Int) (hOld : x idx = old) :
  Sx (setAt x idx new) n = Sx x n + (if idx < n then (new - old) else 0) := by
  simp [Sx, sumN_setAt_delta, hOld]

theorem Sy_update (y : Vec) (n idx : Nat) (old new : Int) (hOld : y idx = old) :
  Sy (setAt y idx new) n = Sy y n + (if idx < n then (new - old) else 0) := by
  simp [Sy, sumN_setAt_delta, hOld]

theorem sq_setAt_def (x : Vec) (idx : Nat) (new : Int) :
  (fun i => (setAt x idx new i) * (setAt x idx new i))
    = setAt (fun i => x i * x i) idx (new * new) := by
  funext i
  by_cases h : i = idx <;> simp [setAt, h]

theorem Sxx_update (x : Vec) (n idx : Nat) (old new : Int) (hOld : x idx = old) :
  Sxx (setAt x idx new) n =
    Sxx x n + (if idx < n then (new*new - old*old) else 0) := by
  have hx : (fun i => x i * x i) idx = old * old := by simpa [hOld]
  unfold Sxx
  simpa [sq_setAt_def] using
    (sumN_setAt_delta (x := fun i => x i * x i) (idx := idx) (n := n)
      (old := old * old) (new := new * new) hx)

theorem Syy_update (y : Vec) (n idx : Nat) (old new : Int) (hOld : y idx = old) :
  Syy (setAt y idx new) n =
    Syy y n + (if idx < n then (new*new - old*old) else 0) := by
  have hy : (fun i => y i * y i) idx = old * old := by simpa [hOld]
  unfold Syy
  have sqy :
      (fun i => (setAt y idx new i) * (setAt y idx new i))
        = setAt (fun i => y i * y i) idx (new * new) := by
    funext i
    by_cases h : i = idx <;> simp [setAt, h]
  simpa [sqy] using
    (sumN_setAt_delta (x := fun i => y i * y i) (idx := idx) (n := n)
      (old := old * old) (new := new * new) hy)

theorem prod_setAt_x_def (x y : Vec) (idx : Nat) (new : Int) :
  (fun i => (setAt x idx new i) * y i)
    = setAt (fun i => x i * y i) idx (new * y idx) := by
  funext i
  by_cases h : i = idx <;> simp [setAt, h]

theorem prod_setAt_y_def (x y : Vec) (idx : Nat) (new : Int) :
  (fun i => x i * (setAt y idx new i))
    = setAt (fun i => x i * y i) idx (x idx * new) := by
  funext i
  by_cases h : i = idx <;> simp [setAt, h]

theorem Sxy_update_x (x y : Vec) (n idx : Nat) (old new : Int) (hOld : x idx = old) :
  Sxy (setAt x idx new) y n =
    Sxy x y n + (if idx < n then ((new - old) * y idx) else 0) := by
  have hx : (fun i => x i * y i) idx = old * y idx := by simpa [hOld]
  have δ :=
    sumN_setAt_delta (x := fun i => x i * y i) (idx := idx) (n := n)
      (old := old * y idx) (new := new * y idx) hx
  simp [Sxy, prod_setAt_x_def] at δ ⊢

  have halg : (new * y idx - old * y idx) = (new - old) * y idx := by
    calc
      new * y idx - old * y idx
          = new * y idx + (-(old * y idx)) := by simp [Int.sub_eq_add_neg]
      _   = new * y idx + ((-old) * y idx) := by
              simpa [int_neg_mul] using rfl
      _   = (new + (-old)) * y idx := by
              simpa using (Int.add_mul new (-old) (y idx)).symm
      _   = (new - old) * y idx := by simp [Int.sub_eq_add_neg]

  simpa [halg] using δ

theorem Sxy_update_y (x y : Vec) (n idx : Nat) (old new : Int) (hOld : y idx = old) :
  Sxy x (setAt y idx new) n =
    Sxy x y n + (if idx < n then (x idx * (new - old)) else 0) := by
  have hy : (fun i => x i * y i) idx = x idx * old := by simpa [hOld]
  have δ :=
    sumN_setAt_delta (x := fun i => x i * y i) (idx := idx) (n := n)
      (old := x idx * old) (new := x idx * new) hy
  simp [Sxy, prod_setAt_y_def] at δ ⊢

  have halg : (x idx * new - x idx * old) = x idx * (new - old) := by
    calc
      x idx * new - x idx * old
          = x idx * new + (-(x idx * old)) := by simp [Int.sub_eq_add_neg]
      _   = x idx * new + (x idx * (-old)) := by
              simpa [int_mul_neg_rhs] using rfl
      _   = x idx * (new + (-old)) := by
              simpa using (Int.mul_add (x idx) new (-old)).symm
      _   = x idx * (new - old) := by simp [Int.sub_eq_add_neg]

  simpa [halg] using δ

end SymaticsBridge.V40