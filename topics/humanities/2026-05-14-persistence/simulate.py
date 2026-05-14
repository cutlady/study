#!/usr/bin/env python3
"""复利模拟: 对比"每天坚持"和"断断续续"的长期差异"""

import math

def simulate(days=365):
    """模拟一年的积累效果"""

    # 每天坚持 (日拱一卒)
    daily = 1.0
    consistent = [daily]
    for _ in range(days):
        daily *= 1.01  # 每天进步 1%
        consistent.append(daily)

    # 断断续续 (做 5 天停 2 天)
    sporadic = 1.0
    sporadic_curve = [sporadic]
    for day in range(days):
        if (day % 7) < 5:  # 周一到周五做
            sporadic *= 1.01
            sporadic_curve.append(sporadic)
        else:               # 周末休息，退步 0.5%
            sporadic *= 0.995
            sporadic_curve.append(sporadic)

    return consistent, sporadic_curve


def simulate_mood():
    """
    模拟低动力日"只做保底" vs "完全不做"
    —— 这更接近真实生活：你不可能永远高能量。
    """
    days = 180
    base = 1.0

    # 策略 A: 高能量日做 2%，低能量日只做 1 个单位（不退步）
    curve_a = [base]
    for day in range(days):
        if day % 5 == 3 or day % 7 == 0:  # 模拟"不想动"的日子
            curve_a.append(curve_a[-1])     # 不进步，也不退步
        else:
            curve_a.append(curve_a[-1] * 1.005)

    # 策略 B: 状态好时做 3%，状态差时不做 + 退步
    curve_b = [base]
    for day in range(days):
        if day % 5 == 3 or day % 7 == 0:
            curve_b.append(curve_b[-1] * 0.99)  # 完全不做就退步
        else:
            curve_b.append(curve_b[-1] * 1.007)

    return curve_a, curve_b


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "mood":
        a, b = simulate_mood()
        print(f"策略A (低动力日保持不动): {a[-1]:.2f}x — 不退步本身就是赢")
        print(f"策略B (低动力日完全放弃): {b[-1]:.2f}x — 退步消耗了好日子的大部分成果")
    else:
        c, s = simulate()
        print(f"每天坚持 365 天: {c[-1]:.1f}x 增长")
        print(f"做五休二 365 天: {s[-1]:.1f}x 增长")
        print(f"差距: {c[-1] - s[-1]:.1f}x")
