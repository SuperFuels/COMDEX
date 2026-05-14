/-
V40 — Correlation over two delta streams (no materialization) (workspace bridge)

Buyer line:
  "Correlation / covariance maintained directly from two delta streams; no snapshot materialization."

This file is intentionally light: it expresses the semantic update identities that any
stream-maintained correlation implementation must satisfy.
-/

namespace SymaticsBridge.V40

/-- A vector is a total map Nat -> Int. -/
def Vec := Nat → Int

/-- Point-set update: set x[idx] := v. -/
def setAt (x : Vec) (idx : Nat) (v : Int) : Vec :=
  fun i => if i = idx then v else x i

/-- Finite sum over indices 0..n-1 (semantic). -/
def sumN (n : Nat) (f : Nat → Int) : Int :=
  (List.range n).foldl (fun acc i => acc + f i) 0

def Sx  (n : Nat) (x : Vec) : Int := sumN n (fun i => x i)
def Sy  (n : Nat) (y : Vec) : Int := sumN n (fun i => y i)
def Sxx (n : Nat) (x : Vec) : Int := sumN n (fun i => (x i) * (x i))
def Syy (n : Nat) (y : Vec) : Int := sumN n (fun i => (y i) * (y i))
def Sxy (n : Nat) (x y : Vec) : Int := sumN n (fun i => (x i) * (y i))

/-
Semantic update identities (the contract).
-/

theorem Sx_update_identity
  (n idx : Nat) (x : Vec) (old new : Int)
  (hOld : x idx = old) :
  Sx n (setAt x idx new)
    =
  Sx n x + (if idx < n then (new - old) else 0) := by
  simp [Sx, sumN, setAt, hOld]

theorem Sy_update_identity
  (n idx : Nat) (y : Vec) (old new : Int)
  (hOld : y idx = old) :
  Sy n (setAt y idx new)
    =
  Sy n y + (if idx < n then (new - old) else 0) := by
  simp [Sy, sumN, setAt, hOld]

theorem Sxx_update_identity
  (n idx : Nat) (x : Vec) (old new : Int)
  (hOld : x idx = old) :
  Sxx n (setAt x idx new)
    =
  Sxx n x + (if idx < n then (new*new - old*old) else 0) := by
  simp [Sxx, sumN, setAt, hOld]

theorem Syy_update_identity
  (n idx : Nat) (y : Vec) (old new : Int)
  (hOld : y idx = old) :
  Syy n (setAt y idx new)
    =
  Syy n y + (if idx < n then (new*new - old*old) else 0) := by
  simp [Syy, sumN, setAt, hOld]

theorem Sxy_update_identity_x
  (n idx : Nat) (x y : Vec) (old new : Int)
  (hOld : x idx = old) :
  Sxy n (setAt x idx new) y
    =
  Sxy n x y + (if idx < n then ((new - old) * (y idx)) else 0) := by
  simp [Sxy, sumN, setAt, hOld]

theorem Sxy_update_identity_y
  (n idx : Nat) (x y : Vec) (old new : Int)
  (hOld : y idx = old) :
  Sxy n x (setAt y idx new)
    =
  Sxy n x y + (if idx < n then ((x idx) * (new - old)) else 0) := by
  simp [Sxy, sumN, setAt, hOld]

/-- Pearson numerator (integer form). -/
def pearsonNum (n : Nat) (x y : Vec) : Int :=
  (Int.ofNat n) * (Sxy n x y) - (Sx n x) * (Sy n y)

/-- Pearson denominator-squared (integer form; avoids sqrt). -/
def pearsonDen2 (n : Nat) (x y : Vec) : Int :=
  let nI : Int := Int.ofNat n
  let a : Int := nI * (Sxx n x) - (Sx n x) * (Sx n x)
  let b : Int := nI * (Syy n y) - (Sy n y) * (Sy n y)
  a * b

end SymaticsBridge.V40