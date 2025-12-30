# Design Concept: The Protocol of Delegation
**"From Settings to Sovereignty"**

## First Principles & Jobs to be Done (JTBD)

In a fintech context where real money is at risk, the user's relationship with an Agent is not User<->Tool, but **Owner<->Manager**.

1.  **Job 1: "Let me sleep at night" (Safety & Trust)**
    *   *Friction:* Fear of limits being ignored or bugs draining wallets.
    *   *Solution:* **Hardened Constraints**. The UI must visually demonstrate boundaries (limits) that felt "locked" and immutable by the agent.

2.  **Job 2: "Amplify my intent" (leverage)**
    *   *Friction:* Configuring 50 complex parameters (slippage, gas, alpha threshold).
    *   *Solution:* **Intent-Based Directives**. "Preserve Capital" vs "Yield Hunt". The Agent translates Intent -> Parameters.

3.  **Job 3: "Keep me in the loop" (Supervision)**
    *   *Friction:* Silent failures or silent actions.
    *   *Solution:* **The Permission Protocol**. Agents shouldn't just "do" or "don't". When they hit a threshold (confidence or budget), they should **Ask**.

## The Ideal Experience: "The Autonomy Dial"

Instead of a binary "On/Off" switch, we present **Levels of Autonomy**. This mental model borrows from Self-Driving Cars (L1-L5).

### 1. The Interaction Model
A centralized "Command Center" where the user defines the **Contract** for each agent.

*   **Level 0: Paused.** (Manual Mode). Agent does nothing.
*   **Level 1: Copilot.** (Advisory). Agent scans, analyzes, and *Suggests* actions in the feed. User must click "Approve" for *everything*.
*   **Level 2: Guarded.** (Bounded Autonomy). Agent executes low-risk actions (e.g., < $100 rebalance) automatically. High-risk actions triggers a **Permission Card**.
*   **Level 3: Sovereign.** (Full Autonomy). Agent executes broadly within daily limits. Only notifies after the fact.

### 2. The "Signing Ceremony" UX
Changing autonomy isn't a toggle. It's a **state change**.
*   When moving from *Copilot* -> *Sovereign*, the UI should present a "Contract" modal.
*   "You are authorizing `LiquidityAgent` to spend up to $5,000/day."
*   User must "Sign" (symbolically or cryptographically). This builds immense trust because the delegation is explicit.

### 3. "Permission Cards" (The Logic of Interruption)
The Feed shouldn't just be text. It should contain interactive **Permission Cards**.
*   *Scenario:* Agent sees a huge yield op, but it requires bridging $10k (over its limit).
*   *UI:* A glowing card appears: "🚀 High Yield Opportunity Detected. Requires $10k Bridge. Confidence: 92%. [Approve One-Time Override] [Dismiss]"
*   This transforms the "Error" (Limit Reached) into a "Management Decision".

## Visual Direction
*   **Visual Metaphor**: "The Leash" or "The Shield". Color changes based on autonomy level (Blue = Safe/Copilot, Orange = Sovereign/Active).
*   **Haptic/Sonic**: "Signing" a new autonomy level should have a satisfying sound/animation, reinforcing the weight of the decision.
