import numpy as np
import matplotlib.pyplot as plt
import streamlit as st

st.title("Seasonal Cycle Phase Explorer")
st.caption("Drag the sliders — the plot updates instantly.")

st.markdown(r"""
$$\beta \cos\!\left(\tfrac{2\pi t}{52}\right) + \gamma \sin\!\left(\tfrac{2\pi t}{52}\right) = A \cos\!\left(\tfrac{2\pi t}{52} - \phi\right)$$

- $A = \sqrt{\beta^2 + \gamma^2}$ — amplitude
- $\phi = \arctan2(\gamma, \beta)$ — phase
- $t^* = \frac{52}{2\pi}\,\phi \mod 52$ — peak week
""")

st.divider()

# --- sliders + live metrics side by side ---
left, right = st.columns([2, 1])
with left:
    beta  = st.slider("β (cosine weight)", min_value=-2.0, max_value=2.0, value=1.0, step=0.05)
    gamma = st.slider("γ (sine weight)",   min_value=-2.0, max_value=2.0, value=0.0, step=0.05)
with right:
    A         = np.sqrt(beta**2 + gamma**2)
    phi       = np.arctan2(gamma, beta)
    peak_week = (52 / (2 * np.pi) * phi) % 52
    st.metric("Amplitude A", f"{A:.3f}")
    st.metric("Phase φ (rad)", f"{phi:.3f}")
    st.metric("Peak week t*", f"{peak_week:.1f}")

# --- plot ---
t = np.linspace(0, 52, 500)
omega = 2 * np.pi / 52
y = beta * np.cos(omega * t) + gamma * np.sin(omega * t)
true_peak = t[np.argmax(y)] % 52

phi_slides        = np.arctan2(-gamma, beta)
peak_slides_wrong = ( 52 / (2 * np.pi) * phi_slides) % 52
peak_slides_right = (-52 / (2 * np.pi) * phi_slides) % 52

fig, ax = plt.subplots(figsize=(9, 3.5))
ax.plot(t, y, linewidth=2, color="steelblue")
ax.axvline(true_peak,         color="black",  linewidth=2,   linestyle="-",  label=f"true peak — wk {true_peak:.1f}")
ax.axvline(peak_week,         color="green",  linewidth=2,   linestyle="--", label=f"arctan2( γ, β) +ve → wk {peak_week:.1f} ✓")
ax.axvline(peak_slides_wrong, color="red",    linewidth=2,   linestyle="--", label=f"arctan2(-γ, β) +ve → wk {peak_slides_wrong:.1f} ✗")
ax.axvline(peak_slides_right, color="orange", linewidth=1.5, linestyle=":",  label=f"arctan2(-γ, β) -ve → wk {peak_slides_right:.1f} ✓")
ax.axhline(0, color="grey", linewidth=0.8, linestyle=":")
ax.set_xlabel("Week (t)")
ax.set_ylabel("Value")
ax.set_xlim(-2, 54)
ax.set_xticks([0, 13, 26, 39, 52])
ax.set_xticklabels(["0\n(Jan)", "13\n(Apr)", "26\n(Jul)", "39\n(Oct)", "52\n(Jan)"])
ax.legend(fontsize=8.5, loc="lower right")
plt.tight_layout()
st.pyplot(fig)

# --- explanation after plot ---
st.divider()
st.markdown("**What the lines mean:**")
st.markdown(r"""
| Line | Formula | Conversion | Correct? |
|---|---|---|---|
| Green | $\arctan2(\gamma, \beta)$ | $+\frac{52}{2\pi}\phi$ | ✓ peak |
| Red | $\arctan2(-\gamma, \beta)$ | $+\frac{52}{2\pi}\phi$ | ✗ wrong week |
| Orange | $\arctan2(-\gamma, \beta)$ | $-\frac{52}{2\pi}\phi$ | ✓ peak |

- Lecture slides use the **red formula** — valid, but requires a **negative** conversion (orange) to recover the peak
- Using the red formula with a positive conversion gives a wrong week (not the peak, not reliably the trough)
""")
st.info("Try β = 0, γ = 1 — peak should be week 13 (Apr). Red lands on week 39.")
