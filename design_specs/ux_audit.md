# UX/UI Audit: CAPP Autonomous Treasury

## Executive Summary
**Current State**: The interface is currently a "functional dashboard" that exposes all capabilities simultaneously. It suffers from **Choice Overload** and **Split Attention**.
**Verdict**: The UI tells the user "Here are tools, you do the work," which contradicts the value proposition of an *Autonomous* Agent.
**Recommendation**: Shift from a "Dashboard" metaphor to a "Cockpit" or "Feed-First" metaphor. The AI should be the protagonist, not a sidebar widget.

---

## The Critique

### 1. Competing Calls to Action (CTA)
**Problem**: The user is bombarded with options immediately.
- **Top**: Autonomy Dial (Critical Control).
- **Middle**: Deposit, Withdraw, Bridge, Settings (Quick Actions).
- **Bottom**: A full Transfer Form (Manual Input).
- **Side**: specific AI prompt buttons (Risk Check, Yield Scan).

**Impact**: The user doesn't know if they should be driving (using forms/buttons) or watching (looking at the feed/radar).

### 2. The "Feed" is Marginalized
**Problem**: The `AiPanel` (the "Brain" of the system) is confined to a narrow 380px sidebar.
**Impact**: If the system is "Autonomous", the *Activity* is the most interesting part. Creating a "Glass Box" experience requires the transparency (the Feed) to be central, not peripheral.

### 3. Redundant Navigation
**Problem**:
- "Bridge" exists as a Quick Action button in `TreasuryCard`.
- "Bridge" exists as a Tab toggle below `TreasuryCard`.
- "TransferForm" is permanently visible, pushing the content down.

### 4. Visual Density
**Problem**: `TreasuryCard` tries to do too much. It displays:
- Total Balance (Good).
- 4-Grid Asset Allocation (Heavy).
- 4 Quick Action Buttons (Heavy).
This pushes the actual "Work" (Bridge/Transfer) below the fold on smaller screens.

---

## Reconstruction Options

### Option A: "The Co-Pilot Cockpit" (Evolution)
*Refine the current layout to create clear hierarchy.*

**Key Changes**:
1.  **Hide the Transfer Form**: Move "Transfer" to a Modal, triggered by a "Send" button in Quick Actions.
2.  **Unified Action Bar**: Treasury Card only shows Balance + Net Worth Graph. The "Grid" of assets moves to a "Portfolio" tab.
3.  **Expanded Feed**: The AI Feed takes up the vertical space gained by hiding the Transfer Form.
4.  **Clear Modes**: When in `SOVEREIGN` mode, manual controls (Transfer/Bridge) dim or collapse, highlighting the Feed.

**Pros**: Familiar dashboard feel. Low engineering lift.
**Cons**: Still feels like a traditional dApp.

### Option B: "The Glass Terminal" (Revolution)
*The AI is the interface. The user chats/commands.*

**Key Changes**:
1.  **Feed is Hero**: The Main View is the AI Timeline (Chat + Activities mixed).
2.  **Command Line**: Instead of a Transfer Form, the user types "Send 500 USDC to Alice". The AI parses this and presents a "Permission Card" for confirmation.
3.  **Floating Wallet**: Balance is a compact pill in the corner.
4.  **Autonomy Dial**: Remains the centerpiece header.

**Pros**: Feels truly agentic and futuristic. Aligns with "Command & Control".
**Cons**: Higher cognitive load for users who prefer clicking buttons.

### Option C: "Focus Mode" (Minimalist)
*Boring is better. Trust requires calm.*

**Key Changes**:
1.  **The "Pulse" View**: The screen shows only *one* thing by default: The Current System Status (e.g., "System Healthy. 3 Transactions Pending").
2.  **Progressive Disclosure**:
    - Clicking "Assets" reveals the Treasury Card.
    - Clicking "Activity" reveals the Feed.
    - Clicking "Controls" reveals Autonomy Dial.
3.  **Intervention-Based**: The UI is silent unless the AI needs help (Copilot Mode). When a Permission Card generates, it takes over the screen.

**Pros**: Extremely premium, high-trust feel.
**Cons**: Hard to debug/monitor at a glance.

---

## Recommendation
**Adopt Option A (The Co-Pilot Cockpit)** as the immediate step to clean up the noise, but borrow **Command Line** elements from Option B for the Transfer flow.

**Immediate Next Steps**:
1.  **Hide `TransferForm`**: Move it to a `TransferModal`.
2.  **Dedup Navigation**: Remove the "Bridge" tab. Make the "Bridge" button open a `BridgeModal` (already exists in code but unused in main view?).
3.  **Centralize Feed**: if possible, allow the Feed to expand or switch the layout so Feed is Left (Main) and Wallet is Right (Side) when in Sovereign Mode.
