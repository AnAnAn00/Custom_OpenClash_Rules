#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从上游模板自动生成你自己的精简模板。

输入（上游那份，永远不要手改）: cfg/Custom_Clash_Full_Fallback.ini
输出（你的那份，订阅里 config= 指向它）: cfg/My_Clash.ini

用法:
    python3 tools/build_my_ini.py
    python3 tools/build_my_ini.py 源文件 输出文件

上游每次更新后重跑一遍即可；GitHub Actions 里也是跑这个脚本。
要调整规则，只改下面 CONFIG 区的常量。
"""
import pathlib
import sys

# Windows 控制台默认 GBK，打印 emoji 会报错；统一成 UTF-8
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# ==================== CONFIG ====================
SRC_DEFAULT = "cfg/Custom_Clash_Full_Fallback.ini"
DST_DEFAULT = "cfg/My_Clash.ini"

AUTO = "♻️ 自动选择"

# 你的节点里没有这些地区/关键字，或者和「自动选择」完全重复 → 整组删掉
REMOVE_GROUPS = {
    "🇭🇰 香港节点", "🇺🇸 美国节点", "🇯🇵 日本节点", "🇸🇬 新加坡节点",
    "🇼🇸 台湾节点", "🇰🇷 韩国节点", "🇨🇦 加拿大节点", "🇬🇧 英国节点",
    "🇫🇷 法国节点", "🇩🇪 德国节点", "🇳🇱 荷兰节点", "🇹🇷 土耳其节点",
    "🇷🇺 俄罗斯节点", "🏠 家宽节点", "🐢 低倍率节点", "🌐 其他地区",
}

# 「自动选择」组的行为：
#   "select"   = 手动选，点哪个用哪个，不会再自己跳
#   "url-test" = 保留自动测速，但用下面的容差让它别频繁换节点
AUTO_MODE = "select"
AUTO_TOLERANCE = "500"
TEST_URL = "http://www.gstatic.com/generate_204"

# 这些分组里把「自动选择」提到第一位（= 默认就走代理）
# 其余分组保持上游顺序，比如「苹果服务/微软服务/国内AI服务」默认仍是直连
AUTO_FIRST_GROUPS = {
    "🌍 国外域名",
}

# 这些组的成员列表强制重写，避免指向被删掉的分组（否则会走直连）
FORCE_MEMBERS = {
    "🐟 漏网之鱼": [AUTO, "DIRECT"],
    # 非标端口（PT/BT 等）默认直连，需要时可在面板里切到「漏网之鱼」走代理
    "🔀 非标端口": ["🎯 全球直连", "🐟 漏网之鱼"],
}
# ================================================


def parse_fields(line: str, prefix: str):
    """把 custom_proxy_group=组名`类型`... 拆成字段列表"""
    return line[len(prefix):].split("`")


def rebuild_auto(fields):
    """重写「自动选择」组的类型和参数"""
    regex = fields[2] if len(fields) > 2 else ".*"
    if AUTO_MODE == "select":
        # select 组不需要测速参数，只保留 名称/类型/正则
        return [fields[0], "select", regex]
    url = fields[3] if len(fields) > 3 and fields[3].startswith("http") else TEST_URL
    return [fields[0], "url-test", regex, url, f"300,{AUTO_TOLERANCE},50"]


def dedup_members(fields):
    """去掉重复的 []成员"""
    seen, out = set(), []
    for f in fields:
        if f.startswith("[]"):
            if f in seen:
                continue
            seen.add(f)
        out.append(f)
    return out


def build(src: pathlib.Path, dst: pathlib.Path) -> int:
    if not src.exists():
        print(f"[错误] 找不到源文件 {src}")
        print("       上游是不是把模板改名了？去 cfg/ 目录看一眼，然后改脚本里的 SRC_DEFAULT")
        return 1

    lines = src.read_text(encoding="utf-8").splitlines()
    out_lines = []
    removed, fixed, repointed = set(), [], []
    auto_found = False

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("custom_proxy_group="):
            fields = parse_fields(line, "custom_proxy_group=")
            name = fields[0].strip()

            if name in REMOVE_GROUPS:
                removed.add(name)
                continue

            if name == AUTO:
                auto_found = True
                fields = rebuild_auto(fields)
                out_lines.append("custom_proxy_group=" + "`".join(fields))
                continue

            if name in FORCE_MEMBERS:
                fields = [fields[0], fields[1]] + [f"[]{m}" for m in FORCE_MEMBERS[name]]
                fixed.append(name)
                out_lines.append("custom_proxy_group=" + "`".join(fields))
                continue

            # 普通分组：删掉对被移除分组的引用
            new_fields, lost_proxy = [], False
            for i, f in enumerate(fields):
                if i >= 2 and f.startswith("[]") and f[2:].strip() in REMOVE_GROUPS:
                    if f[2:].strip() not in ("DIRECT", "REJECT"):
                        lost_proxy = True
                    continue
                new_fields.append(f)
            new_fields = dedup_members(new_fields)

            members = [f[2:].strip() for f in new_fields[2:] if f.startswith("[]")]
            if lost_proxy and AUTO not in members:
                # 原来靠地区分组走代理，现在这些组没了 → 改成走「自动选择」，别退化成直连
                new_fields = new_fields[:2] + [f"[]{AUTO}"] + new_fields[2:]
                fixed.append(name)
            if name in AUTO_FIRST_GROUPS and AUTO in [f[2:].strip() for f in new_fields[2:] if f.startswith("[]")]:
                rest = [f for f in new_fields[2:] if not (f.startswith("[]") and f[2:].strip() == AUTO)]
                new_fields = new_fields[:2] + [f"[]{AUTO}"] + rest
            if len(new_fields) < 3:
                new_fields.append("[]DIRECT")
            out_lines.append("custom_proxy_group=" + "`".join(new_fields))
            continue

        # 规则行如果指向被删掉的分组，改成指向「自动选择」，避免规则失效
        for prefix in ("ruleset=", "clash_rule="):
            if stripped.startswith(prefix):
                body = line[len(prefix):]
                if "," in body:
                    target, rest = body.split(",", 1)
                    if target.strip() in REMOVE_GROUPS:
                        repointed.append(target.strip())
                        line = f"{prefix}{AUTO},{rest}"
                break
        out_lines.append(line)

    dst.parent.mkdir(parents=True, exist_ok=True)
    # newline="\n" 保证 Windows 本地和 GitHub Actions 生成的文件字节一致
    with open(dst, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(out_lines) + "\n")

    print(f"[完成] 生成 {dst}（{len(out_lines)} 行）")
    print(f"  删除分组 {len(removed)} 个: {', '.join(sorted(removed)) or '无'}")
    print(f"  成员补全/重写: {', '.join(fixed) or '无'}")
    print(f"  规则改指向 {AUTO}: {', '.join(sorted(set(repointed))) or '无'}")

    missing = REMOVE_GROUPS - removed
    if missing:
        print(f"  [提醒] 模板里没找到这些分组（可能上游改名了）: {', '.join(sorted(missing))}")
    if not auto_found:
        print(f"  [提醒] 没找到「{AUTO}」分组，检查一下上游模板")
    return 0


def main():
    src = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else SRC_DEFAULT)
    dst = pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else DST_DEFAULT)
    sys.exit(build(src, dst))


if __name__ == "__main__":
    main()
