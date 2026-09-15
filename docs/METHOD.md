# Method notes

The budget and raid formulas are standard kinematics and independent-trial probability. The DDIL delivery model and the centralised-versus-distributed comparison are first-order models by the author, stated with their assumptions so they can be argued with.

## 01 The loop has a period

Boyd's Observe, Orient, Decide, Act is a loop: output feeds back into input, one turn takes time, and the turn degrades under stress, attack and missing or wrong information. Getting inside an adversary's loop means completing yours faster and more accurately, so they react to a situation you have already changed. Speed without correct orientation is worthless: a fast loop making confident errors loses to a slightly slower loop that is right.

The disciplined claim names the phase it improves. Sensors improve Observe; fusion and the common picture improve Orient; decision support and delegated authority improve Decide; tasking and effectors improve Act. Optimising one fast component inside a chain that is slow elsewhere adds nothing.

## 02 Latency budget and decision margin

```
T_impact = (R_detect − R_min) / v_threat
M        = T_impact − (T_detect + T_track + T_identify + T_decide + T_effect + T_comms)
```

A negative M means the defence cannot act in time, however good any single sensor or effector is.

**Worked example (tested).** A small attack drone at 150 km/h (41.7 m/s), first reliably detected at 2 km, arrives in 48 s. Track confirmation 5 s, slew and positive identification 10 s, decision and authority 20 s, effector activation 5 s: the chain is 40 s and **M = 8 s**. Double the decision to 40 s and M = −12 s. Detected at 3 km the same threat gives 72 s.

**Second example (tested).** A drone detected at 3,000 m, closing at 30 m/s, with a 300 m minimum useful engagement range: 90 s available. Detection 5 s, fusion and identification 20 s, human decision 30 s, effect 10 s, communications hops 15 s: 80 s, margin 10 s. Double the closing speed and the window halves to 45 s; the same loop fails by 35 s.

Two inverse quantities are often more useful than the margin itself: the detection range at which the chain has zero margin (1,667 m for the first example), and the fastest threat the chain can still beat at the given detection range (50 m/s). The binding stage is the largest term; in most counter-drone chains it is identification and authority, not sensing. That is why pre-delegated engagement authority, defined weapons control status and rehearsed drills buy more seconds than a longer-range sensor.

## 03 Layered defence: raid arithmetic

For a raid of N threats, n independent shots at each, single-shot defeat probability p:

```
P(no leaker)       P_RA = [1 − (1 − p)^n]^N
expected leakers   E[L] = N·(1 − p)^n
rounds used        M    = n·N              (shoot-shoot, before reload)
```

| Shots each | P(no leaker), N = 10, p = 0.8 | Expected leakers | Rounds |
|---|---|---|---|
| 1 | 0.107 | 2.00 | 10 |
| 2 | 0.665 | 0.40 | 20 |
| 3 | 0.923 | 0.08 | 30 |

Each step toward no leaker costs another full magazine. A twenty-threat raid with three shots each falls to 0.852. An interception rate is not a defended outcome: at p = 0.95 and one shot each, a twenty-threat raid still leaks with probability 0.64. Specify expected leakers against a stated raid, the passive protection for them, and the magazine and reload time behind it.

Layers multiply per threat. An outer layer at p = 0.5 with one shot and an inner layer at p = 0.8 with two leave a per-threat leak probability of 0.5 × 0.04 = 0.02, so P(no leaker) for ten threats is 0.98^10 = 0.817, using 10 outer and an expected 10 inner rounds. Because the inner layer only fires at what the outer layer missed, layering saves inner magazine as well as adding probability.

**Independence flatters the defence.** A shared threat-library gap or a blind sector that every layer shares is a common-mode failure. `common_mode_pra` illustrates the ceiling: if a raid exploits such a gap with probability 0.1, no number of shots lifts P(no leaker) above 0.9.

### Defence is the harder loop

Framed as control, defence is disturbance rejection (hold the state against every disturbance) and offence is setpoint tracking (drive the state along one chosen path). The defender must also estimate what the disturbance is, which is why defensive chains carry extra identify and evaluate steps; feedback acts only after an error appears; and the defender solves a worst-case problem over all approaches while the attacker optimises one. The practical corollaries: shorten your own delay, lengthen the adversary's, reduce structural vulnerability passively first so less active control is needed, and plan for leakers.

## 04 DDIL: how each condition breaks the loop

| Condition | Breaks the assumption that | Engineering response |
|---|---|---|
| Denied | a central service is reachable | decide at the edge |
| Degraded | data is clean and latency stable | retries, integrity checks, explicit confidence |
| Intermittent | a session persists | store and forward, reconcile after reconnection |
| Limited | everything can be sent | send the decision-relevant few bytes, not the raw feed |

The package's per-hop delivery model:

```
attempt   = base latency + message bits / bandwidth
retries   E = attempt / (1 − loss) + timeout · loss / (1 − loss)
outages   + (1 − up fraction) · mean outage          (exponential outages)
denied    ∞
```

With the presets (0.5 s base): connected 0.5 s; degraded at 30% loss with a 2 s timeout 1.57 s; intermittent at 80% up with 20 s mean outages 4.5 s; denied never. On a 9.6 kbps limited link a 2 kbit track message takes 0.71 s and a 2 Mbit video clip 209 s. The same link is adequate or useless depending on what the design insists on sending.

Degraded conditions compound through hops: the 8 s FPV margin above, with three connected hops added, is 6.5 s; with three intermittent hops it is negative.

## 05 Centralised versus distributed control

Centralised control concentrates the picture and decision authority; distributed (edge) control pushes fusion and authority outward. The comparison model:

```
loop time      = local + hops · (up + down delivery) + queue at the centre + decide + act
loop possible  = up_fraction ^ (2 · hops)          (every hop up, independent)
divergence     = 1 − (1 − p_partition) ^ nodes      (some edge picture out of step)
```

With the defaults (5 s local, 3 hops, 15 s queue for shared attention at the centre, 20 s decision, 5 s effect): the centralised loop is 48 s on a connected network, exactly the FPV window; the distributed loop is 30 s. Under intermittent links the centralised loop can close only 26% of the time (0.8^6). The distributed loop does not depend on the network to close, but with six edge deciders each partitioned 10% of the time, some local picture is out of step 47% of the time, and the design must reconcile it.

| | Centralised | Distributed |
|---|---|---|
| Buys | one authoritative picture, coherent decisions, simpler accountability | speed, survivability, bandwidth economy |
| Costs | round trip to the centre, single point of failure, shared attention queue | harder consistency, reconciliation, bounded authority to define |
| Fails under | denied and intermittent links | poor delegation, split-brain decisions after partition |
| Needs | resilient backhaul, prioritisation | mission command, pre-delegated authority, runtime bounds |

The choice is constrained by command philosophy. A tool that assumes flatter, faster delegation than the organisation practises is rejected for reasons that look like usability complaints; a tool that forces central approval for every action can undermine the mission command the organisation actually runs on.

## 06 Checklist: does this loop close

- Is the margin positive for the fastest credible threat, with every communications hop counted?
- Which stage binds, and is it sensing, identification, authority or effect?
- Does the core decision require a central service? If so, it fails Denied and Intermittent; say so.
- Does it degrade gracefully and signal the degraded state, rather than filling gaps silently?
- Does it reconcile after a partition?
- Under Limited, does it send decisions and tracks rather than raw feeds?
- Is magazine depth at least n·N for the credible raid, including a repeat?
- Are expected leakers stated, with passive protection for them?
