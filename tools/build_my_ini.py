#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从上游模板 cfg/Custom_Clash_Full.ini 生成你自己的 cfg/My_Clash.ini

只做三件事：
  1. 删掉匹配不到你节点的分组，并清掉引用它们的地方
     「🚀 手动选择」的引用改成「♻️ 自动选择」；地区分组 / 其他地区 / 家宽 / 低倍率 直接删
  2. 除了「🎯 全球直连」，其它分组的默认（成员第一位）都设成「♻️ 自动选择」＝走代理
  3. 「♻️ 自动选择」保持 url-test + .*（＝全部 CF优选 节点），一个字不动

用法：python3 tools/build_my_ini.py
"""
import pathlib
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SRC = pathlib.Path("cfg/Custom_Clash_Full.ini")
DST = pathlib.Path("cfg/My_Clash.ini")

AUTO = "♻️ 自动选择"
DIRECT_ONLY = {"🎯 全球直连"}   # 这些分组保持直连

# 值不是 None：引用它的地方改成该分组；值为 None：直接删掉这个引用
DELETE = {
    "🚀 手动选择": AUTO,
    "🌐 其他地区": None,
    "🇭🇰 香港节点": None,
    "🇺🇸 美国节点": None,
    "🇯🇵 日本节点": None,
    "🇸🇬 新加坡节点": None,
    "🇼🇸 台湾节点": None,
    "🇰🇷 韩国节点": None,
    "🇨🇦 加拿大节点": None,
    "🇬🇧 英国节点": None,
    "🇫🇷 法国节点": None,
    "🇩🇪 德国节点": None,
    "🇳🇱 荷兰节点": None,
    "🇹🇷 土耳其节点": None,
    "🇷🇺 俄罗斯节点": None,
    "🏠 家宽节点": None,
    "🐢 低倍率节点": None,
}
BUILTIN = ("DIRECT", "REJECT", "PASS", "GLOBAL")


def split_group(line):
    """custom_proxy_group=名字`类型`成员…`参数…  →  名字, 类型, 成员列表, 参数列表"""
    fields = line[len("custom_proxy_group="):].split("`")
    members = [f[2:].strip() for f in fields[2:] if f.startswith("[]")]
    params = [f for f in fields[2:] if not f.startswith("[]")]
    return fields[0], fields[1], members, params


def build():
    if not SRC.exists():
        print("[错误] 找不到 " + str(SRC) + "（上游把模板改名了？）")
        return 1

    out, dropped, renamed, removed = [], [], 0, 0
    for line in SRC.read_text(encoding="utf-8").splitlines():
        s = line.strip()

        if s.startswith("custom_proxy_group="):
            name, gtype, members, params = split_group(line)
            if name in DELETE:
                dropped.append(name)
                continue
            kept = []
            for m in members:
                if m in DELETE:
                    new = DELETE[m]
                    if new is None:
                        removed += 1
                        continue
                    m = new
                    renamed += 1
                if m not in kept:          # 改名之后可能重复，去重
                    kept.append(m)
            if name not in DIRECT_ONLY and name != AUTO:
                if AUTO in kept:
                    kept.remove(AUTO)
                kept.insert(0, AUTO)       # 默认走代理
            out.append(
                "custom_proxy_group="
                + "`".join([name, gtype] + ["[]" + m for m in kept] + params)
            )
            continue

        if s.startswith("ruleset=") or s.startswith("clash_rule="):
            prefix = "ruleset=" if s.startswith("ruleset=") else "clash_rule="
            body = line[len(prefix):]
            if "," in body:
                target, rest = body.split(",", 1)
                if target.strip() in DELETE:
                    line = prefix + str(DELETE[target.strip()] or "DIRECT") + "," + rest
            out.append(line)
            continue

        out.append(line)

    DST.parent.mkdir(parents=True, exist_ok=True)
    with open(DST, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(out) + "\n")

    groups = [l for l in out if l.startswith("custom_proxy_group=")]
    rules = [l for l in out if l.startswith("ruleset=")]
    print("[完成] 生成 " + str(DST) + "：" + str(len(groups)) + " 个分组 / " + str(len(rules)) + " 条规则")
    print("  删除分组 " + str(len(dropped)) + " 个；引用改名 " + str(renamed) + " 处；引用删除 " + str(removed) + " 处")

    names = {split_group(l)[0] for l in groups}
    bad = set()
    for l in groups:
        for m in split_group(l)[2]:
            if m not in names and m not in BUILTIN:
                bad.add(m)
    for l in rules:
        t = l[len("ruleset="):].split(",", 1)[0].strip()
        if t not in names and t not in BUILTIN:
            bad.add(t)
    if bad:
        print("[错误] 有引用找不到分组: " + ", ".join(sorted(bad)))
        return 2
    print("  自检通过：所有引用都有对应分组")
    return 0


if __name__ == "__main__":
    sys.exit(build())
