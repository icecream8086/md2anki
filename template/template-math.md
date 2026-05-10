> 提示：笔记内容请用中文撰写，模板中的英文仅为格式示例。

# Calculus I

## Power Rule

$$
\frac{d}{dx} x^n = n \cdot x^{n-1}
$$

Derivation from first principles:

$$
\begin{aligned}
\frac{d}{dx} x^n &= \lim_{h \to 0} \frac{(x+h)^n - x^n}{h} \\
&= \lim_{h \to 0} \frac{x^n + n x^{n-1}h + \binom{n}{2} x^{n-2}h^2 + \cdots - x^n}{h} \\
&= \lim_{h \to 0} \left( n x^{n-1} + \binom{n}{2} x^{n-2}h + \cdots \right) \\
&= n x^{n-1}
\end{aligned}
$$

The AI will turn the derivation steps into a **math** card with 4 step cards
(Step1 → Step2 → Step3 → Step4).

### Examples

| Function | Derivative |
|---|---|
| $x^5$ | $5x^4$ |
| $x^{-2}$ | $-2x^{-3}$ |
| $x^{1/2}$ | $\frac{1}{2} x^{-1/2}$ |

## Chain Rule

$$
\frac{d}{dx} f(g(x)) = f'(g(x)) \cdot g'(x)
$$

$$
\frac{d}{dx} \sin(x^2) = \cos(x^2) \cdot 2x = 2x \cos(x^2)
$$

### Animated step-by-step

```mermaid
graph LR
    A[sin(x²)] --> B[cos(x²) · d/dx x²]
    B --> C[cos(x²) · 2x]
    C --> D[2x cos(x²)]
```

---

## Set Theory

### Venn: Union and Intersection

| Symbol | Meaning | Example |
|---|---|---|
| $A \cup B$ | Union — elements in A or B | $\{1,2\} \cup \{2,3\} = \{1,2,3\}$ |
| $A \cap B$ | Intersection — elements in both | $\{1,2\} \cap \{2,3\} = \{2\}$ |
| $A \setminus B$ | Difference — in A but not B | $\{1,2\} \setminus \{2,3\} = \{1\}$ |

### De Morgan's Laws

$$
\overline{A \cup B} = \overline{A} \cap \overline{B}
$$
$$
\overline{A \cap B} = \overline{A} \cup \overline{B}
$$
