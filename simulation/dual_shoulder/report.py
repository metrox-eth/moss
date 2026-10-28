"""Writes out/report.html from the studies' JSON in out/. Self-contained page."""
from __future__ import annotations

import html
import json
import math
from datetime import date

import numpy as np

import moss_arm as ma
from charts import SCRIPT, figure

OUT = ma.OUT
STALL_V = ma.STALL_NM * 10.8 / 12


def load(name: str) -> dict:
    return json.loads((OUT / f"{name}.json").read_text())


def e(x) -> str:
    return html.escape(str(x))


def table(head: list[str], rows: list[list], num_from: int = 1) -> str:
    th = "".join(f'<th class="{"num" if i >= num_from else ""}">{e(h)}</th>' for i, h in enumerate(head))
    body = "".join("<tr>" + "".join(f'<td class="{"num" if i >= num_from else ""}">{c}</td>' for i, c in enumerate(r)) + "</tr>" for r in rows)
    return f'<div class="tw"><table><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table></div>'


def heat_fig(s1: dict, s5: dict) -> str:
    reach = s1["reach"]
    A, phi = s5["A_nm"], s5["phi_rad"]
    floor = ma.floor_reach_poses()
    bins = np.arange(0.10, 0.37, 0.02)
    single, dual, spring = [], [], []
    for lo in bins:
        idx = [i for i, r in enumerate(reach) if lo <= r["r"] < lo + 0.02]
        if len(idx) < 3:
            continue
        t0 = np.array([reach[i]["shoulder_lift_tau0"] for i in idx])
        th = np.array([floor[i]["rad"][1] for i in idx])
        x = round(lo + 0.01, 3)
        single.append((x, float(np.median((t0 / ma.RATED_NM) ** 2))))
        dual.append((x, float(np.median((t0 / 2 / ma.RATED_NM) ** 2))))
        spring.append((x, float(np.median(((t0 + A * np.sin(th - phi)) / ma.RATED_NM) ** 2))))
    return figure("f-heat", "Shoulder heat at every floor pick MOSS can make",
                  "Median over the 645 poses of MOSS's reach table, empty gripper, by distance of the pick from the arm's base. 1 = the servo's continuous rating.",
                  [{"name": "One servo (today)", "var": "--s1", "pts": single},
                   {"name": "Two servos, shared", "var": "--s2", "pts": dual, "label": "Two servos"},
                   {"name": "One servo + spring", "var": "--s3", "pts": spring, "label": "+ spring"}],
                  "pick distance from the arm base, m", "heat / continuous rating",
                  refs=[{"y": 1.0, "label": "rating"}], y_range=(0, 1.6), x_fmt="{:.2f}", y_fmt="{:.2f}")


def payload_fig(s5: dict) -> tuple[str, dict]:
    arm = ma.load()
    q = ma.moss_poses()["pick_low"]
    t0, jz = arm.hold_torque(q), arm.tcp_z_jac(q)
    th = q[1]
    spring = s5["A_nm"] * math.sin(th - s5["phi_rad"])
    kgs = np.linspace(0, 0.6, 61)
    sh = [(float(k), abs(t0[1] + k * ma.G * jz[1])) for k in kgs]
    du = [(float(k), abs(t0[1] + k * ma.G * jz[1]) / 2) for k in kgs]
    sp = [(float(k), abs(t0[1] + spring + k * ma.G * jz[1])) for k in kgs]
    el = [(float(k), abs(t0[2] + k * ma.G * jz[2])) for k in kgs]
    marks = [{"x0": ma.MOSS_CAN_KG - 0.002, "x1": ma.MOSS_CAN_KG + 0.002, "label": "MOSS can"},
             {"x0": ma.GLASS_BOTTLE_KG - 0.002, "x1": ma.GLASS_BOTTLE_KG + 0.002, "label": "glass bottle"}]
    fig = figure("f-payload", "Holding torque per servo at MOSS's pick pose",
                 "pick_low: the one pose MOSS picks every object at (the rover brings the object to it). Static, R92 model, arm weighed at 768 g. Stall: the 12 V figure at the 3S pack's 10.8 V.",
                 [{"name": "Shoulder, one servo", "var": "--s1", "pts": sh, "label": "shoulder, 1"},
                  {"name": "Shoulder, two servos (each)", "var": "--s2", "pts": du, "label": "shoulder, 2"},
                  {"name": "Shoulder, one + spring", "var": "--s3", "pts": sp, "label": "shoulder+spring"},
                  {"name": "Elbow (one servo)", "var": "--s4", "pts": el, "label": "elbow"}],
                 "object in the gripper, kg", "N·m per servo",
                 refs=[{"y": ma.RATED_NM, "label": "continuous 0.98"}, {"y": STALL_V, "label": "stall 2.65"}],
                 y_range=(0, 3.0), x_fmt="{:.2f}", y_fmt="{:.2f}", bands=marks)
    m_cross = {name: next((k for k, v in pts if v > ma.RATED_NM), None) for name, pts in
               (("single", sh), ("dual", du), ("spring", sp), ("elbow", el))}
    return fig, m_cross


def cycle_fig(s2: dict) -> str:
    def pick(pp, obj, n, hover=0.0):
        return next(r for r in s2["runs"] if r["pick_pose"] == pp and r["object"] == obj and r["n_shoulder"] == n and r["hover_s"] == hover)
    a, b = pick("pick_low", "MOSS can 20 g", 1), pick("pick_low", "MOSS can 20 g", 2)
    ta = a["trace"]
    series = [{"name": "Shoulder, one servo", "var": "--s1", "pts": list(zip(ta["t"], np.abs(ta["shoulder_nm_per_servo"]).tolist())), "label": "shoulder, 1"},
              {"name": "Shoulder, two servos (each)", "var": "--s2", "pts": list(zip(b["trace"]["t"], np.abs(b["trace"]["shoulder_nm_per_servo"]).tolist())), "label": "shoulder, 2"},
              {"name": "Elbow", "var": "--s4", "pts": list(zip(ta["t"], np.abs(ta["elbow_nm"]).tolist())), "label": "elbow"}]
    bands, start = [], None
    ph = ta["phase"]
    for i, p in enumerate(ph):
        if i == 0 or p != ph[i - 1]:
            if start is not None:
                bands.append((start, ta["t"][i - 1], ph[start_i]))
            start, start_i = ta["t"][i], i
    bands.append((start, ta["t"][-1], ph[start_i]))
    held = [(x0, x1) for x0, x1, p in bands if p in ("lift", "clear", "transfer")]
    bl = [{"x0": held[0][0], "x1": held[-1][1], "label": "object in hand"}]
    return figure("f-cycle", "One pick-and-drop cycle as MOSS runs it: floor pick, its 20 g can",
                  "MuJoCo, MOSS's own sequence and timing (quintic moves, 400 ticks/s ceiling). Torque per servo, absolute.",
                  series, "time, s", "N·m per servo",
                  refs=[{"y": ma.RATED_NM, "label": "continuous 0.98"}], y_range=(0, 1.6), x_fmt="{:.1f}", y_fmt="{:.2f}", bands=bl)


def fight_fig(s3: dict) -> tuple[str, dict]:
    rows = [r for r in s3["rows"] if r["case"] == "pick_low + MOSS can"]
    single = next(r for r in rows if r["setup"]["strategy"] == "single")
    fol = [r for r in rows if r["setup"]["strategy"] == "follower" and abs(r["setup"]["kp"] - ma.KP_P32) < 1]
    series = []
    for k_s, var, nm in ((50.0, "--s1", "flexible bracket (50 N·m/rad)"), (200.0, "--s2", "printed bracket (200)"), (1000.0, "--s3", "stiff, metal (1000)")):
        pts = sorted((r["setup"]["delta_ticks"], r["heat_max"]) for r in rows
                     if r["setup"]["strategy"] == "same_goal" and r["setup"]["k_s"] == k_s
                     and r["setup"]["play_deg"] == 0.0 and abs(r["setup"]["kp"] - ma.KP_P32) < 1)
        series.append({"name": f"Same goal, {nm}", "var": var, "pts": pts, "label": nm.split(" (")[0]})
    fol_heat = max(r["heat_max"] for r in fol)
    fig = figure("f-fight", "Two servos given the same goal: the hotter servo's heat",
                 "Arm at MOSS's pick pose holding its 20 g can. x = how far servo B's encoder disagrees with A's, in ticks (1 tick = 0.088°). The model's servo stiffness (998 N·m/rad, firmware P = 32).",
                 series, "encoder offset between the two servos, ticks", "heat of the hotter servo / rating",
                 refs=[{"y": single["heat_max"], "label": f"one servo {single['heat_max']:.2f}"},
                       {"y": fol_heat, "label": f"follower {fol_heat:.2f}"}],
                 y_range=(0, 8), x_fmt="{:.0f}", y_fmt="{:.2f}")
    return fig, {"single": single, "follower_heat": fol_heat}


def soft_fig(s3: dict, single_heat: float) -> str:
    series = []
    for kp, var in ((50.0, "--s1"), (100.0, "--s2"), (250.0, "--s4")):
        r = next(r for r in s3["stiffness"] if r["kp"] == kp and r["k_s"] == 200.0)
        series.append({"name": f"Kp {kp:.0f} N·m/rad: one servo sags {r['sag_deg']:.2f}° at the pick", "var": var,
                       "pts": [(x["delta_ticks"], x["heat_max"]) for x in r["same_goal"]], "label": f"sags {r['sag_deg']:.1f}°"})
    return figure("f-soft", "Same goal again, with a softer servo",
                  "Printed bracket (200 N·m/rad), MOSS's pick pose and its 20 g can. Each line is a servo that holds its goal less stiffly than the model's 998 N·m/rad; the softer it is, the more one servo alone sags under the arm.",
                  series, "encoder offset between the two servos, ticks", "heat of the hotter servo / rating",
                  refs=[{"y": single_heat, "label": f"one servo {single_heat:.2f}"}], x_fmt="{:.0f}", y_fmt="{:.2f}")


def pick_fig(s6: dict) -> str:
    b = s6["bins"]
    x0 = s6["pick_low_x"]
    return figure("f-pick", "Shoulder heat against where the arm picks, straight ahead",
                  "Every floor pose of MOSS's reach table within 5 cm of the pick line, posed in the R92 model with the 20 g can. x in the model frame: the tracks end at 0.17 m.",
                  [{"name": "Shoulder, best pose at that point", "var": "--s1", "pts": [(r["x"], r["best_shoulder"]) for r in b], "label": "shoulder, best"},
                   {"name": "Shoulder, median pose", "var": "--s2", "pts": [(r["x"], r["median_shoulder"]) for r in b], "label": "shoulder, median"},
                   {"name": "Elbow (best pose)", "var": "--s4", "pts": [(r["x"], r["best_elbow"]) for r in b], "label": "elbow"}],
                  "tool x, m (rover frame)", "heat / continuous rating",
                  refs=[{"y": 1.0, "label": "rating"}], y_range=(0, 1.5), x_fmt="{:.2f}", y_fmt="{:.2f}",
                  bands=[{"x0": x0 - 0.0015, "x1": x0 + 0.0015, "label": "today"}])


CSS = """
:root{color-scheme:light;--bg:#f9f9f7;--surface:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--muted:#898781;--grid:#e1e0d9;--axis:#c3c2b7;
--line:rgba(11,11,11,.10);--s1:#2a78d6;--s2:#eb6834;--s3:#1baf7a;--s4:#6250d6;--band:rgba(11,11,11,.035);--accent:#2a78d6}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){color-scheme:dark;--bg:#0d0d0d;--surface:#1a1a19;--ink:#f0efec;--ink2:#c3c2b7;
--muted:#898781;--grid:#2c2c2a;--axis:#383835;--line:rgba(255,255,255,.10);--s1:#3987e5;--s2:#d95926;--s3:#199e70;--s4:#9085e9;--band:rgba(255,255,255,.04);--accent:#3987e5}}
:root[data-theme="dark"]{color-scheme:dark;--bg:#0d0d0d;--surface:#1a1a19;--ink:#f0efec;--ink2:#c3c2b7;--muted:#898781;--grid:#2c2c2a;--axis:#383835;
--line:rgba(255,255,255,.10);--s1:#3987e5;--s2:#d95926;--s3:#199e70;--s4:#9085e9;--band:rgba(255,255,255,.04);--accent:#3987e5}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:860px;margin:0 auto;padding:32px 16px 64px}h1{font-size:28px;line-height:1.2;margin:0 0 6px}h2{font-size:19px;margin:40px 0 8px}
.lede{color:var(--ink2);margin:0 0 20px}.meta{color:var(--muted);font-size:13px}
.verdict{background:var(--surface);border:1px solid var(--line);border-left:3px solid var(--accent);border-radius:10px;padding:16px 18px;margin:20px 0}
.verdict p{margin:6px 0}.verdict ol{margin:6px 0;padding-left:20px}.verdict li{margin:4px 0}
.fig{background:var(--surface);border:1px solid var(--line);border-radius:10px;margin:18px 0;padding:14px 14px 8px}
figcaption b{display:block;font-size:15px}figcaption span{display:block;color:var(--ink2);font-size:13px}
.legend{display:flex;flex-wrap:wrap;gap:6px 16px;margin:10px 0 4px;font-size:13px;color:var(--ink2)}
.key i{display:inline-block;width:14px;height:3px;border-radius:2px;margin-right:6px;vertical-align:middle}
.plot{position:relative}.chart{width:100%;height:auto;display:block}
.grid{stroke:var(--grid);stroke-width:1}.axis{stroke:var(--axis);stroke-width:1}.ref{stroke:var(--muted);stroke-width:1}
.tick,.ref-label,.band-label{fill:var(--muted);font-size:11px;font-variant-numeric:tabular-nums}.axis-label{fill:var(--ink2);font-size:12px}
.end-label{fill:var(--ink2);font-size:12px}.line{fill:none;stroke-width:2;stroke-linejoin:round;stroke-linecap:round}
.dot{stroke:var(--surface);stroke-width:2}.pt{stroke:var(--surface);stroke-width:1;opacity:.85}.band{fill:var(--band)}
.xhair{stroke:var(--axis);stroke-width:1}.hit{fill:transparent;cursor:crosshair}
.tip{position:absolute;pointer-events:none;background:var(--surface);border:1px solid var(--line);border-radius:8px;padding:8px 10px;font-size:12px;
box-shadow:0 4px 16px rgba(0,0,0,.12);min-width:170px;z-index:2}.tip .th{color:var(--muted);margin-bottom:4px}
.tip div{display:flex;align-items:center;gap:6px}.tip i{width:10px;height:3px;border-radius:2px;display:inline-block}.tip b{margin-left:auto;font-variant-numeric:tabular-nums}
.tw{overflow-x:auto;margin:12px 0}table{border-collapse:collapse;width:100%;font-size:13px;background:var(--surface);border:1px solid var(--line);border-radius:8px}
th,td{padding:6px 10px;border-bottom:1px solid var(--grid);text-align:left;white-space:nowrap}th{color:var(--ink2);font-weight:600}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}tr:last-child td{border-bottom:0}
.note{color:var(--ink2);font-size:13px}code{font-size:13px}ul.tight li{margin:4px 0}
"""


def main() -> None:
    s1, s2, s3, s4, s5, s6 = (load(n) for n in ("s1_torque_budget", "s2_cycle", "s3_two_servos", "s4_tipping", "s5_spring", "s6_pick_point"))
    near = min((r for r in s6["bins"] if r["x"] < s6["pick_low_x"] - 0.03), key=lambda r: abs(r["x"] - (s6["pick_low_x"] - 0.055)))
    mixed = max(s6["bins"], key=lambda r: r["median_shoulder"] - r["best_shoulder"])
    pf, cross = payload_fig(s5)
    ff, fight = fight_fig(s3)

    # study 1 table
    rows1 = []
    for k, v in s1["poses"].items():
        b = v["joints"]
        lim_s = min(b, key=lambda j: b[j]["m_rated_single"])
        lim_d = min(b, key=lambda j: b[j]["m_rated_dual"])
        nice = {"shoulder_lift": "shoulder", "elbow_flex": "elbow", "wrist_flex": "wrist"}
        rows1.append([e(k), f"{abs(b['shoulder_lift']['tau0']):.2f}", f"{abs(b['elbow_flex']['tau0']):.2f}",
                      f"{b[lim_s]['m_rated_single']*1000:.0f} g · {nice[lim_s]}", f"{b[lim_d]['m_rated_dual']*1000:.0f} g · {nice[lim_d]}"])

    # study 2 table
    rows2 = []
    for r in s2["runs"]:
        if r["pick_pose"] == "pick":
            continue
        s, el = r["joints"]["shoulder_lift"], r["joints"]["elbow_flex"]
        rows2.append([e(r["pick_pose"]), e(r["object"]), f"{r['hover_s']:.0f} s", "two" if r["n_shoulder"] == 2 else "one",
                      f"{s['peak_of_stall']:.2f}", f"{s['mean_heat']:.2f}", f"{s['s_over_rated']:.1f} s", f"{s['max_err_deg']:.1f}°",
                      f"{el['mean_heat']:.2f}", f"{el['s_over_rated']:.1f} s"])

    # study 3 tables
    sg = [r for r in s3["rows"] if r["case"] == "pick_low + MOSS can" and r["setup"]["strategy"] == "same_goal"
          and r["setup"]["k_s"] == 200.0 and r["setup"]["play_deg"] == 0.0 and abs(r["setup"]["kp"] - ma.KP_P32) < 1]
    s_single = fight["single"]
    rows3 = [["one servo (today)", "", f"{s_single['tau_a']:.2f}", "", "", f"{s_single['heat_max']:.2f}", f"{s_single['copper_w']:.2f}"]]
    for r in sorted(sg, key=lambda r: r["setup"]["delta_ticks"]):
        rows3.append(["same goal", f"{r['setup']['delta_ticks']:+.0f}", f"{r['tau_a']:.2f}", f"{r['tau_b']:.2f}",
                      f"{r['fight_nm']:.2f}", f"{r['heat_max']:.2f}", f"{r['copper_w']:.2f}"])
    fo = [r for r in s3["rows"] if r["case"] == "pick_low + MOSS can" and r["setup"]["strategy"] == "follower"
          and r["setup"]["k_s"] == 200.0 and abs(r["setup"]["kp"] - ma.KP_P32) < 1]
    for r in fo:
        rows3.append(["follower", "any", f"{r['tau_a']:.2f}", f"{r['tau_b']:.2f}", f"{r['fight_nm']:.2f}", f"{r['heat_max']:.2f}", f"{r['copper_w']:.2f}"])
    rows3f = [[f"{r['setup']['bus_hz']:.0f} Hz", f"{r['setup']['alpha']:.1f}", f"{r['share_b']:.2f}", f"{r['ripple_b']:.3f}",
               "steady" if r["ripple_b"] < 0.02 else "oscillates"] for r in s3["follower"]]
    nice = {"single": "one servo", "same_goal": "same goal", "follower": "follower"}
    rows3m = [[nice[r["setup"]["strategy"]], "" if r["setup"]["strategy"] == "single" else f"{r['setup']['delta_ticks']:.0f}", f"{r['max_err_deg']:.2f}°", f"{r['tau_a']:.2f}", f"{r['tau_b']:.2f}"] for r in s3["moves"]]

    # study 3, the servo's stiffness: same goal against how softly the loop holds its goal
    st = s3["stiffness"]
    tick_deg = math.degrees(ma.TICK_RAD)
    def worst(kp, lim):
        return max(x["heat_max"] for r in st if r["kp"] == kp for x in r["same_goal"] if abs(x["delta_ticks"]) <= lim)
    def sag(kp):
        return next(r["sag_deg"] for r in st if r["kp"] == kp)
    kps = sorted({r["kp"] for r in st})
    soft = max(kp for kp in kps if worst(kp, 4) < s_single["heat_max"])
    tag = {ma.KP_P32: " (model, P 32)", ma.KP_P16: " (model, P 16)"}
    rows3s = [[f"{kp:.0f}{tag.get(kp, '')}", f"{sag(kp):.2f}° · {sag(kp) / tick_deg:.1f} ticks", f"{worst(kp, 0):.2f}",
               f"{worst(kp, 4):.2f}", f"{worst(kp, 8):.2f}"] for kp in kps]

    # robustness across all same-goal setups: how often is the hotter servo worse than one servo alone?
    agg = []
    for case in ("pick_low + MOSS can", "far pick + glass bottle", "clear (light load)"):
        rs = [r for r in s3["rows"] if r["case"] == case]
        one = next(r for r in rs if r["setup"]["strategy"] == "single")["heat_max"]
        same = [r for r in rs if r["setup"]["strategy"] == "same_goal"]
        fol = [r for r in rs if r["setup"]["strategy"] == "follower"]
        worse = sum(r["heat_max"] > one for r in same)
        agg.append([e(case), f"{one:.2f}", f"{np.median([r['heat_max'] for r in same]):.2f}", f"{worse} of {len(same)}",
                    f"{max(r['heat_max'] for r in fol):.2f}"])

    s4w = min((r for r in s4["rows"] if r["pose"] == "stretched level"), key=lambda r: r["m_tip_kg"])
    s4s = min((r for r in s4["rows"] if r["pose"] == "stretched level"), key=lambda r: r["tip_deg_0.53"])
    sp = s5
    def run(pp, obj, n, hover=0.0):
        return next(r for r in s2["runs"] if r["pick_pose"] == pp and r["object"] == obj and r["n_shoulder"] == n and r["hover_s"] == hover)
    can1, can2 = run("pick_low", "MOSS can 20 g", 1), run("pick_low", "MOSS can 20 g", 2)
    glass1 = run("pick_low", "glass bottle 250 g", 1)
    can_cycles = [r for r in s2["runs"] if r["object"] == "MOSS can 20 g" and r["n_shoulder"] == 1 and r["hover_s"] == 0 and r["pick_pose"] in ("pick", "pick_low")]
    arm = ma.load()
    q_low = ma.moss_poses()["pick_low"]
    hold_can = abs(arm.hold_torque(q_low)[1] + ma.MOSS_CAN_KG * ma.G * arm.tcp_z_jac(q_low)[1])
    can_adds = abs(ma.MOSS_CAN_KG * ma.G * arm.tcp_z_jac(q_low)[1])
    q_st = s1["poses"]["stretched (worst case)"]["q"]
    hold_reach = abs(arm.hold_torque(q_st)[1] + ma.MOSS_CAN_KG * ma.G * arm.tcp_z_jac(q_st)[1])
    sp_low = s5["poses"][f"pick_low@{ma.MOSS_CAN_KG}"]
    sp_glass = s5["poses"][f"pick_low@{ma.GLASS_BOTTLE_KG}"]
    over_single = sum(1 for r in s1["reach"] if (r["shoulder_lift_tau0"] / ma.RATED_NM) ** 2 > 1)

    verdict = f"""
<div class="verdict">
<p><b>Short answer, for the litter MOSS is built for (its 20 g reference can): the shoulder is strong enough, and the cycle as written stays cool. Its one weak moment is holding the arm still at the pick, and that load is the arm's own weight, not the litter. The cheapest fix is where the arm picks. After that, a spring. A second servo helps only if the two share the load. Sent the same goal, as RoArm's firmware does it, they share if the servo holds its goal softly and fight if it holds it stiffly, and one reading on the arm tells which.</b></p>
<ol>
<li><b>The litter barely counts.</b> MOSS's own test object (<code>scene.xml</code>: 66 × 115 mm, 20 g) adds {can_adds:.2f} N·m at the pick. Over a whole cycle the shoulder peaks at {max(r['joints']['shoulder_lift']['peak_of_stall'] for r in can_cycles)*100:.0f}% of stall and averages {max(r['joints']['shoulder_lift']['mean_heat'] for r in can_cycles):.2f}× its continuous rating. The elbow stays under its rating the whole time.</li>
<li><b>The weak moment is waiting at the pick.</b> MOSS picks every object at one pose (pick_low), where the shoulder holds {hold_can:.2f} N·m, {ma.heat_ratio(hold_can):.2f}× its continuous rating, with the can or without it. Today the cycle stays above the rating there for about 3 s. A wrist-camera check before the grasp (not built yet, per <code>docs/litter.md</code>) or a re-grasp would add time there. Issue #2's test, a can held at full reach for a minute, is {ma.heat_ratio(hold_reach):.1f}× the rating. It can pass without drift while the servo heats, so log the temperature.</li>
<li><b>The cheapest fix is where the arm picks.</b> The arm sits on top of the rover behind its nose, so today's pick is a stretched reach {s6['pick_low_x'] - s6['track_front_x']:.2f} m past the tracks' front end. Picking {(s6['pick_low_x'] - near['x'])*100:.0f} cm closer (x {near['x']:.2f} m instead of {s6['pick_low_x']:.3f} m) brings the shoulder from {s6['pick_low_heat']['shoulder']:.2f}× to {near['best_shoulder']:.2f}×. That is a change to the pick pose and <code>MOSS_PICK_XY_M</code>, not to the hardware. At a given point, the pose matters too: at x {mixed['x']:.2f} m the reach table's poses run the shoulder anywhere from {mixed['best_shoulder']:.2f}× to over {mixed['median_shoulder']:.1f}×. Its tie-break picks the pose nearest <code>pick_low</code>, not the lightest.</li>
<li><b>Whether the same goal works depends on how stiffly the servo holds its goal.</b> The model's servo (Menagerie's, full torque about 2 ticks off the goal) gives a poor split: behind a printed bracket the second servo takes only {sg[[r['setup']['delta_ticks'] for r in sg].index(0)]['share_b']*100:.0f}% of the load when perfectly calibrated, and at a 4-tick encoder offset the two push against each other, the hotter one at {[r for r in sg if r['setup']['delta_ticks'] == 4][0]['heat_max']:.1f}× its rating against {s_single['heat_max']:.2f}× for one servo. The bench note in issue #2 says the real loop is much softer near its goal: under load, a goal a few ticks away does not move the arm. With a servo soft enough that one alone sags {sag(soft):.1f}° at the pick, same goal with RoArm's zero at boot beats one servo at any offset up to ±4 ticks (hotter servo {worst(soft, 4):.2f}× at worst), and the softer the servo, the lower that worst case ({worst(50.0, 4):.2f}× at a {sag(50.0):.1f}° sag). One reading on today's arm decides it: one servo at pick_low, <code>Present_Position</code> minus the goal. About {sag(soft) / tick_deg:.0f} ticks or more, and same goal will share; 1–2 ticks, and it fights.</li>
<li><b>If the loop is stiff, a follower shares evenly.</b> Servo A holds position. Servo B runs open-loop PWM (STS mode 2) and copies A's <code>Present_Load</code> over the bus. That gives an even 50/50 split at any encoder offset, so at the pick each servo runs at {max(r['heat_max'] for r in fo):.2f}×. B must follow slowly, with a time constant of about 0.1 s (at 50 Hz, 20–30% of the gap per update), or it rings against A's loop.</li>
<li><b>For a load that is all arm weight, a spring is the better fit.</b> A gravity-balance spring of {sp['A_nm']:.2f} N·m peak takes the pick pose to {ma.heat_ratio(sp_low['spring']):.2f}× (two servos sharing evenly: {ma.heat_ratio(sp_low['dual']):.2f}× each), with nothing to sync. Two servos only pull ahead with heavier litter. MOSS's detector also picks glass: with a 250 g bottle at the pick, one servo is at {ma.heat_ratio(sp_glass['single']):.1f}×, the spring {ma.heat_ratio(sp_glass['spring']):.2f}×, and an even pair {ma.heat_ratio(sp_glass['dual']):.2f}× each. Tipping is no risk at these weights; it takes {s4w['m_tip_kg']:.1f} kg held stretched out to the side.</li>
</ol>
</div>"""

    body = f"""<main>
<h1>Does the MOSS shoulder want a second servo?</h1>
<p class="lede">MuJoCo studies on the MOSS V0.6 / R92 model for <a href="https://github.com/metrox-eth/moss/issues/2">issue #2</a>: holding load, the real pick-and-drop cycle, two STS3215 on one shaft, a spring instead, and tipping.</p>
<p class="meta">{date.today().isoformat()} · model <code>simulation/mujoco/model/moss_robot.xml</code> (R92, MuJoCo 3.3.7) · arm calibrated to the weighed 768 g · servo STS3215 / ST3215 12 V: stall 2.94 N·m (2.65 at the 3S pack's 10.8 V), continuous 0.98 N·m · code in <code>simulation/dual_shoulder/</code></p>
{verdict}

<h2>1 · Where the load is</h2>
<p>Holding torque from the model at every pose MOSS uses: its cycle poses, its drive pose, all 645 floor picks of its reach table (gripper within 10° of vertical), and the worst stretched-out pose. Heat goes with torque squared, so <i>heat / rating</i> = (torque / 0.98 N·m)². Above 1, the servo heats past what it can shed and eventually trips its cut-out.</p>
{heat_fig(s1, s5)}
{table(["pose", "shoulder N·m", "elbow N·m", "max object at rating · one servo", "· two shoulder servos"], rows1)}
<p class="note">Read the last two columns as: the heaviest object that pose can hold forever, and the joint that limits it. With one servo the shoulder limits every floor pick. With two, the elbow takes over in {sum(1 for r in s1['reach'] if r['first_rated_dual']=='elbow_flex')} of the 645 floor picks, and in {sum(1 for r in s1['reach'] if r['first_rated_dual']=='elbow_flex' and r['r']>0.30)} of the {sum(1 for r in s1['reach'] if r['r']>0.30)} far ones. In the lift, travel and drop poses the elbow limits anyway.</p>
{pf}
<p class="note">At MOSS's pick pose, one shoulder servo passes its continuous rating at {cross['single']*1000:.0f} g, two at {cross['dual']*1000:.0f} g, and one plus the spring at {cross['spring']*1000:.0f} g. The elbow passes its rating at {(cross['elbow'] or 0.6)*1000:.0f} g{"" if cross['elbow'] else " or more"}. MOSS's can is 20 g. Picks farther out (the rest of the reach table) are where the arm would reach once it stops relying on the rover to bring the object to it.</p>

<h2>2 · The cycle MOSS actually runs</h2>
<p>The sequence from <code>config/arm_drop_poses.json</code>, played the way <code>moss_dimos.arm.load_cycle</code> plays it, under full dynamics with the servos' torque limit. The object is attached from the grip to the release. "Hover" adds 20 s at the pick with the object in hand. <i>Mean heat</i> is over one whole cycle (about 40 s); <i>s over</i> is the time above the continuous rating.</p>
{cycle_fig(s2)}
{table(["pick", "object", "hover", "servos", "peak/stall", "heat", "s over", "sag", "elbow heat", "elbow s over"], rows2, num_from=4)}
<p class="note">Shoulder columns first (peak torque over stall, mean heat over the cycle, time over the rating, worst sag), then the elbow.</p>

<h2>3 · The cheapest fix: where the arm picks</h2>
<p>The mission drives the rover until the object sits at one pick point; the arm never reaches for it. That point decides how far out the arm stretches. Below: every floor pose of the reach table straight ahead, posed in the R92 model with the can.</p>
{pick_fig(s6)}
{table(["tool x, m", "past the tracks, m", "poses", "shoulder, best pose", "shoulder, median", "elbow, best pose"],
       [[f"{r['x']:.2f}", f"{r['ahead_of_tracks_m']:.2f}", str(r['n']), f"{r['best_shoulder']:.2f}", f"{r['median_shoulder']:.2f}", f"{r['best_elbow']:.2f}"] for r in s6['bins']])}
<p class="note">What the model cannot say: whether the nose camera still sees the object that close, and whether the last, open-loop part of the approach lands it there. Both are checks on the robot.</p>

<h2>4 · Two servos on one shaft: share or fight?</h2>
<p>Servo B sits on the far side of the upper arm, mirrored, and reaches the joint through its horn and the printed bracket (a torsion spring, optionally with play). Each STS3215 closes its own position loop on its own <i>output</i> encoder. Gearbox backlash sits inside that loop and hardly matters. What matters is how far the two encoders disagree about the same shaft angle, plus the bracket's flex. Zeroing B against A at one angle (what RoArm-M2's and M3's firmware does at every boot) removes the disagreement at that angle only. How much a leftover offset matters depends on how stiffly each servo holds its goal, which the model takes from Menagerie and the last part of this section sweeps.</p>
{ff}
{table(["strategy", "offset, ticks", "τ A, N·m", "τ B, N·m", "fight, N·m", "hotter servo heat", "copper loss, W"], rows3)}
<p class="note">Printed bracket (200 N·m/rad), no play, the model's stiffness (P = 32), at MOSS's pick pose with its 20 g can. Negative τ holds the arm up. A <i>fight</i> is where the two push in opposite directions: both get hot and the arm gains nothing.</p>
<p>Across every same-goal variant tried at the model's stiffness (offset −8…+8 ticks, bracket 50 / 200 / 1000 N·m/rad, play 0 / 0.3°, firmware P 32 / 16):</p>
{table(["case", "one servo heat", "same goal, median", "same goal worse than one servo", "follower, worst"], agg)}
<h3>How stiffly the servo holds its goal</h3>
<p>The model's 998 N·m/rad is Menagerie's value, not a measurement. The bench note in issue #2 (under load, a goal a few ticks away does not move the arm) rules it out: at that stiffness a few ticks are worth more than the servo's full torque. So the same goal again, with servos that hold their goal less stiffly. The softer the servo, the more one alone sags under the arm, which is what makes it measurable.</p>
{soft_fig(s3, s_single['heat_max'])}
{table(["servo stiffness, N·m/rad", "one servo sags at the pick", "same goal, offset 0", "offset up to ±4 ticks", "up to ±8 ticks"], rows3s)}
<p class="note">Heat of the hotter servo, worst over the three brackets (50 / 200 / 1000 N·m/rad), no play, MOSS's pick pose with its can. One servo: {s_single['heat_max']:.2f}×. A soft loop forgives a stiff bracket; a stiff loop does not. The loop here is linear: a deadband or gear stiction, which the bench note may also point at, would make a small offset leave one servo idle rather than fight.</p>
<h3>The follower's one setting</h3>
<p>B's PWM duty moves towards A's measured duty by a fraction α per bus update, one update late. Too eager and it rings against A's own loop:</p>
{table(["bus rate", "α", "B's share", "ripple, N·m", ""], rows3f, num_from=2)}
<p>The lift itself (pick_low → lift with MOSS's can, 2.6 s):</p>
{table(["strategy", "offset", "worst tracking error", "end τ A", "end τ B"], rows3m)}

<h2>5 · Weak spots</h2>
<ul class="tight">
<li><b>The sync is the design.</b> The same goal the way RoArm does it (zero at boot, P 16, mirrored goals in one packet with the same speed and acceleration, the same torque limit) shares if the loop is soft and fights if it is stiff. Before any payload test, run both servos at a rest pose with nothing in the gripper and read <code>Present_Load</code> on both. If the signs are opposite, they are fighting.</li>
<li><b>Stiff loop + stiff bracket = heat.</b> The fight grows with the stiffness of both the servo's loop and the bracket. With a stiff loop, a printed prototype that couples B rigidly will fight at some poses, and both servos' <code>Present_Load</code> will show it, with opposite signs.</li>
<li><b>The elbow, with heavier litter.</b> With MOSS's can the elbow never passes its rating. With a 250 g glass bottle it is over for {glass1['joints']['elbow_flex']['s_over_rated']:.0f} s of each cycle (mean {glass1['joints']['elbow_flex']['mean_heat']:.2f}×, so still sustainable). Only with full containers, which are beyond what MOSS is built to pick, does it reach 13–20 s per cycle. A stronger shoulder does nothing for it.</li>
<li><b>The pack voltage.</b> The servos run straight off the 3S pack: 12.6 V full, about 10.5 V under load at the end. Stall torque scales with voltage, so the 30 kg·cm figure is closer to 25 kg·cm in use and about 23 at a low pack. The continuous rating (heat) does not change.</li>
<li><b>The follower's failure mode.</b> In PWM mode, B keeps its last duty if the bus or the host stops. Cap B's torque limit (register 48), zero it when A's reading goes stale, and clamp it whenever A is at an end stop. Pinch force near the floor also doubles.</li>
<li><b>Current.</b> Two shoulder servos at stall draw about 5.4 A on top of the others: check the Bus Servo Adapter's rating and the 15 A fuse.</li>
<li><b>Tipping is fine.</b> On flat ground the least payload that tips the rover is {s4w['m_tip_kg']:.2f} kg, held stretched out to the side (pan {s4w['pan_deg']:.0f}°). With a full 0.5 l bottle there, a side slope of {s4s['tip_deg_0.53']:.0f}° would tip it.</li>
<li><b>A model note for the R92 sim:</b> the shipped XML's shoulder range (±100°) stops short of MOSS's drive pose (−104.4°, ticks 860, the calibrated end stop). <code>moss_dimos</code> widens the ranges when it writes its own sim scene; the plain XML does not.</li>
</ul>

<h2>6 · What to measure on the bench</h2>
<ol>
<li><b>How stiffly one servo holds</b> (2 min, today's arm, one servo): at pick_low, read the shoulder's <code>Present_Position</code> minus its goal, arriving from above as the cycle does; then step the goal by 2, 4 and 8 ticks and note when the arm moves. About {sag(soft) / tick_deg:.0f} ticks of sag or more: same goal will share. 1–2 ticks: expect a fight, and use the follower.</li>
<li><b>Encoder offset across the travel</b> (5 min, no power to the motors): couple both servos to the joint, torque off on both, swing the arm by hand end to end, and log both servos' <code>Present_Position</code>. Offset = A − mirror(B). With a soft loop a few ticks are harmless; with a stiff one this number decides how hard same goal fights.</li>
<li><b>Idle fight</b>: torque on, the arm resting in the drive pose. Log <code>Present_Load</code> and <code>Present_Current</code> on both for 30 s.</li>
<li><b>Issue #2's own test</b> with MOSS's can, held for 60 s at the pick pose (pick_low) as well as at full reach. Log <code>Present_Temperature</code> and load on both servos, and compare one servo, two with the same goal, two with the follower, and one with a spring. Report the temperature rise per minute, not just "it held".</li>
<li><b>The pick point</b>: move <code>MOSS_PICK_XY_M</code> and the pick pose a few cm closer, then check that the nose camera still sees the object and the approach lands it there. Log the shoulder's <code>Present_Load</code> at both points.</li>
<li><b>Payload lift</b> last. It only measures stall, which this arm never comes near with litter.</li>
</ol>

<h2>Assumptions and limits</h2>
<ul class="tight note">
<li>Arm masses: MuJoCo Menagerie SO101 plus the R92 gripper, scaled to the weighed 768 g (15 g added at the hand). Rover body 4.0 kg (the model's estimate).</li>
<li>Litter: MOSS's own can from <code>scene.xml</code> (20 g), an empty 0.33 l glass bottle (250 g, the detector's "glass" class), and full containers marked "stress", which MOSS isn't designed to pick. The object sits at the model's tcp. MOSS holds a standing can a few cm farther along the gripper. At the pick the gripper points down, so this barely moves the lever arm: for 20 g it is under 0.01 N·m at any pose.</li>
<li>Servo: Feetech figures (stall 30 kg·cm, continuous 10 kg·cm, 2.7 A stall at 12 V); position stiffness 998 N·m/rad from the model (firmware P = 32), 499 for P = 16, and a sweep from 25 to 998 because the real loop is softer near its goal (issue #2). The loop is linear, with no deadband or stiction. The holding torques and heat do not depend on it; only the split between two servos does. The thermal threshold is the continuous rating, not a measured temperature curve. No thermal time constant is claimed.</li>
<li>Two servos: B's path to the joint is a torsion spring of 50–1000 N·m/rad with 0–0.3° play. Real brackets need measuring. Encoder errors that vary with angle enter as the offset sweep. The follower is modelled with PWM duty proportional to torque at low speed, one bus sample of delay, and no read noise.</li>
<li>Contacts are off in the dynamic studies: they measure what the servos must give, not grasp success. The base is pinned; tipping is static.</li>
<li>Spring: an ideal zero-free-length balancer (torque A·sin(θ − φ)), fitted for the lowest worst-case shoulder load over MOSS's poses. A real spring and its cable or linkage would get somewhat less.</li>
</ul>
</main>"""
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MOSS Shoulder Study</title><style>{CSS}</style></head><body>{body}<script>{SCRIPT}</script></body></html>"""
    p = OUT / "report.html"
    p.write_text(page)
    print(p)


if __name__ == "__main__":
    main()
